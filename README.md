# Doc2MD

Doc2MD is a benchmark for evaluating how accurately AI models convert documents into faithful Markdown. Given a document as input, the model should reconstruct its contents as a single Markdown document, preserving all textual information, document structure, tables, lists, headings, and other formatting where possible. Non-textual elements such as images, figures, diagrams, charts, and illustrations should be described in natural language and inserted inline at their appropriate locations. The objective is faithful reconstruction of the original document's information and reading experience, not summarization, interpretation, citation, or source attribution.

Current benchmark planning is in [docs/benchmark-design.md](docs/benchmark-design.md).

## Current Benchmark

The first runnable suite is **Doc2MD-Core-25**, generated from source with:

```bash
npm run generate
```

Run Gemini 3.1 Flash Lite on the full suite:

```bash
npm run run
npm run score
npm run summary
```

Generated cases live under `benchmark/cases/`. Model outputs and scores live under `runs/`.

The first Gemini 3.1 Flash Lite baseline is summarized in [docs/gemini-3.1-flash-lite-run.md](docs/gemini-3.1-flash-lite-run.md).
