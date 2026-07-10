import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { hashObject, sha256 } from "./cache.js";
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
  scoreAtomicRegions,
  scoringContractFingerprint,
  scoringContractVersion,
  validateJudgeResult,
  type FactFile,
  type FactLeaf,
} from "./score.js";

const defaultManifest = "benchmark/manifest.json";
const defaultOutput = "reports/reference-evidence-audit.json";

type ExactResolution = Exclude<ReturnType<typeof resolveLeafEvidence>, null>;
type ReferenceResolution =
  | "exact"
  | "exact_derived"
  | "semantic_only"
  | "unsupported_exact"
  | "unsupported_semantic";

export type ReferenceLeafAudit = {
  id: string;
  canonicalClaimId: string;
  regionId: string;
  goldSection: string;
  policyType: FactLeaf["evidencePolicy"]["type"];
  resolution: ReferenceResolution;
  policySupported: boolean;
  semanticReviewRequired: boolean;
  candidateLineRefs: number[];
  validatedCandidateLineRefs: number[];
  validatedStatus: "correct" | "missing" | "incorrect";
  reason: string | null;
};

export type ReferenceCaseAudit = {
  id: string;
  pages: number;
  gold: string;
  facts: string;
  goldSha256: string;
  factsSha256: string;
  regionCount: number;
  leafCount: number;
  policyCounts: Record<string, number>;
  exactPolicyLeaves: number;
  semanticOnlyLeaves: number;
  supportedLeaves: number;
  unsupportedLeafIds: string[];
  score: number;
  rawScore: number;
  statusHarm: { correct: number; missing: number; incorrect: number };
  unsupportedClaimCount: number;
  passed: boolean;
  leaves: ReferenceLeafAudit[];
};

export type ReferenceEvidenceAudit = {
  schemaVersion: 1;
  audit: "canonical-reference-evidence-self-audit";
  suite: string;
  benchmarkVersion: string;
  manifest: string;
  manifestSha256: string;
  scoringContractVersion: string;
  scoringContractFingerprint: string;
  auditInputFingerprint: string;
  providerCalls: 0;
  canonicalJudgmentsPerCase: 1;
  humanReviewRequired: boolean;
  summary: {
    caseCount: number;
    casesAt100: number;
    regionCount: number;
    leafCount: number;
    supportedLeaves: number;
    unsupportedLeaves: number;
    exactPolicyLeaves: number;
    semanticOnlyLeaves: number;
    passed: boolean;
  };
  cases: ReferenceCaseAudit[];
};

function normalizedEvidenceText(value: string): string {
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

function containsAlternative(text: string, alternatives: string[]): boolean {
  return alternatives.some((alternative) => {
    const normalized = normalizedEvidenceText(alternative);
    return normalized.length > 0 && phraseIndex(text, normalized) >= 0;
  });
}

function compareReferenceSets(left: number[], right: number[]): number {
  if (left.length !== right.length) return left.length - right.length;
  const leftSpan = left.length === 0 ? 0 : left[left.length - 1]! - left[0]!;
  const rightSpan = right.length === 0 ? 0 : right[right.length - 1]! - right[0]!;
  if (leftSpan !== rightSpan) return leftSpan - rightSpan;
  for (let index = 0; index < left.length; index += 1) {
    if (left[index] !== right[index]) return left[index]! - right[index]!;
  }
  return 0;
}

function headingTitle(line: string): { level: number; title: string } | null {
  const match = line.match(/^(#{1,6})\s+(.+?)\s*#*\s*$/);
  if (!match) return null;
  return { level: match[1]!.length, title: normalizedEvidenceText(match[2]!) };
}

/** Return one-based line references confined to a declared Markdown section. */
export function goldSectionLineRefs(reference: string, goldSection: string): number[] {
  const lines = reference.replace(/\r\n/g, "\n").split("\n");
  const target = normalizedEvidenceText(goldSection);
  const starts = lines.flatMap((line, index) => {
    const heading = headingTitle(line);
    return heading?.title === target ? [{ index, level: heading.level }] : [];
  });
  if (starts.length !== 1) return [];
  const start = starts[0]!;
  let end = lines.length;
  for (let index = start.index + 1; index < lines.length; index += 1) {
    const heading = headingTitle(lines[index]!);
    if (heading && heading.level <= start.level) {
      end = index;
      break;
    }
  }
  return Array.from({ length: end - start.index }, (_unused, index) => start.index + index + 1).filter(
    (ref) => lines[ref - 1]!.trim().length > 0,
  );
}

/**
 * Locate the smallest deterministic citation set that covers required terms.
 * This is only a citation locator for canonical semantic-only fixtures; it is
 * not a semantic classifier and must never promote a model candidate.
 */
export function minimalRequiredTermRefs(reference: string, allowedRefs: number[], groups: string[][]): number[] | null {
  if (groups.length === 0 || groups.length > 30) return null;
  const lines = reference.replace(/\r\n/g, "\n").split("\n");
  const candidates = allowedRefs.flatMap((ref) => {
    const text = normalizedEvidenceText(lines[ref - 1] ?? "");
    if (!text) return [];
    let mask = 0;
    for (let index = 0; index < groups.length; index += 1) {
      if (containsAlternative(text, groups[index]!)) mask |= 1 << index;
    }
    return mask === 0 ? [] : [{ ref, mask }];
  });
  const fullMask = (1 << groups.length) - 1;
  const bestByMask = new Map<number, number[]>([[0, []]]);
  for (const candidate of candidates) {
    const snapshot = [...bestByMask.entries()];
    for (const [mask, refs] of snapshot) {
      const combinedMask = mask | candidate.mask;
      if (combinedMask === mask) continue;
      const combinedRefs = [...refs, candidate.ref];
      const previous = bestByMask.get(combinedMask);
      if (!previous || compareReferenceSets(combinedRefs, previous) < 0) bestByMask.set(combinedMask, combinedRefs);
    }
  }
  return bestByMask.get(fullMask) ?? null;
}

function sortedPolicyCounts(facts: FactFile): Record<string, number> {
  const counts = new Map<string, number>();
  for (const leaf of facts.regions.flatMap((region) => region.leaves)) {
    counts.set(leaf.evidencePolicy.type, (counts.get(leaf.evidencePolicy.type) ?? 0) + 1);
  }
  return Object.fromEntries([...counts.entries()].sort(([left], [right]) => left.localeCompare(right)));
}

function fallbackReference(lines: string[]): number[] {
  const first = lines.findIndex((line) => line.trim().length > 0);
  return first < 0 ? [] : [first + 1];
}

function allNonblankLineRefs(reference: string): number[] {
  return reference
    .replace(/\r\n/g, "\n")
    .split("\n")
    .flatMap((line, index) => (line.trim().length > 0 ? [index + 1] : []));
}

function resolveWithinGoldSection(
  reference: string,
  goldSection: string,
  leaf: FactLeaf,
): ExactResolution | null {
  const globalRefs = goldSectionLineRefs(reference, goldSection);
  if (globalRefs.length === 0) return null;
  const lines = reference.replace(/\r\n/g, "\n").split("\n");
  const localCandidate = globalRefs.map((ref) => lines[ref - 1] ?? "").join("\n");
  const local = resolveLeafEvidence(localCandidate, leaf);
  if (local === null) return null;
  return {
    ...local,
    candidateLineRefs: local.candidateLineRefs?.map((ref) => globalRefs[ref - 1]!).filter(Boolean),
  };
}

type PreparedLeaf = {
  leaf: FactLeaf;
  regionId: string;
  goldSection: string;
  resolution: ReferenceResolution;
  policySupported: boolean;
  semanticReviewRequired: boolean;
  candidateLineRefs: number[];
  reason: string | null;
};

function prepareLeafEvidence(reference: string, facts: FactFile): PreparedLeaf[] {
  const lines = reference.replace(/\r\n/g, "\n").split("\n");
  const fallback = fallbackReference(lines);
  return facts.regions.flatMap((region) =>
    region.leaves.map((leaf): PreparedLeaf => {
      // Repeated row keys, column labels, and checkbox labels are normal in a
      // long packet. Resolve ordinary leaves inside their declared canonical
      // section so an unrelated later table/form cannot manufacture a conflict.
      // Genuine cross-page joins intentionally remain document-scoped.
      const exact: ExactResolution | null =
        leaf.claimType === "cross_page_join"
          ? resolveLeafEvidence(reference, leaf)
          : resolveWithinGoldSection(reference, region.goldSection, leaf);
      if (exact !== null) {
        const refs = exact.candidateLineRefs ?? [];
        const supported = exact.satisfied && refs.length > 0 && refs.length <= 64;
        if (!supported && leaf.evidencePolicy.type === "lexical") {
          const allowedRefs =
            leaf.claimType === "cross_page_join"
              ? allNonblankLineRefs(reference)
              : goldSectionLineRefs(reference, region.goldSection);
          const derivedRefs = minimalRequiredTermRefs(reference, allowedRefs, leaf.evidencePolicy.allOf);
          if (derivedRefs && derivedRefs.length > 0 && derivedRefs.length <= 64) {
            return {
              leaf,
              regionId: region.id,
              goldSection: region.goldSection,
              resolution: "exact_derived",
              policySupported: true,
              semanticReviewRequired: false,
              candidateLineRefs: derivedRefs,
              reason:
                leaf.claimType === "cross_page_join"
                  ? "Minimal lexical citations were derived across the canonical reference; the direct typed gate remains authoritative."
                  : "Minimal lexical citations were derived inside the declared gold section; the direct typed gate remains authoritative.",
            };
          }
        }
        return {
          leaf,
          regionId: region.id,
          goldSection: region.goldSection,
          resolution: supported ? "exact" : "unsupported_exact",
          policySupported: supported,
          semanticReviewRequired: false,
          candidateLineRefs: refs.length > 0 && refs.length <= 64 ? refs : fallback,
          reason: supported ? null : (exact.reason ?? "Exact evidence resolver returned no supporting citation."),
        };
      }

      if (leaf.evidencePolicy.type !== "qualitative") {
        throw new Error(`Resolver returned semantic-only null for non-qualitative leaf ${leaf.id}.`);
      }
      const sectionRefs = goldSectionLineRefs(reference, region.goldSection);
      const refs = minimalRequiredTermRefs(reference, sectionRefs, leaf.evidencePolicy.requiredTerms);
      const supported = refs !== null && refs.length > 0 && refs.length <= 64;
      return {
        leaf,
        regionId: region.id,
        goldSection: region.goldSection,
        resolution: supported ? "semantic_only" : "unsupported_semantic",
        policySupported: supported,
        semanticReviewRequired: true,
        candidateLineRefs: supported ? refs : fallback,
        reason: supported
          ? "Canonical gold citation located; semantic fidelity still requires human review."
          : "The declared gold section cannot ground every required qualitative citation term.",
      };
    }),
  );
}

export function auditReferenceCase(input: {
  testCase: Pick<BenchmarkManifestCase, "id" | "pages" | "gold" | "facts">;
  gold: string;
  factsText: string;
  facts: FactFile;
}): ReferenceCaseAudit {
  const { testCase, gold, factsText, facts } = input;
  const prepared = prepareLeafEvidence(gold, facts);
  const canonicalJudgment = {
    leafResults: prepared.map((item) => ({
      id: item.leaf.id,
      status: "correct" as const,
      candidateLineRefs: item.candidateLineRefs,
    })),
    unsupportedClaims: [],
    rationale: "Canonical gold reference: every declared atomic obligation is submitted as correct for offline self-audit.",
  };
  const validated = validateJudgeResult(facts, canonicalJudgment, gold);
  const atomic = scoreAtomicRegions(facts, canonicalJudgment, gold);
  const validatedById = new Map(validated.leafResults.map((leaf) => [leaf.id, leaf]));
  const atomicStatusById = new Map(
    atomic.regions.flatMap((region) => region.leaves.map((leaf) => [leaf.id, leaf.status] as const)),
  );
  const leaves = prepared.map((item): ReferenceLeafAudit => {
    const validatedLeaf = validatedById.get(item.leaf.id)!;
    const atomicStatus = atomicStatusById.get(item.leaf.id);
    if (atomicStatus !== validatedLeaf.status) {
      throw new Error(`${testCase.id}/${item.leaf.id} changed status between validation and atomic scoring.`);
    }
    const policySupported = item.policySupported && validatedLeaf.status === "correct";
    const resolution: ReferenceResolution = policySupported
      ? item.resolution
      : item.semanticReviewRequired
        ? "unsupported_semantic"
        : "unsupported_exact";
    return {
      id: item.leaf.id,
      canonicalClaimId: item.leaf.canonicalClaimId,
      regionId: item.regionId,
      goldSection: item.goldSection,
      policyType: item.leaf.evidencePolicy.type,
      resolution,
      policySupported,
      semanticReviewRequired: item.semanticReviewRequired,
      candidateLineRefs: item.candidateLineRefs,
      validatedCandidateLineRefs: validatedLeaf.candidateLineRefs,
      validatedStatus: validatedLeaf.status,
      reason:
        policySupported && item.resolution === "exact"
          ? null
          : (validatedLeaf.note ?? item.reason),
    };
  });
  const unsupportedLeafIds = leaves.filter((leaf) => !leaf.policySupported).map((leaf) => leaf.id);
  const passed =
    unsupportedLeafIds.length === 0 &&
    atomic.score === 100 &&
    atomic.rawScore === 100 &&
    atomic.statusHarm.missing === 0 &&
    atomic.statusHarm.incorrect === 0 &&
    atomic.unsupported.count === 0;
  return {
    id: testCase.id,
    pages: testCase.pages,
    gold: testCase.gold,
    facts: testCase.facts,
    goldSha256: sha256(gold),
    factsSha256: sha256(factsText),
    regionCount: facts.regions.length,
    leafCount: leaves.length,
    policyCounts: sortedPolicyCounts(facts),
    exactPolicyLeaves: leaves.filter((leaf) => !leaf.semanticReviewRequired).length,
    semanticOnlyLeaves: leaves.filter((leaf) => leaf.semanticReviewRequired).length,
    supportedLeaves: leaves.filter((leaf) => leaf.policySupported).length,
    unsupportedLeafIds,
    score: atomic.score,
    rawScore: atomic.rawScore,
    statusHarm: atomic.statusHarm,
    unsupportedClaimCount: atomic.unsupported.count,
    passed,
    leaves,
  };
}

function parseCli(argv: string[]) {
  let manifest = defaultManifest;
  let output = defaultOutput;
  const seen = new Set<string>();
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index]!;
    if (!argument.startsWith("--")) throw new Error(`Unexpected positional argument ${argument}.`);
    const option = argument.slice(2);
    if (option !== "manifest" && option !== "output") throw new Error(`Unknown option --${option}.`);
    if (seen.has(option)) throw new Error(`Duplicate option --${option}.`);
    seen.add(option);
    const value = argv[index + 1];
    if (!value || value.startsWith("--")) throw new Error(`--${option} requires a value.`);
    if (option === "manifest") manifest = value;
    else output = value;
    index += 1;
  }
  return { manifest, output };
}

export async function buildReferenceEvidenceAudit(
  manifestReference = defaultManifest,
): Promise<ReferenceEvidenceAudit> {
  const loaded = await loadBenchmarkManifest(manifestReference);
  const cases: ReferenceCaseAudit[] = [];
  for (const testCase of loaded.manifest.cases) {
    const [gold, factsText] = await Promise.all([
      readFile(resolveInsideProject(testCase.gold, `${testCase.id} gold`), "utf8"),
      readFile(resolveInsideProject(testCase.facts, `${testCase.id} facts`), "utf8"),
    ]);
    const facts = parseFactFile(JSON.parse(factsText), { caseId: testCase.id, pages: testCase.pages });
    cases.push(auditReferenceCase({ testCase, gold, factsText, facts }));
  }
  const supportedLeaves = cases.reduce((sum, item) => sum + item.supportedLeaves, 0);
  const leafCount = cases.reduce((sum, item) => sum + item.leafCount, 0);
  const semanticOnlyLeaves = cases.reduce((sum, item) => sum + item.semanticOnlyLeaves, 0);
  const passed = cases.every((item) => item.passed);
  const auditInputFingerprint = hashObject({
    schemaVersion: 1,
    manifestSha256: sha256(loaded.manifestText),
    scoringContractFingerprint,
    cases: cases.map((item) => ({ id: item.id, goldSha256: item.goldSha256, factsSha256: item.factsSha256 })),
  });
  return {
    schemaVersion: 1,
    audit: "canonical-reference-evidence-self-audit",
    suite: loaded.manifest.suite,
    benchmarkVersion: loaded.manifest.version,
    manifest: canonicalProjectReference(loaded.manifestPath),
    manifestSha256: sha256(loaded.manifestText),
    scoringContractVersion,
    scoringContractFingerprint,
    auditInputFingerprint,
    providerCalls: 0,
    canonicalJudgmentsPerCase: 1,
    humanReviewRequired: semanticOnlyLeaves > 0,
    summary: {
      caseCount: cases.length,
      casesAt100: cases.filter((item) => item.score === 100 && item.rawScore === 100).length,
      regionCount: cases.reduce((sum, item) => sum + item.regionCount, 0),
      leafCount,
      supportedLeaves,
      unsupportedLeaves: leafCount - supportedLeaves,
      exactPolicyLeaves: cases.reduce((sum, item) => sum + item.exactPolicyLeaves, 0),
      semanticOnlyLeaves,
      passed,
    },
    cases,
  };
}

export async function auditReferenceEvidence(
  options: { manifest?: string; output?: string } = {},
): Promise<ReferenceEvidenceAudit> {
  const manifest = options.manifest ?? defaultManifest;
  const output = options.output ?? defaultOutput;
  const audit = await buildReferenceEvidenceAudit(manifest);
  const outputPath = path.resolve(output);
  await mkdir(path.dirname(outputPath), { recursive: true });
  await atomicWriteJson(outputPath, audit);
  if (!audit.summary.passed) {
    throw new Error(
      `Canonical reference evidence audit failed: ${audit.summary.unsupportedLeaves} unsupported leaves and ` +
        `${audit.summary.casesAt100}/${audit.summary.caseCount} cases self-scored at 100. Inspect ${output}.`,
    );
  }
  return audit;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const cli = parseCli(process.argv.slice(2));
  const audit = await auditReferenceEvidence(cli);
  console.log(
    `Reference evidence audit passed: ${audit.summary.supportedLeaves}/${audit.summary.leafCount} leaves supported; ` +
      `${audit.summary.semanticOnlyLeaves} semantic-only leaves require human review; provider calls 0.`,
  );
}
