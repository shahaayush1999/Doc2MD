import { access, readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { performance } from "node:perf_hooks";
import { fileURLToPath } from "node:url";
import { generateObject } from "ai";
import { googleVertex } from "@ai-sdk/google-vertex";
import { z } from "zod";
import { fileSha256, hashObject, sha256 } from "./cache.js";

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
  gold: string;
  checks: string;
  facts?: string;
};

type Manifest = {
  cases: ManifestCase[];
};

type JudgeFinding = {
  severity: "critical" | "major" | "minor";
  type: "missing" | "incorrect" | "extra" | "structure" | "format";
  explanation: string;
  expected?: string;
  actual?: string;
};

type Fact = {
  id: string;
  category: string;
  weight: number;
  expectation: string;
  guidance?: string;
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
  accuracy: 0.75,
  completeness: 0.1,
  structure: 0.1,
  markdownQuality: 0.05,
};

const scoringVersion = "fact-judge-v1";
const judgeMaxOutputTokens = 3000;

const scoreField = z.number().min(0).max(100);

const judgeSchema = z.object({
  accuracy: scoreField.describe(
    "Semantic correctness of represented facts, values, labels, state, and bindings. Penalize contradictions and wrong values heavily, but do not lower accuracy for formatting-only issues.",
  ),
  completeness: scoreField.describe("Coverage of all information in the gold answer key."),
  structure: scoreField.describe("Preservation of reading order, grouping, table/list/form structure, and visual-to-text bindings."),
  markdownQuality: scoreField.describe("Usefulness and clarity of Markdown representation. Do not penalize harmless formatting differences."),
  factResults: z
    .array(
      z.object({
        id: z.string(),
        status: z.enum(["correct", "partial", "incorrect", "missing"]),
        rationale: z.string(),
      }),
    )
    .describe("Per-fact judgments for every listed fact obligation."),
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

function factStatusValue(status: FactResult["status"]): number {
  if (status === "correct") return 1;
  if (status === "partial") return 0.5;
  return 0;
}

function scoreFacts(facts: Fact[], factResults: FactResult[]) {
  const byId = new Map(factResults.map((result) => [result.id, result]));
  let earned = 0;
  let possible = 0;
  const details = facts.map((fact) => {
    possible += fact.weight;
    const result = byId.get(fact.id) ?? { id: fact.id, status: "missing" as const, rationale: "The evaluator did not return a judgment for this fact." };
    const credit = factStatusValue(result.status) * fact.weight;
    earned += credit;
    return { ...fact, status: result.status, rationale: result.rationale, earned: round(credit, 2) };
  });
  return {
    score: possible === 0 ? null : round((earned / possible) * 100),
    earned: round(earned, 2),
    possible: round(possible, 2),
    details,
  };
}

function judgePrompt(testCase: ManifestCase, gold: string, facts: Fact[], prediction: string): string {
  const factBlock = facts
    .map((fact) => `- ${fact.id} [${fact.category}, weight ${fact.weight}]: ${fact.expectation}${fact.guidance ? ` Guidance: ${fact.guidance}` : ""}`)
    .join("\n");
  return `You are evaluating Doc2MD, a benchmark for converting documents into faithful Markdown.

Compare the candidate Markdown against the gold answer key. The gold answer key is the authoritative representation of the original document.

Score dimensions:
- accuracy: highest importance. Correct facts, numbers, labels, checkbox states, redline/current-vs-deleted status, table bindings, chart/schedule bindings, and absence of contradictions.
- completeness: whether the candidate preserves all information in the gold answer key.
- structure: whether reading order, grouping, table/list/form structure, and visual-to-text relationships are faithfully represented.
- markdownQuality: whether the Markdown is usable and clear.

All four score dimensions MUST be numeric scores from 0 to 100, where 100 is perfect. Do not use a 0 to 1 scale.

Important judging rules:
- Do not require identical wording or identical Markdown syntax.
- Do not penalize harmless formatting differences, section title variants, or concise natural-language descriptions when the same information is faithfully represented.
- Accuracy is semantic fidelity. Do not lower accuracy for malformed Markdown, raw HTML, table style, or representation choice unless it changes, hides, or makes ambiguous the actual document information.
- Put representation-only problems in structure or markdownQuality, not accuracy.
- Penalize wrong information more than missing information.
- Penalize false assertions, invented values, wrong checkbox states, wrong table row/column bindings, wrong timeline spans, or treating deleted/hidden/covered text as current.
- If the candidate is a summary rather than a reconstruction, score completeness and structure low even if some facts are correct.
- Findings should list only substantive issues.
- You must judge every fact obligation listed below by id.
- Fact status meanings:
  - correct: all required information is present and correctly bound.
  - partial: some required information is present, but a minor value, binding, or context is missing.
  - incorrect: the candidate asserts a contradictory or wrong value/binding/state.
  - missing: the information is absent or too vague to verify.

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
  const evaluatorConfigHash = hashObject({
    scoringVersion,
    evaluator,
    weights,
    judgeMaxOutputTokens,
    judgePromptHash: sha256(judgePrompt.toString()),
    judgeSchemaHash: hashObject(judgeSchema.toJSONSchema()),
  });
  return {
    scoreKey: hashObject({
      caseId: testCase.id,
      predictionHash,
      goldHash,
      checksHash,
      factsHash,
      evaluatorConfigHash,
    }),
    predictionHash,
    goldHash,
    checksHash,
    factsHash,
    evaluatorConfigHash,
  };
}

export async function scoreCase(modelId: string, testCase: ManifestCase, options: { force?: boolean } = {}) {
  const checkFile = JSON.parse(await readFile(testCase.checks, "utf-8")) as CheckFile;
  const factFile = testCase.facts
    ? (JSON.parse(await readFile(testCase.facts, "utf-8")) as FactFile)
    : ({ facts: [] } as unknown as FactFile);
  const runDir = path.join("runs", modelId, testCase.id);
  const predictionPath = path.join(runDir, "prediction.md");
  const scorePath = path.join(runDir, "score.json");
  const scoreCache = await scoringCacheKey(testCase, predictionPath);
  if (!options.force && (await exists(scorePath))) {
    const previous = JSON.parse(await readFile(scorePath, "utf-8")) as any;
    if (previous.scorer?.cache?.scoreKey === scoreCache.scoreKey && !previous.scorer.error) {
      console.log(`${modelId} ${testCase.id}: score skip unchanged`);
      return previous;
    }
  }

  const rawPrediction = await readFile(predictionPath, "utf-8");
  const prediction = normalize(rawPrediction);
  const gold = await readFile(testCase.gold, "utf-8");
  const result = JSON.parse(await readFile(path.join(runDir, "result.json"), "utf-8"));
  const failed = Boolean(result.error || result.finishReason === "error");
  const deterministic = deterministicAudit(checkFile, prediction, failed);

  let judge: JudgeResult;
  let judgeElapsedMs = 0;
  let judgeUsage: any = null;
  let judgeCostUsd = 0;
  let judgeError: string | undefined;

  if (failed) {
    judge = {
      accuracy: 0,
      completeness: 0,
      structure: 0,
      markdownQuality: 0,
      factResults: factFile.facts.map((fact) => ({ id: fact.id, status: "missing", rationale: "Model run failed." })),
      findings: [{ severity: "critical", type: "missing", explanation: "Model run failed, so no faithful Markdown was produced." }],
      rationale: "The model run failed.",
    };
  } else {
    try {
      const judged = await judgeWithGemini(testCase, gold, factFile.facts, rawPrediction);
      judge = judged.result;
      judgeElapsedMs = judged.elapsedMs;
      judgeUsage = judged.usage;
      judgeCostUsd = judged.estimatedCostUsd;
    } catch (error) {
      judgeError = error instanceof Error ? error.message : String(error);
      judge = {
        accuracy: 0,
        completeness: 0,
        structure: 0,
        markdownQuality: 0,
        factResults: factFile.facts.map((fact) => ({ id: fact.id, status: "missing", rationale: `Evaluator failed: ${judgeError}` })),
        findings: [{ severity: "critical", type: "missing", explanation: `Evaluator failed: ${judgeError}` }],
        rationale: "The evaluator failed.",
      };
    }
  }

  const factScore = scoreFacts(factFile.facts, judge.factResults ?? []);
  const dimensionScores = {
    accuracy: factScore.score ?? clampScore(judge.accuracy),
    completeness: clampScore(judge.completeness),
    structure: clampScore(judge.structure),
    markdownQuality: clampScore(judge.markdownQuality),
  };
  const score = round(
    dimensionScores.accuracy * weights.accuracy +
      dimensionScores.completeness * weights.completeness +
      dimensionScores.structure * weights.structure +
      dimensionScores.markdownQuality * weights.markdownQuality,
  );

  const scored = {
    caseId: testCase.id,
    title: checkFile.title,
    family: checkFile.family,
    tags: checkFile.tags,
    modelId,
    score,
    scorer: {
      type: "llm-gold-comparison",
      evaluatorModelId: evaluator.id,
      evaluatorModelName: evaluator.modelName,
      evaluatorReasoning: evaluator.reasoning,
      weights,
      elapsedMs: judgeElapsedMs,
      usage: judgeUsage,
      estimatedCostUsd: judgeCostUsd,
      error: judgeError,
      cache: scoreCache,
    },
    dimensions: dimensionScores,
    factScore,
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

  await writeFile(path.join(runDir, "score.json"), JSON.stringify(scored, null, 2) + "\n", "utf-8");
  return scored;
}

export async function scoreModel(modelId: string, options: { force?: boolean } = {}) {
  const manifest = JSON.parse(await readFile("benchmark/manifest.json", "utf-8")) as Manifest;
  const existing = new Set(await readdir(path.join("runs", modelId)));
  const cases = manifest.cases.filter((testCase) => existing.has(testCase.id));
  if (cases.length === 0) throw new Error(`No run outputs found for ${modelId}`);

  const scores = [];
  for (const testCase of cases) {
    const scored = await scoreCase(modelId, testCase, { force: options.force });
    scores.push(scored);
    console.log(
      `${modelId} ${testCase.id}: ${scored.score.toFixed(1)} ` +
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
  const modelId = process.argv[2] ?? "vertex-gemini-3.1-flash-lite";
  await scoreModel(modelId, { force: process.argv.includes("--force") });
}
