import { createHash } from "node:crypto";
import { readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parseFactFile, type ManifestCase } from "./evaluator.js";
import { loadBenchmarkManifest } from "./manifest.js";
import { applyManualCorrections, readManualCorrections } from "./manual-corrections.js";

const reportedStale = new Set<string>();

/** Overlay reviewed decisions without calling a judge or changing other saved decisions. */
export async function correctedEvaluation(directory: string, testCase: ManifestCase, prediction: string, evaluation: any) {
  const correctionsPath = path.join(directory, "corrections.json");
  const corrections = await readManualCorrections(correctionsPath);
  if (!corrections || evaluation?.valid !== true) return evaluation;
  if (createHash("sha256").update(prediction).digest("hex") !== corrections.predictionHash) {
    if (!reportedStale.has(correctionsPath)) {
      reportedStale.add(correctionsPath);
      console.warn(`${correctionsPath}: belongs to an older prediction; skipped. Review it before applying to the new output.`);
    }
    return evaluation;
  }
  if (!testCase.facts) throw new Error(`${testCase.id} has no facts file.`);
  const facts = parseFactFile(JSON.parse(await readFile(testCase.facts, "utf8")), { caseId: testCase.id, pages: testCase.pages });
  return applyManualCorrections(facts, prediction, evaluation, corrections);
}

/** Persist hand-edited correction files to existing scores, entirely offline. */
export async function applySavedCorrections() {
  const { manifest } = await loadBenchmarkManifest();
  const root = "runs/cache";
  const paths = await readdir(root, { recursive: true }).catch((error) => {
    if (error.code === "ENOENT") return [] as string[];
    throw error;
  });
  let updated = 0;
  for (const relative of paths.filter((entry) => path.basename(entry) === "corrections.json")) {
    const testCase = manifest.cases.find((item) => item.id === relative.split(path.sep)[1]);
    if (!testCase) continue;
    const directory = path.join(root, path.dirname(relative));
    const scorePath = path.join(directory, "score.json");
    const prediction = await readFile(path.join(directory, "prediction.md"), "utf8");
    const evaluation = JSON.parse(await readFile(scorePath, "utf8"));
    const corrected = await correctedEvaluation(directory, testCase, prediction, evaluation);
    if (JSON.stringify(corrected) !== JSON.stringify(evaluation)) {
      await writeFile(scorePath, JSON.stringify(corrected, null, 2) + "\n");
      updated += 1;
      console.log(`${directory}: ${evaluation.score.toFixed(1)} → ${corrected.score.toFixed(1)}`);
    }
  }
  console.log(`Applied saved corrections to ${updated} score file(s), without API calls. Run npm run report to refresh the report.`);
  return updated;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  if (process.argv.length !== 2) throw new Error("Usage: npm run corrections");
  await applySavedCorrections();
}
