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

Every invocation creates a new timestamped directory:

```text
runs/<timestamp>/
  summary.json
  report.html
  <model>/<case>/prediction.md
  <model>/<case>/inference.json
  <model>/<case>/score.json
```

The suite score is the equal-weight mean of all five case scores. If any case fails, the model's suite score is reported as incomplete. The summary and report include inference spend, evaluator spend, and per-case scores.

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
