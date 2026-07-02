# Weekly Ops Dashboard

Purpose: Recover KPI cards and chart facts from a dashboard page.

Source modality: Raster-only dashboard with KPI cards and a bar chart.

Expected gold objects:
- KPI values
- chart labels
- highest/fewest visual facts

Scoring checklist:
- Bind each KPI value to its card.
- Preserve chart extremum facts.
- Penalize reversed trend claims.

Family: `visual`

Tags: `raster-only`, `dashboard`, `chart`
