# Doc2MD

Doc2MD is a benchmark for evaluating how accurately AI models convert documents into faithful Markdown. Given a document as input, the model should reconstruct its contents as a single Markdown document, preserving all textual information, document structure, tables, lists, headings, and other formatting where possible. Non-textual elements such as images, figures, diagrams, charts, and illustrations should be described in natural language and inserted inline at their appropriate locations. The objective is faithful reconstruction of the original document's information and reading experience, not summarization, interpretation, citation, or source attribution.

## Current Benchmark

Each case includes a `gold.md` answer key and `facts.json` weighted fact obligations. `npm run score` uses a Gemini 3.1 Flash Lite judge to mark each fact as correct, partial, incorrect, or missing, then computes accuracy from those fact labels. Deterministic checks are retained as an audit signal in each `score.json`.

Generate the benchmark:

```bash
npm run generate
```

Run the full benchmark:

```bash
npm run bench -- --model vertex-gemini-3.1-flash-lite --concurrency 3
```

The command runs model inference for every case, evaluates the outputs, and writes `runs/<model>/summary.json`. The summary is deterministic: it averages the case scores and sums cost, time, and token counts from the run metadata. It does not use an AI model.

The individual `run`, `score`, and `summary` scripts are kept for debugging a failed run.

Run the comparison set:

```bash
npm run bench -- --model vertex-gemini-3.5-flash --concurrency 3
npm run bench -- --model openai-gpt-5.4-nano --concurrency 3
npm run bench -- --model openai-gpt-5-nano --concurrency 3
```

Generated cases live under `benchmark/cases/`. Local run outputs and rendered inspection artifacts are ignored.
