import { access, readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildRunContext, models, runCacheKey, samplesPerModelCase } from "./run.js";

type Score = {
  caseId: string;
  title?: string;
  family?: string;
  tags?: string[];
  score: number;
  uncappedScore?: number;
  dimensions?: {
    accuracy?: number;
    completeness?: number;
    structure?: number;
    markdownQuality?: number;
  };
  factScore?: {
    rawScore?: number | null;
    statusWeights?: Record<string, number>;
  };
  caps?: {
    appliedCap?: number | null;
  };
  unsupported?: {
    penalty?: number;
  };
  estimatedCostUsd: number;
  elapsedMs: number;
  usage: { inputTokens?: number; outputTokens?: number; totalTokens?: number } | null;
  finishReason: string;
  sample?: string | null;
  runCache?: { runKey?: string };
  error?: string;
};

type ManifestCase = {
  id: string;
  title?: string;
  family?: string;
  tags?: string[];
  pages?: number;
  pdf: string;
};

function mean(values: number[]) {
  return values.length === 0 ? 0 : values.reduce((sum, value) => sum + value, 0) / values.length;
}

function stddev(values: number[]) {
  if (values.length <= 1) return 0;
  const avg = mean(values);
  return Math.sqrt(mean(values.map((value) => (value - avg) ** 2)));
}

function weightedMean(values: Array<{ value: number; weight: number }>) {
  const totalWeight = values.reduce((sum, item) => sum + item.weight, 0);
  if (totalWeight === 0) return 0;
  return values.reduce((sum, item) => sum + item.value * item.weight, 0) / totalWeight;
}

function round(value: number, digits = 1) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

async function exists(filePath: string) {
  try {
    await access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function readJsonIfExists(filePath: string) {
  if (!(await exists(filePath))) return null;
  return JSON.parse(await readFile(filePath, "utf-8")) as any;
}

function parseArgs() {
  const args = new Map<string, string>();
  const positionals: string[] = [];
  for (let i = 2; i < process.argv.length; i += 1) {
    const arg = process.argv[i];
    if (arg.startsWith("--")) {
      const key = arg.slice(2);
      const next = process.argv[i + 1];
      args.set(key, next && !next.startsWith("--") ? process.argv[++i] : "true");
    } else {
      positionals.push(arg);
    }
  }
  return { args, positionals };
}

function rejectUnknownArgs(args: Map<string, string>, allowed: string[]) {
  const allowedSet = new Set(allowed);
  const unknown = [...args.keys()].filter((key) => !allowedSet.has(key));
  if (unknown.length > 0) throw new Error(`Unknown argument(s): ${unknown.map((key) => `--${key}`).join(", ")}`);
}

export async function summarizeModel(modelId: string, options: { manifestPath?: string } = {}) {
  const runRoot = path.join("runs", modelId);
  const manifestPath = options.manifestPath ?? "benchmark/manifest.json";
  const manifest = JSON.parse(await readFile(manifestPath, "utf-8")) as {
    name?: string;
    suite?: string;
    scoreName?: string;
    inputProtocol?: string;
    cases: ManifestCase[];
  };
  const spec = models[modelId];
  if (!spec) throw new Error(`Unknown model ${modelId}. Options: ${Object.keys(models).join(", ")}`);
  const context = await buildRunContext(spec, manifest as any, manifestPath);
  const suite = manifest.suite ?? "official";
  const caseScores = [];

  for (const testCase of manifest.cases) {
    const activeRun = await runCacheKey(testCase as any, spec, context);
    const samples: Score[] = [];
    for (let index = 1; index <= samplesPerModelCase; index += 1) {
      const sample = String(index).padStart(3, "0");
      const score = (await readJsonIfExists(path.join(runRoot, testCase.id, "samples", sample, "score.json"))) as Score | null;
      if (score?.runCache?.runKey === activeRun.runKey) samples.push(score);
    }
    if (samples.length === 0) continue;

    const latest = samples.at(-1)!;
    const scores = samples.map((score) => score.score);
    caseScores.push({
      caseId: testCase.id,
      title: latest.title ?? testCase.title,
      family: latest.family ?? testCase.family,
      tags: testCase.tags ?? latest.tags ?? [],
      pages: testCase.pages ?? 1,
      samples: samples.length,
      score: round(mean(scores)),
      scoreMin: round(Math.min(...scores)),
      scoreMax: round(Math.max(...scores)),
      scoreStddev: round(stddev(scores), 2),
      sampleScores: samples.map((score) => ({ sample: score.sample, score: score.score })),
      uncappedScore: round(mean(samples.map((score) => score.uncappedScore ?? score.score))),
      accuracy: round(mean(samples.map((score) => score.dimensions?.accuracy ?? 0))),
      completeness: round(mean(samples.map((score) => score.dimensions?.completeness ?? 0))),
      structure: round(mean(samples.map((score) => score.dimensions?.structure ?? 0))),
      markdownQuality: round(mean(samples.map((score) => score.dimensions?.markdownQuality ?? 0))),
      rawFactScore: round(mean(samples.map((score) => score.factScore?.rawScore ?? 0))),
      appliedCap: latest.caps?.appliedCap ?? null,
      missingWeight: round(mean(samples.map((score) => score.factScore?.statusWeights?.missing ?? 0))),
      incorrectWeight: round(mean(samples.map((score) => score.factScore?.statusWeights?.incorrect ?? 0))),
      unsupportedPenalty: round(mean(samples.map((score) => score.unsupported?.penalty ?? 0))),
      elapsedMs: Math.round(mean(samples.map((score) => score.elapsedMs))),
      costUsd: round(mean(samples.map((score) => score.estimatedCostUsd)), 6),
      inputTokens: Math.round(mean(samples.map((score) => score.usage?.inputTokens ?? 0))),
      outputTokens: Math.round(mean(samples.map((score) => score.usage?.outputTokens ?? 0))),
      finishReason: latest.finishReason,
      error: latest.error,
    });
  }

  caseScores.sort((a, b) => a.caseId.localeCompare(b.caseId));
  const scoredCaseIds = new Set(caseScores.map((score) => score.caseId));
  const missingCaseIds = manifest.cases.map((testCase) => testCase.id).filter((caseId) => !scoredCaseIds.has(caseId));
  const failed = caseScores.filter((score) => score.error || score.finishReason === "error");
  const totalCostUsd = caseScores.reduce((sum, score) => sum + score.costUsd * score.samples, 0);
  const totalElapsedMs = caseScores.reduce((sum, score) => sum + score.elapsedMs * score.samples, 0);
  const totalInputTokens = caseScores.reduce((sum, score) => sum + score.inputTokens * score.samples, 0);
  const totalOutputTokens = caseScores.reduce((sum, score) => sum + score.outputTokens * score.samples, 0);
  const sampleCount = caseScores.reduce((sum, score) => sum + score.samples, 0);

  const summary = {
    modelId,
    suite,
    manifestPath,
    benchmarkName: manifest.name ?? "Doc2MD",
    scoreName: manifest.scoreName ?? "Doc2MD Native PDF Score",
    inputProtocol: manifest.inputProtocol ?? "native_pdf",
    caseCount: caseScores.length,
    expectedCaseCount: manifest.cases.length,
    complete: missingCaseIds.length === 0,
    missingCaseIds,
    samplesPerModelCase,
    sampleCount,
    score: round(weightedMean(caseScores.map((score) => ({ value: score.score, weight: score.pages })))),
    scoreCaseMean: round(mean(caseScores.map((score) => score.score))),
    scoreStddevCaseMean: round(mean(caseScores.map((score) => score.scoreStddev)), 2),
    scoreAggregation: "page_weighted_case_scores",
    costUsd: round(totalCostUsd, 6),
    meanCostUsdPerSample: sampleCount === 0 ? 0 : round(totalCostUsd / sampleCount, 6),
    totalElapsedMs,
    meanElapsedMsPerSample: sampleCount === 0 ? 0 : Math.round(totalElapsedMs / sampleCount),
    totalInputTokens,
    totalOutputTokens,
    meanOutputTokensPerSample: sampleCount === 0 ? 0 : Math.round(totalOutputTokens / sampleCount),
    failureRate: caseScores.length === 0 ? 0 : round((failed.length / caseScores.length) * 100),
    caseScores,
  };

  const suiteSummaryPath = path.join(runRoot, `summary.${suite}.json`);
  await writeFile(suiteSummaryPath, JSON.stringify(summary, null, 2) + "\n", "utf-8");
  if (suite === "official") {
    await writeFile(path.join(runRoot, "summary.json"), JSON.stringify(summary, null, 2) + "\n", "utf-8");
  }
  return summary;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const { args, positionals } = parseArgs();
  rejectUnknownArgs(args, ["model", "manifest"]);
  const modelId = positionals[0] ?? args.get("model") ?? "vertex-gemini-3.1-flash-lite";
  console.log(JSON.stringify(await summarizeModel(modelId, { manifestPath: args.get("manifest") }), null, 2));
}
