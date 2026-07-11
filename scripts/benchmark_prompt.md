Convert the attached PDF into one faithful Markdown document for downstream machine use.

Return only Markdown. Do not add commentary, citations, JSON, code fences, or an executive summary.

Reconstruct the document exhaustively:
- Process every page and every visible region in source order.
- Preserve all readable text, headings, section hierarchy, lists, captions, footnotes, stamps, annotations, handwritten-style fields, signatures, page-level notes, and document-state notes.
- Do not omit repetitive, dense, low-level, appendix, tabular, or visually embedded information just because it looks secondary.
- Do not paraphrase a table, schedule, matrix, register, ledger, checklist, or form into a summary when row/column/label/value relationships are present.

Tables, forms, and structured regions:
- Preserve every visible row, column, header, unit, label, value, subtotal, footnote marker, continuation row, blank/NA state, and row/column grouping.
- Use Markdown tables, HTML tables, or clear key-value lists only when the relationships remain unambiguous.
- Preserve checkbox/radio states, checked vs unchecked vs disabled states, strikeouts, insertions, corrections, voided values, and final/current values.

Visual and non-text regions:
- For charts, diagrams, maps, floorplans, screenshots, photos, timelines, heatmaps, chromatograms, scorecards, and other visual content, insert inline descriptions or tables at the location where the visual appears.
- Include labels, legends, axes, units, thresholds, colors, symbols, arrows, callouts, spatial relationships, and printed numeric values.
- If exact chart values are printed, include the exact values. If values are only visually inferable, describe the trend or approximate values without inventing precision.

Source-state conflicts:
- Rendered visible current content wins over hidden, stale, covered, deleted, or superseded PDF text.
- Preserve deleted/superseded/stale content only when it is visibly part of the document's reading experience, and clearly mark it as deleted, superseded, draft, historical, or context.
- If a visibly broken export still has legitimate selectable PDF text that is necessary to recover the document, use that recoverable text while preserving the visible document order.

The goal is faithful reconstruction of the original document's information and reading experience, not summarization or interpretation.
