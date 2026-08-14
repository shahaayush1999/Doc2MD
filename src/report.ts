const palette = ["#174f43", "#bb7a28", "#8d5368", "#6d6f78", "#785d91", "#356c83"];
const labColors: Record<string, string> = { openai: "#174f43", google: "#bb7a28", anthropic: "#8d5368", local: "#356c83", hybrid: "#785d91", hosted: "#9a5b32" };

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

function duration(value: number) {
  return `${value.toFixed(value < 1 ? 2 : 1)}s`;
}

function modelColor(model: any, fallbackIndex: number) {
  return labColors[model.configuredModel?.provider] ?? palette[fallbackIndex % palette.length];
}

function candidateType(model: any): "tool" | "llm" {
  return model.configuredModel?.kind === "parser" ? "tool" : "llm";
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
    time: Math.max(model.inferenceSeconds, 0.001),
    color: modelColor(model, 0),
    type: candidateType(model),
  }))).replaceAll("<", "\\u003c");
  return `<div class="bench-chart">
    <div class="report-controls">
      <div class="segmented-control metric-tabs" role="group" aria-label="Choose chart x-axis">
        <button type="button" data-metric="cost" aria-pressed="true">Cost</button>
        <button type="button" data-metric="time" aria-pressed="false">Time</button>
      </div>
      <div class="segmented-control candidate-tabs" role="group" aria-label="Filter candidates">
        <button type="button" data-scope="all" aria-pressed="true">All</button>
        <button type="button" data-scope="tool" aria-pressed="false">Tools</button>
        <button type="button" data-scope="llm" aria-pressed="false">LLMs</button>
      </div>
    </div>
    <div id="chart-stage"></div>
  </div><script>(() => {
    const points=${data};
    let activeMetric="cost",activeScope="all";
    const metrics={
      cost:{title:"Score vs cost",axis:"Published conversion cost (USD)",value:p=>p.cost,format:v=>"$"+v.toFixed(v<.1?3:2),detail:v=>"$"+v.toFixed(4),log:false},
      time:{title:"Score vs time",axis:"Time (seconds, log scale)",value:p=>p.time,format:v=>Math.round(v)+"s",detail:v=>v.toFixed(1)+"s",log:true}
    };
    const esc=s=>String(s).replace(/[&<>\"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
    function render(){
      const visiblePoints=activeScope==="all"?points:points.filter(point=>point.type===activeScope);
      const scoreValues=visiblePoints.map(point=>point.score),scoreMin=Math.min(...scoreValues),scoreMax=Math.max(...scoreValues);
      const scoreSpan=Math.max(scoreMax-scoreMin,10),rawStep=scoreSpan/5,power=10**Math.floor(Math.log10(rawStep)),fraction=rawStep/power;
      const scoreStep=(fraction<=1?1:fraction<=2?2:fraction<=5?5:10)*power;
      const yMin=Math.max(0,Math.floor((scoreMin-scoreSpan*.1)/scoreStep)*scoreStep),yMax=Math.min(100,Math.ceil((scoreMax+scoreSpan*.1)/scoreStep)*scoreStep);
      const yTicks=Array.from({length:Math.round((yMax-yMin)/scoreStep)+1},(_,i)=>yMin+i*scoreStep);
      const m=metrics[activeMetric],W=1000,H=500,p={l:84,r:70,t:70,b:78},right=W-p.r,bottom=H-p.b,vals=visiblePoints.map(m.value),min=m.log?Math.min(...vals):0,max=Math.max(...vals),domainHeadroom=.12;
      const logMin=m.log?Math.log10(min):0,logSpan=m.log?Math.log10(max)-logMin:0;
      const norm=v=>m.log?(Math.log10(v)-logMin)/(logSpan*(1+domainHeadroom)||1):v/(max*(1+domainHeadroom)||1);
      const yDisplayMax=yMax+(yMax-yMin)*domainHeadroom;
      const x=v=>p.l+norm(v)*(right-p.l),y=v=>p.t+(1-(v-yMin)/(yDisplayMax-yMin))*(bottom-p.t);
      const yt=yTicks.map(v=>'<line x1="'+p.l+'" y1="'+y(v)+'" x2="'+right+'" y2="'+y(v)+'" class="grid"/><text x="'+(p.l-14)+'" y="'+(y(v)+5)+'" text-anchor="end" class="tick">'+v+'</text>').join("");
      const xt=(m.log?[min,Math.sqrt(min*max),max]:[0,max/3,max*2/3,max]).map(v=>'<line x1="'+x(v||min)+'" y1="'+bottom+'" x2="'+x(v||min)+'" y2="'+(bottom+7)+'" class="axis"/><text x="'+x(v||min)+'" y="'+(bottom+27)+'" text-anchor="middle" class="tick">'+m.format(v)+'</text>').join("");
      const items=visiblePoints.map((d,i)=>({d,i,px:x(m.value(d)),py:y(d.score),text:d.name}));
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
      document.querySelectorAll("[data-metric]").forEach(button=>button.setAttribute("aria-pressed",String(button.dataset.metric===activeMetric)));
      document.querySelectorAll("[data-scope]").forEach(button=>button.setAttribute("aria-pressed",String(button.dataset.scope===activeScope)));
    }
    function applyScope(){
      render();
    }
    document.querySelectorAll("[data-metric]").forEach(button=>button.addEventListener("click",()=>{activeMetric=button.dataset.metric;render()}));
    document.querySelectorAll("[data-scope]").forEach(button=>button.addEventListener("click",()=>{activeScope=button.dataset.scope;applyScope()}));
    applyScope();
  })()</script>`;
}

function leaderboardRows(models: any[], caseId?: string) {
  return models
    .map((model: any, modelIndex: number) => {
      const testCase = caseId ? model.cases.find((candidate: any) => candidate.caseId === caseId) : undefined;
      return {
        model,
        modelIndex,
        score: caseId ? testCase?.score : model.score,
        cost: caseId ? testCase?.inferenceCostUsd : model.inferenceCostUsd,
        time: caseId ? testCase?.inferenceSeconds : model.inferenceSeconds,
      };
    })
    .filter(({ score, cost, time }: any) => Number.isFinite(score) && Number.isFinite(cost) && Number.isFinite(time))
    .sort((a: any, b: any) => b.score - a.score || a.modelIndex - b.modelIndex)
    .map(({ model, modelIndex, score, cost, time }: any) => {
      const color = modelColor(model, modelIndex);
      return `<div class="leaderboard-row"><div class="candidate-cell"><span class="swatch" style="background:${color}"></span><strong>${escapeHtml(label(model))}</strong></div><div class="score-cell"><span class="track"><i style="width:${score}%;background:${color}"></i></span><strong>${score.toFixed(1)}</strong></div><div class="cost-cell"><span class="mobile-label">Cost</span>${money(cost)}</div><div class="time-cell"><span class="mobile-label">Time</span>${duration(time)}</div></div>`;
    })
    .join("");
}

function resultsExplorer(models: any[], cases: ReportCase[], benchmarkDescription: string) {
  const taskButtons = [
    `<button type="button" data-task="all" aria-pressed="true">All</button>`,
    ...cases.map((_, index) => `<button type="button" data-task="${escapeHtml(cases[index]!.id)}" aria-pressed="false">Task ${index + 1}</button>`),
  ].join("");
  const taskPanels = [
    `<div class="task-panel" data-task-panel="all"><h3>Full benchmark</h3><p>${escapeHtml(benchmarkDescription)}</p></div>`,
    ...cases.map((testCase) => `<div class="task-panel" data-task-panel="${escapeHtml(testCase.id)}" hidden><h3>${escapeHtml(reportCaseTitle(testCase.title))}</h3><p>${escapeHtml(testCase.purpose)}</p><div class="coverage">${testCase.tags.map((item) => `<span>${escapeHtml(humanizeTag(item))}</span>`).join("")}</div></div>`),
  ].join("");
  const taskLists = [
    `<div class="leaderboard-list" data-task-list="all">${leaderboardRows(models)}</div>`,
    ...cases.map((testCase) => `<div class="leaderboard-list" data-task-list="${escapeHtml(testCase.id)}" hidden>${leaderboardRows(models, testCase.id)}</div>`),
  ].join("");
  return `<section class="results-explorer"><h2>Results</h2><p class="subtitle">Switch between the full benchmark and individual tasks. Cost uses published production pricing and ignores free-tier or promotional discounts.</p><div class="task-filter"><div class="mini-label" id="task-filter-label">Benchmark view</div><div class="task-tabs-scroll"><div class="segmented-control task-tabs" style="--task-count:${cases.length + 1}" role="group" aria-labelledby="task-filter-label">${taskButtons}</div></div></div><div class="task-context">${taskPanels}</div><div class="leaderboard"><div class="leaderboard-head"><span>Candidate</span><span>Score</span><span>Cost</span><span>Time</span></div>${taskLists}</div></section><script>(()=>{const buttons=[...document.querySelectorAll("[data-task]")],panels=[...document.querySelectorAll("[data-task-panel]")],lists=[...document.querySelectorAll("[data-task-list]")];function selectTask(task){buttons.forEach(button=>button.setAttribute("aria-pressed",String(button.dataset.task===task)));panels.forEach(panel=>{panel.hidden=panel.dataset.taskPanel!==task});lists.forEach(list=>{list.hidden=list.dataset.taskList!==task})}buttons.forEach(button=>button.addEventListener("click",()=>selectTask(button.dataset.task)));selectTask("all")})()</script>`;
}

export function renderReport(summary: any) {
  const models = summary.models;
  const cases = (summary.cases ?? []) as ReportCase[];
  const benchmarkName = summary.name ?? "Doc2MD";
  const benchmarkDescription = summary.description ?? "A benchmark for faithful PDF-to-Markdown reconstruction.";
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="${escapeHtml(benchmarkDescription)}"><title>${escapeHtml(benchmarkName)} benchmark report</title><style>
  :root{--ink:#17211c;--muted:#626b66;--paper:#f7f5ef;--line:#d8d3c7;--accent:#174f43}*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.6 ui-sans-serif,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;-webkit-font-smoothing:antialiased}main{max-width:1120px;margin:auto;padding:58px 30px 90px}header{padding-bottom:38px;border-bottom:2px solid var(--ink)}a{color:var(--accent);text-decoration-thickness:.08em;text-underline-offset:.14em}.kicker,.mini-label{text-transform:uppercase;letter-spacing:.12em;font-weight:800;font-size:11px;color:var(--accent)}h1{max-width:900px;margin:12px 0 18px;font:700 clamp(42px,7vw,70px)/1 Georgia,serif;letter-spacing:-.035em;text-wrap:balance}.lede{max-width:850px;font:20px/1.5 Georgia,serif;color:#35413b}section{margin-top:58px}h2{font:700 31px/1.15 Georgia,serif;margin:0 0 10px;letter-spacing:-.015em;text-wrap:balance}h3{font:700 22px/1.3 Georgia,serif;margin:0 0 10px;text-wrap:balance}.subtitle,.method p{color:var(--muted);max-width:820px}.purpose{display:block}.purpose h2{margin:0 0 18px}.purpose-copy{display:grid;gap:17px;max-width:850px}.purpose-copy p{margin:0;color:var(--muted)}.purpose-copy .purpose-observation{font:20px/1.5 Georgia,serif;color:#35413b}.figure{margin-top:20px;padding:18px 0;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}.figure svg{display:block;width:100%;height:auto}.report-controls{display:flex;justify-content:center;gap:10px;margin:0 auto 12px}.segmented-control{display:grid;padding:3px;border:1px solid var(--line);border-radius:999px}.metric-tabs{grid-template-columns:repeat(2,1fr);width:min(100%,320px)}.candidate-tabs{grid-template-columns:repeat(3,1fr);width:min(100%,390px)}.segmented-control button{min-height:44px;border:0;border-radius:999px;background:transparent;padding:8px 14px;color:var(--muted);font:600 12px inherit;cursor:pointer;touch-action:manipulation;transition:background .2s,color .2s}.segmented-control button[aria-pressed="true"]{background:#e7e2d6;color:var(--ink)}.segmented-control button:focus-visible{outline:2px solid var(--accent);outline-offset:2px}[hidden]{display:none!important}.grid{stroke:#dedbd2}.axis{stroke:#7c817e}.tick{fill:#69716d;font-size:13px}.axis-label{fill:#525b56;font-size:14px;font-weight:700}.chart-title{fill:var(--ink);font:700 25px Georgia,serif}.chart-point{outline:none;transition:opacity .14s ease}.point-dot{cursor:crosshair;pointer-events:all}.point-label{fill:var(--ink);font-size:12px;font-weight:400;pointer-events:none;paint-order:stroke;stroke:#fffdf8;stroke-width:3px;transition:opacity .14s ease}.chart-has-focus .chart-point.is-muted{opacity:.16}.chart-has-focus .point-label.is-muted{opacity:.15}.crosshair{pointer-events:none}.crosshair-line{stroke:var(--accent);stroke-width:1;stroke-dasharray:4 5;opacity:.8}.crosshair-value{fill:var(--ink);font-size:13px;font-weight:900;font-variant-numeric:tabular-nums;paint-order:stroke;stroke:var(--paper);stroke-width:7px;stroke-linejoin:round}.caption{font-size:12px;color:var(--muted);max-width:850px}.task-filter{margin-top:26px}.task-filter .mini-label{margin-bottom:8px}.task-tabs-scroll{overflow-x:auto;padding-bottom:4px}.task-tabs{grid-template-columns:repeat(var(--task-count),minmax(92px,1fr));min-width:620px;width:100%}.task-context{min-height:178px;border-bottom:1px solid var(--line)}.task-panel{padding:28px 0}.task-panel p{max-width:850px;margin:0;color:var(--muted)}.coverage{display:flex;flex-wrap:wrap;gap:7px;margin-top:16px}.coverage span{padding:4px 8px;background:#ebe7dd;font-size:11px;color:#4c5650}.leaderboard{border-top:2px solid var(--ink);border-bottom:1px solid var(--line)}.leaderboard-head,.leaderboard-row{display:grid;grid-template-columns:minmax(190px,1.1fr) minmax(240px,1.7fr) 90px 90px;gap:18px;align-items:center}.leaderboard-head{padding:10px 12px;color:var(--muted);font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.07em}.leaderboard-row{min-height:52px;padding:10px 12px;border-top:1px solid var(--line)}.candidate-cell{display:flex;align-items:center;gap:10px;min-width:0}.candidate-cell strong{overflow-wrap:anywhere}.swatch{width:9px;height:9px;flex:0 0 auto;border-radius:50%}.score-cell{display:grid;grid-template-columns:minmax(100px,1fr) 44px;gap:12px;align-items:center}.track{height:7px;background:#e3dfd5;overflow:hidden}.track i{display:block;height:100%}.score-cell strong,.cost-cell,.time-cell{text-align:right;font-variant-numeric:tabular-nums}.cost-cell,.time-cell{font-weight:700}.mobile-label{display:none}.method{display:grid;grid-template-columns:1fr 1fr;gap:20px 48px}.method h2{grid-column:1/-1}.method p{margin:0}@media(prefers-reduced-motion:reduce){.chart-point,.point-dot,.point-label{transition:none}}@media(max-width:780px){main{padding:34px 17px 60px}.report-controls{flex-direction:column;align-items:center}.segmented-control{width:100%}.method{grid-template-columns:1fr}.method h2{grid-column:auto}.task-context{min-height:220px}.leaderboard-head{display:none}.leaderboard-row{grid-template-columns:minmax(0,1fr) auto auto;gap:8px 14px;padding:14px 8px}.score-cell{grid-column:1/-1;grid-row:2}.mobile-label{display:inline;margin-right:5px;color:var(--muted);font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em}.figure{overflow-x:auto}.figure svg{min-width:700px}h1{font-size:42px}}
  body{font-size:14px}main{padding-top:24px}section{margin-top:46px}h2{font-size:27px}h3{font-size:19px}.kicker,.mini-label{font-size:10px}.lede{font-size:18px}.report-head{display:flex;align-items:baseline;gap:11px;padding:0 0 10px}.report-head h1{margin:0;font:700 24px/1 Georgia,serif;letter-spacing:-.02em}.plot-first{margin-top:10px}.plot-first .figure{margin-top:0;border:0}.benchmark-intro{padding-top:7px;border-top:2px solid var(--ink)}.report-controls{gap:7px;margin-bottom:8px}.segmented-control{padding:2px}.metric-tabs{width:min(100%,230px)}.candidate-tabs{width:min(100%,300px)}.segmented-control button{min-height:36px;padding:5px 10px;font-size:11px}.chart-title{font-size:21px}.tick,.point-label{font-size:11px}.axis-label{font-size:12px}.task-filter{margin-top:20px}.task-tabs{min-width:540px}.task-context{min-height:150px}.task-panel{padding:20px 0}.task-panel p{line-height:1.5}.coverage{gap:5px;margin-top:12px}.coverage span{padding:3px 7px;font-size:10px}.leaderboard-head,.leaderboard-row{gap:14px}.leaderboard-head{padding:7px 10px;font-size:10px}.leaderboard-row{min-height:42px;padding:6px 10px;font-size:13px}.score-cell{gap:9px}.track{height:6px}.swatch{width:8px;height:8px}.method{display:block}.method h2{margin-bottom:18px}.method p{max-width:850px;margin:0 0 14px}.method p:last-child{margin-bottom:0}@media(pointer:coarse){.segmented-control button{min-height:44px}}@media(max-width:780px){section{margin-top:40px}.task-context{min-height:190px}.leaderboard-row{min-height:48px;padding:10px 6px}}
  </style></head><body><main><header class="report-head"><h1>${escapeHtml(benchmarkName)} benchmark</h1><div class="kicker">PDF-to-Markdown reconstruction · pass@1</div></header>
  <section class="plot-first"><div class="figure">${interactiveChart(models)}</div></section>
  <section class="benchmark-intro"><h2>How faithfully can a system reconstruct a real document?</h2><p class="lede">${escapeHtml(benchmarkDescription)}</p></section>
  <section class="purpose"><h2>Why preprocess documents?</h2><div class="purpose-copy"><p class="purpose-observation">Many LLM workflows send the original PDF with every request. In a request containing five or ten documents, the files usually account for most of the input cost; the prompt itself is comparatively small.</p><p>A better approach is to convert each file to Markdown once, store the result under a content hash, and send that Markdown to downstream models. The PDF is processed again only if the file changes.</p><p>Reuse also matters within organizations. The same contract, report, policy, or presentation may pass through email, chat, agents, and internal tools as several separate attachments. One stored Markdown version avoids processing every copy again.</p><p>On this benchmark, Gemini 3.1 Flash-Lite reduced the file input and its downstream cost by about 88%. Including the conversion, the first use was about 82% cheaper; across ten uses of the same documents, the saving was about 87.5%.</p><p>Raw PDF processing varies by provider and API route. <a href="https://openrouter.ai/docs/guides/overview/multimodal/pdfs">OpenRouter</a> supports native model processing, a free Cloudflare AI parser, and paid Mistral OCR, while vendor SDKs use their own document-processing systems. Stored Markdown removes these PDF-processing differences from later requests.</p></div></section>
  ${resultsExplorer(models, cases, benchmarkDescription)}
  <section class="method"><h2>How scoring works</h2><p>Each candidate receives the original PDF and returns one Markdown reconstruction. The score covers text, tables, layout, visual evidence, reading order, and consistency across the document.</p><p>The evaluator checks whether required information is present, correctly bound, structurally recoverable, and faithful to the controlling source. Incorrect claims lose more credit than omissions because plausible false data is dangerous in downstream use.</p><p>Each capability case has equal weight. A longer document cannot overwhelm a shorter case that tests a different skill.</p><p>The same scoring structure works across document types and modalities. It does not depend on this specific set of files.</p></section></main></body></html>`;
}
