import { createGoogleVertex } from "@ai-sdk/google-vertex";
import { createOpenAI } from "@ai-sdk/openai";

export type ModelSpec = {
  id: string;
  modelName: string;
  provider: "google-vertex" | "openai";
  reasoning?: "none" | "minimal" | "low" | "medium";
  location?: string;
  maxOutputTokens?: number;
  pricingVersion: string;
  inputPerMillion: number;
  cachedInputPerMillion: number;
  cacheWritePerMillion?: number;
  outputPerMillion: number;
};

export const models: Record<string, ModelSpec> = {
  "openai-gpt-4o-mini": {
    id: "openai-gpt-4o-mini",
    modelName: "gpt-4o-mini",
    provider: "openai",
    maxOutputTokens: 16_384,
    pricingVersion: "2026-07-11",
    inputPerMillion: 0.15,
    cachedInputPerMillion: 0.075,
    outputPerMillion: 0.6,
  },
  "openai-gpt-5-nano": {
    id: "openai-gpt-5-nano",
    modelName: "gpt-5-nano",
    provider: "openai",
    reasoning: "minimal",
    pricingVersion: "2026-07-11",
    inputPerMillion: 0.05,
    cachedInputPerMillion: 0.005,
    outputPerMillion: 0.4,
  },
  "vertex-gemini-3.1-flash-lite": {
    id: "vertex-gemini-3.1-flash-lite",
    modelName: "gemini-3.1-flash-lite",
    provider: "google-vertex",
    reasoning: "minimal",
    pricingVersion: "2026-07-11",
    inputPerMillion: 0.45,
    cachedInputPerMillion: 0.045,
    outputPerMillion: 2.7,
  },
  "vertex-gemini-3.1-flash-lite-low": {
    id: "vertex-gemini-3.1-flash-lite-low",
    modelName: "gemini-3.1-flash-lite",
    provider: "google-vertex",
    reasoning: "low",
    pricingVersion: "2026-07-12",
    inputPerMillion: 0.45,
    cachedInputPerMillion: 0.045,
    outputPerMillion: 2.7,
  },
  "vertex-gemini-3.1-flash-lite-medium": {
    id: "vertex-gemini-3.1-flash-lite-medium",
    modelName: "gemini-3.1-flash-lite",
    provider: "google-vertex",
    reasoning: "medium",
    pricingVersion: "2026-07-14",
    inputPerMillion: 0.45,
    cachedInputPerMillion: 0.045,
    outputPerMillion: 2.7,
  },
  "vertex-gemini-2.5-flash-lite": {
    id: "vertex-gemini-2.5-flash-lite",
    modelName: "gemini-2.5-flash-lite",
    provider: "google-vertex",
    reasoning: "minimal",
    location: "global",
    pricingVersion: "2026-07-11",
    inputPerMillion: 0.1,
    cachedInputPerMillion: 0.01,
    outputPerMillion: 0.4,
  },
  "openai-gpt-5.4-nano": {
    id: "openai-gpt-5.4-nano",
    modelName: "gpt-5.4-nano",
    provider: "openai",
    reasoning: "none",
    pricingVersion: "2026-07-11",
    inputPerMillion: 0.2,
    cachedInputPerMillion: 0.02,
    outputPerMillion: 1.25,
  },
  "openai-gpt-5.4-nano-low": {
    id: "openai-gpt-5.4-nano-low",
    modelName: "gpt-5.4-nano",
    provider: "openai",
    reasoning: "low",
    pricingVersion: "2026-07-12",
    inputPerMillion: 0.2,
    cachedInputPerMillion: 0.02,
    outputPerMillion: 1.25,
  },
  "openai-gpt-5.4-nano-medium": {
    id: "openai-gpt-5.4-nano-medium",
    modelName: "gpt-5.4-nano",
    provider: "openai",
    reasoning: "medium",
    pricingVersion: "2026-07-14",
    inputPerMillion: 0.2,
    cachedInputPerMillion: 0.02,
    outputPerMillion: 1.25,
  },
  "openai-gpt-5.4-mini": {
    id: "openai-gpt-5.4-mini",
    modelName: "gpt-5.4-mini",
    provider: "openai",
    reasoning: "none",
    pricingVersion: "2026-07-11",
    inputPerMillion: 0.75,
    cachedInputPerMillion: 0.075,
    outputPerMillion: 4.5,
  },
  "vertex-gemini-3-flash-preview": {
    id: "vertex-gemini-3-flash-preview",
    modelName: "gemini-3-flash-preview",
    provider: "google-vertex",
    reasoning: "minimal",
    location: "global",
    pricingVersion: "2026-07-11",
    inputPerMillion: 0.9,
    cachedInputPerMillion: 0.09,
    outputPerMillion: 5.4,
  },
  "vertex-gemini-3.1-pro": {
    id: "vertex-gemini-3.1-pro",
    modelName: "gemini-3.1-pro-preview",
    provider: "google-vertex",
    reasoning: "minimal",
    pricingVersion: "2026-07-11",
    inputPerMillion: 2,
    cachedInputPerMillion: 0.2,
    outputPerMillion: 12,
  },
  "vertex-gemini-3.5-flash": {
    id: "vertex-gemini-3.5-flash",
    modelName: "gemini-3.5-flash",
    provider: "google-vertex",
    reasoning: "minimal",
    pricingVersion: "2026-07-11",
    inputPerMillion: 2.7,
    cachedInputPerMillion: 0.27,
    outputPerMillion: 16.2,
  },
  "openai-gpt-5.6-luna": {
    id: "openai-gpt-5.6-luna",
    modelName: "gpt-5.6-luna",
    provider: "openai",
    reasoning: "none",
    pricingVersion: "2026-07-11",
    inputPerMillion: 1,
    cachedInputPerMillion: 0.1,
    cacheWritePerMillion: 1.25,
    outputPerMillion: 6,
  },
  "openai-gpt-5.6-luna-low": {
    id: "openai-gpt-5.6-luna-low",
    modelName: "gpt-5.6-luna",
    provider: "openai",
    reasoning: "low",
    pricingVersion: "2026-07-12",
    inputPerMillion: 1,
    cachedInputPerMillion: 0.1,
    cacheWritePerMillion: 1.25,
    outputPerMillion: 6,
  },
  "openai-gpt-5.6-luna-medium": {
    id: "openai-gpt-5.6-luna-medium",
    modelName: "gpt-5.6-luna",
    provider: "openai",
    reasoning: "medium",
    pricingVersion: "2026-07-14",
    inputPerMillion: 1,
    cachedInputPerMillion: 0.1,
    cacheWritePerMillion: 1.25,
    outputPerMillion: 6,
  },
  "openai-gpt-5.6-terra": {
    id: "openai-gpt-5.6-terra",
    modelName: "gpt-5.6-terra",
    provider: "openai",
    reasoning: "none",
    pricingVersion: "2026-07-11",
    inputPerMillion: 2.5,
    cachedInputPerMillion: 0.25,
    cacheWritePerMillion: 3.125,
    outputPerMillion: 15,
  },
  "openai-gpt-5.6-sol": {
    id: "openai-gpt-5.6-sol",
    modelName: "gpt-5.6-sol",
    provider: "openai",
    reasoning: "none",
    pricingVersion: "2026-07-11",
    inputPerMillion: 5,
    cachedInputPerMillion: 0.5,
    cacheWritePerMillion: 6.25,
    outputPerMillion: 30,
  },
  "openai-gpt-5.5": {
    id: "openai-gpt-5.5",
    modelName: "gpt-5.5",
    provider: "openai",
    reasoning: "none",
    pricingVersion: "2026-07-11",
    inputPerMillion: 5,
    cachedInputPerMillion: 0.5,
    outputPerMillion: 30,
  },
};

export const defaultModelIds = ["openai-gpt-5-nano", "vertex-gemini-3.1-flash-lite"];

export function createModel(spec: ModelSpec) {
  if (spec.provider === "openai") return createOpenAI()(spec.modelName);

  const location = spec.location ?? process.env.GOOGLE_VERTEX_LOCATION;
  let baseURL: string | undefined;
  if (process.env.GOOGLE_VERTEX_API_KEY && spec.location) {
    const project = process.env.GOOGLE_VERTEX_PROJECT;
    if (!project) throw new Error(`${spec.id} requires GOOGLE_VERTEX_PROJECT for location ${spec.location}.`);
    const host = spec.location === "global" ? "aiplatform.googleapis.com" : `${spec.location}-aiplatform.googleapis.com`;
    baseURL = `https://${host}/v1/projects/${encodeURIComponent(project)}/locations/${spec.location}/publishers/google`;
  }
  return createGoogleVertex({ location, baseURL })(spec.modelName);
}
