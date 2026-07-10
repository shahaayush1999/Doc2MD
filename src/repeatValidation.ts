import { fileURLToPath } from "node:url";
import { captureValidationSnapshot } from "./captureValidationSnapshot.js";
import { preflightBenchmark } from "./preflight.js";
import { benchmarkModelIds, runModel } from "./run.js";
import { acquireSampleLock } from "./runRuntime.js";
import { scoreModel } from "./score.js";

const repeatSample = "002";
const snapshotPath = "docs/results/anchor-repeat-validation-2026-07-10/draw-002.snapshot.json";

function parseCli(argv: string[]) {
  if (argv.length !== 2 || argv[0] !== "--authorization" || !argv[1]) {
    throw new Error("Usage: npm run repeat:anchors -- --authorization repeat-validation:<checkpoint-id>");
  }
  return { authorization: argv[1] };
}

export async function runAnchorRepeatValidation(authorization: string) {
  const preflight = await preflightBenchmark();
  console.log(`Preflight passed: ${preflight.caseCount} cases / ${preflight.pageCount} pages.`);
  const lock = await acquireSampleLock("runs/.anchor-repeat-validation-002.lock", { staleAfterMs: 24 * 60 * 60 * 1000 });
  try {
    for (const modelId of benchmarkModelIds) {
      await runModel(modelId, {
        skipPreflight: true,
        sampleIds: [repeatSample],
        repeatValidationAuthorization: authorization,
      });
      await scoreModel(modelId, { skipPreflight: true, sampleIds: [repeatSample] });
    }
    const snapshot = await captureValidationSnapshot({ sample: repeatSample, outPath: snapshotPath });
    console.log("Repeat-validation draw captured:");
    console.table(
      snapshot.models.map((model) => ({
        model: model.modelId,
        score: model.displayedSuiteScore,
        inferenceCostUsd: model.inferenceCostUsd,
        evaluatorCostUsd: model.evaluatorCostUsd,
        totalMeasuredCostUsd: model.totalMeasuredCostUsd,
      })),
    );
    console.log(`Snapshot written to ${snapshotPath}`);
    return snapshot;
  } finally {
    await lock.release();
  }
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const { authorization } = parseCli(process.argv.slice(2));
  const keepAlive = setInterval(() => undefined, 1_000);
  try {
    await runAnchorRepeatValidation(authorization);
  } finally {
    clearInterval(keepAlive);
  }
}
