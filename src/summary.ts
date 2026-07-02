import { readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";

type CaseScore = {
  caseId: string;
  title: string;
  family: string;
  score: number;
  estimatedCostUsd: number;
  elapsedMs: number;
  usage: { inputTokens?: number; outputTokens?: number; totalTokens?: number } | null;
  finishReason: string;
  error?: string;
  categoryScores: Record<string, number | null>;
  details: Array<{ id: string; category: string; description: string; matched: boolean }>;
};

function mean(values: number[]) {
  return values.length === 0 ? 0 : values.reduce((sum, value) => sum + value, 0) / values.length;
}

function round(value: number, digits = 1) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

const modelId = process.argv[2] ?? "vertex-gemini-3.1-flash-lite";
const runRoot = path.join("runs", modelId);
const caseIds = await readdir(runRoot);
const scores: CaseScore[] = [];
for (const caseId of caseIds) {
  const scorePath = path.join(runRoot, caseId, "score.json");
  try {
    scores.push(JSON.parse(await readFile(scorePath, "utf-8")) as CaseScore);
  } catch {
    // Ignore unscored runs.
  }
}

scores.sort((a, b) => a.caseId.localeCompare(b.caseId));

const familyMap = new Map<string, CaseScore[]>();
const categoryBuckets = new Map<string, number[]>();
for (const score of scores) {
  familyMap.set(score.family, [...(familyMap.get(score.family) ?? []), score]);
  for (const [category, value] of Object.entries(score.categoryScores)) {
    if (typeof value === "number") {
      categoryBuckets.set(category, [...(categoryBuckets.get(category) ?? []), value]);
    }
  }
}

const familyScores = Object.fromEntries(
  [...familyMap.entries()].map(([family, values]) => [family, round(mean(values.map((score) => score.score)))]),
);
const categoryScores = Object.fromEntries(
  [...categoryBuckets.entries()].map(([category, values]) => [category, round(mean(values))]),
);
const totalCostUsd = scores.reduce((sum, score) => sum + score.estimatedCostUsd, 0);
const totalElapsedMs = scores.reduce((sum, score) => sum + score.elapsedMs, 0);
const totalInputTokens = scores.reduce((sum, score) => sum + (score.usage?.inputTokens ?? 0), 0);
const totalOutputTokens = scores.reduce((sum, score) => sum + (score.usage?.outputTokens ?? 0), 0);
const failed = scores.filter((score) => score.finishReason === "error" || score.error);
const weakestChecks = scores.flatMap((score) =>
  score.details
    .filter((detail) => !detail.matched)
    .slice(0, 8)
    .map((detail) => ({
      caseId: score.caseId,
      category: detail.category,
      description: detail.description,
    })),
);

const summary = {
  modelId,
  caseCount: scores.length,
  overallScore: round(mean(scores.map((score) => score.score))),
  familyMinimum: round(Math.min(...Object.values(familyScores))),
  familyScores,
  categoryScores,
  totalCostUsd: round(totalCostUsd, 6),
  totalElapsedMs,
  averageElapsedMs: Math.round(mean(scores.map((score) => score.elapsedMs))),
  totalInputTokens,
  totalOutputTokens,
  failureRate: scores.length === 0 ? 0 : round((failed.length / scores.length) * 100),
  cases: scores.map((score) => ({
    id: score.caseId,
    title: score.title,
    family: score.family,
    score: score.score,
    finishReason: score.finishReason,
    elapsedMs: score.elapsedMs,
    estimatedCostUsd: round(score.estimatedCostUsd, 6),
  })),
  weakestChecks,
};

await writeFile(path.join(runRoot, "summary.json"), JSON.stringify(summary, null, 2) + "\n", "utf-8");
console.log(JSON.stringify(summary, null, 2));
