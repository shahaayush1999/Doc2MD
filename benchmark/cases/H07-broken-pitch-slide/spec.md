# Overlapping GTM Timeline Slide

Purpose: Recover an overlapping pitch-deck timeline by binding each card to lane, month span, owner, detail, and dependency.

Source modality: Raster-only investor update slide with month grid, swimlanes, overlapping cards, and dependency note.

Expected gold objects:
- lane-card bindings
- month spans
- owners
- dependency note
- footer

Scoring checklist:
- Bind each initiative to the correct lane.
- Preserve month spans and owners.
- Do not assign HIPAA BAA to Product.

Family: `layout`

Tags: `raster-only`, `slide`, `overlap`, `timeline`, `swimlanes`
