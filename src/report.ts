const palette = ["#174f43", "#bb7a28", "#8d5368", "#6d6f78", "#785d91", "#356c83"];
const labColors: Record<string, string> = { openai: "#174f43", google: "#bb7a28", anthropic: "#8d5368" };

type ReportCase = {
  id: string;
  title: string;
  tags: string[];
  purpose: string;
};

function escapeHtml(value: unknown) {
  return String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}

function label(model: string | { modelId: string; configuredModel?: { modelName?: string } }): string {
  if (typeof model === "string") return model.replace(/^(?:anthropic|google|openai)-/, "");
  return model.modelId.replace(/^(?:anthropic|google|openai)-/, "");
}

function money(value: number) {
  return `$${value.toFixed(value < 0.1 ? 4 : 3)}`;
}

function modelColor(model: any, fallbackIndex: number) {
  return labColors[model.configuredModel?.provider] ?? palette[fallbackIndex % palette.length];
}

function humanizeTag(tag: string) {
  return tag.replaceAll("-", " ");
}

function reportCaseTitle(title: string) {
  return title.replace(/\s+across\s+\d+\s+pages$/i, "");
}

function interactiveChart(models: any[]) {
  const data = JSON.stringify(models.map((model) => ({
    name: label(model), score: model.score, cost: model.inferenceCostUsd,
    time: model.inferenceSeconds, tokens: model.totalOutputTokens,
    color: modelColor(model, 0),
  }))).replaceAll("<", "\\u003c");
  return `<div class="bench-chart">
    <div class="chart-tabs" role="group" aria-label="Choose chart x-axis">
      <button type="button" data-metric="cost" aria-selected="true">Cost</button>
      <button type="button" data-metric="time" aria-selected="false">Time</button>
      <button type="button" data-metric="tokens" aria-selected="false">Output tokens</button>
    </div>
    <div id="chart-stage"></div>
  </div><script>(() => {
    const points=${data};
    const metrics={
      cost:{title:"Score vs cost",axis:"Cost (USD, log scale)",value:p=>p.cost,format:v=>"$"+v.toFixed(v<.1?3:2),detail:v=>"$"+v.toFixed(4),log:true},
      time:{title:"Score vs time",axis:"Time (seconds, log scale)",value:p=>p.time,format:v=>Math.round(v)+"s",detail:v=>v.toFixed(1)+"s",log:true},
      tokens:{title:"Score vs output tokens",axis:"Output tokens (log scale)",value:p=>p.tokens,format:v=>Math.round(v/1000)+"k",detail:v=>Math.round(v).toLocaleString(),log:true}
    };
    const esc=s=>String(s).replace(/[&<>\"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
    const scoreValues=points.map(p=>p.score),scoreMin=Math.min(...scoreValues),scoreMax=Math.max(...scoreValues);
    const scoreSpan=Math.max(scoreMax-scoreMin,10),rawStep=scoreSpan/5,power=10**Math.floor(Math.log10(rawStep)),fraction=rawStep/power;
    const scoreStep=(fraction<=1?1:fraction<=2?2:fraction<=5?5:10)*power;
    const yMin=Math.max(0,Math.floor((scoreMin-scoreSpan*.1)/scoreStep)*scoreStep),yMax=Math.min(100,Math.ceil((scoreMax+scoreSpan*.1)/scoreStep)*scoreStep);
    const yTicks=Array.from({length:Math.round((yMax-yMin)/scoreStep)+1},(_,i)=>yMin+i*scoreStep);
    function render(key){
      const m=metrics[key],W=1000,H=500,p={l:84,r:70,t:70,b:78},right=W-p.r,bottom=H-p.b,vals=points.map(m.value),min=m.log?Math.min(...vals):0,max=Math.max(...vals),domainHeadroom=.12;
      const logMin=m.log?Math.log10(min):0,logSpan=m.log?Math.log10(max)-logMin:0;
      const norm=v=>m.log?(Math.log10(v)-logMin)/(logSpan*(1+domainHeadroom)||1):v/(max*(1+domainHeadroom)||1);
      const yDisplayMax=yMax+(yMax-yMin)*domainHeadroom;
      const x=v=>p.l+norm(v)*(right-p.l),y=v=>p.t+(1-(v-yMin)/(yDisplayMax-yMin))*(bottom-p.t);
      const yt=yTicks.map(v=>'<line x1="'+p.l+'" y1="'+y(v)+'" x2="'+right+'" y2="'+y(v)+'" class="grid"/><text x="'+(p.l-14)+'" y="'+(y(v)+5)+'" text-anchor="end" class="tick">'+v+'</text>').join("");
      const xt=(m.log?[min,Math.sqrt(min*max),max]:[0,max/3,max*2/3,max]).map(v=>'<line x1="'+x(v||min)+'" y1="'+bottom+'" x2="'+x(v||min)+'" y2="'+(bottom+7)+'" class="axis"/><text x="'+x(v||min)+'" y="'+(bottom+27)+'" text-anchor="middle" class="tick">'+m.format(v)+'</text>').join("");
      const items=points.map((d,i)=>({d,i,px:x(m.value(d)),py:y(d.score),text:d.name}));
      const labels=items.map(item=>'<text x="'+(item.px+13)+'" y="'+(item.py+4)+'" text-anchor="start" class="point-label" data-point="'+item.i+'">'+esc(item.text)+'</text>').join('');
      const marks=items.map(item=>{const axisValue=m.detail(m.value(item.d)),aria=item.d.name+'; score '+item.d.score.toFixed(2)+'; '+axisValue;return '<g class="chart-point" data-point="'+item.i+'" tabindex="0" role="button" aria-label="'+esc(aria)+'"><circle class="point-dot" cx="'+item.px+'" cy="'+item.py+'" r="5.5" fill="'+item.d.color+'" stroke="#fffdf8" stroke-width="1.5"/></g>'}).join("");
      const crosshair='<g class="crosshair" visibility="hidden" aria-hidden="true"><line class="crosshair-line crosshair-x"/><line class="crosshair-line crosshair-y"/><text class="crosshair-value crosshair-x-value" y="'+(bottom+27)+'" text-anchor="middle"></text><text class="crosshair-value crosshair-y-value" x="'+(p.l-14)+'" text-anchor="end"></text></g>';
      const stage=document.querySelector("#chart-stage");
      stage.innerHTML='<svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="'+esc(m.title)+'"><text x="'+p.l+'" y="38" class="chart-title">'+esc(m.title)+'</text>'+yt+'<line x1="'+p.l+'" y1="'+bottom+'" x2="'+right+'" y2="'+bottom+'" class="axis"/>'+xt+labels+crosshair+marks+'<text x="24" y="'+((p.t+bottom)/2)+'" transform="rotate(-90 24 '+((p.t+bottom)/2)+')" text-anchor="middle" class="axis-label">Score</text><text x="'+((p.l+right)/2)+'" y="'+(H-18)+'" text-anchor="middle" class="axis-label">'+esc(m.axis)+'</text></svg>';
      const svg=stage.querySelector("svg"),groups=[...svg.querySelectorAll(".chart-point")],pointLabels=[...svg.querySelectorAll(".point-label")],cross=svg.querySelector(".crosshair"),crossX=svg.querySelector(".crosshair-x"),crossY=svg.querySelector(".crosshair-y"),crossXValue=svg.querySelector(".crosshair-x-value"),crossYValue=svg.querySelector(".crosshair-y-value");
      const focusPoint=index=>{const item=items.find(candidate=>candidate.i===index);if(!item)return;svg.classList.add("chart-has-focus");groups.forEach(group=>{const active=Number(group.dataset.point)===index;group.classList.toggle("is-active",active);group.classList.toggle("is-muted",!active)});pointLabels.forEach(modelLabel=>modelLabel.classList.toggle("is-muted",Number(modelLabel.dataset.point)!==index));cross.setAttribute("visibility","visible");crossX.setAttribute("x1",item.px);crossX.setAttribute("x2",item.px);crossX.setAttribute("y1",item.py);crossX.setAttribute("y2",bottom);crossY.setAttribute("x1",p.l);crossY.setAttribute("x2",item.px);crossY.setAttribute("y1",item.py);crossY.setAttribute("y2",item.py);crossXValue.setAttribute("x",item.px);crossXValue.textContent=m.detail(m.value(item.d));crossYValue.setAttribute("y",item.py+5);crossYValue.textContent=item.d.score.toFixed(2)};
      const clearFocus=()=>{svg.classList.remove("chart-has-focus");groups.forEach(group=>group.classList.remove("is-active","is-muted"));pointLabels.forEach(modelLabel=>modelLabel.classList.remove("is-muted"));cross.setAttribute("visibility","hidden")};
      const finePointer=window.matchMedia("(hover: hover) and (pointer: fine)").matches;
      groups.forEach(group=>{const index=Number(group.dataset.point),dot=group.querySelector(".point-dot");if(finePointer){dot.addEventListener("pointerenter",()=>focusPoint(index));dot.addEventListener("pointerleave",()=>{if(document.activeElement!==group)clearFocus()})}group.addEventListener("focus",()=>focusPoint(index));group.addEventListener("blur",clearFocus);dot.addEventListener("click",()=>focusPoint(index));group.addEventListener("keydown",event=>{if(event.key==="Escape"){group.blur();clearFocus()}})});
      document.querySelectorAll("[data-metric]").forEach(b=>b.setAttribute("aria-selected",String(b.dataset.metric===key)));
    }
    document.querySelectorAll("[data-metric]").forEach(b=>b.addEventListener("click",()=>render(b.dataset.metric)));render("cost");
  })()</script>`;
}

function caseSections(models: any[], cases: ReportCase[]) {
  return cases.map((testCase) => {
    const scores = models
      .map((model: any, modelIndex: number) => ({
        model,
        modelIndex,
        score: model.cases.find((candidate: any) => candidate.caseId === testCase.id)?.score,
      }))
      .filter(({ score }: any) => Number.isFinite(score))
      .sort((a: any, b: any) => b.score - a.score || a.modelIndex - b.modelIndex)
      .map(({ model, modelIndex, score }: any) =>
        `<div class="case-score"><span class="swatch" style="background:${modelColor(model, modelIndex)}"></span><span>${escapeHtml(label(model))}</span><span class="track"><i style="width:${score}%;background:${modelColor(model, modelIndex)}"></i></span><strong>${score.toFixed(1)}</strong></div>`,
      )
      .join("");
    return `<article class="case-study"><div class="case-copy"><h3>${escapeHtml(reportCaseTitle(testCase.title))}</h3><p>${escapeHtml(testCase.purpose)}</p><div class="coverage">${testCase.tags.map((item) => `<span>${escapeHtml(humanizeTag(item))}</span>`).join("")}</div></div><div class="case-results"><div class="mini-label">Scores</div>${scores}</div></article>`;
  }).join("");
}

export function renderReport(summary: any) {
  const models = summary.models;
  const cases = (summary.cases ?? []) as ReportCase[];
  const benchmarkName = summary.name ?? "Doc2MD";
  const benchmarkDescription = summary.description ?? "A benchmark for faithful PDF-to-Markdown reconstruction.";
  const modelRows = models.map((model: any) => `<tr><td><strong>${escapeHtml(label(model))}</strong></td><td class="num strong">${model.score.toFixed(1)}</td><td class="num">${money(model.inferenceCostUsd)}</td><td class="num">${model.inferenceSeconds.toFixed(1)}s</td><td class="num">${Math.round(model.totalOutputTokens).toLocaleString()}</td></tr>`).join("");
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="${escapeHtml(benchmarkDescription)}"><title>${escapeHtml(benchmarkName)} benchmark report</title><style>
  :root{--ink:#17211c;--muted:#626b66;--paper:#f7f5ef;--line:#d8d3c7;--accent:#174f43}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.6 ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;-webkit-font-smoothing:antialiased}main{max-width:1120px;margin:auto;padding:58px 30px 90px}header{padding-bottom:38px;border-bottom:2px solid var(--ink)}a{color:var(--accent);text-decoration-thickness:.08em;text-underline-offset:.14em}.kicker,.mini-label{text-transform:uppercase;letter-spacing:.12em;font-weight:800;font-size:11px;color:var(--accent)}h1{max-width:900px;margin:12px 0 18px;font:700 clamp(42px,7vw,70px)/1 Georgia,serif;letter-spacing:-.035em;text-wrap:balance}.lede{max-width:850px;font:20px/1.5 Georgia,serif;color:#35413b}section{margin-top:58px}h2{font:700 31px/1.15 Georgia,serif;margin:0 0 10px;letter-spacing:-.015em;text-wrap:balance}h3{font:700 22px/1.3 Georgia,serif;margin:0 0 10px;text-wrap:balance}.subtitle,.method p{color:var(--muted);max-width:820px}.purpose{display:grid;grid-template-columns:minmax(250px,.8fr) minmax(0,1.2fr);gap:20px 56px;align-items:start}.purpose h2{margin:0}.purpose-copy{display:grid;gap:17px}.purpose-copy p{margin:0;color:var(--muted)}.purpose-copy .purpose-observation{font:20px/1.5 Georgia,serif;color:#35413b}.figure{margin-top:20px;padding:18px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}.figure svg{display:block;width:100%;height:auto}.chart-tabs{display:grid;grid-template-columns:repeat(3,1fr);width:min(100%,540px);margin:0 auto 12px;padding:3px;border:1px solid var(--line);border-radius:999px}.chart-tabs button{border:0;border-radius:999px;background:transparent;padding:8px 14px;color:var(--muted);font:600 12px inherit;cursor:pointer;transition:background .2s,color .2s}.chart-tabs button[aria-selected="true"]{background:#e7e2d6;color:var(--ink)}.chart-tabs button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}.grid{stroke:#dedbd2}.axis{stroke:#7c817e}.tick{fill:#69716d;font-size:13px}.axis-label{fill:#525b56;font-size:14px;font-weight:700}.chart-title{fill:var(--ink);font:700 25px Georgia,serif}.chart-point{outline:none;transition:opacity .14s ease}.point-dot{cursor:crosshair;pointer-events:all}.point-label{fill:var(--ink);font-size:12px;font-weight:400;pointer-events:none;paint-order:stroke;stroke:#fffdf8;stroke-width:3px;transition:opacity .14s ease}.chart-has-focus .chart-point.is-muted{opacity:.16}.chart-has-focus .point-label.is-muted{opacity:.15}.crosshair{pointer-events:none}.crosshair-line{stroke:var(--accent);stroke-width:1;stroke-dasharray:4 5;opacity:.8}.crosshair-value{fill:var(--ink);font-size:13px;font-weight:900;font-variant-numeric:tabular-nums;paint-order:stroke;stroke:var(--paper);stroke-width:7px;stroke-linejoin:round}.caption{font-size:12px;color:var(--muted);max-width:850px}.case-study{display:grid;grid-template-columns:minmax(0,1.15fr) minmax(360px,.85fr);gap:55px;padding:34px 0;border-top:1px solid var(--line);align-items:center}.case-study:last-child{border-bottom:1px solid var(--line)}.case-copy p{color:var(--muted);max-width:620px}.coverage{display:flex;flex-wrap:wrap;gap:7px;margin-top:16px}.coverage span{padding:4px 8px;background:#ebe7dd;font-size:11px;color:#4c5650}.case-results{display:grid;gap:10px}.case-score{display:grid;grid-template-columns:10px minmax(110px,1fr) 120px 40px;gap:9px;align-items:center;font-size:12px}.swatch{width:9px;height:9px;border-radius:50%}.track{height:6px;background:#e3dfd5;overflow:hidden}.track i{display:block;height:100%}.case-score strong{text-align:right;font-variant-numeric:tabular-nums}.table-scroll{overflow-x:auto;margin-top:18px;border-top:2px solid var(--ink);border-bottom:1px solid var(--line)}table{width:100%;border-collapse:collapse;min-width:620px}th,td{padding:12px 10px;border-bottom:1px solid var(--line);text-align:left}th{font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted)}tbody tr:last-child td{border-bottom:0}.num{text-align:right;font-variant-numeric:tabular-nums}.strong{font-weight:800}.method{display:grid;grid-template-columns:1fr 1fr;gap:20px 48px}.method h2{grid-column:1/-1}.method p{margin:0}@media(prefers-reduced-motion:reduce){.chart-point,.point-dot,.point-label{transition:none}}@media(max-width:780px){main{padding:34px 17px 60px}.case-study,.method,.purpose{grid-template-columns:1fr}.method h2{grid-column:auto}.case-study{gap:22px}.case-score{grid-template-columns:10px minmax(90px,1fr) 80px 38px}.figure{overflow-x:auto}.figure svg{min-width:700px}h1{font-size:42px}}
  main{padding-top:28px}.report-head{display:flex;align-items:baseline;gap:14px;padding:0 0 14px}.report-head h1{margin:0;font:700 28px/1 Georgia,serif;letter-spacing:-.02em}.plot-first{margin-top:14px}.plot-first .figure{margin-top:0;border:0}.benchmark-intro{padding-top:8px;border-top:2px solid var(--ink)}
  </style></head><body><main><header class="report-head"><h1>${escapeHtml(benchmarkName)} benchmark</h1><div class="kicker">Native PDF reconstruction · pass@1</div></header>
  <section class="plot-first"><div class="figure">${interactiveChart(models)}</div></section>
  <section class="benchmark-intro"><h2>How well can a model reconstruct a real document?</h2><p class="lede">${escapeHtml(benchmarkDescription)}</p></section>
  <section class="purpose"><h2>Why preprocess documents?</h2><div class="purpose-copy"><p class="purpose-observation">Many LLM workflows send the original PDF with every request. In a request containing five or ten documents, the files usually account for most of the input cost; the prompt itself is comparatively small.</p><p>A better approach is to convert each file to Markdown once, store the result under a content hash, and send that Markdown to downstream models. The PDF is processed again only if the file changes.</p><p>Reuse also matters within organizations. The same contract, report, policy, or presentation may pass through email, chat, agents, and internal tools as several separate attachments. One stored Markdown version avoids processing every copy again.</p><p>On this benchmark, Gemini 3.1 Flash-Lite reduced the file input and its downstream cost by about 88%. Including the conversion, the first use was about 82% cheaper; across ten uses of the same documents, the saving was about 87.5%.</p><p>Raw PDF processing varies by provider and API route. <a href="https://openrouter.ai/docs/guides/overview/multimodal/pdfs">OpenRouter</a> supports native model processing, a free Cloudflare AI parser, and paid Mistral OCR, while vendor SDKs use their own document-processing systems. Stored Markdown removes these PDF-processing differences from later requests.</p></div></section>
  <section><h2>Capability breakdown</h2><p class="subtitle">Each section shows one document-processing ability and how the models scored. The document's subject matter is incidental.</p>${caseSections(models, cases)}</section>
  <section><h2>Model comparison</h2><p class="subtitle">Cost uses uncached list pricing so every model is compared on the same basis.</p><div class="table-scroll"><table><thead><tr><th>Model</th><th class="num">Score</th><th class="num">Cost</th><th class="num">Time</th><th class="num">Output tokens</th></tr></thead><tbody>${modelRows}</tbody></table></div></section>
  <section class="method"><h2>How scoring works</h2><p>Each model receives the original PDF and returns one Markdown reconstruction. The score covers text, tables, layout, visual evidence, reading order, and consistency across the document.</p><p>The evaluator checks whether required information is present, correctly bound, structurally recoverable, and faithful to the controlling source. Incorrect claims lose more credit than omissions because plausible false data is dangerous in downstream use.</p><p>Each capability case has equal weight. A longer document cannot overwhelm a shorter case that tests a different skill.</p><p>The same scoring structure works across document types and modalities. It does not depend on this specific set of files.</p></section></main></body></html>`;
}
