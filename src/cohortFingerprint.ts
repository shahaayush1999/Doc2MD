import { access } from "node:fs/promises";
import path from "node:path";
import { fileSha256, hashObject } from "./cache.js";

type CohortCase = { id: string };

async function hashIfPresent(filePath: string) {
  try {
    await access(filePath);
    return await fileSha256(filePath);
  } catch {
    return null;
  }
}

export async function buildCohortArtifactFingerprint(
  modelId: string,
  suite: string,
  cases: CohortCase[],
  samplesPerCase: number,
  runRoot = "runs",
) {
  const entries = [];
  for (const testCase of cases) {
    for (let index = 1; index <= samplesPerCase; index += 1) {
      const sample = String(index).padStart(3, "0");
      const sampleDir = path.join(runRoot, modelId, testCase.id, "samples", sample);
      const [predictionArtifactHash, runArtifactHash, scoreArtifactHash] = await Promise.all([
        hashIfPresent(path.join(sampleDir, "prediction.md")),
        hashIfPresent(path.join(sampleDir, "result.json")),
        hashIfPresent(path.join(sampleDir, "score.json")),
      ]);
      entries.push({ caseId: testCase.id, sample, predictionArtifactHash, runArtifactHash, scoreArtifactHash });
    }
  }
  return hashObject({ schemaVersion: 1, modelId, suite, samplesPerCase, entries });
}
