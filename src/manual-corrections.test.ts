import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import test from "node:test";
import { parseFactFile, scoreAtomicRegions, scoreFinalAtomicRegions, type JudgeResult } from "./evaluator.js";
import { applyManualCorrections } from "./manual-corrections.js";

const facts = parseFactFile({
  schemaVersion: 3, id: "fixture", regions: [{
    id: "exceptions", label: "Exception register", kind: "table", modality: "native_text",
    uniqueEvidence: true, primaryAxis: "table_reconstruction", secondaryAxes: [], textOnlyRecoverable: true,
    budget: 1, sourceAnchors: [{ page: 1, layer: "native_text", sectionPath: ["Exception register"] }],
    goldSection: "Exception register", closedWorld: { scope: "table_rows", keys: ["E-05", "EX-07"] },
    leaves: [
      { id: "e05", canonicalClaimId: "e05", claimType: "table_binding", expectation: "E-05 state is CLOSED.", harm: 1,
        evidencePolicy: { type: "table_binding", row: ["E-05"], column: ["State"], value: ["CLOSED"] } },
      { id: "ex07", canonicalClaimId: "ex07", claimType: "table_binding", expectation: "EX-07 state is OPEN.", harm: 1,
        evidencePolicy: { type: "table_binding", row: ["EX-07"], column: ["State"], value: ["OPEN"] } },
    ],
  }],
});
const prediction = "## Exception register\n\n| Exception | Affected obligation | State |\n|---|---|---|\n| E-05 | T-02 | CLOSED |\n| EX-07 | E-05 | OPEN |";
const judgment: JudgeResult = {
  leafResults: [
    { id: "e05", status: "correct", candidateLineRefs: [3, 5] },
    { id: "ex07", status: "correct", candidateLineRefs: [3, 6] },
  ], unsupportedClaims: [], rationale: "Local fixture.",
};

test("an affected-obligation cross-reference does not become the target table row", () => {
  assert.equal(scoreAtomicRegions(facts, judgment, prediction).score, 100);
  assert.throws(() => scoreFinalAtomicRegions(facts, {
    ...judgment, leafResults: [...judgment.leafResults, judgment.leafResults[0]!],
  }), /exactly one decision/);
});

test("automatically discovered extra rows remain review proposals with zero penalty", () => {
  const extended = prediction + "\n| EXTRA | T-99 | NEW |";
  const score = scoreAtomicRegions(facts, judgment, extended);
  assert.equal(score.score, 100);
  assert.equal(score.unsupported.count, 0);
  assert.equal(score.unsupported.reviewClaims.length, 1);
});

test("manual corrections are final, preserve other saved judgments and legacy notes, and are idempotent", () => {
  const atomicScore = scoreAtomicRegions(facts, judgment, prediction);
  // Simulate a previously adjudicated final result, not a fresh judge response.
  atomicScore.regions[0]!.leaves[1]!.status = "missing";
  const evaluation = { valid: true, atomicScore, judgeResult: judgment, manualCorrections: { applied: ["legacy review"] } };
  const corrections = {
    predictionHash: createHash("sha256").update(prediction).digest("hex"),
    leaves: [{ id: "e05", status: "incorrect" as const, candidateLineRefs: [5], reason: "Synthetic reviewed decision to test final authority." }],
    rejectedUnsupported: [], approvedUnsupported: [],
  };
  const result = applyManualCorrections(facts, prediction, evaluation, corrections);
  assert.equal(result.atomicScore.regions[0]!.leaves[0]!.status, "incorrect");
  assert.equal(result.atomicScore.regions[0]!.leaves[1]!.status, "missing");
  assert.deepEqual(result.manualCorrections.applied, ["legacy review"]);
  assert.deepEqual(applyManualCorrections(facts, prediction, result, corrections), result);
  assert.throws(() => applyManualCorrections(facts, prediction + "changed", evaluation, corrections), /different prediction/);
});

test("only a specifically approved proposal receives an unsupported penalty", () => {
  const extended = prediction + "\n| EXTRA | T-99 | NEW |";
  const atomicScore = scoreAtomicRegions(facts, judgment, extended);
  const result = applyManualCorrections(facts, extended, { valid: true, atomicScore, judgeResult: judgment }, {
    predictionHash: createHash("sha256").update(extended).digest("hex"), leaves: [], rejectedUnsupported: [],
    approvedUnsupported: [{ regionId: "exceptions", key: "EXTRA", reason: "Confirmed extra row in this fixture." }],
  });
  assert.equal(result.atomicScore.unsupported.count, 1);
  assert.equal(result.atomicScore.unsupported.reviewClaims.length, 0);
  assert.equal(result.score, 50);
});
