import assert from "node:assert/strict";
import test from "node:test";
import {
  auditReferenceCase,
  goldSectionLineRefs,
  minimalRequiredTermRefs,
} from "./auditReference.js";
import { parseFactFile, type FactFile } from "./score.js";

const gold = `# Fixture

## Evidence

Record Alpha has value 42.

The red node is visibly left of the blue node.

## Other

The red node is right of the blue node.
`;

function fixtureFacts(exactValue = "42"): FactFile {
  return parseFactFile(
    {
      schemaVersion: 3,
      id: "fixture-case",
      regions: [
        {
          id: "evidence",
          label: "Evidence",
          sourceAnchors: [{ page: 1, layer: "mixed", sectionPath: ["Evidence"] }],
          goldSection: "Evidence",
          kind: "mixed",
          modality: "mixed",
          uniqueEvidence: true,
          primaryAxis: "mixed_modality_fusion",
          secondaryAxes: ["image_description"],
          textOnlyRecoverable: false,
          budget: 1,
          leaves: [
            {
              id: "evidence.value",
              canonicalClaimId: "evidence.value",
              claimType: "scalar",
              expectation: `Record Alpha has value ${exactValue}.`,
              harm: 1,
              evidencePolicy: { type: "lexical", allOf: [["Record Alpha"], [exactValue]] },
            },
            {
              id: "evidence.visual",
              canonicalClaimId: "evidence.visual",
              claimType: "visual_description",
              expectation: "The red node is left of the blue node.",
              harm: 1,
              evidencePolicy: {
                type: "qualitative",
                requiredTerms: [["red node"], ["left"], ["blue node"]],
              },
            },
          ],
        },
      ],
    },
    { caseId: "fixture-case", pages: 1 },
  );
}

function runCase(facts: FactFile, reference = gold) {
  const factsText = `${JSON.stringify(facts, null, 2)}\n`;
  return auditReferenceCase({
    testCase: { id: "fixture-case", pages: 1, gold: "fixture/gold.md", facts: "fixture/facts.json" },
    gold: reference,
    factsText,
    facts,
  });
}

test("semantic citation lookup is confined to the declared gold section and returns a minimal set", () => {
  const sectionRefs = goldSectionLineRefs(gold, "Evidence");
  assert.deepEqual(sectionRefs, [3, 5, 7]);
  assert.deepEqual(
    minimalRequiredTermRefs(gold, sectionRefs, [["red node"], ["left"], ["blue node"]]),
    [7],
  );
  assert.deepEqual(goldSectionLineRefs(gold, "Missing section"), []);
});

test("canonical exact and semantic-only evidence self-scores at 100 deterministically", () => {
  const first = runCase(fixtureFacts());
  const second = runCase(fixtureFacts());
  assert.deepEqual(second, first);
  assert.equal(first.passed, true);
  assert.equal(first.score, 100);
  assert.equal(first.rawScore, 100);
  assert.equal(first.supportedLeaves, 2);
  assert.deepEqual(first.unsupportedLeafIds, []);
  assert.equal(first.leaves.find((leaf) => leaf.id === "evidence.value")?.resolution, "exact");
  assert.deepEqual(first.leaves.find((leaf) => leaf.id === "evidence.value")?.candidateLineRefs, [5]);
  assert.equal(first.leaves.find((leaf) => leaf.id === "evidence.visual")?.resolution, "semantic_only");
  assert.deepEqual(first.leaves.find((leaf) => leaf.id === "evidence.visual")?.candidateLineRefs, [7]);
  assert.equal(first.leaves.find((leaf) => leaf.id === "evidence.visual")?.semanticReviewRequired, true);
});

test("section-scoped exact refs distinguish resolver locality from unsupported reference evidence", () => {
  const splitReference = `# Fixture

## Evidence

Record Alpha is the controlled record.

Unrelated filler one.

Unrelated filler two.

Its value is 42.
`;
  const facts = fixtureFacts();
  facts.regions[0]!.leaves = [facts.regions[0]!.leaves[0]!];
  const audit = runCase(facts, splitReference);
  assert.equal(audit.passed, true);
  assert.equal(audit.score, 100);
  assert.equal(audit.leaves[0]!.resolution, "exact");
  assert.deepEqual(audit.leaves[0]!.candidateLineRefs, [5, 11]);
  assert.equal(audit.leaves[0]!.validatedStatus, "correct");
});

test("an exact policy unsupported by gold fails the case even though the submitted fixture says correct", () => {
  const audit = runCase(fixtureFacts("99"));
  assert.equal(audit.passed, false);
  assert.equal(audit.score, 50);
  assert.deepEqual(audit.unsupportedLeafIds, ["evidence.value"]);
  const leaf = audit.leaves.find((item) => item.id === "evidence.value");
  assert.equal(leaf?.resolution, "unsupported_exact");
  assert.equal(leaf?.policySupported, false);
  assert.equal(leaf?.validatedStatus, "missing");
});
