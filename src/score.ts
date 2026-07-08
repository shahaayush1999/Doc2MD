import { access, readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { performance } from "node:perf_hooks";
import { fileURLToPath } from "node:url";
import { generateObject } from "ai";
import { googleVertex } from "@ai-sdk/google-vertex";
import { z } from "zod";
import { fileSha256, hashObject, sha256 } from "./cache.js";
import { buildRunContext, models, runCacheKey } from "./run.js";

type Check = {
  id: string;
  category: string;
  weight: number;
  description: string;
  all?: string[];
  none?: string[];
  ordered?: string[];
  near?: { terms: string[]; window: number };
};

type CheckFile = {
  id: string;
  title: string;
  family: string;
  tags: string[];
  checks: Check[];
};

type ManifestCase = {
  id: string;
  title: string;
  family: string;
  tags: string[];
  pages?: number;
  pdf: string;
  gold: string;
  checks: string;
  facts?: string;
};

type Manifest = {
  name?: string;
  suite?: string;
  scoreName?: string;
  inputProtocol?: string;
  cases: ManifestCase[];
};

type JudgeFinding = {
  severity: "critical" | "major" | "minor";
  type: "missing" | "incorrect" | "extra" | "structure" | "format";
  explanation: string;
  expected?: string;
  actual?: string;
};

type UnsupportedClaim = {
  severity: "critical" | "major" | "minor";
  claim: string;
  reason: string;
};

type Fact = {
  id: string;
  category: string;
  weight: number;
  expectation: string;
  guidance?: string;
  severity?: "critical" | "major" | "minor";
  modality?: string;
};

type FactFile = {
  id: string;
  title: string;
  family: string;
  tags: string[];
  facts: Fact[];
};

type FactResult = {
  id: string;
  status: "correct" | "partial" | "incorrect" | "missing";
  rationale: string;
};

type JudgeResult = {
  accuracy: number;
  completeness: number;
  structure: number;
  markdownQuality: number;
  factResults: FactResult[];
  unsupportedClaims: UnsupportedClaim[];
  findings: JudgeFinding[];
  rationale: string;
};

const evaluator = {
  id: "vertex-gemini-3.1-flash-lite",
  modelName: "gemini-3.1-flash-lite",
  provider: "google-vertex",
  reasoning: "minimal",
  inputPerMillion: 0.25,
  outputPerMillion: 1.5,
} as const;

const weights = {
  accuracy: 0.96,
  completeness: 0.03,
  structure: 0.01,
  markdownQuality: 0,
};

const scoringVersion = "fact-judge-v17-critical-visual-omission-caps";
const judgeMaxOutputTokens = 6000;

const factStatusCredit = {
  correct: 1,
  partial: 0.5,
  incorrect: -2,
  missing: 0,
} satisfies Record<FactResult["status"], number>;

const unsupportedClaimPenalty = {
  minor: 5,
  major: 15,
  critical: 30,
} satisfies Record<UnsupportedClaim["severity"], number>;

const scoreField = z.number().min(0).max(100);

const judgeSchema = z.object({
  accuracy: scoreField.describe(
    "Downstream recoverability of represented facts, values, labels, states, and bindings. Penalize contradictions and wrong values heavily, but do not lower accuracy for formatting-only issues.",
  ),
  completeness: scoreField.describe("Coverage of answer-key information, regardless of whether it is represented as prose, lists, Markdown tables, or HTML tables."),
  structure: scoreField.describe("Recoverability of grouping, locality, row/column relationships, source-state relationships, and visual-to-text bindings."),
  markdownQuality: scoreField.describe("Machine-usable Markdown/plain text. Give high marks unless malformed output blocks downstream parsing."),
  factResults: z
    .array(
      z.object({
        id: z.string(),
        status: z.enum(["correct", "partial", "incorrect", "missing"]),
        rationale: z.string(),
      }),
    )
    .describe("Per-fact judgments for every listed fact obligation."),
  unsupportedClaims: z
    .array(
      z.object({
        severity: z.enum(["critical", "major", "minor"]),
        claim: z.string().describe("A concise description or quote of unsupported content in the candidate."),
        reason: z.string().describe("Why this claim is unsupported, hallucinated, or contradicted by the gold answer key."),
      }),
    )
    .max(12)
    .describe("Unsupported, hallucinated, or contradicted candidate claims. Leave empty only if there are no substantive unsupported claims."),
  findings: z
    .array(
      z.object({
        severity: z.enum(["critical", "major", "minor"]),
        type: z.enum(["missing", "incorrect", "extra", "structure", "format"]),
        explanation: z.string(),
        expected: z.string().optional(),
        actual: z.string().optional(),
      }),
    )
    .max(12),
  rationale: z.string().describe("Brief explanation of the score in one or two sentences."),
});

function clampScore(value: number): number {
  if (!Number.isFinite(value)) return 0;
  if (value >= 0 && value <= 1) return value * 100;
  return Math.max(0, Math.min(100, value));
}

function round(value: number, digits = 1): number {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function cost(usage: any): number {
  const input = usage?.inputTokens ?? 0;
  const output = usage?.outputTokens ?? 0;
  return (input / 1_000_000) * evaluator.inputPerMillion + (output / 1_000_000) * evaluator.outputPerMillion;
}

async function exists(filePath: string) {
  try {
    await access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function readJsonIfExists(filePath: string) {
  if (!(await exists(filePath))) return null;
  return JSON.parse(await readFile(filePath, "utf-8")) as any;
}

function parseArgs() {
  const args = new Map<string, string>();
  const positionals: string[] = [];
  for (let i = 2; i < process.argv.length; i += 1) {
    const arg = process.argv[i];
    if (arg.startsWith("--")) {
      const key = arg.slice(2);
      const next = process.argv[i + 1];
      args.set(key, next && !next.startsWith("--") ? process.argv[++i] : "true");
    } else {
      positionals.push(arg);
    }
  }
  return { args, positionals };
}

function rejectUnknownArgs(args: Map<string, string>, allowed: string[]) {
  const allowedSet = new Set(allowed);
  const unknown = [...args.keys()].filter((key) => !allowedSet.has(key));
  if (unknown.length > 0) throw new Error(`Unknown argument(s): ${unknown.map((key) => `--${key}`).join(", ")}`);
}

function normalize(text: string): string {
  return text
    .replace(/\r\n/g, "\n")
    .replace(/<[^>]+>/g, " ")
    .replace(/[*_`~]+/g, "")
    .replace(/(\d+(?:\.\d+)?)\s+h\b/giu, "$1h")
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .replace(/[ \t]+/g, " ")
    .replace(/[“”]/g, '"')
    .replace(/[‘’]/g, "'")
    .trim();
}

function reconstructionCoverage(testCase: ManifestCase, gold: string, prediction: string) {
  const normalizedGold = normalize(gold);
  const normalizedPrediction = normalize(prediction);
  const goldLength = normalizedGold.length;
  const predictionLength = normalizedPrediction.length;
  if ((testCase.pages ?? 0) < 6 || goldLength < 3_000) return null;

  const ratio = goldLength === 0 ? 0 : predictionLength / goldLength;
  if (ratio >= 0.95) {
    return {
      goldLength,
      predictionLength,
      ratio: round(ratio, 3),
      scoreCap: null,
      completenessCap: 100,
      reason: "Long-document reconstruction coverage is sufficient.",
    };
  }

  const scoreCap = ratio < 0.25 ? 25 : ratio < 0.4 ? 40 : ratio < 0.55 ? 55 : ratio < 0.7 ? 70 : ratio < 0.85 ? 80 : 88;
  return {
    goldLength,
    predictionLength,
    ratio: round(ratio, 3),
    scoreCap,
    completenessCap: round(Math.min(100, (ratio / 0.85) * 100)),
    reason: "Candidate is materially shorter than the long-document gold reference; Doc2MD requires reconstruction, not a selective summary.",
  };
}

function regex(pattern: string): RegExp {
  return new RegExp(pattern, "imu");
}

function regexGlobal(pattern: string): RegExp {
  return new RegExp(pattern, "gimu");
}

function allMatch(patterns: string[] | undefined, text: string): boolean {
  return patterns?.every((pattern) => regex(pattern).test(text)) ?? true;
}

function noneMatch(patterns: string[] | undefined, text: string): boolean {
  return !(patterns?.some((pattern) => regex(pattern).test(text)) ?? false);
}

function orderedMatch(patterns: string[] | undefined, text: string): boolean {
  if (!patterns) return true;
  let offset = 0;
  for (const pattern of patterns) {
    const match = regex(pattern).exec(text.slice(offset));
    if (!match || match.index < 0) return false;
    offset += match.index + match[0].length;
  }
  return true;
}

function nearMatch(near: Check["near"], text: string): boolean {
  if (!near) return true;
  const rangesByTerm = near.terms.map((term) =>
    [...text.matchAll(regexGlobal(term))].map((match) => ({
      start: match.index,
      end: match.index + match[0].length,
    })),
  );
  if (rangesByTerm.some((ranges) => ranges.length === 0)) return false;

  const candidateStarts = rangesByTerm.flatMap((ranges) => ranges.flatMap((range) => [range.start, range.end - near.window]));
  return candidateStarts.some((start) => {
    const end = start + near.window;
    return rangesByTerm.every((ranges) => ranges.some((range) => range.start >= start && range.end <= end));
  });
}

function deterministicAudit(checkFile: CheckFile, prediction: string, failed: boolean) {
  let earned = 0;
  let possible = 0;
  const byCategory: Record<string, { earned: number; possible: number }> = {};

  const details = checkFile.checks.map((check) => {
    possible += check.weight;
    byCategory[check.category] ??= { earned: 0, possible: 0 };
    byCategory[check.category].possible += check.weight;
    const matched =
      !failed &&
      allMatch(check.all, prediction) &&
      noneMatch(check.none, prediction) &&
      orderedMatch(check.ordered, prediction) &&
      nearMatch(check.near, prediction);
    if (matched) {
      earned += check.weight;
      byCategory[check.category].earned += check.weight;
    }
    return { ...check, matched };
  });

  const categoryScores = Object.fromEntries(
    Object.entries(byCategory).map(([category, value]) => [
      category,
      value.possible === 0 ? null : round((value.earned / value.possible) * 100),
    ]),
  );

  return {
    score: possible === 0 ? 0 : round((earned / possible) * 100),
    earned,
    possible,
    categoryScores,
    details,
  };
}

function scoreFacts(facts: Fact[], factResults: FactResult[]) {
  const byId = new Map(factResults.map((result) => [result.id, result]));
  let earned = 0;
  let possible = 0;
  const statusWeights: Record<FactResult["status"], number> = {
    correct: 0,
    partial: 0,
    incorrect: 0,
    missing: 0,
  };
  const severityStatusWeights: Record<NonNullable<Fact["severity"]>, Record<FactResult["status"], number>> = {
    critical: { correct: 0, partial: 0, incorrect: 0, missing: 0 },
    major: { correct: 0, partial: 0, incorrect: 0, missing: 0 },
    minor: { correct: 0, partial: 0, incorrect: 0, missing: 0 },
  };
  const details = facts.map((fact) => {
    possible += fact.weight;
    const result = byId.get(fact.id) ?? { id: fact.id, status: "missing" as const, rationale: "The evaluator did not return a judgment for this fact." };
    statusWeights[result.status] += fact.weight;
    severityStatusWeights[fact.severity ?? "major"][result.status] += fact.weight;
    const credit = factStatusCredit[result.status] * fact.weight;
    earned += credit;
    return { ...fact, status: result.status, rationale: result.rationale, earned: round(credit, 2) };
  });
  const rawScore = possible === 0 ? null : round((earned / possible) * 100);
  return {
    score: rawScore === null ? null : clampScore(rawScore),
    rawScore,
    earned: round(earned, 2),
    possible: round(possible, 2),
    statusWeights: Object.fromEntries(Object.entries(statusWeights).map(([status, value]) => [status, round(value, 2)])),
    severityStatusWeights: Object.fromEntries(
      Object.entries(severityStatusWeights).map(([severity, weights]) => [
        severity,
        Object.fromEntries(Object.entries(weights).map(([status, value]) => [status, round(value, 2)])),
      ]),
    ),
    details,
  };
}

function unsupportedAudit(judge: JudgeResult) {
  const claims = judge.unsupportedClaims ?? [];
  const fallbackClaims =
    claims.length > 0
      ? []
      : (judge.findings ?? [])
          .filter((finding) => finding.type === "extra")
          .map((finding) => ({
            severity: finding.severity,
            claim: finding.actual ?? finding.explanation,
            reason: finding.explanation,
          }));
  const auditedClaims = [...claims, ...fallbackClaims];
  const penalty = auditedClaims.reduce((sum, claim) => sum + unsupportedClaimPenalty[claim.severity], 0);
  const counts = auditedClaims.reduce(
    (acc, claim) => {
      acc[claim.severity] += 1;
      return acc;
    },
    { critical: 0, major: 0, minor: 0 } as Record<UnsupportedClaim["severity"], number>,
  );
  return {
    claims: auditedClaims,
    counts,
    penalty,
  };
}

function scoreCaps(params: {
  factScore: ReturnType<typeof scoreFacts>;
  unsupported: ReturnType<typeof unsupportedAudit>;
  coverage: ReturnType<typeof reconstructionCoverage>;
}) {
  const caps: Array<{ cap: number; reason: string }> = [];
  const possible = params.factScore.possible || 0;
  const statusWeights = params.factScore.statusWeights as Record<FactResult["status"], number>;
  const partialWeight = statusWeights.partial ?? 0;
  const missingWeight = statusWeights.missing ?? 0;
  const incorrectWeight = statusWeights.incorrect ?? 0;
  const partialPct = possible === 0 ? 0 : (partialWeight / possible) * 100;
  const missingPct = possible === 0 ? 0 : (missingWeight / possible) * 100;
  const incorrectPct = possible === 0 ? 0 : (incorrectWeight / possible) * 100;
  const problemPct = partialPct + missingPct + incorrectPct;
  const weightedProblemPct = partialPct * 0.5 + missingPct + incorrectPct * 1.5;
  const severityStatusWeights = params.factScore.severityStatusWeights as Record<NonNullable<Fact["severity"]>, Record<FactResult["status"], number>>;
  const criticalWeights = severityStatusWeights.critical;
  const criticalPossible = Object.values(criticalWeights).reduce((sum, value) => sum + value, 0);
  const criticalMissingWeight = criticalWeights.missing ?? 0;
  const criticalIncorrectWeight = criticalWeights.incorrect ?? 0;
  const criticalBadWeight = criticalMissingWeight + criticalIncorrectWeight;
  const criticalMissingPct = criticalPossible === 0 ? 0 : ((criticalWeights.missing ?? 0) / criticalPossible) * 100;
  const criticalIncorrectPct = criticalPossible === 0 ? 0 : ((criticalWeights.incorrect ?? 0) / criticalPossible) * 100;
  const criticalBadPct = criticalMissingPct + criticalIncorrectPct;
  const criticalVisualDetails = params.factScore.details.filter(
    (detail) =>
      detail.severity === "critical" &&
      (detail.category === "chart" ||
        detail.category === "visual_relation" ||
        detail.modality === "visual" ||
        detail.modality === "chart"),
  );
  const criticalVisualMissingWeight = criticalVisualDetails
    .filter((detail) => detail.status === "missing")
    .reduce((sum, detail) => sum + detail.weight, 0);
  const criticalVisualIncorrectWeight = criticalVisualDetails
    .filter((detail) => detail.status === "incorrect")
    .reduce((sum, detail) => sum + detail.weight, 0);
  const criticalVisualPartialWeight = criticalVisualDetails
    .filter((detail) => detail.status === "partial")
    .reduce((sum, detail) => sum + detail.weight, 0);
  const criticalVisualProblemWeight = criticalVisualMissingWeight + criticalVisualIncorrectWeight + criticalVisualPartialWeight * 0.5;

  if (partialPct >= 10) caps.push({ cap: 85, reason: `Material partial reconstruction: ${round(partialPct)}% of weighted facts are only partially correct.` });
  if (partialPct >= 20) caps.push({ cap: 75, reason: `Broad partial reconstruction: ${round(partialPct)}% of weighted facts are only partially correct.` });
  if (partialPct >= 30) caps.push({ cap: 65, reason: `Large partial reconstruction failure: ${round(partialPct)}% of weighted facts are only partially correct.` });
  if (partialPct >= 40) caps.push({ cap: 55, reason: `Severe partial reconstruction failure: ${round(partialPct)}% of weighted facts are only partially correct.` });

  if (missingWeight > 0) caps.push({ cap: 90, reason: `Visible fact omissions: ${round(missingPct)}% of weighted facts are missing.` });
  if (missingPct >= 5) caps.push({ cap: 85, reason: `Meaningful omission: ${round(missingPct)}% of weighted facts are missing.` });
  if (missingPct >= 10) caps.push({ cap: 75, reason: `Material omission: ${round(missingPct)}% of weighted facts are missing.` });
  if (missingPct >= 20) caps.push({ cap: 60, reason: `Large omission: ${round(missingPct)}% of weighted facts are missing.` });
  if (missingPct >= 30) caps.push({ cap: 45, reason: `Severe omission: ${round(missingPct)}% of weighted facts are missing.` });
  if (missingPct >= 40) caps.push({ cap: 30, reason: `Critical omission: ${round(missingPct)}% of weighted facts are missing.` });

  if (criticalMissingWeight > 0) caps.push({ cap: 85, reason: `Critical visible fact omissions: ${round(criticalMissingPct)}% of critical weighted facts are missing.` });
  if (criticalMissingWeight >= 10) caps.push({ cap: 75, reason: `Meaningful critical omission: ${round(criticalMissingPct)}% of critical weighted facts are missing.` });
  if (criticalMissingWeight >= 15) caps.push({ cap: 65, reason: `Material critical omission: ${round(criticalMissingPct)}% of critical weighted facts are missing.` });
  if (criticalMissingWeight >= 25) caps.push({ cap: 45, reason: `Large critical omission: ${round(criticalMissingPct)}% of critical weighted facts are missing.` });
  if (criticalMissingWeight >= 40) caps.push({ cap: 30, reason: `Severe critical omission: ${round(criticalMissingPct)}% of critical weighted facts are missing.` });

  if (incorrectWeight > 0) caps.push({ cap: 90, reason: `Incorrect extraction: ${round(incorrectPct)}% of weighted facts are wrong.` });
  if (incorrectPct >= 3) caps.push({ cap: 80, reason: `Meaningful misinformation: ${round(incorrectPct)}% of weighted facts are incorrect.` });
  if (incorrectPct >= 5) caps.push({ cap: 70, reason: `Material misinformation: ${round(incorrectPct)}% of weighted facts are incorrect.` });
  if (incorrectPct >= 10) caps.push({ cap: 50, reason: `Large misinformation failure: ${round(incorrectPct)}% of weighted facts are incorrect.` });
  if (incorrectPct >= 15) caps.push({ cap: 35, reason: `Severe misinformation failure: ${round(incorrectPct)}% of weighted facts are incorrect.` });
  if (incorrectPct >= 25) caps.push({ cap: 20, reason: `Critical misinformation failure: ${round(incorrectPct)}% of weighted facts are incorrect.` });

  if (criticalIncorrectWeight > 0) caps.push({ cap: 85, reason: `Critical fact misinformation: ${round(criticalIncorrectPct)}% of critical weighted facts are incorrect.` });
  if (criticalIncorrectWeight >= 10) caps.push({ cap: 65, reason: `Material critical misinformation: ${round(criticalIncorrectPct)}% of critical weighted facts are incorrect.` });
  if (criticalIncorrectWeight >= 15) caps.push({ cap: 50, reason: `Large critical misinformation: ${round(criticalIncorrectPct)}% of critical weighted facts are incorrect.` });
  if (criticalIncorrectWeight >= 25) caps.push({ cap: 30, reason: `Severe critical misinformation: ${round(criticalIncorrectPct)}% of critical weighted facts are incorrect.` });
  if (criticalBadWeight >= 25) caps.push({ cap: 45, reason: `Large critical reliability failure: missing plus wrong critical facts are ${round(criticalBadPct)}% of critical weighted facts.` });
  if (criticalBadWeight >= 40) caps.push({ cap: 30, reason: `Severe critical reliability failure: missing plus wrong critical facts are ${round(criticalBadPct)}% of critical weighted facts.` });

  if (criticalVisualMissingWeight > 0) {
    caps.push({ cap: 70, reason: "Critical chart/visual relation omitted." });
  }
  if (criticalVisualMissingWeight >= 10) {
    caps.push({ cap: 55, reason: "Large critical chart/visual relation omission." });
  }
  if (criticalVisualIncorrectWeight > 0) {
    caps.push({ cap: 55, reason: "Critical chart/visual relation contradicted or misbound." });
  }
  if (criticalVisualProblemWeight >= 20) {
    caps.push({ cap: 60, reason: "Broad critical chart/visual relation failure." });
  }
  if (criticalVisualProblemWeight >= 30) {
    caps.push({ cap: 45, reason: "Severe critical chart/visual relation failure." });
  }

  if (missingPct + incorrectPct >= 20) {
    caps.push({ cap: 60, reason: `Large reliability failure: missing plus wrong facts are ${round(missingPct + incorrectPct)}% of weighted facts.` });
  }
  if (missingPct + incorrectPct >= 30) {
    caps.push({ cap: 45, reason: `Severe reliability failure: missing plus wrong facts are ${round(missingPct + incorrectPct)}% of weighted facts.` });
  }
  if (missingPct + incorrectPct >= 40) {
    caps.push({ cap: 30, reason: `Critical reliability failure: missing plus wrong facts are ${round(missingPct + incorrectPct)}% of weighted facts.` });
  }
  if (missingPct + incorrectPct >= 55) {
    caps.push({ cap: 20, reason: `Benchmark-task failure: missing plus wrong facts are ${round(missingPct + incorrectPct)}% of weighted facts.` });
  }
  if (weightedProblemPct >= 25) {
    caps.push({ cap: 55, reason: `Broad reconstruction failure: partial, missing, and wrong facts are ${round(problemPct)}% of weighted facts, with misinformation weighted more heavily.` });
  }
  if (weightedProblemPct >= 35) {
    caps.push({ cap: 45, reason: `Severe reconstruction failure: partial, missing, and wrong facts are ${round(problemPct)}% of weighted facts, with misinformation weighted more heavily.` });
  }
  if (weightedProblemPct >= 45) {
    caps.push({ cap: 35, reason: `Critical reconstruction failure: partial, missing, and wrong facts are ${round(problemPct)}% of weighted facts, with misinformation weighted more heavily.` });
  }
  if (weightedProblemPct >= 60) {
    caps.push({ cap: 25, reason: `Benchmark-task failure: partial, missing, and wrong facts are ${round(problemPct)}% of weighted facts, with misinformation weighted more heavily.` });
  }
  const rawFactScore = params.factScore.rawScore ?? 100;
  if (rawFactScore < 85) caps.push({ cap: 80, reason: "Raw signed fact score is below 85." });
  if (rawFactScore < 70) caps.push({ cap: 65, reason: "Raw signed fact score is below 70." });
  if (rawFactScore < 55) caps.push({ cap: 45, reason: "Raw signed fact score is below 55." });
  if (rawFactScore < 40) caps.push({ cap: 30, reason: "Raw signed fact score is below 40." });
  if (rawFactScore < 20) caps.push({ cap: 15, reason: "Raw signed fact score is below 20." });

  if (params.unsupported.counts.minor > 0) caps.push({ cap: 95, reason: "Candidate includes unsupported minor content." });
  if (params.unsupported.counts.major > 0) caps.push({ cap: 60, reason: "Candidate includes unsupported major content." });
  if (params.unsupported.counts.critical > 0) caps.push({ cap: 35, reason: "Candidate includes unsupported critical content." });

  if (params.coverage?.scoreCap) caps.push({ cap: params.coverage.scoreCap, reason: params.coverage.reason });

  return {
    appliedCap: caps.length === 0 ? null : Math.min(...caps.map((cap) => cap.cap)),
    caps,
    factWeightPercentages: {
      partial: possible === 0 ? 0 : round(((statusWeights.partial ?? 0) / possible) * 100),
      incorrect: round(incorrectPct),
      missing: round(missingPct),
    },
  };
}

function deterministicCaseCaps(testCase: ManifestCase, deterministic: ReturnType<typeof deterministicAudit>) {
  const failed = new Set(deterministic.details.filter((detail) => !detail.matched).map((detail) => detail.id));
  const caps: Array<{ cap: number; reason: string }> = [];

  if (testCase.id === "P07-scanned-claims-appeal") {
    if (failed.has("p07-corrected-total")) {
      caps.push({ cap: 60, reason: "Deterministic P07 check failed: corrected EOB total row is not locally reconstructed." });
    }
    if (failed.has("p07-form-correction")) {
      caps.push({ cap: 70, reason: "Deterministic P07 check failed: crossed-out/voided member responsibility and blue correction are not locally bound." });
    }
  }

  return caps;
}

function judgePrompt(testCase: ManifestCase, gold: string, facts: Fact[], prediction: string): string {
  const factBlock = facts
    .map((fact) => `- ${fact.id} [${fact.category}, weight ${fact.weight}]: ${fact.expectation}${fact.guidance ? ` Guidance: ${fact.guidance}` : ""}`)
    .join("\n");
  return `You are evaluating Doc2MD, a benchmark for converting documents into faithful Markdown.

Compare the candidate Markdown against the gold answer key. The gold answer key is the authoritative representation of the original document.

Score dimensions:
- accuracy: highest importance. A downstream AI should be able to recover the same facts, numbers, labels, checkbox states, redline/current-vs-deleted status, table bindings, chart/schedule bindings, source-state relationships, and absence of contradictions.
- completeness: whether the candidate preserves the answer-key information, regardless of whether it uses prose, lists, Markdown tables, or HTML tables.
- structure: whether grouping, locality, row/column relationships, source-state relationships, and visual-to-text relationships remain recoverable for downstream extraction.
- markdownQuality: only whether the output is machine-usable Markdown/plain text. This is not an aesthetics score.

All four score dimensions MUST be numeric scores from 0 to 100, where 100 is perfect. Do not use a 0 to 1 scale.

Important judging rules:
- Do not require identical wording or identical Markdown syntax.
- Do not penalize harmless formatting differences, section title variants, table style, HTML tables, prose instead of tables, or concise natural-language descriptions when the same information and bindings are recoverable.
- Accuracy is faithful visible-content reconstruction. Do not give credit merely because the candidate captures the gist or story of the document.
- Do not lower accuracy for malformed Markdown, raw HTML, table style, or representation choice unless it changes, hides, or makes ambiguous the actual document information for downstream extraction.
- Put representation-only problems in structure or markdownQuality, not accuracy.
- Markdown is a carrier for downstream AI consumption, not a human-facing visual replica. Prefer information recoverability over visual similarity.
- A table can be faithfully represented as a Markdown table, HTML table, bullet list, or key-value prose if row/column/label/value relationships remain unambiguous.
- A candidate should not get extra credit for looking like the source document if the data bindings are wrong, and should not lose credit for looking different if the same data can be reliably extracted.
- Penalize wrong information more than missing information.
- Penalize false assertions, invented values, wrong checkbox states, wrong table row/column bindings, wrong timeline spans, wrong units, wrong IDs, wrong dates, or treating deleted/hidden/covered text as current.
- For exact table cells, IDs, dates, units, checkbox/form states, redlines, source-state conflicts, and visible chart/panel values, mark the fact incorrect if the value or binding is wrong. Do not mark these as partial unless the mistake is truly minor and the document information remains usable.
- Wrong is worse than missing. Hallucinated or unsupported content is worse than wrong extraction.
- If the candidate is a summary rather than a reconstruction, score completeness and structure low even if some facts are correct.
- Populate unsupportedClaims for candidate content that asserts visible facts, values, states, or relationships not supported by the gold answer key. Do not include harmless headings, table wrappers, boilerplate labels, or formatting choices unless they create a false document fact.
- Findings should list only substantive issues.
- You must judge every fact obligation listed below by id.
- Fact status meanings:
  - correct: all required information is present and correctly bound.
  - partial: a genuinely compound fact is partly present and the remaining mistake is minor enough that the represented document information is still mostly usable.
  - incorrect: the candidate asserts a contradictory or wrong value/binding/state.
  - missing: the information is absent or too vague to verify.
- Visual facts do not need to be redrawn as images. Charts, diagrams, chromatograms, floorplans, cards, maps, and screenshots may be faithfully represented as prose, lists, Markdown tables, or HTML tables.
- For a visual fact, mark correct when the candidate preserves the required labels, values, trends, thresholds, legends, spatial relations, and local meaning, even if the original visual form is not recreated.
- Mark a visual fact partial only when a required visual value/relation/state is actually missing or ambiguous. Do not mark partial merely because the candidate uses text instead of a chart or image.

Case: ${testCase.id} - ${testCase.title}
Family: ${testCase.family}
Tags: ${testCase.tags.join(", ")}

FACT OBLIGATIONS:
<<<FACTS
${factBlock}
FACTS

GOLD ANSWER KEY:
<<<GOLD
${gold}
GOLD

CANDIDATE MARKDOWN:
<<<CANDIDATE
${prediction}
CANDIDATE`;
}

async function judgeWithGemini(testCase: ManifestCase, gold: string, facts: Fact[], prediction: string): Promise<{
  result: JudgeResult;
  elapsedMs: number;
  usage: any;
  estimatedCostUsd: number;
}> {
  const started = performance.now();
  const response = await generateObject({
    model: googleVertex(evaluator.modelName),
    schema: judgeSchema,
    prompt: judgePrompt(testCase, gold, facts, prediction),
    reasoning: evaluator.reasoning,
    maxOutputTokens: judgeMaxOutputTokens,
  });
  const elapsedMs = Math.round(performance.now() - started);
  return {
    result: response.object,
    elapsedMs,
    usage: response.usage,
    estimatedCostUsd: cost(response.usage),
  };
}

async function scoringCacheKey(testCase: ManifestCase, predictionPath: string) {
  const predictionHash = await fileSha256(predictionPath);
  const goldHash = await fileSha256(testCase.gold);
  const checksHash = await fileSha256(testCase.checks);
  const factsHash = testCase.facts ? await fileSha256(testCase.facts) : null;
  const judgeConfigHash = hashObject({
    evaluator,
    judgeMaxOutputTokens,
    judgePromptHash: sha256(judgePrompt.toString()),
    judgeSchemaHash: hashObject(judgeSchema.toJSONSchema()),
  });
  const judgeKey = hashObject({
    caseId: testCase.id,
    predictionHash,
    goldHash,
    factsHash,
    judgeConfigHash,
  });
  const scoringConfigHash = hashObject({
    scoringVersion,
    weights,
    factStatusCredit,
    unsupportedClaimPenalty,
    scoreCapsHash: sha256(scoreCaps.toString()),
    deterministicCaseCapsHash: sha256(deterministicCaseCaps.toString()),
  });
  return {
    scoreKey: hashObject({
      caseId: testCase.id,
      checksHash,
      judgeKey,
      scoringConfigHash,
    }),
    judgeKey,
    predictionHash,
    goldHash,
    checksHash,
    factsHash,
    judgeConfigHash,
    scoringConfigHash,
  };
}

export async function scoreCase(
  modelId: string,
  testCase: ManifestCase,
  options: {
    suite?: string;
    manifestPath?: string;
    inputProtocol?: string;
    predictionPath: string;
    resultPath: string;
    scorePath: string;
  },
) {
  const checkFile = JSON.parse(await readFile(testCase.checks, "utf-8")) as CheckFile;
  const factFile = testCase.facts
    ? (JSON.parse(await readFile(testCase.facts, "utf-8")) as FactFile)
    : ({ facts: [] } as unknown as FactFile);
  const predictionPath = options.predictionPath;
  const resultPath = options.resultPath;
  const scorePath = options.scorePath;
  const scoreCache = await scoringCacheKey(testCase, predictionPath);
  if (await exists(scorePath)) {
    const previous = JSON.parse(await readFile(scorePath, "utf-8")) as any;
    if (previous.scorer?.cache?.scoreKey === scoreCache.scoreKey && !previous.scorer.error) {
      console.log(`${modelId} ${testCase.id}: score skip unchanged`);
      return previous;
    }
  }

  const rawPrediction = await readFile(predictionPath, "utf-8");
  const prediction = normalize(rawPrediction);
  const gold = await readFile(testCase.gold, "utf-8");
  const result = JSON.parse(await readFile(resultPath, "utf-8"));
  const failed = Boolean(result.error || result.finishReason === "error");
  const deterministic = deterministicAudit(checkFile, prediction, failed);

  let judge: JudgeResult;
  let judgeElapsedMs = 0;
  let judgeUsage: any = null;
  let judgeCostUsd = 0;
  let judgeError: string | undefined;
  let judgeReused = false;

  if (failed) {
    judge = {
      accuracy: 0,
      completeness: 0,
      structure: 0,
      markdownQuality: 0,
      factResults: factFile.facts.map((fact) => ({ id: fact.id, status: "missing", rationale: "Model run failed." })),
      unsupportedClaims: [],
      findings: [{ severity: "critical", type: "missing", explanation: "Model run failed, so no faithful Markdown was produced." }],
      rationale: "The model run failed.",
    };
  } else {
    try {
      const previous = (await exists(scorePath)) ? (JSON.parse(await readFile(scorePath, "utf-8")) as any) : null;
      if (previous?.scorer?.cache?.judgeKey === scoreCache.judgeKey && previous.judgeResult) {
        judge = previous.judgeResult as JudgeResult;
        judgeReused = true;
      } else {
        const judged = await judgeWithGemini(testCase, gold, factFile.facts, rawPrediction);
        judge = judged.result;
        judgeElapsedMs = judged.elapsedMs;
        judgeUsage = judged.usage;
        judgeCostUsd = judged.estimatedCostUsd;
      }
    } catch (error) {
      judgeError = error instanceof Error ? error.message : String(error);
      judge = {
        accuracy: 0,
        completeness: 0,
        structure: 0,
        markdownQuality: 0,
        factResults: factFile.facts.map((fact) => ({ id: fact.id, status: "missing", rationale: `Evaluator failed: ${judgeError}` })),
        unsupportedClaims: [],
        findings: [{ severity: "critical", type: "missing", explanation: `Evaluator failed: ${judgeError}` }],
        rationale: "The evaluator failed.",
      };
    }
  }

  const factScore = scoreFacts(factFile.facts, judge.factResults ?? []);
  const coverage = reconstructionCoverage(testCase, gold, rawPrediction);
  const unsupported = unsupportedAudit(judge);
  const factFidelity = factScore.score ?? clampScore(judge.accuracy);
  const penalizedAccuracy = Math.max(0, factFidelity - unsupported.penalty);
  const dimensionScores = {
    accuracy: penalizedAccuracy,
    completeness: Math.min(clampScore(judge.completeness), coverage?.completenessCap ?? 100, factFidelity + 15),
    structure: Math.min(clampScore(judge.structure), factFidelity + 20),
    markdownQuality: Math.min(clampScore(judge.markdownQuality), factFidelity + 25),
  };
  const caps = scoreCaps({ factScore, unsupported, coverage });
  const caseCaps = deterministicCaseCaps(testCase, deterministic);
  const appliedCap = Math.min(caps.appliedCap ?? 100, ...caseCaps.map((cap) => cap.cap), 100);
  const uncappedScore = round(
    dimensionScores.accuracy * weights.accuracy +
      dimensionScores.completeness * weights.completeness +
      dimensionScores.structure * weights.structure +
      dimensionScores.markdownQuality * weights.markdownQuality,
  );
  const score = round(Math.min(uncappedScore, appliedCap));

  const scored = {
    caseId: testCase.id,
    title: checkFile.title,
    family: checkFile.family,
    tags: checkFile.tags,
    modelId,
    suite: options.suite ?? "official",
    manifestPath: options.manifestPath ?? "benchmark/manifest.json",
    inputProtocol: options.inputProtocol ?? "native_pdf",
    runCache: result.cache ?? null,
    score,
    uncappedScore,
    scorer: {
      type: "llm-gold-comparison",
      evaluatorModelId: evaluator.id,
      evaluatorModelName: evaluator.modelName,
      evaluatorReasoning: evaluator.reasoning,
      weights,
      elapsedMs: judgeElapsedMs,
      usage: judgeUsage,
      estimatedCostUsd: judgeCostUsd,
      judgeReused,
      error: judgeError,
      cache: scoreCache,
    },
    coverage,
    caps: {
      appliedCap: appliedCap === 100 ? null : appliedCap,
      caps: [...caps.caps, ...caseCaps],
      factWeightPercentages: caps.factWeightPercentages,
    },
    unsupported,
    dimensions: dimensionScores,
    factScore,
    judgeResult: judge,
    findings: judge.findings,
    rationale: judge.rationale,
    deterministic,
    estimatedCostUsd: result.estimatedCostUsd ?? 0,
    elapsedMs: result.elapsedMs ?? 0,
    usage: result.usage ?? null,
    outputLength: result.outputLength ?? prediction.length,
    finishReason: result.finishReason ?? "unknown",
    error: result.error,
  };

  await writeFile(scorePath, JSON.stringify(scored, null, 2) + "\n", "utf-8");
  return scored;
}

async function currentTarget(modelId: string, testCase: ManifestCase, activeRunKey: string) {
  const runDir = path.join("runs", modelId, testCase.id);
  const resultPath = path.join(runDir, "result.json");
  const result = await readJsonIfExists(resultPath);
  if (result?.cache?.runKey !== activeRunKey) return null;
  return {
    predictionPath: path.join(runDir, "prediction.md"),
    resultPath,
    scorePath: path.join(runDir, "score.json"),
  };
}

export async function scoreModel(modelId: string, options: { manifestPath?: string } = {}) {
  const manifestPath = options.manifestPath ?? "benchmark/manifest.json";
  const manifest = JSON.parse(await readFile(manifestPath, "utf-8")) as Manifest;
  const spec = models[modelId];
  if (!spec) throw new Error(`Unknown model ${modelId}. Options: ${Object.keys(models).join(", ")}`);
  const context = await buildRunContext(spec, manifest as any, manifestPath);
  const existing = new Set(await readdir(path.join("runs", modelId)));
  const cases = manifest.cases.filter((testCase) => existing.has(testCase.id));
  if (cases.length === 0) throw new Error(`No run outputs found for ${modelId}`);

  const targets = (
    await Promise.all(
      cases.map(async (testCase) => {
        const activeRun = await runCacheKey(testCase as any, spec, context);
        const target = await currentTarget(modelId, testCase, activeRun.runKey);
        return target ? [{ testCase, target }] : [];
      }),
    )
  ).flat();
  if (targets.length === 0) throw new Error(`No current run outputs found for ${modelId}`);

  const scores = await Promise.all(
    targets.map(({ testCase, target }) =>
      scoreCase(modelId, testCase, {
        suite: manifest.suite ?? "official",
        manifestPath,
        inputProtocol: manifest.inputProtocol ?? "native_pdf",
        ...target,
      }),
    ),
  );
  for (const scored of scores) {
    console.log(
      `${modelId} ${scored.caseId}: ${scored.score.toFixed(1)} ` +
        `(accuracy ${scored.dimensions.accuracy.toFixed(1)}, judge $${scored.scorer.estimatedCostUsd.toFixed(6)})`,
    );
  }

  console.table(
    scores.map((score) => ({
      case: score.caseId,
      pct: score.score,
      accuracy: score.dimensions.accuracy,
      family: score.family,
      finish: score.finishReason,
      cost: Number(score.estimatedCostUsd.toFixed(6)),
      judgeCost: Number(score.scorer.estimatedCostUsd.toFixed(6)),
      ms: score.elapsedMs,
    })),
  );
  return scores;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const { args, positionals } = parseArgs();
  rejectUnknownArgs(args, ["model", "manifest"]);
  const modelId = positionals[0] ?? args.get("model") ?? "vertex-gemini-3.1-flash-lite";
  await scoreModel(modelId, { manifestPath: args.get("manifest") });
}
