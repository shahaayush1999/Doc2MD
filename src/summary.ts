import { readFile, readdir } from "node:fs/promises";
import path from "node:path";

type ScoreFile = {
  caseId: string;
  modelId: string;
  percentage: number;
  estimatedCostUsd: number;
  elapsedMs: number;
  usage: {
    inputTokens: number;
    outputTokens: number;
    totalTokens: number;
  };
};

type Aggregate = {
  modelId: string;
  cases: number;
  averageScore: number;
  totalCostUsd: number;
  totalElapsedMs: number;
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
};

const runsRoot = path.join("experiments", "runs");
const caseIds = await readdir(runsRoot);
const byModel = new Map<string, Aggregate>();

for (const caseId of caseIds) {
  const caseDir = path.join(runsRoot, caseId);
  const modelIds = await readdir(caseDir);
  for (const modelId of modelIds) {
    const scorePath = path.join(caseDir, modelId, "score.json");
    let score: ScoreFile;
    try {
      score = JSON.parse(await readFile(scorePath, "utf-8")) as ScoreFile;
    } catch {
      continue;
    }

    const aggregate =
      byModel.get(modelId) ??
      ({
        modelId,
        cases: 0,
        averageScore: 0,
        totalCostUsd: 0,
        totalElapsedMs: 0,
        inputTokens: 0,
        outputTokens: 0,
        totalTokens: 0,
      } satisfies Aggregate);

    aggregate.cases += 1;
    aggregate.averageScore += score.percentage;
    aggregate.totalCostUsd += score.estimatedCostUsd;
    aggregate.totalElapsedMs += score.elapsedMs;
    aggregate.inputTokens += score.usage.inputTokens;
    aggregate.outputTokens += score.usage.outputTokens;
    aggregate.totalTokens += score.usage.totalTokens;
    byModel.set(modelId, aggregate);
  }
}

const rows = [...byModel.values()]
  .map((row) => ({
    ...row,
    averageScore: row.cases === 0 ? 0 : row.averageScore / row.cases,
  }))
  .sort((a, b) => b.averageScore - a.averageScore || a.totalCostUsd - b.totalCostUsd);

console.table(
  rows.map((row) => ({
    model: row.modelId,
    cases: row.cases,
    avg_pct: Number(row.averageScore.toFixed(1)),
    total_cost_usd: Number(row.totalCostUsd.toFixed(8)),
    total_elapsed_ms: row.totalElapsedMs,
    input_tokens: row.inputTokens,
    output_tokens: row.outputTokens,
    total_tokens: row.totalTokens,
  })),
);
