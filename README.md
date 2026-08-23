# Doc2MD

Doc2MD measures how faithfully a model converts a PDF into one Markdown document. It tests exhaustive recovery of text, tables, forms, visual information, reading order, source precedence, and long-document coherence—not summarization.

The current corpus contains five cases and 84 pages under `benchmark/cases/`. The runtime, scorer, cache, and report are manifest-driven: cases may be added, removed, or replaced without changing them, provided the replacements conform to the standard native-PDF and facts-v3 contract. The small generator registry explicitly lists the builders that produce the current corpus. Each case has:

```text
source.pdf   PDF sent to the model
facts.json   atomic scoring obligations
gold.md      human-readable reference
spec.md      case design notes
```

## Run everything

```bash
npm install
cp .env.example .env.local
npm run bench
```

Set the relevant provider keys in `.env.local`. On a fresh cache, the default run uses the two inexpensive anchors:

- `openai-gpt-5-nano`
- `google-gemini-3.1-flash-lite`

Google models and the Gemini 3.1 Flash-Lite evaluator use the Gemini API through a server-side `GEMINI_API_KEY` created in Google AI Studio. Anthropic models use `ANTHROPIC_API_KEY`; the registered no-thinking models are `anthropic-claude-haiku-4.5`, `anthropic-claude-sonnet-5`, and `anthropic-claude-opus-4.8`.

Select any registered model with repeatable flags:

```bash
npm run bench -- --model openai-gpt-5.4-nano --model google-gemini-3.1-flash-lite
```

## Run off-the-shelf parsers

Install the pinned, isolated Python parser environments once:

```bash
npm run parsers:setup
```

Poppler's `pdftotext` must be available on `PATH`. Marker fast CPU also requires `llama-server`; on macOS these can be installed with `brew install poppler llama.cpp`. Parser environments and downloaded model caches live under ignored `.parser-envs/` and `.parser-cache/` directories.

Run any parser through the same prediction cache, evaluator, and report as the hosted models:

```bash
npm run bench -- --candidate pdftotext
npm run bench -- --candidate firecrawl-pdf-inspector
npm run bench -- --candidate markitdown-base
npm run bench -- --candidate markitdown-ocr-gpt-5.6-luna
npm run bench -- --candidate pymupdf4llm-default
npm run bench -- --candidate docling-standard-cpu
npm run bench -- --candidate marker-fast-cpu
npm run bench -- --candidate reducto-standard
npm run bench -- --candidate reducto-agentic
npm run bench -- --candidate mistral-ocr-4
npm run bench -- --candidate llamaparse-agentic
npm run bench -- --candidate firecrawl-hosted-auto
npm run bench -- --candidate landingai-dpt2
npm run bench -- --candidate upstage-auto
npm run bench -- --candidate nanonets-docstrange
npm run bench -- --candidate unstructured-vlm-gpt4o
```

`--model` remains supported and is an alias for selecting a registered candidate, so model and parser IDs may be mixed in one invocation. Parser cases run serially; hosted model cases retain their existing concurrency. Every prediction and its inference metadata are saved before evaluation begins, so an evaluator rate limit never requires reconversion.

`markitdown-ocr-gpt-5.6-luna` uses the released `markitdown-ocr` plugin and its public `llm_prompt` configuration. Its pinned prompt is [`benchmark/parser-prompts/markitdown-vision.md`](benchmark/parser-prompts/markitdown-vision.md); no package code is patched. The adapter rejects MarkItDown's documented silent base-converter fallback unless at least one vision call succeeds.

`reducto-standard` uses Reducto's hosted Parse endpoint with standard hybrid OCR, whole-document output, dynamic table formatting, page markers, and the default figure-description capability made explicit. Set `REDUCTO_API_KEY` in `.env.local`. Its benchmark cost uses the credits reported by each response at the published Standard pay-as-you-go rate; introductory free credits are ignored.

`reducto-agentic` adds Reducto's released text, table, and figure agentic review scopes, intelligent ordering, and the public per-scope prompt option with one generic document-fidelity prompt. It deliberately leaves the separate advanced chart agent disabled because the benchmark's observed failure was image binding rather than numerical chart extraction.

The free-plan hosted batch uses `MISTRAL_API_KEY`, `LLAMA_CLOUD_API_KEY`, and optionally `FIRECRAWL_API_KEY` from `.env.local`. Mistral runs the standard OCR 4 Markdown endpoint, LlamaParse runs its default Agentic tier, and Firecrawl runs hosted PDF `auto` mode. Firecrawl permits a small keyless POC, but its anonymous daily cap may be too small for all 86 pages; a free account key is therefore recommended for the complete run.

`landingai-dpt2` uses LandingAI ADE's ready-made Parse endpoint and whole-document Markdown output. `upstage-auto` uses Upstage Document Parse's automatic per-page routing between its Standard and Enhanced modes. Their benchmark costs use published list prices ($0.03/page for LandingAI; $0.01 Standard and $0.03 Enhanced per page for Upstage), ignoring free credits.

`nanonets-docstrange` uses Nanonets DocStrange's asynchronous extraction endpoint with its default processing and Markdown output. Its cost uses the published pay-as-you-go rate of one credit per page and $1 per 100 credits ($0.01/page), ignoring the one-time free allowance.

`unstructured-vlm-gpt4o` uses Unstructured's documented Partition endpoint with the released VLM strategy and its documented GPT-4o model option. The ordered JSON elements are serialized as Markdown-compatible HTML, preserving the provider's table, figure, checkbox, and layout markup without a custom parsing step. Its cost uses the Personal Workspace production list price of $0.03/page, ignoring the 15,000-page free allowance.

Leaderboard cost ignores free tiers and promotional credits. Hosted and hybrid candidates use published production list price applied to provider-reported usage; local parsers report zero conversion-API cost. Evaluator time and evaluator cost are excluded from the candidate comparison.

The intended Zennoia production comparison is direct whole-document GPT-5.6 Sol processing versus one-time page-parallel GPT-5.6 Luna preprocessing whose stored Markdown is then consumed by GPT-5.6 Sol production agents. The registered whole-document GPT-5.6 Luna result is benchmark coverage only; it was never a proposed production path and should not be substituted for that operational baseline.

All saved hosted-model timings were observed through unpaid, data-sharing access rather than paid dedicated capacity. They include provider-tier scheduling, contention, and run-to-run instability, so they are directional benchmark observations—not forecasts of paid production latency. Raw observed timings remain in the results; no unmeasured paid-tier improvement is assumed. This timing caveat is independent of cost normalization, which continues to use published production list prices rather than free-tier discounts.

Ensure multiple independent draw slots for selected models:

```bash
npm run bench -- --model google-gemini-3.5-flash --runs 3
```

`--runs 3` means “ensure draws 1–3 exist.” It reuses every valid cached slot and runs only missing model/case/draw combinations. The existing cache is draw 1, so requesting three draws after a normal run creates only draws 2 and 3.

Models run serially. Within each model, every case pipeline runs concurrently. Each pipeline sends the native PDF to the model and starts evaluation as soon as that case finishes. Anthropic responses are streamed so long reconstructions do not hit the non-streaming HTTP header timeout. Google candidate request attempts, including automatic SDK retries, are started 15 seconds apart to remain below the strictest selected model's 5 RPM personal AI Studio limit.

Results are cached per model and case:

```text
runs/cache/<model>/<case>/prediction.md
runs/cache/<model>/<case>/inference.json
runs/cache/<model>/<case>/score.json
runs/cache/<model>/<case>/evaluation-parts/*.json
runs/cache/<model>/<case>/draws/002/{prediction.md,inference.json,score.json}
runs/cache/<model>/<case>/draws/003/{prediction.md,inference.json,score.json}
reports/summary.json
reports/index.html
```

Inference is reused only when the PDF bytes, conversion prompt, model configuration, and output limit match. Evaluation is reused only when the prediction, facts, evaluator model, and score-affecting settings match. Every successful evaluator batch is checkpointed immediately; if another batch fails or rate-limits, rerunning reuses both the completed model inference and completed evaluator batches and calls only the unfinished batches. The runner waits for every started sibling case and draw to settle, continues later requested models after isolated failures, rebuilds the report, and only then returns a combined failure. Changes to provider transport, prompt caching, or pricing do not invalidate an otherwise identical score. A scoring-semantics change therefore rescores cached predictions without rerunning the model. Adding a new case runs only that missing case for previously cached models. Explicit `--model` flags run/check only those models; without flags, the command checks the default anchors plus every model already present in the cache.

After every invocation, the merged report is rebuilt from every model with at least one complete draw for the current manifest. Each draw is the equal-weight mean of its case scores; repeated models report the mean of those complete suite draws plus their range and sample SD. Operating cost, summed case-call latency, and output tokens are shown as means per draw so models with different draw counts remain comparable. Because cases run concurrently, summed case-call latency is not suite wall-clock time. Hosted-model latency is the observed unpaid data-sharing-tier measurement described above, not a paid-production forecast.

## Scoring

Gemini 3.1 Flash-Lite evaluates compact batches of candidate Markdown against source-anchored atomic obligations and classifies each obligation as correct, missing, or incorrect. Evaluator requests start at a fixed 15-second cadence, leaving headroom below the personal AI Studio project's request and input-token limits. Collision-safe deterministic checks first pre-credit unambiguous table bindings, form states, and directed relationships, so the evaluator returns only unresolved obligations; ordered records and ambiguous or repeated locators stay with the semantic evaluator. Stable 64-obligation answer-key batches remain at the beginning of each request so Gemini's implicit cache can reuse them across candidates. Missing results contain only ids; correct and incorrect results also contain candidate-line evidence. A separate conservative audit can penalize source-invented claims only within explicitly declared, source-grounded closed worlds. Successful scores and individual evaluator requests are checkpointed independently; transport-only protocol changes retain compatible completed scores but invalidate incomplete request checkpoints. Corpus and answer-key quality are reviewed during benchmark development; the runtime command never grades the gold answers or runs a paid evaluator preflight.

The scorer has no case-ID branches or corpus-size assumptions. Case-specific knowledge belongs only in each case's `facts.json`, `gold.md`, and `spec.md`; generic runtime validation rejects rubric IDs or ungrounded members masquerading as source-visible closed-world keys. A leaf's `expectation` is the complete semantic contract sent to the evaluator, so non-obvious acceptable equivalents must be stated there. `evidencePolicy` aliases support conservative deterministic recognition and do not silently broaden that semantic contract.

## Editing cases

The committed PDFs are ready to run. To rebuild or inspect them:

```bash
npm run generate
npm run validate
npm run render
```

Case-generation code lives under `scripts/benchmark_cases/`. The original redesign objective is archived in `docs/benchmark-objective.md`; the current case coverage is summarized in `docs/case-challenge-profile.md`.
