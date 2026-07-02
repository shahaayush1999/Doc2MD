import { readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";

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
  checks: string;
};

type Manifest = {
  cases: ManifestCase[];
};

function normalize(text: string): string {
  return text
    .replace(/\r\n/g, "\n")
    .replace(/<[^>]+>/g, " ")
    .replace(/[*_`~]+/g, "")
    .replace(/(\d+(?:\.\d+)?)\s+h\b/giu, "$1h")
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

async function scoreCase(modelId: string, testCase: ManifestCase) {
  const checkFile = JSON.parse(await readFile(testCase.checks, "utf-8")) as CheckFile;
  const runDir = path.join("runs", modelId, testCase.id);
  const prediction = normalize(await readFile(path.join(runDir, "prediction.md"), "utf-8"));
  const result = JSON.parse(await readFile(path.join(runDir, "result.json"), "utf-8"));

  let earned = 0;
  let possible = 0;
  const byCategory: Record<string, { earned: number; possible: number }> = {};

  const details = checkFile.checks.map((check) => {
    possible += check.weight;
    byCategory[check.category] ??= { earned: 0, possible: 0 };
    byCategory[check.category].possible += check.weight;
    const matched =
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
      value.possible === 0 ? null : Math.round((value.earned / value.possible) * 1000) / 10,
    ]),
  );

  const score = possible === 0 ? 0 : (earned / possible) * 100;
  const scored = {
    caseId: testCase.id,
    title: checkFile.title,
    family: checkFile.family,
    tags: checkFile.tags,
    modelId,
    score: Math.round(score * 10) / 10,
    earned,
    possible,
    categoryScores,
    estimatedCostUsd: result.estimatedCostUsd ?? 0,
    elapsedMs: result.elapsedMs ?? 0,
    usage: result.usage ?? null,
    outputLength: result.outputLength ?? prediction.length,
    finishReason: result.finishReason ?? "unknown",
    error: result.error,
    details,
  };

  await writeFile(path.join(runDir, "score.json"), JSON.stringify(scored, null, 2) + "\n", "utf-8");
  return scored;
}

const modelId = process.argv[2] ?? "vertex-gemini-3.1-flash-lite";
const manifest = JSON.parse(await readFile("benchmark/manifest.json", "utf-8")) as Manifest;
const existing = new Set(await readdir(path.join("runs", modelId)));
const cases = manifest.cases.filter((testCase) => existing.has(testCase.id));
if (cases.length === 0) throw new Error(`No run outputs found for ${modelId}`);

const scores = [];
for (const testCase of cases) scores.push(await scoreCase(modelId, testCase));

console.table(
  scores.map((score) => ({
    case: score.caseId,
    pct: score.score,
    family: score.family,
    finish: score.finishReason,
    cost: Number(score.estimatedCostUsd.toFixed(6)),
    ms: score.elapsedMs,
  })),
);
