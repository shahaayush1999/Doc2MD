# NOC Handover Packet

Purpose: Stress realistic multi-page handover reconstruction with spatial spans, borderless alignment, and dense visual encodings.

Source modality: Five-page packet composed of exported slide/image artifacts and a cover page.

Expected gold objects:
- page order
- Gantt rows
- timeline lanes
- team matrix bindings
- heatmap semantics

Scoring checklist:
- Do not summarize the packet.
- Infer visual-only spans and cell states.
- Keep each artifact in page order.
- Bind facts to the correct lane, person column, team row, and day column.

Family: `packet`

Tags: `multi-page`, `raster-gantt`, `timeline`, `borderless-table`, `heatmap`, `visual-binding`
