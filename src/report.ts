const palette = ["#1f4b99", "#c18b2e", "#858b94", "#7c5aa6", "#3d7a68"];

function escapeHtml(value: unknown) {
  return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}

function label(modelId: string) {
  return modelId.replace(/^vertex-/, "").replace(/^openai-/, "");
}

function money(value: number) {
  return `$${value.toFixed(4)}`;
}

function scoreChart(models: any[]) {
  const width = 1040;
  const left = 285;
  const plotWidth = 650;
  const height = 86 + models.length * 76;
  const grid = [0, 25, 50, 75, 100]
    .map((tick) => {
      const x = left + (tick / 100) * plotWidth;
      return `<line x1="${x}" y1="50" x2="${x}" y2="${height - 36}" stroke="#dedbd2"/><text x="${x}" y="34" text-anchor="middle" class="tick">${tick}</text>`;
    })
    .join("");
  const bars = models
    .map((model, index) => {
      const y = 70 + index * 76;
      const barWidth = (model.score / 100) * plotWidth;
      return `<text x="${left - 18}" y="${y + 27}" text-anchor="end" class="model-label">${escapeHtml(label(model.modelId))}</text>
      <rect x="${left}" y="${y}" width="${plotWidth}" height="38" rx="5" fill="#ebe9e2"/>
      <rect x="${left}" y="${y}" width="${barWidth}" height="38" rx="5" fill="${palette[index]}"/>
      <text x="${Math.min(left + barWidth + 12, width - 48)}" y="${y + 27}" class="value">${model.score.toFixed(1)}</text>`;
    })
    .join("");
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Overall Doc2MD score by model">${grid}${bars}</svg>`;
}

function caseChart(models: any[]) {
  const width = 1100;
  const height = 570;
  const top = 70;
  const bottom = 470;
  const left = 80;
  const plotWidth = 960;
  const cases = models[0]?.cases ?? [];
  const groupWidth = plotWidth / cases.length;
  const barWidth = Math.min(42, (groupWidth - 30) / models.length);
  const grid = [0, 25, 50, 75, 100]
    .map((tick) => {
      const y = bottom - (tick / 100) * (bottom - top);
      return `<line x1="${left}" y1="${y}" x2="${left + plotWidth}" y2="${y}" stroke="#dedbd2"/><text x="${left - 12}" y="${y + 5}" text-anchor="end" class="tick">${tick}</text>`;
    })
    .join("");
  const bars = cases
    .map((testCase: any, caseIndex: number) => {
      const groupStart = left + caseIndex * groupWidth + (groupWidth - barWidth * models.length) / 2;
      const marks = models
        .map((model, modelIndex) => {
          const value = model.cases[caseIndex].score;
          const barHeight = (value / 100) * (bottom - top);
          const x = groupStart + modelIndex * barWidth;
          const y = bottom - barHeight;
          return `<rect x="${x}" y="${y}" width="${barWidth - 5}" height="${barHeight}" rx="3" fill="${palette[modelIndex]}"/><text x="${x + (barWidth - 5) / 2}" y="${Math.max(y - 7, 58)}" text-anchor="middle" class="bar-value">${value.toFixed(0)}</text>`;
        })
        .join("");
      return `${marks}<text x="${left + caseIndex * groupWidth + groupWidth / 2}" y="${bottom + 30}" text-anchor="middle" class="case-label">${escapeHtml(testCase.caseId.split("-")[0])}</text>`;
    })
    .join("");
  const legend = models
    .map((model, index) => `<g transform="translate(${left + index * 280},18)"><rect width="16" height="16" rx="3" fill="${palette[index]}"/><text x="24" y="14" class="legend">${escapeHtml(label(model.modelId))}</text></g>`)
    .join("");
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Per-case scores grouped by model">${legend}${grid}${bars}</svg>`;
}

function spendChart(models: any[]) {
  const width = 1040;
  const left = 285;
  const plotWidth = 600;
  const height = 80 + models.length * 74;
  const maximum = Math.max(...models.map((model) => model.inferenceCostUsd));
  const rows = models
    .map((model, index) => {
      const y = 58 + index * 74;
      const inferenceWidth = (model.inferenceCostUsd / maximum) * plotWidth;
      return `<text x="${left - 18}" y="${y + 25}" text-anchor="end" class="model-label">${escapeHtml(label(model.modelId))}</text>
      <rect x="${left}" y="${y}" width="${inferenceWidth}" height="34" rx="4" fill="${palette[index]}"/>
      <text x="${left + inferenceWidth + 12}" y="${y + 24}" class="value">${money(model.inferenceCostUsd)}</text>`;
    })
    .join("");
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Measured model inference spend"><g transform="translate(${left},18)"><rect width="16" height="16" rx="3" fill="#1f4b99"/><text x="24" y="14" class="legend">Model inference</text></g>${rows}</svg>`;
}

function scatterChart(
  models: any[],
  options: { metric: "inferenceCostUsd" | "inferenceSeconds" | "totalOutputTokens"; xLabel: string; format: (value: number) => string; log?: boolean },
) {
  const width = 920;
  const height = 430;
  const left = 92;
  const right = 185;
  const top = 38;
  const bottom = 340;
  const plotWidth = width - left - right;
  const values = models.map((model) => model[options.metric] as number);
  const maximum = Math.max(...values);
  const minimum = options.log ? Math.min(...values.filter((value) => value > 0)) : 0;
  const transformed = (value: number) => {
    if (options.log) {
      const low = Math.log10(minimum);
      const high = Math.log10(maximum);
      return high === low ? 0.5 : (Math.log10(value) - low) / (high - low);
    }
    return maximum === 0 ? 0 : value / maximum;
  };
  const xTicks = options.log
    ? [minimum, Math.sqrt(minimum * maximum), maximum]
    : [0, maximum / 3, (maximum * 2) / 3, maximum];
  const grid = [0, 25, 50, 75, 100]
    .map((tick) => {
      const y = bottom - (tick / 100) * (bottom - top);
      return `<line x1="${left}" y1="${y}" x2="${left + plotWidth}" y2="${y}" stroke="#dedbd2"/><text x="${left - 12}" y="${y + 5}" text-anchor="end" class="tick">${tick}</text>`;
    })
    .join("");
  const xAxis = xTicks
    .map((tick) => {
      const x = left + transformed(tick || minimum) * plotWidth;
      return `<line x1="${x}" y1="${bottom}" x2="${x}" y2="${bottom + 7}" stroke="#858b94"/><text x="${x}" y="${bottom + 26}" text-anchor="middle" class="tick">${escapeHtml(options.format(tick))}</text>`;
    })
    .join("");
  const points = models
    .map((model, index) => {
      const x = left + transformed(model[options.metric]) * plotWidth;
      const y = bottom - (model.score / 100) * (bottom - top);
      const labelY = y + (index === 1 ? 22 : -12);
      return `<line x1="${x}" y1="${y}" x2="${x + 18}" y2="${labelY - 4}" stroke="${palette[index]}" opacity=".55"/><circle cx="${x}" cy="${y}" r="10" fill="${palette[index]}" stroke="#fffdf8" stroke-width="4"/><text x="${x + 24}" y="${labelY}" class="point-label">${escapeHtml(label(model.modelId))} · ${model.score.toFixed(1)}</text>`;
    })
    .join("");
  return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Observed score versus ${escapeHtml(options.xLabel)}">${grid}<line x1="${left}" y1="${bottom}" x2="${left + plotWidth}" y2="${bottom}" stroke="#858b94"/>${xAxis}${points}<text x="22" y="${(top + bottom) / 2}" text-anchor="middle" transform="rotate(-90 22 ${(top + bottom) / 2})" class="axis-label">Observed score</text><text x="${left + plotWidth / 2}" y="${height - 20}" text-anchor="middle" class="axis-label">${escapeHtml(options.xLabel)}${options.log ? " · log scale" : ""}</text></svg>`;
}

export function renderReport(summary: any) {
  const models = summary.models;
  const leader = models[0];
  const weakest = models[models.length - 1];
  const separation = leader.score - weakest.score;
  const caseRows = models
    .flatMap((model: any) => model.cases.map((testCase: any) => ({ ...testCase, modelId: model.modelId })))
    .map((row: any) => `<tr><td>${escapeHtml(label(row.modelId))}</td><td>${escapeHtml(row.caseId)}</td><td class="num">${row.score.toFixed(2)}</td><td class="num">$${row.inferenceCostUsd.toFixed(6)}</td></tr>`)
    .join("");
  const modelRows = models
    .map((model: any) => `<tr><td>${escapeHtml(label(model.modelId))}</td><td class="num strong">${model.score.toFixed(2)}</td><td class="num">$${model.inferenceCostUsd.toFixed(6)}</td><td class="num">${model.inferenceSeconds.toFixed(1)}s</td><td class="num">${model.totalOutputTokens.toLocaleString()}</td></tr>`)
    .join("");
  const inferenceSpend = models.reduce((sum: number, model: any) => sum + model.inferenceCostUsd, 0);
  const evaluatorSpend = models.reduce((sum: number, model: any) => sum + model.evaluatorCostUsd, 0);
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Doc2MD benchmark report</title><style>
  :root{--ink:#17211c;--muted:#66706b;--paper:#f7f5ef;--card:#fffdf8;--line:#d8d5cc;--accent:#1f4b99}*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.55 ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}main{max-width:1180px;margin:auto;padding:58px 30px 90px}header{padding-bottom:34px;border-bottom:2px solid var(--ink)}.kicker{text-transform:uppercase;letter-spacing:.14em;font-weight:800;font-size:12px;color:var(--accent)}h1{margin:12px 0 14px;font:700 clamp(42px,7vw,74px)/.98 Georgia,serif;letter-spacing:-.035em}.lede{font-size:19px;color:var(--muted);max-width:850px}.meta{display:flex;gap:24px;flex-wrap:wrap;margin-top:18px;color:var(--muted);font-size:13px}.cards{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:28px 0}.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:20px}.card .label{text-transform:uppercase;letter-spacing:.08em;color:var(--muted);font-size:11px;font-weight:800}.card .metric{margin-top:8px;font:700 31px/1 Georgia,serif}.card .detail{margin-top:8px;color:var(--muted);font-size:12px}section{margin-top:48px}h2{font:700 29px/1.15 Georgia,serif;margin:0 0 8px}h3{margin:0 0 4px;font:700 17px/1.25 Georgia,serif}.subtitle{color:var(--muted);margin:0 0 16px}.figure{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;overflow:hidden}.figure svg{display:block;width:100%;height:auto}.efficiency-grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}.efficiency-grid .figure:last-child{grid-column:1/-1}.chart-note{color:var(--muted);font-size:12px;margin:2px 0 12px}.tick,.case-label,.legend{fill:#6b716d;font-size:14px}.axis-label{fill:#565e59;font-size:14px;font-weight:700}.point-label{fill:#17211c;font-size:14px;font-weight:800;paint-order:stroke;stroke:#fffdf8;stroke-width:5px}.model-label{fill:#17211c;font-size:16px;font-weight:700}.value{fill:#17211c;font-size:16px;font-weight:800}.bar-value{fill:#414844;font-size:12px;font-weight:700}.table-scroll{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:14px}table{width:100%;border-collapse:collapse;min-width:820px}th,td{padding:12px 14px;border-bottom:1px solid var(--line);text-align:left}thead th{background:#efede6;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.06em}tbody tr:last-child td{border-bottom:0}.num{text-align:right;font-variant-numeric:tabular-nums}.strong{font-weight:800}.note{border-left:4px solid #c18b2e;background:#f7eedb;padding:15px 17px;margin-top:18px;max-width:900px}footer{margin-top:56px;padding-top:18px;border-top:1px solid var(--line);color:var(--muted);font-size:12px}@media(max-width:800px){main{padding:34px 16px 60px}.cards,.efficiency-grid{grid-template-columns:1fr}.efficiency-grid .figure:last-child{grid-column:auto}.figure{padding:8px}}@media(max-width:520px){.cards{grid-template-columns:1fr}h1{font-size:42px}}
  </style></head><body><main><header><div class="kicker">Doc2MD · Native PDF benchmark</div><h1>Model reconstruction report</h1><p class="lede">Five adversarial document packets measuring faithful PDF-to-Markdown recovery across long context, mixed modality, tables, forms, source precedence, diagrams, scans, and malformed native exports.</p><div class="meta"><span>Generated ${escapeHtml(summary.generatedAt)}</span><span>${summary.caseCount} cases</span><span>${models.length} complete models</span><span>One stochastic observation per model/case</span></div></header>
  <div class="cards"><div class="card"><div class="label">Top observed score</div><div class="metric">${leader.score.toFixed(1)}</div><div class="detail">${escapeHtml(label(leader.modelId))}</div></div><div class="card"><div class="label">Model separation</div><div class="metric">${separation.toFixed(1)} pts</div><div class="detail">Top minus weakest observed model</div></div><div class="card"><div class="label">Current cases</div><div class="metric">${summary.caseCount}</div><div class="detail">Equal weight per case</div></div><div class="card"><div class="label">Model inference spend</div><div class="metric">${money(inferenceSpend)}</div><div class="detail">Provider-reported usage for displayed models</div></div></div>
  <section><h2>Overall reconstruction fidelity</h2><p class="subtitle">Equal-case score on a 0–100 scale. Higher is better.</p><div class="figure">${scoreChart(models)}</div></section>
  <section><h2>Observed intelligence versus efficiency</h2><p class="subtitle">Three descriptive 2D views using model inference only. Each point is one model's complete five-case observation.</p><div class="efficiency-grid"><div class="figure"><h3>Score vs inference cost</h3><p class="chart-note">USD · logarithmic x-axis because observed costs span more than an order of magnitude.</p>${scatterChart(models, { metric: "inferenceCostUsd", xLabel: "Model inference cost (USD)", format: (value) => `$${value.toFixed(value < 0.1 ? 3 : 2)}`, log: true })}</div><div class="figure"><h3>Score vs inference time</h3><p class="chart-note">Summed provider-call seconds across five cases; cases ran concurrently.</p>${scatterChart(models, { metric: "inferenceSeconds", xLabel: "Summed inference seconds", format: (value) => `${value.toFixed(0)}s` })}</div><div class="figure"><h3>Score vs output volume</h3><p class="chart-note">Total model output tokens across all five reconstructions.</p>${scatterChart(models, { metric: "totalOutputTokens", xLabel: "Model output tokens", format: (value) => `${Math.round(value / 1_000)}k` })}</div></div><p class="note"><strong>Small sample:</strong> three labeled model observations are shown because these are the models currently run. Treat the plots as descriptive efficiency views, not fitted relationships.</p></section>
  <section><h2>Where models succeed and fail</h2><p class="subtitle">Grouped per-case scores reveal whether separation is broad or driven by one packet.</p><div class="figure">${caseChart(models)}</div></section>
  <section><h2>Model inference cost</h2><p class="subtitle">Cumulative recorded inference cost for the displayed cached observation.</p><div class="figure">${spendChart(models)}</div></section>
  <section><h2>Model summary</h2><div class="table-scroll"><table><thead><tr><th>Model</th><th class="num">Score</th><th class="num">Inference spend</th><th class="num">Summed inference time</th><th class="num">Output tokens</th></tr></thead><tbody>${modelRows}</tbody></table></div></section>
  <section><h2>Exact case results</h2><div class="table-scroll"><table><thead><tr><th>Model</th><th>Case</th><th class="num">Score</th><th class="num">Inference spend</th></tr></thead><tbody>${caseRows}</tbody></table></div><p class="note"><strong>Uncertainty:</strong> each displayed model/case is one stochastic generation and one evaluator judgment. The chart supports observed comparison, not a reliability or variance claim.</p></section>
  <footer>Source: cached Doc2MD predictions and provider-reported token usage. Report generation performs no model calls. Evaluator spend is still measured and retained in <code>reports/summary.json</code>; cumulative evaluator spend for this displayed cohort is ${money(evaluatorSpend)}.</footer></main></body></html>`;
}
