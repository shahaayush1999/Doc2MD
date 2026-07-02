# Dense State Matrix

Purpose: Bind dense YES/NO states to near-duplicate row labels.

Source modality: Raster-only state matrix.

Expected gold objects:
- state matrix rows
- row labels
- legend/policy

Scoring checklist:
- Score row-level state binding.
- Penalize collapsed similar IDs.

Family: `forms`

Tags: `raster-only`, `checkbox`, `state-binding`
