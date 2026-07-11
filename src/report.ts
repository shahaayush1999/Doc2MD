const palette = ["#174f43", "#bb7a28", "#6d6f78", "#785d91", "#356c83"];

const caseContext: Record<string, { modality: string; purpose: string; covers: string[] }> = {
  "P12-pfas-method-validation": {
    modality: "Native laboratory records, full-page bench scans, mixed raster evidence, chromatograms, and continued tables.",
    purpose: "Tests whether a model can reconstruct exact scientific evidence and follow a signed correction chain to the controlling final result.",
    covers: ["scientific notation and calculations", "continued-table reconstruction", "raster chart and chromatogram reading", "source precedence"],
  },
  "P15-architecture-floorplan-diagrams": {
    modality: "Born-digital technical sheets, image-only scans, native schedules, scanned forms, redlines, and field photographs.",
    purpose: "Tests technical coordination across spatial plans and diagrams where relationships, direction, and final release authority matter as much as text.",
    covers: ["floorplans and spatial overlays", "directed topology", "rack, patch, and panel bindings", "scanned form state and final authority"],
  },
  "P17-clinical-trial-site-monitoring": {
    modality: "A 48-page regulated packet combining native pages, full-page scans, and mixed pages with embedded source regions.",
    purpose: "Tests long-context coherence: the correct state must be reconstructed from continued logs, visible corrections, delayed evidence, and obligations near the document tail.",
    covers: ["long-context recall", "longitudinal entity tracking", "checkbox and correction state", "continued tables and tail obligations"],
  },
  "P21-semiconductor-lot-disposition": {
    modality: "Native manufacturing records, scanned reviews and inspection forms, wafer maps, metrology plots, SPC evidence, and SEM imagery.",
    purpose: "Tests precise binding of coordinates, measurements, exceptions, decisions, and shipment authority across a mixed manufacturing quality file.",
    covers: ["wafer-coordinate binding", "metrology and SPC state", "technical image interpretation", "conflict resolution and disposition"],
  },
  "P23-native-text-layer-recovery": {
    modality: "A genuinely malformed office export whose visible layout clips and displaces legitimate native text, plus one raster validation stamp.",
    purpose: "Tests whether a model can recover the document's real reading order and workflow state rather than blindly reproducing its broken visible layout.",
    covers: ["native text-layer recovery", "reading-order reconstruction", "broken table layout", "workflow and source precedence"],
  },
};

function escapeHtml(value: unknown) {
  return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}

function label(modelId: string) {
  return modelId.replace(/^vertex-/, "").replace(/^openai-/, "");
}

function money(value: number) {
  return `$${value.toFixed(value < 0.1 ? 4 : 3)}`;
}

function interactiveChart(models: any[]) {
  const data = JSON.stringify(models.map((model) => ({
    name: label(model.modelId), score: model.score, cost: model.inferenceCostUsd,
    time: model.inferenceSeconds, tokens: model.totalOutputTokens,
  }))).replaceAll("<", "\\u003c");
  return `<div class="bench-chart">
    <div class="chart-tabs" role="group" aria-label="Choose chart x-axis">
      <button type="button" data-metric="cost" aria-selected="true">Cost</button>
      <button type="button" data-metric="time" aria-selected="false">Time</button>
      <button type="button" data-metric="tokens" aria-selected="false">Output tokens</button>
    </div>
    <div id="chart-stage"></div>
  </div><script>(() => {
    const points=${data},palette=${JSON.stringify(palette)};
    const metrics={
      cost:{title:"Reconstruction fidelity vs inference cost",axis:"Model inference cost · USD · log scale",value:p=>p.cost,format:v=>"$"+v.toFixed(v<.1?3:2),log:true},
      time:{title:"Reconstruction fidelity vs model-call time",axis:"Summed inference time · seconds",value:p=>p.time,format:v=>Math.round(v)+"s"},
      tokens:{title:"Reconstruction fidelity vs output volume",axis:"Model output tokens",value:p=>p.tokens,format:v=>Math.round(v/1000)+"k"}
    };
    const esc=s=>String(s).replace(/[&<>\"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
    const scoreValues=points.map(p=>p.score),scoreMin=Math.min(...scoreValues),scoreMax=Math.max(...scoreValues);
    const scoreSpan=Math.max(scoreMax-scoreMin,10),rawStep=scoreSpan/5,power=10**Math.floor(Math.log10(rawStep)),fraction=rawStep/power;
    const scoreStep=(fraction<=1?1:fraction<=2?2:fraction<=5?5:10)*power;
    const yMin=Math.max(0,Math.floor((scoreMin-scoreSpan*.1)/scoreStep)*scoreStep),yMax=Math.min(100,Math.ceil((scoreMax+scoreSpan*.1)/scoreStep)*scoreStep);
    const yTicks=Array.from({length:Math.round((yMax-yMin)/scoreStep)+1},(_,i)=>yMin+i*scoreStep);
    function render(key){
      const m=metrics[key],W=1000,H=500,p={l:84,r:220,t:70,b:78},right=W-p.r,bottom=H-p.b,vals=points.map(m.value),min=m.log?Math.min(...vals):0,max=Math.max(...vals);
      const norm=v=>m.log?(Math.log10(v)-Math.log10(min))/(Math.log10(max)-Math.log10(min)||1):v/(max||1);
      const x=v=>p.l+norm(v)*(right-p.l),y=v=>p.t+(1-(v-yMin)/(yMax-yMin))*(bottom-p.t);
      const yt=yTicks.map(v=>'<line x1="'+p.l+'" y1="'+y(v)+'" x2="'+right+'" y2="'+y(v)+'" class="grid"/><text x="'+(p.l-14)+'" y="'+(y(v)+5)+'" text-anchor="end" class="tick">'+v+'</text>').join("");
      const xt=(m.log?[min,Math.sqrt(min*max),max]:[0,max/3,max*2/3,max]).map(v=>'<line x1="'+x(v||min)+'" y1="'+bottom+'" x2="'+x(v||min)+'" y2="'+(bottom+7)+'" class="axis"/><text x="'+x(v||min)+'" y="'+(bottom+27)+'" text-anchor="middle" class="tick">'+m.format(v)+'</text>').join("");
      const marks=points.map((d,i)=>{const px=x(m.value(d)),py=y(d.score),ly=py+(i===1?25:-14),color=palette[i%palette.length];return '<line x1="'+px+'" y1="'+py+'" x2="'+(px+18)+'" y2="'+(ly-5)+'" stroke="'+color+'" opacity=".5"/><circle cx="'+px+'" cy="'+py+'" r="10" fill="'+color+'" stroke="#fffdf8" stroke-width="4"/><text x="'+(px+24)+'" y="'+ly+'" class="point-label">'+esc(d.name)+' · '+d.score.toFixed(1)+'</text>'}).join("");
      document.querySelector("#chart-stage").innerHTML='<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="'+esc(m.title)+'"><text x="'+p.l+'" y="38" class="chart-title">'+esc(m.title)+'</text>'+yt+'<line x1="'+p.l+'" y1="'+bottom+'" x2="'+right+'" y2="'+bottom+'" class="axis"/>'+xt+marks+'<text x="24" y="'+((p.t+bottom)/2)+'" transform="rotate(-90 24 '+((p.t+bottom)/2)+')" text-anchor="middle" class="axis-label">Observed score · focused range</text><text x="'+((p.l+right)/2)+'" y="'+(H-18)+'" text-anchor="middle" class="axis-label">'+esc(m.axis)+'</text></svg>';
      document.querySelectorAll("[data-metric]").forEach(b=>b.setAttribute("aria-selected",String(b.dataset.metric===key)));
    }
    document.querySelectorAll("[data-metric]").forEach(b=>b.addEventListener("click",()=>render(b.dataset.metric)));render("cost");
  })()</script>`;
}

function caseSections(models: any[]) {
  const cases = models[0]?.cases ?? [];
  return cases.map((testCase: any, index: number) => {
    const context = caseContext[testCase.caseId];
    const scores = models.map((model: any, modelIndex: number) => {
      const score = model.cases[index].score;
      return `<div class="case-score"><span class="swatch" style="background:${palette[modelIndex % palette.length]}"></span><span>${escapeHtml(label(model.modelId))}</span><span class="track"><i style="width:${score}%"></i></span><strong>${score.toFixed(1)}</strong></div>`;
    }).join("");
    return `<article class="case-study"><div class="case-copy"><div class="eyebrow">${escapeHtml(testCase.title)}</div><h3>${escapeHtml(context?.purpose ?? "Document reconstruction case")}</h3><p>${escapeHtml(context?.modality ?? "Mixed document evidence.")}</p><div class="coverage">${(context?.covers ?? []).map((item) => `<span>${escapeHtml(item)}</span>`).join("")}</div></div><div class="case-results"><div class="mini-label">Observed score</div>${scores}</div></article>`;
  }).join("");
}

export function renderReport(summary: any) {
  const models = summary.models;
  const modelRows = models.map((model: any) => `<tr><td><strong>${escapeHtml(label(model.modelId))}</strong></td><td class="num">${model.drawCount}</td><td class="num strong">${model.score.toFixed(1)}${model.drawCount > 1 ? `<div class="range">${model.scoreMin.toFixed(1)}–${model.scoreMax.toFixed(1)} · SD ${model.scoreStddev.toFixed(1)}</div>` : ""}</td><td class="num">${money(model.inferenceCostUsd)}</td><td class="num">${model.inferenceSeconds.toFixed(1)}s</td><td class="num">${Math.round(model.totalOutputTokens).toLocaleString()}</td></tr>`).join("");
  const evaluatorSpend = models.reduce((sum: number, model: any) => sum + model.cumulativeEvaluatorCostUsd, 0);
  const drawCounts = models.map((model: any) => model.drawCount);
  const minimumDraws = Math.min(...drawCounts);
  const maximumDraws = Math.max(...drawCounts);
  const drawLabel = minimumDraws === maximumDraws ? `${minimumDraws} complete draw${minimumDraws === 1 ? "" : "s"} per model` : `${minimumDraws}–${maximumDraws} complete draws per model`;
  const hasRepeatedDraws = maximumDraws > 1;
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="Doc2MD native PDF reconstruction benchmark report"><title>Doc2MD benchmark report</title><style>
  :root{--ink:#17211c;--muted:#626b66;--paper:#f7f5ef;--line:#d8d3c7;--accent:#174f43}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.6 ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}main{max-width:1120px;margin:auto;padding:58px 30px 90px}header{padding-bottom:38px;border-bottom:2px solid var(--ink)}.kicker,.eyebrow,.mini-label{text-transform:uppercase;letter-spacing:.12em;font-weight:800;font-size:11px;color:var(--accent)}h1{max-width:900px;margin:12px 0 18px;font:700 clamp(42px,7vw,70px)/1 Georgia,serif;letter-spacing:-.035em;text-wrap:balance}.lede{max-width:850px;font:20px/1.5 Georgia,serif;color:#35413b}.meta{display:flex;gap:10px 24px;flex-wrap:wrap;margin-top:20px;color:var(--muted);font-size:13px}section{margin-top:58px}h2{font:700 31px/1.15 Georgia,serif;margin:0 0 10px;letter-spacing:-.015em}h3{font:700 22px/1.3 Georgia,serif;margin:7px 0 10px}.subtitle,.method p{color:var(--muted);max-width:820px}.figure{margin-top:20px;padding:18px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}.figure svg{display:block;width:100%;height:auto}.chart-tabs{display:grid;grid-template-columns:repeat(3,1fr);width:min(100%,540px);margin:0 auto 12px;padding:3px;border:1px solid var(--line);border-radius:999px}.chart-tabs button{border:0;border-radius:999px;background:transparent;padding:8px 14px;color:var(--muted);font:600 12px inherit;cursor:pointer;transition:background .2s,color .2s}.chart-tabs button[aria-selected="true"]{background:#e7e2d6;color:var(--ink)}.chart-tabs button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}.grid{stroke:#dedbd2}.axis{stroke:#7c817e}.tick{fill:#69716d;font-size:13px}.axis-label{fill:#525b56;font-size:14px;font-weight:700}.chart-title{fill:var(--ink);font:700 25px Georgia,serif}.point-label{fill:var(--ink);font-size:14px;font-weight:800;paint-order:stroke;stroke:#fffdf8;stroke-width:5px}.caption{font-size:12px;color:var(--muted);max-width:850px}.case-study{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(360px,.85fr);gap:55px;padding:34px 0;border-top:1px solid var(--line);align-items:center}.case-study:last-child{border-bottom:1px solid var(--line)}.case-copy p{color:var(--muted);max-width:620px}.coverage{display:flex;flex-wrap:wrap;gap:7px;margin-top:16px}.coverage span{padding:4px 8px;background:#ebe7dd;font-size:11px;color:#4c5650}.case-results{display:grid;gap:10px}.case-score{display:grid;grid-template-columns:10px minmax(110px,1fr) 120px 40px;gap:9px;align-items:center;font-size:12px}.swatch{width:9px;height:9px;border-radius:50%}.track{height:6px;background:#e3dfd5}.case-score strong{text-align:right;font-variant-numeric:tabular-nums}.table-scroll{overflow-x:auto;margin-top:18px;border-top:2px solid var(--ink);border-bottom:1px solid var(--line)}table{width:100%;border-collapse:collapse;min-width:700px}th,td{padding:12px 10px;border-bottom:1px solid var(--line);text-align:left}th{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}tbody tr:last-child td{border-bottom:0}.num{text-align:right;font-variant-numeric:tabular-nums}.strong{font-weight:800}.range{color:var(--muted);font-size:10px;font-weight:500;white-space:nowrap}.note{border-left:3px solid #b47b2d;padding-left:14px;color:#554329;max-width:860px}.method{display:grid;grid-template-columns:1fr 1fr;gap:20px 48px}.method h2{grid-column:1/-1}.method p{margin:0}footer{margin-top:60px;padding-top:18px;border-top:1px solid var(--line);color:var(--muted);font-size:11px}@media(max-width:780px){main{padding:34px 17px 60px}.case-study,.method{grid-template-columns:1fr}.method h2{grid-column:auto}.case-study{gap:22px}.case-score{grid-template-columns:10px minmax(90px,1fr) 80px 38px}.figure{overflow-x:auto}.figure svg{min-width:700px}h1{font-size:42px}}
  </style></head><body><main><header><div class="kicker">Doc2MD · Native PDF benchmark</div><h1>How well can a model reconstruct a real document?</h1><p class="lede">Doc2MD measures faithful PDF-to-Markdown reconstruction—not isolated OCR. Models must preserve facts, structure, relationships, visual evidence, reading order, and the controlling final state across long, mixed-modality documents.</p><div class="meta"><span>${summary.caseCount} adversarial cases · 84 pages</span><span>${models.length} models compared</span><span>${drawLabel}</span><span>Generated ${escapeHtml(summary.generatedAt)}</span></div></header>
  <section><h2>Observed fidelity and operating cost</h2><p class="subtitle">The y-axis is the mean equal-case reconstruction score. Switch the x-axis between mean inference cost, summed provider-call time, and output volume per draw.</p><div class="figure">${interactiveChart(models)}</div><p class="caption">The score axis uses a focused, padded range around the displayed models rather than a forced 0–100 scale. Each point represents one model's mean across its complete five-case draws. Cost, time, and token values are mean model-inference totals per draw, keeping models with different draw counts comparable. ${hasRepeatedDraws ? "Ranges and sample SD appear in the comparison table; with only a few draws, treat them as sensitivity evidence rather than precise reliability estimates." : "With one draw per model, small differences remain directional rather than precise."}</p></section>
  <section><h2>What the benchmark asks models to solve</h2><p class="subtitle">Each case targets a different failure mode seen in real document-processing systems. Titles and objectives matter more than internal filenames, so the report presents the task itself.</p>${caseSections(models)}</section>
  <section><h2>Model comparison</h2><p class="subtitle">Mean fidelity and mean operating totals per complete five-case draw.</p><div class="table-scroll"><table><thead><tr><th>Model</th><th class="num">Draws</th><th class="num">Mean fidelity</th><th class="num">Mean inference cost</th><th class="num">Mean summed time</th><th class="num">Mean output tokens</th></tr></thead><tbody>${modelRows}</tbody></table></div><p class="note"><strong>Interpretation:</strong> ${hasRepeatedDraws ? "each model is averaged only across its own complete suite draws. Range and sample SD describe the observed draws and are not high-precision reliability estimates." : "each displayed model currently has one stochastic suite draw, so the comparison is directional and no variance estimate is inferred."}</p></section>
  <section class="method"><h2>What the score means</h2><p>The harness sends each native PDF directly to the provider and asks for one faithful Markdown reconstruction. The result therefore measures the end-to-end document capability: provider PDF ingestion, model perception, long-context coherence, and reconstruction quality.</p><p>Each case contains source-audited, page-anchored obligations. The evaluator checks whether required information is present, correctly bound, structurally recoverable, and faithful to the controlling source. Incorrect claims are penalized more heavily than omissions because plausible false data is especially dangerous downstream.</p><p>The suite combines native text, raster scans, forms, tables, diagrams, plots, photographs, malformed exports, corrections, and conflicting draft/final states. A model must integrate those layers rather than succeed through plain text extraction alone.</p><p>Cases receive equal weight so the 48-page clinical packet cannot overwhelm smaller but distinct challenges. The goal is a benchmark whose score tracks whether a model can actually solve varied document-processing work, not how verbose its Markdown looks.</p></section>
  <footer>Source: cached Doc2MD predictions and provider-reported usage. Report generation performs no model calls. Evaluator spend remains measured in <code>reports/summary.json</code> (${money(evaluatorSpend)} for this displayed cohort) but is excluded from the comparison UI.</footer></main></body></html>`;
}
