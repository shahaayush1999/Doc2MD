import assert from "node:assert/strict";
import test from "node:test";
import {
  parseFactFile,
  scoreAtomicRegions,
  type FactFile,
  type FactLeaf,
  type FactRegion,
  type JudgeResult,
  type LeafStatus,
} from "./score.js";

type LeafInput = {
  id: string;
  claimType: FactLeaf["claimType"];
  expectation: string;
  evidencePolicy: FactLeaf["evidencePolicy"];
  harm?: 1 | 2;
};

type RegionOptions = {
  kind?: FactRegion["kind"];
  modality?: FactRegion["modality"];
  primaryAxis?: FactRegion["primaryAxis"];
  closedWorld?: FactRegion["closedWorld"];
};

type UnsupportedClaim = JudgeResult["unsupportedClaims"][number];

type MutationScenario = {
  name: string;
  facts: FactFile;
  reference: string;
  mutation: string;
  expectedChanged: Record<string, Exclude<LeafStatus, "correct">>;
  mutationUnsupported?: (candidate: string) => UnsupportedClaim[];
  mutationRefsByLeaf?: Record<string, number[]>;
};

function leaf(input: LeafInput): FactLeaf {
  return {
    id: input.id,
    canonicalClaimId: `mutation:${input.id}`,
    claimType: input.claimType,
    expectation: input.expectation,
    harm: input.harm ?? 2,
    evidencePolicy: input.evidencePolicy,
  };
}

function tableLeaf(id: string, row: string, column: string, value: string): FactLeaf {
  return leaf({
    id,
    claimType: "table_binding",
    expectation: `${row} binds ${column} to ${value}.`,
    evidencePolicy: { type: "table_binding", row: [row], column: [column], value: [value] },
  });
}

function lexicalLeaf(id: string, expectation: string, allOf: string[][]): FactLeaf {
  return leaf({ id, claimType: "scalar", expectation, evidencePolicy: { type: "lexical", allOf } });
}

function makeFacts(leaves: FactLeaf[], options: RegionOptions = {}): FactFile {
  const modality = options.modality ?? "native_text";
  return parseFactFile({
    schemaVersion: 3,
    id: `mutation-${leaves.map((item) => item.id).join("-")}`,
    title: "Deterministic scorer mutation fixture",
    regions: [
      {
        id: "region",
        label: "Controlled mutation region",
        sourceAnchors: [{ page: 1, layer: modality, sectionPath: ["Controlled mutation"] }],
        goldSection: "Controlled mutation",
        kind: options.kind ?? "text",
        modality,
        uniqueEvidence: true,
        primaryAxis: options.primaryAxis ?? "precise_recall",
        secondaryAxes: [],
        textOnlyRecoverable: modality === "native_text",
        budget: 2,
        ...(options.closedWorld ? { closedWorld: options.closedWorld } : {}),
        leaves,
      },
    ],
  });
}

function nonblankLineRefs(candidate: string): number[] {
  return candidate.split(/\r?\n/).flatMap((line, index) => (line.trim() ? [index + 1] : []));
}

function lineRefContaining(candidate: string, value: string): number {
  const refs = candidate.split(/\r?\n/).flatMap((line, index) => (line.includes(value) ? [index + 1] : []));
  assert.equal(refs.length, 1, `Expected exactly one candidate line containing ${value}.`);
  return refs[0]!;
}

function overclaimingJudgment(
  facts: FactFile,
  candidate: string,
  unsupportedClaims: UnsupportedClaim[] = [],
  refsByLeaf: Record<string, number[]> = {},
): JudgeResult {
  const defaultRefs = nonblankLineRefs(candidate);
  return {
    leafResults: facts.regions.flatMap((region) =>
      region.leaves.map((item) => ({
        id: item.id,
        status: "correct" as const,
        candidateLineRefs: refsByLeaf[item.id] ?? defaultRefs,
      })),
    ),
    unsupportedClaims,
    rationale: "Deliberately over-credit every expected leaf so deterministic gates must resolve the mutation.",
  };
}

function evaluate(
  facts: FactFile,
  candidate: string,
  unsupportedClaims: UnsupportedClaim[] = [],
  refsByLeaf: Record<string, number[]> = {},
) {
  return scoreAtomicRegions(facts, overclaimingJudgment(facts, candidate, unsupportedClaims, refsByLeaf), candidate);
}

function statuses(scored: ReturnType<typeof scoreAtomicRegions>): Record<string, LeafStatus> {
  return Object.fromEntries(
    scored.regions.flatMap((region) => region.leaves.map((item) => [item.id, item.status] as const)),
  );
}

function closedWorldClaim(candidate: string, key: string, scope: string): UnsupportedClaim {
  return {
    regionId: "region",
    key,
    claim: `${key} is an invented extra ${scope}.`,
    obligationEvidence: `The declared ${scope} keys are exhaustive.`,
    verification: "closed_world_absence",
    candidateLineRefs: [lineRefContaining(candidate, key)],
  };
}

const exactFields = makeFacts(
  [
    tableLeaf("scalar", "Dose", "Amount", "12.5"),
    tableLeaf("unit", "Dose", "Unit", "mg"),
    tableLeaf("sign", "Dose", "Change", "+4.2"),
  ],
  { kind: "table", primaryAxis: "table_reconstruction" },
);
const exactFieldsReference = [
  "| Metric | Amount | Unit | Change |",
  "| --- | ---: | --- | ---: |",
  "| Dose | 12.5 | mg | +4.2 |",
].join("\n");

const adjacentFacts = makeFacts(
  [tableLeaf("row-r1", "R-1", "State", "OPEN"), tableLeaf("row-r2", "R-2", "State", "HOLD")],
  { kind: "table", primaryAxis: "table_reconstruction" },
);
const adjacentReference = [
  "| Record | State |",
  "| --- | --- |",
  "| R-1 | OPEN |",
  "| R-2 | HOLD |",
].join("\n");

const entitySwapFacts = makeFacts(
  [tableLeaf("north-owner", "North", "Owner", "Avery"), tableLeaf("south-owner", "South", "Owner", "Blair")],
  { kind: "table", primaryAxis: "table_reconstruction" },
);
const entitySwapReference = [
  "| Unit | Owner |",
  "| --- | --- |",
  "| North | Avery |",
  "| South | Blair |",
].join("\n");

const longRecordFacts = makeFacts(
  [
    lexicalLeaf("opening", "Opening control O-11 was reconciled.", [["Opening control O-11"], ["reconciled"]]),
    lexicalLeaf("middle", "Middle checkpoint M-22 was reconciled.", [["Middle checkpoint M-22"], ["reconciled"]]),
    lexicalLeaf("tail", "Tail closure T-33 was reconciled.", [["Tail closure T-33"], ["reconciled"]]),
  ],
  { primaryAxis: "long_context_coherence" },
);
const longRecordReference = [
  "Opening control O-11 was reconciled.",
  "Middle checkpoint M-22 was reconciled.",
  "Tail closure T-33 was reconciled.",
].join("\n");

const scenarios: MutationScenario[] = [
  {
    name: "omission",
    facts: makeFacts([lexicalLeaf("control", "Control C-7 is active.", [["Control C-7"], ["active"]])]),
    reference: "Control C-7 is active.",
    mutation: "The executive summary remains available.",
    expectedChanged: { control: "missing" },
  },
  {
    name: "wrong scalar",
    facts: exactFields,
    reference: exactFieldsReference,
    mutation: exactFieldsReference.replace("| Dose | 12.5 | mg | +4.2 |", "| Dose | 21.5 | mg | +4.2 |"),
    expectedChanged: { scalar: "incorrect" },
  },
  {
    name: "wrong unit",
    facts: exactFields,
    reference: exactFieldsReference,
    mutation: exactFieldsReference.replace("| Dose | 12.5 | mg | +4.2 |", "| Dose | 12.5 | g | +4.2 |"),
    expectedChanged: { unit: "incorrect" },
  },
  {
    name: "wrong sign",
    facts: exactFields,
    reference: exactFieldsReference,
    mutation: exactFieldsReference.replace("| Dose | 12.5 | mg | +4.2 |", "| Dose | 12.5 | mg | -4.2 |"),
    expectedChanged: { sign: "incorrect" },
  },
  {
    name: "row-column swap",
    facts: makeFacts([tableLeaf("state", "R-1", "State", "HOLD")], {
      kind: "table",
      primaryAxis: "table_reconstruction",
    }),
    reference: "| Record | State | Owner |\n| --- | --- | --- |\n| R-1 | HOLD | Avery |",
    mutation: "| Record | State | Owner |\n| --- | --- | --- |\n| R-1 | Avery | HOLD |",
    expectedChanged: { state: "incorrect" },
  },
  {
    name: "adjacent-row shift",
    facts: adjacentFacts,
    reference: adjacentReference,
    mutation: adjacentReference.replace("| R-1 | OPEN |\n| R-2 | HOLD |", "| R-1 | HOLD |\n| R-2 | OPEN |"),
    expectedChanged: { "row-r1": "incorrect", "row-r2": "incorrect" },
  },
  {
    name: "entity swap",
    facts: entitySwapFacts,
    reference: entitySwapReference,
    mutation: entitySwapReference.replace("| North | Avery |\n| South | Blair |", "| North | Blair |\n| South | Avery |"),
    expectedChanged: { "north-owner": "incorrect", "south-owner": "incorrect" },
  },
  {
    name: "edge reversal",
    facts: makeFacts(
      [
        leaf({
          id: "flow",
          claimType: "directed_edge",
          expectation: "Sensor A feeds Alarm B.",
          evidencePolicy: { type: "directed_edge", source: ["Sensor A"], destination: ["Alarm B"], relation: ["feeds"] },
        }),
      ],
      { kind: "diagram", modality: "vector_geometry", primaryAxis: "chart_diagram_spatial" },
    ),
    reference: "Sensor A feeds Alarm B.",
    mutation: "Alarm B feeds Sensor A.",
    expectedChanged: { flow: "incorrect" },
  },
  {
    name: "checkbox flip",
    facts: makeFacts(
      [
        leaf({
          id: "dose-hold",
          claimType: "form_state",
          expectation: "Dose hold is checked.",
          evidencePolicy: { type: "form_state", label: ["Dose hold"], state: "checked" },
        }),
      ],
      { kind: "form", modality: "raster", primaryAxis: "form_state" },
    ),
    reference: "[x] Dose hold",
    mutation: "[ ] Dose hold",
    expectedChanged: { "dose-hold": "incorrect" },
  },
  {
    name: "superseded-as-current",
    facts: makeFacts(
      [
        leaf({
          id: "version-order",
          claimType: "source_precedence",
          expectation: "The superseded draft is noncontrolling; the current signed order sets HOLD.",
          evidencePolicy: {
            type: "ordered_tokens",
            tokens: [["Superseded draft D-1"], ["noncontrolling"], ["Current signed order O-9"], ["HOLD"]],
          },
        }),
      ],
      { kind: "mixed", primaryAxis: "source_precedence" },
    ),
    reference: "Superseded draft D-1 is noncontrolling.\nCurrent signed order O-9 sets HOLD.",
    mutation:
      "Current signed order O-9 sets HOLD.\nSuperseded draft D-1 is presented as current despite being noncontrolling.",
    expectedChanged: { "version-order": "incorrect" },
  },
  {
    name: "wrong source binding",
    facts: makeFacts(
      [
        leaf({
          id: "authority",
          claimType: "source_precedence",
          expectation: "Controlling signed order O-9 authorizes HOLD.",
          evidencePolicy: {
            type: "ordered_tokens",
            tokens: [["Controlling signed order O-9"], ["authorizes"], ["HOLD"]],
          },
        }),
      ],
      { kind: "mixed", primaryAxis: "source_precedence" },
    ),
    reference: "Controlling signed order O-9 authorizes HOLD.",
    mutation: "Finance memo F-2 authorizes HOLD; controlling signed order O-9 is listed only as background.",
    expectedChanged: { authority: "incorrect" },
  },
  {
    name: "caption-only visual reconstruction",
    facts: makeFacts(
      [
        leaf({
          id: "visual-flow",
          claimType: "visual_description",
          expectation: "A red arrow begins at Pump P-4, points east, and terminates at Valve V-9.",
          evidencePolicy: {
            type: "qualitative",
            requiredTerms: [["red arrow"], ["Pump P-4"], ["points east"], ["Valve V-9"]],
          },
        }),
      ],
      { kind: "image", modality: "raster", primaryAxis: "image_description" },
    ),
    reference: "A red arrow begins at Pump P-4, points east, and terminates at Valve V-9.",
    mutation: "Figure 4 caption: Pump P-4 / Valve V-9, red arrow.",
    expectedChanged: { "visual-flow": "missing" },
  },
  {
    name: "distant entity drift",
    facts: makeFacts(
      [
        tableLeaf("early-custodian", "S-019", "Custodian", "Blair"),
        tableLeaf("tail-custodian", "S-204", "Custodian", "Avery"),
      ],
      { kind: "table", primaryAxis: "long_context_coherence" },
    ),
    reference: [
      "| Subject | Custodian |",
      "| --- | --- |",
      "| S-019 | Blair |",
      "Narrative section 1.",
      "Narrative section 2.",
      "Narrative section 3.",
      "Narrative section 4.",
      "Narrative section 5.",
      "| Subject | Custodian |",
      "| --- | --- |",
      "| S-204 | Avery |",
    ].join("\n"),
    mutation: [
      "| Subject | Custodian |",
      "| --- | --- |",
      "| S-019 | Blair |",
      "Narrative section 1.",
      "Narrative section 2.",
      "Narrative section 3.",
      "Narrative section 4.",
      "Narrative section 5.",
      "| Subject | Custodian |",
      "| --- | --- |",
      "| S-204 | Blair |",
    ].join("\n"),
    expectedChanged: { "tail-custodian": "incorrect" },
  },
  {
    name: "middle deletion",
    facts: longRecordFacts,
    reference: longRecordReference,
    mutation: "Opening control O-11 was reconciled.\nTail closure T-33 was reconciled.",
    expectedChanged: { middle: "missing" },
  },
  {
    name: "tail deletion",
    facts: longRecordFacts,
    reference: longRecordReference,
    mutation: "Opening control O-11 was reconciled.\nMiddle checkpoint M-22 was reconciled.",
    expectedChanged: { tail: "missing" },
  },
  {
    name: "continuation corruption",
    facts: makeFacts(
      [tableLeaf("first-state", "R-1", "State", "OPEN"), tableLeaf("continued-state", "R-9", "State", "HOLD")],
      { kind: "table", primaryAxis: "table_reconstruction" },
    ),
    reference: [
      "| Record | State | Owner |",
      "| --- | --- | --- |",
      "| R-1 | OPEN | Avery |",
      "Table continued",
      "| Record | State | Owner |",
      "| --- | --- | --- |",
      "| R-9 | HOLD | Blair |",
    ].join("\n"),
    mutation: [
      "| Record | State | Owner |",
      "| --- | --- | --- |",
      "| R-1 | OPEN | Avery |",
      "Table continued",
      "| Record | Owner | State |",
      "| --- | --- | --- |",
      "| R-9 | HOLD | Blair |",
    ].join("\n"),
    expectedChanged: { "continued-state": "incorrect" },
  },
  {
    name: "detached footnote",
    facts: makeFacts(
      [
        tableLeaf("footnote-marker", "Plan X", "Note", "[a]"),
        lexicalLeaf("footnote-meaning", "[a] means measured from acceptance.", [["[a]"], ["measured from acceptance"]]),
      ],
      { kind: "table", primaryAxis: "table_reconstruction" },
    ),
    reference: "| Plan | Window | Note |\n| --- | --- | --- |\n| Plan X | 30 days | [a] |\n[a]: measured from acceptance.",
    mutation:
      "| Plan | Window | Note |\n| --- | --- | --- |\n| Plan X | 30 days | [b] |\n[a]: measured from acceptance.\n[b]: measured from dispatch.",
    expectedChanged: { "footnote-marker": "incorrect" },
  },
  {
    name: "extra closed-world row",
    facts: makeFacts([tableLeaf("known-row", "E-01", "State", "OPEN")], {
      kind: "table",
      primaryAxis: "table_reconstruction",
      closedWorld: { scope: "table_rows", keys: ["E-01"] },
    }),
    reference: "| Exception | State |\n| --- | --- |\n| E-01 | OPEN |",
    mutation: "| Exception | State |\n| --- | --- |\n| E-01 | OPEN |\n| E-99 | WAIVED |",
    expectedChanged: {},
    mutationUnsupported: (candidate) => [closedWorldClaim(candidate, "E-99", "row")],
  },
  {
    name: "extra closed-world form option",
    facts: makeFacts(
      [
        leaf({
          id: "option-a",
          claimType: "form_state",
          expectation: "Option A is checked.",
          evidencePolicy: { type: "form_state", label: ["Option A"], state: "checked" },
        }),
      ],
      {
        kind: "form",
        modality: "raster",
        primaryAxis: "form_state",
        closedWorld: { scope: "form_options", keys: ["Option A", "Option B"] },
      },
    ),
    reference: "[x] Option A\n[ ] Option B",
    mutation: "[x] Option A\n[ ] Option B\n[x] Option C",
    expectedChanged: {},
    mutationUnsupported: (candidate) => [closedWorldClaim(candidate, "Option C", "form option")],
  },
  {
    name: "simultaneous correct-and-wrong assertion",
    facts: makeFacts([tableLeaf("duplicate-state", "R-1", "State", "HOLD")], {
      kind: "table",
      primaryAxis: "table_reconstruction",
    }),
    reference: "| Record | State |\n| --- | --- |\n| R-1 | HOLD |",
    mutation: "| Record | State |\n| --- | --- |\n| R-1 | HOLD |\n| R-1 | RELEASED |",
    expectedChanged: { "duplicate-state": "incorrect" },
  },
  {
    name: "flattened hierarchy",
    facts: makeFacts(
      [
        leaf({
          id: "program-phase",
          claimType: "structure",
          expectation: "Program contains Phase A.",
          evidencePolicy: { type: "directed_edge", source: ["Program"], destination: ["Phase A"], relation: ["contains"] },
        }),
        leaf({
          id: "phase-task",
          claimType: "structure",
          expectation: "Phase A contains Task 1.",
          evidencePolicy: { type: "directed_edge", source: ["Phase A"], destination: ["Task 1"], relation: ["contains"] },
        }),
      ],
      { kind: "structure", primaryAxis: "structure_reconstruction" },
    ),
    reference: "Program contains Phase A.\nPhase A contains Task 1.",
    mutation: "Program, Phase A, and Task 1 are peer sections.",
    expectedChanged: { "program-phase": "missing", "phase-task": "missing" },
  },
  {
    name: "unrelated cited lines",
    facts: makeFacts(
      [lexicalLeaf("authorization", "Final authorization sets HOLD.", [["Final authorization"], ["HOLD"]])],
    ),
    reference: "Final authorization sets HOLD.",
    mutation: "Appendix inventory is unchanged.",
    expectedChanged: { authorization: "missing" },
    mutationRefsByLeaf: { authorization: [1] },
  },
  {
    name: "image-placeholder-only page",
    facts: makeFacts(
      [
        leaf({
          id: "scan-content",
          claimType: "visual_description",
          expectation: "The scan shows a cracked flange at Valve V-9 with an orange quarantine tag.",
          evidencePolicy: {
            type: "qualitative",
            requiredTerms: [["cracked flange"], ["Valve V-9"], ["orange quarantine tag"]],
          },
        }),
      ],
      { kind: "image", modality: "raster", primaryAxis: "image_description" },
    ),
    reference: "The scan shows a cracked flange at Valve V-9 with an orange quarantine tag.",
    mutation: "![Page 7](page-7.png)",
    expectedChanged: { "scan-content": "missing" },
  },
];

const requiredMutationClasses = [
  "omission",
  "wrong scalar",
  "wrong unit",
  "wrong sign",
  "row-column swap",
  "adjacent-row shift",
  "entity swap",
  "edge reversal",
  "checkbox flip",
  "superseded-as-current",
  "wrong source binding",
  "caption-only visual reconstruction",
  "distant entity drift",
  "middle deletion",
  "tail deletion",
  "continuation corruption",
  "detached footnote",
  "extra closed-world row",
  "extra closed-world form option",
  "simultaneous correct-and-wrong assertion",
  "flattened hierarchy",
  "unrelated cited lines",
  "image-placeholder-only page",
] as const;

test("deterministic corpus mutation matrix enforces exact leaf transitions without double charging", async (t) => {
  assert.deepEqual(
    scenarios.map((scenario) => scenario.name),
    requiredMutationClasses,
    "the deterministic matrix must retain every promised mutation class",
  );
  for (const scenario of scenarios) {
    await t.test(scenario.name, () => {
      const reference = evaluate(scenario.facts, scenario.reference);
      const referenceStatuses = statuses(reference);
      assert.deepEqual(
        referenceStatuses,
        Object.fromEntries(Object.keys(referenceStatuses).map((id) => [id, "correct"])),
        `${scenario.name}: the unmutated reference must be fully recovered`,
      );
      assert.equal(reference.rawScore, 100, `${scenario.name}: reference raw score`);
      assert.equal(reference.unsupported.count, 0, `${scenario.name}: reference unsupported claims`);

      const unsupported = scenario.mutationUnsupported?.(scenario.mutation) ?? [];
      const mutated = evaluate(
        scenario.facts,
        scenario.mutation,
        unsupported,
        scenario.mutationRefsByLeaf,
      );
      const mutatedStatuses = statuses(mutated);
      const expectedStatuses: Record<string, LeafStatus> = { ...referenceStatuses, ...scenario.expectedChanged };
      assert.deepEqual(mutatedStatuses, expectedStatuses, `${scenario.name}: exact leaf statuses`);

      const changedIds = Object.keys(referenceStatuses)
        .filter((id) => referenceStatuses[id] !== mutatedStatuses[id])
        .sort();
      assert.deepEqual(changedIds, Object.keys(scenario.expectedChanged).sort(), `${scenario.name}: exact changed leaf ids`);
      assert.equal(mutated.unsupported.count, unsupported.length, `${scenario.name}: applied unsupported count`);
      assert.equal(mutated.unsupported.reportedCount, unsupported.length, `${scenario.name}: reported unsupported count`);
      assert.deepEqual(
        mutated.unsupported.claims.map((claim) => claim.key),
        unsupported.map((claim) => claim.key),
        `${scenario.name}: exact unsupported keys`,
      );

      if (unsupported.length === 0) {
        assert.equal(mutated.unsupported.penalty, 0, `${scenario.name}: a leaf error must not also be charged as unsupported`);
      } else {
        assert.deepEqual(changedIds, [], `${scenario.name}: a novel closed-world key must not alter expected leaves`);
        assert.deepEqual(
          mutated.statusHarm,
          reference.statusHarm,
          `${scenario.name}: unsupported content is charged once outside expected-leaf statuses`,
        );
        assert.equal(mutated.unsupported.penalty, 2, `${scenario.name}: exactly one region-derived unsupported harm`);
      }
      assert.ok(mutated.rawScore < reference.rawScore, `${scenario.name}: the exact mutation must reduce signed utility`);
    });
  }
});
