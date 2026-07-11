import { createHash } from "node:crypto";
import { mkdir, readFile, readdir, stat, writeFile } from "node:fs/promises";
import path from "node:path";
import { performance } from "node:perf_hooks";
import { fileURLToPath } from "node:url";
import { generateText } from "ai";
import {
  evaluatePrediction,
  type ManifestCase,
} from "./evaluator.js";
import { loadBenchmarkManifest } from "./manifest.js";
import { calculateCost } from "./pricing.js";
import { createModel, defaultModelIds, models, type ModelSpec } from "./models.js";
import { renderReport } from "./report.js";

const cacheRoot = "runs/cache";
const promptPath = "benchmark/prompt.md";
const maxOutputTokens = 60_000;
const inferenceProtocolVersion = 2;
const ingestionMode = "native PDF attached directly to the provider model API";

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

function cacheDirectory(modelId: string, caseId: string, draw = 1) {
  const firstDraw = path.join(cacheRoot, modelId, caseId);
  return draw === 1 ? firstDraw : path.join(firstDraw, "draws", String(draw).padStart(3, "0"));
}

function configuredModel(spec: ModelSpec) {
  return {
    id: spec.id,
    modelName: spec.modelName,
    provider: spec.provider,
    reasoning: spec.reasoning ?? null,
    location: spec.location ?? null,
    maxOutputTokens: spec.maxOutputTokens ?? maxOutputTokens,
  };
}

async function packageLockHash() {
  return sha256(await readFile("package-lock.json"));
}

async function legacyInferenceKey(spec: ModelSpec, testCase: ManifestCase, prompt: string) {
  const pdf = await readFile(testCase.pdf);
  const outputLimit = spec.maxOutputTokens ?? maxOutputTokens;
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
      maxOutputTokens: outputLimit,
    }),
  );
}

async function inferenceKey(spec: ModelSpec, testCase: ManifestCase, prompt: string) {
  const pdf = await readFile(testCase.pdf);
  return sha256(JSON.stringify({
    protocolVersion: inferenceProtocolVersion,
    ingestionMode,
    packageLock: await packageLockHash(),
    pdf: sha256(pdf),
    prompt: sha256(prompt),
    model: configuredModel(spec),
  }));
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

async function loadCachedCase(modelId: string, testCase: ManifestCase, prompt: string, evaluatorSourceHash: string, draw = 1) {
  const directory = cacheDirectory(modelId, testCase.id, draw);
  const [prediction, inference, evaluation] = await Promise.all([
    readFile(path.join(directory, "prediction.md"), "utf8").catch(() => null),
    readJsonOrNull(path.join(directory, "inference.json")),
    readJsonOrNull(path.join(directory, "score.json")),
  ]);
  if (!prediction || !inference) return null;
  const expectedInferenceKey = await inferenceKey(models[modelId]!, testCase, prompt);
  const isLegacyKey = inference.cacheKey === await legacyInferenceKey(models[modelId]!, testCase, prompt);
  if (inference.cacheKey !== expectedInferenceKey && !isLegacyKey) return null;
  const inferenceStat = await stat(path.join(directory, "inference.json"));
  const expectedScoreKey = await scoreKey(testCase, prediction, evaluatorSourceHash);
  return {
    directory,
    prediction,
    inference,
    evaluation: evaluation?.cacheKey === expectedScoreKey ? evaluation : null,
    inferenceKey: expectedInferenceKey,
    inferenceNeedsUpgrade: isLegacyKey,
    inferenceFileMtime: inferenceStat.mtime,
    scoreKey: expectedScoreKey,
  };
}

function errorMessage(error: unknown) {
  return error instanceof Error ? `${error.name}: ${error.message}` : String(error);
}

async function runCase(modelId: string, testCase: ManifestCase, prompt: string, evaluatorSourceHash: string, draw: number) {
  const spec = models[modelId]!;
  const directory = cacheDirectory(modelId, testCase.id, draw);
  await mkdir(directory, { recursive: true });
  let cached = await loadCachedCase(modelId, testCase, prompt, evaluatorSourceHash, draw);
  let prediction = cached?.prediction ?? null;
  let inference = cached?.inference ?? null;
  let inferenceSpent = 0;
  let evaluatorSpent = 0;

  if (prediction && inference && cached?.inferenceNeedsUpgrade) {
    const finishedAt = cached.inferenceFileMtime.toISOString();
    const startedAt = new Date(cached.inferenceFileMtime.getTime() - Math.max(0, inference.elapsedMs ?? 0)).toISOString();
    inference = {
      ...inference,
      configuredModel: configuredModel(spec),
      ingestionMode,
      protocolVersion: inferenceProtocolVersion,
      packageLockHash: await packageLockHash(),
      pricingVersion: spec.pricingVersion,
      recordedCostUsd: inference.costUsd ?? null,
      costUsd: calculateCost(spec, inference.usage),
      startedAt,
      finishedAt,
      timestampSource: "cache-file-mtime",
      cacheKey: cached.inferenceKey,
    };
    await writeJson(path.join(directory, "inference.json"), inference);
  }

  if (!prediction || !inference) {
    const pdf = await readFile(testCase.pdf);
    const outputLimit = spec.maxOutputTokens ?? maxOutputTokens;
    const startedAt = new Date();
    const started = performance.now();
    const response = await generateText({
      model: createModel(spec),
      messages: [{ role: "user", content: [{ type: "text", text: prompt }, { type: "file", data: pdf, mediaType: "application/pdf", filename: `${testCase.id}.pdf` }] }],
      maxOutputTokens: outputLimit,
      maxRetries: 2,
      ...(spec.reasoning ? { reasoning: spec.reasoning } : {}),
    });
    prediction = response.text;
    inferenceSpent = calculateCost(spec, response.usage);
    const finishedAt = new Date();
    inference = {
      modelId,
      configuredModel: configuredModel(spec),
      resolvedModel: response.response.modelId,
      ingestionMode,
      protocolVersion: inferenceProtocolVersion,
      packageLockHash: await packageLockHash(),
      pricingVersion: spec.pricingVersion,
      startedAt: startedAt.toISOString(),
      finishedAt: finishedAt.toISOString(),
      timestampSource: "provider-call-clock",
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
  console.log(`${modelId} draw ${draw} ${testCase.id}: ${evaluation.score === null ? "INVALID" : evaluation.score.toFixed(1)} (${cacheStatus})`);
  return {
    draw,
    caseId: testCase.id,
    title: testCase.title,
    score: evaluation.score as number | null,
    inferenceCostUsd: calculateCost(spec, inference.usage),
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

function sampleStddev(values: number[]) {
  if (values.length < 2) return null;
  const average = mean(values);
  return Math.sqrt(values.reduce((sum, value) => sum + (value - average) ** 2, 0) / (values.length - 1));
}

async function cachedModelIds() {
  const entries = await readdir(cacheRoot, { withFileTypes: true }).catch(() => []);
  return entries.filter((entry) => entry.isDirectory() && models[entry.name]).map((entry) => entry.name);
}

function parseOptions(argv: string[]) {
  const selected: string[] = [];
  let runs = 1;
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index];
    const value = argv[index + 1];
    if (argument === "--model" && value) {
      if (!models[value]) throw new Error(`Unknown model ${value}. Models: ${Object.keys(models).join(", ")}`);
      if (!selected.includes(value)) selected.push(value);
      index += 1;
      continue;
    }
    if (argument === "--runs" && value) {
      runs = Number(value);
      if (!Number.isSafeInteger(runs) || runs < 1 || runs > 20) throw new Error("--runs must be an integer from 1 to 20.");
      index += 1;
      continue;
    }
    throw new Error("Usage: npm run bench -- [--model MODEL_ID ...] [--runs N]");
  }
  return { modelIds: selected, runs };
}

async function collectMergedResults(manifest: { cases: ManifestCase[] }, prompt: string, evaluatorSourceHash: string) {
  const merged = [];
  const exclusions: Array<{ modelId: string; reason: string }> = [];
  for (const modelId of await cachedModelIds()) {
    const draws: any[] = [];
    for (let draw = 1; draw <= 20; draw += 1) {
      const cases = [];
      for (const testCase of manifest.cases) {
        const cached = await loadCachedCase(modelId, testCase, prompt, evaluatorSourceHash, draw);
        if (!cached?.evaluation || !Number.isFinite(cached.evaluation.score)) break;
        cases.push({
          caseId: testCase.id,
          title: testCase.title,
          score: cached.evaluation.score,
          inferenceCostUsd: calculateCost(models[modelId]!, cached.inference.usage),
          evaluatorCostUsd: cached.evaluation.evaluator.costUsd ?? 0,
          outputTokens: cached.inference.usage?.outputTokens ?? 0,
          inferenceElapsedMs: cached.inference.elapsedMs ?? 0,
          resolvedModel: cached.inference.resolvedModel ?? null,
          evaluatorResolvedModel: cached.evaluation.evaluator?.resolved?.modelId ?? null,
          startedAt: cached.inference.startedAt ?? null,
          finishedAt: cached.inference.finishedAt ?? null,
        });
      }
      if (cases.length !== manifest.cases.length) break;
      draws.push({
        draw,
        score: mean(cases.map((testCase) => testCase.score)),
        inferenceCostUsd: cases.reduce((sum, testCase) => sum + testCase.inferenceCostUsd, 0),
        evaluatorCostUsd: cases.reduce((sum, testCase) => sum + testCase.evaluatorCostUsd, 0),
        totalOutputTokens: cases.reduce((sum, testCase) => sum + testCase.outputTokens, 0),
        inferenceSeconds: cases.reduce((sum, testCase) => sum + testCase.inferenceElapsedMs, 0) / 1_000,
        cases,
      });
    }
    if (draws.length === 0) continue;
    const resolvedModels = [...new Set(draws.flatMap((draw) => draw.cases.map((item: any) => item.resolvedModel)).filter(Boolean))];
    const resolvedEvaluators = [...new Set(draws.flatMap((draw) => draw.cases.map((item: any) => item.evaluatorResolvedModel)).filter(Boolean))];
    if (resolvedModels.length !== 1 || resolvedEvaluators.length !== 1) {
      exclusions.push({
        modelId,
        reason: `Resolved identity drift: model=${resolvedModels.join(", ") || "missing"}; evaluator=${resolvedEvaluators.join(", ") || "missing"}`,
      });
      continue;
    }
    const drawScores = draws.map((draw) => draw.score);
    const cases = manifest.cases.map((testCase, caseIndex) => {
      const observations = draws.map((draw) => draw.cases[caseIndex]!);
      const scores = observations.map((observation) => observation.score);
      return {
        caseId: testCase.id,
        title: testCase.title,
        score: mean(scores),
        scoreMin: Math.min(...scores),
        scoreMax: Math.max(...scores),
        scoreStddev: sampleStddev(scores),
        inferenceCostUsd: mean(observations.map((observation) => observation.inferenceCostUsd)),
      };
    });
    const inferenceCostUsd = mean(draws.map((draw) => draw.inferenceCostUsd));
    const evaluatorCostUsd = mean(draws.map((draw) => draw.evaluatorCostUsd));
    merged.push({
      modelId,
      configuredModel: configuredModel(models[modelId]!),
      resolvedModel: resolvedModels[0],
      evaluatorResolvedModel: resolvedEvaluators[0],
      pricingVersion: models[modelId]!.pricingVersion,
      drawCount: draws.length,
      score: mean(drawScores),
      scoreMin: Math.min(...drawScores),
      scoreMax: Math.max(...drawScores),
      scoreStddev: sampleStddev(drawScores),
      inferenceCostUsd,
      evaluatorCostUsd,
      totalCostUsd: inferenceCostUsd + evaluatorCostUsd,
      cumulativeInferenceCostUsd: draws.reduce((sum, draw) => sum + draw.inferenceCostUsd, 0),
      cumulativeEvaluatorCostUsd: draws.reduce((sum, draw) => sum + draw.evaluatorCostUsd, 0),
      totalOutputTokens: mean(draws.map((draw) => draw.totalOutputTokens)),
      inferenceSeconds: mean(draws.map((draw) => draw.inferenceSeconds)),
      cases,
      draws,
      measurementStartedAt: draws.flatMap((draw) => draw.cases.map((item: any) => item.startedAt)).filter(Boolean).sort()[0] ?? null,
      measurementFinishedAt: draws.flatMap((draw) => draw.cases.map((item: any) => item.finishedAt)).filter(Boolean).sort().at(-1) ?? null,
    });
  }
  return { models: merged.sort((a, b) => b.score - a.score), exclusions };
}

export async function runBenchmark(requestedModelIds: string[], requestedRuns = 1) {
  const { manifest } = await loadBenchmarkManifest();
  const [promptFile, evaluatorSource] = await Promise.all([readFile(promptPath, "utf8"), readFile("src/evaluator.ts")]);
  const prompt = promptFile.trimEnd();
  const evaluatorSourceHash = sha256(evaluatorSource);
  const modelIds = requestedModelIds.length > 0 ? requestedModelIds : [...new Set([...defaultModelIds, ...(await cachedModelIds())])];
  let incrementalInferenceSpendUsd = 0;
  let incrementalEvaluatorSpendUsd = 0;

  for (const modelId of modelIds) {
    console.log(`\n${modelId}: ensuring ${requestedRuns} draw slot${requestedRuns === 1 ? "" : "s"} × ${manifest.cases.length} cases`);
    const cases = await Promise.all(
      Array.from({ length: requestedRuns }, (_, drawIndex) =>
        manifest.cases.map((testCase) => runCase(modelId, testCase as ManifestCase, prompt, evaluatorSourceHash, drawIndex + 1)),
      ).flat(),
    );
    incrementalInferenceSpendUsd += cases.reduce((sum, testCase) => sum + testCase.incrementalInferenceCostUsd, 0);
    incrementalEvaluatorSpendUsd += cases.reduce((sum, testCase) => sum + testCase.incrementalEvaluatorCostUsd, 0);
  }

  const collected = await collectMergedResults(manifest as { cases: ManifestCase[] }, prompt, evaluatorSourceHash);
  const mergedModels = collected.models;
  const manifestHash = sha256(await readFile("benchmark/manifest.json"));
  const promptHash = sha256(prompt);
  const summary = {
    generatedAt: new Date().toISOString(),
    caseCount: manifest.cases.length,
    provenance: {
      inferenceProtocolVersion,
      ingestionMode,
      promptHash,
      manifestHash,
      evaluatorSourceHash,
      packageLockHash: await packageLockHash(),
      measurementStartedAt: mergedModels.map((model) => model.measurementStartedAt).filter(Boolean).sort()[0] ?? null,
      measurementFinishedAt: mergedModels.map((model) => model.measurementFinishedAt).filter(Boolean).sort().at(-1) ?? null,
    },
    exclusions: collected.exclusions,
    incrementalSpendUsd: incrementalInferenceSpendUsd + incrementalEvaluatorSpendUsd,
    incrementalInferenceSpendUsd,
    incrementalEvaluatorSpendUsd,
    totalCostUsd: mergedModels.reduce(
      (sum, model) => sum + model.cumulativeInferenceCostUsd + model.cumulativeEvaluatorCostUsd,
      0,
    ),
    models: mergedModels,
  };
  await mkdir("reports", { recursive: true });
  await Promise.all([
    writeJson("reports/summary.json", summary),
    writeJson("results/latest.json", summary),
    writeFile("reports/index.html", renderReport(summary), "utf8"),
  ]);
  console.table(mergedModels.map((model) => ({ model: model.modelId, draws: model.drawCount, score: model.score, meanInferenceSpendUsd: model.inferenceCostUsd })));
  console.log(`Incremental model inference spend: $${incrementalInferenceSpendUsd.toFixed(6)}`);
  console.log("Report: reports/index.html");
  return summary;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const options = parseOptions(process.argv.slice(2));
  await runBenchmark(options.modelIds, options.runs);
}
