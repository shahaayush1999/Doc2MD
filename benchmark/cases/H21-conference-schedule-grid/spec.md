# Conference Schedule Grid

Purpose: Recover a time-by-room schedule grid with room-spanning cells and icon legend semantics.

Source modality: Raster-only conference schedule with merged cells and legend icons.

Expected gold objects:
- time/room grid
- merged-room sessions
- all-room sessions
- icon legend

Scoring checklist:
- Preserve room spans and blank cells.
- Bind icons to their legend meanings.
- Do not duplicate merged sessions into wrong rooms without noting the span.

Family: `spatial`

Tags: `raster-only`, `schedule`, `merged-cells`, `icons`, `room-grid`
