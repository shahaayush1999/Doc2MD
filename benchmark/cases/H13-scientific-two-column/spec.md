# Scientific Paper With Embedded Table And Figure

Purpose: Recover paper reading order while preserving embedded table, equation, figure, sidebar, and footnote.

Source modality: Raster-only scientific page with three text columns and embedded visual objects.

Expected gold objects:
- abstract
- method equation
- ablation table
- figure path
- limitations
- reviewer note
- footnote

Scoring checklist:
- Preserve abstract before sections.
- Bind ablation values to variants.
- Describe Figure 2 path after results.
- Do not move reviewer note before results.

Family: `layout`

Tags: `raster-only`, `scientific-paper`, `multi-column`, `table`, `figure`, `footnote`
