import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import {
  discoverStructuredClosedWorldClaims,
  explicitCandidatePages,
  parseFactFile,
  resolveLeafEvidence,
  validateJudgeResult,
  type FactLeaf,
  type FactRegion,
} from "./evaluator.js";
import { loadBenchmarkManifest } from "./manifest.js";

function normalized(value: string) {
  return value
    .normalize("NFKC")
    .toLocaleLowerCase("und")
    .replace(/\\(?:longrightarrow|rightarrow|to)\b/g, "->")
    .replace(/\\(?:longleftarrow|leftarrow)\b/g, "<-")
    .replace(/[‐‑‒–—−]/g, "-")
    .replace(/→/g, "->")
    .replace(/←/g, "<-")
    .replace(/≤/g, "<=")
    .replace(/≥/g, ">=")
    .replace(/×/g, "x")
    .replace(/(?<=\p{N})(?=\p{L})|(?<=\p{L})(?=\p{N})/gu, " ")
    .replace(/[|*_`#]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function escapeRegex(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function containsWholePhrase(text: string, phrase: string) {
  const haystack = normalized(text);
  const needle = normalized(phrase);
  if (!needle) return false;
  const leftBoundary = /^[\p{L}\p{N}]/u.test(needle) ? "(?<![\\p{L}\\p{N}])" : "";
  const rightBoundary = /[\p{L}\p{N}]$/u.test(needle) ? "(?![\\p{L}\\p{N}])" : "";
  return new RegExp(`${leftBoundary}${escapeRegex(needle)}${rightBoundary}`, "u").test(haystack);
}

function goldSections(markdown: string, caseId: string) {
  const headings = [...markdown.matchAll(/^## (.+)$/gm)];
  const names = headings.map((heading) => heading[1]!.trim());
  const duplicates = [...new Set(names.filter((name, index) => names.indexOf(name) !== index))];
  if (duplicates.length > 0) {
    throw new Error(`${caseId}: duplicate level-two gold headings are ambiguous: ${duplicates.join(", ")}`);
  }
  return new Map(headings.map((heading, index) => [
    heading[1]!.trim(),
    markdown.slice(heading.index! + heading[0].length, headings[index + 1]?.index ?? markdown.length),
  ]));
}

function markdownTableColumnSets(section: string) {
  const lines = section.split("\n");
  const cells = (line: string) => line.includes("|")
    ? line.trim().replace(/^\|/, "").replace(/(?<!\\)\|$/, "").split(/(?<!\\)\|/).map((cell) => cell.replace(/\\\|/g, "|").trim())
    : null;
  const delimiter = (row: string[]) => row.length > 0 && row.every((cell) => /^:?-{3,}:?$/.test(cell.replace(/\s+/g, "")));
  const rowSets: Set<string>[] = [];
  for (let index = 0; index + 1 < lines.length; index += 1) {
    const header = cells(lines[index]!);
    const rule = cells(lines[index + 1]!);
    if (!header || !rule || header.length !== rule.length || !delimiter(rule)) continue;
    const columnSets = header.map(() => new Set<string>());
    for (let rowIndex = index + 2; rowIndex < lines.length; rowIndex += 1) {
      const row = cells(lines[rowIndex]!);
      if (!row || row.length !== header.length || delimiter(row)) break;
      row.forEach((value, columnIndex) => {
        if (normalized(value)) columnSets[columnIndex]!.add(normalized(value));
      });
    }
    rowSets.push(...columnSets.filter((values) => values.size > 0));
  }
  return rowSets;
}

function sameSet(left: Set<string>, right: Set<string>) {
  return left.size === right.size && [...left].every((value) => right.has(value));
}

function validateClosedWorld(caseId: string, region: FactRegion, goldSection: string) {
  if (!region.closedWorld) return;
  const internalIds = new Set(region.leaves.flatMap((leaf) => [normalized(leaf.id), normalized(leaf.canonicalClaimId)]));
  const leakedIds = region.closedWorld.keys.filter((key) => internalIds.has(normalized(key)));
  if (leakedIds.length > 0) {
    throw new Error(`${caseId}/${region.id}: closed-world members leak rubric ids: ${leakedIds.join(", ")}`);
  }

  const ungrounded = region.closedWorld.keys.filter((key) => !containsWholePhrase(goldSection, key));
  if (ungrounded.length > 0) {
    throw new Error(`${caseId}/${region.id}: closed-world members are absent from gold: ${ungrounded.join(", ")}`);
  }

  if (region.closedWorld.scope === "table_rows") {
    const declared = new Set(region.closedWorld.keys.map(normalized));
    const matches = markdownTableColumnSets(goldSection).filter((rowSet) => sameSet(rowSet, declared));
    if (matches.length !== 1) {
      throw new Error(
        `${caseId}/${region.id}: table_rows must exactly match one gold table column's member set (matched ${matches.length})`,
      );
    }
  }
}

function fixture(expectation: string, claimType: FactLeaf["claimType"], evidencePolicy: FactLeaf["evidencePolicy"]): FactLeaf {
  return { id: "fixture", canonicalClaimId: "fixture", expectation, claimType, harm: 1, evidencePolicy } as FactLeaf;
}

function requireGate(name: string, text: string, leaf: FactLeaf, expected: "satisfied" | "noncontradictory") {
  const result = resolveLeafEvidence(text, leaf);
  const ok = expected === "satisfied" ? result?.satisfied === true : result?.contradiction !== true;
  if (!ok) throw new Error(`${name}: ${result?.reason ?? "no deterministic evidence policy"}`);
}

export async function auditBenchmark() {
  const { manifest } = await loadBenchmarkManifest();
  const leafIds = new Set<string>();
  let regionCount = 0;
  let leafCount = 0;

  if (!(await readFile("benchmark/prompt.md", "utf8")).includes("faithful reconstruction")) {
    throw new Error("benchmark/prompt.md is missing or incomplete");
  }

  for (const testCase of manifest.cases) {
    const caseId = testCase.id;
    const facts = parseFactFile(JSON.parse(await readFile(testCase.facts, "utf8")), {
      caseId,
      pages: testCase.pages,
    });
    const gold = await readFile(testCase.gold, "utf8");
    const sections = goldSections(gold, caseId);
    for (const region of facts.regions) {
      regionCount += 1;
      const goldSection = sections.get(region.goldSection);
      if (goldSection === undefined) {
        throw new Error(`${caseId}/${region.id}: declared gold section is absent: ${region.goldSection}`);
      }
      validateClosedWorld(caseId, region, goldSection);
      for (const leaf of region.leaves) {
        leafCount += 1;
        const qualifiedId = `${caseId}/${leaf.id}`;
        if (leafIds.has(qualifiedId)) throw new Error(`${qualifiedId}: duplicate leaf id`);
        leafIds.add(qualifiedId);
      }
    }
  }

  requireGate(
    "bullet-pipe table",
    "Metric | Sample A | Sample B\n- Viscosity | 87 | 91",
    fixture("Sample A viscosity is 87.", "table_binding", {
      type: "table_binding", row: ["Viscosity"], column: ["Sample A"], value: ["87"],
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
    "### Directed links\nNODE-A \\rightarrow NODE-B \\rightarrow NODE-C",
    fixture("NODE-A connects to NODE-B.", "directed_edge", {
      type: "directed_edge", source: ["NODE-A"], destination: ["NODE-B"],
    }),
    "satisfied",
  );
  requireGate(
    "nested-bullet directed edge",
    "### Directed links\n- **NODE-A** → **NODE-B**\n  - Tagged trunk: `data`\n- **NODE-B** → **NODE-C**\n  - Tagged trunk: `control`",
    fixture("NODE-A sends data to NODE-B.", "directed_edge", {
      type: "directed_edge", source: ["NODE-A"], destination: ["NODE-B"], relation: ["data"],
    }),
    "satisfied",
  );
  requireGate(
    "nested-bullet dashed directed edge",
    "- **NODE-A** ⇢ **NODE-B**\n  - `optional trend`\n  - Dashed conditional edge",
    fixture("A dashed conditional trend runs from NODE-A to NODE-B.", "directed_edge", {
      type: "directed_edge", source: ["NODE-A"], destination: ["NODE-B"], relation: ["dashed", "conditional", "trend"],
    }),
    "satisfied",
  );
  requireGate(
    "unicode unchecked state",
    "- ☐ Production field updated",
    fixture("Production field updated is unchecked.", "scalar", {
      type: "lexical", allOf: [["Production field updated"], ["unchecked"]],
    }),
    "satisfied",
  );
  requireGate(
    "markdown unchecked state",
    "| State | Status |\n|---|---|\n| Production field updated | [ ] |",
    fixture("Production field updated is unchecked.", "scalar", {
      type: "lexical", allOf: [["Production field updated"], ["unchecked"]],
    }),
    "satisfied",
  );
  const reversedProse = resolveLeafEvidence(
    "NODE-A receives data from NODE-B.",
    fixture("NODE-A sends data to NODE-B.", "directed_edge", {
      type: "directed_edge", source: ["NODE-A"], destination: ["NODE-B"], relation: ["data"],
    }),
  );
  if (reversedProse?.satisfied || reversedProse?.contradiction !== true) {
    throw new Error("directed prose: a receive-from relation was not recognized as reversed");
  }
  const originatingFrom = resolveLeafEvidence(
    "CP-4 is the terminating point for a dashed blue data arrow originating from BAS-214.",
    fixture("A dashed data path runs from CP-4 to BAS-214.", "directed_edge", {
      type: "directed_edge", source: ["CP-4"], destination: ["BAS-214"], relation: ["data"],
    }),
  );
  if (originatingFrom?.satisfied || originatingFrom?.contradiction !== true) {
    throw new Error("directed prose: an originating-from relation was not recognized as reversed");
  }
  const leadingTo = resolveLeafEvidence(
    "BAS-214: Dashed blue line (BAS data) leading to CP-4.",
    fixture("A dashed data path runs from CP-4 to BAS-214.", "directed_edge", {
      type: "directed_edge", source: ["CP-4"], destination: ["BAS-214"], relation: ["data"],
    }),
  );
  if (leadingTo?.satisfied || leadingTo?.contradiction !== true) {
    throw new Error("directed prose: a leading-to relation was not recognized as reversed");
  }
  requireGate(
    "unrelated negation",
    "Release state is GO. It does not close unrelated item Z-9.",
    fixture("Release state is GO.", "scalar", { type: "lexical", allOf: [["Release state"], ["GO"]] }),
    "satisfied",
  );
  requireGate(
    "wrong order is not a deterministic contradiction",
    "Third step, second step, first step.",
    fixture("First step precedes second step and third step.", "ordered_record", {
      type: "ordered_tokens", tokens: [["First step"], ["second step"], ["third step"]],
    }),
    "noncontradictory",
  );
  requireGate(
    "numbered record with detail lines",
    "1. Alpha\ndetail for alpha\n\n2. Beta\ndetail for beta\n\n3. Gamma",
    fixture("The order is Alpha, Beta, Gamma.", "ordered_record", {
      type: "ordered_tokens", tokens: [["Alpha"], ["Beta"], ["Gamma"]],
    }),
    "satisfied",
  );
  requireGate(
    "colon-delimited schema",
    "Field: Controlled value",
    fixture("The schema is Field, Controlled value.", "structure", {
      type: "ordered_tokens", tokens: [["Field"], ["Controlled value"]],
    }),
    "satisfied",
  );
  const sparseCounterMap = explicitCandidatePages([
    "# First section",
    "Readable content that has no reliable page boundary.",
    "5 / 5",
  ], 5);
  if (sparseCounterMap.some((page) => page !== null)) {
    throw new Error("sparse page counter: one isolated footer incorrectly activated page scoping");
  }

  const shortFirstPageFooterMap = explicitCandidatePages([
    "# Short cover",
    "Only one line of page-one content.",
    "1 / 3",
    "---",
    "# Page two content",
    "Second-page detail.",
    "2 / 3",
    "---",
    "# Page three content",
    "Third-page detail.",
    "3 / 3",
  ], 3);
  const expectedFooterPages = [1, 1, 1, 2, 2, 2, 2, 3, 3, 3, 3];
  if (shortFirstPageFooterMap.some((page, index) => page !== expectedFooterPages[index])) {
    throw new Error("short first page: a complete footer sequence was incorrectly treated as page starts");
  }

  const closedTableFixture = parseFactFile({
    schemaVersion: 3,
    id: "closed-table-fixture",
    title: "Closed table fixture",
    family: "fixture",
    tags: ["fixture"],
    regions: [{
      id: "colors",
      label: "Color register",
      sourceAnchors: [{ page: 1, layer: "native_text", sectionPath: ["Color register"] }],
      goldSection: "Color register",
      kind: "table",
      modality: "native_text",
      uniqueEvidence: true,
      primaryAxis: "table_reconstruction",
      secondaryAxes: [],
      textOnlyRecoverable: true,
      budget: 1,
      closedWorld: { scope: "table_rows", keys: ["Red", "Blue"] },
      leaves: [
        {
          id: "red.state",
          canonicalClaimId: "red.state",
          claimType: "table_binding",
          expectation: "Red has state ready.",
          harm: 1,
          evidencePolicy: { type: "table_binding", row: ["Red"], column: ["State"], value: ["ready"] },
        },
        {
          id: "blue.state",
          canonicalClaimId: "blue.state",
          claimType: "table_binding",
          expectation: "Blue has state held.",
          harm: 1,
          evidencePolicy: { type: "table_binding", row: ["Blue"], column: ["State"], value: ["held"] },
        },
      ],
    }],
  }, { caseId: "closed-table-fixture", pages: 1 });
  const inventedRows = discoverStructuredClosedWorldClaims(
    closedTableFixture,
    "## Color register\n\n| Seq | Color | State |\n| --- | --- | --- |\n| 1 | Red | ready |\n| 2 | Blue | held |\n| 3 | Green | pending |",
  );
  if (inventedRows.length !== 1 || inventedRows[0]?.key !== "Green") {
    throw new Error("closed table labels: an invented non-identifier row was not isolated");
  }

  const wrongScopeRows = discoverStructuredClosedWorldClaims(
    closedTableFixture,
    "## Other register\n\n| Seq | Color | State |\n| --- | --- | --- |\n| 1 | Red | ready |\n| 2 | Blue | held |\n| 3 | Green | pending |",
  );
  if (wrongScopeRows.length !== 0) {
    throw new Error("closed table scope: a similarly shaped table in another region was misattributed");
  }

  const contradictedTable = validateJudgeResult(closedTableFixture, {
    leafResults: [
      { id: "red.state", status: "correct", candidateLineRefs: [3] },
      { id: "blue.state", status: "correct", candidateLineRefs: [4] },
    ],
    unsupportedClaims: [],
    rationale: "Fixture intentionally claims both rows are correct.",
  }, "| Color | State |\n| --- | --- |\n| Red | blocked |\n| Blue | held |");
  if (contradictedTable.leafResults.find((item) => item.id === "red.state")?.status !== "incorrect") {
    throw new Error("table contradiction: a model's correct label overrode a contradictory bound value");
  }

  console.log(`Audit passed: ${manifest.cases.length} cases, ${regionCount} regions, ${leafCount} scored leaves, 18 representation checks.`);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) await auditBenchmark();
