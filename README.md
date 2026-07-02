# Doc2MD

Doc2MD is a benchmark for evaluating how accurately AI models convert documents into faithful Markdown. Given a document as input, the model should reconstruct its contents as a single Markdown document, preserving all textual information, document structure, tables, lists, headings, and other formatting where possible. Non-textual elements such as images, figures, diagrams, charts, and illustrations should be described in natural language and inserted inline at their appropriate locations. The objective is faithful reconstruction of the original document's information and reading experience, not summarization, interpretation, citation, or source attribution.

Current benchmark planning is in [docs/benchmark-design.md](docs/benchmark-design.md). Initial calibration results are in [docs/hard-suite-results.md](docs/hard-suite-results.md).

## Hard Candidate Suite

The current runnable suite is **Doc2MD-Hard-12**, a compact benchmark focused on visible-vs-extractable conflicts, raster spatial normalization, complex table semantics, dense form state binding, dashboards, and nonlinear layouts.

Generate the benchmark:

```bash
npm run generate
```

Run one case:

```bash
npm run run -- --model vertex-gemini-3.1-flash-lite --case H03-raster-gantt
npm run score -- vertex-gemini-3.1-flash-lite
```

Run the full suite:

```bash
npm run run -- --model vertex-gemini-3.1-flash-lite
npm run score -- vertex-gemini-3.1-flash-lite
npm run summary -- vertex-gemini-3.1-flash-lite
```

Run the weak visual baseline after the suite is not saturated by Gemini:

```bash
npm run run -- --model vertex-gemini-3.5-flash
npm run score -- vertex-gemini-3.5-flash
npm run summary -- vertex-gemini-3.5-flash

npm run run -- --model openai-gpt-5.4-nano
npm run score -- openai-gpt-5.4-nano
npm run summary -- openai-gpt-5.4-nano

npm run run -- --model openai-gpt-5-nano
npm run score -- openai-gpt-5-nano
npm run summary -- openai-gpt-5-nano

npm run run -- --model openai-gpt-4o-mini
npm run score -- openai-gpt-4o-mini
npm run summary -- openai-gpt-4o-mini
```

Generated cases live under `benchmark/cases/`. Local run outputs and rendered inspection artifacts are ignored.
