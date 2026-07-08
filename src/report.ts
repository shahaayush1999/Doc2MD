import { mkdir, readFile, readdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

type CaseScore = {
  caseId: string;
  title?: string;
  family?: string;
  tags: string[];
  pages: number;
  samples: number;
  score: number;
  scoreMin: number;
  scoreMax: number;
  scoreStddev: number;
  accuracy: number;
  completeness: number;
  structure: number;
  outputTokens: number;
};

type Summary = {
  modelId: string;
  benchmarkName: string;
  scoreName: string;
  inputProtocol: string;
  caseCount: number;
  samplesPerModelCase: number;
  sampleCount: number;
  score: number;
  scoreCaseMean: number;
  scoreStddevCaseMean: number;
  costUsd: number;
  totalElapsedMs: number;
  totalInputTokens: number;
  totalOutputTokens: number;
  failureRate: number;
  complete: boolean;
  caseScores: CaseScore[];
};

type ManifestCase = {
  id: string;
  title: string;
  family: string;
  tags: string[];
  pages: number;
};

type Manifest = {
  name: string;
  scoreName?: string;
  inputProtocol?: string;
  description?: string;
  pageCount?: number;
  cases: ManifestCase[];
};

const caseChallengeFallback: Record<string, string> = {
  "P07-launch-readiness-dossier":
    "A product launch packet with a dashboard, dependency map, readiness register, escalation heatmap, procurement ledger, and draft/final source-state conflicts.",
  "P12-pfas-method-validation":
    "A scientific-regulatory supplement with equations, calibration tables, continuation tables, chromatogram panels, QC qualifiers, and final result cross-references.",
  "P15-architecture-floorplan-diagrams":
    "An architecture and facilities packet with floorplan callouts, rack positions, topology arrows, panel schedules, and RFI markup.",
  "P17-clinical-trial-site-monitoring":
    "A clinical operations binder with subject visit matrices, lab flags, adverse events, protocol deviations, accountability tables, source forms, and final monitoring status.",
  "P20-utility-outage-restoration":
    "A utility incident packet with SCADA sequence, feeder one-line diagram, switching log, restoration chart, DER clearance, customer-impact map, and draft/final cause conflict.",
  "P21-semiconductor-lot-disposition":
    "A semiconductor quality file with wafer maps, metrology, SPC exceptions, recipe conflicts, MRB disposition, reliability results, shipping holds, and audit evidence.",
  "P22-pharma-stability-release":
    "A pharmaceutical release file with stability continuation, dissolution data, chromatograms, chamber map, hardness mini-trends, deviations, regulatory commitments, and final QA release state.",
  "P23-native-text-layer-recovery":
    "A bad-export logistics packet whose visible rendering is damaged but whose native PDF text layer contains recoverable memo, register, table, and final-control information.",
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
  return modelId.replace(/^openai-/, "").replace(/^vertex-/, "").replace(/-/g, " ");
}

function slug(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "");
}

async function readJson<T>(filePath: string): Promise<T> {
  return JSON.parse(await readFile(filePath, "utf-8")) as T;
}

async function loadSummaries(): Promise<Summary[]> {
  const entries = await readdir("runs", { withFileTypes: true }).catch(() => []);
  const summaries: Summary[] = [];
  for (const entry of entries) {
    if (!entry.isDirectory()) continue;
    const summaryPath = path.join("runs", entry.name, "summary.json");
    try {
      summaries.push(await readJson<Summary>(summaryPath));
    } catch {
      // Ignore incomplete model directories.
    }
  }
  return summaries.sort((a, b) => b.score - a.score);
}

function bestBy<T>(items: T[], score: (item: T) => number): T | null {
  if (items.length === 0) return null;
  return items.reduce((best, item) => (score(item) > score(best) ? item : best));
}

function caseRows(manifest: Manifest, summaries: Summary[]) {
  return manifest.cases.map((testCase) => {
    const scores = summaries.map((summary) => summary.caseScores.find((score) => score.caseId === testCase.id));
    const valid = scores.filter((score): score is CaseScore => Boolean(score));
    const high = valid.length === 0 ? 0 : Math.max(...valid.map((score) => score.score));
    const low = valid.length === 0 ? 0 : Math.min(...valid.map((score) => score.score));
    return { testCase, scores, high, low, spread: round(high - low) };
  });
}

function bar(value: number, max = 100) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  return `<span class="bar" aria-hidden="true"><span style="width:${pct}%"></span></span>`;
}

function scatterSvg(summaries: Summary[], xField: "cost" | "time") {
  const width = 720;
  const height = 300;
  const pad = { left: 56, right: 28, top: 24, bottom: 48 };
  const xValues = summaries.map((summary) => (xField === "cost" ? summary.costUsd : summary.totalElapsedMs / 1000));
  const maxX = Math.max(...xValues, 1);
  const minX = 0;
  const x = (value: number) => pad.left + ((value - minX) / (maxX - minX || 1)) * (width - pad.left - pad.right);
  const y = (score: number) => pad.top + (1 - score / 100) * (height - pad.top - pad.bottom);
  const xLabel = xField === "cost" ? "Total benchmark cost, USD" : "Total sampled model time, seconds";
  const pointColor = xField === "cost" ? "#0f766e" : "#1d4ed8";

  const points = summaries
    .map((summary) => {
      const rawX = xField === "cost" ? summary.costUsd : summary.totalElapsedMs / 1000;
      const label = modelLabel(summary.modelId);
      return `<g>
        <circle cx="${x(rawX)}" cy="${y(summary.score)}" r="5.5" fill="${pointColor}"></circle>
        <text x="${Math.min(width - 190, x(rawX) + 10)}" y="${Math.max(18, y(summary.score) - 8)}">${escapeHtml(label)} (${summary.score})</text>
      </g>`;
    })
    .join("\n");

  return `<svg class="figure-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Score versus ${escapeHtml(xLabel)}">
    <line x1="${pad.left}" y1="${height - pad.bottom}" x2="${width - pad.right}" y2="${height - pad.bottom}" stroke="#1f2937" stroke-width="1"></line>
    <line x1="${pad.left}" y1="${pad.top}" x2="${pad.left}" y2="${height - pad.bottom}" stroke="#1f2937" stroke-width="1"></line>
    <g class="ticks">
      <text x="${pad.left - 38}" y="${y(100) + 4}">100</text>
      <text x="${pad.left - 30}" y="${y(75) + 4}">75</text>
      <text x="${pad.left - 30}" y="${y(50) + 4}">50</text>
      <text x="${pad.left - 30}" y="${y(25) + 4}">25</text>
      <text x="${pad.left - 20}" y="${y(0) + 4}">0</text>
      <line x1="${pad.left}" y1="${y(75)}" x2="${width - pad.right}" y2="${y(75)}" stroke="#e5e7eb"></line>
      <line x1="${pad.left}" y1="${y(50)}" x2="${width - pad.right}" y2="${y(50)}" stroke="#e5e7eb"></line>
      <line x1="${pad.left}" y1="${y(25)}" x2="${width - pad.right}" y2="${y(25)}" stroke="#e5e7eb"></line>
      <text x="${pad.left}" y="${height - 14}">0</text>
      <text x="${width - 150}" y="${height - 14}">${round(maxX, xField === "cost" ? 3 : 0)}</text>
    </g>
    ${points}
    <text class="axis-title" x="${width / 2 - 92}" y="${height - 4}">${escapeHtml(xLabel)}</text>
    <text class="axis-title" transform="translate(14 ${height / 2 + 46}) rotate(-90)">Doc2MD score</text>
  </svg>`;
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
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 14px;
      margin: 26px 0 8px;
    }
    .metric {
      border-top: 3px solid var(--ink);
      padding: 12px 0 6px;
    }
    .metric strong {
      display: block;
      font: 700 28px/1.05 ui-sans-serif, system-ui, sans-serif;
      margin-bottom: 4px;
    }
    .metric span {
      display: block;
      color: var(--muted);
      font: 13px/1.35 ui-sans-serif, system-ui, sans-serif;
    }
    .figure {
      margin: 24px 0 30px;
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
      max-width: 760px;
      height: auto;
      display: block;
      background: #fffaf0;
    }
    svg text {
      font-family: ui-sans-serif, system-ui, sans-serif;
      font-size: 12px;
      fill: #1f2937;
    }
    svg .axis-title { fill: var(--muted); font-weight: 700; }
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
    .bar {
      display: inline-block;
      width: 82px;
      height: 6px;
      border: 1px solid #cbd5e1;
      margin-right: 8px;
      vertical-align: middle;
      background: white;
    }
    .bar > span {
      display: block;
      height: 100%;
      background: var(--accent);
    }
    .case-list {
      display: grid;
      grid-template-columns: 1fr;
      gap: 18px;
      margin-top: 20px;
    }
    .case {
      border-top: 1px solid var(--line);
      padding-top: 16px;
    }
    .case h3 {
      margin-top: 0;
      font-size: 18px;
    }
    .tags {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin: 8px 0 10px;
    }
    .tag {
      border: 1px solid #d1d5db;
      padding: 2px 6px;
      font: 11px/1.3 ui-sans-serif, system-ui, sans-serif;
      color: var(--muted);
      background: #fff;
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
      .summary-grid { grid-template-columns: 1fr 1fr; }
      table { font-size: 12px; }
    }
  </style>`;
}

function renderReport(manifest: Manifest, summaries: Summary[]) {
  const generatedAt = new Date();
  const bestScore = bestBy(summaries, (summary) => summary.score);
  const bestValue = bestBy(summaries, (summary) => (summary.costUsd > 0 ? summary.score / summary.costUsd : 0));
  const fastestPerPoint = bestBy(summaries, (summary) => (summary.totalElapsedMs > 0 ? summary.score / (summary.totalElapsedMs / 1000) : 0));
  const rows = caseRows(manifest, summaries);
  const scoreSpread = summaries.length >= 2 ? round(Math.max(...summaries.map((s) => s.score)) - Math.min(...summaries.map((s) => s.score))) : 0;
  const totalPages = manifest.pageCount ?? manifest.cases.reduce((sum, testCase) => sum + (testCase.pages ?? 1), 0);
  const sampleCount = summaries[0]?.samplesPerModelCase ?? 0;

  const modelTable = summaries
    .map(
      (summary) => `<tr>
        <td><strong>${escapeHtml(summary.modelId)}</strong></td>
        <td class="num">${bar(summary.score)}${summary.score}</td>
        <td class="num">${fmtMoney(summary.costUsd)}</td>
        <td class="num">${fmtSeconds(summary.totalElapsedMs)}</td>
        <td class="num">${summary.totalOutputTokens.toLocaleString()}</td>
        <td class="num">${summary.scoreStddevCaseMean}</td>
        <td class="num">${summary.sampleCount}</td>
      </tr>`,
    )
    .join("\n");

  const caseTableHeader = summaries.map((summary) => `<th class="num">${escapeHtml(modelLabel(summary.modelId))}</th>`).join("");
  const caseTableRows = rows
    .map((row) => {
      const scoreCells = row.scores
        .map((score) =>
          score
            ? `<td class="num">${score.score}<br><span class="muted">${score.scoreMin}-${score.scoreMax}, sd ${score.scoreStddev}</span></td>`
            : `<td class="num">-</td>`,
        )
        .join("");
      return `<tr>
        <td><a href="#${slug(row.testCase.id)}">${escapeHtml(row.testCase.id)}</a></td>
        <td>${escapeHtml(row.testCase.title)}</td>
        <td class="num">${row.testCase.pages}</td>
        ${scoreCells}
        <td class="num">${row.spread}</td>
      </tr>`;
    })
    .join("\n");

  const caseSections = rows
    .map((row) => {
      const scores = row.scores
        .map((score, index) => {
          const summary = summaries[index];
          if (!score) return "";
          return `<tr>
            <td>${escapeHtml(modelLabel(summary.modelId))}</td>
            <td class="num">${score.score}</td>
            <td class="num">${score.scoreMin}-${score.scoreMax}</td>
            <td class="num">${score.scoreStddev}</td>
            <td class="num">${score.accuracy}</td>
            <td class="num">${score.outputTokens.toLocaleString()}</td>
          </tr>`;
        })
        .join("");
      return `<section class="case" id="${slug(row.testCase.id)}">
        <h3>${escapeHtml(row.testCase.id)}: ${escapeHtml(row.testCase.title)}</h3>
        <div class="tags">${row.testCase.tags.map((tag) => `<span class="tag">${escapeHtml(tag)}</span>`).join("")}</div>
        <p>${escapeHtml(caseChallengeFallback[row.testCase.id] ?? "This case tests faithful reconstruction of dense document information into machine-usable Markdown.")}</p>
        <table>
          <thead><tr><th>Model</th><th class="num">Mean</th><th class="num">Range</th><th class="num">Stddev</th><th class="num">Accuracy</th><th class="num">Mean Output Tokens</th></tr></thead>
          <tbody>${scores}</tbody>
        </table>
      </section>`;
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
      <p class="lede">Doc2MD evaluates whether a model can turn a PDF into a single Markdown document that preserves the document's information, structure, tables, visual elements, and reading experience. This report is generated from cached benchmark outputs; regenerating the report does not rerun paid model or evaluator calls.</p>
      <div class="meta">
        <span>Generated ${escapeHtml(generatedAt.toLocaleString("en-US", { timeZone: "Asia/Kolkata" }))} IST</span>
        <span>${manifest.cases.length} cases</span>
        <span>${totalPages} pages</span>
        <span>${sampleCount} samples per model/case</span>
        <span>Input protocol: ${escapeHtml(manifest.inputProtocol ?? "native_pdf")}</span>
      </div>
    </header>

    <section>
      <h2>Highlights</h2>
      <div class="summary-grid">
        <div class="metric"><strong>${escapeHtml(bestScore ? modelLabel(bestScore.modelId) : "n/a")}</strong><span>highest average reconstruction score${bestScore ? ` (${bestScore.score})` : ""}</span></div>
        <div class="metric"><strong>${scoreSpread}</strong><span>point spread between best and weakest model</span></div>
        <div class="metric"><strong>${escapeHtml(bestValue ? modelLabel(bestValue.modelId) : "n/a")}</strong><span>best score per dollar in this run</span></div>
        <div class="metric"><strong>${escapeHtml(fastestPerPoint ? modelLabel(fastestPerPoint.modelId) : "n/a")}</strong><span>best score per sampled second</span></div>
      </div>
      <p>The key tradeoff is not just raw intelligence. A useful document conversion model must be accurate, economical, and predictable enough for repeated production use. The score measures reconstruction fidelity; cost, sampled latency, output length, and run-to-run variance describe whether that fidelity is practical.</p>
    </section>

    <section>
      <h2>Result Table</h2>
      <table>
        <thead>
          <tr><th>Model</th><th class="num">Score</th><th class="num">Cost</th><th class="num">Sampled Time</th><th class="num">Output Tokens</th><th class="num">Mean Case Stddev</th><th class="num">Samples</th></tr>
        </thead>
        <tbody>${modelTable}</tbody>
      </table>
      <p class="note">Scores are averaged across ${sampleCount} runs per model/case and then page-weighted across cases. Cost and time are totals across all samples in this report, not the wall-clock time of a parallel run.</p>
    </section>

    <section>
      <h2>Intelligence, Cost, And Time</h2>
      <div class="figure">
        <div class="figure-title">Figure 1. Reconstruction score versus benchmark cost</div>
        ${scatterSvg(summaries, "cost")}
        <div class="caption">A model on the upper-left is preferable: higher fidelity at lower cost. This view highlights whether accuracy gains are economically meaningful.</div>
      </div>
      <div class="figure">
        <div class="figure-title">Figure 2. Reconstruction score versus sampled model time</div>
        ${scatterSvg(summaries, "time")}
        <div class="caption">Time is the sum of reported sample durations. The benchmark executes in parallel, but summed model time is still useful for comparing latency burden.</div>
      </div>
    </section>

    <section>
      <h2>Method</h2>
      <p>The benchmark sends native PDF files directly to providers and asks for one faithful Markdown reconstruction. It does not convert official inputs into page images inside the harness. This means the score reflects the end-to-end provider experience: the model, the provider's PDF ingestion path, and the model's ability to preserve document information.</p>
      <p>Each case has a human-authored gold answer key and weighted fact obligations. The evaluator compares the candidate Markdown against that answer key and marks facts as correct, partial, missing, or incorrect. Wrong information is penalized more harshly than omission because downstream systems can often detect missing information, but wrong extracted facts silently corrupt later reasoning.</p>
      <p>The report is deterministic. It reads existing <code>summary.json</code> files, recomputes no model outputs, calls no judge, and writes a fresh HTML page every time the benchmark command completes.</p>
    </section>

    <section>
      <h2>Case-Level Separation</h2>
      <table>
        <thead>
          <tr><th>Case</th><th>Document</th><th class="num">Pages</th>${caseTableHeader}<th class="num">Spread</th></tr>
        </thead>
        <tbody>${caseTableRows}</tbody>
      </table>
      <p>Cases with high spread are currently doing the most leaderboard work. Cases where all models score near 100 are still useful as capability or regression checks, but they contribute less to ranking strong and weak document parsers.</p>
    </section>

    <section>
      <h2>What The Cases Test</h2>
      <div class="case-list">${caseSections}</div>
    </section>

    <section>
      <h2>Interpretation</h2>
      <p>Doc2MD is intentionally not a plain OCR benchmark. The hard cases stress compound document reconstruction: page order, table continuation, chart semantics, source-state conflicts, maps, forms, lab panels, regulated release decisions, and dense operational packets. The main failure mode for weaker models is not merely reading text incorrectly; it is dropping whole regions, collapsing structured tables into prose, binding values to the wrong labels, or inventing a plausible but false final state.</p>
      <p>Because LLM outputs are not precision instruments, the benchmark uses repeated samples. The reported score should be read as an estimate of expected reconstruction quality, while the per-case range and standard deviation show reliability. A model that sometimes solves a case and sometimes omits entire sections is less production-worthy than a model with the same mean score and tighter variance.</p>
    </section>
  </main>
</body>
</html>`;
}

export async function generateReport(summaries?: Summary[], options: { outPath?: string; manifestPath?: string } = {}) {
  const manifestPath = options.manifestPath ?? "benchmark/manifest.json";
  const outPath = options.outPath ?? "reports/index.html";
  const manifest = await readJson<Manifest>(manifestPath);
  const loadedSummaries = summaries ?? (await loadSummaries());
  if (loadedSummaries.length === 0) {
    throw new Error("No benchmark summaries found. Run the benchmark before generating the report.");
  }
  await mkdir(path.dirname(outPath), { recursive: true });
  const html = renderReport(manifest, loadedSummaries);
  await writeFile(outPath, html, "utf-8");
  return { outPath, summaries: loadedSummaries.length };
}

function parseArgs() {
  const args = new Map<string, string>();
  for (let i = 2; i < process.argv.length; i += 1) {
    const arg = process.argv[i];
    if (!arg.startsWith("--")) continue;
    const key = arg.slice(2);
    const next = process.argv[i + 1];
    args.set(key, next && !next.startsWith("--") ? process.argv[++i] : "true");
  }
  return args;
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const args = parseArgs();
  const result = await generateReport(undefined, {
    outPath: args.get("out"),
    manifestPath: args.get("manifest"),
  });
  console.log(`Wrote ${result.outPath} from ${result.summaries} model summaries`);
}
