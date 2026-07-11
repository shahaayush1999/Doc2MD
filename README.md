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

Ensure multiple independent draw slots for selected models:

```bash
npm run bench -- --model vertex-gemini-3.5-flash --runs 3
```

`--runs 3` means “ensure draws 1–3 exist.” It reuses every valid cached slot and runs only missing model/case/draw combinations. The existing cache is draw 1, so requesting three draws after a normal run creates only draws 2 and 3.

Models run serially. Within each model, all five case pipelines run concurrently. Each pipeline sends the native PDF to the model and starts evaluation as soon as that case finishes.

Results are cached per model and case:

```text
runs/cache/<model>/<case>/prediction.md
runs/cache/<model>/<case>/inference.json
runs/cache/<model>/<case>/score.json
runs/cache/<model>/<case>/draws/002/{prediction.md,inference.json,score.json}
runs/cache/<model>/<case>/draws/003/{prediction.md,inference.json,score.json}
reports/summary.json
reports/index.html
```

Inference is reused only when the PDF bytes, conversion prompt, model configuration, and output limit match. Evaluation is reused only when the prediction, facts, and evaluator implementation match. A scorer change therefore rescores cached predictions without rerunning the model. Adding a new case runs only that missing case for previously cached models. Explicit `--model` flags run/check only those models; without flags, the command checks the default anchors plus every model already present in the cache.

After every invocation, the merged report is rebuilt from every model with at least one complete draw for the current manifest. Each draw is the equal-weight mean of its five case scores; repeated models report the mean of those complete suite draws plus their range and sample SD. Operating cost, time, and output tokens are shown as means per draw so models with different draw counts remain comparable.

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
