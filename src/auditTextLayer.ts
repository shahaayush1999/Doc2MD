import { execFile } from "node:child_process";
import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";
import { promisify } from "node:util";
import { fileURLToPath } from "node:url";
import { fileSha256, hashObject, sha256 } from "./cache.js";
import {
  canonicalProjectReference,
  loadBenchmarkManifest,
  resolveInsideProject,
  type BenchmarkManifestCase,
} from "./manifest.js";
import { atomicWriteJson } from "./runRuntime.js";
import {
  parseFactFile,
  resolveLeafEvidence,
  scoringContractFingerprint,
  scoringContractVersion,
  type FactFile,
  type FactLeaf,
  type FactRegion,
} from "./score.js";

const execFileAsync = promisify(execFile);
const defaultManifest = "benchmark/manifest.json";
const defaultOutput = "reports/text-layer-exposure-audit.json";
const extractionMode = "poppler-pdftotext-page-scoped-layout-utf8-v1";

export type NativeTextLeafResolution = "exact" | "contradictory" | "unresolved" | "semantic_only";

export type NativeTextLeafAudit = {
  id: string;
  canonicalClaimId: string;
  policyType: FactLeaf["evidencePolicy"]["type"];
  harm: 1 | 2;
  resolution: NativeTextLeafResolution;
  semanticTermPotential: boolean | null;
  humanReviewRequired: boolean;
  extractedLineRefs: number[];
  reason: string | null;
};

export type DeclarationAssessment = {
  status:
    | "consistent_exact"
    | "consistent_not_fully_exposed"
    | "support_gap"
    | "possible_false_declaration"
    | "hard_contradiction"
    | "intentional_native_layer_exposure";
  hard: boolean;
  code: string | null;
  explanation: string;
};

export type NativeTextRegionAudit = {
  id: string;
  label: string;
  pages: number[];
  anchorLayers: FactRegion["modality"][];
  kind: FactRegion["kind"];
  modality: FactRegion["modality"];
  primaryAxis: FactRegion["primaryAxis"];
  textOnlyRecoverable: boolean;
  budget: number;
  nativeTextCharacters: number;
  nativeTextLines: number;
  leafCount: number;
  leafHarm: number;
  exactRecoveredLeaves: number;
  exactRecoveredHarm: number;
  contradictoryLeaves: number;
  contradictoryHarm: number;
  unresolvedLeaves: number;
  unresolvedHarm: number;
  semanticOnlyLeaves: number;
  semanticOnlyHarm: number;
  semanticPotentialLeaves: number;
  semanticPotentialHarm: number;
  exactRecoveredBudget: number;
  semanticPotentialBudget: number;
  exactPlusSemanticPotentialBudget: number;
  exactExposureRatio: number;
  exactPlusSemanticPotentialRatio: number;
  declaration: DeclarationAssessment;
  leaves: NativeTextLeafAudit[];
};

export type ExposureRollup = {
  key: string;
  regionCount: number;
  leafCount: number;
  leafHarm: number;
  exactRecoveredLeaves: number;
  exactRecoveredHarm: number;
  contradictoryLeaves: number;
  contradictoryHarm: number;
  unresolvedLeaves: number;
  unresolvedHarm: number;
  semanticOnlyLeaves: number;
  semanticOnlyHarm: number;
  semanticPotentialLeaves: number;
  semanticPotentialHarm: number;
  totalBudget: number;
  exactRecoveredBudget: number;
  semanticPotentialBudget: number;
  exactPlusSemanticPotentialBudget: number;
  exactExposureRatio: number;
  exactPlusSemanticPotentialRatio: number;
};

export type NativeTextPageAudit = {
  page: number;
  characters: number;
  nonblankLines: number;
  words: number;
  sha256: string;
};

export type NativeTextCaseAudit = {
  id: string;
  pages: number;
  pdf: string;
  facts: string;
  pdfSha256: string;
  factsSha256: string;
  pageNativeText: NativeTextPageAudit[];
  rollup: ExposureRollup;
  hardDeclarationContradictions: number;
  declarationReviewItems: number;
  regions: NativeTextRegionAudit[];
};

export type NativeTextExposureAudit = {
  schemaVersion: 1;
  audit: "native-text-layer-exposure";
  suite: string;
  benchmarkVersion: string;
  manifest: string;
  manifestSha256: string;
  scoringContractVersion: string;
  scoringContractFingerprint: string;
  extractionMode: typeof extractionMode;
  providerCalls: 0;
  interpretation: {
    metric: string;
    exactRecoveredBudget: string;
    semanticPotential: string;
    equalCaseAggregation: string;
    nativeLayerRecovery: string;
    hardDeclarationContradiction: string;
  };
  auditInputFingerprint: string;
  summary: {
    caseCount: number;
    regionCount: number;
    leafCount: number;
    hardDeclarationContradictions: number;
    declarationReviewItems: number;
    exactRecoveredHarm: number;
    leafHarm: number;
    exactRecoveredBudget: number;
    totalBudget: number;
    pooledExactExposureRatioDiagnosticOnly: number;
    equalCaseExactExposureRatio: number;
    equalCaseExactPlusSemanticPotentialRatio: number;
    humanReviewRequired: boolean;
    passed: boolean;
  };
  rollups: {
    byCase: ExposureRollup[];
    byPrimaryAxis: ExposureRollup[];
    byModality: ExposureRollup[];
    byKind: ExposureRollup[];
  };
  cases: NativeTextCaseAudit[];
};

function round(value: number, digits = 6): number {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function ratio(numerator: number, denominator: number): number {
  return denominator === 0 ? 0 : round(numerator / denominator);
}

function normalizeEvidenceText(value: string): string {
  return value
    .normalize("NFKC")
    .toLowerCase()
    .replace(/[‐‑‒–—−]/g, "-")
    .replace(/→/g, "->")
    .replace(/←/g, "<-")
    .replace(/≤/g, "<=")
    .replace(/≥/g, ">=")
    .replace(/×/g, "x")
    .replace(/°\s*c\b/g, " c")
    .replace(/(\d)([a-z])/g, "$1 $2")
    .replace(/([a-z])(\d)/g, "$1 $2")
    .replace(/\r?\n|\|/g, " . ")
    .replace(/[*_`#]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

function phraseIndex(text: string, phrase: string): number {
  let offset = 0;
  while (offset <= text.length) {
    const index = text.indexOf(phrase, offset);
    if (index < 0) return -1;
    const before = index === 0 ? "" : text[index - 1]!;
    const afterIndex = index + phrase.length;
    const after = afterIndex >= text.length ? "" : text[afterIndex]!;
    const beginsWord = /^[a-z0-9]/.test(phrase);
    const endsWord = /[a-z0-9]$/.test(phrase);
    if ((!beginsWord || !/[a-z0-9]/.test(before)) && (!endsWord || !/[a-z0-9]/.test(after))) return index;
    offset = index + 1;
  }
  return -1;
}

function hasAlternative(text: string, alternatives: string[]): boolean {
  return alternatives.some((alternative) => {
    const normalized = normalizeEvidenceText(alternative);
    return normalized.length > 0 && phraseIndex(text, normalized) >= 0;
  });
}

function qualitativeTermPotential(candidate: string, leaf: FactLeaf): boolean {
  if (leaf.evidencePolicy.type !== "qualitative") return false;
  const text = normalizeEvidenceText(candidate);
  return leaf.evidencePolicy.requiredTerms.every((alternatives) => hasAlternative(text, alternatives));
}

function pageCandidate(pageTexts: readonly string[], pages: readonly number[]): string {
  return pages.map((page) => pageTexts[page - 1] ?? "").join("\n\n");
}

function assessDeclaration(input: {
  region: FactRegion;
  nativeTextCharacters: number;
  exactRecoveredLeaves: number;
  contradictoryLeaves: number;
  unresolvedLeaves: number;
  semanticOnlyLeaves: number;
  semanticPotentialLeaves: number;
}): DeclarationAssessment {
  const { region } = input;
  const allLeavesExact = input.exactRecoveredLeaves === region.leaves.length;
  const allLeavesPotentiallyExposed =
    input.exactRecoveredLeaves + input.semanticPotentialLeaves === region.leaves.length &&
    input.unresolvedLeaves === 0 &&
    input.contradictoryLeaves === 0;

  if (region.textOnlyRecoverable) {
    if (input.nativeTextCharacters === 0) {
      return {
        status: "hard_contradiction",
        hard: true,
        code: "declared_recoverable_but_no_native_text",
        explanation: "The region is declared text-only recoverable, but its anchor pages expose no native text.",
      };
    }
    if (input.contradictoryLeaves > 0) {
      return {
        status: "support_gap",
        hard: false,
        code: "declared_recoverable_native_text_policy_conflict",
        explanation:
          "The typed resolver reports a polarity or binding conflict on native text. This is a declaration review item, not a hard contradiction, because plain-text extraction can collapse table columns or clause boundaries.",
      };
    }
    if (allLeavesExact) {
      return {
        status: "consistent_exact",
        hard: false,
        code: null,
        explanation: "Every scored leaf is deterministically recoverable from anchor-page native text.",
      };
    }
    return {
      status: "support_gap",
      hard: false,
      code: "declared_recoverable_not_deterministically_verified",
      explanation:
        input.semanticOnlyLeaves > 0 && allLeavesPotentiallyExposed
          ? "Exact policies pass and qualitative terms are present, but semantic correctness still requires human review."
          : "The deterministic resolver does not verify every leaf from anchor-page native text; review the declaration and extraction limits.",
    };
  }

  // Native-layer recovery is deliberately a distinct construct: its scored
  // content may be present in a hidden/malformed native layer even though the
  // visible page cannot be faithfully reconstructed from plain extracted text.
  // Count that exposure in the metric, but do not rewrite it as a declaration
  // error merely because extraction succeeds.
  if (region.modality === "native_layer_recovery" && (allLeavesExact || allLeavesPotentiallyExposed)) {
    return {
      status: "intentional_native_layer_exposure",
      hard: false,
      code: "native_layer_recovery_exposed",
      explanation:
        "Anchor-page native text exposes the scored content; this is counted as exposure while the malformed visible layout remains a separate recovery construct.",
    };
  }
  if (allLeavesExact) {
    return {
      status: "hard_contradiction",
      hard: true,
      code: "declared_not_recoverable_but_fully_exact",
      explanation: "Every scored leaf is deterministically recoverable from native text despite the false declaration.",
    };
  }
  if (allLeavesPotentiallyExposed) {
    return {
      status: "possible_false_declaration",
      hard: false,
      code: "declared_not_recoverable_but_semantic_terms_present",
      explanation: "All exact leaves resolve and all qualitative term groups are present; semantic review is required before calling this a contradiction.",
    };
  }
  return {
    status: "consistent_not_fully_exposed",
    hard: false,
    code: null,
    explanation: "At least one scored leaf is not recoverable from anchor-page native text under the deterministic policy audit.",
  };
}

export function auditNativeTextRegion(region: FactRegion, pageTexts: readonly string[]): NativeTextRegionAudit {
  const pages = [...new Set(region.sourceAnchors.map((anchor) => anchor.page))].sort((left, right) => left - right);
  const anchorLayers = [...new Set(region.sourceAnchors.map((anchor) => anchor.layer))].sort();
  const candidate = pageCandidate(pageTexts, pages);
  const leaves: NativeTextLeafAudit[] = region.leaves.map((leaf) => {
    const resolution = resolveLeafEvidence(candidate, leaf);
    if (resolution === null) {
      return {
        id: leaf.id,
        canonicalClaimId: leaf.canonicalClaimId,
        policyType: leaf.evidencePolicy.type,
        harm: leaf.harm,
        resolution: "semantic_only",
        semanticTermPotential: qualitativeTermPotential(candidate, leaf),
        humanReviewRequired: true,
        extractedLineRefs: [],
        reason: "Qualitative term co-occurrence is only an exposure signal; semantic correctness requires human review.",
      };
    }
    return {
      id: leaf.id,
      canonicalClaimId: leaf.canonicalClaimId,
      policyType: leaf.evidencePolicy.type,
      harm: leaf.harm,
      resolution: resolution.satisfied ? "exact" : resolution.contradiction ? "contradictory" : "unresolved",
      semanticTermPotential: null,
      humanReviewRequired: false,
      extractedLineRefs: resolution.candidateLineRefs ?? [],
      reason: resolution.reason ?? null,
    };
  });
  const leafHarm = leaves.reduce((sum, leaf) => sum + leaf.harm, 0);
  const exact = leaves.filter((leaf) => leaf.resolution === "exact");
  const contradictory = leaves.filter((leaf) => leaf.resolution === "contradictory");
  const unresolved = leaves.filter((leaf) => leaf.resolution === "unresolved");
  const semanticOnly = leaves.filter((leaf) => leaf.resolution === "semantic_only");
  const semanticPotential = semanticOnly.filter((leaf) => leaf.semanticTermPotential);
  const exactRecoveredHarm = exact.reduce((sum, leaf) => sum + leaf.harm, 0);
  const contradictoryHarm = contradictory.reduce((sum, leaf) => sum + leaf.harm, 0);
  const unresolvedHarm = unresolved.reduce((sum, leaf) => sum + leaf.harm, 0);
  const semanticOnlyHarm = semanticOnly.reduce((sum, leaf) => sum + leaf.harm, 0);
  const semanticPotentialHarm = semanticPotential.reduce((sum, leaf) => sum + leaf.harm, 0);
  const exactRecoveredBudget = leafHarm === 0 ? 0 : round((region.budget * exactRecoveredHarm) / leafHarm);
  const semanticPotentialBudget = leafHarm === 0 ? 0 : round((region.budget * semanticPotentialHarm) / leafHarm);
  const nativeTextCharacters = candidate.replace(/\s/g, "").length;
  const declaration = assessDeclaration({
    region,
    nativeTextCharacters,
    exactRecoveredLeaves: exact.length,
    contradictoryLeaves: contradictory.length,
    unresolvedLeaves: unresolved.length,
    semanticOnlyLeaves: semanticOnly.length,
    semanticPotentialLeaves: semanticPotential.length,
  });
  return {
    id: region.id,
    label: region.label,
    pages,
    anchorLayers,
    kind: region.kind,
    modality: region.modality,
    primaryAxis: region.primaryAxis,
    textOnlyRecoverable: region.textOnlyRecoverable,
    budget: region.budget,
    nativeTextCharacters,
    nativeTextLines: candidate.split("\n").filter((line) => line.trim()).length,
    leafCount: leaves.length,
    leafHarm,
    exactRecoveredLeaves: exact.length,
    exactRecoveredHarm,
    contradictoryLeaves: contradictory.length,
    contradictoryHarm,
    unresolvedLeaves: unresolved.length,
    unresolvedHarm,
    semanticOnlyLeaves: semanticOnly.length,
    semanticOnlyHarm,
    semanticPotentialLeaves: semanticPotential.length,
    semanticPotentialHarm,
    exactRecoveredBudget,
    semanticPotentialBudget,
    exactPlusSemanticPotentialBudget: round(exactRecoveredBudget + semanticPotentialBudget),
    exactExposureRatio: ratio(exactRecoveredHarm, leafHarm),
    exactPlusSemanticPotentialRatio: ratio(exactRecoveredHarm + semanticPotentialHarm, leafHarm),
    declaration,
    leaves,
  };
}

function rollup(key: string, regions: readonly NativeTextRegionAudit[]): ExposureRollup {
  const totalBudget = regions.reduce((sum, region) => sum + region.budget, 0);
  const exactRecoveredBudget = round(regions.reduce((sum, region) => sum + region.exactRecoveredBudget, 0));
  const semanticPotentialBudget = round(regions.reduce((sum, region) => sum + region.semanticPotentialBudget, 0));
  const exactPlusSemanticPotentialBudget = round(exactRecoveredBudget + semanticPotentialBudget);
  return {
    key,
    regionCount: regions.length,
    leafCount: regions.reduce((sum, region) => sum + region.leafCount, 0),
    leafHarm: regions.reduce((sum, region) => sum + region.leafHarm, 0),
    exactRecoveredLeaves: regions.reduce((sum, region) => sum + region.exactRecoveredLeaves, 0),
    exactRecoveredHarm: regions.reduce((sum, region) => sum + region.exactRecoveredHarm, 0),
    contradictoryLeaves: regions.reduce((sum, region) => sum + region.contradictoryLeaves, 0),
    contradictoryHarm: regions.reduce((sum, region) => sum + region.contradictoryHarm, 0),
    unresolvedLeaves: regions.reduce((sum, region) => sum + region.unresolvedLeaves, 0),
    unresolvedHarm: regions.reduce((sum, region) => sum + region.unresolvedHarm, 0),
    semanticOnlyLeaves: regions.reduce((sum, region) => sum + region.semanticOnlyLeaves, 0),
    semanticOnlyHarm: regions.reduce((sum, region) => sum + region.semanticOnlyHarm, 0),
    semanticPotentialLeaves: regions.reduce((sum, region) => sum + region.semanticPotentialLeaves, 0),
    semanticPotentialHarm: regions.reduce((sum, region) => sum + region.semanticPotentialHarm, 0),
    totalBudget,
    exactRecoveredBudget,
    semanticPotentialBudget,
    exactPlusSemanticPotentialBudget,
    exactExposureRatio: ratio(exactRecoveredBudget, totalBudget),
    exactPlusSemanticPotentialRatio: ratio(exactPlusSemanticPotentialBudget, totalBudget),
  };
}

function groupedRollups(
  regions: readonly NativeTextRegionAudit[],
  keyOf: (region: NativeTextRegionAudit) => string,
): ExposureRollup[] {
  const groups = new Map<string, NativeTextRegionAudit[]>();
  for (const region of regions) {
    const key = keyOf(region);
    groups.set(key, [...(groups.get(key) ?? []), region]);
  }
  return [...groups.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, group]) => rollup(key, group));
}

export function auditNativeTextCase(input: {
  testCase: Pick<BenchmarkManifestCase, "id" | "pages" | "pdf" | "facts">;
  facts: FactFile;
  pageTexts: readonly string[];
  pdfSha256?: string;
  factsSha256?: string;
}): NativeTextCaseAudit {
  if (input.pageTexts.length !== input.testCase.pages) {
    throw new Error(
      `${input.testCase.id} native text extraction returned ${input.pageTexts.length} pages; expected ${input.testCase.pages}.`,
    );
  }
  const regions = input.facts.regions.map((region) => auditNativeTextRegion(region, input.pageTexts));
  return {
    id: input.testCase.id,
    pages: input.testCase.pages,
    pdf: input.testCase.pdf,
    facts: input.testCase.facts,
    pdfSha256: input.pdfSha256 ?? "fixture",
    factsSha256: input.factsSha256 ?? "fixture",
    pageNativeText: input.pageTexts.map((text, index) => ({
      page: index + 1,
      characters: text.replace(/\s/g, "").length,
      nonblankLines: text.split("\n").filter((line) => line.trim()).length,
      words: text.match(/\S+/g)?.length ?? 0,
      sha256: sha256(text),
    })),
    rollup: rollup(input.testCase.id, regions),
    hardDeclarationContradictions: regions.filter((region) => region.declaration.hard).length,
    declarationReviewItems: regions.filter((region) =>
      ["support_gap", "possible_false_declaration", "intentional_native_layer_exposure"].includes(region.declaration.status),
    ).length,
    regions,
  };
}

export function summarizeNativeTextExposure(input: {
  suite: string;
  benchmarkVersion: string;
  manifest: string;
  manifestText: string;
  cases: NativeTextCaseAudit[];
}): NativeTextExposureAudit {
  const allRegions = input.cases.flatMap((testCase) => testCase.regions);
  const byCase = input.cases.map((testCase) => testCase.rollup);
  const exactRecoveredBudget = round(byCase.reduce((sum, item) => sum + item.exactRecoveredBudget, 0));
  const totalBudget = byCase.reduce((sum, item) => sum + item.totalBudget, 0);
  const equalCaseExactExposureRatio = round(
    byCase.reduce((sum, item) => sum + item.exactExposureRatio, 0) / Math.max(1, byCase.length),
  );
  const equalCaseExactPlusSemanticPotentialRatio = round(
    byCase.reduce((sum, item) => sum + item.exactPlusSemanticPotentialRatio, 0) / Math.max(1, byCase.length),
  );
  const hardDeclarationContradictions = input.cases.reduce(
    (sum, testCase) => sum + testCase.hardDeclarationContradictions,
    0,
  );
  const declarationReviewItems = input.cases.reduce((sum, testCase) => sum + testCase.declarationReviewItems, 0);
  const auditInputFingerprint = hashObject({
    schemaVersion: 1,
    manifestSha256: sha256(input.manifestText),
    scoringContractFingerprint,
    extractionMode,
    cases: input.cases.map((testCase) => ({
      id: testCase.id,
      pdfSha256: testCase.pdfSha256,
      factsSha256: testCase.factsSha256,
      pageNativeTextSha256: testCase.pageNativeText.map((page) => page.sha256),
    })),
  });
  return {
    schemaVersion: 1,
    audit: "native-text-layer-exposure",
    suite: input.suite,
    benchmarkVersion: input.benchmarkVersion,
    manifest: input.manifest,
    manifestSha256: sha256(input.manifestText),
    scoringContractVersion,
    scoringContractFingerprint,
    extractionMode,
    providerCalls: 0,
    interpretation: {
      metric:
        "Exposure upper bound from raw anchor-page native text under deterministic typed evidence policies; it is not a model score or performance estimate.",
      exactRecoveredBudget:
        "For each region: region budget multiplied by exact recovered leaf harm divided by total leaf harm.",
      semanticPotential:
        "Qualitative required-term presence is reported separately and always requires human semantic review; it is never promoted to exact recovery.",
      equalCaseAggregation:
        "Suite exposure is the arithmetic mean of case exposure ratios, giving every case equal weight; pooled budget exposure is diagnostic only.",
      nativeLayerRecovery:
        "Native-layer recovery exposure is counted even when visible layout is malformed; successful extraction does not assert faithful visual reconstruction.",
      hardDeclarationContradiction:
        "Release fails only when a true declaration has no native text on its anchor pages, or a false non-native-layer declaration has every leaf deterministically exact. Resolver conflicts and unresolved leaves remain review items because plain-text extraction can collapse columns and clause boundaries.",
    },
    auditInputFingerprint,
    summary: {
      caseCount: input.cases.length,
      regionCount: allRegions.length,
      leafCount: allRegions.reduce((sum, region) => sum + region.leafCount, 0),
      hardDeclarationContradictions,
      declarationReviewItems,
      exactRecoveredHarm: allRegions.reduce((sum, region) => sum + region.exactRecoveredHarm, 0),
      leafHarm: allRegions.reduce((sum, region) => sum + region.leafHarm, 0),
      exactRecoveredBudget,
      totalBudget,
      pooledExactExposureRatioDiagnosticOnly: ratio(exactRecoveredBudget, totalBudget),
      equalCaseExactExposureRatio,
      equalCaseExactPlusSemanticPotentialRatio,
      humanReviewRequired:
        declarationReviewItems > 0 || allRegions.some((region) => region.semanticOnlyLeaves > 0),
      passed: hardDeclarationContradictions === 0,
    },
    rollups: {
      byCase,
      byPrimaryAxis: groupedRollups(allRegions, (region) => region.primaryAxis),
      byModality: groupedRollups(allRegions, (region) => region.modality),
      byKind: groupedRollups(allRegions, (region) => region.kind),
    },
    cases: input.cases,
  };
}

export async function extractNativeTextPages(
  pdfPath: string,
  pageCount: number,
  executable = process.env.PDFTOTEXT_BIN || "pdftotext",
): Promise<string[]> {
  const pages: string[] = [];
  for (let page = 1; page <= pageCount; page += 1) {
    const { stdout } = await execFileAsync(
      executable,
      ["-f", String(page), "-l", String(page), "-layout", "-enc", "UTF-8", pdfPath, "-"],
      { encoding: "utf8", maxBuffer: 32 * 1024 * 1024 },
    );
    pages.push(stdout.replace(/\r\n/g, "\n").replace(/\f+$/g, "").replace(/\s+$/g, ""));
  }
  return pages;
}

export async function buildNativeTextExposureAudit(manifestReference = defaultManifest): Promise<NativeTextExposureAudit> {
  const loaded = await loadBenchmarkManifest(manifestReference);
  const cases: NativeTextCaseAudit[] = [];
  for (const testCase of loaded.manifest.cases) {
    const [factsText, pdfSha256, factsSha256, pageTexts] = await Promise.all([
      readFile(resolveInsideProject(testCase.facts), "utf8"),
      fileSha256(resolveInsideProject(testCase.pdf)),
      fileSha256(resolveInsideProject(testCase.facts)),
      extractNativeTextPages(resolveInsideProject(testCase.pdf), testCase.pages),
    ]);
    const facts = parseFactFile(JSON.parse(factsText), { caseId: testCase.id, pages: testCase.pages });
    cases.push(auditNativeTextCase({ testCase, facts, pageTexts, pdfSha256, factsSha256 }));
  }
  return summarizeNativeTextExposure({
    suite: loaded.manifest.suite,
    benchmarkVersion: loaded.manifest.version,
    manifest: canonicalProjectReference(loaded.manifestPath),
    manifestText: loaded.manifestText,
    cases,
  });
}

type CliOptions = { manifest?: string; output?: string };

function parseCli(args: string[]): CliOptions {
  const options: CliOptions = {};
  for (let index = 0; index < args.length; index += 1) {
    const argument = args[index]!;
    if (argument === "--manifest" || argument === "--output") {
      const value = args[index + 1];
      if (!value) throw new Error(`${argument} requires a value.`);
      if (argument === "--manifest") options.manifest = value;
      else options.output = value;
      index += 1;
      continue;
    }
    throw new Error(`Unknown argument: ${argument}`);
  }
  return options;
}

export async function auditNativeTextExposure(options: CliOptions = {}): Promise<NativeTextExposureAudit> {
  const output = options.output ?? defaultOutput;
  const audit = await buildNativeTextExposureAudit(options.manifest ?? defaultManifest);
  const outputPath = path.resolve(output);
  await mkdir(path.dirname(outputPath), { recursive: true });
  await atomicWriteJson(outputPath, audit);
  if (!audit.summary.passed) {
    throw new Error(
      `Native-text exposure audit found ${audit.summary.hardDeclarationContradictions} hard declaration contradictions. ` +
        `Inspect ${canonicalProjectReference(outputPath)}.`,
    );
  }
  return audit;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const audit = await auditNativeTextExposure(parseCli(process.argv.slice(2)));
  console.log(
    `Native-text exposure audit passed: equal-case exact exposure ${round(audit.summary.equalCaseExactExposureRatio * 100, 2)}%; ` +
      `${audit.summary.declarationReviewItems} declaration review items; provider calls 0.`,
  );
}
