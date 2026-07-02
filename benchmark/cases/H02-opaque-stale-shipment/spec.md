# Opaque Stale Shipment Overlay

Purpose: Ensure an opaque rendered overlay beats stale text underneath.

Source modality: Stale extractable text is drawn first, then covered by an opaque raster card.

Expected gold objects:
- shipment fields
- status/port/ETA binding
- covered stale text policy

Scoring checklist:
- Preserve visible delayed Osaka ETA values.
- Penalize stale ON TIME Busan values.

Family: `visibility`

Tags: `covered-text`, `raster-card`, `negative-check`
