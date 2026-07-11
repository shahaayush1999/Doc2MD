import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import { resolveLeafEvidence, type FactLeaf } from "./evaluator.js";

type Facts = {
  id: string;
  regions: Array<{
    id: string;
    primaryAxis: string;
    goldSection: string;
    leaves: FactLeaf[];
  }>;
};

function fixture(expectation: string, claimType: FactLeaf["claimType"], evidencePolicy: FactLeaf["evidencePolicy"]): FactLeaf {
  return { id: "fixture", canonicalClaimId: "fixture", expectation, claimType, harm: 1, evidencePolicy } as FactLeaf;
}

function requireGate(name: string, text: string, leaf: FactLeaf, expected: "satisfied" | "noncontradictory") {
  const result = resolveLeafEvidence(text, leaf);
  const ok = expected === "satisfied" ? result?.satisfied === true : result?.contradiction !== true;
  if (!ok) throw new Error(`${name}: ${result?.reason ?? "no deterministic evidence policy"}`);
}

async function main() {
  const caseRoot = "benchmark/cases";
  const caseIds = (await readdir(caseRoot)).sort();
  const leafIds = new Set<string>();
  let regionCount = 0;
  let leafCount = 0;

  if (!(await readFile("benchmark/prompt.md", "utf8")).includes("faithful reconstruction")) {
    throw new Error("benchmark/prompt.md is missing or incomplete");
  }

  for (const caseId of caseIds) {
    const directory = path.join(caseRoot, caseId);
    const facts = JSON.parse(await readFile(path.join(directory, "facts.json"), "utf8")) as Facts;
    const gold = await readFile(path.join(directory, "gold.md"), "utf8");
    if (/Integrated reference conclusions|Cross-page entity lineage synthesis/i.test(gold)) {
      throw new Error(`${caseId}: gold contains authored synthesis absent from the source document`);
    }
    for (const region of facts.regions) {
      regionCount += 1;
      if (region.id.startsWith("x") || region.primaryAxis === "cross_page_join") {
        throw new Error(`${caseId}/${region.id}: hidden synthesis region is part of the official score`);
      }
      if (!gold.toLowerCase().includes(region.goldSection.toLowerCase())) {
        throw new Error(`${caseId}/${region.id}: declared gold section is absent: ${region.goldSection}`);
      }
      for (const leaf of region.leaves) {
        leafCount += 1;
        if (leaf.claimType === "cross_page_join") {
          throw new Error(`${caseId}/${leaf.id}: hidden synthesis leaf is part of the official score`);
        }
        const qualifiedId = `${caseId}/${leaf.id}`;
        if (leafIds.has(qualifiedId)) throw new Error(`${qualifiedId}: duplicate leaf id`);
        leafIds.add(qualifiedId);
      }
    }
  }

  requireGate(
    "bullet-pipe table",
    "Metric | Wafer 03 | Wafer 05\n- CD (nm) | 87 | 91",
    fixture("Wafer 03 CD is 87 nm.", "table_binding", {
      type: "table_binding", row: ["CD (nm)"], column: ["Wafer 03"], value: ["87"],
    }),
    "satisfied",
  );
  requireGate(
    "key-value list",
    "Control | Value | Interpretation\n- Base committed cost: $25,070 (implementation and validation)",
    fixture("Base committed cost is $25,070.", "table_binding", {
      type: "table_binding", row: ["Base committed cost"], column: ["Value"], value: ["$25,070"],
    }),
    "satisfied",
  );
  requireGate(
    "LaTeX directed edge",
    "### Internal patch paths\nPP-7/07 \\rightarrow CS-2/07 \\rightarrow D215-03",
    fixture("PP-7/07 patches to CS-2/07.", "directed_edge", {
      type: "directed_edge", source: ["PP-7/07"], destination: ["CS-2/07"], relation: ["patch"],
    }),
    "satisfied",
  );
  requireGate(
    "unrelated negation",
    "Physical cutover is GO for eligible inventory. It does not close EX-07.",
    fixture("Physical cutover is GO.", "scalar", { type: "lexical", allOf: [["Physical cutover"], ["GO"]] }),
    "satisfied",
  );
  requireGate(
    "wrong order is not a deterministic contradiction",
    "Final release, answered RFI, Revision C sheets.",
    fixture("Revision C precedes the answered RFI and final release.", "ordered_record", {
      type: "ordered_tokens", tokens: [["Revision C"], ["answered RFI"], ["final release"]],
    }),
    "noncontradictory",
  );

  console.log(`Audit passed: ${caseIds.length} cases, ${regionCount} regions, ${leafCount} scored leaves, 5 representation checks.`);
}

await main();
