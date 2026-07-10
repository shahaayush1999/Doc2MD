import { fileURLToPath } from "node:url";
import { benchmarkModelIds, models, runModel } from "./run.js";
import { scoreModel } from "./score.js";
import { summarizeModel } from "./summary.js";
import { generateReport } from "./report.js";
import { preflightBenchmark } from "./preflight.js";
import { acquireSampleLock } from "./runRuntime.js";

export type BenchCliArgs = {
  modelIds: string[];
  finalValidationAuthorization?: string;
};

export function parseBenchCliArgs(argv: string[]): BenchCliArgs {
  const selectedModels: string[] = [];
  let finalValidationAuthorization: string | undefined;
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index]!;
    if (argument === "--force") {
      throw new Error(
        "--force is disabled: a current stochastic draw cannot be silently replaced. Repeated validation requires a separately authorized protocol.",
      );
    }
    if (argument === "--model") {
      const value = argv[index + 1];
      if (!value || value.startsWith("--")) throw new Error("--model requires a model id.");
      if (selectedModels.includes(value)) throw new Error(`Duplicate model ${value}.`);
      if (!models[value]) throw new Error(`Unknown model ${value}. Options: ${Object.keys(models).join(", ")}`);
      selectedModels.push(value);
      index += 1;
      continue;
    }
    if (argument === "--final-validation-authorization") {
      const value = argv[index + 1];
      if (!value || value.startsWith("--")) throw new Error("--final-validation-authorization requires a checkpoint id.");
      if (finalValidationAuthorization !== undefined) throw new Error("Duplicate --final-validation-authorization option.");
      finalValidationAuthorization = value;
      index += 1;
      continue;
    }
    throw new Error(
      `Unknown argument ${argument}. Use --model MODEL_ID (repeatable) and, only for an approved non-anchor checkpoint, ` +
        "--final-validation-authorization ID.",
    );
  }
  return {
    modelIds: selectedModels.length > 0 ? selectedModels : [...benchmarkModelIds],
    ...(finalValidationAuthorization === undefined ? {} : { finalValidationAuthorization }),
  };
}

export async function runBenchmark(options: BenchCliArgs) {
  const preflight = await preflightBenchmark();
  console.log(`Preflight passed: ${preflight.caseCount} cases / ${preflight.pageCount} pages.`);
  const benchmarkLock = await acquireSampleLock("runs/.bench.lock", { staleAfterMs: 24 * 60 * 60 * 1000 });

  try {
    console.log(`Running official Doc2MD native-PDF benchmark:
1. model inference for one stochastic sample of every selected model/case in parallel
2. evaluator scoring with structured Zod output in parallel per model
3. deterministic, equal-case aggregation across the complete single-draw cohort

Unchanged model/case runs and scores are skipped automatically. An immutable attempt marker prevents silent redraws.
Transport retries, when needed, remain part of the same logical stochastic sample and are recorded separately.
Models: ${options.modelIds.join(", ")}`);

    const summaries = [];
    for (const modelId of options.modelIds) {
      await runModel(modelId, {
        skipPreflight: true,
        finalValidationAuthorization: options.finalValidationAuthorization,
      });
      await scoreModel(modelId, { skipPreflight: true });
      summaries.push(await summarizeModel(modelId));
    }

    const selectedOnlyDevelopmentAnchors = options.modelIds.every((modelId) =>
      (benchmarkModelIds as readonly string[]).includes(modelId),
    );
    // A one-anchor debugging run reloads all current anchor summaries, so the
    // second separate anchor run produces the combined comparison report.
    const report = selectedOnlyDevelopmentAnchors ? await generateReport() : await generateReport(summaries);

    console.log("Processed model summaries:");
    console.table(
      summaries.map((summary) => ({
        model: summary.modelId,
        score: summary.score,
        observedVariability: summary.scoreStddev === null ? "N/A (one sample)" : Number(summary.scoreStddev.toFixed(1)),
        samples: summary.sampleCount,
        logicalGenerationCalls: summary.modelCallCount,
        transportRequestAttempts: summary.totalTransportRequestAttempts,
        estimatedInferenceCostUsd: summary.costUsd,
        summedModelCallMs: summary.totalElapsedMs,
        inferenceOutputTokens: summary.totalOutputTokens,
        modelFailures: summary.modelFailureCount,
        evaluatorFailures: summary.evaluatorFailureCount,
        complete: summary.complete,
      })),
    );
    console.log("Detailed machine-audit summaries remain in runs/<model>/summary.official.json.");
    console.log(`Report written to ${report.outPath}`);
    return { summaries, report };
  } finally {
    await benchmarkLock.release();
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const keepAlive = setInterval(() => undefined, 1_000);
  try {
    await runBenchmark(parseBenchCliArgs(process.argv.slice(2)));
  } finally {
    clearInterval(keepAlive);
  }
}
