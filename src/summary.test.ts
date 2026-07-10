import assert from "node:assert/strict";
import test from "node:test";
import { evaluatorPriceReport, parseFactFile, scoreAtomicRegions, scoringContractFingerprint, scoringContractVersion } from "./score.js";
import {
  aggregateSampleFirst,
  sampleStddev,
  validateCurrentScoreArtifact,
  type AggregationCase,
  type ScoreArtifactExpectation,
} from "./summary.js";

const sampleIds = ["001", "002", "003"];

const facts = parseFactFile({
  schemaVersion: 2,
  id: "case-a",
  regions: [
    {
      id: "p01.memo",
      page: 1,
      label: "Memo",
      kind: "text",
      budget: 1,
      closedWorld: false,
      leaves: [{ id: "p01.memo.value", expectation: "Value is 7.", harm: 1, allowPartial: false }],
    },
  ],
});
const judgeResult = {
  leafResults: [{ id: "p01.memo.value", status: "correct" as const, candidateLineRefs: [1] }],
  unsupportedClaims: [],
  rationale: "Correct.",
};
const prediction = "Value is 7.";
const atomicScore = scoreAtomicRegions(facts, judgeResult, prediction);
const evaluatorUsage = { inputTokens: 10, outputTokens: 5, totalTokens: 15 };
const runCache = { runKey: "run-key", predictionHash: "prediction-hash" };
const scoreCache = { scoreKey: "score-key", judgeKey: "judge-key", factsHash: "facts-hash" };
const expectedArtifact: ScoreArtifactExpectation = {
  caseId: "case-a",
  modelId: "model-a",
  sample: "001",
  suite: "official",
  manifestPath: "benchmark/manifest.json",
  inputProtocol: "native_pdf",
  modelCallFailed: false,
  finishReason: "stop",
  runCache,
  scoreCache,
  prediction,
};
const validArtifact = {
  caseId: "case-a",
  modelId: "model-a",
  sample: "001",
  suite: "official",
  manifestPath: "benchmark/manifest.json",
  inputProtocol: "native_pdf",
  finishReason: "stop",
  runCache,
  scoringContractVersion,
  scoringContractFingerprint,
  valid: true,
  score: atomicScore.score,
  modelCallFailed: false,
  evaluatorFailure: false,
  scorer: {
    status: "valid",
    estimatedCostUsd: evaluatorPriceReport(evaluatorUsage).estimatedCostUsd,
    elapsedMs: 10,
    attempts: 1,
    errors: [],
    judgeReused: false,
    usage: evaluatorUsage,
    pricing: evaluatorPriceReport(evaluatorUsage),
    resolved: { provider: "google-vertex", modelId: "gemini-3.1-flash-lite" },
    cache: scoreCache,
  },
  atomicScore,
  judgeResult,
};

test("score artifact validation recomputes rather than trusting a stored score", () => {
  const valid = validateCurrentScoreArtifact(facts, validArtifact, expectedArtifact);
  assert.equal(valid.kind, "evaluator_valid");
  assert.equal(valid.score, 100);

  const tampered = validateCurrentScoreArtifact(facts, { ...validArtifact, score: 99 }, expectedArtifact);
  assert.equal(tampered.kind, "missing_invalid");
  assert.match(tampered.reason!, /does not match recomputed/);
});

test("score artifact validation rejects out-of-range and tampered atomic evidence", () => {
  const outOfRange = validateCurrentScoreArtifact(facts, { ...validArtifact, score: 101 }, expectedArtifact);
  assert.match(outOfRange.reason!, /outside \[0, 100\]/);

  const alteredAtomic = validateCurrentScoreArtifact(
    facts,
    { ...validArtifact, atomicScore: { ...atomicScore, score: 50 } },
    expectedArtifact,
  );
  assert.match(alteredAtomic.reason!, /stored atomic score does not match/);
});

test("sample standard deviation uses n minus one", () => {
  assert.equal(sampleStddev([1, 2, 3]), 1);
});

test("suite aggregation is equal-case and sample-first", () => {
  const cases: AggregationCase[] = [
    {
      caseId: "a",
      samples: [
        { sample: "001", score: 0, valid: true },
        { sample: "002", score: 30, valid: true },
        { sample: "003", score: 60, valid: true },
      ],
    },
    {
      caseId: "b",
      samples: [
        { sample: "001", score: 100, valid: true },
        { sample: "002", score: 70, valid: true },
        { sample: "003", score: 40, valid: true },
      ],
    },
  ];
  const aggregate = aggregateSampleFirst(cases, sampleIds);
  assert.equal(aggregate.complete, true);
  assert.deepEqual(aggregate.suiteSampleScores, [
    { sample: "001", score: 50 },
    { sample: "002", score: 50 },
    { sample: "003", score: 50 },
  ]);
  assert.equal(aggregate.score, 50);
  assert.equal(aggregate.scoreStddev, 0);
});

test("model-call failure remains a valid zero sample", () => {
  const aggregate = aggregateSampleFirst(
    [
      {
        caseId: "a",
        samples: [
          { sample: "001", score: 0, valid: true, modelCallFailed: true },
          { sample: "002", score: 80, valid: true },
          { sample: "003", score: 100, valid: true },
        ],
      },
    ],
    sampleIds,
  );
  assert.equal(aggregate.complete, true);
  assert.equal(aggregate.score, 60);
});

test("evaluator failure invalidates the cohort instead of becoming zero", () => {
  const aggregate = aggregateSampleFirst(
    [
      {
        caseId: "a",
        samples: [
          { sample: "001", score: 100, valid: true },
          { sample: "002", score: null, valid: false, evaluatorFailure: true },
          { sample: "003", score: 100, valid: true },
        ],
      },
    ],
    sampleIds,
  );
  assert.equal(aggregate.complete, false);
  assert.equal(aggregate.score, null);
  assert.deepEqual(aggregate.suiteSampleScores, []);
  assert.match(aggregate.invalidSamples[0].reason, /evaluator failure/);
});

test("missing or duplicate sample slots invalidate the cohort", () => {
  const aggregate = aggregateSampleFirst(
    [
      {
        caseId: "a",
        samples: [
          { sample: "001", score: 90, valid: true },
          { sample: "001", score: 90, valid: true },
          { sample: "002", score: 90, valid: true },
        ],
      },
    ],
    sampleIds,
  );
  assert.equal(aggregate.complete, false);
  assert.ok(aggregate.invalidSamples.some((sample) => sample.sample === "001" && sample.reason === "duplicate sample"));
  assert.ok(aggregate.invalidSamples.some((sample) => sample.sample === "003" && sample.reason === "missing sample"));
});
