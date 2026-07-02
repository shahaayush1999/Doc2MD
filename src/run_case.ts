import { readFile, mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { performance } from "node:perf_hooks";
import { generateText } from "ai";
import { openai } from "@ai-sdk/openai";
import { googleVertex } from "@ai-sdk/google-vertex";

type ModelSpec = {
  id: string;
  provider: "openai" | "google-vertex";
  modelName: string;
  reasoning: "none" | "minimal";
  inputPerMillion: number;
  outputPerMillion: number;
};

const models: ModelSpec[] = [
  {
    id: "openai-gpt-5.4-nano",
    provider: "openai",
    modelName: "gpt-5.4-nano",
    reasoning: "none",
    inputPerMillion: 0.2,
    outputPerMillion: 1.25,
  },
  {
    id: "vertex-gemini-3.1-flash-lite",
    provider: "google-vertex",
    modelName: "gemini-3.1-flash-lite",
    reasoning: "minimal",
    inputPerMillion: 0.25,
    outputPerMillion: 1.5,
  },
];

const prompt = `Convert the attached PDF into a single faithful Markdown document.

Rules:
- Return only Markdown.
- Preserve all visible text in reading order.
- Preserve headings, lists, tables, and captions where possible.
- For images, charts, diagrams, and figures, insert concise natural-language descriptions inline at the original location.
- Do not summarize or add commentary about the conversion.`;

function modelFor(spec: ModelSpec) {
  if (spec.provider === "openai") return openai(spec.modelName);
  return googleVertex(spec.modelName);
}

function dollars(spec: ModelSpec, usage: any): number {
  const input = usage?.inputTokens ?? 0;
  const output = usage?.outputTokens ?? 0;
  return (input / 1_000_000) * spec.inputPerMillion + (output / 1_000_000) * spec.outputPerMillion;
}

async function runOne(caseId: string, spec: ModelSpec) {
  const caseDir = path.join("experiments", "cases", caseId);
  const pdfPath = path.join(caseDir, "source.pdf");
  const outputDir = path.join("experiments", "runs", caseId, spec.id);
  await mkdir(outputDir, { recursive: true });

  const pdf = await readFile(pdfPath);
  const started = performance.now();
  const result = await generateText({
    model: modelFor(spec),
    messages: [
      {
        role: "user",
        content: [
          { type: "text", text: prompt },
          {
            type: "file",
            data: pdf,
            mediaType: "application/pdf",
            filename: `${caseId}.pdf`,
          },
        ],
      },
    ],
    maxOutputTokens: 4096,
    reasoning: spec.reasoning,
  });
  const elapsedMs = Math.round(performance.now() - started);

  const summary = {
    caseId,
    model: spec.id,
    provider: spec.provider,
    modelName: spec.modelName,
    reasoning: spec.reasoning,
    elapsedMs,
    finishReason: result.finishReason,
    usage: result.usage,
    estimatedCostUsd: dollars(spec, result.usage),
  };

  await writeFile(path.join(outputDir, "prediction.md"), result.text, "utf-8");
  await writeFile(path.join(outputDir, "result.json"), JSON.stringify(summary, null, 2) + "\n", "utf-8");
  console.log(JSON.stringify(summary, null, 2));
}

const caseId = process.argv[2] ?? "001-figure-trap";
const modelArg = process.argv[3] ?? "all";
const selected = modelArg === "all" ? models : models.filter((model) => model.id === modelArg);

if (selected.length === 0) {
  throw new Error(`Unknown model "${modelArg}". Options: all, ${models.map((model) => model.id).join(", ")}`);
}

for (const spec of selected) {
  await runOne(caseId, spec);
}
