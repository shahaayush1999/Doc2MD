import { createGoogleVertex } from "@ai-sdk/google-vertex";
import { createOpenAI } from "@ai-sdk/openai";

export type ModelSpec = {
  id: string;
  modelName: string;
  provider: "google-vertex" | "openai";
  reasoning?: "none" | "minimal";
  location?: string;
  inputPerMillion: number;
  cachedInputPerMillion: number;
  outputPerMillion: number;
};

export const models: Record<string, ModelSpec> = {
  "openai-gpt-5-nano": {
    id: "openai-gpt-5-nano",
    modelName: "gpt-5-nano",
    provider: "openai",
    reasoning: "minimal",
    inputPerMillion: 0.05,
    cachedInputPerMillion: 0.005,
    outputPerMillion: 0.4,
  },
  "vertex-gemini-3.1-flash-lite": {
    id: "vertex-gemini-3.1-flash-lite",
    modelName: "gemini-3.1-flash-lite",
    provider: "google-vertex",
    reasoning: "minimal",
    inputPerMillion: 0.25,
    cachedInputPerMillion: 0.025,
    outputPerMillion: 1.5,
  },
  "vertex-gemini-2.5-flash-lite": {
    id: "vertex-gemini-2.5-flash-lite",
    modelName: "gemini-2.5-flash-lite",
    provider: "google-vertex",
    reasoning: "minimal",
    location: "global",
    inputPerMillion: 0.1,
    cachedInputPerMillion: 0.01,
    outputPerMillion: 0.4,
  },
  "openai-gpt-5.4-nano": {
    id: "openai-gpt-5.4-nano",
    modelName: "gpt-5.4-nano",
    provider: "openai",
    reasoning: "none",
    inputPerMillion: 0.2,
    cachedInputPerMillion: 0.02,
    outputPerMillion: 1.25,
  },
  "openai-gpt-5.4-mini": {
    id: "openai-gpt-5.4-mini",
    modelName: "gpt-5.4-mini",
    provider: "openai",
    reasoning: "none",
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
    inputPerMillion: 0.5,
    cachedInputPerMillion: 0.05,
    outputPerMillion: 3,
  },
  "vertex-gemini-3.1-pro": {
    id: "vertex-gemini-3.1-pro",
    modelName: "gemini-3.1-pro-preview",
    provider: "google-vertex",
    reasoning: "minimal",
    inputPerMillion: 2,
    cachedInputPerMillion: 0.2,
    outputPerMillion: 12,
  },
  "vertex-gemini-3.5-flash": {
    id: "vertex-gemini-3.5-flash",
    modelName: "gemini-3.5-flash",
    provider: "google-vertex",
    reasoning: "minimal",
    inputPerMillion: 1.5,
    cachedInputPerMillion: 0.15,
    outputPerMillion: 9,
  },
  "openai-gpt-5.5": {
    id: "openai-gpt-5.5",
    modelName: "gpt-5.5",
    provider: "openai",
    reasoning: "none",
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

export const conversionPrompt = `Convert the attached PDF into one faithful Markdown document for downstream machine use.

Return only Markdown. Do not add commentary, citations, JSON, code fences, or an executive summary.

Reconstruct the document exhaustively:
- Process every page and every visible region in source order.
- Preserve all readable text, headings, section hierarchy, lists, captions, footnotes, stamps, annotations, signatures, page-level notes, and document-state notes.
- Preserve every table row, column, header, unit, label, value, subtotal, continuation, blank/NA state, and row/column relationship.
- Preserve checkbox/radio states, strikeouts, insertions, corrections, voided values, and final/current values.
- Describe charts, diagrams, maps, floorplans, screenshots, photos, timelines, heatmaps, chromatograms, and other visual content inline where it appears. Include labels, legends, axes, units, thresholds, colors, symbols, arrows, spatial relationships, and printed values.
- Never invent precision for values that are only visually inferable.
- Rendered visible current content wins over hidden, stale, covered, deleted, or superseded PDF text. Preserve visibly historical content only when it is part of the reading experience and label its state clearly.
- If a broken export has legitimate selectable PDF text needed to recover the document, use it while preserving visible reading order.

The goal is faithful reconstruction of the original document's information and reading experience, not summarization or interpretation.`;
