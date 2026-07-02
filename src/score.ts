import { readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";

type Check = {
  id: string;
  weight: number;
  pattern?: string;
  patterns?: string[];
  mustNotPattern?: string;
  mustNotPatterns?: string[];
};

type CheckFile = {
  id: string;
  checks: Check[];
};

function normalize(text: string): string {
  return text.replace(/\r\n/g, "\n").replace(/[ \t]+/g, " ").trim();
}

async function scoreRun(caseId: string, modelId: string) {
  const caseDir = path.join("experiments", "cases", caseId);
  const runDir = path.join("experiments", "runs", caseId, modelId);
  const checks = JSON.parse(await readFile(path.join(caseDir, "checks.json"), "utf-8")) as CheckFile;
  const prediction = normalize(await readFile(path.join(runDir, "prediction.md"), "utf-8"));
  const result = JSON.parse(await readFile(path.join(runDir, "result.json"), "utf-8"));

  let earned = 0;
  let possible = 0;
  const details = checks.checks.map((check) => {
    possible += check.weight;
    const patterns = check.patterns ?? (check.pattern ? [check.pattern] : []);
    const mustNotPatterns = check.mustNotPatterns ?? (check.mustNotPattern ? [check.mustNotPattern] : []);
    const positiveMatched = patterns.length === 0 || patterns.some((pattern) => new RegExp(pattern, "iu").test(prediction));
    const forbiddenMatched = mustNotPatterns.some((pattern) => new RegExp(pattern, "iu").test(prediction));
    const matched = positiveMatched && !forbiddenMatched;
    if (matched) earned += check.weight;
    return { ...check, matched };
  });

  const score = possible === 0 ? 0 : earned / possible;
  const scored = {
    caseId,
    modelId,
    score,
    percentage: Math.round(score * 1000) / 10,
    earned,
    possible,
    estimatedCostUsd: result.estimatedCostUsd,
    elapsedMs: result.elapsedMs,
    usage: result.usage,
    details,
  };
  await writeFile(path.join(runDir, "score.json"), JSON.stringify(scored, null, 2) + "\n", "utf-8");
  return scored;
}

const caseId = process.argv[2] ?? "001-figure-trap";
const runsDir = path.join("experiments", "runs", caseId);
const modelIds = process.argv.length > 3 ? process.argv.slice(3) : await readdir(runsDir);

const scores = [];
for (const modelId of modelIds) {
  scores.push(await scoreRun(caseId, modelId));
}

scores.sort((a, b) => b.score - a.score || a.estimatedCostUsd - b.estimatedCostUsd);
console.table(
  scores.map((score) => ({
    model: score.modelId,
    pct: score.percentage,
    cost_usd: Number(score.estimatedCostUsd.toFixed(8)),
    elapsed_ms: score.elapsedMs,
    input_tokens: score.usage.inputTokens,
    output_tokens: score.usage.outputTokens,
  })),
);
