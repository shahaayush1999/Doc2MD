import { readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";

type Score = {
  caseId: string;
  title: string;
  family: string;
  score: number;
  dimensions?: Record<string, number>;
  findings?: Array<{ severity: string; type: string; explanation: string }>;
  scorer?: { estimatedCostUsd?: number; elapsedMs?: number; evaluatorModelId?: string };
  estimatedCostUsd: number;
  elapsedMs: number;
  usage: { inputTokens?: number; outputTokens?: number; totalTokens?: number } | null;
  outputLength: number;
  finishReason: string;
  error?: string;
  deterministic?: {
    score: number;
    categoryScores: Record<string, number | null>;
    details: Array<{ category: string; description: string; matched: boolean }>;
  };
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
const manifest = JSON.parse(await readFile("benchmark/manifest.json", "utf-8")) as { cases: Array<{ id: string }> };
const manifestCaseIds = new Set(manifest.cases.map((testCase) => testCase.id));
const caseIds = (await readdir(runRoot)).filter((name) => manifestCaseIds.has(name));
const scores: Score[] = [];
for (const caseId of caseIds) {
  try {
    scores.push(JSON.parse(await readFile(path.join(runRoot, caseId, "score.json"), "utf-8")) as Score);
  } catch {
    // Ignore unscored runs.
  }
}
scores.sort((a, b) => a.caseId.localeCompare(b.caseId));

const families = new Map<string, Score[]>();
const dimensions = new Map<string, number[]>();
const deterministicCategories = new Map<string, number[]>();
for (const score of scores) {
  families.set(score.family, [...(families.get(score.family) ?? []), score]);
  for (const [dimension, value] of Object.entries(score.dimensions ?? {})) {
    if (typeof value === "number") dimensions.set(dimension, [...(dimensions.get(dimension) ?? []), value]);
  }
  for (const [category, value] of Object.entries(score.deterministic?.categoryScores ?? {})) {
    if (typeof value === "number") deterministicCategories.set(category, [...(deterministicCategories.get(category) ?? []), value]);
  }
}

const familyScores = Object.fromEntries([...families.entries()].map(([family, values]) => [family, round(mean(values.map((s) => s.score)))]));
const dimensionScores = Object.fromEntries([...dimensions.entries()].map(([dimension, values]) => [dimension, round(mean(values))]));
const deterministicCategoryScores = Object.fromEntries(
  [...deterministicCategories.entries()].map(([category, values]) => [category, round(mean(values))]),
);
const failed = scores.filter((score) => score.error || score.finishReason === "error");
const totalCostUsd = scores.reduce((sum, score) => sum + score.estimatedCostUsd, 0);
const totalJudgeCostUsd = scores.reduce((sum, score) => sum + (score.scorer?.estimatedCostUsd ?? 0), 0);
const totalJudgeElapsedMs = scores.reduce((sum, score) => sum + (score.scorer?.elapsedMs ?? 0), 0);
const totalElapsedMs = scores.reduce((sum, score) => sum + score.elapsedMs, 0);
const totalInputTokens = scores.reduce((sum, score) => sum + (score.usage?.inputTokens ?? 0), 0);
const totalOutputTokens = scores.reduce((sum, score) => sum + (score.usage?.outputTokens ?? 0), 0);
const totalOutputLength = scores.reduce((sum, score) => sum + score.outputLength, 0);
const weakestFindings = scores.flatMap((score) =>
  (score.findings ?? [])
    .filter((finding) => finding.severity === "critical" || finding.severity === "major")
    .map((finding) => ({ caseId: score.caseId, severity: finding.severity, type: finding.type, explanation: finding.explanation })),
);
const weakestDeterministicChecks = scores.flatMap((score) =>
  (score.deterministic?.details ?? [])
    .filter((detail) => !detail.matched)
    .map((detail) => ({ caseId: score.caseId, category: detail.category, description: detail.description })),
);

const summary = {
  modelId,
  caseCount: scores.length,
  overallScore: round(mean(scores.map((score) => score.score))),
  familyMinimum: round(Math.min(...Object.values(familyScores))),
  familyScores,
  dimensionScores,
  deterministicCategoryScores,
  totalCostUsd: round(totalCostUsd, 6),
  totalJudgeCostUsd: round(totalJudgeCostUsd, 6),
  totalElapsedMs,
  totalJudgeElapsedMs,
  averageElapsedMs: Math.round(mean(scores.map((score) => score.elapsedMs))),
  totalInputTokens,
  totalOutputTokens,
  totalOutputLength,
  failureRate: scores.length === 0 ? 0 : round((failed.length / scores.length) * 100),
  cases: scores.map((score) => ({
    id: score.caseId,
    title: score.title,
    family: score.family,
    score: score.score,
    accuracy: score.dimensions?.accuracy,
    finishReason: score.finishReason,
    elapsedMs: score.elapsedMs,
    estimatedCostUsd: round(score.estimatedCostUsd, 6),
    judgeCostUsd: round(score.scorer?.estimatedCostUsd ?? 0, 6),
    deterministicScore: score.deterministic?.score,
  })),
  weakestFindings,
  weakestDeterministicChecks,
};

await writeFile(path.join(runRoot, "summary.json"), JSON.stringify(summary, null, 2) + "\n", "utf-8");
console.log(JSON.stringify(summary, null, 2));
