import { access, mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { performance } from "node:perf_hooks";
import { fileURLToPath } from "node:url";
import { generateText } from "ai";
import { googleVertex } from "@ai-sdk/google-vertex";
import { openai } from "@ai-sdk/openai";
import { fileSha256, hashObject, sha256 } from "./cache.js";

type ManifestCase = {
  id: string;
  title: string;
  family: string;
  pdf: string;
};

type Manifest = {
  name: string;
  cases: ManifestCase[];
};

type ModelSpec = {
  id: string;
  modelName: string;
  provider: "google-vertex" | "openai";
  reasoning?: "none" | "minimal";
  inputPerMillion: number;
  outputPerMillion: number;
};

export const models: Record<string, ModelSpec> = {
  "vertex-gemini-3.1-flash-lite": {
    id: "vertex-gemini-3.1-flash-lite",
    modelName: "gemini-3.1-flash-lite",
    provider: "google-vertex",
    reasoning: "minimal",
    inputPerMillion: 0.25,
    outputPerMillion: 1.5,
  },
  "vertex-gemini-3.5-flash": {
    id: "vertex-gemini-3.5-flash",
    modelName: "gemini-3.5-flash",
    provider: "google-vertex",
    reasoning: "minimal",
    inputPerMillion: 1.5,
    outputPerMillion: 9,
  },
  "openai-gpt-5.4-nano": {
    id: "openai-gpt-5.4-nano",
    modelName: "gpt-5.4-nano",
    provider: "openai",
    reasoning: "none",
    inputPerMillion: 0.2,
    outputPerMillion: 1.25,
  },
  "openai-gpt-5-nano": {
    id: "openai-gpt-5-nano",
    modelName: "gpt-5-nano",
    provider: "openai",
    reasoning: "minimal",
    inputPerMillion: 0.05,
    outputPerMillion: 0.4,
  },
};

const maxOutputTokens = 12000;

export const prompt = `Convert the attached PDF into one faithful Markdown document.

Rules:
- Return only Markdown.
- Preserve visible text in reading order.
- Preserve headings, lists, tables, forms, captions, code, checkbox states, stamps, handwritten notes, and footnotes where possible.
- For charts, diagrams, schedules, raster tables, cards, and other non-text visual content, insert concise natural-language descriptions or Markdown tables inline at the original location.
- Rendered visible content wins over hidden, stale, covered, or invisible PDF text.
- Do not summarize, cite sources, add commentary, emit JSON, or wrap the Markdown.`;

function providerModel(spec: ModelSpec) {
  if (spec.provider === "google-vertex") return googleVertex(spec.modelName);
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

async function exists(filePath: string) {
  try {
    await access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function runCacheKey(testCase: ManifestCase, spec: ModelSpec) {
  const pdfHash = await fileSha256(testCase.pdf);
  const promptHash = sha256(prompt);
  const modelConfigHash = hashObject({
    id: spec.id,
    modelName: spec.modelName,
    provider: spec.provider,
    reasoning: spec.reasoning ?? null,
    maxOutputTokens,
  });
  return {
    runKey: hashObject({ caseId: testCase.id, pdfHash, promptHash, modelConfigHash }),
    pdfHash,
    promptHash,
    modelConfigHash,
  };
}

async function runCase(testCase: ManifestCase, spec: ModelSpec, options: { force?: boolean } = {}) {
  const outputDir = path.join("runs", spec.id, testCase.id);
  await mkdir(outputDir, { recursive: true });
  const resultPath = path.join(outputDir, "result.json");
  const predictionPath = path.join(outputDir, "prediction.md");
  const cache = await runCacheKey(testCase, spec);
  if (!options.force && (await exists(resultPath)) && (await exists(predictionPath))) {
    const previous = JSON.parse(await readFile(resultPath, "utf-8")) as { cache?: { runKey?: string }; error?: string; finishReason?: string };
    if (previous.cache?.runKey === cache.runKey && !previous.error && previous.finishReason !== "error") {
      console.log(`${spec.id} ${testCase.id}: skip unchanged`);
      return { skipped: true, caseId: testCase.id };
    }
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
      elapsedMs,
      finishReason: result.finishReason,
      usage: result.usage,
      estimatedCostUsd: cost(spec, result.usage),
      outputLength: result.text.length,
      cache,
    };
    await writeFile(predictionPath, result.text, "utf-8");
    await writeFile(resultPath, JSON.stringify(summary, null, 2) + "\n", "utf-8");
    console.log(`${spec.id} ${testCase.id}: ${summary.finishReason} ${elapsedMs}ms $${summary.estimatedCostUsd.toFixed(6)}`);
    return { skipped: false, caseId: testCase.id };
  } catch (error) {
    const elapsedMs = Math.round(performance.now() - started);
    const summary = {
      caseId: testCase.id,
      title: testCase.title,
      modelId: spec.id,
      modelName: spec.modelName,
      provider: spec.provider,
      elapsedMs,
      finishReason: "error",
      usage: null,
      estimatedCostUsd: 0,
      outputLength: 0,
      error: error instanceof Error ? error.message : String(error),
      cache,
    };
    await writeFile(predictionPath, "", "utf-8");
    await writeFile(resultPath, JSON.stringify(summary, null, 2) + "\n", "utf-8");
    console.error(`${spec.id} ${testCase.id}: ERROR ${summary.error}`);
    return { skipped: false, caseId: testCase.id };
  }
}

async function runWithConcurrency<T, R>(items: T[], concurrency: number, worker: (item: T) => Promise<R>) {
  const limit = Math.max(1, Math.min(concurrency, items.length));
  let next = 0;
  const results: R[] = [];
  const workers = Array.from({ length: limit }, async () => {
    while (next < items.length) {
      const item = items[next++];
      results.push(await worker(item));
    }
  });
  await Promise.all(workers);
  return results;
}

export async function runModel(modelId: string, options: { caseId?: string; concurrency?: number; force?: boolean } = {}) {
  const spec = models[modelId];
  if (!spec) throw new Error(`Unknown model ${modelId}. Options: ${Object.keys(models).join(", ")}`);

  const manifest = JSON.parse(await readFile("benchmark/manifest.json", "utf-8")) as Manifest;
  const selected = options.caseId ? manifest.cases.filter((testCase) => testCase.id === options.caseId) : manifest.cases;
  if (selected.length === 0) throw new Error(`No selected cases. Use one of: ${manifest.cases.map((testCase) => testCase.id).join(", ")}`);
  const concurrency = options.concurrency ?? 3;
  if (!Number.isFinite(concurrency) || concurrency < 1) throw new Error(`Invalid --concurrency ${concurrency}`);

  console.log(`Running ${selected.length} case(s) from ${manifest.name} with ${spec.id} at concurrency ${Math.min(concurrency, selected.length)}`);
  const results = await runWithConcurrency(selected, concurrency, (testCase) => runCase(testCase, spec, { force: options.force }));
  const skipped = results.filter((result) => result.skipped).length;
  console.log(`${spec.id}: ${selected.length - skipped} run, ${skipped} skipped`);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const args = parseArgs();
  await runModel(args.get("model") ?? "vertex-gemini-3.1-flash-lite", {
    caseId: args.get("case"),
    concurrency: Number(args.get("concurrency") ?? "3"),
    force: args.has("force"),
  });
}
