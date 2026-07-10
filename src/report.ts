import { mkdir, readFile, readdir, rm } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { buildBenchmarkFingerprint } from "./benchmarkFingerprint.js";
import { sha256, stableJson } from "./cache.js";
import { models, prompt, samplesPerModelCase } from "./run.js";
import { scoringContractFingerprint } from "./score.js";
import { atomicWriteText } from "./runRuntime.js";
import { loadBenchmarkManifest } from "./manifest.js";
import { deriveModelSummary } from "./summary.js";

export type CaseScore = {
  caseId: string;
  title?: string;
  family?: string;
  tags: string[];
  pages: number;
  samples?: number;
  expectedSamples?: number;
  complete?: boolean;
  score: number | null;
  scoreMin: number | null;
  scoreMax: number | null;
  scoreStddev: number | null;
  sampleScores: Array<{ sample: string; score: number; valid?: boolean; modelCallFailed?: boolean }>;
  finishReasons?: Array<{ sample: string; finishReason: string }>;
  outputTokens?: number;
};

export type Summary = {
  modelId: string;
  provider: string;
  suite: string;
  manifestPath: string;
  benchmarkFingerprint: string;
  inferenceBenchmarkFingerprint: string;
  inferenceProtocolFingerprint: string;
  modelConfigFingerprint: string;
  resolvedInferenceModelId: string | null;
  resolvedEvaluatorModelId: string | null;
  pricingFingerprint: string;
  pricingVersion: string;
  scoringContractFingerprint: string;
  cohortArtifactFingerprint: string;
  benchmarkName?: string;
  scoreName?: string;
  inputProtocol?: string;
  caseCount: number;
  expectedCaseCount: number;
  samplesPerModelCase: number;
  sampleCount: number;
  score: number | null;
  suiteSampleScores: Array<{ sample: string; score: number }>;
  scoreStddev: number | null;
  scoreMin: number | null;
  scoreMax: number | null;
  scoreAggregation: string;
  costUsd: number;
  totalElapsedMs: number;
  totalInputTokens: number;
  totalOutputTokens: number;
  modelFailureCount?: number;
  modelFailureRate?: number;
  evaluatorFailureCount?: number;
  evaluatorFailureRate?: number;
  complete: boolean;
  missingCaseIds?: string[];
  invalidSamples?: unknown[];
  caseScores: CaseScore[];
};

export type ManifestCase = {
  id: string;
  title: string;
  family: string;
  tags: string[];
  pages: number;
  pdf: string;
  gold: string;
  spec: string;
  facts: string;
};

export type Manifest = {
  schemaVersion?: number;
  name: string;
  suite?: string;
  scoreName?: string;
  inputProtocol?: string;
  description?: string;
  pageCount?: number;
  cases: ManifestCase[];
};

function round(value: number, digits = 1) {
  const factor = 10 ** digits;
  return Math.round(value * factor) / factor;
}

function escapeHtml(value: unknown) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fmtMoney(value: number) {
  return `$${value.toFixed(value < 0.01 ? 6 : 4)}`;
}

function fmtSeconds(ms: number) {
  return `${round(ms / 1000, 1)}s`;
}

function modelLabel(modelId: string) {
  return models[modelId]?.modelName ?? modelId;
}

async function readJson<T>(filePath: string): Promise<T> {
  return JSON.parse(await readFile(filePath, "utf-8")) as T;
}

type SummaryFreshness = {
  inferenceBenchmarkFingerprint: string;
  inferenceProtocolFingerprint: string;
  modelConfigFingerprint: string;
  pricingFingerprint: string;
  pricingVersion: string;
  cohortArtifactFingerprint: string;
  artifactDerivedSummary?: Summary;
};

function mean(values: number[]) {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function sampleStddev(values: number[]) {
  if (values.length <= 1) return 0;
  const average = mean(values);
  return Math.sqrt(values.reduce((sum, value) => sum + (value - average) ** 2, 0) / (values.length - 1));
}

function approximatelyEqual(left: number, right: number, tolerance = 0.000005) {
  return Math.abs(left - right) <= tolerance;
}

function canonicalPersistedJson(value: unknown) {
  return stableJson(JSON.parse(JSON.stringify(value)));
}

export function validateSummaryArithmetic(summary: Summary, manifest: Manifest): string | null {
  const expectedSampleIds = Array.from({ length: summary.samplesPerModelCase }, (_, index) => String(index + 1).padStart(3, "0"));
  const sampleIdSet = new Set(expectedSampleIds);
  const caseById = new Map(manifest.cases.map((testCase) => [testCase.id, testCase]));
  const sampleScoresByCase = new Map<string, Map<string, number>>();

  for (const caseScore of summary.caseScores) {
    const testCase = caseById.get(caseScore.caseId);
    if (!testCase) return `unknown case summary ${caseScore.caseId}`;
    if (
      caseScore.title !== testCase.title ||
      caseScore.family !== testCase.family ||
      caseScore.pages !== testCase.pages ||
      JSON.stringify(caseScore.tags) !== JSON.stringify(testCase.tags)
    ) {
      return `case metadata is stale for ${caseScore.caseId}`;
    }
    if (caseScore.complete !== true || caseScore.samples !== summary.samplesPerModelCase) {
      return `case cohort is incomplete for ${caseScore.caseId}`;
    }
    if (!Array.isArray(caseScore.sampleScores) || caseScore.sampleScores.length !== expectedSampleIds.length) {
      return `case sample cohort is incomplete for ${caseScore.caseId}`;
    }
    const bySample = new Map<string, number>();
    for (const sample of caseScore.sampleScores) {
      if (!sampleIdSet.has(sample.sample) || bySample.has(sample.sample)) return `case sample ids are invalid for ${caseScore.caseId}`;
      if (sample.valid !== true || !Number.isFinite(sample.score) || sample.score < 0 || sample.score > 100) {
        return `case sample score is invalid for ${caseScore.caseId}#${sample.sample}`;
      }
      bySample.set(sample.sample, sample.score);
    }
    const values = expectedSampleIds.map((sample) => bySample.get(sample)!);
    if (
      !approximatelyEqual(caseScore.score!, round(mean(values), 6)) ||
      !approximatelyEqual(caseScore.scoreMin!, round(Math.min(...values), 6)) ||
      !approximatelyEqual(caseScore.scoreMax!, round(Math.max(...values), 6)) ||
      !approximatelyEqual(caseScore.scoreStddev!, round(sampleStddev(values), 6))
    ) {
      return `case aggregate arithmetic is invalid for ${caseScore.caseId}`;
    }
    sampleScoresByCase.set(caseScore.caseId, bySample);
  }

  const suiteBySample = new Map(summary.suiteSampleScores.map((sample) => [sample.sample, sample.score]));
  if (suiteBySample.size !== expectedSampleIds.length) return "full-suite sample ids are invalid";
  const recomputedSuiteScores: number[] = [];
  for (const sampleId of expectedSampleIds) {
    const expected = round(mean(manifest.cases.map((testCase) => sampleScoresByCase.get(testCase.id)!.get(sampleId)!)), 6);
    const stored = suiteBySample.get(sampleId);
    if (stored === undefined || !approximatelyEqual(stored, expected)) return `full-suite sample arithmetic is invalid for ${sampleId}`;
    recomputedSuiteScores.push(expected);
  }
  if (
    !approximatelyEqual(summary.score!, round(mean(recomputedSuiteScores))) ||
    !approximatelyEqual(summary.scoreStddev!, round(sampleStddev(recomputedSuiteScores), 6)) ||
    !approximatelyEqual(summary.scoreMin!, round(Math.min(...recomputedSuiteScores), 6)) ||
    !approximatelyEqual(summary.scoreMax!, round(Math.max(...recomputedSuiteScores), 6))
  ) {
    return "full-suite aggregate arithmetic is invalid";
  }
  return null;
}

export function validSummary(
  summary: Summary,
  manifest: Manifest,
  benchmarkFingerprint: string,
  freshness?: SummaryFreshness,
) {
  const expectedCaseIds = new Set(manifest.cases.map((testCase) => testCase.id));
  if (!summary.complete) return "summary is incomplete";
  if ((summary.missingCaseIds?.length ?? 0) > 0 || (summary.invalidSamples?.length ?? 0) > 0) {
    return "summary contains missing cases or invalid samples";
  }
  if (summary.benchmarkFingerprint !== benchmarkFingerprint) return "benchmark fingerprint is stale";
  if (summary.scoringContractFingerprint !== scoringContractFingerprint) return "scoring contract is stale";
  if (freshness) {
    if (summary.inferenceBenchmarkFingerprint !== freshness.inferenceBenchmarkFingerprint) return "inference benchmark fingerprint is stale";
    if (summary.inferenceProtocolFingerprint !== freshness.inferenceProtocolFingerprint) return "inference protocol fingerprint is stale";
    if (summary.modelConfigFingerprint !== freshness.modelConfigFingerprint) return "model configuration fingerprint is stale";
    if (summary.pricingFingerprint !== freshness.pricingFingerprint || summary.pricingVersion !== freshness.pricingVersion) {
      return "pricing metadata is stale";
    }
    if (summary.cohortArtifactFingerprint !== freshness.cohortArtifactFingerprint) return "run/score cohort artifacts are stale";
    if (
      freshness.artifactDerivedSummary &&
      canonicalPersistedJson(summary) !== canonicalPersistedJson(freshness.artifactDerivedSummary)
    ) {
      return "summary content does not match current run/score artifacts";
    }
  }
  if (summary.suite !== (manifest.suite ?? "official")) return "suite does not match the manifest";
  if (typeof summary.score !== "number" || !Number.isFinite(summary.score)) return "aggregate score is missing";
  if (
    typeof summary.scoreStddev !== "number" ||
    !Number.isFinite(summary.scoreStddev) ||
    typeof summary.scoreMin !== "number" ||
    !Number.isFinite(summary.scoreMin) ||
    typeof summary.scoreMax !== "number" ||
    !Number.isFinite(summary.scoreMax)
  ) {
    return "full-suite variability fields are missing";
  }
  if (!models[summary.modelId]) return "model is not in the current registry";
  if (summary.provider !== models[summary.modelId].provider) return "provider metadata does not match the current model registry";
  if (typeof summary.resolvedInferenceModelId !== "string" || summary.resolvedInferenceModelId.length === 0) {
    return "resolved inference model identity is missing";
  }
  if ((summary.modelFailureCount ?? 0) < summary.sampleCount &&
      (typeof summary.resolvedEvaluatorModelId !== "string" || summary.resolvedEvaluatorModelId.length === 0)) {
    return "resolved evaluator model identity is missing";
  }
  if (summary.expectedCaseCount !== manifest.cases.length || summary.caseCount !== manifest.cases.length) return "case count is stale";
  if (!Array.isArray(summary.caseScores) || summary.caseScores.length !== manifest.cases.length) return "case summaries are incomplete";
  const caseScoreIds = new Set(summary.caseScores.map((caseScore) => caseScore.caseId));
  if (caseScoreIds.size !== expectedCaseIds.size || [...expectedCaseIds].some((caseId) => !caseScoreIds.has(caseId))) {
    return "case summaries do not match the manifest";
  }
  if (summary.samplesPerModelCase !== samplesPerModelCase) return "sample count does not match the current protocol";
  if (summary.sampleCount !== manifest.cases.length * summary.samplesPerModelCase) return "sample count is incomplete";
  if (!Array.isArray(summary.suiteSampleScores) || summary.suiteSampleScores.length !== summary.samplesPerModelCase) {
    return "full-suite sample scores are incomplete";
  }
  const expectedSampleIds = new Set(Array.from({ length: summary.samplesPerModelCase }, (_, index) => String(index + 1).padStart(3, "0")));
  const suiteSampleIds = new Set(summary.suiteSampleScores.map((sampleScore) => sampleScore.sample));
  if (
    suiteSampleIds.size !== expectedSampleIds.size ||
    [...expectedSampleIds].some((sampleId) => !suiteSampleIds.has(sampleId)) ||
    summary.suiteSampleScores.some((sampleScore) => !Number.isFinite(sampleScore.score))
  ) {
    return "full-suite sample cohort is invalid";
  }
  if (summary.scoreAggregation !== "equal_case_sample_first") return "score aggregation contract is stale";
  if (
    summary.caseScores.some(
      (caseScore) =>
        !Number.isFinite(caseScore.score) ||
        !Number.isFinite(caseScore.scoreMin) ||
        !Number.isFinite(caseScore.scoreMax) ||
        !Array.isArray(caseScore.sampleScores) ||
        caseScore.sampleScores.length !== summary.samplesPerModelCase ||
        new Set(caseScore.sampleScores.map((sampleScore) => sampleScore.sample)).size !== expectedSampleIds.size ||
        [...expectedSampleIds].some(
          (sampleId) => !caseScore.sampleScores.some((sampleScore) => sampleScore.sample === sampleId && Number.isFinite(sampleScore.score)),
        ),
    )
  ) {
    return "per-case score ranges are incomplete";
  }
  if (
    [summary.costUsd, summary.totalElapsedMs, summary.totalInputTokens, summary.totalOutputTokens].some(
      (value) => typeof value !== "number" || !Number.isFinite(value) || value < 0,
    )
  ) {
    return "inference operating totals are invalid";
  }
  const arithmeticError = validateSummaryArithmetic(summary, manifest);
  if (arithmeticError) return arithmeticError;
  return null;
}

async function currentSummaryFreshness(summary: Summary, manifest: Manifest, manifestPath: string): Promise<SummaryFreshness> {
  if (!models[summary.modelId]) throw new Error(`Unknown model ${summary.modelId}.`);
  const derived = (await deriveModelSummary(summary.modelId, { manifestPath, lockSamples: false })) as Summary;
  return {
    inferenceBenchmarkFingerprint: derived.inferenceBenchmarkFingerprint,
    inferenceProtocolFingerprint: derived.inferenceProtocolFingerprint,
    modelConfigFingerprint: derived.modelConfigFingerprint,
    pricingFingerprint: derived.pricingFingerprint,
    pricingVersion: derived.pricingVersion,
    cohortArtifactFingerprint: derived.cohortArtifactFingerprint,
    artifactDerivedSummary: derived,
  };
}

async function loadSummaries(manifest: Manifest, manifestPath: string, benchmarkFingerprint: string): Promise<Summary[]> {
  const entries = await readdir("runs", { withFileTypes: true }).catch(() => []);
  const summaries: Summary[] = [];
  const summaryFile = `summary.${manifest.suite ?? "official"}.json`;
  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const summaryPath = path.join("runs", entry.name, summaryFile);
    try {
      const summary = await readJson<Summary>(summaryPath);
      if (summary.modelId !== entry.name) {
        console.warn(`Ignoring ${summaryPath}: model id does not match its run directory`);
        continue;
      }
      const freshness = await currentSummaryFreshness(summary, manifest, manifestPath);
      const invalidReason = validSummary(summary, manifest, benchmarkFingerprint, freshness);
      if (invalidReason) {
        console.warn(`Ignoring ${summaryPath}: ${invalidReason}`);
      } else {
        summaries.push(summary);
      }
    } catch (error) {
      const detail = error instanceof Error ? error.message : String(error);
      console.warn(`Ignoring ${summaryPath}: cannot read or validate summary (${detail})`);
    }
  }
  return summaries.sort((a, b) => (b.score ?? -Infinity) - (a.score ?? -Infinity) || (a.modelId < b.modelId ? -1 : a.modelId > b.modelId ? 1 : 0));
}

function bar(value: number, max = 100) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return `<span class="bar" aria-hidden="true"><span style="width:${pct}%"></span></span>`;
}

function scoreBar(value: number) {
  return `<span class="score-cell">${bar(value)}<span class="score-value">${value}</span></span>`;
}

function chartDataScript(summaries: Summary[]) {
  const data = summaries.map((summary) => ({
    id: summary.modelId,
    label: modelLabel(summary.modelId),
    score: summary.score!,
    cost: summary.costUsd,
    time: round(summary.totalElapsedMs / 1000, 1),
    tokens: summary.totalOutputTokens,
    provider: summary.provider,
  }));
  return JSON.stringify(data).replace(/</g, "\\u003c");
}

function interactiveChart(summaries: Summary[], inferenceCallCount: number) {
  return `<div class="bench-chart" id="doc2md-bench-chart" data-points="${escapeHtml(chartDataScript(summaries))}">
    <div class="bench-chart__tabs" role="tablist" aria-label="Chart x-axis metric">
      <button type="button" data-metric="cost" aria-selected="true">Fidelity vs Cost</button>
      <button type="button" data-metric="time" aria-selected="false">Fidelity vs Time</button>
      <button type="button" data-metric="tokens" aria-selected="false">Fidelity vs Output</button>
    </div>
    <div class="bench-chart__stage"></div>
  </div>
  <script>
(() => {
  const root = document.getElementById("doc2md-bench-chart");
  if (!root) return;
  const data = JSON.parse(root.dataset.points || "[]");
  const stage = root.querySelector(".bench-chart__stage");
  const buttons = Array.from(root.querySelectorAll("[data-metric]"));
  const W = 2400, H = 1500;
  const pad = { left: 150, right: 120, top: 140, bottom: 210 };
  const right = W - pad.right;
  const bottom = H - pad.bottom;
  const providerColors = { "openai": "#0f766e", "google-vertex": "#2563eb" };
  const color = (point) => providerColors[point.provider] || "#6b7280";
  const fmtMoney = (v) => "$" + (v < 0.01 ? v.toFixed(4) : v.toFixed(v < 1 ? 3 : 2));
  const fmtSeconds = (v) => Math.round(v) + "s";
  const fmtTokens = (v) => Math.round(v / 1000) + "k";
  const metrics = {
    cost: { title: "Reconstruction fidelity vs estimated inference cost", axis: "Estimated inference cost for ${inferenceCallCount} calls, USD (log scale)", value: p => p.cost, format: fmtMoney, ticks: [0.03, 0.1, 0.3, 1, 3], scale: "log" },
    time: { title: "Reconstruction fidelity vs model-call duration", axis: "Summed model-call duration for ${inferenceCallCount} calls", value: p => p.time, format: fmtSeconds, ticks: [0, 300, 600, 900, 1200] },
    tokens: { title: "Reconstruction fidelity vs output volume", axis: "Total inference output tokens for ${inferenceCallCount} calls", value: p => p.tokens, format: fmtTokens, ticks: [0, 50000, 100000, 150000] },
  };
  const labelOffsets = {
    cost: {
      "openai-gpt-5.4-mini": { dx: -34, dy: 18, anchor: "end" },
      "vertex-gemini-3-flash-preview": { dx: 34, dy: 116, anchor: "start" },
      "vertex-gemini-3.1-flash-lite": { dx: -34, dy: 92, anchor: "end" },
      "vertex-gemini-2.5-flash-lite": { dx: 34, dy: 56, anchor: "start" },
      "openai-gpt-5.4-nano": { dx: -34, dy: -48, anchor: "end" },
      "openai-gpt-5-nano": { dx: 34, dy: 58, anchor: "start" },
    },
    time: {
      "openai-gpt-5.4-mini": { dx: -34, dy: -46, anchor: "end" },
      "vertex-gemini-3-flash-preview": { dx: 34, dy: 122, anchor: "start" },
      "vertex-gemini-3.1-flash-lite": { dx: -34, dy: 58, anchor: "end" },
      "vertex-gemini-2.5-flash-lite": { dx: 34, dy: 58, anchor: "start" },
      "openai-gpt-5.4-nano": { dx: -34, dy: -50, anchor: "end" },
      "openai-gpt-5-nano": { dx: 34, dy: 58, anchor: "start" },
    },
    tokens: {
      "openai-gpt-5.4-mini": { dx: -86, dy: 34, anchor: "end" },
      "vertex-gemini-3-flash-preview": { dx: 34, dy: 122, anchor: "start" },
      "vertex-gemini-3.1-flash-lite": { dx: -34, dy: 58, anchor: "end" },
      "vertex-gemini-2.5-flash-lite": { dx: -34, dy: 58, anchor: "end" },
      "openai-gpt-5.4-nano": { dx: -34, dy: -50, anchor: "end" },
      "openai-gpt-5-nano": { dx: 34, dy: 58, anchor: "start" },
    },
  };
  const esc = (value) => String(value).replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]));
  const yMin = Math.max(0, Math.floor((Math.min(...data.map(p => p.score)) - 4) / 5) * 5);
  const y = (score) => pad.top + (1 - (score - yMin) / (100 - yMin || 1)) * (bottom - pad.top);
  const yTicks = Array.from({ length: Math.floor((100 - yMin) / 10) + 1 }, (_, i) => 100 - i * 10).filter(v => v >= yMin);
  function render(metricName) {
    const metric = metrics[metricName];
    const values = data.map(metric.value);
    const positiveValues = values.filter(value => value > 0);
    const minPositive = positiveValues.length ? Math.min(...positiveValues) : 0.000001;
    const logFloor = Math.max(minPositive * 0.8, 0.000001);
    const maxRawX = Math.max(...values, metric.scale === "log" ? logFloor * 10 : 1);
    const minX = metric.scale === "log" ? Math.log10(logFloor) : 0;
    const maxX = metric.scale === "log" ? Math.log10(Math.max(maxRawX * 1.12, logFloor * 10)) : maxRawX;
    const transformX = (value) => metric.scale === "log" ? Math.log10(Math.max(value, logFloor)) : value;
    const x = (value) => pad.left + ((transformX(value) - minX) / (maxX - minX || 1)) * (right - pad.left);
    const positioned = data.map(point => ({ ...point, x: x(metric.value(point)), y: y(point.score), rawX: metric.value(point) }));
    const xTicks = metric.ticks.filter(tick => (metric.scale === "log" ? tick >= minPositive : tick >= 0) && tick <= maxRawX);
    const grid = yTicks.map(tick => '<g><line x1="' + pad.left + '" y1="' + y(tick) + '" x2="' + right + '" y2="' + y(tick) + '" stroke="#d8d2c3" stroke-width="2"></line><text x="' + pad.left + '" y="' + (y(tick) - 18) + '">' + tick + '</text></g>').join("")
      + xTicks.map(tick => '<g><line x1="' + x(tick) + '" y1="' + pad.top + '" x2="' + x(tick) + '" y2="' + bottom + '" stroke="#ebe6d9" stroke-width="1.5"></line><text x="' + x(tick) + '" y="' + (bottom + 78) + '" text-anchor="middle">' + metric.format(tick) + '</text></g>').join("");
    const labelItems = positioned.map(point => {
      const offset = (labelOffsets[metricName] && labelOffsets[metricName][point.id]) || { dx: 34, dy: -34, anchor: "start" };
      const lx = Math.max(pad.left + 20, Math.min(right - 20, point.x + offset.dx));
      const ly = Math.max(pad.top + 32, Math.min(bottom - 16, point.y + offset.dy));
      return { point, lx, ly, anchor: offset.anchor };
    });
    const connectors = labelItems.map(item => {
      const labelEdgeX = item.anchor === "end" ? item.lx + 14 : item.lx - 14;
      const labelEdgeY = item.ly - 10;
      const farEnough = Math.abs(labelEdgeX - item.point.x) > 42 || Math.abs(labelEdgeY - item.point.y) > 42;
      if (!farEnough) return "";
      return '<line class="bench-chart__leader" x1="' + item.point.x + '" y1="' + item.point.y + '" x2="' + labelEdgeX + '" y2="' + labelEdgeY + '" stroke="' + color(item.point) + '"></line>';
    }).join("");
    const labels = labelItems.map(item => '<text class="bench-chart__label" x="' + item.lx + '" y="' + item.ly + '" text-anchor="' + item.anchor + '" style="fill:' + color(item.point) + '">' + esc(item.point.label) + ' (' + item.point.score + ')</text>').join("");
    const points = positioned.map(point => '<g class="bench-chart__point" tabindex="0" data-id="' + esc(point.id) + '" aria-label="' + esc(point.label + ": " + point.score + ", " + metric.format(point.rawX)) + '"><circle cx="' + point.x + '" cy="' + point.y + '" r="26" fill="transparent"></circle><circle cx="' + point.x + '" cy="' + point.y + '" r="15" fill="' + color(point) + '" stroke="#fffdf8" stroke-width="7"></circle><title>' + esc(point.label + " — score " + point.score + ", " + metric.axis + ": " + metric.format(point.rawX)) + '</title></g>').join("");
    stage.innerHTML = '<svg class="figure-svg" viewBox="0 0 ' + W + ' ' + H + '" role="img" aria-label="' + esc(metric.title) + '"><rect width="' + W + '" height="' + H + '" fill="#fffdf8"></rect><text class="chart-title" x="' + pad.left + '" y="86">' + esc(metric.title) + '</text><g class="ticks">' + grid + '</g>' + connectors + points + labels + '<text class="axis-title" text-anchor="middle" x="' + (pad.left + (right - pad.left) / 2) + '" y="' + (H - 34) + '">' + esc(metric.axis) + '</text><text class="axis-title" transform="translate(58 ' + (H / 2 + 110) + ') rotate(-90)">Reconstruction fidelity score</text></svg>';
  }
  buttons.forEach(button => {
    button.addEventListener("click", () => {
      buttons.forEach(other => other.setAttribute("aria-selected", String(other === button)));
      render(button.dataset.metric || "cost");
    });
  });
  render("cost");
})();
  </script>`;
}

function css() {
  return `<style>
    :root {
      --ink: #111827;
      --muted: #4b5563;
      --faint: #6b7280;
      --line: #d1d5db;
      --soft: #f3f4f6;
      --paper: #fffdf8;
      --accent: #0f766e;
      --accent-2: #1d4ed8;
      --warn: #b45309;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: #f7f5ef;
      color: var(--ink);
      font-family: ui-serif, Georgia, Cambria, "Times New Roman", serif;
      line-height: 1.55;
    }
    main {
      max-width: 1120px;
      margin: 0 auto;
      padding: 48px 28px 72px;
      background: var(--paper);
      min-height: 100vh;
      border-left: 1px solid #ebe7dc;
      border-right: 1px solid #ebe7dc;
    }
    header {
      border-bottom: 2px solid var(--ink);
      padding-bottom: 28px;
      margin-bottom: 32px;
    }
    .kicker {
      font: 700 12px/1.2 ui-sans-serif, system-ui, sans-serif;
      text-transform: uppercase;
      letter-spacing: .12em;
      color: var(--accent);
      margin-bottom: 18px;
    }
    h1 {
      font-size: 52px;
      line-height: .98;
      letter-spacing: 0;
      max-width: 860px;
      margin: 0 0 18px;
    }
    h2 {
      font-size: 29px;
      line-height: 1.12;
      margin: 46px 0 12px;
      border-top: 1px solid var(--line);
      padding-top: 22px;
    }
    h3 {
      font: 700 17px/1.25 ui-sans-serif, system-ui, sans-serif;
      margin: 28px 0 8px;
    }
    p { max-width: 800px; margin: 0 0 14px; }
    .lede {
      font-size: 20px;
      line-height: 1.45;
      max-width: 900px;
      color: #1f2937;
    }
    .meta {
      display: flex;
      flex-wrap: wrap;
      gap: 10px 22px;
      color: var(--muted);
      font: 13px/1.4 ui-sans-serif, system-ui, sans-serif;
      margin-top: 20px;
    }
    .figure {
      margin: 18px 0 30px;
      border-top: 1px solid var(--line);
      border-bottom: 1px solid var(--line);
      padding: 18px 0 12px;
    }
    .figure-title {
      font: 700 14px/1.3 ui-sans-serif, system-ui, sans-serif;
      margin-bottom: 8px;
    }
    .caption {
      color: var(--muted);
      font: 13px/1.45 ui-sans-serif, system-ui, sans-serif;
      max-width: 860px;
      margin-top: 8px;
    }
    .figure-svg {
      width: 100%;
      max-width: 980px;
      height: auto;
      display: block;
      background: #fffdf8;
      border: 1px solid #e5dfd0;
    }
    .bench-chart {
      max-width: 980px;
    }
    .bench-chart__tabs {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      width: min(100%, 620px);
      margin: 0 auto 14px;
      padding: 3px;
      border: 1px solid #ddd6c5;
      border-radius: 999px;
      background: #fffdf8;
      font: 12px/1.2 ui-sans-serif, system-ui, sans-serif;
    }
    .bench-chart__tabs button {
      border: 0;
      border-radius: 999px;
      background: transparent;
      color: var(--muted);
      cursor: pointer;
      padding: 7px 13px;
      font: inherit;
    }
    .bench-chart__tabs button[aria-selected="true"] {
      background: #ece7da;
      color: var(--ink);
      font-weight: 700;
    }
    svg text {
      font-family: ui-sans-serif, system-ui, sans-serif;
      font-size: 30px;
      fill: #1f2937;
    }
    svg .chart-title {
      font-size: 42px;
      font-weight: 700;
      fill: #111827;
    }
    svg .axis-title {
      fill: var(--muted);
      font-size: 34px;
      font-weight: 700;
    }
    svg .bench-chart__label {
      font-size: 34px;
      font-weight: 800;
      fill: #111827;
      stroke: #fffdf8;
      stroke-width: 8px;
      paint-order: stroke fill;
    }
    svg .bench-chart__leader {
      opacity: 0.34;
      stroke-width: 3px;
      stroke-linecap: round;
    }
    svg .bench-chart__point circle {
      transition: r 140ms ease, opacity 140ms ease;
    }
    svg .bench-chart__point:hover circle:last-child,
    svg .bench-chart__point:focus circle:last-child {
      r: 22px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 18px 0 28px;
      font: 13px/1.35 ui-sans-serif, system-ui, sans-serif;
    }
    th {
      text-align: left;
      border-bottom: 2px solid var(--ink);
      padding: 9px 8px;
      vertical-align: bottom;
    }
    td {
      border-bottom: 1px solid #e5e7eb;
      padding: 9px 8px;
      vertical-align: top;
    }
    td.num, th.num { text-align: right; font-variant-numeric: tabular-nums; }
    .table-scroll {
      width: 100%;
      overflow-x: auto;
    }
    .table-scroll table { min-width: 940px; }
    .appendix-table th,
    .appendix-table td { white-space: nowrap; }
    .appendix-table th:first-child,
    .appendix-table td:first-child {
      min-width: 250px;
      white-space: normal;
    }
    .bar {
      display: block;
      width: 92px;
      height: 6px;
      border: 1px solid #cbd5e1;
      background: white;
    }
    .bar > span {
      display: block;
      height: 100%;
      background: var(--accent);
    }
    .score-cell {
      display: grid;
      grid-template-columns: 92px 42px;
      align-items: center;
      justify-content: end;
      gap: 10px;
      font-variant-numeric: tabular-nums;
    }
    .score-value {
      display: block;
      text-align: right;
    }
    .note {
      border-left: 3px solid var(--warn);
      padding-left: 12px;
      color: #3f2d12;
      max-width: 840px;
    }
    .muted { color: var(--faint); font-size: 12px; }
    code {
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      font-size: .92em;
      background: #f1f5f9;
      padding: 1px 4px;
    }
    @media (max-width: 760px) {
      main { padding: 32px 18px 56px; }
      h1 { font-size: 38px; }
      table { font-size: 12px; }
    }
  </style>`;
}

export function renderReport(manifest: Manifest, summaries: Summary[]) {
  summaries = [...summaries].sort((a, b) => b.score! - a.score! || (a.modelId < b.modelId ? -1 : a.modelId > b.modelId ? 1 : 0));
  const totalPages = manifest.pageCount ?? manifest.cases.reduce((sum, testCase) => sum + (testCase.pages ?? 1), 0);
  const samplesPerCaseValues = new Set(summaries.map((summary) => summary.samplesPerModelCase));
  const inferenceCallCounts = new Set(summaries.map((summary) => summary.sampleCount));
  if (samplesPerCaseValues.size !== 1 || inferenceCallCounts.size !== 1) {
    throw new Error("Cannot compare summaries with different sample cohorts");
  }
  if (new Set(summaries.map((summary) => summary.modelId)).size !== summaries.length) {
    throw new Error("Cannot compare duplicate model summaries");
  }
  const samplesPerCase = [...samplesPerCaseValues][0];
  const inferenceCallCount = [...inferenceCallCounts][0];
  const tokenLimitFinishes = (summary: Summary) =>
    summary.caseScores.reduce(
      (count, caseScore) => count + (caseScore.finishReasons ?? []).filter((item) => item.finishReason === "length").length,
      0,
    );

  const modelTable = summaries
    .map(
      (summary) => `<tr>
        <td><strong>${escapeHtml(modelLabel(summary.modelId))}</strong><div class="muted">${escapeHtml(summary.modelId)}</div></td>
        <td class="num">${scoreBar(summary.score!)}</td>
        <td class="num">${summary.scoreStddev!.toFixed(2)}</td>
        <td class="num">${summary.scoreMin!.toFixed(1)}–${summary.scoreMax!.toFixed(1)}</td>
        <td class="num">${fmtMoney(summary.costUsd)}</td>
        <td class="num">${fmtSeconds(summary.totalElapsedMs)}</td>
        <td class="num">${summary.totalOutputTokens.toLocaleString("en-US")}</td>
        <td class="num">${summary.modelFailureCount ?? 0}/${summary.sampleCount}</td>
        <td class="num">${tokenLimitFinishes(summary)}/${summary.sampleCount}</td>
      </tr>`,
    )
    .join("\n");

  const caseScoreMaps = new Map(
    summaries.map((summary) => [summary.modelId, new Map(summary.caseScores.map((caseScore) => [caseScore.caseId, caseScore]))]),
  );
  const caseAppendix = manifest.cases
    .map((testCase) => {
      const cells = summaries
        .map((summary) => {
          const caseScore = caseScoreMaps.get(summary.modelId)!.get(testCase.id)!;
          return `<td class="num"><strong>${caseScore.score!.toFixed(1)}</strong> <span class="muted">(${caseScore.scoreMin!.toFixed(1)}–${caseScore.scoreMax!.toFixed(1)})</span></td>`;
        })
        .join("");
      return `<tr><td><strong>${escapeHtml(testCase.id)}</strong><div class="muted">${escapeHtml(testCase.title)}</div></td>${cells}</tr>`;
    })
    .join("\n");

  return `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Doc2MD Benchmark Report</title>
  ${css()}
</head>
<body>
  <main>
    <header>
      <div class="kicker">Doc2MD Technical Report</div>
      <h1>Faithful document-to-Markdown reconstruction under dense PDF conditions</h1>
      <p class="lede">Doc2MD evaluates whether a model can turn a PDF into a single Markdown document that preserves the document's information, structure, tables, visual elements, and reading experience.</p>
      <div class="meta">
        <span>${manifest.cases.length} cases</span>
        <span>${totalPages} pages</span>
        <span>${samplesPerCase} samples per model/case</span>
        <span>Input protocol: ${escapeHtml(manifest.inputProtocol ?? "native_pdf")}</span>
      </div>
    </header>

    <section>
      <h2>Reconstruction Fidelity, Cost, and Model-call Duration</h2>
      <div class="figure">
        <div class="figure-title">Figure 1. Reconstruction score by operating metric</div>
        ${interactiveChart(summaries, inferenceCallCount)}
        <div class="caption">Switch the x-axis between estimated inference cost, summed model-call duration, and inference output tokens. Each total covers ${inferenceCallCount} model calls. Duration is the sum of individual calls, not parallel benchmark wall-clock time. These operating metrics do not affect the reconstruction-fidelity score.</div>
      </div>
    </section>

    <section>
      <h2>Result Table</h2>
      <div class="table-scroll"><table>
        <thead>
          <tr><th>Model</th><th class="num">Fidelity</th><th class="num">Full-suite SD</th><th class="num">Full-suite range</th><th class="num">Estimated inference cost<br><span class="muted">${inferenceCallCount} calls</span></th><th class="num">Summed model-call duration<br><span class="muted">${inferenceCallCount} calls</span></th><th class="num">Inference output tokens<br><span class="muted">${inferenceCallCount} calls</span></th><th class="num">Model failures</th><th class="num">Token-limit finishes</th></tr>
        </thead>
        <tbody>${modelTable}</tbody>
      </table></div>
      <p class="note">For each sample slot, scores are averaged equally across cases; the reported fidelity is the mean of those ${samplesPerCase} full-suite scores. SD is the sample standard deviation (n−1), and the range is their minimum–maximum. Scoreable response-level model failures remain in the cohort as zero-score samples; provider or transport invocation errors make the cohort incomplete. Token-limit finishes are scoreable responses whose provider finish reason was <code>length</code>.</p>
    </section>

    <section>
      <h2>Per-case Appendix</h2>
      <p>Each cell shows the per-case mean followed by its minimum–maximum across ${samplesPerCase} samples.</p>
      <div class="table-scroll"><table class="appendix-table">
        <thead><tr><th>Case</th>${summaries.map((summary) => `<th class="num">${escapeHtml(modelLabel(summary.modelId))}</th>`).join("")}</tr></thead>
        <tbody>${caseAppendix}</tbody>
      </table></div>
    </section>

    <section>
      <h2>Method</h2>
      <p>The benchmark sends native PDF files directly to providers and asks for one faithful Markdown reconstruction. It does not convert official inputs into page images inside the harness. This means the score reflects the end-to-end provider experience: the model, the provider's PDF ingestion path, and the model's ability to preserve document information.</p>
      <p>Each case has a source-audited reference reconstruction and page-anchored atomic obligations grouped into bounded document regions. To prevent answer leakage, the evaluator receives the audited obligations and numbered candidate lines, but not the PDF or reference text; every non-missing judgment must cite candidate lines. Wrong information is penalized more harshly than omission because downstream systems can often detect missing information, while incorrect extracted facts can silently corrupt later work.</p>
      <p>Doc2MD is intentionally not a plain OCR benchmark. The cases stress compound document reconstruction: page order, table continuation, chart semantics, source-state conflicts, maps, forms, scientific notation, regulated workflows, and realistic mixed-modality packets. The main failure mode for weaker models is not merely reading text incorrectly; it is dropping whole regions, collapsing structured relationships into prose, binding values to the wrong labels, or inventing a plausible but false final state.</p>
      <p>Because model outputs vary, the benchmark uses repeated samples. It first computes a complete suite score for each sample slot by weighting every case equally, then reports the mean, sample standard deviation, minimum, and maximum of those suite scores. Per-case ranges in the appendix expose localized instability without substituting a mean of case-level deviations for full-suite uncertainty.</p>
    </section>
  </main>
</body>
</html>`;
}

export async function generateReport(summaries?: Summary[], options: { outPath?: string; manifestPath?: string } = {}) {
  const manifestPath = options.manifestPath ?? "benchmark/manifest.json";
  const outPath = options.outPath ?? "reports/index.html";
  const manifest = (await loadBenchmarkManifest(manifestPath)).manifest as Manifest;
  const fingerprint = await buildBenchmarkFingerprint({
    manifestPath,
    promptHash: sha256(prompt),
    scoringContractFingerprint,
  });
  const loadedSummaries = summaries ?? (await loadSummaries(manifest, manifestPath, fingerprint.benchmarkFingerprint));
  if (loadedSummaries.length === 0) {
    throw new Error("No complete summaries match the current benchmark fingerprint. Run the benchmark before generating the report.");
  }
  const invalidSummaries = (
    await Promise.all(
      loadedSummaries.map(async (summary) => ({
        modelId: summary.modelId,
        reason: validSummary(
          summary,
          manifest,
          fingerprint.benchmarkFingerprint,
          await currentSummaryFreshness(summary, manifest, manifestPath),
        ),
      })),
    )
  ).filter((entry) => entry.reason);
  if (invalidSummaries.length > 0) {
    throw new Error(
      `Cannot generate a report from stale or incomplete summaries: ${invalidSummaries
        .map((entry) => `${entry.modelId}: ${entry.reason}`)
        .join("; ")}`,
    );
  }
  const assertStillFresh = async () => {
    const currentFingerprint = await buildBenchmarkFingerprint({
      manifestPath,
      promptHash: sha256(prompt),
      scoringContractFingerprint,
    });
    if (currentFingerprint.benchmarkFingerprint !== fingerprint.benchmarkFingerprint) {
      throw new Error("Benchmark artifacts changed while generating the report; retry after active work completes.");
    }
    const stale = (
      await Promise.all(
        loadedSummaries.map(async (summary) => ({
          modelId: summary.modelId,
          reason: validSummary(
            summary,
            manifest,
            currentFingerprint.benchmarkFingerprint,
            await currentSummaryFreshness(summary, manifest, manifestPath),
          ),
        })),
      )
    ).filter((entry) => entry.reason);
    if (stale.length > 0) {
      throw new Error(`Summary/cohort artifacts changed while generating the report: ${stale.map((entry) => `${entry.modelId}: ${entry.reason}`).join("; ")}`);
    }
  };
  await mkdir(path.dirname(outPath), { recursive: true });
  const html = renderReport(manifest, loadedSummaries);
  await assertStillFresh();
  await atomicWriteText(outPath, html);
  try {
    await assertStillFresh();
  } catch (error) {
    await rm(outPath, { force: true }).catch(() => undefined);
    throw error;
  }
  return { outPath, summaries: loadedSummaries.length };
}

function parseCli(argv: string[]) {
  const values = new Map<string, string>();
  for (let index = 0; index < argv.length; index += 1) {
    const argument = argv[index]!;
    if (!argument.startsWith("--")) throw new Error(`Unexpected positional argument ${argument}.`);
    const key = argument.slice(2);
    if (key !== "out" && key !== "manifest") throw new Error(`Unknown option --${key}.`);
    if (values.has(key)) throw new Error(`Duplicate option --${key}.`);
    const value = argv[index + 1];
    if (!value || value.startsWith("--")) throw new Error(`--${key} requires a value.`);
    values.set(key, value);
    index += 1;
  }
  return { outPath: values.get("out"), manifestPath: values.get("manifest") };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const cli = parseCli(process.argv.slice(2));
  const result = await generateReport(undefined, {
    outPath: cli.outPath,
    manifestPath: cli.manifestPath,
  });
  console.log(`Wrote ${result.outPath} from ${result.summaries} model summaries`);
}
