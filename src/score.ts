import { readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";

type Check = {
  id: string;
  category: string;
  weight: number;
  description: string;
  patterns?: string[];
  mustNotPatterns?: string[];
};

type ChecksFile = {
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
    .replace(/[ \t]+/g, " ")
    .replace(/[“”]/g, '"')
    .replace(/[‘’]/g, "'")
    .trim();
}

function testPattern(pattern: string, text: string): boolean {
  return new RegExp(pattern, "imu").test(text);
}

async function scoreCase(modelId: string, testCase: ManifestCase) {
  const checksFile = JSON.parse(await readFile(testCase.checks, "utf-8")) as ChecksFile;
  const runDir = path.join("runs", modelId, testCase.id);
  const prediction = normalize(await readFile(path.join(runDir, "prediction.md"), "utf-8"));
  const result = JSON.parse(await readFile(path.join(runDir, "result.json"), "utf-8"));

  let earned = 0;
  let possible = 0;
  const byCategory: Record<string, { earned: number; possible: number }> = {};
  const details = checksFile.checks.map((check) => {
    possible += check.weight;
    byCategory[check.category] ??= { earned: 0, possible: 0 };
    byCategory[check.category].possible += check.weight;
    const positive = check.patterns?.every((pattern) => testPattern(pattern, prediction)) ?? true;
    const forbidden = check.mustNotPatterns?.some((pattern) => testPattern(pattern, prediction)) ?? false;
    const matched = positive && !forbidden;
    if (matched) {
      earned += check.weight;
      byCategory[check.category].earned += check.weight;
    }
    return { ...check, matched };
  });
  const score = possible === 0 ? 0 : (earned / possible) * 100;
  const categoryScores = Object.fromEntries(
    Object.entries(byCategory).map(([category, value]) => [
      category,
      value.possible === 0 ? null : Math.round((value.earned / value.possible) * 1000) / 10,
    ]),
  );
  const scored = {
    caseId: testCase.id,
    title: checksFile.title,
    family: checksFile.family,
    tags: checksFile.tags,
    modelId,
    score: Math.round(score * 10) / 10,
    earned,
    possible,
    categoryScores,
    estimatedCostUsd: result.estimatedCostUsd ?? 0,
    elapsedMs: result.elapsedMs ?? 0,
    usage: result.usage ?? null,
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

if (cases.length === 0) {
  throw new Error(`No run outputs found for ${modelId}`);
}

const scores = [];
for (const testCase of cases) {
  scores.push(await scoreCase(modelId, testCase));
}

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
