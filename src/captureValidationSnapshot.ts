import { execFileSync } from "node:child_process";
import { mkdir, readFile, readdir } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { benchmarkModelIds } from "./run.js";
import { sha256Bytes } from "./cache.js";
import { loadBenchmarkManifest } from "./manifest.js";
import { atomicWriteJson } from "./runRuntime.js";

type SnapshotOptions = {
  sample: string;
  outPath: string;
  capturedAt?: string;
};

function mean(values: number[]) {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

async function readJson(filePath: string) {
  return JSON.parse(await readFile(filePath, "utf-8")) as any;
}

async function artifactRecord(filePath: string) {
  const contents = await readFile(filePath);
  return {
    path: filePath,
    sha256: sha256Bytes(contents),
    bytes: contents.byteLength,
  };
}

export async function captureValidationSnapshot(options: SnapshotOptions) {
  if (!/^\d{3}$/.test(options.sample)) {
    throw new Error(`Invalid sample ${JSON.stringify(options.sample)}; expected a three-digit slot.`);
  }

  const manifestPath = "benchmark/manifest.json";
  const manifest = (await loadBenchmarkManifest(manifestPath)).manifest as {
    name: string;
    suite?: string;
    cases: Array<{ id: string; title: string }>;
  };
  const sourceGitCommit = execFileSync("git", ["rev-parse", "HEAD"], { encoding: "utf-8" }).trim();
  const sourceGitStatus = execFileSync("git", ["status", "--short"], { encoding: "utf-8" }).trim();
  const models = [];

  for (const modelId of benchmarkModelIds) {
    const summaryPath = path.join("runs", modelId, "summary.official.json");
    const summary = await readJson(summaryPath);
    const cases = [];

    for (const testCase of manifest.cases) {
      const sampleDirectory = path.join("runs", modelId, testCase.id, "samples", options.sample);
      const resultPath = path.join(sampleDirectory, "result.json");
      const predictionPath = path.join(sampleDirectory, "prediction.md");
      const scorePath = path.join(sampleDirectory, "score.json");
      const attemptsDirectory = path.join(sampleDirectory, "attempts");
      const attemptFiles = (await readdir(attemptsDirectory))
        .filter((name) => name.endsWith(".json"))
        .sort()
        .map((name) => path.join(attemptsDirectory, name));
      const [result, score, resultArtifact, predictionArtifact, scoreArtifact, attemptArtifacts] = await Promise.all([
        readJson(resultPath),
        readJson(scorePath),
        artifactRecord(resultPath),
        artifactRecord(predictionPath),
        artifactRecord(scorePath),
        Promise.all(attemptFiles.map(artifactRecord)),
      ]);

      if (result.sample !== options.sample || score.sample !== options.sample) {
        throw new Error(`${modelId} ${testCase.id} does not contain sample ${options.sample}.`);
      }
      if (!Number.isFinite(score.score) || score.valid !== true) {
        throw new Error(`${modelId} ${testCase.id}#${options.sample} does not have a valid finite score.`);
      }

      cases.push({
        caseId: testCase.id,
        title: testCase.title,
        sample: options.sample,
        score: score.score,
        inference: {
          estimatedCostUsd: result.estimatedCostUsd,
          elapsedMs: result.elapsedMs,
          finishReason: result.finishReason,
          outputLength: result.outputLength,
          usage: result.usage,
          logicalGenerationCalls: result.inferenceAttempt?.logicalGenerationCalls,
          transportRequestAttempts: result.inferenceAttempt?.transportRequestAttempts,
          runMode: result.executionProvenance?.runMode,
          authorizationHash: result.executionProvenance?.authorizationHash,
          runKey: result.cache?.runKey,
          predictionHash: result.cache?.predictionHash,
        },
        evaluator: {
          status: score.scorer?.status,
          estimatedCostUsd: score.scorer?.estimatedCostUsd,
          elapsedMs: score.scorer?.elapsedMs,
          attempts: score.scorer?.attempts,
          usage: score.scorer?.usage,
          judgeReused: score.scorer?.judgeReused,
          scoreKey: score.scorer?.cache?.scoreKey,
          judgeKey: score.scorer?.cache?.judgeKey,
        },
        artifacts: {
          result: resultArtifact,
          prediction: predictionArtifact,
          score: scoreArtifact,
          attempts: attemptArtifacts,
        },
      });
    }

    const exactSuiteScore = mean(cases.map((testCase) => testCase.score));
    const inferenceCostUsd = cases.reduce((sum, testCase) => sum + testCase.inference.estimatedCostUsd, 0);
    const evaluatorCostUsd = cases.reduce((sum, testCase) => sum + testCase.evaluator.estimatedCostUsd, 0);
    if (options.sample === "001" && Math.abs(exactSuiteScore - summary.suiteSampleScores[0].score) > 5e-7) {
      throw new Error(`${modelId} exact suite score does not match the official summary.`);
    }

    models.push({
      modelId,
      sample: options.sample,
      exactSuiteScore,
      displayedSuiteScore: Math.round(exactSuiteScore * 10) / 10,
      inferenceCostUsd,
      evaluatorCostUsd,
      totalMeasuredCostUsd: inferenceCostUsd + evaluatorCostUsd,
      fingerprints: {
        benchmark: summary.benchmarkFingerprint,
        inferenceBenchmark: summary.inferenceBenchmarkFingerprint,
        inferenceProtocol: summary.inferenceProtocolFingerprint,
        scoringContract: summary.scoringContractFingerprint,
        modelConfig: summary.modelConfigFingerprint,
        pricing: summary.pricingFingerprint,
        cohortArtifact: summary.cohortArtifactFingerprint,
      },
      summaryArtifact: await artifactRecord(summaryPath),
      officialSummaryAtCapture: summary,
      cases,
    });
  }

  const snapshot = {
    schemaVersion: 1,
    kind: "doc2md_anchor_validation_draw_snapshot",
    capturedAt: options.capturedAt ?? new Date().toISOString(),
    sourceGitCommit,
    sourceWorktreeWasClean: sourceGitStatus.length === 0,
    sourceWorktreeStatus: sourceGitStatus,
    benchmark: {
      name: manifest.name,
      suite: manifest.suite ?? "official",
      manifestPath,
      caseCount: manifest.cases.length,
      sample: options.sample,
      modelIds: [...benchmarkModelIds],
    },
    comparison: {
      exactScoreGap: models[1]!.exactSuiteScore - models[0]!.exactSuiteScore,
      displayedScoreGap: models[1]!.displayedSuiteScore - models[0]!.displayedSuiteScore,
      inferenceCostUsd: models.reduce((sum, model) => sum + model.inferenceCostUsd, 0),
      evaluatorCostUsd: models.reduce((sum, model) => sum + model.evaluatorCostUsd, 0),
      totalMeasuredCostUsd: models.reduce((sum, model) => sum + model.totalMeasuredCostUsd, 0),
    },
    models,
  };

  await mkdir(path.dirname(options.outPath), { recursive: true });
  await atomicWriteJson(options.outPath, snapshot);
  return snapshot;
}

function parseCli(argv: string[]): SnapshotOptions {
  let sample = "001";
  let outPath = "docs/results/anchor-repeat-validation-2026-07-10/draw-001.snapshot.json";
  const seen = new Set<string>();
  for (let index = 0; index < argv.length; index += 1) {
    const key = argv[index];
    if (key !== "--sample" && key !== "--out") throw new Error(`Unknown option ${key}.`);
    if (seen.has(key)) throw new Error(`Duplicate option ${key}.`);
    seen.add(key);
    const value = argv[index + 1];
    if (!value || value.startsWith("--")) throw new Error(`${key} requires a value.`);
    if (key === "--sample") sample = value;
    else outPath = value;
    index += 1;
  }
  return { sample, outPath };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const snapshot = await captureValidationSnapshot(parseCli(process.argv.slice(2)));
  console.log(
    `Captured ${snapshot.models.length} model(s) / ${snapshot.benchmark.caseCount} cases to ` +
      `${parseCli(process.argv.slice(2)).outPath}.`,
  );
}
