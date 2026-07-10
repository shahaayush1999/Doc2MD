import { benchmarkModelIds, models, runModel } from "./run.js";
import { scoreModel } from "./score.js";
import { summarizeModel } from "./summary.js";
import { generateReport } from "./report.js";
import { preflightBenchmark } from "./preflight.js";
import { acquireSampleLock } from "./runRuntime.js";

function parseArgs() {
  let force = false;
  const selectedModels: string[] = [];
  for (let index = 2; index < process.argv.length; index += 1) {
    const argument = process.argv[index]!;
    if (argument === "--force") {
      if (force) throw new Error("Duplicate --force option.");
      force = true;
      continue;
    }
    if (argument === "--model") {
      const value = process.argv[index + 1];
      if (!value || value.startsWith("--")) throw new Error("--model requires a model id.");
      if (selectedModels.includes(value)) throw new Error(`Duplicate model ${value}.`);
      if (!models[value]) throw new Error(`Unknown model ${value}. Options: ${Object.keys(models).join(", ")}`);
      selectedModels.push(value);
      index += 1;
      continue;
    }
    throw new Error(`Unknown argument ${argument}. Use --model MODEL_ID (repeatable) and optional --force.`);
  }
  return { force, modelIds: selectedModels.length > 0 ? selectedModels : [...benchmarkModelIds] };
}

const options = parseArgs();

const preflight = await preflightBenchmark();
console.log(`Preflight passed: ${preflight.caseCount} cases / ${preflight.pageCount} pages.`);
const benchmarkLock = await acquireSampleLock("runs/.bench.lock", { staleAfterMs: 24 * 60 * 60 * 1000 });

try {
  console.log(`Running official Doc2MD native-PDF benchmark:
1. model inference for three samples of every selected model/case in parallel
2. evaluator scoring with structured Zod output in parallel per model
3. deterministic, equal-case aggregation across complete sample slots

Unchanged model/case runs and scores are skipped automatically. Use --force to overwrite cached runs.
Models: ${options.modelIds.join(", ")}`);

  const summaries = [];
  for (const modelId of options.modelIds) {
    await runModel(modelId, { force: options.force, skipPreflight: true });
    await scoreModel(modelId, { skipPreflight: true });
    summaries.push(await summarizeModel(modelId));
  }
  const report = await generateReport(summaries);

  console.log("Final summaries:");
  console.table(
    summaries.map((summary) => ({
      model: summary.modelId,
      score: summary.score,
      fullSuiteStddev: summary.scoreStddev,
      fullSuiteMin: summary.scoreMin,
      fullSuiteMax: summary.scoreMax,
      samples: summary.sampleCount,
      estimatedInferenceCostUsd: summary.costUsd,
      summedModelCallMs: summary.totalElapsedMs,
      inferenceOutputTokens: summary.totalOutputTokens,
      modelFailures: summary.modelFailureCount,
      evaluatorFailures: summary.evaluatorFailureCount,
      complete: summary.complete,
    })),
  );
  console.log(JSON.stringify(summaries, null, 2));
  console.log(`Report written to ${report.outPath}`);
} finally {
  await benchmarkLock.release();
}
