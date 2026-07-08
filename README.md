# Doc2MD

Doc2MD is a benchmark for evaluating how accurately AI models convert documents into faithful Markdown. Given a document as input, the model should reconstruct its contents as a single Markdown document, preserving all textual information, document structure, tables, lists, headings, and other formatting where possible. Non-textual elements such as images, figures, diagrams, charts, and illustrations should be described in natural language and inserted inline at their appropriate locations. The objective is faithful reconstruction of the original document's information and reading experience, not summarization, interpretation, citation, or source attribution.

## Current Benchmark

The official benchmark is the native-PDF end-to-end path: the harness sends each PDF file directly to the provider and asks for one faithful Markdown reconstruction. There are no capability gates in the official score; every case is scored directly on the quality of the returned Markdown.

Each official case includes a `gold.md` answer key and `facts.json` weighted fact obligations. `npm run score` uses a Gemini 3.1 Flash Lite judge to mark each fact as correct, partial, incorrect, or missing, then computes accuracy from those fact labels. Deterministic checks are retained as an audit signal in each `score.json`.

Generate the benchmark:

```bash
npm run generate
```

Run the full benchmark:

```bash
npm run bench
```

The command runs model inference for every official case, evaluates the outputs, and writes `runs/<model>/summary.json` and `runs/<model>/summary.official.json`. It is idempotent: unchanged model/case predictions and unchanged scores are skipped automatically. If one benchmark case changes, only that case is rerun. If a new model is added, only that model is run.

To intentionally rerun and overwrite cached outputs for an unchanged model/case, use `--force`:

```bash
npm run run -- --model openai-gpt-5-nano --case P15-architecture-floorplan-diagrams --force
npm run score -- openai-gpt-5-nano
npm run summary -- openai-gpt-5-nano
```

Run data is written as one flat cached result per model/case:

```text
runs/<model>/<case>/prediction.md
runs/<model>/<case>/result.json
runs/<model>/<case>/score.json
```

The summary is deterministic: it uses the current-fingerprint `score.json` for each case and computes the official score as the page-weighted mean of case scores. The report includes per-case score, cost, time, and token counts. It does not use an AI model.

The configured benchmark model set is intentionally small while the benchmark is being designed:

- `openai-gpt-5-nano` with minimal thinking, the lowest setting supported by the API

All configured cases run in parallel by default. `vertex-gemini-3.1-flash-lite` is used as the scoring evaluator.

The individual `run`, `score`, and `summary` scripts are kept for debugging a failed run.

Generated cases live under `benchmark/cases/`. Local run outputs and rendered inspection artifacts are ignored.
