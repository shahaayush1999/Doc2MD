# Complex Financial Table

Purpose: Recover financial table semantics, negative values, units, and footnote association.

Source modality: Raster-only financial table with multi-column measures and footnotes.

Expected gold objects:
- unit statement
- negative values
- segment rows
- footnote B association

Scoring checklist:
- Preserve parentheses as negative values.
- Bind SMB footnote to west-region churn.
- Do not make eliminations positive.

Family: `tables`

Tags: `raster-only`, `multi-row-header`, `footnotes`, `negative-values`
