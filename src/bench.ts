import { benchmarkModelIds, runModel } from "./run.js";
import { scoreModel } from "./score.js";
import { summarizeModel } from "./summary.js";

console.log(`Running full Doc2MD benchmark:
1. model inference for every selected model/case in parallel
2. evaluator scoring with structured Zod output in parallel per model
3. deterministic summary aggregation

Unchanged model/case runs and scores are skipped automatically.
Models: ${benchmarkModelIds.join(", ")}`);

const summaries = await Promise.all(benchmarkModelIds.map(async (modelId) => {
  await runModel(modelId);
  await scoreModel(modelId);
  return summarizeModel(modelId);
}));

console.log("Final summaries:");
console.table(
  summaries.map((summary) => ({
    model: summary.modelId,
    score: summary.score,
    cost: summary.costUsd,
    ms: summary.totalElapsedMs,
    outputTokens: summary.totalOutputTokens,
    failures: summary.failureRate,
    complete: summary.complete,
  })),
);
console.log(JSON.stringify(summaries, null, 2));
