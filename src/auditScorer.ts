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
  type ManifestCase,
} from "./score.js";

type AuditVariant = "reference" | "contradicted" | "omitted";

const defaultCaseId = "P23-native-text-layer-recovery";
const defaultRepeats = 3;

function positiveInteger(value: string | undefined, fallback: number) {
  if (value === undefined) return fallback;
  const parsed = Number(value);
  if (!Number.isSafeInteger(parsed) || parsed < 1 || parsed > 10) {
    throw new Error("--repeats must be an integer from 1 through 10.");
  }
  return parsed;
}

function parseCli(argv: string[]) {
  let caseId = defaultCaseId;
  let repeats = defaultRepeats;
  let output = "reports/scorer-audit.json";
  let recompute = false;
  const seen = new Set<string>();
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index]!;
    if (!argument.startsWith("--")) throw new Error(`Unexpected positional argument ${argument}.`);
    const key = argument.slice(2);
    if (!new Set(["case", "repeats", "output", "recompute"]).has(key)) throw new Error(`Unknown option --${key}.`);
    if (seen.has(key)) throw new Error(`Duplicate option --${key}.`);
    seen.add(key);
    if (key === "recompute") {
      recompute = true;
      continue;
    }
    const value = argv[index + 1];
    if (!value || value.startsWith("--")) throw new Error(`--${key} requires a value.`);
    if (key === "case") caseId = value;
    else if (key === "repeats") repeats = positiveInteger(value, defaultRepeats);
    else output = value;
    index += 1;
  }
  return { caseId, repeats, output, recompute };
}

function contradictedCandidate(reference: string) {
  const replacements: Array<[string, string]> = [
    ["HOLD — dock crew exception", "RELEASED — staffing exception closed"],
    ["D-17 is the only open blocking decision.", "D-17 is closed; there are no open blocking decisions."],
    ["| Reno → SFO | 41 | Dock crew short by 3 | BLOCKED | Ravi closes D-17 |", "| Reno → SFO | 41 | Dock crew short by 3 | RELEASED | No further action |"],
    ["| Reno | Ravi Mehta | Crew roster RC-118 | No outbound consolidation |", "| Reno | Ravi Mehta | Crew roster RC-118 | Outbound consolidation permitted |"],
    ["Reno may not consolidate until the D-17 exception owner records closure.", "Reno may consolidate immediately because D-17 is closed."],
    [
      "Reno outbound consolidation remains **ON HOLD** until Ravi Mehta closes the D-17 dock staffing exception.",
      "Reno outbound consolidation is **RELEASED** because Ravi Mehta closed the D-17 dock staffing exception.",
    ],
    ["| Exception owner | Ravi Mehta | Open — not signed | Next review 12 Jul 16:00 PT |", "| Exception owner | Ravi Mehta | Closed — signed | Closed 10 Jul 15:00 PT |"],
    [
      "Ravi Mehta's row remains open and unsigned, so the controlling statement remains in force.",
      "Ravi Mehta's row is closed and signed, so the controlling hold is lifted.",
    ],
  ];
  let candidate = reference;
  for (const [before, after] of replacements) {
    if (!candidate.includes(before)) throw new Error(`Counterfactual fixture is stale; missing exact source text: ${before}`);
    candidate = candidate.replace(before, after);
  }
  return candidate;
}

function omittedCandidate(reference: string) {
  const startMarker = "## Lane risk register";
  const endMarker = "## Cost reserve authorization";
  const start = reference.indexOf(startMarker);
  const end = reference.indexOf(endMarker);
  if (start < 0 || end <= start) throw new Error("Omission counterfactual fixture is stale.");
  return `${reference.slice(0, start)}${reference.slice(end)}`;
}

function spread(values: number[]) {
  return values.length === 0 ? null : Math.max(...values) - Math.min(...values);
}

function mean(values: number[]) {
  return values.length === 0 ? null : values.reduce((sum, value) => sum + value, 0) / values.length;
}

export async function auditScorer(options: { caseId?: string; repeats?: number; output?: string; recompute?: boolean } = {}) {
  const caseId = options.caseId ?? defaultCaseId;
  const repeats = options.repeats ?? defaultRepeats;
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
  const benchmark = await buildBenchmarkFingerprint({
    manifestPath: "benchmark/manifest.json",
    promptHash: sha256(prompt),
    scoringContractFingerprint,
  });
  const auditInputFingerprint = hashObject({
    schemaVersion: 3,
    caseId,
    pdfHash: sha256Bytes(pdf),
    goldHash: sha256(gold),
    factsHash: sha256(factsText),
    scoringContractFingerprint,
  });
  const candidates: Record<AuditVariant, string> = {
    reference: gold,
    contradicted: contradictedCandidate(gold),
    omitted: omittedCandidate(gold),
  };
  let runs: Array<Record<string, unknown>> = [];

  if (options.recompute) {
    const previous = JSON.parse(await readFile(output, "utf-8")) as {
      caseId?: string;
      repeats?: number;
      auditInputFingerprint?: string;
      runs?: Array<Record<string, unknown>>;
    };
    if (
      previous.caseId !== caseId ||
      previous.repeats !== repeats ||
      previous.auditInputFingerprint !== auditInputFingerprint ||
      !Array.isArray(previous.runs)
    ) {
      throw new Error(`Stored scorer audit at ${output} does not match case ${caseId} with ${repeats} repeats.`);
    }
    runs = previous.runs.map((run) => {
      const variant = run.variant as AuditVariant;
      const atomic = scoreAtomicRegions(facts, run.judgeResult, candidates[variant]);
      return {
        ...run,
        score: atomic.score,
        rawScore: atomic.rawScore,
        statusHarm: atomic.statusHarm,
        unsupported: atomic.unsupported,
      };
    });
  } else {
    // Alternate variants so any transient provider drift affects both cohorts similarly.
    for (let repeat = 1; repeat <= repeats; repeat += 1) {
      for (const variant of ["reference", "contradicted", "omitted"] as const) {
        const judged = await judgeWithGemini(testCase, facts, candidates[variant]);
        if (!judged.ok) {
          throw new Error(`${variant} audit repeat ${repeat} failed: ${judged.errors.join("; ")}`);
        }
        const atomic = scoreAtomicRegions(facts, judged.result, candidates[variant]);
        runs.push({
          variant,
          repeat,
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
        console.log(`${variant} repeat ${repeat}: ${atomic.score.toFixed(2)} ($${judged.estimatedCostUsd.toFixed(6)})`);
      }
    }
  }

  const referenceScores = runs.filter((run) => run.variant === "reference").map((run) => run.score as number);
  const contradictedScores = runs.filter((run) => run.variant === "contradicted").map((run) => run.score as number);
  const omittedScores = runs.filter((run) => run.variant === "omitted").map((run) => run.score as number);
  const referenceMean = mean(referenceScores)!;
  const contradictedMean = mean(contradictedScores)!;
  const omittedMean = mean(omittedScores)!;
  const acceptance = {
    referenceMinimum: Math.min(...referenceScores) >= 98,
    referenceSpreadAtMostOnePoint: spread(referenceScores)! <= 1,
    contradictedSpreadAtMostOnePoint: spread(contradictedScores)! <= 1,
    omittedSpreadAtMostOnePoint: spread(omittedScores)! <= 1,
    counterfactualDropAtLeastFivePoints: referenceMean - contradictedMean >= 5,
    omissionDropAtLeastTenPoints: referenceMean - omittedMean >= 10,
    noScoredUnsupportedClaimsForLeafOnlyCounterfactual: runs
      .filter((run) => run.variant === "contradicted")
      .every((run) => (run.unsupported as { count?: number }).count === 0),
  };
  const passed = Object.values(acceptance).every(Boolean);
  const audit = {
    schemaVersion: 3,
    caseId,
    repeats,
    benchmarkFingerprint: benchmark.benchmarkFingerprint,
    scoringContractFingerprint,
    auditInputFingerprint,
    recomputedFromStoredJudgments: options.recompute === true,
    fixture: {
      reference: "canonical gold Markdown",
      contradicted: "eight exact substitutions that falsely release the Reno/D-17 hold",
      omitted: "the complete page-2 lane risk register and local release-controls section removed",
    },
    summary: {
      referenceScores,
      contradictedScores,
      omittedScores,
      referenceMean,
      contradictedMean,
      omittedMean,
      referenceSpread: spread(referenceScores),
      contradictedSpread: spread(contradictedScores),
      omittedSpread: spread(omittedScores),
      scoreDrop: referenceMean - contradictedMean,
      omissionScoreDrop: referenceMean - omittedMean,
      totalEstimatedCostUsd: runs.reduce((sum, run) => sum + (run.estimatedCostUsd as number), 0),
    },
    acceptance,
    passed,
    runs,
  };
  await mkdir(path.dirname(output), { recursive: true });
  await atomicWriteJson(output, audit);
  if (!passed) throw new Error(`Scorer audit failed acceptance gates; inspect ${output}.`);
  return audit;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const cli = parseCli(process.argv.slice(2));
  const audit = await auditScorer(cli);
  console.log(`Scorer audit passed; score drop ${audit.summary.scoreDrop.toFixed(2)}, cost $${audit.summary.totalEstimatedCostUsd.toFixed(6)}.`);
}
