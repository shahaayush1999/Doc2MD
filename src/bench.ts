import { createHash } from "node:crypto";
import { execFile as execFileCallback } from "node:child_process";
import { mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { performance } from "node:perf_hooks";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";
import { generateText } from "ai";
import { auditBenchmark } from "./audit.js";
import { disposeEvaluatorCaches } from "./evaluator-client.js";
import {
  evaluatorConfiguration,
  evaluatePrediction,
  type ManifestCase,
} from "./evaluator.js";
import { loadBenchmarkManifest } from "./manifest.js";
import { calculateCost, calculateUncachedCost } from "./pricing.js";
import { createModel, defaultModelIds, models, type ModelSpec } from "./models.js";
import { renderReport } from "./report.js";

const cacheRoot = "runs/cache";
const promptPath = "benchmark/prompt.md";
const maxOutputTokens = 60_000;
const inferenceProtocolVersion = 2;
const ingestionMode = "native PDF attached directly to the provider model API";
const reportedInvalidInferenceSlots = new Set<string>();
const execFile = promisify(execFileCallback);

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

async function validateCorpusArtifacts() {
  let stdout: string;
  try {
    ({ stdout } = await execFile(
      "uv",
      ["run", "python", "scripts/validate_benchmark.py", "--benchmark", "benchmark", "--json"],
      { cwd: process.cwd(), maxBuffer: 16 * 1024 * 1024, encoding: "utf8" },
    ));
  } catch (error: any) {
    throw new Error(`Benchmark artifact validation failed before inference: ${error?.stderr || errorMessage(error)}`);
  }
  const validation = JSON.parse(stdout) as { ok?: boolean; errors?: string[]; warnings?: string[] };
  if (validation.ok !== true) {
    throw new Error(`Benchmark artifact validation failed before inference: ${(validation.errors ?? []).join("; ")}`);
  }
  for (const warning of validation.warnings ?? []) console.warn(`benchmark warning: ${warning}`);
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

function promptCacheKey(inferenceCacheKey: string) {
  return `doc2md-${inferenceCacheKey.slice(0, 48)}`;
}

function usageWithCacheWrite(spec: ModelSpec, usage: any) {
  if (!spec.cacheWritePerMillion) return usage;
  if (Number.isFinite(usage?.inputTokenDetails?.cacheWriteTokens)) return usage;
  const input = Math.max(0, usage?.inputTokens ?? 0);
  const cached = Math.min(input, Math.max(0, usage?.inputTokenDetails?.cacheReadTokens ?? 0));
  return {
    ...usage,
    inputTokenDetails: {
      ...usage?.inputTokenDetails,
      cacheWriteTokens: input - cached,
    },
  };
}

async function packageLockHash() {
  return sha256(await readFile("package-lock.json"));
}

function specField(spec: string, field: string) {
  const escapedField = field.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = spec.match(new RegExp(`^${escapedField}\\s*:\\s*(.+)$`, "im"));
  return match?.[1]?.trim().replaceAll("`", "") || null;
}

async function reportCaseMetadata(cases: Array<ManifestCase & { spec: string }>) {
  return Promise.all(cases.map(async (testCase) => {
    const spec = await readFile(testCase.spec, "utf8");
    return {
      id: testCase.id,
      title: testCase.title,
      family: testCase.family,
      tags: testCase.tags,
      pages: testCase.pages ?? 0,
      purpose: specField(spec, "Purpose") ?? `Test faithful PDF-to-Markdown reconstruction for ${testCase.title}.`,
      sourceModality: specField(spec, "Source modality") ?? "Native PDF input; see the case tags for its evidence mix.",
    };
  }));
}

async function inferenceKey(spec: ModelSpec, testCase: ManifestCase, prompt: string) {
  const pdf = await readFile(testCase.pdf);
  return sha256(JSON.stringify({
    protocolVersion: inferenceProtocolVersion,
    ingestionMode,
    pdf: sha256(pdf),
    prompt: sha256(prompt),
    model: configuredModel(spec),
  }));
}

async function legacyInferenceKey(spec: ModelSpec, testCase: ManifestCase, prompt: string) {
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
      case: { id: testCase.id, title: testCase.title },
      evaluator: evaluatorSourceHash,
    }),
  );
}

function inferenceTelemetryIssue(prediction: string, inference: any): string | null {
  const outputTokens = inference?.usage?.outputTokens;
  const outputBytes = Buffer.byteLength(prediction, "utf8");
  if (!Number.isSafeInteger(outputTokens) || outputTokens < 0 || (outputBytes > 0 && outputTokens === 0)) {
    return `invalid reported output token count ${String(outputTokens)}`;
  }
  // Provider tokenizers differ, so this is deliberately a very loose integrity
  // bound rather than a local token estimate. Natural document Markdown in the
  // cache is normally around 2–5 UTF-8 bytes per token; a sustained ratio over
  // 16 indicates that the usage record and stored response cannot describe the
  // same provider call.
  if (outputBytes >= 4_096 && outputBytes / outputTokens > 16) {
    return `${outputBytes} output bytes cannot be reconciled with ${outputTokens} reported output tokens`;
  }
  return null;
}

async function loadCachedCase(modelId: string, testCase: ManifestCase, prompt: string, evaluatorSourceHash: string, draw = 1) {
  const directory = cacheDirectory(modelId, testCase.id, draw);
  const [prediction, rawInference, evaluation] = await Promise.all([
    readFile(path.join(directory, "prediction.md"), "utf8").catch(() => null),
    readJsonOrNull(path.join(directory, "inference.json")),
    readJsonOrNull(path.join(directory, "score.json")),
  ]);
  let inference = rawInference;
  if (prediction === null || !inference) return null;
  const telemetryIssue = inferenceTelemetryIssue(prediction, inference);
  if (telemetryIssue) {
    const slot = `${modelId}/${testCase.id}/draw-${draw}`;
    if (!reportedInvalidInferenceSlots.has(slot)) {
      reportedInvalidInferenceSlots.add(slot);
      console.warn(`${slot}: ignoring invalid inference cache (${telemetryIssue})`);
    }
    return null;
  }
  const [expectedInferenceKey, previousInferenceKey] = await Promise.all([
    inferenceKey(models[modelId]!, testCase, prompt),
    legacyInferenceKey(models[modelId]!, testCase, prompt),
  ]);
  if (inference.cacheKey !== expectedInferenceKey && inference.cacheKey !== previousInferenceKey) return null;
  if (inference.cacheKey === previousInferenceKey && previousInferenceKey !== expectedInferenceKey) {
    inference = {
      ...inference,
      cacheKey: expectedInferenceKey,
      cacheKeyMigration: {
        from: previousInferenceKey,
        migratedAt: new Date().toISOString(),
        reason: "Removed unrelated package-lock coupling from inference identity.",
      },
    };
    await writeJson(path.join(directory, "inference.json"), inference);
  }
  const expectedScoreKey = await scoreKey(testCase, prediction, evaluatorSourceHash);
  const validEvaluation = evaluation?.valid === true && Number.isFinite(evaluation.score);
  return {
    directory,
    prediction,
    inference,
    evaluation: validEvaluation && evaluation.cacheKey === expectedScoreKey ? evaluation : null,
    inferenceKey: expectedInferenceKey,
    scoreKey: expectedScoreKey,
  };
}

function errorMessage(error: unknown) {
  return error instanceof Error ? `${error.name}: ${error.message}` : String(error);
}

async function runCase(
  modelId: string,
  testCase: ManifestCase,
  prompt: string,
  evaluatorSourceHash: string,
  draw: number,
) {
  const spec = models[modelId]!;
  const directory = cacheDirectory(modelId, testCase.id, draw);
  await mkdir(directory, { recursive: true });
  let cached = await loadCachedCase(modelId, testCase, prompt, evaluatorSourceHash, draw);
  let prediction = cached?.prediction ?? null;
  let inference = cached?.inference ?? null;
  let inferenceSpent = 0;
  let evaluatorSpent = 0;

  if (prediction === null || !inference) {
    const pdf = await readFile(testCase.pdf);
    const outputLimit = spec.maxOutputTokens ?? maxOutputTokens;
    const startedAt = new Date();
    const started = performance.now();
    const requestInferenceKey = await inferenceKey(spec, testCase, prompt);
    const requestPromptCacheKey = promptCacheKey(requestInferenceKey);
    const response = await generateText({
      model: createModel(spec),
      messages: [{
        role: "user",
        content: [
          { type: "text", text: prompt },
          {
            type: "file",
            data: pdf,
            mediaType: "application/pdf",
            filename: `${testCase.id}.pdf`,
            ...(spec.provider === "openai" && spec.modelName.startsWith("gpt-5.6-") ? {
              providerOptions: {
                openai: { promptCacheBreakpoint: { mode: "explicit" as const } },
              },
            } : {}),
          },
        ],
      }],
      maxOutputTokens: outputLimit,
      maxRetries: 2,
      ...(spec.reasoning ? { reasoning: spec.reasoning } : {}),
      ...(spec.provider === "openai" ? {
        providerOptions: {
          openai: {
            promptCacheKey: requestPromptCacheKey,
            ...(spec.modelName.startsWith("gpt-5.6-") ? {
              promptCacheOptions: { mode: "explicit" as const, ttl: "30m" as const },
            } : {}),
          },
        },
      } : {}),
    });
    const usage = usageWithCacheWrite(spec, response.usage);
    prediction = response.text;
    inferenceSpent = calculateCost(spec, usage);
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
      usage,
      providerCache: {
        mode: spec.provider === "openai"
          ? spec.modelName.startsWith("gpt-5.6-") ? "explicit-prefix-30m" : "prompt-cache-key"
          : "implicit",
        key: spec.provider === "openai" ? requestPromptCacheKey : null,
        cacheReadTokens: usage?.inputTokenDetails?.cacheReadTokens ?? 0,
        cacheWriteTokens: usage?.inputTokenDetails?.cacheWriteTokens ?? 0,
      },
      costUsd: inferenceSpent,
      uncachedCostUsd: calculateUncachedCost(spec, usage),
      cacheKey: requestInferenceKey,
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
    if (!evaluation.valid || !Number.isFinite(evaluation.score)) {
      throw new Error(
        `${modelId} draw ${draw} ${testCase.id}: evaluator failed; ${evaluation.evaluator.errors?.join("; ") || "no diagnostic"}`,
      );
    }
  }

  const cacheStatus = inferenceSpent === 0 && evaluatorSpent === 0 ? "cached" : inferenceSpent === 0 ? "rescored" : "run";
  const providerCache = inferenceSpent > 0
    ? `; provider cache ${inference.usage?.inputTokenDetails?.cacheReadTokens ?? 0}/${inference.usage?.inputTokens ?? 0} input tokens`
    : "";
  console.log(`${modelId} draw ${draw} ${testCase.id}: ${evaluation.score === null ? "INVALID" : evaluation.score.toFixed(1)} (${cacheStatus}${providerCache})`);
  return {
    draw,
    caseId: testCase.id,
    title: testCase.title,
    score: evaluation.score as number | null,
    inferenceCostUsd: calculateUncachedCost(spec, inference.usage),
    actualInferenceCostUsd: Number.isFinite(inference.costUsd) ? inference.costUsd : calculateCost(spec, inference.usage),
    evaluatorCostUsd: evaluation.evaluator.costUsd ?? 0,
    incrementalCostUsd: inferenceSpent + evaluatorSpent,
    incrementalInferenceCostUsd: inferenceSpent,
    incrementalEvaluatorCostUsd: evaluatorSpent,
    cacheStatus,
    inputTokens: inference.usage?.inputTokens ?? 0,
    cacheReadTokens: inference.usage?.inputTokenDetails?.cacheReadTokens ?? 0,
    cacheWriteTokens: inference.usage?.inputTokenDetails?.cacheWriteTokens ?? 0,
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

async function collectMergedResults(
  manifest: { cases: ManifestCase[] },
  prompt: string,
  evaluatorSourceHash: string,
) {
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
          inferenceCostUsd: calculateUncachedCost(models[modelId]!, cached.inference.usage),
          actualInferenceCostUsd: Number.isFinite(cached.inference.costUsd)
            ? cached.inference.costUsd
            : calculateCost(models[modelId]!, cached.inference.usage),
          evaluatorCostUsd: cached.evaluation.evaluator.costUsd ?? 0,
          outputTokens: cached.inference.usage?.outputTokens ?? 0,
          inputTokens: cached.inference.usage?.inputTokens ?? 0,
          cacheReadTokens: cached.inference.usage?.inputTokenDetails?.cacheReadTokens ?? 0,
          cacheWriteTokens: cached.inference.usage?.inputTokenDetails?.cacheWriteTokens ?? 0,
          evaluatorInputTokens: cached.evaluation.evaluator?.usage?.inputTokens ?? 0,
          evaluatorCacheReadTokens: cached.evaluation.evaluator?.usage?.inputTokenDetails?.cacheReadTokens ?? 0,
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
        actualInferenceCostUsd: cases.reduce((sum, testCase) => sum + testCase.actualInferenceCostUsd, 0),
        evaluatorCostUsd: cases.reduce((sum, testCase) => sum + testCase.evaluatorCostUsd, 0),
        totalOutputTokens: cases.reduce((sum, testCase) => sum + testCase.outputTokens, 0),
        inputTokens: cases.reduce((sum, testCase) => sum + testCase.inputTokens, 0),
        cacheReadTokens: cases.reduce((sum, testCase) => sum + testCase.cacheReadTokens, 0),
        cacheWriteTokens: cases.reduce((sum, testCase) => sum + testCase.cacheWriteTokens, 0),
        evaluatorInputTokens: cases.reduce((sum, testCase) => sum + testCase.evaluatorInputTokens, 0),
        evaluatorCacheReadTokens: cases.reduce((sum, testCase) => sum + testCase.evaluatorCacheReadTokens, 0),
        inferenceSeconds: cases.reduce((sum, testCase) => sum + testCase.inferenceElapsedMs, 0) / 1_000,
        cases,
      });
    }
    if (draws.length === 0) {
      exclusions.push({ modelId, reason: "No complete draw has a valid score for the current scorer and corpus." });
      continue;
    }
    const resolvedModels = [...new Set(draws.flatMap((draw) => draw.cases.map((item: any) => item.resolvedModel)).filter(Boolean))];
    const resolvedEvaluators = [...new Set(draws.flatMap((draw) => draw.cases.map((item: any) => item.evaluatorResolvedModel)).filter(Boolean))];
    if (
      resolvedModels.length !== 1 ||
      resolvedEvaluators.length !== 1
    ) {
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
        actualInferenceCostUsd: mean(observations.map((observation) => observation.actualInferenceCostUsd)),
      };
    });
    const inferenceCostUsd = mean(draws.map((draw) => draw.inferenceCostUsd));
    const actualInferenceCostUsd = mean(draws.map((draw) => draw.actualInferenceCostUsd));
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
      normalizedInferenceCostUsd: inferenceCostUsd,
      actualInferenceCostUsd,
      evaluatorCostUsd,
      totalCostUsd: actualInferenceCostUsd + evaluatorCostUsd,
      cumulativeInferenceCostUsd: draws.reduce((sum, draw) => sum + draw.inferenceCostUsd, 0),
      cumulativeActualInferenceCostUsd: draws.reduce((sum, draw) => sum + draw.actualInferenceCostUsd, 0),
      cumulativeEvaluatorCostUsd: draws.reduce((sum, draw) => sum + draw.evaluatorCostUsd, 0),
      inputTokens: draws.reduce((sum, draw) => sum + draw.inputTokens, 0),
      cacheReadTokens: draws.reduce((sum, draw) => sum + draw.cacheReadTokens, 0),
      cacheWriteTokens: draws.reduce((sum, draw) => sum + draw.cacheWriteTokens, 0),
      cacheHitRate: draws.reduce((sum, draw) => sum + draw.inputTokens, 0) === 0 ? 0 :
        draws.reduce((sum, draw) => sum + draw.cacheReadTokens, 0) / draws.reduce((sum, draw) => sum + draw.inputTokens, 0),
      evaluatorInputTokens: draws.reduce((sum, draw) => sum + draw.evaluatorInputTokens, 0),
      evaluatorCacheReadTokens: draws.reduce((sum, draw) => sum + draw.evaluatorCacheReadTokens, 0),
      evaluatorCacheHitRate: draws.reduce((sum, draw) => sum + draw.evaluatorInputTokens, 0) === 0 ? 0 :
        draws.reduce((sum, draw) => sum + draw.evaluatorCacheReadTokens, 0) /
          draws.reduce((sum, draw) => sum + draw.evaluatorInputTokens, 0),
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

async function runBenchmarkCore(requestedModelIds: string[], requestedRuns = 1) {
  await validateCorpusArtifacts();
  const { manifest } = await loadBenchmarkManifest();
  await auditBenchmark();
  const [promptFile, evaluatorSource, evaluatorClientSource] = await Promise.all([
    readFile(promptPath, "utf8"),
    readFile("src/evaluator.ts"),
    readFile("src/evaluator-client.ts"),
  ]);
  const prompt = promptFile.trimEnd();
  const { pricingVersion: _pricingVersion, ...scoringConfiguration } = evaluatorConfiguration();
  const evaluatorSourceHash = sha256(JSON.stringify({
    evaluatorSource: sha256(evaluatorSource),
    evaluatorClientSource: sha256(evaluatorClientSource),
    configuration: scoringConfiguration,
  }));
  const modelIds = requestedModelIds.length > 0 ? requestedModelIds : [...new Set([...defaultModelIds, ...(await cachedModelIds())])];
  let incrementalInferenceSpendUsd = 0;
  let incrementalEvaluatorSpendUsd = 0;

  for (const modelId of modelIds) {
    console.log(`\n${modelId}: ensuring ${requestedRuns} draw slot${requestedRuns === 1 ? "" : "s"} × ${manifest.cases.length} cases`);
    const cases = (await Promise.all(manifest.cases.map(async (testCase) => {
      const drawNumbers = Array.from({ length: requestedRuns }, (_, index) => index + 1);
      const cachedSlots = await Promise.all(drawNumbers.map((draw) =>
        loadCachedCase(modelId, testCase as ManifestCase, prompt, evaluatorSourceHash, draw),
      ));
      if (cachedSlots.every(Boolean)) {
        return Promise.all(drawNumbers.map((draw) => runCase(
          modelId,
          testCase as ManifestCase,
          prompt,
          evaluatorSourceHash,
          draw,
        )));
      }

      // When inference is missing, one provider call warms the repeated-input
      // cache before the remaining missing draws fan out. Existing slots do
      // not need that serialization.
      const draws = [];
      for (let draw = 1; draw <= requestedRuns; draw += 1) {
        const result = await runCase(
          modelId,
          testCase as ManifestCase,
          prompt,
          evaluatorSourceHash,
          draw,
        );
        draws.push(result);
        if (result.incrementalInferenceCostUsd > 0 && draw < requestedRuns) {
          draws.push(...await Promise.all(
            Array.from({ length: requestedRuns - draw }, (_, offset) =>
              runCase(
                modelId,
                testCase as ManifestCase,
                prompt,
                evaluatorSourceHash,
                draw + offset + 1,
              ),
            ),
          ));
          break;
        }
      }
      return draws;
    }))).flat();
    incrementalInferenceSpendUsd += cases.reduce((sum, testCase) => sum + testCase.incrementalInferenceCostUsd, 0);
    incrementalEvaluatorSpendUsd += cases.reduce((sum, testCase) => sum + testCase.incrementalEvaluatorCostUsd, 0);
  }

  const collected = await collectMergedResults(
    manifest as { cases: ManifestCase[] },
    prompt,
    evaluatorSourceHash,
  );
  const mergedModels = collected.models;
  const reportCases = await reportCaseMetadata(manifest.cases);
  const manifestHash = sha256(await readFile("benchmark/manifest.json"));
  const promptHash = sha256(prompt);
  const summary = {
    name: manifest.name,
    description: (manifest as typeof manifest & { description?: string }).description ?? "A benchmark for faithful PDF-to-Markdown reconstruction.",
    generatedAt: new Date().toISOString(),
    caseCount: manifest.cases.length,
    pageCount: manifest.pageCount,
    cases: reportCases,
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
    costMethodology: {
      comparison: "Every input token is priced at the model's uncached list rate; output uses list price.",
      actualSpend: "Provider-reported cache reads and configured cache-write rates are applied separately.",
      comparisonField: "models[].inferenceCostUsd",
      actualSpendField: "models[].actualInferenceCostUsd",
    },
    exclusions: collected.exclusions,
    incrementalSpendUsd: incrementalInferenceSpendUsd + incrementalEvaluatorSpendUsd,
    incrementalInferenceSpendUsd,
    incrementalEvaluatorSpendUsd,
    totalCostUsd: mergedModels.reduce(
      (sum, model) => sum + model.cumulativeActualInferenceCostUsd + model.cumulativeEvaluatorCostUsd,
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
  console.table(mergedModels.map((model) => ({
    model: model.modelId,
    draws: model.drawCount,
    score: model.score,
    meanUncachedInferenceCostUsd: model.inferenceCostUsd,
    meanActualInferenceSpendUsd: model.actualInferenceCostUsd,
  })));
  console.log(`Incremental model inference spend: $${incrementalInferenceSpendUsd.toFixed(6)}`);
  console.log("Report: reports/index.html");
  return summary;
}

export async function runBenchmark(requestedModelIds: string[], requestedRuns = 1) {
  try {
    return await runBenchmarkCore(requestedModelIds, requestedRuns);
  } finally {
    await disposeEvaluatorCaches();
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const options = parseOptions(process.argv.slice(2));
  await runBenchmark(options.modelIds, options.runs);
}
