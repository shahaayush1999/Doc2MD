# Bilingual Service Credit

Purpose: Recover bilingual form fields and checkbox state without flipping unchecked state.

Source modality: Raster-only bilingual service-credit form.

Expected gold objects:
- Spanish/English labels
- credit amount
- invoice
- checkbox states

Scoring checklist:
- Preserve bilingual values.
- Bind service delay and next visit.
- Do not mark pending part as selected.

Family: `forms`

Tags: `raster-only`, `bilingual`, `checkbox`
