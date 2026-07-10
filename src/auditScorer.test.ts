import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";
import { assertReusableStoredAudit, buildCounterfactualCandidates } from "./auditScorer.js";
import { parseFactFile } from "./score.js";

const reference = `# Northstar

## 2. Cutover workplan and handoff sequence

workplan body

## 3. Commercial validation and invoice routing

| Vendor | PO | Cost center | Reviewer | Route |
| --- | --- | --- | --- | --- |
| Boreal Storage | 44018-3 | CC-7420 | Jonah Mercer | AP-West / transition |
| ThermoVision | 43991-2 | CC-7314 | Nadia Brooks | AP-Quality / validation |

Raster finance stamp: Jonah Mercer; 09 Jul 2026 16:42 MST; ceiling $28,070; control VC-2048; cost validation is not operational release.

| Marker | Meaning | Operational consequence |
| --- | --- | --- |
| OPEN | open | hold |

## 5. Final implementation authorization

**PHYSICAL CUTOVER: GO.** Begin at 14 Jul 2026 22:00 MST for eligible inventory only. **KESTREL CREDENTIAL DECOMMISSION: HOLD** until C-3 is satisfied.
`;

test("counterfactual suite changes exactly the intended construct once", () => {
  const variants = buildCounterfactualCandidates(reference);
  assert.equal(variants.reference, reference);
  assert.doesNotMatch(variants.omission, /workplan body/);
  assert.match(variants.omission, /Commercial validation/);
  assert.match(variants.substitution, /18:42 MST; ceiling \$28,070; control VC-9999/);
  assert.match(variants.misbinding, /Boreal Storage \| 43991-2 \| CC-7420/);
  assert.match(variants.misbinding, /ThermoVision \| 44018-3 \| CC-7314/);
  assert.match(variants.hallucination, /E-99/);
  assert.match(variants.source_precedence, /PHYSICAL CUTOVER: GO/);
  assert.match(variants.source_precedence, /Finance validation on page 3 overrides C-3/);
  assert.match(variants.source_precedence, /DECOMMISSION: RELEASED/);
});

test("counterfactual builder fails closed when the source fixture drifts", () => {
  assert.throws(() => buildCounterfactualCandidates(reference.replace("VC-2048", "VC-2049")), /fixture is stale/);
});

test("stored-judgment replay migrates legacy identity only under the unchanged scorer contract", () => {
  const current = {
    caseId: "P23-native-text-layer-recovery",
    fixtureInputFingerprint: "fixture-v1",
    legacyAuditInputFingerprint: "legacy-combined",
  };
  assert.doesNotThrow(() =>
    assertReusableStoredAudit(
      { caseId: current.caseId, auditInputFingerprint: "legacy-combined" },
      current,
    ),
  );
  assert.throws(
    () =>
      assertReusableStoredAudit(
        { caseId: current.caseId, auditInputFingerprint: "different-scorer-or-input" },
        current,
      ),
    /cannot be migrated/,
  );
});

test("migrated stored judgments ignore scorer-only drift but reject every fixture-input drift", () => {
  const current = {
    caseId: "P23-native-text-layer-recovery",
    fixtureInputFingerprint: "fixture-v1",
    legacyAuditInputFingerprint: "new-scorer-combined",
  };
  assert.doesNotThrow(() =>
    assertReusableStoredAudit(
      {
        caseId: current.caseId,
        fixtureInputFingerprint: "fixture-v1",
        auditInputFingerprint: "old-scorer-combined",
      },
      current,
    ),
  );
  assert.throws(
    () =>
      assertReusableStoredAudit(
        { caseId: current.caseId, fixtureInputFingerprint: "changed-fixture" },
        current,
      ),
    /case\/PDF\/gold\/facts\/candidate inputs/,
  );
  assert.throws(
    () =>
      assertReusableStoredAudit(
        { caseId: "P12-pfas-method-validation", fixtureInputFingerprint: "fixture-v1" },
        current,
      ),
    /not P23-native-text-layer-recovery/,
  );
});

test("counterfactual mutations are linked to scored P23 leaves", async () => {
  const [gold, factsValue] = await Promise.all([
    readFile("benchmark/cases/P23-native-text-layer-recovery/gold.md", "utf8"),
    readFile("benchmark/cases/P23-native-text-layer-recovery/facts.json", "utf8").then(JSON.parse),
  ]);
  const facts = parseFactFile(factsValue, { caseId: "P23-native-text-layer-recovery", pages: 5 });
  const leaves = new Map(facts.regions.flatMap((region) => region.leaves).map((leaf) => [leaf.id, leaf]));
  assert.deepEqual(leaves.get("p03.invoice.boreal-storage.po")?.evidencePolicy, {
    type: "table_binding",
    row: ["Boreal Storage"],
    column: ["PO"],
    value: ["44018-3"],
  });
  assert.deepEqual(leaves.get("p03.invoice.thermovision.po")?.evidencePolicy, {
    type: "table_binding",
    row: ["ThermoVision"],
    column: ["PO"],
    value: ["43991-2"],
  });
  const variants = buildCounterfactualCandidates(gold);
  assert.doesNotMatch(variants.misbinding, /Boreal Storage \| 44018-3/);
  assert.doesNotMatch(variants.misbinding, /ThermoVision \| 43991-2/);
  assert.match(variants.source_precedence, /PHYSICAL CUTOVER: GO/);
});
