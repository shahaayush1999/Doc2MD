import { benchmarkModelIds, runModel } from "./run.js";
import { scoreModel } from "./score.js";
import { summarizeModel } from "./summary.js";

function parseArgs() {
  const args = new Set(process.argv.slice(2));
  const unknown = [...args].filter((arg) => arg !== "--force");
  if (unknown.length > 0) throw new Error(`Unknown argument(s): ${unknown.join(", ")}`);
  return { force: args.has("--force") };
}

const options = parseArgs();

console.log(`Running official Doc2MD native-PDF benchmark:
1. model inference for every selected model/case in parallel
2. evaluator scoring with structured Zod output in parallel per model
3. deterministic summary aggregation

Unchanged model/case runs and scores are skipped automatically. Use --force to overwrite cached runs.
Models: ${benchmarkModelIds.join(", ")}`);

const summaries = await Promise.all(benchmarkModelIds.map(async (modelId) => {
  await runModel(modelId, { force: options.force });
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
