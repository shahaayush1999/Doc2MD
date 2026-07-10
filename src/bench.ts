import { createHash } from "node:crypto";
import { mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { performance } from "node:perf_hooks";
import { fileURLToPath } from "node:url";
import { generateText } from "ai";
import { evaluatePrediction, type ManifestCase } from "./evaluator.js";
import { loadBenchmarkManifest } from "./manifest.js";
import { calculateCost } from "./pricing.js";
import { createModel, defaultModelIds, models, type ModelSpec } from "./models.js";
import { renderReport } from "./report.js";

const cacheRoot = "runs/cache";
const promptPath = "benchmark/prompt.md";
const maxOutputTokens = 60_000;

function sha256(value: string | Uint8Array) {
  return createHash("sha256").update(value).digest("hex");
}

async function readJson(filePath: string) {
  return JSON.parse(await readFile(filePath, "utf8")) as any;
}

async function readJsonOrNull(filePath: string) {
  try {
    return await readJson(filePath);
  } catch {
    return null;
  }
}

async function writeJson(filePath: string, value: unknown) {
  await mkdir(path.dirname(filePath), { recursive: true });
  await writeFile(filePath, JSON.stringify(value, null, 2) + "\n", "utf8");
}

function cacheDirectory(modelId: string, caseId: string) {
  return path.join(cacheRoot, modelId, caseId);
}

async function inferenceKey(spec: ModelSpec, testCase: ManifestCase, prompt: string) {
  const pdf = await readFile(testCase.pdf);
  return sha256(
    JSON.stringify({
      pdf: sha256(pdf),
      prompt: sha256(prompt),
      model: {
        id: spec.id,
        modelName: spec.modelName,
        provider: spec.provider,
        reasoning: spec.reasoning ?? null,
        location: spec.location ?? null,
      },
      maxOutputTokens,
    }),
  );
}

async function scoreKey(testCase: ManifestCase, prediction: string, evaluatorSourceHash: string) {
  if (!testCase.facts) throw new Error(`${testCase.id} has no facts file.`);
  return sha256(
    JSON.stringify({
      prediction: sha256(prediction),
      facts: sha256(await readFile(testCase.facts)),
      evaluator: evaluatorSourceHash,
    }),
  );
}

async function loadCachedCase(modelId: string, testCase: ManifestCase, prompt: string, evaluatorSourceHash: string) {
  const directory = cacheDirectory(modelId, testCase.id);
  const [prediction, inference, evaluation] = await Promise.all([
    readFile(path.join(directory, "prediction.md"), "utf8").catch(() => null),
    readJsonOrNull(path.join(directory, "inference.json")),
    readJsonOrNull(path.join(directory, "score.json")),
  ]);
  if (!prediction || !inference) return null;
  const expectedInferenceKey = await inferenceKey(models[modelId]!, testCase, prompt);
  if (inference.cacheKey !== expectedInferenceKey) return null;
  const expectedScoreKey = await scoreKey(testCase, prediction, evaluatorSourceHash);
  return {
    directory,
    prediction,
    inference,
    evaluation: evaluation?.cacheKey === expectedScoreKey ? evaluation : null,
    inferenceKey: expectedInferenceKey,
    scoreKey: expectedScoreKey,
  };
}

async function importLegacyResults(manifest: { cases: ManifestCase[] }, prompt: string, evaluatorSourceHash: string) {
  for (const modelId of Object.keys(models)) {
    const spec = models[modelId]!;
    for (const testCase of manifest.cases) {
      const directory = cacheDirectory(modelId, testCase.id);
      if (await readJsonOrNull(path.join(directory, "inference.json"))) continue;
      const legacyDirectory = path.join("runs", modelId, testCase.id, "samples", "001");
      const [prediction, result, score] = await Promise.all([
        readFile(path.join(legacyDirectory, "prediction.md"), "utf8").catch(() => null),
        readJsonOrNull(path.join(legacyDirectory, "result.json")),
        readJsonOrNull(path.join(legacyDirectory, "score.json")),
      ]);
      if (!prediction || !result || !score || !Number.isFinite(score.score)) continue;
      const pdfHash = sha256(await readFile(testCase.pdf));
      if (
        result.modelId !== modelId ||
        result.modelName !== spec.modelName ||
        result.cache?.pdfHash !== pdfHash ||
        result.cache?.promptHash !== sha256(prompt)
      ) {
        continue;
      }
      const importedInference = {
        modelId,
        resolvedModel: result.providerMetadata?.resolved?.modelId ?? result.modelName,
        elapsedMs: result.elapsedMs ?? 0,
        finishReason: result.finishReason ?? "unknown",
        usage: result.usage ?? null,
        costUsd: result.estimatedCostUsd ?? 0,
        cacheKey: await inferenceKey(spec, testCase, prompt),
        importedFromLegacyRun: true,
      };
      const importedScore = {
        valid: score.valid === true,
        score: score.score,
        evaluator: {
          model: score.scorer?.evaluatorModelName ?? "gemini-3.1-flash-lite",
          attempts: score.scorer?.attempts ?? 0,
          errors: score.scorer?.errors ?? [],
          elapsedMs: score.scorer?.elapsedMs ?? 0,
          usage: score.scorer?.usage ?? null,
          costUsd: score.scorer?.estimatedCostUsd ?? 0,
        },
        atomicScore: score.atomicScore,
        judgeResult: score.judgeResult,
        cacheKey: await scoreKey(testCase, prediction, evaluatorSourceHash),
        importedFromLegacyRun: true,
      };
      await mkdir(directory, { recursive: true });
      await Promise.all([
        writeFile(path.join(directory, "prediction.md"), prediction, "utf8"),
        writeJson(path.join(directory, "inference.json"), importedInference),
        writeJson(path.join(directory, "score.json"), importedScore),
      ]);
    }
  }
}

function errorMessage(error: unknown) {
  return error instanceof Error ? `${error.name}: ${error.message}` : String(error);
}

async function runCase(modelId: string, testCase: ManifestCase, prompt: string, evaluatorSourceHash: string) {
  const spec = models[modelId]!;
  const directory = cacheDirectory(modelId, testCase.id);
  await mkdir(directory, { recursive: true });
  let cached = await loadCachedCase(modelId, testCase, prompt, evaluatorSourceHash);
  let prediction = cached?.prediction ?? null;
  let inference = cached?.inference ?? null;
  let inferenceSpent = 0;
  let evaluatorSpent = 0;

  if (!prediction || !inference) {
    const pdf = await readFile(testCase.pdf);
    const started = performance.now();
    const response = await generateText({
      model: createModel(spec),
      messages: [{ role: "user", content: [{ type: "text", text: prompt }, { type: "file", data: pdf, mediaType: "application/pdf", filename: `${testCase.id}.pdf` }] }],
      maxOutputTokens,
      maxRetries: 2,
      ...(spec.reasoning ? { reasoning: spec.reasoning } : {}),
    });
    prediction = response.text;
    inferenceSpent = calculateCost(spec, response.usage);
    inference = {
      modelId,
      resolvedModel: response.response.modelId,
      elapsedMs: Math.round(performance.now() - started),
      finishReason: response.finishReason,
      usage: response.usage,
      costUsd: inferenceSpent,
      cacheKey: await inferenceKey(spec, testCase, prompt),
    };
    await Promise.all([
      writeFile(path.join(directory, "prediction.md"), prediction, "utf8"),
      writeJson(path.join(directory, "inference.json"), inference),
    ]);
    cached = null;
  }

  let evaluation = cached?.evaluation ?? null;
  if (!evaluation) {
    evaluation = await evaluatePrediction(testCase, prediction);
    evaluatorSpent = evaluation.evaluator.costUsd;
    evaluation.cacheKey = await scoreKey(testCase, prediction, evaluatorSourceHash);
    await writeJson(path.join(directory, "score.json"), evaluation);
  }

  const cacheStatus = inferenceSpent === 0 && evaluatorSpent === 0 ? "cached" : inferenceSpent === 0 ? "rescored" : "run";
  console.log(`${modelId} ${testCase.id}: ${evaluation.score === null ? "INVALID" : evaluation.score.toFixed(1)} (${cacheStatus})`);
  return {
    caseId: testCase.id,
    title: testCase.title,
    score: evaluation.score as number | null,
    inferenceCostUsd: inference.costUsd ?? 0,
    evaluatorCostUsd: evaluation.evaluator.costUsd ?? 0,
    incrementalCostUsd: inferenceSpent + evaluatorSpent,
    incrementalInferenceCostUsd: inferenceSpent,
    incrementalEvaluatorCostUsd: evaluatorSpent,
    cacheStatus,
  };
}

function mean(values: number[]) {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

async function cachedModelIds() {
  const entries = await readdir(cacheRoot, { withFileTypes: true }).catch(() => []);
  return entries.filter((entry) => entry.isDirectory() && models[entry.name]).map((entry) => entry.name);
}

function parseRequestedModels(argv: string[]) {
  const selected: string[] = [];
  for (let index = 0; index < argv.length; index += 1) {
    if (argv[index] !== "--model" || !argv[index + 1]) throw new Error("Usage: npm run bench -- [--model MODEL_ID ...]");
    const modelId = argv[++index]!;
    if (!models[modelId]) throw new Error(`Unknown model ${modelId}. Models: ${Object.keys(models).join(", ")}`);
    if (!selected.includes(modelId)) selected.push(modelId);
  }
  return selected;
}

async function collectMergedResults(manifest: { cases: ManifestCase[] }, prompt: string, evaluatorSourceHash: string) {
  const merged = [];
  for (const modelId of await cachedModelIds()) {
    const cases = [];
    for (const testCase of manifest.cases) {
      const cached = await loadCachedCase(modelId, testCase, prompt, evaluatorSourceHash);
      if (!cached?.evaluation || !Number.isFinite(cached.evaluation.score)) break;
      cases.push({
        caseId: testCase.id,
        title: testCase.title,
        score: cached.evaluation.score,
        inferenceCostUsd: cached.inference.costUsd ?? 0,
        evaluatorCostUsd: cached.evaluation.evaluator.costUsd ?? 0,
        outputTokens: cached.inference.usage?.outputTokens ?? 0,
        inferenceElapsedMs: cached.inference.elapsedMs ?? 0,
      });
    }
    if (cases.length !== manifest.cases.length) continue;
    const inferenceCostUsd = cases.reduce((sum, testCase) => sum + testCase.inferenceCostUsd, 0);
    const evaluatorCostUsd = cases.reduce((sum, testCase) => sum + testCase.evaluatorCostUsd, 0);
    const totalOutputTokens = cases.reduce((sum, testCase) => sum + testCase.outputTokens, 0);
    const inferenceSeconds = cases.reduce((sum, testCase) => sum + testCase.inferenceElapsedMs, 0) / 1_000;
    merged.push({ modelId, score: mean(cases.map((testCase) => testCase.score)), inferenceCostUsd, evaluatorCostUsd, totalCostUsd: inferenceCostUsd + evaluatorCostUsd, totalOutputTokens, inferenceSeconds, cases });
  }
  return merged.sort((a, b) => b.score - a.score);
}

export async function runBenchmark(requestedModelIds: string[]) {
  const { manifest } = await loadBenchmarkManifest();
  const [promptFile, evaluatorSource] = await Promise.all([readFile(promptPath, "utf8"), readFile("src/evaluator.ts")]);
  const prompt = promptFile.trimEnd();
  const evaluatorSourceHash = sha256(evaluatorSource);
  await importLegacyResults(manifest as { cases: ManifestCase[] }, prompt, evaluatorSourceHash);
  const modelIds = requestedModelIds.length > 0 ? requestedModelIds : [...new Set([...defaultModelIds, ...(await cachedModelIds())])];
  let incrementalInferenceSpendUsd = 0;
  let incrementalEvaluatorSpendUsd = 0;

  for (const modelId of modelIds) {
    console.log(`\n${modelId}: checking ${manifest.cases.length} cases`);
    const cases = await Promise.all(manifest.cases.map((testCase) => runCase(modelId, testCase as ManifestCase, prompt, evaluatorSourceHash)));
    incrementalInferenceSpendUsd += cases.reduce((sum, testCase) => sum + testCase.incrementalInferenceCostUsd, 0);
    incrementalEvaluatorSpendUsd += cases.reduce((sum, testCase) => sum + testCase.incrementalEvaluatorCostUsd, 0);
  }

  const mergedModels = await collectMergedResults(manifest as { cases: ManifestCase[] }, prompt, evaluatorSourceHash);
  const summary = {
    generatedAt: new Date().toISOString(),
    caseCount: manifest.cases.length,
    incrementalSpendUsd: incrementalInferenceSpendUsd + incrementalEvaluatorSpendUsd,
    incrementalInferenceSpendUsd,
    incrementalEvaluatorSpendUsd,
    totalCostUsd: mergedModels.reduce((sum, model) => sum + model.totalCostUsd, 0),
    models: mergedModels,
  };
  await mkdir("reports", { recursive: true });
  await Promise.all([writeJson("reports/summary.json", summary), writeFile("reports/index.html", renderReport(summary), "utf8")]);
  console.table(mergedModels.map((model) => ({ model: model.modelId, score: model.score, inferenceSpendUsd: model.inferenceCostUsd })));
  console.log(`Incremental model inference spend: $${incrementalInferenceSpendUsd.toFixed(6)}`);
  console.log("Report: reports/index.html");
  return summary;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  await runBenchmark(parseRequestedModels(process.argv.slice(2)));
}
