import { access, readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildRunContext, models, runCacheKey } from "./run.js";

type Score = {
  caseId: string;
  title?: string;
  family?: string;
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
    counts?: Record<string, number>;
  };
  estimatedCostUsd: number;
  elapsedMs: number;
  usage: { inputTokens?: number; outputTokens?: number; totalTokens?: number } | null;
  finishReason: string;
  attemptId?: string | null;
  runCache?: { runKey?: string };
  error?: string;
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

async function attemptIds(runDir: string) {
  const root = path.join(runDir, "attempts");
  if (!(await exists(root))) return [];
  return (await readdir(root, { withFileTypes: true }))
    .filter((entry) => entry.isDirectory())
    .map((entry) => entry.name)
    .sort();
}

async function currentScoresForCase(modelId: string, testCase: { id: string; pdf: string }, activeRunKey: string) {
  const runDir = path.join("runs", modelId, testCase.id);
  const scores: Score[] = [];
  for (const attemptId of await attemptIds(runDir)) {
    const scorePath = path.join(runDir, "attempts", attemptId, "score.json");
    const score = (await readJsonIfExists(scorePath)) as Score | null;
    if (score?.runCache?.runKey === activeRunKey) scores.push(score);
  }
  return scores;
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
    cases: Array<{ id: string; pages?: number; pdf: string }>;
  };
  const spec = models[modelId];
  if (!spec) throw new Error(`Unknown model ${modelId}. Options: ${Object.keys(models).join(", ")}`);
  const context = await buildRunContext(spec, manifest as any, manifestPath);
  const suite = manifest.suite ?? "official";
  const manifestCaseIds = new Set(manifest.cases.map((testCase) => testCase.id));
  const pagesByCaseId = new Map(manifest.cases.map((testCase) => [testCase.id, testCase.pages ?? 1]));
  const expectedCaseIds = manifest.cases.map((testCase) => testCase.id);
  const caseIds = (await readdir(runRoot)).filter((name) => manifestCaseIds.has(name));
  const scoresByCaseId = new Map<string, Score[]>();
  for (const testCase of manifest.cases.filter((candidate) => caseIds.includes(candidate.id))) {
    const activeRun = await runCacheKey(testCase as any, spec, context);
    const caseScores = await currentScoresForCase(modelId, testCase, activeRun.runKey);
    if (caseScores.length > 0) scoresByCaseId.set(testCase.id, caseScores);
  }
  const scores = [...scoresByCaseId.values()].flat().sort((a, b) => a.caseId.localeCompare(b.caseId));
  const scoredCaseIds = new Set(scoresByCaseId.keys());
  const missingCaseIds = expectedCaseIds.filter((caseId) => !scoredCaseIds.has(caseId));

  const failed = scores.filter((score) => score.error || score.finishReason === "error");
  const totalCostUsd = scores.reduce((sum, score) => sum + score.estimatedCostUsd, 0);
  const totalElapsedMs = scores.reduce((sum, score) => sum + score.elapsedMs, 0);
  const totalInputTokens = scores.reduce((sum, score) => sum + (score.usage?.inputTokens ?? 0), 0);
  const totalOutputTokens = scores.reduce((sum, score) => sum + (score.usage?.outputTokens ?? 0), 0);
  const caseScores = [...scoresByCaseId.entries()]
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([caseId, attempts]) => {
      const latest = attempts.at(-1)!;
      const values = attempts.map((score) => score.score);
      return {
        caseId,
        title: latest.title,
        family: latest.family,
        pages: pagesByCaseId.get(caseId) ?? 1,
        attempts: attempts.length,
        score: round(mean(values)),
        scoreMin: round(Math.min(...values)),
        scoreMax: round(Math.max(...values)),
        scoreStddev: round(stddev(values), 2),
        latestScore: latest.score,
        uncappedScore: round(mean(attempts.map((score) => score.uncappedScore ?? score.score))),
        accuracy: round(mean(attempts.map((score) => score.dimensions?.accuracy ?? 0))),
        completeness: round(mean(attempts.map((score) => score.dimensions?.completeness ?? 0))),
        structure: round(mean(attempts.map((score) => score.dimensions?.structure ?? 0))),
        markdownQuality: round(mean(attempts.map((score) => score.dimensions?.markdownQuality ?? 0))),
        rawFactScore: round(mean(attempts.map((score) => score.factScore?.rawScore ?? 0))),
        appliedCap: latest.caps?.appliedCap ?? null,
        missingWeight: round(mean(attempts.map((score) => score.factScore?.statusWeights?.missing ?? 0))),
        incorrectWeight: round(mean(attempts.map((score) => score.factScore?.statusWeights?.incorrect ?? 0))),
        unsupportedPenalty: round(mean(attempts.map((score) => score.unsupported?.penalty ?? 0))),
        elapsedMs: Math.round(mean(attempts.map((score) => score.elapsedMs))),
        costUsd: round(mean(attempts.map((score) => score.estimatedCostUsd)), 6),
        outputTokens: Math.round(mean(attempts.map((score) => score.usage?.outputTokens ?? 0))),
        attemptIds: attempts.map((score) => score.attemptId),
      };
    });

  const summary = {
    modelId,
    suite,
    manifestPath,
    benchmarkName: manifest.name ?? "Doc2MD",
    scoreName: manifest.scoreName ?? (suite === "official" ? "Doc2MD Native PDF Score" : "Doc2MD Capability Gate Score"),
    inputProtocol: manifest.inputProtocol ?? "native_pdf",
    caseCount: caseScores.length,
    expectedCaseCount: expectedCaseIds.length,
    complete: missingCaseIds.length === 0,
    missingCaseIds,
    score: round(weightedMean(caseScores.map((score) => ({ value: score.score, weight: pagesByCaseId.get(score.caseId) ?? 1 })))),
    scoreCaseMean: round(mean(caseScores.map((score) => score.score))),
    scoreAggregation: "page_weighted",
    costUsd: round(totalCostUsd, 6),
    meanCostUsdPerCaseAttempt: round(mean(scores.map((score) => score.estimatedCostUsd)), 6),
    totalElapsedMs,
    meanElapsedMsPerCaseAttempt: Math.round(mean(scores.map((score) => score.elapsedMs))),
    totalInputTokens,
    totalOutputTokens,
    meanOutputTokensPerCaseAttempt: Math.round(mean(scores.map((score) => score.usage?.outputTokens ?? 0))),
    attemptCount: scores.length,
    minAttemptsPerCase: caseScores.length === 0 ? 0 : Math.min(...caseScores.map((score) => score.attempts)),
    maxAttemptsPerCase: caseScores.length === 0 ? 0 : Math.max(...caseScores.map((score) => score.attempts)),
    failureRate: scores.length === 0 ? 0 : round((failed.length / scores.length) * 100),
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
