import { runJobsInParallel } from "./concurrency.js";
import { loadBenchmarkManifest } from "./manifest.js";
import { runModel } from "./run.js";
import { scoreModel } from "./score.js";

export type ModelPipelineOptions = {
  manifestPath?: string;
  sampleIds?: string[];
  finalValidationAuthorization?: string;
  repeatValidationAuthorization?: string;
};

/**
 * Run every case as an independent inference -> evaluation pipeline. All case
 * pipelines for one model start together, while the caller controls whether
 * different models are processed serially or concurrently.
 */
export async function runModelCasePipelines(modelId: string, options: ModelPipelineOptions = {}) {
  const manifestPath = options.manifestPath ?? "benchmark/manifest.json";
  const manifest = (await loadBenchmarkManifest(manifestPath)).manifest as { cases: Array<{ id: string }> };
  return runJobsInParallel(
    manifest.cases.map((testCase) => async () => {
      await runModel(modelId, {
        caseId: testCase.id,
        manifestPath,
        skipPreflight: true,
        finalValidationAuthorization: options.finalValidationAuthorization,
        sampleIds: options.sampleIds,
        repeatValidationAuthorization: options.repeatValidationAuthorization,
      });
      return scoreModel(modelId, {
        caseId: testCase.id,
        manifestPath,
        skipPreflight: true,
        sampleIds: options.sampleIds,
      });
    }),
  );
}
