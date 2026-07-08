import { access, readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildRunContext, models, runCacheKey } from "./run.js";

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
  const existing = new Set((await exists(runRoot)) ? await readdir(runRoot) : []);
  const caseScores = [];

  for (const testCase of manifest.cases) {
    if (!existing.has(testCase.id)) continue;
    const activeRun = await runCacheKey(testCase as any, spec, context);
    const score = (await readJsonIfExists(path.join(runRoot, testCase.id, "score.json"))) as Score | null;
    if (!score || score.runCache?.runKey !== activeRun.runKey) continue;
    caseScores.push({
      caseId: testCase.id,
      title: score.title ?? testCase.title,
      family: score.family ?? testCase.family,
      tags: testCase.tags ?? score.tags ?? [],
      pages: testCase.pages ?? 1,
      score: score.score,
      uncappedScore: score.uncappedScore ?? score.score,
      accuracy: score.dimensions?.accuracy ?? 0,
      completeness: score.dimensions?.completeness ?? 0,
      structure: score.dimensions?.structure ?? 0,
      markdownQuality: score.dimensions?.markdownQuality ?? 0,
      rawFactScore: score.factScore?.rawScore ?? null,
      appliedCap: score.caps?.appliedCap ?? null,
      missingWeight: score.factScore?.statusWeights?.missing ?? 0,
      incorrectWeight: score.factScore?.statusWeights?.incorrect ?? 0,
      unsupportedPenalty: score.unsupported?.penalty ?? 0,
      elapsedMs: score.elapsedMs,
      costUsd: score.estimatedCostUsd,
      inputTokens: score.usage?.inputTokens ?? 0,
      outputTokens: score.usage?.outputTokens ?? 0,
      finishReason: score.finishReason,
      error: score.error,
    });
  }

  caseScores.sort((a, b) => a.caseId.localeCompare(b.caseId));
  const scoredCaseIds = new Set(caseScores.map((score) => score.caseId));
  const missingCaseIds = manifest.cases.map((testCase) => testCase.id).filter((caseId) => !scoredCaseIds.has(caseId));
  const failed = caseScores.filter((score) => score.error || score.finishReason === "error");
  const totalCostUsd = caseScores.reduce((sum, score) => sum + score.costUsd, 0);
  const totalElapsedMs = caseScores.reduce((sum, score) => sum + score.elapsedMs, 0);
  const totalInputTokens = caseScores.reduce((sum, score) => sum + score.inputTokens, 0);
  const totalOutputTokens = caseScores.reduce((sum, score) => sum + score.outputTokens, 0);

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
    score: round(weightedMean(caseScores.map((score) => ({ value: score.score, weight: score.pages })))),
    scoreCaseMean: round(mean(caseScores.map((score) => score.score))),
    scoreAggregation: "page_weighted_case_scores",
    costUsd: round(totalCostUsd, 6),
    meanCostUsdPerCase: round(mean(caseScores.map((score) => score.costUsd)), 6),
    totalElapsedMs,
    meanElapsedMsPerCase: Math.round(mean(caseScores.map((score) => score.elapsedMs))),
    totalInputTokens,
    totalOutputTokens,
    meanOutputTokensPerCase: Math.round(mean(caseScores.map((score) => score.outputTokens))),
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
