import { mkdir, readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";
import { buildBenchmarkFingerprint } from "./benchmarkFingerprint.js";
import { hashObject, sha256, sha256Bytes } from "./cache.js";
import { loadBenchmarkManifest } from "./manifest.js";
import { preflightBenchmark } from "./preflight.js";
import { prompt } from "./run.js";
import { atomicWriteJson } from "./runRuntime.js";
import {
  judgeWithGemini,
  parseFactFile,
  scoreAtomicRegions,
  scoringContractFingerprint,
  validateJudgeResult,
  type JudgeResult,
  type ManifestCase,
  type ScoredUnsupportedClaim,
} from "./score.js";

export type AuditVariant =
  | "reference"
  | "omission"
  | "substitution"
  | "misbinding"
  | "hallucination"
  | "source_precedence";

const auditVariants: AuditVariant[] = [
  "reference",
  "omission",
  "substitution",
  "misbinding",
  "hallucination",
  "source_precedence",
];
const defaultCaseId = "P23-native-text-layer-recovery";

type StoredAuditIdentity = {
  caseId?: string;
  fixtureInputFingerprint?: string;
  auditInputFingerprint?: string;
};

export function assertReusableStoredAudit(
  previous: StoredAuditIdentity,
  current: {
    caseId: string;
    fixtureInputFingerprint: string;
    legacyAuditInputFingerprint: string;
  },
): void {
  if (previous.caseId !== current.caseId) {
    throw new Error(`Stored scorer audit is for ${previous.caseId ?? "an unknown case"}, not ${current.caseId}.`);
  }
  if (previous.fixtureInputFingerprint !== undefined) {
    if (previous.fixtureInputFingerprint !== current.fixtureInputFingerprint) {
      throw new Error("Stored scorer audit does not match the current case/PDF/gold/facts/candidate inputs.");
    }
    return;
  }
  // Schema-v4 reports predate the scorer-independent fixture fingerprint. A
  // one-time migration is safe only while their original combined fingerprint
  // still matches exactly; after migration scorer-only revisions may replay the
  // same provider judgments while all evaluator inputs remain byte-identical.
  if (previous.auditInputFingerprint !== current.legacyAuditInputFingerprint) {
    throw new Error("Legacy stored scorer audit cannot be migrated because its original input contract is stale.");
  }
}

function replaceExact(source: string, before: string, after: string, label: string): string {
  const first = source.indexOf(before);
  if (first < 0) throw new Error(`Counterfactual fixture is stale; missing ${label}: ${before}`);
  if (source.indexOf(before, first + before.length) >= 0) {
    throw new Error(`Counterfactual fixture is ambiguous; ${label} occurs more than once.`);
  }
  return source.slice(0, first) + after + source.slice(first + before.length);
}

function omitSection(reference: string): string {
  const startMarker = "## 2. Cutover workplan and handoff sequence";
  const endMarker = "## 3. Commercial validation and invoice routing";
  const start = reference.indexOf(startMarker);
  const end = reference.indexOf(endMarker);
  if (start < 0 || end <= start) throw new Error("Omission counterfactual fixture is stale.");
  return reference.slice(0, start) + reference.slice(end);
}

export function buildCounterfactualCandidates(reference: string): Record<AuditVariant, string> {
  const substitution = replaceExact(
    reference,
    "Raster finance stamp: Jonah Mercer; 09 Jul 2026 16:42 MST; ceiling $28,070; control VC-2048; cost validation is not operational release.",
    "Raster finance stamp: Jonah Mercer; 09 Jul 2026 18:42 MST; ceiling $28,070; control VC-9999; cost validation is not operational release.",
    "raster-stamp scalar record",
  );

  const borealRow =
    "| Boreal Storage | 44018-3 | CC-7420 | Jonah Mercer | AP-West / transition |";
  const thermoRow =
    "| ThermoVision | 43991-2 | CC-7314 | Nadia Brooks | AP-Quality / validation |";
  let misbinding = replaceExact(
    reference,
    borealRow,
    "| Boreal Storage | 43991-2 | CC-7420 | Jonah Mercer | AP-West / transition |",
    "Boreal invoice row",
  );
  misbinding = replaceExact(
    misbinding,
    thermoRow,
    "| ThermoVision | 44018-3 | CC-7314 | Nadia Brooks | AP-Quality / validation |",
    "ThermoVision invoice row",
  );

  const noteTableMarker = "| Marker | Meaning | Operational consequence |";
  const hallucinationIndex = reference.indexOf(noteTableMarker);
  if (hallucinationIndex < 0) throw new Error("Hallucination counterfactual fixture is stale.");
  const hallucination =
    reference.slice(0, hallucinationIndex) +
    "| E-99 | T-04 Phoenix transfer | Sponsor waived the telemetry gate. | Avery Kim | 14 Jul 20:00 MST | Verbal approval | OPEN |\n\n" +
    reference.slice(hallucinationIndex);

  const sourcePrecedence = replaceExact(
    reference,
    "**KESTREL CREDENTIAL DECOMMISSION: HOLD** until C-3 is satisfied.",
    "**KESTREL CREDENTIAL DECOMMISSION: RELEASED.** Finance validation on page 3 overrides C-3 and authorizes closure.",
    "credential source-precedence decision",
  );

  return {
    reference,
    omission: omitSection(reference),
    substitution,
    misbinding,
    hallucination,
    source_precedence: sourcePrecedence,
  };
}

function parseCli(argv: string[]) {
  let caseId = defaultCaseId;
  let output = "reports/scorer-audit.json";
  let recompute = false;
  const seen = new Set<string>();
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index]!;
    if (!argument.startsWith("--")) throw new Error(`Unexpected positional argument ${argument}.`);
    const key = argument.slice(2);
    if (!new Set(["case", "output", "recompute"]).has(key)) throw new Error(`Unknown option --${key}.`);
    if (seen.has(key)) throw new Error(`Duplicate option --${key}.`);
    seen.add(key);
    if (key === "recompute") {
      recompute = true;
      continue;
    }
    const value = argv[index + 1];
    if (!value || value.startsWith("--")) throw new Error(`--${key} requires a value.`);
    if (key === "case") caseId = value;
    else output = value;
    index += 1;
  }
  return { caseId, output, recompute };
}

type AuditRun = {
  variant: AuditVariant;
  score: number;
  rawScore: number;
  statusHarm: { correct: number; missing: number; incorrect: number };
  unsupported: { count: number; reportedCount: number; penalty: number; claims: ScoredUnsupportedClaim[] };
  judgeResult: JudgeResult;
  attempts?: number;
  errors?: string[];
  elapsedMs?: number;
  usage?: unknown;
  estimatedCostUsd: number;
  resolved?: unknown;
};

function runByVariant(runs: AuditRun[], variant: AuditVariant): AuditRun {
  const matches = runs.filter((run) => run.variant === variant);
  if (matches.length !== 1) throw new Error(`Expected exactly one ${variant} scorer-audit run; found ${matches.length}.`);
  return matches[0]!;
}

function leafStatus(run: AuditRun, leafId: string) {
  const matches = run.judgeResult.leafResults.filter((leaf) => leaf.id === leafId);
  if (matches.length !== 1) throw new Error(`Expected one ${leafId} result in ${run.variant}; found ${matches.length}.`);
  return matches[0]!.status;
}

function changedLeafIds(reference: AuditRun, counterfactual: AuditRun): string[] {
  const referenceIds = reference.judgeResult.leafResults.map((leaf) => leaf.id);
  const counterfactualIds = counterfactual.judgeResult.leafResults.map((leaf) => leaf.id);
  if (JSON.stringify(referenceIds) !== JSON.stringify(counterfactualIds)) {
    throw new Error(`${counterfactual.variant} returned a different leaf identity/order from the reference.`);
  }
  return referenceIds.filter((id) => leafStatus(reference, id) !== leafStatus(counterfactual, id));
}

function exactChangedLeaves(reference: AuditRun, counterfactual: AuditRun, expected: string[]): boolean {
  return JSON.stringify(changedLeafIds(reference, counterfactual).sort()) === JSON.stringify([...expected].sort());
}

function correctTo(runFrom: AuditRun, runTo: AuditRun, leafIds: string[], status: "missing" | "incorrect"): boolean {
  return leafIds.every((id) => leafStatus(runFrom, id) === "correct" && leafStatus(runTo, id) === status);
}

function counterfactualAcceptance(runs: AuditRun[]) {
  const reference = runByVariant(runs, "reference");
  const omission = runByVariant(runs, "omission");
  const substitution = runByVariant(runs, "substitution");
  const misbinding = runByVariant(runs, "misbinding");
  const hallucination = runByVariant(runs, "hallucination");
  const sourcePrecedence = runByVariant(runs, "source_precedence");
  const leafOnly = [omission, substitution, misbinding, sourcePrecedence];
  const omissionTargets = [
    "p02.workplan.t-01.activity",
    "p02.sidebar.access",
    "p02.reading-order.sections",
    "p02.handoff.rollback-invoked.required-content",
    "p02.rollback.report",
  ];
  const substitutionTargets = ["p03.stamp.signer-time", "p03.stamp.control"];
  const misbindingTargets = ["p03.invoice.boreal-storage.po", "p03.invoice.thermovision.po"];
  const sourcePrecedenceTargets = ["p05.decision.hold"];
  const sourcePrecedenceAllowed = new Set([
    "p01.authority.final",
    "p01.authority.finance",
    "p01.authority.scope",
    "p03.scope.no-release",
    "p03.stamp.scope",
    "p04.scope.sources",
    "p05.decision.hold",
    "p05.interpretation.sources",
    "x01.selective-release.credentials",
    "x01.selective-release.finance",
  ]);
  const hallucinations = hallucination.unsupported.claims;
  return {
    referenceIsFullyRecovered:
      reference.score >= 99 &&
      reference.statusHarm.missing === 0 &&
      reference.statusHarm.incorrect === 0 &&
      reference.unsupported.count === 0,
    omissionCreatesMissingEvidence:
      correctTo(reference, omission, omissionTargets, "missing") &&
      changedLeafIds(reference, omission).every((id) => id.startsWith("p02.") || id.startsWith("x01.")) &&
      omission.score < reference.score,
    substitutionCreatesIncorrectEvidence:
      correctTo(reference, substitution, substitutionTargets, "incorrect") &&
      exactChangedLeaves(reference, substitution, substitutionTargets) &&
      substitution.score < reference.score,
    misbindingCreatesIncorrectEvidence:
      correctTo(reference, misbinding, misbindingTargets, "incorrect") &&
      exactChangedLeaves(reference, misbinding, misbindingTargets) &&
      misbinding.score < reference.score,
    hallucinationIsProvenOnlyThroughClosedWorld:
      exactChangedLeaves(reference, hallucination, []) &&
      hallucinations.length === 1 &&
      hallucinations[0]!.regionId === "p04.exceptions" &&
      hallucinations[0]!.key === "E-99" &&
      /\bE-99\b/.test(hallucinations[0]!.claim) &&
      hallucination.unsupported.count === 1 &&
      hallucination.score < reference.score,
    wrongSourcePrecedenceCreatesIncorrectEvidence:
      correctTo(reference, sourcePrecedence, sourcePrecedenceTargets, "incorrect") &&
      leafStatus(sourcePrecedence, "p05.decision.go") === "correct" &&
      changedLeafIds(reference, sourcePrecedence).every((id) => sourcePrecedenceAllowed.has(id)) &&
      sourcePrecedence.score < reference.score,
    noLeafErrorIsDoubleChargedAsUnsupported: leafOnly.every((run) => run.unsupported.count === 0),
  };
}

export async function auditScorer(
  options: { caseId?: string; output?: string; recompute?: boolean } = {},
) {
  const caseId = options.caseId ?? defaultCaseId;
  const output = options.output ?? "reports/scorer-audit.json";
  await preflightBenchmark("benchmark/manifest.json");
  const { manifest } = await loadBenchmarkManifest("benchmark/manifest.json");
  const testCase = manifest.cases.find((item) => item.id === caseId) as ManifestCase | undefined;
  if (!testCase) throw new Error(`Unknown audit case ${caseId}.`);
  if (!testCase.facts) throw new Error(`Audit case ${caseId} has no facts file.`);

  const [gold, factsText, pdf] = await Promise.all([
    readFile(testCase.gold, "utf-8"),
    readFile(testCase.facts, "utf-8"),
    readFile(testCase.pdf),
  ]);
  const facts = parseFactFile(JSON.parse(factsText), { caseId: testCase.id, pages: testCase.pages });
  const candidates = buildCounterfactualCandidates(gold);
  const benchmark = await buildBenchmarkFingerprint({
    manifestPath: "benchmark/manifest.json",
    promptHash: sha256(prompt),
    scoringContractFingerprint,
  });
  const auditInputFingerprint = hashObject({
    schemaVersion: 4,
    caseId,
    pdfHash: sha256Bytes(pdf),
    goldHash: sha256(gold),
    factsHash: sha256(factsText),
    candidateHashes: Object.fromEntries(auditVariants.map((variant) => [variant, sha256(candidates[variant])])),
    scoringContractFingerprint,
  });
  const fixtureInputFingerprint = hashObject({
    schemaVersion: 1,
    caseId,
    pdfHash: sha256Bytes(pdf),
    goldHash: sha256(gold),
    factsHash: sha256(factsText),
    candidateHashes: Object.fromEntries(auditVariants.map((variant) => [variant, sha256(candidates[variant])])),
  });
  let runs: AuditRun[] = [];
  let judgmentProvenance:
    | {
        source: "stored-provider-judgments";
        scoringContractFingerprintAtJudgment: string;
        auditInputFingerprintAtJudgment: string;
      }
    | undefined;

  if (options.recompute) {
    const previous = JSON.parse(await readFile(output, "utf-8")) as {
      caseId?: string;
      fixtureInputFingerprint?: string;
      auditInputFingerprint?: string;
      scoringContractFingerprint?: string;
      judgmentProvenance?: {
        source?: string;
        scoringContractFingerprintAtJudgment?: string;
        auditInputFingerprintAtJudgment?: string;
      };
      runs?: AuditRun[];
    };
    assertReusableStoredAudit(previous, {
      caseId,
      fixtureInputFingerprint,
      legacyAuditInputFingerprint: auditInputFingerprint,
    });
    if (!Array.isArray(previous.runs)) throw new Error(`Stored scorer audit at ${output} has no reusable runs.`);
    const scoringContractFingerprintAtJudgment =
      previous.judgmentProvenance?.scoringContractFingerprintAtJudgment ?? previous.scoringContractFingerprint;
    const auditInputFingerprintAtJudgment =
      previous.judgmentProvenance?.auditInputFingerprintAtJudgment ?? previous.auditInputFingerprint;
    if (!scoringContractFingerprintAtJudgment || !auditInputFingerprintAtJudgment) {
      throw new Error(`Stored scorer audit at ${output} lacks evaluator-judgment provenance.`);
    }
    judgmentProvenance = {
      source: "stored-provider-judgments",
      scoringContractFingerprintAtJudgment,
      auditInputFingerprintAtJudgment,
    };
    runs = previous.runs.map((run) => {
      const judgeResult = validateJudgeResult(facts, run.judgeResult, candidates[run.variant]);
      const atomic = scoreAtomicRegions(facts, judgeResult, candidates[run.variant]);
      return {
        ...run,
        judgeResult,
        score: atomic.score,
        rawScore: atomic.rawScore,
        statusHarm: atomic.statusHarm,
        unsupported: atomic.unsupported,
      };
    });
  } else {
    for (const variant of auditVariants) {
      const judged = await judgeWithGemini(testCase, facts, candidates[variant]);
      if (!judged.ok) throw new Error(`${variant} counterfactual failed: ${judged.errors.join("; ")}`);
      const atomic = scoreAtomicRegions(facts, judged.result, candidates[variant]);
      runs.push({
        variant,
        score: atomic.score,
        rawScore: atomic.rawScore,
        statusHarm: atomic.statusHarm,
        unsupported: atomic.unsupported,
        judgeResult: judged.result,
        attempts: judged.attempts,
        errors: judged.errors,
        elapsedMs: judged.elapsedMs,
        usage: judged.usage,
        estimatedCostUsd: judged.estimatedCostUsd,
        resolved: judged.resolved,
      });
      console.log(`${variant}: ${atomic.score.toFixed(1)} ($${judged.estimatedCostUsd.toFixed(6)})`);
    }
  }

  for (const variant of auditVariants) runByVariant(runs, variant);
  const referenceScore = runByVariant(runs, "reference").score;
  const scores = Object.fromEntries(
    auditVariants.map((variant) => {
      const run = runByVariant(runs, variant);
      return [
        variant,
        {
          score: run.score,
          rawScore: run.rawScore,
          dropFromReference: referenceScore - run.score,
          statusHarm: run.statusHarm,
          unsupported: run.unsupported,
        },
      ];
    }),
  );
  const acceptance = counterfactualAcceptance(runs);
  const passed = Object.values(acceptance).every(Boolean);
  const audit = {
    schemaVersion: 5,
    caseId,
    samplesPerVariant: 1,
    variabilityEstimate: null,
    reliabilityClaim: null,
    humanReviewRequired: true,
    benchmarkFingerprint: benchmark.benchmarkFingerprint,
    scoringContractFingerprint,
    fixtureInputFingerprint,
    auditInputFingerprint,
    judgmentProvenance,
    recomputedFromStoredJudgments: options.recompute === true,
    fixtures: {
      reference: "canonical gold Markdown",
      omission: "complete workplan/handoff section removed",
      substitution: "raster-stamp time and control identifier replaced",
      misbinding: "Boreal and ThermoVision PO values exchanged across invoice rows",
      hallucination: "invented E-99 row added to the closed-world exception register",
      source_precedence: "physical GO is preserved while finance falsely overrides C-3 and releases held credentials",
    },
    scores,
    totalEstimatedCostUsd: runs.reduce((sum, run) => sum + (run.estimatedCostUsd ?? 0), 0),
    acceptance,
    passed,
    runs,
  };
  await mkdir(path.dirname(output), { recursive: true });
  await atomicWriteJson(output, audit);
  if (!passed) throw new Error(`Scorer counterfactual audit failed; inspect ${output}.`);
  return audit;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const cli = parseCli(process.argv.slice(2));
  const keepAlive = setInterval(() => undefined, 1_000);
  try {
    const audit = await auditScorer(cli);
    console.log(
      `Scorer counterfactual audit passed mechanically; human judgment review remains required. Cost $${audit.totalEstimatedCostUsd.toFixed(6)}.`,
    );
  } finally {
    clearInterval(keepAlive);
  }
}
