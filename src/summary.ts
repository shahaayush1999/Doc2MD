import { access, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildBenchmarkFingerprint } from "./benchmarkFingerprint.js";
import { sha256, stableJson } from "./cache.js";
import { buildCohortArtifactFingerprint } from "./cohortFingerprint.js";
import {
  aggregateSampleFirst,
  sampleStddev as aggregationSampleStddev,
  type AggregationCase,
  type AggregationSample,
} from "./aggregation.js";
export { aggregateSampleFirst, sampleStddev, type AggregationCase, type AggregationSample } from "./aggregation.js";
import {
  buildRunContext,
  buildRunCacheExpectation,
  modelConfigFingerprint,
  modelPricingFingerprint,
  models,
  priceReport,
  prompt,
  readCurrentCachedRun,
  runCacheKey,
  samplesPerModelCase,
} from "./run.js";
import { acquireSampleLock, atomicWriteJson } from "./runRuntime.js";
import { loadBenchmarkManifest } from "./manifest.js";
import {
  normalizeRunOutcome,
  evaluatorPriceReport,
  parseFactFile,
  scoreAtomicRegions,
  scoringCacheKey,
  scoringContractFingerprint,
  scoringContractVersion,
  validateJudgeResult,
  type FactFile,
  type ManifestCase,
} from "./score.js";

type Manifest = {
  name?: string;
  suite?: string;
  scoreName?: string;
  inputProtocol?: string;
  cases: ManifestCase[];
};

export type ScoreArtifact = {
  caseId: string;
  modelId: string;
  sample?: string | null;
  suite?: string;
  manifestPath?: string;
  inputProtocol?: string;
  score: number | null;
  valid?: boolean;
  modelCallFailed?: boolean;
  evaluatorFailure?: boolean;
  scoringContractVersion?: string;
  scoringContractFingerprint?: string;
  runCache?: Record<string, unknown> | null;
  atomicScore?: unknown;
  judgeResult?: unknown;
  finishReason?: unknown;
  scorer?: {
    status?: string;
    estimatedCostUsd?: number;
    elapsedMs?: number;
    attempts?: number;
    errors?: unknown;
    judgeReused?: boolean;
    usage?: { inputTokens?: number; outputTokens?: number; totalTokens?: number } | null;
    pricing?: Record<string, unknown>;
    resolved?: Record<string, unknown> | null;
    cache?: Record<string, unknown> & { scoreKey?: string; judgeKey?: string };
  };
};

export type ScoreArtifactExpectation = {
  caseId: string;
  modelId: string;
  sample: string;
  suite: string;
  manifestPath: string;
  inputProtocol: string;
  modelCallFailed: boolean;
  finishReason?: unknown;
  runCache: unknown;
  scoreCache: Record<string, unknown> & { scoreKey: string; judgeKey: string };
  prediction: string;
};

export type EvaluatorValidationStatus = "valid" | "failed" | "missing_invalid" | "not_required";
export type ScoreArtifactValidationKind = "evaluator_valid" | "evaluator_failed" | "model_failure" | "missing_invalid";

export type ScoreArtifactValidation = {
  kind: ScoreArtifactValidationKind;
  evaluatorStatus: EvaluatorValidationStatus;
  valid: boolean;
  score: number | null;
  reason?: string;
  artifact: ScoreArtifact | null;
};

export type AtomicDiagnosticRow = {
  key: string;
  regionCount: number;
  totalBudget: number;
  score: number;
  rawScore: number;
};

export type AtomicDiagnostics = {
  byPrimaryAxis: AtomicDiagnosticRow[];
  byModality: AtomicDiagnosticRow[];
};

export type DiagnosticAggregationSample = {
  sample: string;
  diagnostics: AtomicDiagnostics | null;
};

export type DiagnosticAggregationCase = {
  caseId: string;
  samples: DiagnosticAggregationSample[];
};

export type DiagnosticSampleScore = {
  sample: string;
  score: number;
  rawScore: number;
};

export type DiagnosticAggregate = {
  key: string;
  caseCount: number;
  regionCount: number;
  totalBudget: number;
  score: number;
  rawScore: number;
  sampleScores: DiagnosticSampleScore[];
  scoreStddev: number | null;
  scoreMin: number | null;
  scoreMax: number | null;
};

export type SummaryDiagnostics = {
  aggregation: "evidence_budget_sample_first";
  complete: boolean;
  byPrimaryAxis: DiagnosticAggregate[];
  byModality: DiagnosticAggregate[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function canonicalJson(value: unknown): string | null {
  try {
    const serialized = JSON.stringify(value);
    return serialized === undefined ? null : stableJson(JSON.parse(serialized));
  } catch {
    return null;
  }
}

function exactJsonEqual(left: unknown, right: unknown): boolean {
  const leftJson = canonicalJson(left);
  return leftJson !== null && leftJson === canonicalJson(right);
}

function nonNegativeFinite(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value >= 0;
}

function validEvaluatorTelemetry(scorer: ScoreArtifact["scorer"]): boolean {
  if (!scorer || !nonNegativeFinite(scorer.estimatedCostUsd) || !nonNegativeFinite(scorer.elapsedMs)) return false;
  if (!Number.isInteger(scorer.attempts) || (scorer.attempts ?? -1) < 0) return false;
  if (!Array.isArray(scorer.errors) || !scorer.errors.every((error) => typeof error === "string")) return false;
  if (scorer.usage !== null) {
    if (!isRecord(scorer.usage)) return false;
    if (![scorer.usage.inputTokens, scorer.usage.outputTokens, scorer.usage.totalTokens].every(nonNegativeFinite)) return false;
  }
  const currentPricing = evaluatorPriceReport(scorer.usage);
  return scorer.estimatedCostUsd === currentPricing.estimatedCostUsd && exactJsonEqual(scorer.pricing, currentPricing);
}

export function validateCurrentScoreArtifact(
  facts: FactFile,
  value: unknown,
  expected: ScoreArtifactExpectation,
): ScoreArtifactValidation {
  const invalid = (reason: string, artifact: ScoreArtifact | null = null): ScoreArtifactValidation => ({
    kind: "missing_invalid",
    evaluatorStatus: expected.modelCallFailed ? "not_required" : "missing_invalid",
    valid: false,
    score: null,
    reason,
    artifact,
  });

  if (!isRecord(value)) return invalid("missing score artifact");
  const artifact = value as ScoreArtifact;
  if (artifact.caseId !== expected.caseId || artifact.modelId !== expected.modelId || artifact.sample !== expected.sample) {
    return invalid("score identity mismatch", artifact);
  }
  if (artifact.suite !== expected.suite || artifact.manifestPath !== expected.manifestPath || artifact.inputProtocol !== expected.inputProtocol) {
    return invalid("score run-context mismatch", artifact);
  }
  if (artifact.finishReason !== expected.finishReason) return invalid("score finish reason does not match run artifact", artifact);
  if (!exactJsonEqual(artifact.runCache, expected.runCache)) return invalid("score references a stale or altered model run cache", artifact);
  if (artifact.scoringContractVersion !== scoringContractVersion || artifact.scoringContractFingerprint !== scoringContractFingerprint) {
    return invalid("scoring contract fingerprint is stale", artifact);
  }
  if (!artifact.scorer?.cache) return invalid("missing scorer cache identity", artifact);
  if (
    artifact.scorer.cache.scoreKey !== expected.scoreCache.scoreKey ||
    artifact.scorer.cache.judgeKey !== expected.scoreCache.judgeKey ||
    !exactJsonEqual(artifact.scorer.cache, expected.scoreCache)
  ) {
    return invalid("score cache fingerprint is stale or altered", artifact);
  }
  if (artifact.modelCallFailed !== expected.modelCallFailed) return invalid("model failure state does not match run artifact", artifact);

  if (expected.modelCallFailed) {
    if (
      artifact.valid !== true ||
      artifact.evaluatorFailure !== false ||
      artifact.score !== 0 ||
      artifact.scorer.status !== "not_run_model_failure" ||
      artifact.scorer.attempts !== 0 ||
      !Array.isArray(artifact.scorer.errors) ||
      artifact.scorer.errors.length !== 0 ||
      artifact.scorer.elapsedMs !== 0 ||
      artifact.scorer.estimatedCostUsd !== 0 ||
      artifact.scorer.usage !== null ||
      artifact.scorer.judgeReused !== false
    ) {
      return invalid("model failure must be a valid zero score with a not-run evaluator envelope", artifact);
    }
    try {
      const judgeResult = validateJudgeResult(facts, artifact.judgeResult, expected.prediction);
      if (judgeResult.leafResults.some((leaf) => leaf.status !== "missing") || judgeResult.unsupportedClaims.length !== 0) {
        return invalid("model failure judgment must mark every leaf missing without unsupported claims", artifact);
      }
      const recomputed = scoreAtomicRegions(facts, judgeResult, expected.prediction);
      if (recomputed.score !== 0 || artifact.score !== recomputed.score) {
        return invalid("model failure score does not match recomputed atomic score", artifact);
      }
      if (!exactJsonEqual(artifact.atomicScore, recomputed)) return invalid("stored atomic score does not match recomputed atomic score", artifact);
    } catch {
      return invalid("model failure judgment is invalid", artifact);
    }
    return { kind: "model_failure", evaluatorStatus: "not_required", valid: true, score: 0, artifact };
  }

  if (artifact.scorer.status === "failed") {
    if (
      artifact.valid !== false ||
      artifact.evaluatorFailure !== true ||
      artifact.score !== null ||
      artifact.atomicScore !== null ||
      artifact.judgeResult !== null ||
      artifact.scorer.judgeReused !== false ||
      !validEvaluatorTelemetry(artifact.scorer) ||
      (artifact.scorer.attempts ?? 0) < 1
    ) {
      return invalid("evaluator failure envelope is invalid", artifact);
    }
    return {
      kind: "evaluator_failed",
      evaluatorStatus: "failed",
      valid: false,
      score: null,
      reason: "evaluator failure",
      artifact,
    };
  }

  if (
    artifact.scorer.status !== "valid" ||
    artifact.valid !== true ||
    artifact.evaluatorFailure !== false ||
    !validEvaluatorTelemetry(artifact.scorer) ||
    !isRecord(artifact.scorer.resolved) ||
    typeof artifact.scorer.resolved.modelId !== "string" ||
    artifact.scorer.resolved.modelId.length === 0
  ) {
    return invalid("successful model call lacks a valid evaluator envelope", artifact);
  }
  if (typeof artifact.score !== "number" || !Number.isFinite(artifact.score) || artifact.score < 0 || artifact.score > 100) {
    return invalid("stored score is outside [0, 100]", artifact);
  }
  try {
    const judgeResult = validateJudgeResult(facts, artifact.judgeResult, expected.prediction);
    const recomputed = scoreAtomicRegions(facts, judgeResult, expected.prediction);
    if (!Number.isFinite(recomputed.score) || recomputed.score < 0 || recomputed.score > 100) {
      return invalid("recomputed score is outside [0, 100]", artifact);
    }
    if (artifact.score !== recomputed.score) return invalid("stored score does not match recomputed atomic score", artifact);
    if (!exactJsonEqual(artifact.atomicScore, recomputed)) return invalid("stored atomic score does not match recomputed atomic score", artifact);
    return { kind: "evaluator_valid", evaluatorStatus: "valid", valid: true, score: recomputed.score, artifact };
  } catch {
    return invalid("cached judge result is invalid", artifact);
  }
}

function mean(values: number[]): number {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function round(value: number, digits = 1): number {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function validAtomicDiagnosticRow(value: AtomicDiagnosticRow): boolean {
  return (
    typeof value.key === "string" &&
    value.key.length > 0 &&
    Number.isInteger(value.regionCount) &&
    value.regionCount > 0 &&
    Number.isFinite(value.totalBudget) &&
    value.totalBudget > 0 &&
    Number.isFinite(value.score) &&
    value.score >= 0 &&
    value.score <= 100 &&
    Number.isFinite(value.rawScore)
  );
}

function uniqueDiagnosticRows(rows: AtomicDiagnosticRow[]): boolean {
  return rows.every(validAtomicDiagnosticRow) && new Set(rows.map((row) => row.key)).size === rows.length;
}

function aggregateDiagnosticDimension(
  cases: DiagnosticAggregationCase[],
  expectedSampleIds: string[],
  dimension: keyof AtomicDiagnostics,
): DiagnosticAggregate[] | null {
  const perSample = new Map<
    string,
    Map<string, { caseCount: number; regionCount: number; totalBudget: number; weightedRawScore: number }>
  >();

  for (const sampleId of expectedSampleIds) {
    const byKey = new Map<string, { caseCount: number; regionCount: number; totalBudget: number; weightedRawScore: number }>();
    for (const testCase of cases) {
      const matches = testCase.samples.filter((sample) => sample.sample === sampleId);
      if (matches.length !== 1 || !matches[0]!.diagnostics) return null;
      const rows = matches[0]!.diagnostics![dimension];
      if (!Array.isArray(rows) || !uniqueDiagnosticRows(rows)) return null;
      for (const row of rows) {
        const current = byKey.get(row.key) ?? { caseCount: 0, regionCount: 0, totalBudget: 0, weightedRawScore: 0 };
        current.caseCount += 1;
        current.regionCount += row.regionCount;
        current.totalBudget += row.totalBudget;
        current.weightedRawScore += row.rawScore * row.totalBudget;
        byKey.set(row.key, current);
      }
    }
    perSample.set(sampleId, byKey);
  }

  const firstKeys = [...(perSample.get(expectedSampleIds[0]!)?.keys() ?? [])].sort();
  if (firstKeys.length === 0) return null;
  if (
    expectedSampleIds.some((sampleId) => {
      const keys = [...(perSample.get(sampleId)?.keys() ?? [])].sort();
      return keys.length !== firstKeys.length || keys.some((key, index) => key !== firstKeys[index]);
    })
  ) {
    return null;
  }

  return firstKeys.map((key) => {
    const sampleScores = expectedSampleIds.map((sample) => {
      const item = perSample.get(sample)!.get(key)!;
      const rawScore = item.weightedRawScore / item.totalBudget;
      return {
        sample,
        score: round(Math.max(0, Math.min(100, rawScore)), 6),
        rawScore: round(rawScore, 6),
      };
    });
    const metadata = expectedSampleIds.map((sample) => perSample.get(sample)!.get(key)!);
    const first = metadata[0]!;
    if (
      metadata.some(
        (item) =>
          item.caseCount !== first.caseCount || item.regionCount !== first.regionCount || item.totalBudget !== first.totalBudget,
      )
    ) {
      throw new Error(`Diagnostic evidence metadata changed across sample slots for ${dimension}:${key}.`);
    }
    const scores = sampleScores.map((sample) => sample.score);
    const rawScores = sampleScores.map((sample) => sample.rawScore);
    const hasObservedVariability = scores.length > 1;
    return {
      key,
      caseCount: first.caseCount,
      regionCount: first.regionCount,
      totalBudget: first.totalBudget,
      score: round(mean(scores), 6),
      rawScore: round(mean(rawScores), 6),
      sampleScores,
      scoreStddev: hasObservedVariability ? round(aggregationSampleStddev(scores)!, 6) : null,
      scoreMin: hasObservedVariability ? round(Math.min(...scores), 6) : null,
      scoreMax: hasObservedVariability ? round(Math.max(...scores), 6) : null,
    };
  });
}

/**
 * Build diagnostic slices from already-validated atomic scores. These slices do not
 * contribute to the official equal-case benchmark score: within each sample slot,
 * signed region utility is weighted only by the evidence budget for that slice.
 */
export function aggregateDiagnosticSampleFirst(
  cases: DiagnosticAggregationCase[],
  expectedSampleIds: string[],
): SummaryDiagnostics {
  const expectedSampleIdSet = new Set(expectedSampleIds);
  const cohortShapeIsValid =
    cases.length > 0 &&
    expectedSampleIds.length > 0 &&
    expectedSampleIdSet.size === expectedSampleIds.length &&
    cases.every(
      (testCase) =>
        testCase.samples.length === expectedSampleIds.length &&
        new Set(testCase.samples.map((sample) => sample.sample)).size === expectedSampleIds.length &&
        testCase.samples.every((sample) => expectedSampleIdSet.has(sample.sample) && sample.diagnostics !== null),
    );
  if (!cohortShapeIsValid) {
    return {
      aggregation: "evidence_budget_sample_first",
      complete: false,
      byPrimaryAxis: [],
      byModality: [],
    };
  }

  const byPrimaryAxis = aggregateDiagnosticDimension(cases, expectedSampleIds, "byPrimaryAxis");
  const byModality = aggregateDiagnosticDimension(cases, expectedSampleIds, "byModality");
  return {
    aggregation: "evidence_budget_sample_first",
    complete: byPrimaryAxis !== null && byModality !== null,
    byPrimaryAxis: byPrimaryAxis ?? [],
    byModality: byModality ?? [],
  };
}

async function exists(filePath: string) {
  try {
    await access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function readJsonIfExists(filePath: string) {
  if (!(await exists(filePath))) return null;
  try {
    return JSON.parse(await readFile(filePath, "utf-8")) as any;
  } catch {
    return null;
  }
}

function expectedSampleIds() {
  return Array.from({ length: samplesPerModelCase }, (_, index) => String(index + 1).padStart(3, "0"));
}

export async function deriveModelSummary(
  modelId: string,
  options: { manifestPath?: string; lockSamples?: boolean } = {},
) {
  const runRoot = path.join("runs", modelId);
  const manifestPath = options.manifestPath ?? "benchmark/manifest.json";
  const manifest = (await loadBenchmarkManifest(manifestPath)).manifest as Manifest;
  const spec = models[modelId];
  if (!spec) throw new Error(`Unknown model ${modelId}. Options: ${Object.keys(models).join(", ")}`);
  const context = await buildRunContext(spec, manifest as any, manifestPath);
  const suite = manifest.suite ?? "official";
  const fingerprint = await buildBenchmarkFingerprint({
    manifestPath,
    promptHash: sha256(prompt),
    scoringContractFingerprint,
  });
  const cohortArtifactFingerprintBefore = await buildCohortArtifactFingerprint(
    modelId,
    suite,
    manifest.cases,
    samplesPerModelCase,
  );
  const sampleIds = expectedSampleIds();
  const aggregationCases: AggregationCase[] = [];
  const caseDetails: any[] = [];
  const observedResults: any[] = [];
  const validatedEvaluatorArtifacts: ScoreArtifact[] = [];
  const artifactValidations: ScoreArtifactValidation[] = [];

  for (const testCase of manifest.cases) {
    if (!testCase.facts) throw new Error(`Case ${testCase.id} has no facts path.`);
    const facts = parseFactFile(JSON.parse(await readFile(testCase.facts, "utf-8")), {
      caseId: testCase.id,
      pages: testCase.pages,
    });
    const samples: AggregationSample[] = [];
    const detailSamples: any[] = [];

    for (const sample of sampleIds) {
      const sampleDir = path.join(runRoot, testCase.id, "samples", sample);
      const resultPath = path.join(sampleDir, "result.json");
      const predictionPath = path.join(sampleDir, "prediction.md");
      const scorePath = path.join(sampleDir, "score.json");
      const snapshotLock = options.lockSamples ? await acquireSampleLock(path.join(sampleDir, ".run.lock")) : null;
      try {
      const activeRun = await runCacheKey(testCase as any, spec, context, sample);
      const result = await readCurrentCachedRun(
        resultPath,
        predictionPath,
        buildRunCacheExpectation(testCase as any, spec, context, sample, activeRun),
      );
      if (!result) {
        samples.push({ sample, score: null, valid: false, reason: "missing, stale, or integrity-invalid model result" });
        detailSamples.push({
          sample,
          score: null,
          valid: false,
          reason: "missing, stale, or integrity-invalid model result",
          diagnostics: null,
        });
        continue;
      }

      observedResults.push(result);
      const modelCallFailed = normalizeRunOutcome(result).kind === "model_failure";
      const prediction = await readFile(predictionPath, "utf-8");
      const expectedCache = await scoringCacheKey(testCase, predictionPath, result);
      const rawScore = await readJsonIfExists(scorePath);
      const validation = validateCurrentScoreArtifact(facts, rawScore, {
        caseId: testCase.id,
        modelId,
        sample,
        suite: context.suite,
        manifestPath: context.manifestPath,
        inputProtocol: context.inputProtocol,
        modelCallFailed,
        finishReason: result.finishReason,
        runCache: result.cache,
        scoreCache: expectedCache,
        prediction,
      });
      artifactValidations.push(validation);
      if ((validation.evaluatorStatus === "valid" || validation.evaluatorStatus === "failed") && validation.artifact) {
        validatedEvaluatorArtifacts.push(validation.artifact);
      }
      const diagnostics =
        validation.valid && validation.artifact
          ? ((validation.artifact.atomicScore as ReturnType<typeof scoreAtomicRegions>).diagnostics as AtomicDiagnostics)
          : null;
      samples.push({
        sample,
        score: validation.score,
        valid: validation.valid,
        modelCallFailed,
        evaluatorFailure: validation.evaluatorStatus === "failed",
        evaluatorMissingInvalid: validation.evaluatorStatus === "missing_invalid",
        evaluatorStatus: validation.evaluatorStatus,
        reason: validation.reason,
      });
      detailSamples.push({
        sample,
        score: validation.score,
        valid: validation.valid,
        reason: validation.reason,
        modelCallFailed,
        evaluatorFailure: validation.evaluatorStatus === "failed",
        evaluatorMissingInvalid: validation.evaluatorStatus === "missing_invalid",
        evaluatorStatus: validation.evaluatorStatus,
        scoreArtifactKind: validation.kind,
        finishReason: result.finishReason ?? "unknown",
        error: result.error,
        elapsedMs: result.elapsedMs ?? 0,
        costUsd: priceReport(spec, result.usage).estimatedCostUsd,
        inputTokens: result.usage?.inputTokens ?? 0,
        outputTokens: result.usage?.outputTokens ?? 0,
        logicalGenerationCalls: result.inferenceAttempt.logicalGenerationCalls,
        transportRequestAttempts: result.inferenceAttempt.transportRequestAttempts,
        diagnostics,
      });
      } finally {
        if (snapshotLock) await snapshotLock.release();
      }
    }

    aggregationCases.push({ caseId: testCase.id, samples });
    caseDetails.push({ testCase, samples: detailSamples });
  }

  const aggregate = aggregateSampleFirst(aggregationCases, sampleIds);
  const diagnostics = aggregateDiagnosticSampleFirst(
    caseDetails.map(({ testCase, samples }) => ({
      caseId: testCase.id,
      samples: samples.map((sample: any) => ({ sample: sample.sample, diagnostics: sample.diagnostics ?? null })),
    })),
    sampleIds,
  );
  const aggregateByCase = new Map(aggregate.caseAggregates.map((item) => [item.caseId, item]));
  const caseScores = caseDetails.map(({ testCase, samples }) => {
    const scoreAggregate = aggregateByCase.get(testCase.id)!;
    const current = samples.filter((sample: any) => sample.valid);
    const observed = samples.filter((sample: any) => sample.finishReason !== undefined);
    return {
      caseId: testCase.id,
      title: testCase.title,
      family: testCase.family,
      tags: testCase.tags ?? [],
      pages: testCase.pages ?? 1,
      samples: current.length,
      expectedSamples: samplesPerModelCase,
      complete: scoreAggregate.complete,
      score: scoreAggregate.score === null ? null : round(scoreAggregate.score, 6),
      scoreMin: scoreAggregate.scoreMin === null ? null : round(scoreAggregate.scoreMin, 6),
      scoreMax: scoreAggregate.scoreMax === null ? null : round(scoreAggregate.scoreMax, 6),
      scoreStddev: scoreAggregate.scoreStddev === null ? null : round(scoreAggregate.scoreStddev, 6),
      sampleScores: samples.map((sample: any) => ({
        sample: sample.sample,
        score: sample.score,
        valid: sample.valid,
        reason: sample.reason,
        modelCallFailed: sample.modelCallFailed,
        evaluatorFailure: sample.evaluatorFailure,
        evaluatorMissingInvalid: sample.evaluatorMissingInvalid,
        evaluatorStatus: sample.evaluatorStatus,
        scoreArtifactKind: sample.scoreArtifactKind,
      })),
      modelFailureCount: samples.filter((sample: any) => sample.modelCallFailed).length,
      evaluatorValidCount: samples.filter((sample: any) => sample.evaluatorStatus === "valid").length,
      evaluatorFailureCount: samples.filter((sample: any) => sample.evaluatorFailure).length,
      evaluatorMissingInvalidCount: samples.filter((sample: any) => sample.evaluatorStatus === "missing_invalid").length,
      elapsedMs: observed.length === 0 ? 0 : Math.round(mean(observed.map((sample: any) => sample.elapsedMs))),
      costUsd: observed.length === 0 ? 0 : round(mean(observed.map((sample: any) => sample.costUsd)), 6),
      inputTokens: observed.length === 0 ? 0 : Math.round(mean(observed.map((sample: any) => sample.inputTokens))),
      outputTokens: observed.length === 0 ? 0 : Math.round(mean(observed.map((sample: any) => sample.outputTokens))),
      logicalGenerationCalls: observed.reduce((sum: number, sample: any) => sum + (sample.logicalGenerationCalls ?? 0), 0),
      transportRequestAttempts: observed.reduce((sum: number, sample: any) => sum + (sample.transportRequestAttempts ?? 0), 0),
      transportRetryCount: observed.reduce(
        (sum: number, sample: any) => sum + Math.max(0, (sample.transportRequestAttempts ?? 0) - (sample.logicalGenerationCalls ?? 0)),
        0,
      ),
      transportRetriesAreCohortSamples: false as const,
      finishReasons: observed.map((sample: any) => ({ sample: sample.sample, finishReason: sample.finishReason, error: sample.error })),
    };
  });

  const modelFailureCount = observedResults.filter((result) => normalizeRunOutcome(result).kind === "model_failure").length;
  const evaluatorRequiredCount = observedResults.length - modelFailureCount;
  const evaluatorValidCount = artifactValidations.filter((validation) => validation.evaluatorStatus === "valid").length;
  const evaluatorFailureCount = artifactValidations.filter((validation) => validation.evaluatorStatus === "failed").length;
  const evaluatorMissingInvalidCount = artifactValidations.filter((validation) => validation.evaluatorStatus === "missing_invalid").length;
  const totalCostUsd = observedResults.reduce((sum, result) => sum + priceReport(spec, result.usage).estimatedCostUsd, 0);
  const totalElapsedMs = observedResults.reduce((sum, result) => sum + (result.elapsedMs ?? 0), 0);
  const totalInputTokens = observedResults.reduce((sum, result) => sum + (result.usage?.inputTokens ?? 0), 0);
  const totalOutputTokens = observedResults.reduce((sum, result) => sum + (result.usage?.outputTokens ?? 0), 0);
  const totalTransportRequestAttempts = observedResults.reduce(
    (sum, result) => sum + result.inferenceAttempt.transportRequestAttempts,
    0,
  );
  const evaluatorCostUsd = validatedEvaluatorArtifacts.reduce(
    (sum, score) => sum + evaluatorPriceReport(score.scorer?.usage ?? null).estimatedCostUsd,
    0,
  );
  const evaluatorElapsedMs = validatedEvaluatorArtifacts.reduce((sum, score) => sum + (score.scorer?.elapsedMs ?? 0), 0);
  const evaluatorInputTokens = validatedEvaluatorArtifacts.reduce((sum, score) => sum + (score.scorer?.usage?.inputTokens ?? 0), 0);
  const evaluatorOutputTokens = validatedEvaluatorArtifacts.reduce((sum, score) => sum + (score.scorer?.usage?.outputTokens ?? 0), 0);
  const validSampleCount = aggregationCases.reduce((sum, testCase) => sum + testCase.samples.filter((sample) => sample.valid).length, 0);
  const incompleteCaseIds = caseScores.filter((testCase) => !testCase.complete).map((testCase) => testCase.caseId);
  const rawResolvedInferenceModelIds: unknown[] = observedResults.map((result) => result.providerMetadata?.resolved?.modelId);
  const rawResolvedEvaluatorModelIds: unknown[] = validatedEvaluatorArtifacts
    .filter((artifact) => artifact.scorer?.status === "valid")
    .map((artifact) => artifact.scorer?.resolved?.modelId);
  if (rawResolvedInferenceModelIds.some((value) => typeof value !== "string")) {
    throw new Error(`Inference cohort for ${modelId} contains missing or mixed resolved model identities.`);
  }
  if (rawResolvedEvaluatorModelIds.some((value) => typeof value !== "string")) {
    throw new Error(`Evaluator cohort for ${modelId} contains missing or mixed resolved model identities.`);
  }
  const resolvedInferenceModelIds = [...new Set(rawResolvedInferenceModelIds as string[])];
  const resolvedEvaluatorModelIds = [...new Set(rawResolvedEvaluatorModelIds as string[])];
  if (resolvedInferenceModelIds.length > 1) throw new Error(`Inference cohort for ${modelId} mixes resolved model revisions.`);
  if (resolvedEvaluatorModelIds.length > 1) throw new Error(`Evaluator cohort for ${modelId} mixes resolved model revisions.`);
  const cohortArtifactFingerprint = await buildCohortArtifactFingerprint(
    modelId,
    suite,
    manifest.cases,
    samplesPerModelCase,
  );
  if (cohortArtifactFingerprint !== cohortArtifactFingerprintBefore) {
    throw new Error(`Run/score artifacts changed while summarizing ${modelId}; retry after active work completes.`);
  }
  const finalBenchmarkFingerprint = await buildBenchmarkFingerprint({
    manifestPath,
    promptHash: sha256(prompt),
    scoringContractFingerprint,
  });
  if (finalBenchmarkFingerprint.benchmarkFingerprint !== fingerprint.benchmarkFingerprint) {
    throw new Error(`Benchmark artifacts changed while summarizing ${modelId}; retry after regeneration completes.`);
  }

  const summary = {
    modelId,
    provider: spec.provider,
    suite,
    manifestPath,
    benchmarkFingerprint: fingerprint.benchmarkFingerprint,
    inferenceBenchmarkFingerprint: context.inferenceBenchmarkFingerprint,
    inferenceProtocolFingerprint: context.protocolHash,
    modelConfigFingerprint: modelConfigFingerprint(spec),
    resolvedInferenceModelId: resolvedInferenceModelIds[0] ?? null,
    resolvedEvaluatorModelId: resolvedEvaluatorModelIds[0] ?? null,
    pricingFingerprint: modelPricingFingerprint(spec),
    pricingVersion: spec.pricingVersion,
    scoringContractVersion,
    scoringContractFingerprint,
    cohortArtifactFingerprint,
    benchmarkName: manifest.name ?? "Doc2MD",
    scoreName: manifest.scoreName ?? "Doc2MD Native PDF Score",
    inputProtocol: manifest.inputProtocol ?? "native_pdf",
    caseCount: manifest.cases.length,
    expectedCaseCount: manifest.cases.length,
    complete: aggregate.complete,
    missingCaseIds: incompleteCaseIds,
    invalidSamples: aggregate.invalidSamples,
    samplesPerModelCase,
    expectedSampleCount: manifest.cases.length * samplesPerModelCase,
    sampleCount: validSampleCount,
    score: aggregate.score === null ? null : round(aggregate.score),
    suiteSampleScores: aggregate.suiteSampleScores.map((item) => ({ sample: item.sample, score: round(item.score, 6) })),
    scoreStddev: aggregate.scoreStddev === null ? null : round(aggregate.scoreStddev, 6),
    scoreMin: aggregate.scoreMin === null ? null : round(aggregate.scoreMin, 6),
    scoreMax: aggregate.scoreMax === null ? null : round(aggregate.scoreMax, 6),
    scoreAggregation: "equal_case_sample_first" as const,
    costUsd: round(totalCostUsd, 6),
    meanCostUsdPerSample: observedResults.length === 0 ? 0 : round(totalCostUsd / observedResults.length, 6),
    totalElapsedMs,
    meanElapsedMsPerSample: observedResults.length === 0 ? 0 : Math.round(totalElapsedMs / observedResults.length),
    totalInputTokens,
    totalOutputTokens,
    meanOutputTokensPerSample: observedResults.length === 0 ? 0 : Math.round(totalOutputTokens / observedResults.length),
    modelCallCount: observedResults.length,
    logicalGenerationCallCount: observedResults.length,
    totalTransportRequestAttempts,
    transportRetryCount: Math.max(0, totalTransportRequestAttempts - observedResults.length),
    transportRetriesAreCohortSamples: false as const,
    modelFailureCount,
    modelFailureRate: observedResults.length === 0 ? 0 : round((modelFailureCount / observedResults.length) * 100, 2),
    evaluatorRequiredCount,
    evaluatorValidCount,
    evaluatorFailureCount,
    evaluatorMissingInvalidCount,
    evaluatorStatusCounts: {
      valid: evaluatorValidCount,
      failed: evaluatorFailureCount,
      missingInvalid: evaluatorMissingInvalidCount,
    },
    evaluatorFailureRate: evaluatorRequiredCount === 0 ? 0 : round((evaluatorFailureCount / evaluatorRequiredCount) * 100, 2),
    evaluatorMissingInvalidRate:
      evaluatorRequiredCount === 0 ? 0 : round((evaluatorMissingInvalidCount / evaluatorRequiredCount) * 100, 2),
    evaluatorCostUsd: round(evaluatorCostUsd, 6),
    evaluatorElapsedMs,
    evaluatorInputTokens,
    evaluatorOutputTokens,
    diagnostics,
    caseScores,
  };

  return summary;
}

export async function summarizeModel(modelId: string, options: { manifestPath?: string } = {}) {
  const summary = await deriveModelSummary(modelId, { manifestPath: options.manifestPath, lockSamples: true });
  const runRoot = path.join("runs", modelId);
  const suiteSummaryPath = path.join(runRoot, `summary.${summary.suite}.json`);
  await atomicWriteJson(suiteSummaryPath, summary);
  if (summary.suite === "official") await atomicWriteJson(path.join(runRoot, "summary.json"), summary);
  return summary;
}

function parseCli(argv: string[]) {
  let positionalModel: string | undefined;
  let model: string | undefined;
  let manifestPath: string | undefined;
  let sawOption = false;
  const seen = new Set<string>();
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index]!;
    if (!argument.startsWith("--")) {
      if (sawOption || positionalModel) throw new Error(`Unexpected positional argument ${argument}.`);
      positionalModel = argument;
      continue;
    }
    sawOption = true;
    const key = argument.slice(2);
    if (key !== "model" && key !== "manifest") throw new Error(`Unknown option --${key}.`);
    if (seen.has(key)) throw new Error(`Duplicate option --${key}.`);
    seen.add(key);
    const value = argv[index + 1];
    if (!value || value.startsWith("--")) throw new Error(`--${key} requires a value.`);
    if (key === "model") model = value;
    else manifestPath = value;
    index += 1;
  }
  if (positionalModel && model) throw new Error("Do not specify the model both positionally and with --model.");
  return { modelId: positionalModel ?? model ?? "vertex-gemini-3.1-flash-lite", manifestPath };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const cli = parseCli(process.argv.slice(2));
  const keepAlive = setInterval(() => undefined, 1_000);
  try {
    console.log(JSON.stringify(await summarizeModel(cli.modelId, { manifestPath: cli.manifestPath }), null, 2));
  } finally {
    clearInterval(keepAlive);
  }
}
