# Insurance Explanation of Benefits

Purpose: Recover an EOB table, summary card, deadline, and selected network state.

Source modality: Raster-only explanation-of-benefits page.

Expected gold objects:
- claim identity
- network checkbox state
- claim table
- summary card
- appeal deadline

Scoring checklist:
- Preserve row-level money values.
- Do not treat the document as a bill.
- Preserve selected and unselected network states.

Family: `forms`

Tags: `raster-only`, `insurance`, `checkbox`, `summary-card`, `financial-table`
