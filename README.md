# Doc2MD

Doc2MD measures how faithfully a model converts a PDF into one Markdown document. It tests exhaustive recovery of text, tables, forms, visual information, reading order, source precedence, and long-document coherence—not summarization.

The current corpus contains five cases and 86 pages under `benchmark/cases/`. The runtime, scorer, cache, and report are manifest-driven: cases may be added, removed, or replaced without changing them, provided the replacements conform to the standard native-PDF and facts-v3 contract. The small generator registry explicitly lists the builders that produce the current corpus. Each case has:

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

Ensure multiple independent draw slots for selected models:

```bash
npm run bench -- --model google-gemini-3.5-flash --runs 3
```

`--runs 3` means “ensure draws 1–3 exist.” It reuses every valid cached slot and runs only missing model/case/draw combinations. The existing cache is draw 1, so requesting three draws after a normal run creates only draws 2 and 3.

Models run serially. Within each model, every case pipeline runs concurrently. Each pipeline sends the native PDF to the model and starts evaluation as soon as that case finishes. Google candidate request attempts, including automatic SDK retries, are started 15 seconds apart to remain below the strictest selected model's 5 RPM personal AI Studio limit.

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

Inference is reused only when the PDF bytes, conversion prompt, model configuration, and output limit match. Evaluation is reused only when the prediction, facts, evaluator model, and score-affecting settings match. Every successful evaluator batch is checkpointed immediately; if another batch fails or rate-limits, rerunning reuses both the completed model inference and completed evaluator batches and calls only the unfinished batches. Changes to provider transport, prompt caching, or pricing do not invalidate an otherwise identical score. A scoring-semantics change therefore rescores cached predictions without rerunning the model. Adding a new case runs only that missing case for previously cached models. Explicit `--model` flags run/check only those models; without flags, the command checks the default anchors plus every model already present in the cache.

After every invocation, the merged report is rebuilt from every model with at least one complete draw for the current manifest. Each draw is the equal-weight mean of its case scores; repeated models report the mean of those complete suite draws plus their range and sample SD. Operating cost, summed case-call latency, and output tokens are shown as means per draw so models with different draw counts remain comparable. Because cases run concurrently, summed case-call latency is not suite wall-clock time.

## Scoring

Gemini 3.1 Flash-Lite evaluates compact batches of candidate Markdown against source-anchored atomic obligations and classifies each obligation as correct, missing, or incorrect. Evaluator request starts are spaced six seconds apart (10 RPM) to leave headroom below the personal AI Studio project's 15 RPM free-tier limit while model cases remain concurrent. Collision-safe deterministic checks first pre-credit unambiguous table bindings, form states, and directed relationships, so the evaluator returns only unresolved obligations; ordered records and ambiguous or repeated locators stay with the semantic evaluator. Stable answer-key batches remain at the beginning of each Gemini API request so the provider's automatic implicit cache can reuse them across candidate models; reported cache-hit tokens are recorded. Each scoring request remains capped at 32 obligations. A separate conservative audit can penalize source-invented claims only within explicitly declared, source-grounded closed worlds. Corpus and answer-key quality are reviewed during benchmark development; the runtime command never grades the gold answers or runs a paid evaluator preflight.

The scorer has no case-ID branches or corpus-size assumptions. Case-specific knowledge belongs only in each case's `facts.json`, `gold.md`, and `spec.md`; generic runtime validation rejects rubric IDs or ungrounded members masquerading as source-visible closed-world keys. A leaf's `expectation` is the complete semantic contract sent to the evaluator, so non-obvious acceptable equivalents must be stated there. `evidencePolicy` aliases support conservative deterministic recognition and do not silently broaden that semantic contract.

## Editing cases

The committed PDFs are ready to run. To rebuild or inspect them:

```bash
npm run generate
npm run validate
npm run render
```

Case-generation code lives under `scripts/benchmark_cases/`. The original redesign objective is archived in `docs/benchmark-objective.md`; the current case coverage is summarized in `docs/case-challenge-profile.md`.
