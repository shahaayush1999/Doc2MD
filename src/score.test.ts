import assert from "node:assert/strict";
import { performance } from "node:perf_hooks";
import test from "node:test";
import {
  BenchmarkContractError,
  derivedScoreCacheKey,
  EvaluatorContractError,
  judgeRegionsForPrompt,
  normalizeRunOutcome,
  parseFactFile,
  recomputeCachedJudgment,
  resolveLeafEvidence,
  scoreAtomicRegions,
  unsupportedHarmForRegion,
  validateJudgeResult,
  type FactFile,
  type JudgeResult,
} from "./score.js";

const fixturePrediction = "A\nB\nC";

function facts(): FactFile {
  return parseFactFile(
    {
      schemaVersion: 3,
      id: "case-1",
      title: "Fixture",
      regions: [
        {
          id: "open",
          label: "Open prose",
          sourceAnchors: [{ page: 1, layer: "native_text", sectionPath: ["Open prose"] }],
          goldSection: "Open prose",
          kind: "text",
          modality: "native_text",
          uniqueEvidence: false,
          primaryAxis: "precise_recall",
          secondaryAxes: [],
          textOnlyRecoverable: true,
          budget: 1,
          leaves: [
            {
              id: "a",
              canonicalClaimId: "claim-a",
              claimType: "scalar",
              expectation: "A",
              harm: 1,
              evidencePolicy: { type: "lexical", allOf: [["A"]] },
            },
            {
              id: "b",
              canonicalClaimId: "claim-b",
              claimType: "scalar",
              expectation: "B",
              harm: 2,
              evidencePolicy: { type: "lexical", allOf: [["B"]] },
            },
          ],
        },
        {
          id: "closed",
          label: "Closed table",
          sourceAnchors: [
            {
              page: 2,
              layer: "raster",
              sectionPath: ["Closed table"],
              bbox: [0.1, 0.2, 0.9, 0.8],
            },
          ],
          goldSection: "Closed table",
          kind: "table",
          modality: "raster",
          uniqueEvidence: true,
          primaryAxis: "table_reconstruction",
          secondaryAxes: ["precise_recall"],
          textOnlyRecoverable: false,
          budget: 2,
          closedWorld: { scope: "table_rows", keys: ["C"] },
          leaves: [
            {
              id: "c",
              canonicalClaimId: "claim-c",
              claimType: "scalar",
              expectation: "C",
              harm: 1,
              evidencePolicy: { type: "lexical", allOf: [["C"]] },
            },
          ],
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
    { id: "a", status: "correct", candidateLineRefs: [1] },
    { id: "b", status: "correct", candidateLineRefs: [2] },
    { id: "c", status: "correct", candidateLineRefs: [3] },
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

function singleLeafFacts(input: {
  claimType: string;
  evidencePolicy: unknown;
  expectation?: string;
  kind?: string;
  modality?: string;
}): FactFile {
  return parseFactFile({
    schemaVersion: 3,
    id: "gate",
    regions: [
      {
        id: "gate-region",
        label: "Gate region",
        sourceAnchors: [{ page: 1, layer: input.modality ?? "native_text", sectionPath: ["Gate"] }],
        goldSection: "Gate",
        kind: input.kind ?? "text",
        modality: input.modality ?? "native_text",
        uniqueEvidence: true,
        primaryAxis: "precise_recall",
        secondaryAxes: [],
        textOnlyRecoverable: input.modality === undefined || input.modality === "native_text",
        budget: 1,
        leaves: [
          {
            id: "gate-leaf",
            canonicalClaimId: "gate-claim",
            claimType: input.claimType,
            expectation: input.expectation ?? "Gate expectation",
            harm: 2,
            evidencePolicy: input.evidencePolicy,
          },
        ],
      },
    ],
  });
}

function correctGateJudgment(refs: number[]): JudgeResult {
  return {
    leafResults: [{ id: "gate-leaf", status: "correct", candidateLineRefs: refs }],
    unsupportedClaims: [],
    rationale: "Judge claimed the leaf was correct.",
  };
}

function missingGateJudgment(): JudgeResult {
  return {
    leafResults: [{ id: "gate-leaf", status: "missing", candidateLineRefs: [] }],
    unsupportedClaims: [],
    rationale: "Judge overlooked candidate evidence.",
  };
}

test("all-correct atomic regions score 100 with typed diagnostic metadata", () => {
  const scored = scoreAtomicRegions(facts(), judgment(), fixturePrediction);
  assert.equal(scored.score, 100);
  assert.deepEqual(scored.statusHarm, { correct: 4, missing: 0, incorrect: 0 });
  assert.deepEqual(scored.regions[1]!.sourceAnchors[0]!.bbox, [0.1, 0.2, 0.9, 0.8]);
  assert.equal(scored.regions[1]!.primaryAxis, "table_reconstruction");
  assert.deepEqual(
    scored.diagnostics.byModality.map(({ key, score }) => ({ key, score })),
    [
      { key: "native_text", score: 100 },
      { key: "raster", score: 100 },
    ],
  );
});

test("atomic scoring cannot bypass evidence gates by omitting the candidate", () => {
  assert.throws(
    () => (scoreAtomicRegions as any)(facts(), judgment()),
    /requires the candidate prediction so typed evidence gates cannot be bypassed/,
  );
});

test("facts v3 rejects v2, duplicate ids, duplicate canonical claims, and out-of-range anchors", () => {
  const v2 = JSON.parse(JSON.stringify(facts())) as any;
  v2.schemaVersion = 2;
  assert.throws(() => parseFactFile(v2), /Invalid facts schema v3/);

  const duplicateLeaf = JSON.parse(JSON.stringify(facts())) as any;
  duplicateLeaf.regions[1].leaves[0].id = "a";
  assert.throws(
    () => parseFactFile(duplicateLeaf),
    (error: unknown) => error instanceof BenchmarkContractError && /Duplicate leaf ids: a/.test(error.message),
  );

  const duplicateCanonical = JSON.parse(JSON.stringify(facts())) as any;
  duplicateCanonical.regions[1].leaves[0].canonicalClaimId = "claim-a";
  assert.throws(() => parseFactFile(duplicateCanonical), /double-charge evidence: claim-a/);

  const page = JSON.parse(JSON.stringify(facts())) as any;
  page.regions[0].sourceAnchors[0].page = 3;
  assert.throws(() => parseFactFile(page, { pages: 2 }), /Source anchors reference pages beyond the 2-page source: open:3/);
});

test("facts v3 validates bbox, axis, closed-world, and claim-policy structure", () => {
  const bbox = JSON.parse(JSON.stringify(facts())) as any;
  bbox.regions[1].sourceAnchors[0].bbox = [0.9, 0.2, 0.1, 0.8];
  assert.throws(() => parseFactFile(bbox), /bbox must have x0 < x1 and y0 < y1/);

  const repeatedAxis = JSON.parse(JSON.stringify(facts())) as any;
  repeatedAxis.regions[0].secondaryAxes = ["precise_recall"];
  assert.throws(() => parseFactFile(repeatedAxis), /repeats its primary capability axis/);

  const keys = JSON.parse(JSON.stringify(facts())) as any;
  keys.regions[1].closedWorld.keys = ["C", "c"];
  assert.throws(() => parseFactFile(keys), /repeats closed-world keys: c/);

  const policy = JSON.parse(JSON.stringify(facts())) as any;
  policy.regions[0].leaves[0].claimType = "table_binding";
  assert.throws(() => parseFactFile(policy), /a:table_binding->lexical/);

  for (const modality of ["raster", "native_layer_recovery"]) {
    const contradiction = JSON.parse(JSON.stringify(facts())) as any;
    contradiction.regions[0].modality = modality;
    contradiction.regions[0].sourceAnchors[0].layer = modality;
    assert.throws(
      () => parseFactFile(contradiction),
      new RegExp(`cannot be textOnlyRecoverable when its modality is ${modality}`),
    );
  }
});

test("correct, missing, and incorrect use signed atomic harm without partial credit", () => {
  const scored = scoreAtomicRegions(
    facts(),
    judgment({
      leafResults: [
        { id: "a", status: "incorrect", note: "Wrong value.", candidateLineRefs: [1] },
        { id: "b", status: "missing" },
        { id: "c", status: "correct", candidateLineRefs: [3] },
      ],
    }),
    fixturePrediction,
  );
  const open = scored.regions.find((region) => region.regionId === "open")!;
  assert.equal(open.earned, -0.5);
  assert.ok(Math.abs(open.rawScore + 100 / 6) < 1e-12);
  assert.equal(scored.statusHarm.incorrect, 1);
  assert.equal(scored.statusHarm.missing, 2);

  const invalid = judgment() as any;
  invalid.leafResults[0].status = "partial";
  assert.throws(() => validateJudgeResult(facts(), invalid, fixturePrediction), /Judge output does not match schema/);
});

test("verified unsupported claims deduct once inside their structured closed-world region", () => {
  const scored = scoreAtomicRegions(
    facts(),
    judgment({
      unsupportedClaims: [
        {
          regionId: "closed",
          key: "C-99",
          claim: "C-99 is an invented extra row",
          obligationEvidence: "The declared row keys are exhaustive and contain no extra row.",
          verification: "closed_world_absence",
          candidateLineRefs: [4],
        },
      ],
    }),
    `${fixturePrediction}\nC-99`,
  );
  assert.equal(scored.unsupported.penalty, 1);
  assert.equal(scored.regions.find((region) => region.regionId === "closed")!.score, 0);
  assert.ok(Math.abs(scored.score - 100 / 3) < 1e-12);
});

test("structured closed-world tables recover a judge-missed novel row conservatively", () => {
  const tableFacts = parseFactFile(
    {
      schemaVersion: 3,
      id: "closed-table",
      regions: [
        {
          id: "exceptions",
          label: "Exception register",
          sourceAnchors: [{ page: 1, layer: "native_text", sectionPath: ["Exceptions"] }],
          goldSection: "Exceptions",
          kind: "table",
          modality: "native_text",
          uniqueEvidence: true,
          primaryAxis: "table_reconstruction",
          secondaryAxes: [],
          textOnlyRecoverable: true,
          budget: 1,
          closedWorld: { scope: "table_rows", keys: ["E-01", "E-02"] },
          leaves: [
            {
              id: "e01.state",
              canonicalClaimId: "e01.state",
              claimType: "table_binding",
              expectation: "E-01 State is OPEN.",
              harm: 1,
              evidencePolicy: { type: "table_binding", row: ["E-01"], column: ["State"], value: ["OPEN"] },
            },
            {
              id: "e02.owner",
              canonicalClaimId: "e02.owner",
              claimType: "table_binding",
              expectation: "E-02 Owner is IP.",
              harm: 1,
              evidencePolicy: { type: "table_binding", row: ["E-02"], column: ["Owner"], value: ["IP"] },
            },
          ],
        },
      ],
    },
    { caseId: "closed-table", pages: 1 },
  );
  const base = "| Exception | State | Owner |\n| --- | --- | --- |\n| E-01 | OPEN | AK |\n| E-02 | CLOSED | IP |";
  const judge: JudgeResult = {
    leafResults: [
      { id: "e01.state", status: "correct", candidateLineRefs: [1, 3] },
      { id: "e02.owner", status: "correct", candidateLineRefs: [1, 4] },
    ],
    unsupportedClaims: [],
    rationale: "The evaluator overlooked any extra row.",
  };

  assert.equal(scoreAtomicRegions(tableFacts, judge, base).score, 100);
  const scored = scoreAtomicRegions(tableFacts, judge, `${base}\n\n| E-99 | OPEN | LS |`);

  assert.equal(scored.score, 50);
  assert.equal(scored.unsupported.count, 1);
  assert.equal(scored.unsupported.reportedCount, 0);
  assert.equal(scored.unsupported.claims[0]!.regionId, "exceptions");
  assert.equal(scored.unsupported.claims[0]!.key, "E-99");
  assert.deepEqual(scored.unsupported.claims[0]!.candidateLineRefs, [6]);
});

test("signed region utility keeps an incorrect leaf strictly below an omitted leaf", () => {
  const missing = scoreAtomicRegions(
    facts(),
    judgment({
      leafResults: [
        { id: "a", status: "missing" },
        { id: "b", status: "correct", candidateLineRefs: [2] },
        { id: "c", status: "correct", candidateLineRefs: [3] },
      ],
    }),
    fixturePrediction,
  );
  const incorrect = scoreAtomicRegions(
    facts(),
    judgment({
      leafResults: [
        { id: "a", status: "incorrect", candidateLineRefs: [1] },
        { id: "b", status: "correct", candidateLineRefs: [2] },
        { id: "c", status: "correct", candidateLineRefs: [3] },
      ],
    }),
    fixturePrediction,
  );
  assert.ok(incorrect.score < missing.score);

  const allMissing = scoreAtomicRegions(
    facts(),
    judgment({ leafResults: ["a", "b", "c"].map((id) => ({ id, status: "missing" as const })) }),
    fixturePrediction,
  );
  const incorrectAtFloor = scoreAtomicRegions(
    facts(),
    judgment({
      leafResults: [
        { id: "a", status: "incorrect", candidateLineRefs: [1] },
        { id: "b", status: "missing" },
        { id: "c", status: "missing" },
      ],
    }),
    fixturePrediction,
  );
  assert.equal(allMissing.score, 0);
  assert.equal(incorrectAtFloor.score, 0);
  assert.ok(incorrectAtFloor.rawScore < allMissing.rawScore);
});

test("a closed-world extra claim still lowers a region that also has a missing leaf", () => {
  const baseLeafResults: TestLeafResult[] = [
    { id: "a", status: "correct", candidateLineRefs: [1] },
    { id: "b", status: "correct", candidateLineRefs: [2] },
    { id: "c", status: "missing" },
  ];
  const withoutUnsupported = scoreAtomicRegions(facts(), judgment({ leafResults: baseLeafResults }), fixturePrediction);
  const withUnsupported = scoreAtomicRegions(
    facts(),
    judgment({
      leafResults: baseLeafResults,
      unsupportedClaims: [
        {
          regionId: "closed",
          key: "C-99",
          claim: "C-99 is an invented extra row",
          obligationEvidence: "The declared keys are exhaustive.",
          verification: "closed_world_absence",
          candidateLineRefs: [4],
        },
      ],
    }),
    `${fixturePrediction}\nC-99`,
  );
  assert.equal(withUnsupported.regions.find((region) => region.regionId === "closed")!.score, -100);
  assert.ok(withUnsupported.rawScore < withoutUnsupported.rawScore);
  assert.equal(withUnsupported.unsupported.count, 1);
});

test("judge validation rejects duplicate, unknown, and missing leaf ids", () => {
  assert.throws(
    () =>
      validateJudgeResult(
        facts(),
        judgment({
          leafResults: [
            { id: "a", status: "correct", candidateLineRefs: [1] },
            { id: "a", status: "correct", candidateLineRefs: [1] },
            { id: "unknown", status: "correct", candidateLineRefs: [1] },
          ],
        }),
        fixturePrediction,
      ),
    (error: unknown) =>
      error instanceof EvaluatorContractError &&
      error.message.includes("duplicate leaf ids: a") &&
      error.message.includes("unknown leaf ids: unknown") &&
      error.message.includes("missing leaf ids: b, c"),
  );
});

test("judge validation requires nonblank in-range candidate-line evidence", () => {
  const noEvidence = judgment();
  noEvidence.leafResults[0]!.candidateLineRefs = [];
  assert.throws(() => validateJudgeResult(facts(), noEvidence, fixturePrediction), /a is correct but cites no candidate lines/);

  const missingWithEvidence = judgment();
  missingWithEvidence.leafResults[0] = { id: "a", status: "missing", candidateLineRefs: [1] };
  assert.throws(() => validateJudgeResult(facts(), missingWithEvidence, fixturePrediction), /a is missing but cites candidate lines/);

  const outOfRange = judgment();
  outOfRange.leafResults[0]!.candidateLineRefs = [4];
  assert.throws(() => validateJudgeResult(facts(), outOfRange, fixturePrediction), /candidate line 4, but the candidate has 3 lines/);

  const blank = judgment();
  blank.leafResults[0]!.candidateLineRefs = [2];
  assert.throws(() => validateJudgeResult(facts(), blank, "A\n\nC"), /a cites blank candidate line 2/);
});

test("exact Markdown table binding requires the cited header, target row, column identity, and value", () => {
  const fixture = singleLeafFacts({
    claimType: "table_binding",
    kind: "table",
    evidencePolicy: { type: "table_binding", row: ["Reno"], column: ["State"], value: ["BLOCKED"] },
  });
  const correct = "| Route | State | Owner |\n| --- | --- | --- |\n| Reno | BLOCKED | Alice |";
  assert.equal(validateJudgeResult(fixture, correctGateJudgment([1, 3]), correct).leafResults[0]!.status, "correct");

  const swapped = "| Route | State | Owner |\n| --- | --- | --- |\n| Reno | Alice | BLOCKED |";
  assert.equal(validateJudgeResult(fixture, correctGateJudgment([1, 3]), swapped).leafResults[0]!.status, "incorrect");

  const adjacent = "| Route | State |\n| --- | --- |\n| Reno | RELEASED |\n| Boise | BLOCKED |";
  assert.equal(validateJudgeResult(fixture, correctGateJudgment([1, 3, 4]), adjacent).leafResults[0]!.status, "incorrect");

  const repairedHeaderReference = validateJudgeResult(fixture, correctGateJudgment([3]), correct);
  assert.equal(repairedHeaderReference.leafResults[0]!.status, "correct");
  assert.deepEqual(repairedHeaderReference.leafResults[0]!.candidateLineRefs, [1, 3]);
});

test("exact table binding supports explicit prose and cited plain header+row fallback", () => {
  const fixture = singleLeafFacts({
    claimType: "table_binding",
    kind: "table",
    evidencePolicy: { type: "table_binding", row: ["Reno"], column: ["State"], value: ["BLOCKED"] },
  });
  assert.equal(
    validateJudgeResult(fixture, correctGateJudgment([1]), "For Reno, State: BLOCKED").leafResults[0]!.status,
    "correct",
  );
  assert.equal(
    validateJudgeResult(fixture, correctGateJudgment([1]), "Reno is RELEASED; Boise State: BLOCKED").leafResults[0]!.status,
    "missing",
  );
  const plain = "Route  State  Owner\nReno  BLOCKED  Alice";
  assert.equal(validateJudgeResult(fixture, correctGateJudgment([1, 2]), plain).leafResults[0]!.status, "correct");
});

test("exact table binding supports cited HTML tables and rejects HTML column swaps", () => {
  const fixture = singleLeafFacts({
    claimType: "table_binding",
    kind: "table",
    evidencePolicy: { type: "table_binding", row: ["Reno"], column: ["State"], value: ["BLOCKED"] },
  });
  const correct = [
    "<table>",
    "<tr><th>Route</th><th>State</th><th>Owner</th></tr>",
    "<tr><td>Reno</td><td><strong>BLOCKED</strong></td><td>Alice</td></tr>",
    "</table>",
  ].join("\n");
  assert.equal(validateJudgeResult(fixture, correctGateJudgment([2, 3]), correct).leafResults[0]!.status, "correct");

  const swapped = [
    "<table>",
    "<tr><th>Route</th><th>State</th><th>Owner</th></tr>",
    "<tr><td>Reno</td><td>Alice</td><td>BLOCKED</td></tr>",
    "</table>",
  ].join("\n");
  assert.equal(validateJudgeResult(fixture, correctGateJudgment([2, 3]), swapped).leafResults[0]!.status, "incorrect");

  const multilineWithRowHeader = [
    "<table>",
    "<tr>",
    "<th>Route</th>",
    "<th>State</th>",
    "<th>Owner</th>",
    "</tr>",
    "<tr>",
    '<th scope="row">Reno</th>',
    "<td>BLOCKED</td>",
    "<td>Alice</td>",
    "</tr>",
    "</table>",
  ].join("\n");
  assert.equal(
    validateJudgeResult(fixture, correctGateJudgment([4, 8, 9]), multilineWithRowHeader).leafResults[0]!.status,
    "correct",
  );
  const repairedHeaderReference = validateJudgeResult(
    fixture,
    correctGateJudgment([8, 9]),
    multilineWithRowHeader,
  ).leafResults[0]!;
  assert.equal(repairedHeaderReference.status, "correct");
  assert.deepEqual(repairedHeaderReference.candidateLineRefs, [4, 8, 9]);
});

test("deterministic table resolution recovers judge-missed Markdown, HTML, and plain bindings", () => {
  const fixture = singleLeafFacts({
    claimType: "table_binding",
    kind: "table",
    evidencePolicy: { type: "table_binding", row: ["Reno"], column: ["State"], value: ["BLOCKED"] },
  });
  const candidates = [
    "| Route | State | Owner |\n| --- | --- | --- |\n| Reno | BLOCKED | Alice |",
    "<table>\n<tr><th>Route</th><th>State</th><th>Owner</th></tr>\n<tr><td>Reno</td><td>BLOCKED</td><td>Alice</td></tr>\n</table>",
    "Route  State  Owner\nReno  BLOCKED  Alice",
  ];
  for (const candidate of candidates) {
    const result = validateJudgeResult(fixture, missingGateJudgment(), candidate).leafResults[0]!;
    assert.equal(result.status, "correct");
    assert.ok(result.candidateLineRefs.length >= 1);
  }
});

test("deterministic table resolution detects judge-missed contradictions in Markdown, HTML, and plain tables", () => {
  const fixture = singleLeafFacts({
    claimType: "table_binding",
    kind: "table",
    evidencePolicy: { type: "table_binding", row: ["Reno"], column: ["State"], value: ["BLOCKED"] },
  });
  const candidates = [
    "| Route | State | Owner |\n| --- | --- | --- |\n| Reno | RELEASED | Alice |",
    "<table>\n<tr><th>Route</th><th>State</th><th>Owner</th></tr>\n<tr><td>Reno</td><td>RELEASED</td><td>Alice</td></tr>\n</table>",
    "Route  State  Owner\nReno  RELEASED  Alice",
  ];
  for (const candidate of candidates) {
    const result = validateJudgeResult(fixture, missingGateJudgment(), candidate).leafResults[0]!;
    assert.equal(result.status, "incorrect");
    assert.ok(result.candidateLineRefs.length >= 1);
  }
});

test("table row identity is the first column and conflicting duplicate bindings are incorrect", () => {
  const fixture = singleLeafFacts({
    claimType: "table_binding",
    kind: "table",
    evidencePolicy: { type: "table_binding", row: ["Reno"], column: ["State"], value: ["BLOCKED"] },
  });
  const wrongKeyColumn = "| Route | State | Owner |\n| --- | --- | --- |\n| Boise | Reno | BLOCKED |";
  assert.equal(validateJudgeResult(fixture, missingGateJudgment(), wrongKeyColumn).leafResults[0]!.status, "missing");

  const conflicting = [
    "| Route | State | Owner |",
    "| --- | --- | --- |",
    "| Reno | BLOCKED | Alice |",
    "| Reno | RELEASED | Alice |",
  ].join("\n");
  assert.equal(validateJudgeResult(fixture, missingGateJudgment(), conflicting).leafResults[0]!.status, "incorrect");

  const taskFixture = singleLeafFacts({
    claimType: "table_binding",
    kind: "table",
    evidencePolicy: { type: "table_binding", row: ["T-01"], column: ["State"], value: ["READY"] },
  });
  const displacedTask = "| ID | State | Owner |\n| --- | --- | --- |\n| T-02 | READY | T-01 |";
  assert.equal(validateJudgeResult(taskFixture, missingGateJudgment(), displacedTask).leafResults[0]!.status, "missing");
});

test("P17 regression: wrong excursion value, implicit unchecked options, and wrong coordinator time cannot receive credit", () => {
  const fixture = parseFactFile({
    schemaVersion: 3,
    id: "P17-regression",
    regions: [
      {
        id: "p17",
        label: "Excursion form",
        sourceAnchors: [{ page: 1, layer: "raster", sectionPath: ["Excursion form"] }],
        goldSection: "Excursion form",
        kind: "mixed",
        modality: "raster",
        uniqueEvidence: true,
        primaryAxis: "form_state",
        secondaryAxes: ["table_reconstruction", "precise_recall"],
        textOnlyRecoverable: false,
        budget: 4,
        leaves: [
          {
            id: "peak",
            canonicalClaimId: "p17-peak",
            claimType: "table_binding",
            expectation: "At 13:40 the temperature was 4.7 C.",
            harm: 2,
            evidencePolicy: { type: "table_binding", row: ["13:40"], column: ["Temperature"], value: ["4.7 C"] },
          },
          {
            id: "do-not-dose",
            canonicalClaimId: "p17-do-not-dose",
            claimType: "form_state",
            expectation: "Do-not-dose is checked.",
            harm: 2,
            evidencePolicy: { type: "form_state", label: ["Do-not-dose", "Do not dose"], state: "checked" },
          },
          {
            id: "return",
            canonicalClaimId: "p17-return",
            claimType: "form_state",
            expectation: "Return-to-stock is unchecked.",
            harm: 1,
            evidencePolicy: { type: "form_state", label: ["Return-to-stock", "Return to stock"], state: "unchecked" },
          },
          {
            id: "destroy",
            canonicalClaimId: "p17-destroy",
            claimType: "form_state",
            expectation: "Destroy is unchecked.",
            harm: 1,
            evidencePolicy: { type: "form_state", label: ["Destroy"], state: "unchecked" },
          },
          {
            id: "coordinator-time",
            canonicalClaimId: "p17-coordinator-time",
            claimType: "scalar",
            expectation: "Coordinator timestamp is 13:40.",
            harm: 2,
            evidencePolicy: { type: "lexical", allOf: [["Coordinator"], ["13:40"]] },
          },
        ],
      },
    ],
  });
  const candidate = [
    "| Time | Temperature | Duration |",
    "| --- | --- | --- |",
    "| 13:40 | 9.1 C | 3 h |",
    "[x] Do-not-dose",
    "Return-to-stock",
    "Destroy",
    "Coordinator approved at 15:20",
  ].join("\n");
  const result = validateJudgeResult(
    fixture,
    {
      leafResults: [
        { id: "peak", status: "correct", candidateLineRefs: [1, 3] },
        { id: "do-not-dose", status: "correct", candidateLineRefs: [4] },
        { id: "return", status: "correct", candidateLineRefs: [4, 5] },
        { id: "destroy", status: "correct", candidateLineRefs: [4, 6] },
        { id: "coordinator-time", status: "correct", candidateLineRefs: [7] },
      ],
      unsupportedClaims: [],
      rationale: "Over-crediting fixture.",
    },
    candidate,
  );
  assert.deepEqual(
    result.leafResults.map(({ id, status }) => ({ id, status })),
    [
      { id: "peak", status: "incorrect" },
      { id: "do-not-dose", status: "correct" },
      { id: "return", status: "missing" },
      { id: "destroy", status: "missing" },
      { id: "coordinator-time", status: "missing" },
    ],
  );
});

test("form-state resolution binds the nearest state to the exact option label", () => {
  const fixture = singleLeafFacts({
    claimType: "form_state",
    kind: "form",
    evidencePolicy: { type: "form_state", label: ["Option B"], state: "unchecked" },
  });
  const prose = "Option A is checked, while Option B is unchecked.";
  const result = validateJudgeResult(fixture, missingGateJudgment(), prose).leafResults[0]!;
  assert.equal(result.status, "correct");
  assert.deepEqual(result.candidateLineRefs, [1]);

  const wrong = "Option A is unchecked, while Option B is checked.";
  assert.equal(validateJudgeResult(fixture, missingGateJudgment(), wrong).leafResults[0]!.status, "incorrect");
  const conflicting = "Option B is checked and unchecked.";
  assert.equal(validateJudgeResult(fixture, missingGateJudgment(), conflicting).leafResults[0]!.status, "incorrect");

  const table = "| Option | State |\n| --- | --- |\n| Option A | checked |\n| Option B | unchecked |";
  assert.equal(validateJudgeResult(fixture, missingGateJudgment(), table).leafResults[0]!.status, "correct");

  const sameRow = "| Option A | checked | Option B | unchecked |";
  assert.equal(validateJudgeResult(fixture, missingGateJudgment(), sameRow).leafResults[0]!.status, "correct");
  const optionA = singleLeafFacts({
    claimType: "form_state",
    kind: "form",
    evidencePolicy: { type: "form_state", label: ["Option A"], state: "checked" },
  });
  assert.equal(validateJudgeResult(optionA, missingGateJudgment(), sameRow).leafResults[0]!.status, "correct");
  const wrongOptionB = singleLeafFacts({
    claimType: "form_state",
    kind: "form",
    evidencePolicy: { type: "form_state", label: ["Option B"], state: "checked" },
  });
  assert.equal(validateJudgeResult(wrongOptionB, missingGateJudgment(), sameRow).leafResults[0]!.status, "incorrect");
});

test("minimal lexical resolution agrees with cited compact multi-sentence evidence without paragraph-wide bags", () => {
  const fixture = singleLeafFacts({
    claimType: "scalar",
    expectation:
      "A lower-priority record may supply detail but cannot reverse a higher-priority state; closure applies only to the obligation named in an exception row.",
    evidencePolicy: {
      type: "lexical",
      allOf: [["lower-priority"], ["cannot reverse"], ["higher-priority"], ["obligation named"]],
    },
  });
  const compact =
    "A lower-priority record may supply detail but cannot reverse a higher-priority state. Closure applies only to the obligation named in the exception row.";
  assert.equal(validateJudgeResult(fixture, correctGateJudgment([1]), compact).leafResults[0]!.status, "correct");
  assert.deepEqual(resolveLeafEvidence(compact, fixture.regions[0]!.leaves[0]!), {
    satisfied: true,
    contradiction: false,
    candidateLineRefs: [1],
  });

  const unrelated =
    "A lower-priority memo was archived. " +
    "This paragraph contains unrelated operational history, owners, timestamps, and status notes that do not bind the claims. ".repeat(4) +
    "A separate rule cannot reverse a higher-priority state. Another unrelated register mentions an obligation named elsewhere.";
  assert.equal(resolveLeafEvidence(unrelated, fixture.regions[0]!.leaves[0]!)?.satisfied, false);
});

test("judge-confirmed lexical citation recovery grounds a minimal multi-line cover without trusting omissions", () => {
  const fixture = singleLeafFacts({
    claimType: "scalar",
    expectation: "Rollback stops the active transfer and preserves custody at the last confirmed location.",
    evidencePolicy: { type: "lexical", allOf: [["rollback"], ["confirmed"]] },
  });
  const candidate = [
    "Unrelated heading",
    "Rollback invoked: notify both site leads.",
    "Stop the active transfer and preserve custody at the last confirmed location.",
  ].join("\n");

  const judgeConfirmed = validateJudgeResult(fixture, correctGateJudgment([1]), candidate).leafResults[0]!;
  assert.equal(judgeConfirmed.status, "correct");
  assert.deepEqual(judgeConfirmed.candidateLineRefs, [2, 3]);

  const judgeMissing = validateJudgeResult(fixture, missingGateJudgment(), candidate).leafResults[0]!;
  assert.equal(judgeMissing.status, "missing");

  const replayedDemotion = validateJudgeResult(
    fixture,
    {
      ...missingGateJudgment(),
      leafResults: [
        {
          id: "gate-leaf",
          status: "missing",
          candidateLineRefs: [],
          note: "[typed-evidence-gate] The citations omit one or more required lexical term groups.",
        },
      ],
    },
    candidate,
  ).leafResults[0]!;
  assert.equal(replayedDemotion.status, "correct");
  assert.deepEqual(replayedDemotion.candidateLineRefs, [2, 3]);
});

test("judge-reported lexical omissions do not rescan the full candidate", () => {
  const leafCount = 120;
  const fixture = parseFactFile({
    schemaVersion: 3,
    id: "lexical-omission-performance",
    regions: [
      {
        id: "requirements",
        label: "Requirements",
        sourceAnchors: [{ page: 1, layer: "native_text", sectionPath: ["Requirements"] }],
        goldSection: "Requirements",
        kind: "text",
        modality: "native_text",
        uniqueEvidence: true,
        primaryAxis: "precise_recall",
        secondaryAxes: [],
        textOnlyRecoverable: true,
        budget: 1,
        leaves: Array.from({ length: leafCount }, (_, index) => ({
          id: `leaf-${index}`,
          canonicalClaimId: `claim-${index}`,
          claimType: "scalar",
          expectation: `Requirement TOKEN-${index} is present.`,
          harm: 1,
          evidencePolicy: { type: "lexical", allOf: [[`TOKEN-${index}`], ["present"]] },
        })),
      },
    ],
  });
  const candidate = Array.from(
    { length: 400 },
    (_, index) => `Unrelated operational history line ${index} contains enough prose to exercise locality scanning.`,
  ).join("\n");
  const omitted: JudgeResult = {
    leafResults: fixture.regions[0]!.leaves.map((leaf) => ({
      id: leaf.id,
      status: "missing",
      candidateLineRefs: [],
    })),
    unsupportedClaims: [],
    rationale: "The candidate omits every requirement.",
  };

  const started = performance.now();
  const validated = validateJudgeResult(fixture, omitted, candidate);
  const elapsedMs = performance.now() - started;

  assert.equal(validated.leafResults.every((leaf) => leaf.status === "missing"), true);
  assert.ok(elapsedMs < 500, `lexical omission validation took ${elapsedMs.toFixed(1)}ms`);
});

test("judge-confirmed lexical recovery rejects paragraph bags, cross-row bindings, and negated evidence", () => {
  const bagFixture = singleLeafFacts({
    claimType: "scalar",
    expectation: "Rollback stops the active transfer and preserves custody at the last confirmed location.",
    evidencePolicy: { type: "lexical", allOf: [["rollback"], ["confirmed"]] },
  });
  const bag = "Rollback appears in an appendix.\nA different shipment was confirmed yesterday.";
  assert.equal(validateJudgeResult(bagFixture, correctGateJudgment([1]), bag).leafResults[0]!.status, "missing");

  const bindingFixture = singleLeafFacts({
    claimType: "scalar",
    expectation: "Kestrel credentials remain HOLD until C-3.",
    evidencePolicy: { type: "lexical", allOf: [["Kestrel credentials"], ["HOLD"], ["C-3"]] },
  });
  const crossedRows = [
    "| Account | State | Condition |",
    "| --- | --- | --- |",
    "| Kestrel credentials | ACTIVE | C-2 |",
    "| Boreal credentials | HOLD | C-3 |",
  ].join("\n");
  assert.equal(
    validateJudgeResult(bindingFixture, correctGateJudgment([1, 3, 4]), crossedRows).leafResults[0]!.status,
    "missing",
  );

  const polarityFixture = singleLeafFacts({
    claimType: "scalar",
    expectation: "Physical release is authorized after C-3.",
    evidencePolicy: { type: "lexical", allOf: [["physical release"], ["authorized"], ["C-3"]] },
  });
  const negated = "Physical release is not authorized.\nC-3 is listed separately.";
  assert.equal(validateJudgeResult(polarityFixture, correctGateJudgment([1]), negated).leafResults[0]!.status, "incorrect");
});

test("directed, ordered, lexical, and qualitative gates reject unsupported correct classifications", () => {
  const directed = singleLeafFacts({
    claimType: "directed_edge",
    evidencePolicy: { type: "directed_edge", source: ["Intake"], destination: ["Review"] },
  });
  assert.equal(validateJudgeResult(directed, correctGateJudgment([1]), "Review -> Intake").leafResults[0]!.status, "incorrect");
  assert.equal(validateJudgeResult(directed, correctGateJudgment([1]), "Intake -> Review").leafResults[0]!.status, "correct");

  const directedProse = singleLeafFacts({
    claimType: "directed_edge",
    evidencePolicy: { type: "directed_edge", source: ["Intake"], destination: ["Review"], relation: ["routes to"] },
  });
  assert.equal(validateJudgeResult(directedProse, correctGateJudgment([1]), "Intake never routes to Review").leafResults[0]!.status, "incorrect");
  assert.equal(
    validateJudgeResult(directedProse, missingGateJudgment(), "Routing path: Intake to Review (routes to).").leafResults[0]!.status,
    "correct",
  );
  assert.equal(
    validateJudgeResult(directedProse, missingGateJudgment(), "The routes to path runs from Intake to Review.").leafResults[0]!.status,
    "correct",
  );

  const ordered = singleLeafFacts({
    claimType: "ordered_record",
    evidencePolicy: { type: "ordered_tokens", tokens: [["alpha"], ["beta"], ["gamma"]] },
  });
  assert.equal(validateJudgeResult(ordered, correctGateJudgment([1]), "gamma beta alpha").leafResults[0]!.status, "incorrect");
  assert.equal(
    validateJudgeResult(
      ordered,
      correctGateJudgment([5, 4, 3, 2, 1]),
      "gamma\nfiller\nbeta\nfiller\nalpha",
    ).leafResults[0]!.status,
    "incorrect",
  );

  const lexical = singleLeafFacts({
    claimType: "scalar",
    evidencePolicy: { type: "lexical", allOf: [["temperature", "temp"], ["4.7 C", "4.7C"], ["13:40"]] },
  });
  assert.equal(validateJudgeResult(lexical, correctGateJudgment([1]), "Temp 4.7C at 13:40").leafResults[0]!.status, "correct");
  const negated = singleLeafFacts({
    claimType: "scalar",
    evidencePolicy: { type: "lexical", allOf: [["physical release"], ["authorized"]] },
  });
  assert.equal(
    validateJudgeResult(negated, correctGateJudgment([1]), "Physical release is not authorized.").leafResults[0]!.status,
    "incorrect",
  );
  const signed = singleLeafFacts({
    claimType: "scalar",
    evidencePolicy: { type: "lexical", allOf: [["EX-07"], ["signed"]] },
  });
  assert.equal(
    validateJudgeResult(signed, correctGateJudgment([1]), "EX-07 is not signed.").leafResults[0]!.status,
    "incorrect",
  );
  const expectedUnsigned = singleLeafFacts({
    claimType: "scalar",
    expectation: "EX-07 is not signed.",
    evidencePolicy: { type: "lexical", allOf: [["EX-07"], ["signed"]] },
  });
  assert.equal(
    validateJudgeResult(expectedUnsigned, correctGateJudgment([1]), "EX-07 is not signed.").leafResults[0]!.status,
    "correct",
  );
  const joined = singleLeafFacts({
    claimType: "cross_page_join",
    evidencePolicy: { type: "lexical", allOf: [["Kestrel"], ["HOLD"], ["C-3"]] },
  });
  assert.equal(
    validateJudgeResult(
      joined,
      correctGateJudgment([1, 2]),
      "Kestrel credentials are not on HOLD.\nC-3 remains listed.",
    ).leafResults[0]!.status,
    "incorrect",
  );

  const visual = singleLeafFacts({
    claimType: "visual_description",
    kind: "diagram",
    modality: "vector_geometry",
    evidencePolicy: { type: "qualitative", requiredTerms: [["red", "crimson"], ["dashed"], ["upper-right", "top right"]] },
  });
  assert.equal(validateJudgeResult(visual, correctGateJudgment([1]), "A red dashed line.").leafResults[0]!.status, "missing");
  assert.equal(
    validateJudgeResult(visual, missingGateJudgment(), "A red dashed line terminates in the upper-right.").leafResults[0]!.status,
    "missing",
  );
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
              key: "X-99",
              claim: "Unverified extra prose",
              obligationEvidence: "The open region is not exhaustive.",
              verification: "closed_world_absence",
              candidateLineRefs: [1],
            },
          ],
        }),
        fixturePrediction,
      ),
    /closed_world_absence cites open-world region open/,
  );
});

test("closed-world unsupported claims require a novel keyed assertion grounded in cited candidate lines", () => {
  const expectedKey = judgment({
    unsupportedClaims: [
      {
        regionId: "closed",
        key: "C",
        claim: "C is an unsupported row",
        obligationEvidence: "The declared row keys are exhaustive.",
        verification: "closed_world_absence",
        candidateLineRefs: [3],
      },
    ],
  });
  assert.throws(
    () => validateJudgeResult(facts(), expectedKey, fixturePrediction),
    /does not ground a novel closed-world key/,
  );

  const uncitedNovelKey = judgment({
    unsupportedClaims: [
      {
        regionId: "closed",
        key: "C-99",
        claim: "C-99 is an unsupported row",
        obligationEvidence: "The declared row keys are exhaustive.",
        verification: "closed_world_absence",
        candidateLineRefs: [3],
      },
    ],
  });
  assert.throws(
    () => validateJudgeResult(facts(), uncitedNovelKey, `${fixturePrediction}\nC-99`),
    /does not ground a novel closed-world key/,
  );

  const duplicateKey = judgment({
    unsupportedClaims: [
      {
        regionId: "closed",
        key: "C-99",
        claim: "C-99 is an unsupported row",
        obligationEvidence: "The row keys are exhaustive.",
        verification: "closed_world_absence",
        candidateLineRefs: [4],
      },
      {
        regionId: "closed",
        key: "c-99",
        claim: "c-99 is also described as invented",
        obligationEvidence: "The row keys are exhaustive.",
        verification: "closed_world_absence",
        candidateLineRefs: [4],
      },
    ],
  });
  assert.throws(
    () => validateJudgeResult(facts(), duplicateKey, `${fixturePrediction}\nC-99`),
    /duplicate unsupported claims/,
  );
});

test("unsupported claims reject removed classifications and judge-chosen harm", () => {
  const classification = judgment() as any;
  classification.unsupportedClaims = [
    {
      regionId: "open",
      key: "launch",
      claim: "The memo says launch was cancelled.",
      obligationEvidence: "An expected leaf says approved.",
      verification: "direct_source_contradiction",
      candidateLineRefs: [1],
    },
  ];
  assert.throws(() => validateJudgeResult(facts(), classification, fixturePrediction), /Judge output does not match schema/);

  const harm = judgment({
    unsupportedClaims: [
      {
        regionId: "closed",
        key: "C-99",
        claim: "An invented row",
        obligationEvidence: "The keys are exhaustive.",
        verification: "closed_world_absence",
        candidateLineRefs: [3],
        harm: 1,
      } as any,
    ],
  });
  assert.throws(() => validateJudgeResult(facts(), harm, fixturePrediction), /Judge output does not match schema/);
});

test("judge-facing obligations expose typed policies but omit scorer harm and budgets", () => {
  const projected = judgeRegionsForPrompt(facts());
  assert.deepEqual(projected[0]!.leaves[0], {
    id: "a",
    canonicalClaimId: "claim-a",
    claimType: "scalar",
    expectation: "A",
    evidencePolicy: { type: "lexical", allOf: [["A"]] },
  });
  assert.equal(JSON.stringify(projected).includes('"harm"'), false);
  assert.equal(JSON.stringify(projected).includes('"budget"'), false);
  assert.equal(JSON.stringify(projected).includes('"sourceAnchors"'), false);
});

test("unsupported harm is derived from the highest atomic harm in a closed region", () => {
  const fixture = facts();
  fixture.regions[0]!.closedWorld = { scope: "region_claims", keys: ["A", "B"] };
  assert.equal(unsupportedHarmForRegion(fixture.regions[0]!), 2);
  assert.equal(unsupportedHarmForRegion(fixture.regions[1]!), 1);

  const scored = scoreAtomicRegions(
    fixture,
    judgment({
      unsupportedClaims: [
        {
          regionId: "open",
          key: "A-99",
          claim: "A-99 is an invented assertion",
          obligationEvidence: "The declared claims are exhaustive.",
          verification: "closed_world_absence",
          candidateLineRefs: [4],
        },
      ],
    }),
    `${fixturePrediction}\nA-99`,
  );
  assert.equal(scored.unsupported.penalty, 2);
  assert.equal(scored.unsupported.claims[0]!.harm, 2);
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
  assert.equal(recomputeCachedJudgment(facts(), syntheticFailureScore, base.judgeKey, ""), null);
});

test("cached judge output is evidence-gated and atomic score is recomputed", () => {
  const cached = {
    valid: true,
    score: 7,
    atomicScore: { score: 7 },
    scorer: { status: "valid", cache: { judgeKey: "judge-key" } },
    judgeResult: judgment(),
  };
  const recomputed = recomputeCachedJudgment(facts(), cached, "judge-key", fixturePrediction);
  assert.equal(recomputed?.atomicScore.score, 100);

  const wrongCandidate = recomputeCachedJudgment(facts(), cached, "judge-key", "wrong\nwrong\nwrong");
  assert.equal(wrongCandidate?.atomicScore.score, 0);

  const invalid = structuredClone(cached);
  (invalid.judgeResult.leafResults[0] as any).status = "partial";
  assert.equal(recomputeCachedJudgment(facts(), invalid, "judge-key", fixturePrediction), null);
});

test("cached judgment replays across implementation-only scorer drift but not content drift", () => {
  const currentIdentity = {
    judgeKey: "new-judge-key",
    predictionHash: "prediction",
    pdfHash: "pdf",
    goldHash: "gold",
    factsHash: "facts",
    renderedPromptHash: "prompt",
    judgeContractFingerprint: "new-contract",
  };
  const cached = {
    valid: true,
    scoringContractVersion: "atomic-region-candidate-grounded-v9",
    scorer: {
      status: "valid",
      evaluatorModelId: "vertex-gemini-3.1-flash-lite",
      evaluatorModelName: "gemini-3.1-flash-lite",
      evaluatorReasoning: "minimal",
      cache: { ...currentIdentity, judgeKey: "old-judge-key", judgeContractFingerprint: "old-contract" },
    },
    judgeResult: judgment(),
  };

  assert.equal(recomputeCachedJudgment(facts(), cached, currentIdentity, fixturePrediction)?.atomicScore.score, 100);

  for (const field of ["predictionHash", "pdfHash", "goldHash", "factsHash", "renderedPromptHash"] as const) {
    const drifted = structuredClone(currentIdentity);
    drifted[field] = `changed-${field}`;
    assert.equal(recomputeCachedJudgment(facts(), cached, drifted, fixturePrediction), null, field);
  }

  const semanticVersionDrift = structuredClone(cached);
  semanticVersionDrift.scoringContractVersion = "different-version";
  assert.equal(recomputeCachedJudgment(facts(), semanticVersionDrift, currentIdentity, fixturePrediction), null);
});
