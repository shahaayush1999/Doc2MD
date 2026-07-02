# Insurance Intake Form

Purpose: Reconstruct selected and blank form fields without inventing values.

Source modality: Raster-only insurance-style intake form with selected/unselected boxes, stamp, and signature.

Expected gold objects:
- claim fields
- blank prior auth
- checkbox states
- stamp/signature

Scoring checklist:
- Mark prior auth as blank.
- Distinguish selected from unselected coverage boxes.
- Preserve review stamp and signature.

Family: `forms`

Tags: `raster-only`, `checkbox`, `stamp`, `blank-field`
