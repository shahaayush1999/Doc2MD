import { mkdir, readFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { fileSha256 } from "./cache.js";
import { atomicWriteJson, atomicWriteText } from "./runRuntime.js";

const evidenceDirectory = "docs/results/anchor-repeat-validation-2026-07-10";
const firstSnapshotPath = path.join(evidenceDirectory, "draw-001.snapshot.json");
const repeatSnapshotPath = path.join(evidenceDirectory, "draw-002.snapshot.json");
const analysisPath = path.join(evidenceDirectory, "analysis.json");
const reportPath = path.join(evidenceDirectory, "report.html");

function mean(values: number[]) {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function sampleStddev(values: number[]) {
  if (values.length < 2) return null;
  const average = mean(values);
  return Math.sqrt(values.reduce((sum, value) => sum + (value - average) ** 2, 0) / (values.length - 1));
}

function escapeHtml(value: unknown) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function metric(display: string, source: string) {
  const escapedSource = escapeHtml(source);
  return `<span class="sourced-number" tabindex="0" title="${escapedSource}" data-source="${escapedSource}">${escapeHtml(display)}</span>`;
}

function score(value: number, source: string) {
  return metric(value.toFixed(2), source);
}

function signedScore(value: number, source: string) {
  return metric(`${value >= 0 ? "+" : ""}${value.toFixed(2)}`, source);
}

function money(value: number, source: string) {
  return metric(`$${value.toFixed(6)}`, source);
}

async function readJson(filePath: string) {
  return JSON.parse(await readFile(filePath, "utf-8")) as any;
}

function buildAnalysis(first: any, repeat: any, sourceHashes: Record<string, string>) {
  if (first.benchmark.caseCount !== repeat.benchmark.caseCount) throw new Error("Draw snapshots use different case counts.");
  if (JSON.stringify(first.benchmark.modelIds) !== JSON.stringify(repeat.benchmark.modelIds)) {
    throw new Error("Draw snapshots use different model cohorts.");
  }

  const models = first.models.map((firstModel: any) => {
    const repeatModel = repeat.models.find((candidate: any) => candidate.modelId === firstModel.modelId);
    if (!repeatModel) throw new Error(`Repeat snapshot is missing ${firstModel.modelId}.`);
    const caseComparisons = firstModel.cases.map((firstCase: any) => {
      const repeatCase = repeatModel.cases.find((candidate: any) => candidate.caseId === firstCase.caseId);
      if (!repeatCase) throw new Error(`Repeat snapshot is missing ${firstModel.modelId} ${firstCase.caseId}.`);
      return {
        caseId: firstCase.caseId,
        title: firstCase.title,
        firstScore: firstCase.score,
        repeatScore: repeatCase.score,
        delta: repeatCase.score - firstCase.score,
        absoluteDelta: Math.abs(repeatCase.score - firstCase.score),
      };
    });
    const scores = [firstModel.exactSuiteScore, repeatModel.exactSuiteScore];
    return {
      modelId: firstModel.modelId,
      suite: {
        firstScore: scores[0],
        repeatScore: scores[1],
        delta: scores[1] - scores[0],
        mean: mean(scores),
        sampleStddev: sampleStddev(scores),
        minimum: Math.min(...scores),
        maximum: Math.max(...scores),
        observedRange: Math.max(...scores) - Math.min(...scores),
      },
      spend: {
        first: {
          inferenceCostUsd: firstModel.inferenceCostUsd,
          evaluatorCostUsd: firstModel.evaluatorCostUsd,
          totalMeasuredCostUsd: firstModel.totalMeasuredCostUsd,
        },
        repeat: {
          inferenceCostUsd: repeatModel.inferenceCostUsd,
          evaluatorCostUsd: repeatModel.evaluatorCostUsd,
          totalMeasuredCostUsd: repeatModel.totalMeasuredCostUsd,
        },
        cumulative: {
          inferenceCostUsd: firstModel.inferenceCostUsd + repeatModel.inferenceCostUsd,
          evaluatorCostUsd: firstModel.evaluatorCostUsd + repeatModel.evaluatorCostUsd,
          totalMeasuredCostUsd: firstModel.totalMeasuredCostUsd + repeatModel.totalMeasuredCostUsd,
        },
      },
      cases: caseComparisons,
    };
  });

  const firstGap = first.comparison.exactScoreGap;
  const repeatGap = repeat.comparison.exactScoreGap;
  const spend = {
    first: {
      inferenceCostUsd: first.comparison.inferenceCostUsd,
      evaluatorCostUsd: first.comparison.evaluatorCostUsd,
      totalMeasuredCostUsd: first.comparison.totalMeasuredCostUsd,
    },
    repeat: {
      inferenceCostUsd: repeat.comparison.inferenceCostUsd,
      evaluatorCostUsd: repeat.comparison.evaluatorCostUsd,
      totalMeasuredCostUsd: repeat.comparison.totalMeasuredCostUsd,
    },
    cumulative: {
      inferenceCostUsd: first.comparison.inferenceCostUsd + repeat.comparison.inferenceCostUsd,
      evaluatorCostUsd: first.comparison.evaluatorCostUsd + repeat.comparison.evaluatorCostUsd,
      totalMeasuredCostUsd: first.comparison.totalMeasuredCostUsd + repeat.comparison.totalMeasuredCostUsd,
    },
  };

  return {
    schemaVersion: 1,
    kind: "doc2md_anchor_two_draw_validation_analysis",
    generatedAt: new Date().toISOString(),
    sources: {
      firstSnapshot: { path: firstSnapshotPath, sha256: sourceHashes.first },
      repeatSnapshot: { path: repeatSnapshotPath, sha256: sourceHashes.repeat },
      firstCapturedAt: first.capturedAt,
      repeatCapturedAt: repeat.capturedAt,
      firstSourceGitCommit: first.sourceGitCommit,
      repeatSourceGitCommit: repeat.sourceGitCommit,
    },
    scope: {
      modelIds: first.benchmark.modelIds,
      caseCount: first.benchmark.caseCount,
      observationsPerModelCase: 2,
      logicalInferenceCallsPerDraw: first.benchmark.caseCount * first.benchmark.modelIds.length,
      repeatSample: repeat.benchmark.sample,
    },
    integrity: {
      repeatLogicalInferenceCalls: repeat.models.reduce(
        (sum: number, model: any) => sum + model.cases.reduce((caseSum: number, testCase: any) => caseSum + testCase.inference.logicalGenerationCalls, 0),
        0,
      ),
      repeatTransportRequestAttempts: repeat.models.reduce(
        (sum: number, model: any) => sum + model.cases.reduce((caseSum: number, testCase: any) => caseSum + testCase.inference.transportRequestAttempts, 0),
        0,
      ),
      repeatTransportRetries: repeat.models.reduce(
        (sum: number, model: any) =>
          sum + model.cases.reduce((caseSum: number, testCase: any) => caseSum + testCase.inference.transportRequestAttempts - 1, 0),
        0,
      ),
      repeatValidEvaluatorJudgments: repeat.models.reduce(
        (sum: number, model: any) => sum + model.cases.filter((testCase: any) => testCase.evaluator.status === "valid").length,
        0,
      ),
      repeatEvaluatorAttempts: repeat.models.reduce(
        (sum: number, model: any) => sum + model.cases.reduce((caseSum: number, testCase: any) => caseSum + testCase.evaluator.attempts, 0),
        0,
      ),
      repeatJudgeReuses: repeat.models.reduce(
        (sum: number, model: any) => sum + model.cases.filter((testCase: any) => testCase.evaluator.judgeReused).length,
        0,
      ),
      repeatAuthorizationHashes: [
        ...new Set(
          repeat.models.flatMap((model: any) => model.cases.map((testCase: any) => testCase.inference.authorizationHash)),
        ),
      ],
      repeatRunModes: [...new Set(repeat.models.flatMap((model: any) => model.cases.map((testCase: any) => testCase.inference.runMode)))],
    },
    gap: {
      first: firstGap,
      repeat: repeatGap,
      delta: repeatGap - firstGap,
      mean: mean([firstGap, repeatGap]),
      sampleStddev: sampleStddev([firstGap, repeatGap]),
      minimum: Math.min(firstGap, repeatGap),
      maximum: Math.max(firstGap, repeatGap),
      observedRange: Math.abs(repeatGap - firstGap),
    },
    spend,
    evaluatorShareOfRepeatSpend: spend.repeat.evaluatorCostUsd / spend.repeat.totalMeasuredCostUsd,
    evaluatorShareOfCumulativeSpend: spend.cumulative.evaluatorCostUsd / spend.cumulative.totalMeasuredCostUsd,
    models,
    interpretation: {
      result: "The large good-versus-bad anchor separation replicated across both observed draws.",
      uncertainty:
        "Two observations are insufficient to estimate a stable score distribution. The reported sample SD and range describe only these two draws.",
      attribution:
        "Each repeat used both a fresh model generation and a fresh evaluator judgment, so score movement combines generation and evaluator stochasticity.",
    },
  };
}

function buildHtml(analysis: any) {
  const nano = analysis.models.find((model: any) => model.modelId === "openai-gpt-5-nano");
  const gemini = analysis.models.find((model: any) => model.modelId === "vertex-gemini-3.1-flash-lite");
  const largestCase = analysis.models
    .flatMap((model: any) => model.cases.map((testCase: any) => ({ modelId: model.modelId, ...testCase })))
    .sort((a: any, b: any) => b.absoluteDelta - a.absoluteDelta)[0];
  const source = (path: string) => `analysis.json → ${path}`;

  const modelRows = analysis.models
    .map(
      (model: any, index: number) => `<tr>
        <th scope="row">${escapeHtml(model.modelId)}</th>
        <td>${score(model.suite.firstScore, source(`models[${index}].suite.firstScore`))}</td>
        <td>${score(model.suite.repeatScore, source(`models[${index}].suite.repeatScore`))}</td>
        <td class="${model.suite.delta >= 0 ? "positive" : "negative"}">${signedScore(model.suite.delta, source(`models[${index}].suite.delta`))}</td>
        <td>${score(model.suite.mean, source(`models[${index}].suite.mean`))}</td>
        <td>${score(model.suite.sampleStddev, source(`models[${index}].suite.sampleStddev`))}</td>
        <td>${score(model.suite.observedRange, source(`models[${index}].suite.observedRange`))}</td>
      </tr>`,
    )
    .join("");

  const caseRows = analysis.models
    .flatMap((model: any, modelIndex: number) =>
      model.cases.map(
        (testCase: any, caseIndex: number) => `<tr>
          <th scope="row">${escapeHtml(model.modelId)}</th>
          <td><span class="case-id">${escapeHtml(testCase.caseId)}</span><span class="case-title">${escapeHtml(testCase.title)}</span></td>
          <td>${score(testCase.firstScore, source(`models[${modelIndex}].cases[${caseIndex}].firstScore`))}</td>
          <td>${score(testCase.repeatScore, source(`models[${modelIndex}].cases[${caseIndex}].repeatScore`))}</td>
          <td class="${testCase.delta >= 0 ? "positive" : "negative"}">${signedScore(testCase.delta, source(`models[${modelIndex}].cases[${caseIndex}].delta`))}</td>
        </tr>`,
      ),
    )
    .join("");

  const spendRows = (["first", "repeat", "cumulative"] as const)
    .map((key) => {
      const label = key === "first" ? "First draw" : key === "repeat" ? "Repeat draw" : "Cumulative evidence";
      return `<tr>
        <th scope="row">${label}</th>
        <td>${money(analysis.spend[key].inferenceCostUsd, source(`spend.${key}.inferenceCostUsd`))}</td>
        <td>${money(analysis.spend[key].evaluatorCostUsd, source(`spend.${key}.evaluatorCostUsd`))}</td>
        <td>${money(analysis.spend[key].totalMeasuredCostUsd, source(`spend.${key}.totalMeasuredCostUsd`))}</td>
      </tr>`;
    })
    .join("");

  return `<!doctype html>
<html lang="en" data-report-audience="technical">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Doc2MD anchor repeat-validation audit</title>
  <style>
    :root { --ink:#17211c; --muted:#66706b; --paper:#f5f3ed; --panel:#fffdf8; --line:#d8d6ce; --green:#0f6b46; --green-soft:#e4f1e9; --amber:#946a17; --amber-soft:#f8efd8; --red:#a03e3e; }
    * { box-sizing:border-box; }
    body { margin:0; color:var(--ink); background:var(--paper); font:15px/1.55 ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    main { max-width:1180px; margin:0 auto; padding:64px 28px 96px; }
    header { border-bottom:1px solid var(--line); padding-bottom:34px; margin-bottom:28px; }
    .eyebrow { color:var(--green); font-size:12px; font-weight:800; letter-spacing:.14em; text-transform:uppercase; }
    h1 { margin:10px 0 12px; max-width:900px; font:700 clamp(36px,6vw,68px)/1.02 Georgia, serif; letter-spacing:-.035em; }
    .lede { max-width:820px; color:var(--muted); font-size:18px; }
    .status { display:inline-flex; align-items:center; gap:8px; margin-top:18px; padding:8px 12px; border:1px solid #b9d4c4; background:var(--green-soft); color:var(--green); border-radius:999px; font-weight:750; }
    .status::before { content:""; width:8px; height:8px; background:var(--green); border-radius:50%; }
    section { margin-top:44px; }
    h2 { font:700 27px/1.2 Georgia, serif; margin:0 0 14px; }
    h3 { font-size:15px; text-transform:uppercase; letter-spacing:.08em; margin:0 0 8px; }
    p { max-width:900px; }
    .cards { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; margin-top:20px; }
    .card { background:var(--panel); border:1px solid var(--line); border-radius:14px; padding:20px; }
    .card .label { color:var(--muted); font-size:12px; font-weight:800; letter-spacing:.08em; text-transform:uppercase; }
    .card .value { margin-top:8px; font:700 32px/1 Georgia,serif; }
    .card .note { color:var(--muted); font-size:13px; margin-top:8px; }
    .callout { border-left:4px solid var(--amber); background:var(--amber-soft); padding:16px 18px; margin:20px 0; max-width:940px; }
    .table-wrap { overflow-x:auto; background:var(--panel); border:1px solid var(--line); border-radius:14px; }
    table { width:100%; border-collapse:collapse; min-width:780px; }
    th, td { padding:13px 14px; text-align:right; border-bottom:1px solid var(--line); vertical-align:top; }
    thead th { color:var(--muted); background:#f0eee7; font-size:12px; letter-spacing:.04em; text-transform:uppercase; }
    th:first-child, td:first-child, .case-table td:nth-child(2), .case-table th:nth-child(2) { text-align:left; }
    tbody tr:last-child th, tbody tr:last-child td { border-bottom:0; }
    .case-id { display:block; font-weight:750; }
    .case-title { display:block; color:var(--muted); font-size:12px; max-width:360px; }
    .positive { color:var(--green); font-weight:750; }
    .negative { color:var(--red); font-weight:750; }
    .sourced-number { position:relative; border-bottom:1px dotted currentColor; cursor:help; white-space:nowrap; }
    .sourced-number:focus { outline:2px solid var(--green); outline-offset:3px; border-radius:2px; }
    .sourced-number:hover::after, .sourced-number:focus::after { content:attr(data-source); position:absolute; z-index:10; left:50%; bottom:calc(100% + 9px); transform:translateX(-50%); width:max-content; max-width:340px; padding:8px 10px; color:white; background:#17211c; border-radius:7px; font:11px/1.35 ui-monospace,SFMono-Regular,Menlo,monospace; box-shadow:0 8px 24px #0002; white-space:normal; }
    .two-col { display:grid; grid-template-columns:1fr 1fr; gap:16px; }
    ul { padding-left:20px; max-width:900px; }
    li + li { margin-top:8px; }
    code { font-family:ui-monospace,SFMono-Regular,Menlo,monospace; font-size:.9em; }
    footer { margin-top:56px; padding-top:20px; border-top:1px solid var(--line); color:var(--muted); font-size:12px; }
    @media (max-width:800px) { main{padding:38px 18px 70px}.cards,.two-col{grid-template-columns:1fr}h1{font-size:42px}.card .value{font-size:28px} }
    @media print { body{background:white}.sourced-number{border-bottom:0}.sourced-number::after{display:none!important}main{max-width:none;padding:24px}.card,.table-wrap{break-inside:avoid} }
  </style>
</head>
<body>
<main>
  <header>
    <div class="eyebrow">Doc2MD benchmark evidence</div>
    <h1>Anchor repeat-validation audit</h1>
    <p class="lede">A non-destructive, explicitly authorized second observation of the two cheapest anchor models across the same five-case native-PDF suite.</p>
    <div class="status">Large anchor separation replicated</div>
  </header>

  <section id="technical-summary" data-report-section="technical-summary">
    <h2>Technical summary</h2>
    <p>The first-draw good-versus-bad anchor gap was ${score(analysis.gap.first, source("gap.first"))} points; the repeat gap was ${score(analysis.gap.repeat, source("gap.repeat"))}. The gap changed by only ${signedScore(analysis.gap.delta, source("gap.delta"))} points and remained near thirty points in both observations. This is strong evidence that the redesigned suite is differentiating these two anchors, but it is not a reliability estimate.</p>
    <div class="cards">
      <article class="card"><div class="label">First anchor gap</div><div class="value">${score(analysis.gap.first, source("gap.first"))}</div><div class="note">Gemini minus GPT‑5 Nano</div></article>
      <article class="card"><div class="label">Repeat anchor gap</div><div class="value">${score(analysis.gap.repeat, source("gap.repeat"))}</div><div class="note">Gemini minus GPT‑5 Nano</div></article>
      <article class="card"><div class="label">Repeat-run spend</div><div class="value">${money(analysis.spend.repeat.totalMeasuredCostUsd, source("spend.repeat.totalMeasuredCostUsd"))}</div><div class="note">Inference plus evaluator</div></article>
    </div>
  </section>

  <section id="key-findings" data-report-section="key-findings">
    <h2>Key findings</h2>
    <ul>
      <li>GPT‑5 Nano moved from ${score(nano.suite.firstScore, source("models[0].suite.firstScore"))} to ${score(nano.suite.repeatScore, source("models[0].suite.repeatScore"))}, a ${signedScore(nano.suite.delta, source("models[0].suite.delta"))}-point change.</li>
      <li>Gemini 3.1 Flash‑Lite moved from ${score(gemini.suite.firstScore, source("models[1].suite.firstScore"))} to ${score(gemini.suite.repeatScore, source("models[1].suite.repeatScore"))}, a ${signedScore(gemini.suite.delta, source("models[1].suite.delta"))}-point change.</li>
      <li>The largest case movement was ${escapeHtml(largestCase.modelId)} on ${escapeHtml(largestCase.caseId)}: ${signedScore(largestCase.delta, "analysis.json → largest absolute case delta derived from models[].cases[]")} points. That single case explains most of Gemini's suite movement.</li>
      <li>The repeat used ${metric(String(analysis.integrity.repeatLogicalInferenceCalls), source("integrity.repeatLogicalInferenceCalls"))} logical model calls and ${metric(String(analysis.integrity.repeatTransportRequestAttempts), source("integrity.repeatTransportRequestAttempts"))} transport attempts, so there were ${metric(String(analysis.integrity.repeatTransportRetries), source("integrity.repeatTransportRetries"))} model transport retries.</li>
    </ul>
  </section>

  <section id="score-comparison" data-report-section="results">
    <h2>Suite score comparison</h2>
    <div class="table-wrap"><table>
      <thead><tr><th scope="col">Model</th><th scope="col">First draw</th><th scope="col">Repeat draw</th><th scope="col">Change</th><th scope="col">Two-draw mean</th><th scope="col">Sample SD</th><th scope="col">Observed range</th></tr></thead>
      <tbody>${modelRows}</tbody>
    </table></div>
    <div class="callout"><strong>Do not over-read the SD.</strong> With only ${metric(String(analysis.scope.observationsPerModelCase), source("scope.observationsPerModelCase"))} observations per model/case, sample SD is mathematically defined but statistically unstable. It describes these two draws only.</div>
  </section>

  <section id="case-comparison" data-report-section="case-results">
    <h2>Per-case movement</h2>
    <div class="table-wrap"><table class="case-table">
      <thead><tr><th scope="col">Model</th><th scope="col">Case</th><th scope="col">First</th><th scope="col">Repeat</th><th scope="col">Change</th></tr></thead>
      <tbody>${caseRows}</tbody>
    </table></div>
    <p><strong>Why there is no chart:</strong> an exact table is more honest for two observations. A distribution chart would visually imply more repeatability evidence than exists.</p>
  </section>

  <section id="spend" data-report-section="spend">
    <h2>Measured spend</h2>
    <div class="table-wrap"><table>
      <thead><tr><th scope="col">Evidence cohort</th><th scope="col">Model inference</th><th scope="col">Evaluator</th><th scope="col">Total</th></tr></thead>
      <tbody>${spendRows}</tbody>
    </table></div>
    <p>The evaluator accounted for ${metric(`${(analysis.evaluatorShareOfRepeatSpend * 100).toFixed(1)}%`, source("evaluatorShareOfRepeatSpend"))} of repeat-run spend. All values are usage-derived estimates recorded in provider result artifacts; they are not invoice reconciliation.</p>
  </section>

  <section id="data-contract-section" data-report-section="data-contract" data-report-audience="technical">
    <h2>Scope, data, and metric definitions</h2>
    <div class="two-col">
      <article class="card"><h3>Unit of analysis</h3><p>One model-generated Markdown reconstruction for one case and one sample slot. Each suite score is the equal-weight mean across ${metric(String(analysis.scope.caseCount), source("scope.caseCount"))} cases.</p></article>
      <article class="card"><h3>Comparison</h3><p>The anchor gap is Gemini 3.1 Flash‑Lite score minus GPT‑5 Nano score within the same draw slot. Positive values favor Gemini.</p></article>
      <article class="card"><h3>Cost</h3><p>Inference cost and evaluator cost are reported separately, then summed. No human labor or infrastructure cost is included.</p></article>
      <article class="card"><h3>Preservation</h3><p>Both snapshots contain exact scores, usage, costs, cache identities, and hashes of the underlying ignored run artifacts. Source snapshot hashes are recorded in <code>analysis.json</code>.</p></article>
    </div>
  </section>

  <section id="methodology" data-report-section="methodology">
    <h2>Methodology and integrity checks</h2>
    <ol>
      <li>Captured and pushed draw one before any repeat call.</li>
      <li>Reserved immutable sample slot <code>002</code> under one authorization hash and forbade replacement of <code>001</code>.</li>
      <li>Ran the same prompt, PDFs, model configurations, inference protocol, and scoring contract.</li>
      <li>Used a fresh evaluator judgment for every repeat output: ${metric(String(analysis.integrity.repeatValidEvaluatorJudgments), source("integrity.repeatValidEvaluatorJudgments"))} valid judgments, ${metric(String(analysis.integrity.repeatEvaluatorAttempts), source("integrity.repeatEvaluatorAttempts"))} attempts, and ${metric(String(analysis.integrity.repeatJudgeReuses), source("integrity.repeatJudgeReuses"))} cached judgment reuses.</li>
      <li>Computed each draw's suite score case-first with equal case weight, then compared the two complete draw slots.</li>
    </ol>
  </section>

  <section id="limitations" data-report-section="limitations">
    <h2>Limitations, uncertainty, and robustness</h2>
    <ul>
      <li>Two draws are a sensitivity check, not a stable variance estimate or confidence interval.</li>
      <li>Fresh generation and fresh evaluator judgment were both stochastic, so observed deltas cannot be attributed to generation alone.</li>
      <li>The two anchors establish local differentiation, not a calibrated ranking across the broader model market.</li>
      <li>The official development summary intentionally remains one-draw; this report is a separate validation artifact.</li>
      <li>The robust result is the replicated large gap. The less robust result is the exact score level, especially on the long clinical packet.</li>
    </ul>
  </section>

  <section id="recommendations" data-report-section="recommendations">
    <h2>Recommended next steps</h2>
    <ul>
      <li>Keep one draw as the normal iteration default and retain this repeat checkpoint as a variance warning, not as a new multi-run benchmark default.</li>
      <li>When the suite is frozen, use a small predeclared repeat cohort only for release validation and report intervals without false precision.</li>
      <li>Audit the long clinical case's evaluator stability before attributing its large Gemini movement entirely to model behavior.</li>
      <li>Continue improving cases where both anchors are high or move together; preserve cases where the score gap reflects real document-processing utility.</li>
    </ul>
  </section>

  <section id="further-questions" data-report-section="further-questions">
    <h2>Further questions</h2>
    <ul>
      <li>How much of the clinical-case movement survives deterministic replay of each stored evaluator judgment?</li>
      <li>Does the same large separation persist for a stronger, still-affordable good anchor without saturating the suite?</li>
      <li>Which capability axes contribute most consistently to the anchor gap across future frozen checkpoints?</li>
    </ul>
  </section>

  <footer>Generated from hash-bound local snapshots. Hover or focus any dotted numeric value to see its exact source field. Machine-readable analysis: <code>analysis.json</code>.</footer>
</main>
</body>
</html>`;
}

export async function buildRepeatValidationReport() {
  const [first, repeat, firstHash, repeatHash] = await Promise.all([
    readJson(firstSnapshotPath),
    readJson(repeatSnapshotPath),
    fileSha256(firstSnapshotPath),
    fileSha256(repeatSnapshotPath),
  ]);
  const analysis = buildAnalysis(first, repeat, { first: firstHash, repeat: repeatHash });
  if (
    analysis.integrity.repeatLogicalInferenceCalls !== analysis.scope.logicalInferenceCallsPerDraw ||
    analysis.integrity.repeatTransportRequestAttempts !== analysis.scope.logicalInferenceCallsPerDraw ||
    analysis.integrity.repeatTransportRetries !== 0 ||
    analysis.integrity.repeatValidEvaluatorJudgments !== analysis.scope.logicalInferenceCallsPerDraw ||
    analysis.integrity.repeatEvaluatorAttempts !== analysis.scope.logicalInferenceCallsPerDraw ||
    analysis.integrity.repeatJudgeReuses !== 0 ||
    analysis.integrity.repeatAuthorizationHashes.length !== 1 ||
    analysis.integrity.repeatRunModes.length !== 1 ||
    analysis.integrity.repeatRunModes[0] !== "repeat_validation"
  ) {
    throw new Error("Repeat-validation integrity checks failed; refusing to publish the report.");
  }
  await mkdir(evidenceDirectory, { recursive: true });
  await atomicWriteJson(analysisPath, analysis);
  await atomicWriteText(reportPath, buildHtml(analysis));
  console.log(`Analysis written to ${analysisPath}`);
  console.log(`Report written to ${reportPath}`);
  return { analysisPath, reportPath, analysis };
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  await buildRepeatValidationReport();
}
