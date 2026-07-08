import { access, mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { performance } from "node:perf_hooks";
import { fileURLToPath } from "node:url";
import { generateText } from "ai";
import { createGoogleVertex, googleVertex } from "@ai-sdk/google-vertex";
import { openai } from "@ai-sdk/openai";
import { fileSha256, hashObject, sha256 } from "./cache.js";

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

export type ModelSpec = {
  id: string;
  modelName: string;
  provider: "google-vertex" | "openai";
  reasoning?: "none" | "minimal";
  location?: string;
  baseURL?: string;
  inputPerMillion: number;
  outputPerMillion: number;
};

export const models: Record<string, ModelSpec> = {
  "vertex-gemini-2.5-flash-lite": {
    id: "vertex-gemini-2.5-flash-lite",
    modelName: "gemini-2.5-flash-lite",
    provider: "google-vertex",
    reasoning: "minimal",
    location: "global",
    baseURL: "https://aiplatform.googleapis.com/v1/projects/803270566601/locations/global/publishers/google",
    inputPerMillion: 0.1,
    outputPerMillion: 0.4,
  },
  "vertex-gemini-3.1-flash-lite": {
    id: "vertex-gemini-3.1-flash-lite",
    modelName: "gemini-3.1-flash-lite",
    provider: "google-vertex",
    reasoning: "minimal",
    inputPerMillion: 0.25,
    outputPerMillion: 1.5,
  },
  "vertex-gemini-3-flash-preview": {
    id: "vertex-gemini-3-flash-preview",
    modelName: "gemini-3-flash-preview",
    provider: "google-vertex",
    reasoning: "minimal",
    inputPerMillion: 0.5,
    outputPerMillion: 3,
  },
  "openai-gpt-5-nano": {
    id: "openai-gpt-5-nano",
    modelName: "gpt-5-nano",
    provider: "openai",
    reasoning: "minimal",
    inputPerMillion: 0.05,
    outputPerMillion: 0.4,
  },
  "openai-gpt-5.4-nano": {
    id: "openai-gpt-5.4-nano",
    modelName: "gpt-5.4-nano",
    provider: "openai",
    reasoning: "none",
    inputPerMillion: 0.2,
    outputPerMillion: 1.25,
  },
  "openai-gpt-5.5": {
    id: "openai-gpt-5.5",
    modelName: "gpt-5.5",
    provider: "openai",
    reasoning: "none",
    inputPerMillion: 5,
    outputPerMillion: 30,
  },
  "vertex-gemini-3.5-flash": {
    id: "vertex-gemini-3.5-flash",
    modelName: "gemini-3.5-flash",
    provider: "google-vertex",
    reasoning: "minimal",
    inputPerMillion: 0.3,
    outputPerMillion: 2.5,
  },
};

export const benchmarkModelIds = ["openai-gpt-5-nano", "vertex-gemini-3.1-flash-lite"] as const;

export const samplesPerModelCase = 3;
const maxOutputTokens = 24000;
const inputMode = "native_pdf";

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

function providerModel(spec: ModelSpec) {
  if (spec.provider === "google-vertex") {
    if (spec.location || spec.baseURL) {
      return createGoogleVertex({ location: spec.location, baseURL: spec.baseURL })(spec.modelName);
    }
    return googleVertex(spec.modelName);
  }
  return openai(spec.modelName);
}

function cost(spec: ModelSpec, usage: any): number {
  const input = usage?.inputTokens ?? 0;
  const output = usage?.outputTokens ?? 0;
  return (input / 1_000_000) * spec.inputPerMillion + (output / 1_000_000) * spec.outputPerMillion;
}

function parseArgs() {
  const args = new Map<string, string>();
  for (let i = 2; i < process.argv.length; i += 1) {
    const arg = process.argv[i];
    if (arg.startsWith("--")) {
      const key = arg.slice(2);
      const next = process.argv[i + 1];
      args.set(key, next && !next.startsWith("--") ? process.argv[++i] : "true");
    }
  }
  return args;
}

function rejectUnknownArgs(args: Map<string, string>, allowed: string[]) {
  const allowedSet = new Set(allowed);
  const unknown = [...args.keys()].filter((key) => !allowedSet.has(key));
  if (unknown.length > 0) throw new Error(`Unknown argument(s): ${unknown.map((key) => `--${key}`).join(", ")}`);
}

async function exists(filePath: string) {
  try {
    await access(filePath);
    return true;
  } catch {
    return false;
  }
}

type RunContext = {
  suite: string;
  manifestPath: string;
  inputProtocol: string;
  providerFileMode: string;
};

async function providerFileMode(spec: ModelSpec) {
  try {
    const capabilities = JSON.parse(await readFile("benchmark/provider-capabilities.json", "utf-8")) as {
      providers?: Record<string, { documents?: Record<string, { ingestionMode?: string }> }>;
    };
    return capabilities.providers?.[spec.provider]?.documents?.pdf?.ingestionMode ?? "unknown";
  } catch {
    return "unknown";
  }
}

export async function buildRunContext(spec: ModelSpec, manifest: Manifest, manifestPath: string): Promise<RunContext> {
  return {
    suite: manifest.suite ?? "official",
    manifestPath,
    inputProtocol: manifest.inputProtocol ?? inputMode,
    providerFileMode: await providerFileMode(spec),
  };
}

export async function runCacheKey(testCase: ManifestCase, spec: ModelSpec, context: RunContext) {
  const pdfHash = await fileSha256(testCase.pdf);
  const promptHash = sha256(prompt);
  const modelConfigHash = hashObject({
    id: spec.id,
    modelName: spec.modelName,
    provider: spec.provider,
    reasoning: spec.reasoning ?? null,
    location: spec.location ?? null,
    baseURL: spec.baseURL ?? null,
    maxOutputTokens,
    inputMode,
    suite: context.suite,
    manifestPath: context.manifestPath,
    inputProtocol: context.inputProtocol,
    providerFileMode: context.providerFileMode,
  });
  return {
    runKey: hashObject({ caseId: testCase.id, pdfHash, promptHash, modelConfigHash }),
    pdfHash,
    promptHash,
    modelConfigHash,
  };
}

async function readJsonIfExists(filePath: string) {
  if (!(await exists(filePath))) return null;
  return JSON.parse(await readFile(filePath, "utf-8")) as any;
}

async function currentSuccessfulRunExists(resultPath: string, runKey: string) {
  const result = await readJsonIfExists(resultPath);
  return Boolean(result?.cache?.runKey === runKey && !result.error && result.finishReason !== "error");
}

function sampleId(index: number) {
  return String(index).padStart(3, "0");
}

async function runCaseSample(testCase: ManifestCase, spec: ModelSpec, context: RunContext, sample: string, options: { force?: boolean } = {}) {
  const outputDir = path.join("runs", spec.id, testCase.id, "samples", sample);
  await mkdir(outputDir, { recursive: true });
  const cache = await runCacheKey(testCase, spec, context);
  const resultPath = path.join(outputDir, "result.json");
  const predictionPath = path.join(outputDir, "prediction.md");
  if (!options.force && (await currentSuccessfulRunExists(resultPath, cache.runKey))) {
    console.log(`${spec.id} ${testCase.id}#${sample}: skip cached`);
    return { skipped: true, caseId: testCase.id };
  }

  const pdf = await readFile(testCase.pdf);
  const started = performance.now();
  try {
    const result = await generateText({
      model: providerModel(spec),
      messages: [
        {
          role: "user",
          content: [
            { type: "text", text: prompt },
            { type: "file", data: pdf, mediaType: "application/pdf", filename: `${testCase.id}.pdf` },
          ],
        },
      ],
      maxOutputTokens,
      ...(spec.reasoning ? { reasoning: spec.reasoning } : {}),
    });
    const elapsedMs = Math.round(performance.now() - started);
    const summary = {
      caseId: testCase.id,
      title: testCase.title,
      modelId: spec.id,
      modelName: spec.modelName,
      provider: spec.provider,
      suite: context.suite,
      manifestPath: context.manifestPath,
      inputProtocol: context.inputProtocol,
      providerFileMode: context.providerFileMode,
      elapsedMs,
      finishReason: result.finishReason,
      usage: result.usage,
      estimatedCostUsd: cost(spec, result.usage),
      outputLength: result.text.length,
      sample,
      cache,
      inputMode,
    };
    await writeFile(predictionPath, result.text, "utf-8");
    await writeFile(resultPath, JSON.stringify(summary, null, 2) + "\n", "utf-8");
    console.log(`${spec.id} ${testCase.id}#${sample}: ${summary.finishReason} ${elapsedMs}ms $${summary.estimatedCostUsd.toFixed(6)}`);
    return { skipped: false, caseId: testCase.id };
  } catch (error) {
    const elapsedMs = Math.round(performance.now() - started);
    const summary = {
      caseId: testCase.id,
      title: testCase.title,
      modelId: spec.id,
      modelName: spec.modelName,
      provider: spec.provider,
      suite: context.suite,
      manifestPath: context.manifestPath,
      inputProtocol: context.inputProtocol,
      providerFileMode: context.providerFileMode,
      elapsedMs,
      finishReason: "error",
      usage: null,
      estimatedCostUsd: 0,
      outputLength: 0,
      sample,
      error: error instanceof Error ? error.message : String(error),
      cache,
      inputMode,
    };
    await writeFile(predictionPath, "", "utf-8");
    await writeFile(resultPath, JSON.stringify(summary, null, 2) + "\n", "utf-8");
    console.error(`${spec.id} ${testCase.id}#${sample}: ERROR ${summary.error}`);
    return { skipped: false, caseId: testCase.id };
  }
}

export async function runModel(modelId: string, options: { caseId?: string; force?: boolean; manifestPath?: string } = {}) {
  const spec = models[modelId];
  if (!spec) throw new Error(`Unknown model ${modelId}. Options: ${Object.keys(models).join(", ")}`);

  const manifestPath = options.manifestPath ?? "benchmark/manifest.json";
  const manifest = JSON.parse(await readFile(manifestPath, "utf-8")) as Manifest;
  const selected = options.caseId ? manifest.cases.filter((testCase) => testCase.id === options.caseId) : manifest.cases;
  if (selected.length === 0) throw new Error(`No selected cases. Use one of: ${manifest.cases.map((testCase) => testCase.id).join(", ")}`);

  const context = await buildRunContext(spec, manifest, manifestPath);
  console.log(
    `Running ${selected.length} case(s) x ${samplesPerModelCase} sample(s) from ${manifest.name} (${manifestPath}) with ${spec.id} in parallel ` +
      `[suite=${context.suite}, protocol=${context.inputProtocol}, providerFileMode=${context.providerFileMode}]`,
  );
  const jobs = selected.flatMap((testCase) =>
    Array.from({ length: samplesPerModelCase }, (_, index) => runCaseSample(testCase, spec, context, sampleId(index + 1), { force: options.force })),
  );
  const results = await Promise.all(jobs);
  const skipped = results.filter((result) => result.skipped).length;
  console.log(`${spec.id}: ${results.length - skipped} run, ${skipped} skipped`);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const args = parseArgs();
  rejectUnknownArgs(args, ["model", "case", "force", "manifest"]);
  await runModel(args.get("model") ?? "vertex-gemini-3.1-flash-lite", {
    caseId: args.get("case"),
    force: args.has("force"),
    manifestPath: args.get("manifest"),
  });
}
