import { access, mkdir, readFile, rm } from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";
import { performance } from "node:perf_hooks";
import { fileURLToPath } from "node:url";
import { generateText } from "ai";
import { createGoogleVertex } from "@ai-sdk/google-vertex";
import { createOpenAI } from "@ai-sdk/openai";
import { z } from "zod";
import { fileSha256, hashObject, sha256, sha256Bytes } from "./cache.js";
import { runBoundedJobs } from "./concurrency.js";
import {
  acquireSampleLock,
  atomicWriteJson,
  atomicWriteText,
  calculateTokenCostUsd,
  parseRunCliArgs,
  runUsage,
  writeImmutableJson,
} from "./runRuntime.js";
import { canonicalProjectReference, loadBenchmarkManifest } from "./manifest.js";

export type ManifestCase = {
  id: string;
  title: string;
  family: string;
  pdf: string;
};

export type Manifest = {
  name: string;
  suite?: string;
  scoreName?: string;
  inputProtocol?: string;
  cases: ManifestCase[];
};

const nonnegativeInteger = z.number().int().nonnegative();
const tokenUsageSchema = z.object({
  inputTokens: nonnegativeInteger,
  outputTokens: nonnegativeInteger,
  totalTokens: nonnegativeInteger,
}).passthrough();
const runCacheSchema = z.strictObject({
  schemaVersion: z.literal(3),
  runKey: z.string().length(64),
  inferenceFingerprint: z.string().length(64),
  sample: z.string().regex(/^\d{3}$/),
  pdfHash: z.string().length(64),
  promptHash: z.string().length(64),
  modelConfigHash: z.string().length(64),
  protocolHash: z.string().length(64),
  inferenceBenchmarkFingerprint: z.string().length(64),
  providerFileMode: z.string().min(1),
  predictionHash: z.string().length(64),
});
const inferenceAttemptMarkerSchema = z.strictObject({
  schemaVersion: z.literal(1),
  kind: z.literal("paid_inference_attempt_reserved"),
  runKey: z.string().length(64),
  caseId: z.string().min(1),
  modelId: z.string().min(1),
  sample: z.string().regex(/^\d{3}$/),
  logicalSampleDraw: z.literal(1),
  transportMaxRetries: nonnegativeInteger,
  runMode: z.enum(["development_anchor", "repeat_validation", "final_validation"]),
  authorizationHash: z.string().length(64).nullable(),
  createdAt: z.string().min(1),
});
const inferenceAttemptReferenceSchema = z.strictObject({
  markerPath: z.string().min(1),
  markerHash: z.string().length(64),
  logicalSampleDraw: z.literal(1),
  logicalGenerationCalls: z.literal(1),
  transportMaxRetries: nonnegativeInteger,
  transportRequestAttempts: z.number().int().positive(),
  retriesAreCohortSamples: z.literal(false),
});
const currentRunArtifactSchema = z.object({
  artifactStatus: z.literal("scoreable_model_response"),
  responseReceived: z.literal(true),
  caseId: z.string().min(1),
  title: z.string().min(1),
  modelId: z.string().min(1),
  modelName: z.string().min(1),
  provider: z.enum(["google-vertex", "openai"]),
  suite: z.string().min(1),
  manifestPath: z.string().min(1),
  inputProtocol: z.string().min(1),
  providerFileMode: z.string().min(1),
  executionProvenance: z.object({
    schemaVersion: z.literal(1),
    protocolVersion: z.string().min(1),
    inputMode: z.string().min(1),
    inputProtocol: z.string().min(1),
    mediaType: z.literal("application/pdf"),
    providerFileMode: z.string().min(1),
    maxOutputTokens: nonnegativeInteger,
    maxRetries: nonnegativeInteger,
    transportEpoch: z.string().min(1),
    providerPayloadMode: z.string().min(1),
    samplingMode: z.string().min(1),
    logicalSampleDraw: z.literal(1),
    logicalGenerationCalls: z.literal(1),
    transportRequestAttempts: z.number().int().positive(),
    retriesAreCohortSamples: z.literal(false),
    runMode: z.enum(["development_anchor", "repeat_validation", "final_validation"]),
    authorizationHash: z.string().length(64).nullable(),
    sdkVersions: z.strictObject({
      ai: z.string().min(1),
      providerPackage: z.string().min(1),
      providerPackageVersion: z.string().min(1),
    }),
    promptHash: z.string().length(64),
    protocolHash: z.string().length(64),
    pdfHash: z.string().length(64),
    modelConfigHash: z.string().length(64),
    inferenceFingerprint: z.string().length(64),
    inferenceBenchmarkFingerprint: z.string().length(64),
  }).passthrough(),
  providerMetadata: z.object({
    requested: z.object({ provider: z.string().min(1), modelId: z.string().min(1) }).passthrough(),
    resolved: z.object({ provider: z.string().min(1), modelId: z.string().min(1) }).passthrough(),
  }).passthrough(),
  elapsedMs: nonnegativeInteger,
  finishReason: z.string().min(1),
  usage: tokenUsageSchema,
  estimatedCostUsd: z.number().finite().nonnegative(),
  pricing: z.object({
    version: z.string().min(1),
    currency: z.literal("USD"),
    inputPerMillion: z.number().finite().nonnegative(),
    cachedInputPerMillion: z.number().finite().nonnegative(),
    outputPerMillion: z.number().finite().nonnegative(),
    estimatedCostUsd: z.number().finite().nonnegative(),
  }).passthrough(),
  outputLength: nonnegativeInteger,
  sample: z.string().regex(/^\d{3}$/),
  cache: runCacheSchema,
  inferenceAttempt: inferenceAttemptReferenceSchema,
  inputMode: z.string().min(1),
}).passthrough();

export type ModelSpec = {
  id: string;
  modelName: string;
  provider: "google-vertex" | "openai";
  reasoning?: "none" | "minimal";
  location?: string;
  baseURL?: string;
  pricingVersion: string;
  inputPerMillion: number;
  cachedInputPerMillion: number;
  outputPerMillion: number;
};

const pricingVersion = "2026-07-10";

export const models: Record<string, ModelSpec> = {
  "vertex-gemini-2.5-flash-lite": {
    id: "vertex-gemini-2.5-flash-lite",
    modelName: "gemini-2.5-flash-lite",
    provider: "google-vertex",
    reasoning: "minimal",
    location: "global",
    pricingVersion,
    inputPerMillion: 0.1,
    cachedInputPerMillion: 0.01,
    outputPerMillion: 0.4,
  },
  "vertex-gemini-3.1-flash-lite": {
    id: "vertex-gemini-3.1-flash-lite",
    modelName: "gemini-3.1-flash-lite",
    provider: "google-vertex",
    reasoning: "minimal",
    pricingVersion,
    inputPerMillion: 0.25,
    cachedInputPerMillion: 0.025,
    outputPerMillion: 1.5,
  },
  "vertex-gemini-3.1-pro": {
    id: "vertex-gemini-3.1-pro",
    modelName: "gemini-3.1-pro-preview",
    provider: "google-vertex",
    reasoning: "minimal",
    pricingVersion,
    inputPerMillion: 2,
    cachedInputPerMillion: 0.2,
    outputPerMillion: 12,
  },
  "vertex-gemini-3-flash-preview": {
    id: "vertex-gemini-3-flash-preview",
    modelName: "gemini-3-flash-preview",
    provider: "google-vertex",
    reasoning: "minimal",
    location: "global",
    pricingVersion,
    inputPerMillion: 0.5,
    cachedInputPerMillion: 0.05,
    outputPerMillion: 3,
  },
  "openai-gpt-5-nano": {
    id: "openai-gpt-5-nano",
    modelName: "gpt-5-nano",
    provider: "openai",
    reasoning: "minimal",
    pricingVersion,
    inputPerMillion: 0.05,
    cachedInputPerMillion: 0.005,
    outputPerMillion: 0.4,
  },
  "openai-gpt-5.4-nano": {
    id: "openai-gpt-5.4-nano",
    modelName: "gpt-5.4-nano",
    provider: "openai",
    reasoning: "none",
    pricingVersion,
    inputPerMillion: 0.2,
    cachedInputPerMillion: 0.02,
    outputPerMillion: 1.25,
  },
  "openai-gpt-5.4-mini": {
    id: "openai-gpt-5.4-mini",
    modelName: "gpt-5.4-mini",
    provider: "openai",
    reasoning: "none",
    pricingVersion,
    inputPerMillion: 0.75,
    cachedInputPerMillion: 0.075,
    outputPerMillion: 4.5,
  },
  "openai-gpt-5.5": {
    id: "openai-gpt-5.5",
    modelName: "gpt-5.5",
    provider: "openai",
    reasoning: "none",
    pricingVersion,
    inputPerMillion: 5,
    cachedInputPerMillion: 0.5,
    outputPerMillion: 30,
  },
  "vertex-gemini-3.5-flash": {
    id: "vertex-gemini-3.5-flash",
    modelName: "gemini-3.5-flash",
    provider: "google-vertex",
    reasoning: "minimal",
    pricingVersion,
    inputPerMillion: 1.5,
    cachedInputPerMillion: 0.15,
    outputPerMillion: 9,
  },
};

export const benchmarkModelIds = ["openai-gpt-5-nano", "vertex-gemini-3.1-flash-lite"] as const;

export const finalValidationAuthorizationEnvironment = "DOC2MD_FINAL_VALIDATION_AUTHORIZATION";
const finalValidationAuthorizationPrefix = "final-validation:";
export const repeatValidationAuthorizationEnvironment = "DOC2MD_REPEAT_VALIDATION_AUTHORIZATION";
const repeatValidationAuthorizationPrefix = "repeat-validation:";

export type PaidInferenceAuthorization = {
  runMode: "development_anchor" | "repeat_validation" | "final_validation";
  authorizationHash: string | null;
};

/**
 * Central authorization gate for every paid inference path. A non-anchor model
 * requires the same checkpoint id from both the caller and the environment, so
 * selecting a registry model by name alone can never start a paid request.
 */
export function authorizePaidInference(
  modelId: string,
  suppliedAuthorization?: string,
  environment: NodeJS.ProcessEnv = process.env,
): PaidInferenceAuthorization {
  if ((benchmarkModelIds as readonly string[]).includes(modelId)) {
    return { runMode: "development_anchor", authorizationHash: null };
  }
  const configuredAuthorization = environment[finalValidationAuthorizationEnvironment]?.trim();
  const supplied = suppliedAuthorization?.trim();
  if (
    !configuredAuthorization ||
    !supplied ||
    configuredAuthorization !== supplied ||
    !configuredAuthorization.startsWith(finalValidationAuthorizationPrefix) ||
    configuredAuthorization.length <= finalValidationAuthorizationPrefix.length
  ) {
    throw new Error(
      `${modelId} is not a development anchor. A non-anchor final-validation run requires a checkpoint id beginning ` +
        `with ${JSON.stringify(finalValidationAuthorizationPrefix)} supplied both through --final-validation-authorization and ` +
        `${finalValidationAuthorizationEnvironment}.`,
    );
  }
  return { runMode: "final_validation", authorizationHash: sha256(configuredAuthorization) };
}

/**
 * A repeat anchor draw is a separately authorized validation observation. It
 * cannot target non-anchor models or the official 001 slot, and its checkpoint
 * identity is persisted as a hash in the immutable attempt ledger.
 */
export function authorizeRepeatValidation(
  modelId: string,
  suppliedAuthorization?: string,
  environment: NodeJS.ProcessEnv = process.env,
): PaidInferenceAuthorization {
  if (!(benchmarkModelIds as readonly string[]).includes(modelId)) {
    throw new Error(`${modelId} is not a development anchor and cannot use repeat-anchor authorization.`);
  }
  const configuredAuthorization = environment[repeatValidationAuthorizationEnvironment]?.trim();
  const supplied = suppliedAuthorization?.trim();
  if (
    !configuredAuthorization ||
    !supplied ||
    configuredAuthorization !== supplied ||
    !configuredAuthorization.startsWith(repeatValidationAuthorizationPrefix) ||
    configuredAuthorization.length <= repeatValidationAuthorizationPrefix.length
  ) {
    throw new Error(
      `A repeat anchor draw requires a checkpoint id beginning with ${JSON.stringify(repeatValidationAuthorizationPrefix)} ` +
        `supplied both through the repeat-validation command and ${repeatValidationAuthorizationEnvironment}.`,
    );
  }
  return { runMode: "repeat_validation", authorizationHash: sha256(configuredAuthorization) };
}

// Development runs intentionally use one stochastic draw. Repeated cohorts are
// reserved for an explicitly approved final-validation checkpoint; changing
// this value is part of the hashed inference protocol, so prior multi-sample
// artifacts cannot be mistaken for current development evidence.
export const samplesPerModelCase = 1;
// Both development anchors support at least 65,535 output tokens. Keep enough
// headroom for exhaustive long-document reconstruction so a 48-page case is
// measuring model fidelity rather than an artificial harness truncation.
export const maxOutputTokens = 60_000;
export const inputMode = "native_pdf";
export const inferenceProtocolVersion = "native-pdf-v3-immutable-attempt-ledger";
export const inferenceMaxRetries = 2;
export const inferenceConcurrency = positiveIntegerEnvironment("DOC2MD_INFERENCE_CONCURRENCY", 6);
const pdfMediaType = "application/pdf";

function positiveIntegerEnvironment(name: string, fallback: number) {
  const raw = process.env[name];
  if (raw === undefined || raw === "") return fallback;
  const parsed = Number(raw);
  if (!Number.isSafeInteger(parsed) || parsed < 1 || parsed > 64) {
    throw new Error(`${name} must be an integer from 1 through 64.`);
  }
  return parsed;
}

export const prompt = `Convert the attached PDF into one faithful Markdown document for downstream machine use.

Return only Markdown. Do not add commentary, citations, JSON, code fences, or an executive summary.

Reconstruct the document exhaustively:
- Process every page and every visible region in source order.
- Preserve all readable text, headings, section hierarchy, lists, captions, footnotes, stamps, annotations, handwritten-style fields, signatures, page-level notes, and document-state notes.
- Do not omit repetitive, dense, low-level, appendix, tabular, or visually embedded information just because it looks secondary.
- Do not paraphrase a table, schedule, matrix, register, ledger, checklist, or form into a summary when row/column/label/value relationships are present.

Tables, forms, and structured regions:
- Preserve every visible row, column, header, unit, label, value, subtotal, footnote marker, continuation row, blank/NA state, and row/column grouping.
- Use Markdown tables, HTML tables, or clear key-value lists only when the relationships remain unambiguous.
- Preserve checkbox/radio states, checked vs unchecked vs disabled states, strikeouts, insertions, corrections, voided values, and final/current values.

Visual and non-text regions:
- For charts, diagrams, maps, floorplans, screenshots, photos, timelines, heatmaps, chromatograms, scorecards, and other visual content, insert inline descriptions or tables at the location where the visual appears.
- Include labels, legends, axes, units, thresholds, colors, symbols, arrows, callouts, spatial relationships, and printed numeric values.
- If exact chart values are printed, include the exact values. If values are only visually inferable, describe the trend or approximate values without inventing precision.

Source-state conflicts:
- Rendered visible current content wins over hidden, stale, covered, deleted, or superseded PDF text.
- Preserve deleted/superseded/stale content only when it is visibly part of the document's reading experience, and clearly mark it as deleted, superseded, draft, historical, or context.
- If a visibly broken export still has legitimate selectable PDF text that is necessary to recover the document, use that recoverable text while preserving the visible document order.

The goal is faithful reconstruction of the original document's information and reading experience, not summarization or interpretation.`;

export function vertexProviderRoute(spec: ModelSpec, environment: NodeJS.ProcessEnv = process.env) {
  if (spec.provider !== "google-vertex") {
    throw new Error(`Cannot build a Vertex route for non-Vertex model ${spec.id}.`);
  }

  const apiKeyMode = Boolean(environment.GOOGLE_VERTEX_API_KEY);
  const location = spec.location ?? environment.GOOGLE_VERTEX_LOCATION;
  const project = environment.GOOGLE_VERTEX_PROJECT;
  let baseURL = spec.baseURL;

  // The provider SDK's Express/API-key endpoint ignores its `location`
  // option. Use the standard project-scoped endpoint when a model declares a
  // location, while retaining API-key authentication through x-goog-api-key.
  if (apiKeyMode && spec.location && !baseURL) {
    if (!project) {
      throw new Error(
        `${spec.id} requires GOOGLE_VERTEX_PROJECT because ${spec.modelName} is routed to the explicit Vertex location ${spec.location}.`,
      );
    }
    if (!/^[a-z0-9][a-z0-9._:-]*$/i.test(project)) {
      throw new Error("GOOGLE_VERTEX_PROJECT contains characters that are not valid in a Vertex resource path.");
    }
    if (!/^[a-z0-9-]+$/i.test(spec.location)) {
      throw new Error(`Invalid Vertex location ${spec.location}.`);
    }
    const host = spec.location === "global" ? "aiplatform.googleapis.com" : `${spec.location}-aiplatform.googleapis.com`;
    baseURL = `https://${host}/v1/projects/${encodeURIComponent(project)}/locations/${spec.location}/publishers/google`;
  }

  return {
    authMode: apiKeyMode ? "express_api_key" : "application_default_credentials",
    project: apiKeyMode && !spec.location ? null : project ?? null,
    location: location ?? null,
    baseURL: baseURL ?? null,
  } as const;
}

type TransportAttemptCounter = { requests: number };

function countedFetch(counter: TransportAttemptCounter): typeof globalThis.fetch {
  return async (input, init) => {
    counter.requests += 1;
    return globalThis.fetch(input, init);
  };
}

function providerModel(spec: ModelSpec, counter: TransportAttemptCounter) {
  const fetch = countedFetch(counter);
  switch (spec.provider) {
    case "google-vertex": {
      const route = vertexProviderRoute(spec);
      return createGoogleVertex({
        location: route.location ?? undefined,
        baseURL: route.baseURL ?? undefined,
        fetch,
      })(spec.modelName);
    }
    case "openai":
      return createOpenAI({ fetch })(spec.modelName);
  }
}

export function modelPricingFingerprint(spec: ModelSpec) {
  return hashObject({
    schemaVersion: 2,
    modelId: spec.id,
    pricingVersion: spec.pricingVersion,
    inputPerMillion: spec.inputPerMillion,
    cachedInputPerMillion: spec.cachedInputPerMillion,
    outputPerMillion: spec.outputPerMillion,
    calculatorHash: sha256(calculateTokenCostUsd.toString()),
  });
}

export function modelConfigFingerprint(spec: ModelSpec) {
  const route = spec.provider === "google-vertex" ? vertexProviderRoute(spec) : null;
  const providerRuntime = route
    ? {
        authMode: route.authMode,
        project: route.project,
        location: route.location,
        ...(route.baseURL !== (spec.baseURL ?? null) ? { effectiveBaseURL: route.baseURL } : {}),
      }
    : { authMode: "openai_api_key" };
  return hashObject({
    schemaVersion: 2,
    modelName: spec.modelName,
    provider: spec.provider,
    reasoning: spec.reasoning ?? null,
    location: spec.location ?? null,
    baseURL: spec.baseURL ?? null,
    providerRuntime,
  });
}

export function priceReport(spec: ModelSpec, usage: any) {
  return {
    version: spec.pricingVersion,
    source:
      spec.provider === "openai"
        ? `https://developers.openai.com/api/docs/models/${spec.modelName}`
        : "https://cloud.google.com/gemini-enterprise-agent-platform/generative-ai/pricing",
    basis: "standard on-demand token pricing; documents remain below long-context thresholds",
    currency: "USD",
    inputPerMillion: spec.inputPerMillion,
    cachedInputPerMillion: spec.cachedInputPerMillion,
    outputPerMillion: spec.outputPerMillion,
    estimatedCostUsd: calculateTokenCostUsd(spec, usage),
  };
}

export class RunInfrastructureError extends Error {
  constructor(message: string, options?: ErrorOptions) {
    super(message, options);
    this.name = "RunInfrastructureError";
  }
}

async function exists(filePath: string) {
  try {
    await access(filePath);
    return true;
  } catch {
    return false;
  }
}

export type InferenceProtocol = {
  version: string;
  inputMode: string;
  inputProtocol: string;
  mediaType: string;
  providerFileMode: string;
  maxOutputTokens: number;
  maxRetries: number;
  samplesPerModelCase: number;
  transportEpoch: string;
  providerPayloadMode: string;
  samplingMode: string;
  sdkVersions: {
    ai: string;
    providerPackage: string;
    providerPackageVersion: string;
  };
};

const require = createRequire(import.meta.url);
const aiSdkVersion = (require("ai/package.json") as { version: string }).version;
const inferenceTransportEpoch = "generate-text-native-pdf-buffer-v3-counted-transport";
const inferenceProviderPayloadMode = "messages.user.content.file.buffer";
const inferenceSamplingMode = "provider-default-sampling";

function inferenceSdkVersions(spec: ModelSpec): InferenceProtocol["sdkVersions"] {
  const providerPackage = spec.provider === "openai" ? "@ai-sdk/openai" : "@ai-sdk/google-vertex";
  const providerPackageVersion = (require(`${providerPackage}/package.json`) as { version: string }).version;
  return { ai: aiSdkVersion, providerPackage, providerPackageVersion };
}

export type RunContext = {
  suite: string;
  manifestPath: string;
  inputProtocol: string;
  providerFileMode: string;
  protocol: InferenceProtocol;
  protocolHash: string;
  promptHash: string;
  casePdfHashes: Record<string, string>;
  inferenceBenchmarkFingerprint: string;
};

async function providerFileMode(spec: ModelSpec, manifestPath: string) {
  try {
    const capabilitiesPath = path.join(path.dirname(manifestPath), "provider-capabilities.json");
    const capabilities = JSON.parse(await readFile(capabilitiesPath, "utf-8")) as {
      providers?: Record<string, { documents?: Record<string, { ingestionMode?: string }> }>;
    };
    return capabilities.providers?.[spec.provider]?.documents?.pdf?.ingestionMode ?? "unknown";
  } catch {
    return "unknown";
  }
}

export async function buildRunContext(spec: ModelSpec, manifest: Manifest, manifestPath: string): Promise<RunContext> {
  const canonicalManifestPath = canonicalProjectReference(manifestPath);
  const caseIds = manifest.cases.map((testCase) => testCase.id);
  if (new Set(caseIds).size !== caseIds.length) {
    throw new Error(`Benchmark manifest contains duplicate case ids: ${canonicalManifestPath}`);
  }
  const inputProtocol = manifest.inputProtocol ?? inputMode;
  const documentedProviderFileMode = await providerFileMode(spec, canonicalManifestPath);
  const protocol = {
    version: inferenceProtocolVersion,
    inputMode,
    inputProtocol,
    mediaType: pdfMediaType,
    providerFileMode: documentedProviderFileMode,
    maxOutputTokens,
    maxRetries: inferenceMaxRetries,
    samplesPerModelCase,
    transportEpoch: inferenceTransportEpoch,
    providerPayloadMode: inferenceProviderPayloadMode,
    samplingMode: inferenceSamplingMode,
    sdkVersions: inferenceSdkVersions(spec),
  } satisfies InferenceProtocol;
  const casePdfEntries = await Promise.all(
    manifest.cases.map(async (testCase) => [testCase.id, await fileSha256(testCase.pdf)] as const),
  );
  const casePdfHashes = Object.fromEntries(casePdfEntries);
  const promptHash = sha256(prompt);
  const protocolHash = hashObject(protocol);
  return {
    suite: manifest.suite ?? "official",
    manifestPath: canonicalManifestPath,
    inputProtocol,
    providerFileMode: documentedProviderFileMode,
    protocol,
    protocolHash,
    promptHash,
    casePdfHashes,
    inferenceBenchmarkFingerprint: hashObject({
      schemaVersion: 1,
      promptHash,
      protocolHash,
      cases: casePdfEntries.map(([caseId, pdfHash]) => ({ caseId, pdfHash })),
    }),
  };
}

export async function runCacheKey(testCase: ManifestCase, spec: ModelSpec, context: RunContext, sample: string) {
  if (!/^\d{3}$/.test(sample)) throw new Error(`Invalid sample id ${JSON.stringify(sample)}; expected a three-digit slot.`);
  const pdfHash = context.casePdfHashes[testCase.id] ?? (await fileSha256(testCase.pdf));
  const modelConfigHash = modelConfigFingerprint(spec);
  const runKey = hashObject({
    schemaVersion: 3,
    caseId: testCase.id,
    sample,
    pdfHash,
    promptHash: context.promptHash,
    modelConfigHash,
    protocolHash: context.protocolHash,
  });
  return {
    schemaVersion: 3,
    runKey,
    inferenceFingerprint: runKey,
    sample,
    pdfHash,
    promptHash: context.promptHash,
    modelConfigHash,
    protocolHash: context.protocolHash,
    inferenceBenchmarkFingerprint: context.inferenceBenchmarkFingerprint,
    providerFileMode: context.providerFileMode,
  };
}

async function readJsonIfExists(filePath: string) {
  if (!(await exists(filePath))) return null;
  try {
    return JSON.parse(await readFile(filePath, "utf-8")) as any;
  } catch {
    return null;
  }
}

export type RunCacheExpectation = {
  runKey: string;
  caseId: string;
  modelId: string;
  sample: string;
  suite: string;
  manifestPath: string;
  inputProtocol: string;
  providerFileMode: string;
  protocol: InferenceProtocol;
  inferenceBenchmarkFingerprint: string;
  protocolHash: string;
  modelConfigHash: string;
  pdfHash: string;
};

export function buildRunCacheExpectation(
  testCase: ManifestCase,
  spec: ModelSpec,
  context: RunContext,
  sample: string,
  cache: Awaited<ReturnType<typeof runCacheKey>>,
): RunCacheExpectation {
  return {
    runKey: cache.runKey,
    caseId: testCase.id,
    modelId: spec.id,
    sample,
    suite: context.suite,
    manifestPath: context.manifestPath,
    inputProtocol: context.inputProtocol,
    providerFileMode: context.providerFileMode,
    protocol: context.protocol,
    inferenceBenchmarkFingerprint: context.inferenceBenchmarkFingerprint,
    protocolHash: context.protocolHash,
    modelConfigHash: cache.modelConfigHash,
    pdfHash: cache.pdfHash,
  };
}

export function inferenceAttemptMarkerPath(sampleDirectory: string, runKey: string): string {
  return path.join(sampleDirectory, "attempts", `${runKey}.json`);
}

export async function readCurrentCachedRun(resultPath: string, predictionPath: string, expected: RunCacheExpectation) {
  const rawResult = await readJsonIfExists(resultPath);
  const parsed = currentRunArtifactSchema.safeParse(rawResult);
  if (!parsed.success) return null;
  const result = parsed.data;
  const spec = models[expected.modelId];
  if (!spec) return null;
  if (
    result.cache.runKey !== expected.runKey ||
    result.cache.inferenceFingerprint !== expected.runKey ||
    result.cache.sample !== expected.sample ||
    result.caseId !== expected.caseId ||
    result.modelId !== expected.modelId ||
    result.sample !== expected.sample ||
    result.suite !== expected.suite ||
    canonicalProjectReference(result.manifestPath) !== canonicalProjectReference(expected.manifestPath) ||
    result.inputProtocol !== expected.inputProtocol ||
    result.providerFileMode !== expected.providerFileMode ||
    result.modelName !== spec.modelName ||
    result.provider !== spec.provider ||
    result.cache.protocolHash !== expected.protocolHash ||
    result.cache.modelConfigHash !== expected.modelConfigHash ||
    result.cache.pdfHash !== expected.pdfHash ||
    result.executionProvenance.inferenceFingerprint !== expected.runKey ||
    result.executionProvenance.protocolHash !== expected.protocolHash ||
    result.executionProvenance.protocolVersion !== expected.protocol.version ||
    result.executionProvenance.mediaType !== expected.protocol.mediaType ||
    result.executionProvenance.maxOutputTokens !== expected.protocol.maxOutputTokens ||
    result.executionProvenance.maxRetries !== expected.protocol.maxRetries ||
    result.executionProvenance.transportEpoch !== expected.protocol.transportEpoch ||
    result.executionProvenance.providerPayloadMode !== expected.protocol.providerPayloadMode ||
    result.executionProvenance.samplingMode !== expected.protocol.samplingMode ||
    JSON.stringify(result.executionProvenance.sdkVersions) !== JSON.stringify(expected.protocol.sdkVersions) ||
    result.executionProvenance.modelConfigHash !== expected.modelConfigHash ||
    result.executionProvenance.pdfHash !== expected.pdfHash ||
    result.executionProvenance.promptHash !== result.cache.promptHash ||
    result.executionProvenance.providerFileMode !== expected.providerFileMode ||
    result.executionProvenance.inputProtocol !== expected.inputProtocol ||
    result.executionProvenance.inputMode !== inputMode ||
    result.providerMetadata.requested.provider !== spec.provider ||
    result.providerMetadata.requested.modelId !== spec.modelName ||
    result.estimatedCostUsd !== result.pricing.estimatedCostUsd
  ) {
    return null;
  }
  // Legacy artifacts used one broad catch block and could record disk/configuration
  // failures as model errors. They are not trustworthy scoreable responses.
  if (result.error) return null;
  const expectedAttemptPath = inferenceAttemptMarkerPath(path.dirname(resultPath), expected.runKey);
  if (canonicalProjectReference(result.inferenceAttempt.markerPath) !== canonicalProjectReference(expectedAttemptPath)) return null;
  const rawAttemptMarker = await readJsonIfExists(expectedAttemptPath);
  const parsedAttemptMarker = inferenceAttemptMarkerSchema.safeParse(rawAttemptMarker);
  if (!parsedAttemptMarker.success) return null;
  const attemptMarker = parsedAttemptMarker.data;
  const anchorRun = (benchmarkModelIds as readonly string[]).includes(expected.modelId);
  const expectedRunMode = anchorRun ? (expected.sample === "001" ? "development_anchor" : "repeat_validation") : "final_validation";
  if (
    attemptMarker.runKey !== expected.runKey ||
    attemptMarker.caseId !== expected.caseId ||
    attemptMarker.modelId !== expected.modelId ||
    attemptMarker.sample !== expected.sample ||
    attemptMarker.transportMaxRetries !== expected.protocol.maxRetries ||
    attemptMarker.runMode !== expectedRunMode ||
    (expectedRunMode === "development_anchor" ? attemptMarker.authorizationHash !== null : attemptMarker.authorizationHash === null) ||
    result.inferenceAttempt.logicalSampleDraw !== 1 ||
    result.inferenceAttempt.logicalGenerationCalls !== 1 ||
    result.inferenceAttempt.transportMaxRetries !== expected.protocol.maxRetries ||
    result.inferenceAttempt.transportRequestAttempts > expected.protocol.maxRetries + 1 ||
    result.inferenceAttempt.retriesAreCohortSamples !== false ||
    result.executionProvenance.logicalSampleDraw !== 1 ||
    result.executionProvenance.logicalGenerationCalls !== 1 ||
    result.executionProvenance.transportRequestAttempts !== result.inferenceAttempt.transportRequestAttempts ||
    result.executionProvenance.retriesAreCohortSamples !== false ||
    result.executionProvenance.runMode !== attemptMarker.runMode ||
    result.executionProvenance.authorizationHash !== attemptMarker.authorizationHash
  ) {
    return null;
  }
  try {
    if ((await fileSha256(expectedAttemptPath)) !== result.inferenceAttempt.markerHash) return null;
  } catch {
    return null;
  }
  if (!(await exists(predictionPath))) return null;
  const prediction = await readFile(predictionPath, "utf-8");
  if (prediction.length !== result.outputLength || sha256(prediction) !== result.cache.predictionHash) return null;
  return result;
}

export async function readValidCachedRun(resultPath: string, predictionPath: string, expected: RunCacheExpectation) {
  const result = await readCurrentCachedRun(resultPath, predictionPath, expected);
  if (!result || result.error || result.finishReason === "error") return null;
  return result;
}

async function refreshPriceReport(resultPath: string, result: any, spec: ModelSpec) {
  const pricing = priceReport(spec, result.usage);
  const rawUsage = result.rawUsage ?? result.usage?.raw ?? null;
  if (
    result.estimatedCostUsd === pricing.estimatedCostUsd &&
    result.pricing?.version === pricing.version &&
    result.pricing?.inputPerMillion === pricing.inputPerMillion &&
    result.pricing?.cachedInputPerMillion === pricing.cachedInputPerMillion &&
    result.pricing?.outputPerMillion === pricing.outputPerMillion &&
    result.rawUsage !== undefined
  ) {
    return result;
  }
  const refreshed = { ...result, estimatedCostUsd: pricing.estimatedCostUsd, pricing, rawUsage };
  await atomicWriteJson(resultPath, refreshed);
  return refreshed;
}

function sampleId(index: number) {
  return String(index).padStart(3, "0");
}

async function reserveInferenceAttempt(
  markerPath: string,
  marker: z.infer<typeof inferenceAttemptMarkerSchema>,
): Promise<{ markerPath: string; markerHash: string }> {
  try {
    await writeImmutableJson(markerPath, marker);
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "EEXIST") {
      throw new RunInfrastructureError(
        `An immutable paid-attempt marker already exists for ${marker.modelId} ${marker.caseId}#${marker.sample} ` +
          `and run key ${marker.runKey}. The harness will not issue another stochastic draw. Investigate the prior attempt marker instead.`,
        { cause: error },
      );
    }
    throw new RunInfrastructureError(
      `Cannot reserve the immutable paid-attempt marker for ${marker.modelId} ${marker.caseId}#${marker.sample}; provider call was not started.`,
      { cause: error },
    );
  }
  return { markerPath: canonicalProjectReference(markerPath), markerHash: await fileSha256(markerPath) };
}

async function runCaseSample(
  testCase: ManifestCase,
  spec: ModelSpec,
  context: RunContext,
  sample: string,
  authorization: PaidInferenceAuthorization,
) {
  const outputDir = path.join("runs", spec.id, testCase.id, "samples", sample);
  await mkdir(outputDir, { recursive: true });
  const cache = await runCacheKey(testCase, spec, context, sample);
  const expectedRun = buildRunCacheExpectation(testCase, spec, context, sample, cache);
  const resultPath = path.join(outputDir, "result.json");
  const predictionPath = path.join(outputDir, "prediction.md");
  const lock = await acquireSampleLock(path.join(outputDir, ".run.lock"));
  try {
    // The cache must be checked only after exclusive ownership: another runner
    // may have completed this exact sample while this process waited.
    const cached = await readCurrentCachedRun(resultPath, predictionPath, expectedRun);
    if (cached) {
      await refreshPriceReport(resultPath, cached, spec);
      console.log(`${spec.id} ${testCase.id}#${sample}: skip cached${cached.finishReason === "error" ? " model response failure" : ""}`);
      return { skipped: true, caseId: testCase.id };
    }

    let pdf: Buffer;
    try {
      pdf = await readFile(testCase.pdf);
    } catch (error) {
      throw new RunInfrastructureError(`Cannot read source PDF for ${spec.id} ${testCase.id}#${sample}.`, { cause: error });
    }
    if (sha256Bytes(pdf) !== cache.pdfHash) {
      throw new RunInfrastructureError(
        `Source PDF changed after preflight for ${spec.id} ${testCase.id}#${sample}; provider call was not started. Rerun preflight.`,
      );
    }

    const transportAttemptCounter: TransportAttemptCounter = { requests: 0 };
    let model: ReturnType<typeof providerModel>;
    try {
      model = providerModel(spec, transportAttemptCounter);
    } catch (error) {
      throw new RunInfrastructureError(`Cannot configure provider model ${spec.id}.`, { cause: error });
    }

    // Remove the commit marker before spending on a replacement. If the provider
    // or persistence fails, prediction.md may remain for diagnosis but the sample
    // cannot be mistaken for a current completed run.
    try {
      await rm(resultPath, { force: true });
    } catch (error) {
      throw new RunInfrastructureError(`Cannot invalidate prior result for ${spec.id} ${testCase.id}#${sample}; provider call was not started.`, {
        cause: error,
      });
    }

    const attemptMarker = inferenceAttemptMarkerSchema.parse({
      schemaVersion: 1,
      kind: "paid_inference_attempt_reserved",
      runKey: cache.runKey,
      caseId: testCase.id,
      modelId: spec.id,
      sample,
      logicalSampleDraw: 1,
      transportMaxRetries: inferenceMaxRetries,
      runMode: authorization.runMode,
      authorizationHash: authorization.authorizationHash,
      createdAt: new Date().toISOString(),
    });
    const attemptReference = await reserveInferenceAttempt(
      inferenceAttemptMarkerPath(outputDir, cache.runKey),
      attemptMarker,
    );

    const started = performance.now();
    const result = await (async () => {
      try {
        return await generateText({
          model,
          messages: [
            {
              role: "user",
              content: [
                { type: "text", text: prompt },
                { type: "file", data: pdf, mediaType: pdfMediaType, filename: `${testCase.id}.pdf` },
              ],
            },
          ],
          maxOutputTokens,
          maxRetries: inferenceMaxRetries,
          ...(spec.reasoning ? { reasoning: spec.reasoning } : {}),
        });
      } catch (error) {
        throw new RunInfrastructureError(
          `Provider invocation failed for ${spec.id} ${testCase.id}#${sample}; no scoreable model-response artifact was written.`,
          { cause: error },
        );
      }
    })();
    const elapsedMs = Math.round(performance.now() - started);
    if (transportAttemptCounter.requests < 1 || transportAttemptCounter.requests > inferenceMaxRetries + 1) {
      throw new RunInfrastructureError(
        `Provider transport-attempt telemetry was invalid for ${spec.id} ${testCase.id}#${sample}; ` +
          `recorded ${transportAttemptCounter.requests} request(s) with maxRetries=${inferenceMaxRetries}. No scoreable artifact was written.`,
      );
    }
    const predictionHash = sha256(result.text);
    const pricing = priceReport(spec, result.usage);
    const summary = {
      artifactStatus: "scoreable_model_response",
      responseReceived: true,
      caseId: testCase.id,
      title: testCase.title,
      modelId: spec.id,
      modelName: spec.modelName,
      provider: spec.provider,
      suite: context.suite,
      manifestPath: context.manifestPath,
      inputProtocol: context.inputProtocol,
      providerFileMode: context.providerFileMode,
      executionProvenance: {
        schemaVersion: 1,
        protocolVersion: context.protocol.version,
        inputMode: context.protocol.inputMode,
        inputProtocol: context.protocol.inputProtocol,
        mediaType: context.protocol.mediaType,
        providerFileMode: context.providerFileMode,
        maxOutputTokens: context.protocol.maxOutputTokens,
        maxRetries: context.protocol.maxRetries,
        transportEpoch: context.protocol.transportEpoch,
        providerPayloadMode: context.protocol.providerPayloadMode,
        samplingMode: context.protocol.samplingMode,
        logicalSampleDraw: 1,
        logicalGenerationCalls: 1,
        transportRequestAttempts: transportAttemptCounter.requests,
        retriesAreCohortSamples: false,
        runMode: authorization.runMode,
        authorizationHash: authorization.authorizationHash,
        sdkVersions: context.protocol.sdkVersions,
        promptHash: context.promptHash,
        protocolHash: context.protocolHash,
        pdfHash: cache.pdfHash,
        modelConfigHash: cache.modelConfigHash,
        inferenceFingerprint: cache.inferenceFingerprint,
        inferenceBenchmarkFingerprint: context.inferenceBenchmarkFingerprint,
      },
      providerMetadata: {
        requested: {
          provider: spec.provider,
          modelId: spec.modelName,
          reasoning: spec.reasoning ?? null,
          location: spec.location ?? null,
          baseURL: spec.baseURL ?? null,
          ...(spec.provider === "google-vertex"
            ? {
                effectiveLocation: vertexProviderRoute(spec).location,
                effectiveBaseURL: vertexProviderRoute(spec).baseURL,
              }
            : {}),
          documentedPdfIngestionMode: context.providerFileMode,
        },
        resolved: {
          provider: model.provider,
          modelId: result.response.modelId,
          responseId: result.response.id,
          responseTimestamp: result.response.timestamp,
          rawFinishReason: result.rawFinishReason ?? null,
          warnings: result.warnings ?? [],
          providerMetadata: result.providerMetadata ?? null,
        },
      },
      elapsedMs,
      finishReason: result.finishReason,
      usage: result.usage,
      rawUsage: result.usage.raw ?? null,
      estimatedCostUsd: pricing.estimatedCostUsd,
      pricing,
      outputLength: result.text.length,
      sample,
      cache: { ...cache, predictionHash },
      inferenceAttempt: {
        ...attemptReference,
        logicalSampleDraw: 1,
        logicalGenerationCalls: 1,
        transportMaxRetries: inferenceMaxRetries,
        transportRequestAttempts: transportAttemptCounter.requests,
        retriesAreCohortSamples: false,
      },
      inputMode,
    };
    const validatedSummary = currentRunArtifactSchema.safeParse(summary);
    if (!validatedSummary.success) {
      throw new RunInfrastructureError(
        `Provider returned an incomplete result envelope for ${spec.id} ${testCase.id}#${sample}; no cache commit was written. ${validatedSummary.error.message}`,
      );
    }
    try {
      // result.json is the commit marker and is intentionally renamed last. A
      // crash between the two writes leaves no valid cache hit.
      await atomicWriteText(predictionPath, result.text);
      await atomicWriteJson(resultPath, validatedSummary.data);
    } catch (error) {
      await rm(resultPath, { force: true }).catch(() => undefined);
      throw new RunInfrastructureError(
        `Failed to persist ${spec.id} ${testCase.id}#${sample}; the sample was invalidated instead of being recorded as a model zero.`,
        { cause: error },
      );
    }
    console.log(`${spec.id} ${testCase.id}#${sample}: ${summary.finishReason} ${elapsedMs}ms $${summary.estimatedCostUsd.toFixed(6)}`);
    return { skipped: false, caseId: testCase.id };
  } finally {
    await lock.release();
  }
}

export async function runModel(
  modelId: string,
  options: {
    caseId?: string;
    manifestPath?: string;
    skipPreflight?: boolean;
    finalValidationAuthorization?: string;
    sampleIds?: string[];
    repeatValidationAuthorization?: string;
  } = {},
) {
  const spec = models[modelId];
  if (!spec) throw new Error(`Unknown model ${modelId}. Options: ${Object.keys(models).join(", ")}`);
  const selectedSampleIds = options.sampleIds ?? Array.from({ length: samplesPerModelCase }, (_, index) => sampleId(index + 1));
  if (
    selectedSampleIds.length === 0 ||
    new Set(selectedSampleIds).size !== selectedSampleIds.length ||
    selectedSampleIds.some((sample) => !/^\d{3}$/.test(sample))
  ) {
    throw new Error("Selected sample ids must be a non-empty, unique list of three-digit slots.");
  }
  const isRepeatValidation = options.sampleIds !== undefined;
  if (isRepeatValidation && selectedSampleIds.includes("001")) {
    throw new Error("Repeat validation cannot target or replace the official 001 sample slot.");
  }
  if (!isRepeatValidation && options.repeatValidationAuthorization !== undefined) {
    throw new Error("Repeat-validation authorization was supplied without explicit repeat sample ids.");
  }
  const authorization = isRepeatValidation
    ? authorizeRepeatValidation(modelId, options.repeatValidationAuthorization)
    : authorizePaidInference(modelId, options.finalValidationAuthorization);
  if (!options.skipPreflight) {
    const { preflightBenchmark } = await import("./preflight.js");
    await preflightBenchmark(options.manifestPath ?? "benchmark/manifest.json");
  }

  const manifestPath = options.manifestPath ?? "benchmark/manifest.json";
  const manifest = (await loadBenchmarkManifest(manifestPath)).manifest as Manifest;
  const selected = options.caseId ? manifest.cases.filter((testCase) => testCase.id === options.caseId) : manifest.cases;
  if (selected.length === 0) throw new Error(`No selected cases. Use one of: ${manifest.cases.map((testCase) => testCase.id).join(", ")}`);

  const context = await buildRunContext(spec, manifest, manifestPath);
  console.log(
    `Running ${selected.length} case(s) x ${selectedSampleIds.length} sample(s) [${selectedSampleIds.join(", ")}] from ` +
      `${manifest.name} (${manifestPath}) with ${spec.id}, ` +
      `up to ${inferenceConcurrency} concurrent calls ` +
      `[suite=${context.suite}, protocol=${context.inputProtocol}, providerFileMode=${context.providerFileMode}]`,
  );
  const jobs = selected.flatMap((testCase) =>
    selectedSampleIds.map((selectedSampleId) => () => runCaseSample(testCase, spec, context, selectedSampleId, authorization)),
  );
  const results = await runBoundedJobs(jobs, inferenceConcurrency);
  const skipped = results.filter((result) => result.skipped).length;
  console.log(`${spec.id}: ${results.length - skipped} run, ${skipped} skipped`);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const args = parseRunCliArgs(process.argv.slice(2));
  const keepAlive = setInterval(() => undefined, 1_000);
  try {
    if (args.help) {
      console.log(runUsage);
    } else {
      await runModel(args.modelId, {
        caseId: args.caseId,
        manifestPath: args.manifestPath,
        finalValidationAuthorization: args.finalValidationAuthorization,
      });
    }
  } finally {
    clearInterval(keepAlive);
  }
}
