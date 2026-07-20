import { GoogleGenAI, ThinkingLevel } from "@google/genai";
import { setTimeout as delay } from "node:timers/promises";

type Usage = {
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  inputTokenDetails: {
    cacheReadTokens: number;
    cacheWriteTokens: number;
  };
};

export type EvaluatorJsonRequest = {
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

export type EvaluatorJsonResponse = {
  value: unknown;
  usage: Usage;
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

let client: GoogleGenAI | null = null;
// The personal AI Studio project allows 15 requests/minute for the evaluator.
// Allocate request starts globally within this process so concurrent case and
// batch evaluation remains below that limit without serializing response time.
const evaluatorStartIntervalMs = 6_000;
let nextEvaluatorStartAt = 0;
let pacingTail: Promise<void> = Promise.resolve();
const thinkingLevels = {
  minimal: ThinkingLevel.MINIMAL,
  low: ThinkingLevel.LOW,
  medium: ThinkingLevel.MEDIUM,
  high: ThinkingLevel.HIGH,
} as const;

function evaluatorClient() {
  const apiKey = process.env.GEMINI_API_KEY ?? process.env.GOOGLE_API_KEY;
  if (!apiKey) throw new Error("The evaluator requires GEMINI_API_KEY for the Google AI Studio Gemini API.");
  client ??= new GoogleGenAI({ apiKey });
  return client;
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

async function waitForEvaluatorStart() {
  const previous = pacingTail;
  let release!: () => void;
  pacingTail = new Promise<void>((resolve) => {
    release = resolve;
  });
  await previous;
  try {
    const waitMs = Math.max(0, nextEvaluatorStartAt - Date.now());
    if (waitMs > 0) await delay(waitMs);
    nextEvaluatorStartAt = Date.now() + evaluatorStartIntervalMs;
  } finally {
    release();
  }
}

export async function generateEvaluatorJson(request: EvaluatorJsonRequest): Promise<EvaluatorJsonResponse> {
  await waitForEvaluatorStart();
  const response = await evaluatorClient().models.generateContent({
    model: request.model,
    contents: `${request.stablePrompt}\n\n${request.prompt}`,
    config: {
      systemInstruction: request.systemInstruction,
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
  if (!text) throw new EvaluatorGenerationError("Evaluator returned no JSON text.", { usage, finishReason });
  try {
    return {
      value: JSON.parse(text),
      usage,
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
