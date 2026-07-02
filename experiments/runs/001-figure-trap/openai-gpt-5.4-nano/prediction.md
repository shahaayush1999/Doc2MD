# Quarterly Routing Memo

Document ID: A1-FIGURE-TRAP

This memo tests whether a document conversion model preserves normal text while also describing visual content that is embedded as images.

## Instructions

- Preserve the document identifier exactly.
- Keep the list structure intact.
- Insert descriptions of both figures at their original locations.

**Figure 1 description (inserted inline):** A pipeline control diagram titled “Pipeline control diagram - anchor VIS-3TB” shows four connected labeled stages in blue rounded boxes: **Upload PDF** → **Parse Blocks** → **Reconstruct Markdown** → **Score Output**, with right-pointing arrows between stages. A critical note below the diagram reads: “Critical note: preserve each stage label exactly; do not summarize this diagram.”

Critical note: preserve each stage label exactly; do not summarize this diagram.

The diagram above is not decorative. Its anchor code and stage labels are part of the document record.

## Quarterly token spend by reconstruction stage

**Figure 2 description (inserted inline):** A line chart titled “Quarterly token spend by reconstruction stage” with quarters labeled along the x-axis (**Q1**, **Q2**, **Q3**, **Q4**) and a horizontal red review-threshold line across the plot. A green line with points labeled **$12k** (at Q1), **$18k** (at Q2), **$17k** (at Q3), and **$29k** (at Q4) is connected across quarters. The chart includes red labels near the threshold reading **review threshold: $24k** and a red annotation at Q4 reading **$29k**.

Interpretation rule: Q1 crosses the review threshold; Q3 dips slightly below Q2.

## Action

| Trigger | Required handling |
|---|---|
| Delta exceeds 8% | Escalate |
| Chart appears decorative | Still describe it inline |