import assert from "node:assert/strict";
import test from "node:test";
import {
  BenchmarkContractError,
  derivedScoreCacheKey,
  EvaluatorContractError,
  judgeRegionsForPrompt,
  normalizeRunOutcome,
  parseFactFile,
  recomputeCachedJudgment,
  scoreAtomicRegions,
  unsupportedHarmForRegion,
  validateJudgeResult,
  type FactFile,
  type JudgeResult,
} from "./score.js";

function facts(): FactFile {
  return parseFactFile(
    {
      schemaVersion: 2,
      id: "case-1",
      title: "Fixture",
      regions: [
        {
          id: "open",
          page: 1,
          label: "Open prose",
          kind: "text",
          budget: 1,
          closedWorld: false,
          leaves: [
            { id: "a", expectation: "A", harm: 1, allowPartial: false },
            { id: "b", expectation: "B", harm: 2, allowPartial: true },
          ],
        },
        {
          id: "closed",
          page: 2,
          label: "Closed table",
          kind: "table",
          budget: 2,
          closedWorld: true,
          leaves: [{ id: "c", expectation: "C", harm: 1, allowPartial: false }],
        },
      ],
    },
    { caseId: "case-1", pages: 2 },
  );
}

type TestLeafResult = Omit<JudgeResult["leafResults"][number], "candidateLineRefs"> & { candidateLineRefs?: number[] };
type TestUnsupportedClaim = Omit<JudgeResult["unsupportedClaims"][number], "candidateLineRefs"> & { candidateLineRefs?: number[] };
type TestJudgmentOverrides = Omit<Partial<JudgeResult>, "leafResults" | "unsupportedClaims"> & {
  leafResults?: TestLeafResult[];
  unsupportedClaims?: TestUnsupportedClaim[];
};

function judgment(overrides: TestJudgmentOverrides = {}): JudgeResult {
  const leafResults = overrides.leafResults ?? [
    { id: "a", status: "correct" },
    { id: "b", status: "correct" },
    { id: "c", status: "correct" },
  ];
  const unsupportedClaims = overrides.unsupportedClaims ?? [];
  const { leafResults: _leafResults, unsupportedClaims: _unsupportedClaims, ...rest } = overrides;
  return {
    leafResults: leafResults.map((item) => ({
      ...item,
      candidateLineRefs: item.candidateLineRefs ?? (item.status === "missing" ? [] : [1]),
    })),
    unsupportedClaims: unsupportedClaims.map((claim) => ({ ...claim, candidateLineRefs: claim.candidateLineRefs ?? [1] })),
    rationale: "Fixture judgment.",
    ...rest,
  };
}

test("all-correct atomic regions score 100", () => {
  const scored = scoreAtomicRegions(facts(), judgment());
  assert.equal(scored.score, 100);
  assert.deepEqual(scored.statusHarm, { correct: 4, partial: 0, missing: 0, incorrect: 0 });
});

test("facts v2 rejects duplicate leaf ids before any evaluator call", () => {
  const fixture = JSON.parse(JSON.stringify(facts())) as any;
  fixture.regions[1].leaves[0].id = "a";
  assert.throws(() => parseFactFile(fixture), (error: unknown) => error instanceof BenchmarkContractError && /Duplicate leaf ids: a/.test(error.message));
});

test("partial and incorrect credits are applied by leaf harm within a region", () => {
  const scored = scoreAtomicRegions(
    facts(),
    judgment({
      leafResults: [
        { id: "a", status: "incorrect", note: "Wrong value." },
        { id: "b", status: "partial", note: "One allowed qualifier is absent." },
        { id: "c", status: "correct" },
      ],
    }),
  );
  const open = scored.regions.find((region) => region.regionId === "open")!;
  assert.equal(open.earned, 0.5);
  assert.ok(Math.abs(open.rawScore - 100 / 6) < 1e-12);
  assert.equal(scored.statusHarm.incorrect, 1);
  assert.equal(scored.statusHarm.partial, 2);
});

test("verified unsupported claims deduct once inside their closed-world region", () => {
  const scored = scoreAtomicRegions(
    facts(),
    judgment({
      unsupportedClaims: [
        {
          regionId: "closed",
          claim: "Invented extra row",
          obligationEvidence: "The closed region defines an exhaustive three-row table and no extra row.",
          verification: "closed_world_absence",
        },
      ],
    }),
  );
  assert.equal(scored.unsupported.penalty, 1);
  assert.equal(scored.regions.find((region) => region.regionId === "closed")!.score, 0);
  assert.ok(Math.abs(scored.score - 100 / 3) < 1e-12);
});

test("signed region utility keeps an incorrect leaf strictly below an omitted leaf", () => {
  const missing = scoreAtomicRegions(
    facts(),
    judgment({
      leafResults: [
        { id: "a", status: "missing" },
        { id: "b", status: "correct" },
        { id: "c", status: "correct" },
      ],
    }),
  );
  const incorrect = scoreAtomicRegions(
    facts(),
    judgment({
      leafResults: [
        { id: "a", status: "incorrect" },
        { id: "b", status: "correct" },
        { id: "c", status: "correct" },
      ],
    }),
  );
  assert.ok(incorrect.score < missing.score);

  const allMissing = scoreAtomicRegions(
    facts(),
    judgment({ leafResults: ["a", "b", "c"].map((id) => ({ id, status: "missing" as const })) }),
  );
  const incorrectAtFloor = scoreAtomicRegions(
    facts(),
    judgment({
      leafResults: [
        { id: "a", status: "incorrect" },
        { id: "b", status: "missing" },
        { id: "c", status: "missing" },
      ],
    }),
  );
  assert.equal(allMissing.score, 0);
  assert.equal(incorrectAtFloor.score, 0);
  assert.ok(incorrectAtFloor.rawScore < allMissing.rawScore, "signed audit utility distinguishes errors at the public zero floor");
});

test("a closed-world extra claim still lowers a region that also has a non-correct leaf", () => {
  const baseLeafResults: TestLeafResult[] = [
    { id: "a", status: "correct" },
    { id: "b", status: "correct" },
    { id: "c", status: "missing" },
  ];
  const withoutUnsupported = scoreAtomicRegions(facts(), judgment({ leafResults: baseLeafResults }));
  const withUnsupported = scoreAtomicRegions(
    facts(),
    judgment({
      leafResults: baseLeafResults,
      unsupportedClaims: [
        {
          regionId: "closed",
          claim: "Invented extra row",
          obligationEvidence: "The exhaustive obligations do not contain it.",
          verification: "closed_world_absence",
        },
      ],
    }),
  );
  const penalizedRegion = withUnsupported.regions.find((region) => region.regionId === "closed")!;
  assert.equal(penalizedRegion.score, -100);
  assert.ok(withUnsupported.rawScore < withoutUnsupported.rawScore);
  assert.ok(withUnsupported.score < withoutUnsupported.score);
  assert.equal(withUnsupported.unsupported.count, 1);
  assert.equal(withUnsupported.unsupported.reportedCount, 1);
});

test("judge validation rejects duplicate, unknown, and missing leaf ids", () => {
  assert.throws(
    () =>
      validateJudgeResult(
        facts(),
        judgment({
          leafResults: [
            { id: "a", status: "correct" },
            { id: "a", status: "correct" },
            { id: "unknown", status: "correct" },
          ],
        }),
      ),
    (error: unknown) =>
      error instanceof EvaluatorContractError &&
      error.message.includes("duplicate leaf ids: a") &&
      error.message.includes("unknown leaf ids: unknown") &&
      error.message.includes("missing leaf ids: b, c"),
  );
});

test("judge validation rejects partial on an exact leaf", () => {
  assert.throws(
    () =>
      validateJudgeResult(
        facts(),
        judgment({
          leafResults: [
            { id: "a", status: "partial", note: "Not allowed." },
            { id: "b", status: "correct" },
            { id: "c", status: "correct" },
          ],
        }),
      ),
    /a does not allow partial credit/,
  );
});

test("judge validation requires candidate-line evidence and checks its range", () => {
  const noEvidence = judgment();
  noEvidence.leafResults[0]!.candidateLineRefs = [];
  assert.throws(() => validateJudgeResult(facts(), noEvidence, "A"), /a is correct but cites no candidate lines/);

  const missingWithEvidence = judgment();
  missingWithEvidence.leafResults[0] = { id: "a", status: "missing", candidateLineRefs: [1] };
  assert.throws(() => validateJudgeResult(facts(), missingWithEvidence, "A"), /a is missing but cites candidate lines/);

  const outOfRange = judgment();
  outOfRange.leafResults[0]!.candidateLineRefs = [2];
  assert.throws(() => validateJudgeResult(facts(), outOfRange, "A"), /candidate line 2, but the candidate has 1 lines/);
});

test("exact table bindings are repaired from candidate evidence or downgraded", () => {
  const fixture = facts();
  fixture.regions[0].leaves[0].expectation = "For Reno → SFO, State is BLOCKED.";
  const result = judgment();
  result.leafResults[0]!.candidateLineRefs = [1];
  const downgraded = validateJudgeResult(fixture, result, "| Reno -> SFO | RELEASED |");
  assert.equal(downgraded.leafResults[0]!.status, "missing");
  assert.deepEqual(downgraded.leafResults[0]!.candidateLineRefs, []);

  const miscited = judgment();
  miscited.leafResults[0]!.candidateLineRefs = [1];
  const repaired = validateJudgeResult(fixture, miscited, "Unrelated heading\n| Reno -> SFO | BLOCKED |");
  assert.equal(repaired.leafResults[0]!.status, "correct");
  assert.deepEqual(repaired.leafResults[0]!.candidateLineRefs, [2]);
});

test("closed-world absence cannot cite an open-world region", () => {
  assert.throws(
    () =>
      validateJudgeResult(
        facts(),
        judgment({
          unsupportedClaims: [
            {
              regionId: "open",
              claim: "Unverified extra prose",
              obligationEvidence: "The open region is not exhaustive.",
              verification: "closed_world_absence",
            },
          ],
        }),
      ),
    /closed_world_absence cites open-world region open/,
  );
});

test("unsupported claims reject the removed direct-contradiction classification", () => {
  const invalid = judgment() as any;
  invalid.unsupportedClaims = [
    {
      regionId: "open",
      claim: "The memo says the launch was cancelled.",
      obligationEvidence: "An expected leaf says approved.",
      verification: "direct_source_contradiction",
      candidateLineRefs: [1],
    },
  ];
  assert.throws(
    () => validateJudgeResult(facts(), invalid),
    /Judge output does not match schema/,
  );
});

test("judge-facing leaf obligations omit scorer harm", () => {
  const projected = judgeRegionsForPrompt(facts());
  assert.deepEqual(projected[0].leaves[0], { id: "a", expectation: "A", allowPartial: false });
  assert.equal(JSON.stringify(projected).includes('"harm"'), false);
});

test("unsupported harm is derived from the highest atomic harm in a closed region", () => {
  const fixture = facts();
  fixture.regions[0].closedWorld = true;
  assert.equal(unsupportedHarmForRegion(fixture.regions[0]), 2);
  assert.equal(unsupportedHarmForRegion(fixture.regions[1]), 1);

  const scored = scoreAtomicRegions(
    fixture,
    judgment({
      unsupportedClaims: [
        {
          regionId: "open",
          claim: "An invented extra row",
          obligationEvidence: "The region obligations define the exhaustive set.",
          verification: "closed_world_absence",
        },
      ],
    }),
  );
  assert.equal(scored.unsupported.penalty, 2);
  assert.equal(scored.unsupported.claims[0].harm, 2);

  const judgeChoosingHarm = judgment({
    unsupportedClaims: [
      {
        regionId: "open",
        claim: "An invented extra row",
        obligationEvidence: "The region obligations define the exhaustive set.",
        verification: "closed_world_absence",
        harm: 1,
      } as any,
    ],
  });
  assert.throws(() => validateJudgeResult(fixture, judgeChoosingHarm), /Judge output does not match schema/);
});

test("success to model-failure changes only the derived score identity", () => {
  const success = normalizeRunOutcome({ finishReason: "stop", error: null });
  const failure = normalizeRunOutcome({ finishReason: "error", error: "forced failure" });
  const base = { caseId: "case-1", judgeKey: "same-source-and-prediction", factsHash: "same-scoring-facts" };
  const successfulScoreKey = derivedScoreCacheKey({ ...base, runOutcome: success });
  const failedScoreKey = derivedScoreCacheKey({ ...base, runOutcome: failure });

  assert.deepEqual(success, { kind: "success" });
  assert.deepEqual(failure, { kind: "model_failure" });
  assert.notEqual(failedScoreKey, successfulScoreKey);
  assert.equal(base.judgeKey, "same-source-and-prediction");
});

test("model-failure to empty success cannot reuse its synthetic missing judgment", () => {
  const base = { caseId: "case-1", judgeKey: "empty-prediction-judge-key", factsHash: "facts" };
  const failedScoreKey = derivedScoreCacheKey({ ...base, runOutcome: normalizeRunOutcome({ finishReason: "error" }) });
  const successfulScoreKey = derivedScoreCacheKey({ ...base, runOutcome: normalizeRunOutcome({ finishReason: "stop" }) });
  const syntheticFailureScore = {
    valid: true,
    scorer: { status: "not_run_model_failure", cache: { judgeKey: base.judgeKey } },
    judgeResult: judgment({
      leafResults: ["a", "b", "c"].map((id) => ({ id, status: "missing" as const })),
    }),
  };

  assert.notEqual(successfulScoreKey, failedScoreKey);
  assert.equal(recomputeCachedJudgment(facts(), syntheticFailureScore, base.judgeKey), null);
});

test("cached judge output is validated and atomic score is recomputed", () => {
  const cached = {
    valid: true,
    score: 7,
    atomicScore: { score: 7 },
    scorer: { status: "valid", cache: { judgeKey: "judge-key" } },
    judgeResult: judgment(),
  };
  const recomputed = recomputeCachedJudgment(facts(), cached, "judge-key");
  assert.equal(recomputed?.atomicScore.score, 100);

  const invalid = structuredClone(cached);
  invalid.judgeResult.leafResults[0].status = "partial";
  assert.equal(recomputeCachedJudgment(facts(), invalid, "judge-key"), null);
});
