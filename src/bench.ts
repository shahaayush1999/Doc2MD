import { mkdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { performance } from "node:perf_hooks";
import { fileURLToPath } from "node:url";
import { generateText } from "ai";
import { evaluatePrediction, type ManifestCase } from "./evaluator.js";
import { loadBenchmarkManifest } from "./manifest.js";
import { calculateCost } from "./pricing.js";
import { conversionPrompt, createModel, defaultModelIds, models } from "./models.js";

const maxOutputTokens = 60_000;

function parseModels(argv: string[]) {
  const selected: string[] = [];
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] !== "--model" || !argv[index + 1]) {
      throw new Error(`Usage: npm run bench -- [--model MODEL_ID ...]\nModels: ${Object.keys(models).join(", ")}`);
    }
    const modelId = argv[++index]!;
    if (!models[modelId]) throw new Error(`Unknown model ${modelId}. Models: ${Object.keys(models).join(", ")}`);
    if (!selected.includes(modelId)) selected.push(modelId);
  }
  return selected.length > 0 ? selected : defaultModelIds;
}

async function writeJson(filePath: string, value: unknown) {
  await writeFile(filePath, JSON.stringify(value, null, 2) + "\n", "utf8");
}

function errorMessage(error: unknown) {
  return error instanceof Error ? `${error.name}: ${error.message}` : String(error);
}

async function runCase(modelId: string, testCase: ManifestCase, modelDirectory: string) {
  const spec = models[modelId]!;
  const caseDirectory = path.join(modelDirectory, testCase.id);
  await mkdir(caseDirectory, { recursive: true });

  let prediction: string;
  let inference: any;
  try {
    const pdf = await readFile(testCase.pdf);
    const started = performance.now();
    const response = await generateText({
      model: createModel(spec),
      messages: [
        {
          role: "user",
          content: [
            { type: "text", text: conversionPrompt },
            { type: "file", data: pdf, mediaType: "application/pdf", filename: `${testCase.id}.pdf` },
          ],
        },
      ],
      maxOutputTokens,
      maxRetries: 2,
      ...(spec.reasoning ? { reasoning: spec.reasoning } : {}),
    });
    prediction = response.text;
    inference = {
      modelId,
      resolvedModel: response.response.modelId,
      elapsedMs: Math.round(performance.now() - started),
      finishReason: response.finishReason,
      usage: response.usage,
      costUsd: calculateCost(spec, response.usage),
    };
    await Promise.all([
      writeFile(path.join(caseDirectory, "prediction.md"), prediction, "utf8"),
      writeJson(path.join(caseDirectory, "inference.json"), inference),
    ]);
  } catch (error) {
    const failure = { caseId: testCase.id, modelId, stage: "inference", error: errorMessage(error) };
    await writeJson(path.join(caseDirectory, "error.json"), failure);
    console.error(`${modelId} ${testCase.id}: inference failed`);
    return { caseId: testCase.id, title: testCase.title, score: null, inferenceCostUsd: 0, evaluatorCostUsd: 0, error: failure.error };
  }

  try {
    const evaluation = await evaluatePrediction(testCase, prediction);
    await writeJson(path.join(caseDirectory, "score.json"), evaluation);
    console.log(
      `${modelId} ${testCase.id}: ${evaluation.score === null ? "INVALID" : evaluation.score.toFixed(1)} ` +
        `($${(inference.costUsd + evaluation.evaluator.costUsd).toFixed(6)})`,
    );
    return {
      caseId: testCase.id,
      title: testCase.title,
      score: evaluation.score,
      inferenceCostUsd: inference.costUsd,
      evaluatorCostUsd: evaluation.evaluator.costUsd,
      inferenceElapsedMs: inference.elapsedMs,
      evaluatorElapsedMs: evaluation.evaluator.elapsedMs,
      error: evaluation.valid ? null : evaluation.evaluator.errors.join("; "),
    };
  } catch (error) {
    const failure = { caseId: testCase.id, modelId, stage: "evaluation", error: errorMessage(error) };
    await writeJson(path.join(caseDirectory, "error.json"), failure);
    console.error(`${modelId} ${testCase.id}: evaluation failed`);
    return {
      caseId: testCase.id,
      title: testCase.title,
      score: null,
      inferenceCostUsd: inference.costUsd,
      evaluatorCostUsd: 0,
      error: failure.error,
    };
  }
}

function mean(values: number[]) {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function escapeHtml(value: unknown) {
  return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}

function renderReport(summary: any) {
  const sections = summary.models
    .map(
      (model: any) => `<section><h2>${escapeHtml(model.modelId)} — ${model.score === null ? "Incomplete" : model.score.toFixed(1)}</h2>
      <table><thead><tr><th>Case</th><th>Score</th><th>Inference</th><th>Evaluator</th></tr></thead><tbody>
      ${model.cases
        .map(
          (testCase: any) => `<tr><td>${escapeHtml(testCase.caseId)}</td><td>${testCase.score === null ? "—" : testCase.score.toFixed(1)}</td><td>$${testCase.inferenceCostUsd.toFixed(6)}</td><td>$${testCase.evaluatorCostUsd.toFixed(6)}</td></tr>`,
        )
        .join("")}
      </tbody></table></section>`,
    )
    .join("");
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Doc2MD benchmark</title><style>
  body{max-width:1000px;margin:48px auto;padding:0 20px;font:15px/1.5 system-ui;color:#18201c;background:#f6f5f0}h1,h2{font-family:Georgia,serif}section{margin:36px 0;background:white;padding:20px;border:1px solid #ddd;border-radius:10px}table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:9px;border-bottom:1px solid #ddd}th{color:#59625d}code{background:#ecebe5;padding:2px 5px}</style></head><body>
  <h1>Doc2MD benchmark</h1><p>Run <code>${escapeHtml(summary.runId)}</code> · ${summary.caseCount} cases · Total spend $${summary.totalCostUsd.toFixed(6)}</p>${sections}</body></html>`;
}

export async function runBenchmark(modelIds: string[]) {
  const startedAt = new Date();
  const runId = startedAt.toISOString().replaceAll(":", "-").replaceAll(".", "-");
  const runDirectory = path.join("runs", runId);
  const { manifest } = await loadBenchmarkManifest();
  await mkdir(runDirectory, { recursive: true });

  const modelResults = [];
  for (const modelId of modelIds) {
    console.log(`\n${modelId}: starting ${manifest.cases.length} case pipelines in parallel`);
    const cases = await Promise.all(
      manifest.cases.map((testCase) => runCase(modelId, testCase as ManifestCase, path.join(runDirectory, modelId))),
    );
    const validScores = cases.flatMap((testCase) => (testCase.score === null ? [] : [testCase.score]));
    const inferenceCostUsd = cases.reduce((sum, testCase) => sum + testCase.inferenceCostUsd, 0);
    const evaluatorCostUsd = cases.reduce((sum, testCase) => sum + testCase.evaluatorCostUsd, 0);
    modelResults.push({
      modelId,
      score: validScores.length === cases.length ? mean(validScores) : null,
      inferenceCostUsd,
      evaluatorCostUsd,
      totalCostUsd: inferenceCostUsd + evaluatorCostUsd,
      cases,
    });
  }

  const summary = {
    runId,
    startedAt: startedAt.toISOString(),
    completedAt: new Date().toISOString(),
    caseCount: manifest.cases.length,
    models: modelResults,
    totalCostUsd: modelResults.reduce((sum, model) => sum + model.totalCostUsd, 0),
  };
  await Promise.all([
    writeJson(path.join(runDirectory, "summary.json"), summary),
    writeFile(path.join(runDirectory, "report.html"), renderReport(summary), "utf8"),
  ]);
  console.table(modelResults.map((model) => ({ model: model.modelId, score: model.score, spendUsd: model.totalCostUsd })));
  console.log(`Report: ${path.join(runDirectory, "report.html")}`);
  return summary;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  await runBenchmark(parseModels(process.argv.slice(2)));
}
