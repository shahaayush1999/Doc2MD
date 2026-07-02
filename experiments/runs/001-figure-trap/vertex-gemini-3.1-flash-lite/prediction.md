# Quarterly Routing Memo

**Document ID: A1-FIGURE-TRAP**

This memo tests whether a document conversion model preserves normal text while also describing visual content that is embedded as images.

### Instructions
- Preserve the document identifier exactly.
- Keep the list structure intact.
- Insert descriptions of both figures at their original locations.

### Pipeline control diagram - anchor VIS-37B

![A flow diagram consisting of four blue rectangular boxes connected by red arrows pointing from left to right. The boxes are labeled: "Upload PDF", "Parse Blocks", "Reconstruct Markdown", and "Score Output".]

Critical note: preserve each stage label exactly; do not summarize this diagram.

The diagram above is not decorative. Its anchor code and stage labels are part of the document record.

### Quarterly token spend by reconstruction stage

![A line graph showing quarterly token spending. The x-axis lists Q1 through Q4. The y-axis represents cost in thousands of dollars. Data points show $12k in Q1, $18k in Q2, $17k in Q3, and $29k in Q4. A horizontal red line labeled "review threshold: $24k" spans the graph.]

Interpretation cue: Q4 crosses the review threshold; Q3 dips slightly below Q2.

### Action

| Trigger | Required handling |
| :--- | :--- |
| Delta exceeds 8% | Escalate |
| Chart appears decorative | Still describe it inline |