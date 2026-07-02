import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { performance } from "node:perf_hooks";
import { generateText } from "ai";
import { googleVertex } from "@ai-sdk/google-vertex";

type ManifestCase = {
  id: string;
  title: string;
  family: string;
  tags: string[];
  pdf: string;
};

type Manifest = {
  name: string;
  cases: ManifestCase[];
};

type RunSummary = {
  caseId: string;
  title: string;
  modelId: string;
  modelName: string;
  elapsedMs: number;
  finishReason: string;
  usage: unknown;
  estimatedCostUsd: number;
  error?: string;
};

const MODEL_ID = "vertex-gemini-3.1-flash-lite";
const MODEL_NAME = "gemini-3.1-flash-lite";
const INPUT_PER_MILLION = 0.25;
const OUTPUT_PER_MILLION = 1.5;

const prompt = `Convert the attached PDF into one faithful Markdown document.

Rules:
- Return only Markdown.
- Preserve visible text in reading order.
- Preserve headings, lists, tables, forms, captions, code blocks, math, checkbox states, and footnotes where possible.
- For charts, diagrams, stamps, handwriting, images, and other non-textual content, insert concise natural-language descriptions inline where they appear.
- Do not summarize the document.
- Do not add source citations, commentary, JSON, or a wrapper.`;

function usageCost(usage: any): number {
  const input = usage?.inputTokens ?? 0;
  const output = usage?.outputTokens ?? 0;
  return (input / 1_000_000) * INPUT_PER_MILLION + (output / 1_000_000) * OUTPUT_PER_MILLION;
}

function parseArgs() {
  const args = new Map<string, string>();
  for (let i = 2; i < process.argv.length; i += 1) {
    const arg = process.argv[i];
    if (arg.startsWith("--")) {
      args.set(arg.slice(2), process.argv[i + 1] && !process.argv[i + 1].startsWith("--") ? process.argv[++i] : "true");
    }
  }
  return args;
}

async function runCase(testCase: ManifestCase) {
  const pdf = await readFile(testCase.pdf);
  const outputDir = path.join("runs", MODEL_ID, testCase.id);
  await mkdir(outputDir, { recursive: true });
  const started = performance.now();

  try {
    const result = await generateText({
      model: googleVertex(MODEL_NAME),
      messages: [
        {
          role: "user",
          content: [
            { type: "text", text: prompt },
            {
              type: "file",
              data: pdf,
              mediaType: "application/pdf",
              filename: `${testCase.id}.pdf`,
            },
          ],
        },
      ],
      maxOutputTokens: 12000,
      providerOptions: {
        vertex: {
          thinkingConfig: {
            thinkingBudget: 128,
          },
        },
      },
    });
    const elapsedMs = Math.round(performance.now() - started);
    const summary: RunSummary = {
      caseId: testCase.id,
      title: testCase.title,
      modelId: MODEL_ID,
      modelName: MODEL_NAME,
      elapsedMs,
      finishReason: result.finishReason,
      usage: result.usage,
      estimatedCostUsd: usageCost(result.usage),
    };
    await writeFile(path.join(outputDir, "prediction.md"), result.text, "utf-8");
    await writeFile(path.join(outputDir, "result.json"), JSON.stringify(summary, null, 2) + "\n", "utf-8");
    console.log(`${testCase.id}: ${summary.finishReason} ${summary.elapsedMs}ms $${summary.estimatedCostUsd.toFixed(6)}`);
  } catch (error) {
    const elapsedMs = Math.round(performance.now() - started);
    const summary: RunSummary = {
      caseId: testCase.id,
      title: testCase.title,
      modelId: MODEL_ID,
      modelName: MODEL_NAME,
      elapsedMs,
      finishReason: "error",
      usage: null,
      estimatedCostUsd: 0,
      error: error instanceof Error ? error.message : String(error),
    };
    await writeFile(path.join(outputDir, "prediction.md"), "", "utf-8");
    await writeFile(path.join(outputDir, "result.json"), JSON.stringify(summary, null, 2) + "\n", "utf-8");
    console.error(`${testCase.id}: ERROR ${summary.error}`);
  }
}

const args = parseArgs();
const manifest = JSON.parse(await readFile("benchmark/manifest.json", "utf-8")) as Manifest;
const caseArg = args.get("case");
const selected = caseArg ? manifest.cases.filter((testCase) => testCase.id === caseArg) : manifest.cases;

if (selected.length === 0) {
  throw new Error(`No cases selected. Use --case with one of: ${manifest.cases.map((testCase) => testCase.id).join(", ")}`);
}

console.log(`Running ${selected.length} case(s) from ${manifest.name} with ${MODEL_ID}`);
for (const testCase of selected) {
  await runCase(testCase);
}
