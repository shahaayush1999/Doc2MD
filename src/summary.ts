import { readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";

type Score = {
  caseId: string;
  score: number;
  estimatedCostUsd: number;
  elapsedMs: number;
  usage: { inputTokens?: number; outputTokens?: number; totalTokens?: number } | null;
  finishReason: string;
  error?: string;
};

function mean(values: number[]) {
  return values.length === 0 ? 0 : values.reduce((sum, value) => sum + value, 0) / values.length;
}

function round(value: number, digits = 1) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

const modelId = process.argv[2] ?? "vertex-gemini-3.1-flash-lite";
const runRoot = path.join("runs", modelId);
const manifest = JSON.parse(await readFile("benchmark/manifest.json", "utf-8")) as { cases: Array<{ id: string }> };
const manifestCaseIds = new Set(manifest.cases.map((testCase) => testCase.id));
const caseIds = (await readdir(runRoot)).filter((name) => manifestCaseIds.has(name));
const scores: Score[] = [];
for (const caseId of caseIds) {
  try {
    scores.push(JSON.parse(await readFile(path.join(runRoot, caseId, "score.json"), "utf-8")) as Score);
  } catch {
    // Ignore unscored runs.
  }
}
scores.sort((a, b) => a.caseId.localeCompare(b.caseId));

const failed = scores.filter((score) => score.error || score.finishReason === "error");
const totalCostUsd = scores.reduce((sum, score) => sum + score.estimatedCostUsd, 0);
const totalElapsedMs = scores.reduce((sum, score) => sum + score.elapsedMs, 0);
const totalInputTokens = scores.reduce((sum, score) => sum + (score.usage?.inputTokens ?? 0), 0);
const totalOutputTokens = scores.reduce((sum, score) => sum + (score.usage?.outputTokens ?? 0), 0);

const summary = {
  modelId,
  caseCount: scores.length,
  score: round(mean(scores.map((score) => score.score))),
  costUsd: round(totalCostUsd, 6),
  totalElapsedMs,
  totalInputTokens,
  totalOutputTokens,
  failureRate: scores.length === 0 ? 0 : round((failed.length / scores.length) * 100),
};

await writeFile(path.join(runRoot, "summary.json"), JSON.stringify(summary, null, 2) + "\n", "utf-8");
console.log(JSON.stringify(summary, null, 2));
