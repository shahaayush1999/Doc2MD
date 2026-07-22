import { createAnthropic } from "@ai-sdk/anthropic";
import { createGoogleGenerativeAI } from "@ai-sdk/google";
import { createOpenAI } from "@ai-sdk/openai";
import { setTimeout as delay } from "node:timers/promises";

export type ModelSpec = {
  id: string;
  modelName: string;
  provider: "anthropic" | "google" | "openai";
  reasoning?: "none" | "minimal";
  location?: string;
  maxOutputTokens?: number;
  pricingVersion: string;
  inputPerMillion: number;
  cachedInputPerMillion: number;
  cacheWritePerMillion?: number;
  outputPerMillion: number;
};

export const models: Record<string, ModelSpec> = {
  "anthropic-claude-haiku-4.5": {
    id: "anthropic-claude-haiku-4.5",
    modelName: "claude-haiku-4-5-20251001",
    provider: "anthropic",
    reasoning: "none",
    pricingVersion: "2026-07-20",
    inputPerMillion: 1,
    cachedInputPerMillion: 0.1,
    outputPerMillion: 5,
  },
  "anthropic-claude-sonnet-5": {
    id: "anthropic-claude-sonnet-5",
    modelName: "claude-sonnet-5",
    provider: "anthropic",
    reasoning: "none",
    pricingVersion: "2026-07-20-introductory",
    inputPerMillion: 2,
    cachedInputPerMillion: 0.2,
    outputPerMillion: 10,
  },
  "anthropic-claude-opus-4.8": {
    id: "anthropic-claude-opus-4.8",
    modelName: "claude-opus-4-8",
    provider: "anthropic",
    reasoning: "none",
    pricingVersion: "2026-07-20",
    inputPerMillion: 5,
    cachedInputPerMillion: 0.5,
    outputPerMillion: 25,
  },
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
  "google-gemini-3.1-flash-lite": {
    id: "google-gemini-3.1-flash-lite",
    modelName: "gemini-3.1-flash-lite",
    provider: "google",
    reasoning: "minimal",
    pricingVersion: "2026-07-20",
    inputPerMillion: 0.25,
    cachedInputPerMillion: 0.025,
    outputPerMillion: 1.5,
  },
  "google-gemini-3.5-flash-lite": {
    id: "google-gemini-3.5-flash-lite",
    modelName: "gemini-3.5-flash-lite",
    provider: "google",
    reasoning: "minimal",
    pricingVersion: "2026-07-21",
    inputPerMillion: 0.3,
    cachedInputPerMillion: 0.03,
    outputPerMillion: 2.5,
  },
  "google-gemini-2.5-flash-lite": {
    id: "google-gemini-2.5-flash-lite",
    modelName: "gemini-2.5-flash-lite",
    provider: "google",
    reasoning: "minimal",
    pricingVersion: "2026-07-20",
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
  "google-gemini-3-flash-preview": {
    id: "google-gemini-3-flash-preview",
    modelName: "gemini-3-flash-preview",
    provider: "google",
    reasoning: "minimal",
    pricingVersion: "2026-07-20",
    inputPerMillion: 0.5,
    cachedInputPerMillion: 0.05,
    outputPerMillion: 3,
  },
  "google-gemini-3.1-pro": {
    id: "google-gemini-3.1-pro",
    modelName: "gemini-3.1-pro-preview",
    provider: "google",
    reasoning: "minimal",
    pricingVersion: "2026-07-20",
    inputPerMillion: 2,
    cachedInputPerMillion: 0.2,
    outputPerMillion: 12,
  },
  "google-gemini-3.5-flash": {
    id: "google-gemini-3.5-flash",
    modelName: "gemini-3.5-flash",
    provider: "google",
    reasoning: "minimal",
    pricingVersion: "2026-07-20",
    inputPerMillion: 1.5,
    cachedInputPerMillion: 0.15,
    outputPerMillion: 9,
  },
  "google-gemini-3.6-flash": {
    id: "google-gemini-3.6-flash",
    modelName: "gemini-3.6-flash",
    provider: "google",
    reasoning: "minimal",
    pricingVersion: "2026-07-21",
    inputPerMillion: 1.5,
    cachedInputPerMillion: 0.15,
    outputPerMillion: 7.5,
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

export const defaultModelIds = ["openai-gpt-5-nano", "google-gemini-3.1-flash-lite"];

// The strictest Google candidate model in this benchmark allows 5 RPM on the
// personal AI Studio free tier. Pace the underlying fetches—not just cases—so
// automatic SDK retries cannot accidentally exceed that quota.
const googleCandidateStartIntervalMs = 15_000;
let nextGoogleCandidateStartAt = 0;
let googleCandidatePacingTail: Promise<void> = Promise.resolve();

async function waitForGoogleCandidateStart() {
  const previous = googleCandidatePacingTail;
  let release!: () => void;
  googleCandidatePacingTail = new Promise<void>((resolve) => {
    release = resolve;
  });
  await previous;
  try {
    const waitMs = Math.max(0, nextGoogleCandidateStartAt - Date.now());
    if (waitMs > 0) await delay(waitMs);
    nextGoogleCandidateStartAt = Date.now() + googleCandidateStartIntervalMs;
  } finally {
    release();
  }
}

async function pacedGoogleCandidateFetch(input: RequestInfo | URL, init?: RequestInit) {
  await waitForGoogleCandidateStart();
  return fetch(input, init);
}

export function createModel(spec: ModelSpec) {
  if (spec.provider === "anthropic") return createAnthropic({ apiKey: process.env.ANTHROPIC_API_KEY })(spec.modelName);
  if (spec.provider === "openai") return createOpenAI()(spec.modelName);
  return createGoogleGenerativeAI({
    apiKey: process.env.GEMINI_API_KEY,
    fetch: pacedGoogleCandidateFetch,
  })(spec.modelName);
}
