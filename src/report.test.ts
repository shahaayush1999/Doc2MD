import assert from "node:assert/strict";
import test from "node:test";
import {
  defaultReportModelIds,
  renderReport,
  validSummary,
  validateSummaryArithmetic,
  type Manifest,
  type Summary,
} from "./report.js";
import { scoringContractFingerprint } from "./score.js";

const manifest: Manifest = {
  name: "Doc2MD",
  suite: "official",
  scoreName: "Doc2MD Native PDF Score",
  inputProtocol: "native_pdf",
  pageCount: 1,
  cases: [
    {
      id: "case-a",
      title: "Case A",
      family: "fixture",
      tags: ["native-pdf"],
      pages: 1,
      pdf: "benchmark/cases/case-a/source.pdf",
      gold: "benchmark/cases/case-a/gold.md",
      spec: "benchmark/cases/case-a/spec.md",
      facts: "benchmark/cases/case-a/facts.json",
    },
  ],
};

const summary: Summary = {
  modelId: "openai-gpt-5-nano",
  provider: "openai",
  suite: "official",
  manifestPath: "benchmark/manifest.json",
  benchmarkFingerprint: "benchmark",
  inferenceBenchmarkFingerprint: "inference-benchmark",
  inferenceProtocolFingerprint: "protocol",
  modelConfigFingerprint: "model",
  resolvedInferenceModelId: "gpt-5-nano-test",
  resolvedEvaluatorModelId: "gemini-3.1-flash-lite",
  pricingFingerprint: "pricing",
  pricingVersion: "2026-07-10",
  scoringContractFingerprint: "scoring",
  cohortArtifactFingerprint: "cohort",
  benchmarkName: "Doc2MD",
  scoreName: "Doc2MD Native PDF Score",
  inputProtocol: "native_pdf",
  caseCount: 1,
  expectedCaseCount: 1,
  samplesPerModelCase: 1,
  sampleCount: 1,
  score: 50,
  suiteSampleScores: [{ sample: "001", score: 50 }],
  scoreStddev: null,
  scoreMin: null,
  scoreMax: null,
  scoreAggregation: "equal_case_sample_first",
  costUsd: 0.01,
  totalElapsedMs: 3000,
  totalInputTokens: 300,
  totalOutputTokens: 150,
  modelCallCount: 1,
  logicalGenerationCallCount: 1,
  totalTransportRequestAttempts: 1,
  transportRetryCount: 0,
  transportRetriesAreCohortSamples: false,
  modelFailureCount: 0,
  complete: true,
  missingCaseIds: [],
  invalidSamples: [],
  diagnostics: {
    aggregation: "evidence_budget_sample_first",
    complete: true,
    byPrimaryAxis: [
      {
        key: "precise_recall",
        caseCount: 1,
        regionCount: 1,
        totalBudget: 1,
        score: 50,
        rawScore: 50,
        sampleScores: [{ sample: "001", score: 50, rawScore: 50 }],
        scoreStddev: null,
        scoreMin: null,
        scoreMax: null,
      },
    ],
    byModality: [
      {
        key: "native_text",
        caseCount: 1,
        regionCount: 1,
        totalBudget: 1,
        score: 50,
        rawScore: 50,
        sampleScores: [{ sample: "001", score: 50, rawScore: 50 }],
        scoreStddev: null,
        scoreMin: null,
        scoreMax: null,
      },
    ],
  },
  caseScores: [
    {
      caseId: "case-a",
      title: "Case A",
      family: "fixture",
      tags: ["native-pdf"],
      pages: 1,
      samples: 1,
      expectedSamples: 1,
      complete: true,
      score: 50,
      scoreMin: null,
      scoreMax: null,
      scoreStddev: null,
      sampleScores: [{ sample: "001", score: 50, valid: true, modelCallFailed: false }],
      logicalGenerationCalls: 1,
      transportRequestAttempts: 1,
      transportRetryCount: 0,
      transportRetriesAreCohortSamples: false,
      finishReasons: [{ sample: "001", finishReason: "stop" }],
    },
  ],
};

test("report arithmetic validation recomputes case and full-suite values", () => {
  assert.equal(validateSummaryArithmetic(summary, manifest), null);
  const tampered = {
    ...summary,
    suiteSampleScores: summary.suiteSampleScores.map((sample) => ({ ...sample, score: 99 })),
  };
  assert.match(validateSummaryArithmetic(tampered, manifest)!, /full-suite sample arithmetic/);
});

test("report rendering is byte-deterministic for identical inputs", () => {
  assert.equal(renderReport(manifest, [summary]), renderReport(manifest, [summary]));
});

test("standalone reports default to only the two development anchors", () => {
  assert.deepEqual(defaultReportModelIds, ["openai-gpt-5-nano", "vertex-gemini-3.1-flash-lite"]);
});

test("report attributes observed separation by capability and modality without hiding signed utility", () => {
  const stronger: Summary = {
    ...summary,
    modelId: "vertex-gemini-3.1-flash-lite",
    provider: "google-vertex",
    score: 80,
    diagnostics: {
      ...summary.diagnostics,
      byPrimaryAxis: summary.diagnostics.byPrimaryAxis.map((row) => ({
        ...row,
        score: 80,
        rawScore: 90,
        sampleScores: [{ sample: "001", score: 80, rawScore: 90 }],
      })),
      byModality: summary.diagnostics.byModality.map((row) => ({
        ...row,
        score: 80,
        rawScore: 90,
        sampleScores: [{ sample: "001", score: 80, rawScore: 90 }],
      })),
    },
  };
  const html = renderReport(manifest, [summary, stronger]);
  assert.match(html, /Capability and Modality Diagnostics/);
  assert.match(html, /Precise Recall/);
  assert.match(html, /Native Text/);
  assert.match(html, /Observed spread/);
  assert.match(html, /raw 90\.0/);
  assert.match(html, /raw 40\.0/);
  assert.match(html, /same single stochastic draw/);
});

test("one-sample reports explicitly withhold variability and reliability claims", () => {
  const html = renderReport(manifest, [summary]);
  assert.match(html, /1 sample per model\/case/);
  assert.match(html, /SD and range are unavailable/);
  assert.match(html, /no repeatability or reliability claim/);
  assert.doesNotMatch(html, /\(50\.0–50\.0\)/);
  assert.match(html, /Transport retries are attempts to complete the same reserved logical draw/);
  assert.match(html, /<th class="num">Logical draws<\/th>/);
});

test("one-sample summary validation rejects manufactured zero variability", () => {
  const current = { ...summary, scoringContractFingerprint };
  assert.match(
    validSummary({ ...current, scoreStddev: 0, scoreMin: 50, scoreMax: 50 }, manifest, "benchmark")!,
    /variability fields do not match the sample protocol/,
  );
});

test("one-sample diagnostic validation rejects manufactured variability", () => {
  const current = { ...summary, scoringContractFingerprint };
  const tampered: Summary = {
    ...current,
    diagnostics: {
      ...current.diagnostics,
      byPrimaryAxis: current.diagnostics.byPrimaryAxis.map((row) => ({
        ...row,
        scoreStddev: 0,
        scoreMin: row.score,
        scoreMax: row.score,
      })),
    },
  };
  assert.match(validateSummaryArithmetic(tampered, manifest)!, /primary-axis diagnostic aggregate arithmetic/);
});

test("report freshness rejects a summary after cohort artifacts change", () => {
  const current = { ...summary, scoringContractFingerprint };
  const freshness = {
    inferenceBenchmarkFingerprint: current.inferenceBenchmarkFingerprint,
    inferenceProtocolFingerprint: current.inferenceProtocolFingerprint,
    modelConfigFingerprint: current.modelConfigFingerprint,
    pricingFingerprint: current.pricingFingerprint,
    pricingVersion: current.pricingVersion,
    cohortArtifactFingerprint: current.cohortArtifactFingerprint,
    artifactDerivedSummary: current,
  };
  assert.equal(validSummary(current, manifest, "benchmark", freshness), null);
  assert.match(
    validSummary(current, manifest, "benchmark", { ...freshness, cohortArtifactFingerprint: "changed" })!,
    /cohort artifacts are stale/,
  );
});

test("report rejects coherent score and aggregate tampering that diverges from score artifacts", () => {
  const current = { ...summary, scoringContractFingerprint };
  const freshness = {
    inferenceBenchmarkFingerprint: current.inferenceBenchmarkFingerprint,
    inferenceProtocolFingerprint: current.inferenceProtocolFingerprint,
    modelConfigFingerprint: current.modelConfigFingerprint,
    pricingFingerprint: current.pricingFingerprint,
    pricingVersion: current.pricingVersion,
    cohortArtifactFingerprint: current.cohortArtifactFingerprint,
    artifactDerivedSummary: current,
  };
  const tampered: Summary = {
    ...current,
    score: 90,
    scoreStddev: null,
    scoreMin: null,
    scoreMax: null,
    suiteSampleScores: current.suiteSampleScores.map((sample) => ({ ...sample, score: 90 })),
    caseScores: current.caseScores.map((caseScore) => ({
      ...caseScore,
      score: 90,
      scoreMin: null,
      scoreMax: null,
      scoreStddev: null,
      sampleScores: caseScore.sampleScores.map((sample) => ({ ...sample, score: 90 })),
    })),
  };
  assert.equal(validateSummaryArithmetic(tampered, manifest), null, "the tampering is deliberately arithmetically coherent");
  assert.match(validSummary(tampered, manifest, "benchmark", freshness)!, /does not match current run\/score artifacts/);
});

test("report rejects telemetry and finish-reason tampering that diverges from run artifacts", () => {
  const current = { ...summary, scoringContractFingerprint };
  const freshness = {
    inferenceBenchmarkFingerprint: current.inferenceBenchmarkFingerprint,
    inferenceProtocolFingerprint: current.inferenceProtocolFingerprint,
    modelConfigFingerprint: current.modelConfigFingerprint,
    pricingFingerprint: current.pricingFingerprint,
    pricingVersion: current.pricingVersion,
    cohortArtifactFingerprint: current.cohortArtifactFingerprint,
    artifactDerivedSummary: current,
  };
  const tampered: Summary = {
    ...current,
    costUsd: 0.000001,
    totalElapsedMs: 1,
    totalOutputTokens: 1,
    caseScores: current.caseScores.map((caseScore) => ({
      ...caseScore,
      finishReasons: caseScore.finishReasons?.map((finish, index) =>
        index === 0 ? { ...finish, finishReason: "length" } : finish,
      ),
    })),
  };
  assert.equal(validateSummaryArithmetic(tampered, manifest), null, "telemetry does not affect score arithmetic");
  assert.match(validSummary(tampered, manifest, "benchmark", freshness)!, /does not match current run\/score artifacts/);
});
