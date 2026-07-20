import { createHash } from "node:crypto";
import { GoogleGenAI, ThinkingLevel } from "@google/genai";

type Usage = {
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  inputTokenDetails: {
    cacheReadTokens: number;
    cacheWriteTokens: number;
  };
};

type CacheHandle = {
  name: string | null;
  createUsage: Usage | null;
};

type CacheEntry = {
  promise: Promise<CacheHandle>;
  createUsageClaimed: boolean;
};

export type CachedJsonRequest = {
  model: string;
  systemInstruction: string;
  stablePrompt: string;
  prompt: string;
  responseJsonSchema: unknown;
  temperature: number;
  seed: number;
  maxOutputTokens: number;
  thinkingLevel?: "minimal" | "low" | "medium" | "high";
};

export type CachedJsonResponse = {
  value: unknown;
  usage: Usage;
  cacheCreateUsage: Usage | null;
  modelId: string | null;
  responseId: string | null;
  finishReason: string | null;
};

export class EvaluatorGenerationError extends Error {
  usage: Usage | null;
  finishReason: string | null;

  constructor(message: string, options?: { usage?: Usage | null; finishReason?: string | null; cause?: unknown }) {
    super(message, { cause: options?.cause });
    this.name = "EvaluatorGenerationError";
    this.usage = options?.usage ?? null;
    this.finishReason = options?.finishReason ?? null;
  }
}

const cacheTtl = "7200s";
const minimumCacheCharacters = 14_000;
const cacheEntries = new Map<string, CacheEntry>();
let client: GoogleGenAI | null = null;
const thinkingLevels = {
  minimal: ThinkingLevel.MINIMAL,
  low: ThinkingLevel.LOW,
  medium: ThinkingLevel.MEDIUM,
  high: ThinkingLevel.HIGH,
} as const;

function project() {
  const value = process.env.GOOGLE_VERTEX_PROJECT ?? process.env.GOOGLE_CLOUD_PROJECT;
  if (!value) {
    throw new Error("The evaluator requires GOOGLE_VERTEX_PROJECT (or GOOGLE_CLOUD_PROJECT) with official ADC authentication.");
  }
  return value;
}

function location() {
  return process.env.GOOGLE_VERTEX_LOCATION ?? process.env.GOOGLE_CLOUD_LOCATION ?? "global";
}

function evaluatorClient() {
  client ??= new GoogleGenAI({
    vertexai: true,
    project: project(),
    location: location(),
    httpOptions: { apiVersion: "v1" },
  });
  return client;
}

function cacheKey(request: CachedJsonRequest) {
  return createHash("sha256").update(JSON.stringify({
    project: project(),
    location: location(),
    model: request.model,
    systemInstruction: request.systemInstruction,
    stablePrompt: request.stablePrompt,
  })).digest("hex");
}

function generationUsage(metadata: any): Usage {
  const inputTokens = metadata?.promptTokenCount ?? 0;
  const outputTokens = (metadata?.candidatesTokenCount ?? 0) + (metadata?.thoughtsTokenCount ?? 0);
  return {
    inputTokens,
    outputTokens,
    totalTokens: metadata?.totalTokenCount ?? inputTokens + outputTokens,
    inputTokenDetails: {
      cacheReadTokens: metadata?.cachedContentTokenCount ?? 0,
      cacheWriteTokens: 0,
    },
  };
}

function cacheWriteUsage(tokens: number): Usage {
  return {
    inputTokens: tokens,
    outputTokens: 0,
    totalTokens: tokens,
    inputTokenDetails: { cacheReadTokens: 0, cacheWriteTokens: tokens },
  };
}

async function createCache(request: CachedJsonRequest): Promise<CacheHandle> {
  if (request.systemInstruction.length + request.stablePrompt.length < minimumCacheCharacters) {
    return { name: null, createUsage: null };
  }
  let cache;
  try {
    cache = await evaluatorClient().caches.create({
      model: request.model,
      config: {
        displayName: `doc2md-evaluator-${cacheKey(request).slice(0, 16)}`,
        systemInstruction: request.systemInstruction,
        contents: [{ role: "user", parts: [{ text: request.stablePrompt }] }],
        ttl: cacheTtl,
      },
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (/minimum token count to start caching/i.test(message)) return { name: null, createUsage: null };
    throw error;
  }
  if (!cache.name) throw new Error("Vertex created an evaluator cache without a resource name.");
  const tokens = cache.usageMetadata?.totalTokenCount ?? 0;
  return { name: cache.name, createUsage: tokens > 0 ? cacheWriteUsage(tokens) : null };
}

async function cacheLease(request: CachedJsonRequest) {
  const key = cacheKey(request);
  let entry = cacheEntries.get(key);
  if (!entry) {
    entry = { promise: createCache(request), createUsageClaimed: false };
    cacheEntries.set(key, entry);
  }
  const handle = await entry.promise;
  const createUsage = !entry.createUsageClaimed ? handle.createUsage : null;
  entry.createUsageClaimed = true;
  return { ...handle, createUsage };
}

export async function generateCachedJson(request: CachedJsonRequest): Promise<CachedJsonResponse> {
  const cache = await cacheLease(request);
  const response = await evaluatorClient().models.generateContent({
    model: request.model,
    contents: cache.name ? request.prompt : `${request.stablePrompt}\n\n${request.prompt}`,
    config: {
      ...(cache.name
        ? { cachedContent: cache.name }
        : { systemInstruction: request.systemInstruction }),
      temperature: request.temperature,
      seed: request.seed,
      maxOutputTokens: request.maxOutputTokens,
      responseMimeType: "application/json",
      responseJsonSchema: request.responseJsonSchema,
      ...(request.thinkingLevel ? { thinkingConfig: { thinkingLevel: thinkingLevels[request.thinkingLevel] } } : {}),
    },
  });
  const usage = generationUsage(response.usageMetadata);
  const finishReason = response.candidates?.[0]?.finishReason ?? null;
  const text = response.text;
  if (!text) {
    throw new EvaluatorGenerationError("Evaluator returned no JSON text.", { usage, finishReason });
  }
  try {
    return {
      value: JSON.parse(text),
      usage,
      cacheCreateUsage: cache.createUsage,
      modelId: response.modelVersion ?? null,
      responseId: response.responseId ?? null,
      finishReason,
    };
  } catch (cause) {
    throw new EvaluatorGenerationError(`Evaluator returned invalid JSON (${text.length} characters).`, {
      usage,
      finishReason,
      cause,
    });
  }
}

export async function disposeEvaluatorCaches() {
  const entries = [...cacheEntries.values()];
  cacheEntries.clear();
  const handles = await Promise.all(entries.map((entry) => entry.promise.catch(() => null)));
  await Promise.all(handles.flatMap((handle) => handle?.name
    ? [evaluatorClient().caches.delete({ name: handle.name }).catch(() => undefined)]
    : []));
}
