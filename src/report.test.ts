import assert from "node:assert/strict";
import test from "node:test";
import { renderReport, validSummary, validateSummaryArithmetic, type Manifest, type Summary } from "./report.js";
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
  samplesPerModelCase: 3,
  sampleCount: 3,
  score: 50,
  suiteSampleScores: [
    { sample: "001", score: 40 },
    { sample: "002", score: 50 },
    { sample: "003", score: 60 },
  ],
  scoreStddev: 10,
  scoreMin: 40,
  scoreMax: 60,
  scoreAggregation: "equal_case_sample_first",
  costUsd: 0.01,
  totalElapsedMs: 3000,
  totalInputTokens: 300,
  totalOutputTokens: 150,
  modelFailureCount: 0,
  complete: true,
  missingCaseIds: [],
  invalidSamples: [],
  caseScores: [
    {
      caseId: "case-a",
      title: "Case A",
      family: "fixture",
      tags: ["native-pdf"],
      pages: 1,
      samples: 3,
      expectedSamples: 3,
      complete: true,
      score: 50,
      scoreMin: 40,
      scoreMax: 60,
      scoreStddev: 10,
      sampleScores: [
        { sample: "001", score: 40, valid: true, modelCallFailed: false },
        { sample: "002", score: 50, valid: true, modelCallFailed: false },
        { sample: "003", score: 60, valid: true, modelCallFailed: false },
      ],
      finishReasons: [
        { sample: "001", finishReason: "stop" },
        { sample: "002", finishReason: "stop" },
        { sample: "003", finishReason: "stop" },
      ],
    },
  ],
};

test("report arithmetic validation recomputes case and full-suite values", () => {
  assert.equal(validateSummaryArithmetic(summary, manifest), null);
  const tampered = {
    ...summary,
    suiteSampleScores: summary.suiteSampleScores.map((sample) => (sample.sample === "002" ? { ...sample, score: 99 } : sample)),
  };
  assert.match(validateSummaryArithmetic(tampered, manifest)!, /full-suite sample arithmetic/);
});

test("report rendering is byte-deterministic for identical inputs", () => {
  assert.equal(renderReport(manifest, [summary]), renderReport(manifest, [summary]));
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
    scoreStddev: 0,
    scoreMin: 90,
    scoreMax: 90,
    suiteSampleScores: current.suiteSampleScores.map((sample) => ({ ...sample, score: 90 })),
    caseScores: current.caseScores.map((caseScore) => ({
      ...caseScore,
      score: 90,
      scoreMin: 90,
      scoreMax: 90,
      scoreStddev: 0,
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
