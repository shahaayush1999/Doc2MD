# Continuation Register

Purpose: Recover a multi-page continued table with inherited group labels.

Source modality: Two raster pages with repeated headers, blank cells, and a ditto continuation.

Expected gold objects:
- continued table
- expanded group labels
- page policy

Scoring checklist:
- Bind inherited groups across pages.
- Preserve blocked/open statuses with correct owners and due dates.

Family: `tables`

Tags: `raster-only`, `multi-page-table`, `carry-down`
