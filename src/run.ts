import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { performance } from "node:perf_hooks";
import { generateText } from "ai";
import { googleVertex } from "@ai-sdk/google-vertex";
import { openai } from "@ai-sdk/openai";

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

const models: Record<string, ModelSpec> = {
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
  "openai-gpt-4o-mini": {
    id: "openai-gpt-4o-mini",
    modelName: "gpt-4o-mini",
    provider: "openai",
    inputPerMillion: 0.15,
    outputPerMillion: 0.6,
  },
};

const prompt = `Convert the attached PDF into one faithful Markdown document.

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

async function runCase(testCase: ManifestCase, spec: ModelSpec) {
  const outputDir = path.join("runs", spec.id, testCase.id);
  await mkdir(outputDir, { recursive: true });
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
      maxOutputTokens: 12000,
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
    };
    await writeFile(path.join(outputDir, "prediction.md"), result.text, "utf-8");
    await writeFile(path.join(outputDir, "result.json"), JSON.stringify(summary, null, 2) + "\n", "utf-8");
    console.log(`${spec.id} ${testCase.id}: ${summary.finishReason} ${elapsedMs}ms $${summary.estimatedCostUsd.toFixed(6)}`);
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
    };
    await writeFile(path.join(outputDir, "prediction.md"), "", "utf-8");
    await writeFile(path.join(outputDir, "result.json"), JSON.stringify(summary, null, 2) + "\n", "utf-8");
    console.error(`${spec.id} ${testCase.id}: ERROR ${summary.error}`);
  }
}

const args = parseArgs();
const modelId = args.get("model") ?? "vertex-gemini-3.1-flash-lite";
const spec = models[modelId];
if (!spec) throw new Error(`Unknown model ${modelId}. Options: ${Object.keys(models).join(", ")}`);

const manifest = JSON.parse(await readFile("benchmark/manifest.json", "utf-8")) as Manifest;
const caseArg = args.get("case");
const selected = caseArg ? manifest.cases.filter((testCase) => testCase.id === caseArg) : manifest.cases;
if (selected.length === 0) throw new Error(`No selected cases. Use one of: ${manifest.cases.map((testCase) => testCase.id).join(", ")}`);

console.log(`Running ${selected.length} case(s) from ${manifest.name} with ${spec.id}`);
for (const testCase of selected) {
  await runCase(testCase, spec);
}
