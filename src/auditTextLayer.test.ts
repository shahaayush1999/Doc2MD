import assert from "node:assert/strict";
import test from "node:test";
import {
  auditNativeTextCase,
  auditNativeTextRegion,
  summarizeNativeTextExposure,
} from "./auditTextLayer.js";
import { parseFactFile, type FactFile } from "./score.js";

type FixtureOptions = {
  id?: string;
  page?: number;
  pages?: number;
  modality?: "native_text" | "raster" | "vector_geometry" | "mixed" | "native_layer_recovery";
  textOnlyRecoverable?: boolean;
  budget?: 1 | 2 | 3 | 4;
  qualitative?: boolean;
};

function fixtureFacts(options: FixtureOptions = {}): FactFile {
  const id = options.id ?? "fixture-case";
  const modality = options.modality ?? "native_text";
  const qualitative = options.qualitative ?? false;
  return parseFactFile(
    {
      schemaVersion: 3,
      id,
      regions: [
        {
          id: "evidence",
          label: "Evidence",
          sourceAnchors: [{ page: options.page ?? 1, layer: modality, sectionPath: ["Evidence"] }],
          goldSection: "Evidence",
          kind: qualitative ? "image" : "text",
          modality,
          uniqueEvidence: true,
          primaryAxis: qualitative ? "image_description" : "precise_recall",
          secondaryAxes: [],
          textOnlyRecoverable: options.textOnlyRecoverable ?? modality === "native_text",
          budget: options.budget ?? 1,
          leaves: [
            qualitative
              ? {
                  id: "evidence.visual",
                  canonicalClaimId: "evidence.visual",
                  claimType: "visual_description",
                  expectation: "The red node is visibly left of the blue node.",
                  harm: 2,
                  evidencePolicy: {
                    type: "qualitative",
                    requiredTerms: [["red node"], ["left"], ["blue node"]],
                  },
                }
              : {
                  id: "evidence.value",
                  canonicalClaimId: "evidence.value",
                  claimType: "scalar",
                  expectation: "Record Alpha is approved.",
                  harm: 2,
                  evidencePolicy: { type: "lexical", allOf: [["Record Alpha"], ["approved"]] },
                },
          ],
        },
      ],
    },
    { caseId: id, pages: options.pages ?? Math.max(1, options.page ?? 1) },
  );
}

function runFixture(facts: FactFile, pageTexts: string[]) {
  return auditNativeTextCase({
    testCase: {
      id: facts.id,
      pages: pageTexts.length,
      pdf: `benchmark/cases/${facts.id}/source.pdf`,
      facts: `benchmark/cases/${facts.id}/facts.json`,
    },
    facts,
    pageTexts,
  });
}

test("typed recovery is restricted to a region's source-anchor pages", () => {
  const facts = fixtureFacts({ pages: 2 });
  const exposed = auditNativeTextRegion(facts.regions[0]!, ["Record Alpha is approved.", ""]);
  assert.equal(exposed.exactRecoveredLeaves, 1);
  assert.equal(exposed.exactRecoveredHarm, 2);
  assert.equal(exposed.exactRecoveredBudget, 1);

  const leakedOnlyElsewhere = auditNativeTextRegion(facts.regions[0]!, ["No relevant statement.", "Record Alpha is approved."]);
  assert.equal(leakedOnlyElsewhere.exactRecoveredLeaves, 0);
  assert.equal(leakedOnlyElsewhere.unresolvedLeaves, 1);
  assert.equal(leakedOnlyElsewhere.exactRecoveredBudget, 0);
});

test("qualitative term potential is never promoted to exact recovery", () => {
  const facts = fixtureFacts({ qualitative: true });
  const audit = auditNativeTextRegion(facts.regions[0]!, ["The red node is left of the blue node."]);
  assert.equal(audit.exactRecoveredLeaves, 0);
  assert.equal(audit.semanticOnlyLeaves, 1);
  assert.equal(audit.semanticPotentialLeaves, 1);
  assert.equal(audit.semanticPotentialHarm, 2);
  assert.equal(audit.semanticPotentialBudget, 1);
  assert.equal(audit.leaves[0]!.humanReviewRequired, true);
  assert.equal(audit.leaves[0]!.semanticTermPotential, true);
});

test("fully exposed false declarations are hard contradictions outside native-layer recovery", () => {
  const mixedFacts = fixtureFacts({ modality: "mixed", textOnlyRecoverable: false });
  const mixed = auditNativeTextRegion(mixedFacts.regions[0]!, ["Record Alpha is approved."]);
  assert.equal(mixed.declaration.status, "hard_contradiction");
  assert.equal(mixed.declaration.code, "declared_not_recoverable_but_fully_exact");
  assert.equal(mixed.declaration.hard, true);

  const nativeLayerFacts = fixtureFacts({ modality: "native_layer_recovery", textOnlyRecoverable: false });
  const nativeLayer = auditNativeTextRegion(nativeLayerFacts.regions[0]!, ["Record Alpha is approved."]);
  assert.equal(nativeLayer.exactExposureRatio, 1);
  assert.equal(nativeLayer.declaration.status, "intentional_native_layer_exposure");
  assert.equal(nativeLayer.declaration.hard, false);
});

test("typed conflicts and unresolved leaves in true declarations remain explicit review gaps", () => {
  const facts = fixtureFacts();
  const contradiction = auditNativeTextRegion(facts.regions[0]!, ["Record Alpha is not approved."]);
  assert.equal(contradiction.contradictoryLeaves, 1);
  assert.equal(contradiction.declaration.status, "support_gap");
  assert.equal(contradiction.declaration.code, "declared_recoverable_native_text_policy_conflict");
  assert.equal(contradiction.declaration.hard, false);

  const unresolved = auditNativeTextRegion(facts.regions[0]!, ["Record Alpha review is pending."]);
  assert.equal(unresolved.unresolvedLeaves, 1);
  assert.equal(unresolved.declaration.status, "support_gap");
  assert.equal(unresolved.declaration.hard, false);
});

test("a true declaration with no native text is a hard contradiction", () => {
  const facts = fixtureFacts();
  const audit = auditNativeTextRegion(facts.regions[0]!, [""]);
  assert.equal(audit.declaration.status, "hard_contradiction");
  assert.equal(audit.declaration.code, "declared_recoverable_but_no_native_text");
  assert.equal(audit.declaration.hard, true);
});

test("suite exposure is equal-case rather than pooled-budget weighted", () => {
  const highBudgetFacts = fixtureFacts({ id: "case-a", budget: 4 });
  const lowBudgetFacts = fixtureFacts({ id: "case-b", budget: 1 });
  const cases = [
    runFixture(highBudgetFacts, ["Record Alpha is approved."]),
    runFixture(lowBudgetFacts, ["No relevant evidence."]),
  ];
  const report = summarizeNativeTextExposure({
    suite: "fixture",
    benchmarkVersion: "1.0.0",
    manifest: "fixture/manifest.json",
    manifestText: "fixture-manifest",
    cases,
  });
  assert.equal(report.summary.equalCaseExactExposureRatio, 0.5);
  assert.equal(report.summary.pooledExactExposureRatioDiagnosticOnly, 0.8);
  assert.equal(report.summary.passed, true);
  assert.equal(report.rollups.byCase[0]!.key, "case-a");
  assert.equal(report.rollups.byPrimaryAxis[0]!.key, "precise_recall");
  assert.equal(report.rollups.byModality[0]!.key, "native_text");
  assert.equal(report.rollups.byKind[0]!.key, "text");
});

test("case audit rejects page-count drift", () => {
  const facts = fixtureFacts({ pages: 2 });
  assert.throws(
    () =>
      auditNativeTextCase({
        testCase: {
          id: facts.id,
          pages: 2,
          pdf: `benchmark/cases/${facts.id}/source.pdf`,
          facts: `benchmark/cases/${facts.id}/facts.json`,
        },
        facts,
        pageTexts: ["one page only"],
      }),
    /expected 2/,
  );
});
