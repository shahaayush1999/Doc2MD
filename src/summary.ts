import { readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

type Score = {
  caseId: string;
  title?: string;
  family?: string;
  score: number;
  uncappedScore?: number;
  dimensions?: {
    accuracy?: number;
    completeness?: number;
    structure?: number;
    markdownQuality?: number;
  };
  factScore?: {
    rawScore?: number | null;
    statusWeights?: Record<string, number>;
  };
  caps?: {
    appliedCap?: number | null;
  };
  unsupported?: {
    penalty?: number;
    counts?: Record<string, number>;
  };
  estimatedCostUsd: number;
  elapsedMs: number;
  usage: { inputTokens?: number; outputTokens?: number; totalTokens?: number } | null;
  finishReason: string;
  error?: string;
};

function mean(values: number[]) {
  return values.length === 0 ? 0 : values.reduce((sum, value) => sum + value, 0) / values.length;
}

function weightedMean(values: Array<{ value: number; weight: number }>) {
  const totalWeight = values.reduce((sum, item) => sum + item.weight, 0);
  if (totalWeight === 0) return 0;
  return values.reduce((sum, item) => sum + item.value * item.weight, 0) / totalWeight;
}

function round(value: number, digits = 1) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

export async function summarizeModel(modelId: string) {
  const runRoot = path.join("runs", modelId);
  const manifest = JSON.parse(await readFile("benchmark/manifest.json", "utf-8")) as { cases: Array<{ id: string; pages?: number }> };
  const manifestCaseIds = new Set(manifest.cases.map((testCase) => testCase.id));
  const pagesByCaseId = new Map(manifest.cases.map((testCase) => [testCase.id, testCase.pages ?? 1]));
  const expectedCaseIds = manifest.cases.map((testCase) => testCase.id);
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
  const scoredCaseIds = new Set(scores.map((score) => score.caseId));
  const missingCaseIds = expectedCaseIds.filter((caseId) => !scoredCaseIds.has(caseId));

  const failed = scores.filter((score) => score.error || score.finishReason === "error");
  const totalCostUsd = scores.reduce((sum, score) => sum + score.estimatedCostUsd, 0);
  const totalElapsedMs = scores.reduce((sum, score) => sum + score.elapsedMs, 0);
  const totalInputTokens = scores.reduce((sum, score) => sum + (score.usage?.inputTokens ?? 0), 0);
  const totalOutputTokens = scores.reduce((sum, score) => sum + (score.usage?.outputTokens ?? 0), 0);
  const caseScores = scores.map((score) => ({
    caseId: score.caseId,
    title: score.title,
    family: score.family,
    pages: pagesByCaseId.get(score.caseId) ?? 1,
    score: score.score,
    uncappedScore: score.uncappedScore,
    accuracy: score.dimensions?.accuracy,
    completeness: score.dimensions?.completeness,
    structure: score.dimensions?.structure,
    markdownQuality: score.dimensions?.markdownQuality,
    rawFactScore: score.factScore?.rawScore,
    appliedCap: score.caps?.appliedCap ?? null,
    missingWeight: score.factScore?.statusWeights?.missing ?? 0,
    incorrectWeight: score.factScore?.statusWeights?.incorrect ?? 0,
    unsupportedPenalty: score.unsupported?.penalty ?? 0,
    elapsedMs: score.elapsedMs,
    costUsd: round(score.estimatedCostUsd, 6),
    outputTokens: score.usage?.outputTokens ?? 0,
  }));

  const summary = {
    modelId,
    caseCount: scores.length,
    expectedCaseCount: expectedCaseIds.length,
    complete: missingCaseIds.length === 0,
    missingCaseIds,
    score: round(weightedMean(scores.map((score) => ({ value: score.score, weight: pagesByCaseId.get(score.caseId) ?? 1 })))),
    scoreCaseMean: round(mean(scores.map((score) => score.score))),
    scoreAggregation: "page_weighted",
    costUsd: round(totalCostUsd, 6),
    totalElapsedMs,
    totalInputTokens,
    totalOutputTokens,
    failureRate: scores.length === 0 ? 0 : round((failed.length / scores.length) * 100),
    caseScores,
  };

  await writeFile(path.join(runRoot, "summary.json"), JSON.stringify(summary, null, 2) + "\n", "utf-8");
  return summary;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const modelId = process.argv[2] ?? "vertex-gemini-3.1-flash-lite";
  console.log(JSON.stringify(await summarizeModel(modelId), null, 2));
}
