# Doc2MD

Doc2MD is a benchmark for evaluating how accurately AI models convert documents into faithful Markdown. Given a document as input, the model should reconstruct its contents as a single Markdown document, preserving all textual information, document structure, tables, lists, headings, and other formatting where possible. Non-textual elements such as images, figures, diagrams, charts, and illustrations should be described in natural language and inserted inline at their appropriate locations. The objective is faithful reconstruction of the original document's information and reading experience, not summarization, interpretation, citation, or source attribution.

## Current Benchmark

The official benchmark is the native-PDF end-to-end path: the harness sends each PDF file directly to the provider and asks for one faithful Markdown reconstruction. Capability gates are part of the official run: they determine which depth-task groups a model is qualified to score on.

Each official case includes a `gold.md` answer key and `facts.json` weighted fact obligations. `npm run score` uses a Gemini 3.1 Flash Lite judge to mark each fact as correct, partial, incorrect, or missing, then computes accuracy from those fact labels. Deterministic checks are retained as an audit signal in each `score.json`.

Generate the benchmark:

```bash
npm run generate
```

Run the full benchmark:

```bash
npm run bench
```

The command runs model inference for every official gate and depth case, evaluates the outputs, and writes `runs/<model>/summary.json` and `runs/<model>/summary.official.json`. It is idempotent: unchanged model/case predictions and unchanged scores are skipped automatically. If one benchmark case changes, only that case is rerun. If a new model is added, only that model is run.

Repeated runs are append-only. To intentionally collect another sample for an unchanged model/case, use `--repeat`:

```bash
npm run run -- --model openai-gpt-5-nano --case P15-architecture-floorplan-diagrams --repeat
npm run score -- openai-gpt-5-nano
npm run summary -- openai-gpt-5-nano
```

Attempt data is written under `runs/<model>/<case>/attempts/<n>/`. Attempt folders are the only run data used by scoring and summaries.

The summary is deterministic: it averages current-fingerprint attempts per case, then applies capability gates. Gate cases are reported as pass/fail and do not add easy points to the official denominator. Depth cases report both `rawScore` and `finalScore`; a failed required gate sets the dependent depth case `finalScore` to zero. The official score is the page-weighted mean of depth-case final scores. The report also includes capability-group scores, qualified group scores, per-case attempt count, min, max, standard deviation, cost, time, and token counts. It does not use an AI model.

The configured benchmark model set is intentionally small while the benchmark is being designed:

- `openai-gpt-5-nano` with minimal thinking, the lowest setting supported by the API

All configured cases run in parallel by default. `vertex-gemini-3.1-flash-lite` is used for visual page audits and as the scoring evaluator, not as a regular benchmark anchor during cheap iteration.

The individual `run`, `score`, and `summary` scripts are kept for debugging a failed run.

Generated cases live under `benchmark/cases/`. Local run outputs and rendered inspection artifacts are ignored.
