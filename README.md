# Doc2MD

Doc2MD measures how faithfully a model converts a PDF into one Markdown document. It tests exhaustive recovery of text, tables, forms, visual information, reading order, source precedence, and long-document coherence—not summarization.

The benchmark contains five cases and 84 pages under `benchmark/cases/`. Each case has:

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

Set the relevant provider keys in `.env.local`. The default run uses the two inexpensive anchors:

- `openai-gpt-5-nano`
- `vertex-gemini-3.1-flash-lite`

Select any registered model with repeatable flags:

```bash
npm run bench -- --model openai-gpt-5.4-nano --model vertex-gemini-3.1-flash-lite
```

Models run serially. Within each model, all five case pipelines run concurrently. Each pipeline sends the native PDF to the model and starts evaluation as soon as that case finishes.

Results are cached per model and case:

```text
runs/cache/<model>/<case>/prediction.md
runs/cache/<model>/<case>/inference.json
runs/cache/<model>/<case>/score.json
reports/summary.json
reports/index.html
```

Inference is reused only when the PDF bytes, conversion prompt, model configuration, and output limit match. Evaluation is reused only when the prediction, facts, and evaluator implementation match. A scorer change therefore rescores cached predictions without rerunning the model. Adding a new case runs only that missing case for previously cached models. Explicit `--model` flags run/check only those models; without flags, the command checks the default anchors plus every model already present in the cache.

After every invocation, the merged report is rebuilt from every model with a complete cache for the current manifest. The suite score is the equal-weight mean of all case scores. The report includes inference spend, evaluator spend, and per-case scores.

## Scoring

Gemini 3.1 Flash-Lite evaluates the candidate Markdown against the case's atomic obligations. Each obligation is classified as correct, missing, or incorrect and must cite candidate lines. Deterministic evidence checks verify table bindings, form states, directed relationships, ordered records, source precedence, and closed-world hallucinations. This scoring logic is the benchmark's core and remains intentionally strict.

## Editing cases

The committed PDFs are ready to run. To rebuild or inspect them:

```bash
npm run generate
npm run validate
npm run render
```

Case-generation code lives under `scripts/benchmark_cases/`. The benchmark objective is documented in `docs/benchmark-objective.md`; the case coverage is summarized in `docs/case-challenge-profile.md`.
