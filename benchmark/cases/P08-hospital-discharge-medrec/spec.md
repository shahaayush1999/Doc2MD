# Hospital Discharge Medication Reconciliation

Purpose: Stress a realistic discharge packet with lab units/flags, final-vs-draft medication state, selected actions, held/administered MAR states, visual vitals, and follow-up conflicts.

Source modality: Five-page medical discharge packet with mixed memo text, tables, checkboxes, chart, and draft/source-state conflict.

Expected gold objects:
- discharge summary
- lab trends
- medication reconciliation
- MAR grid
- referrals
- draft precedence

Scoring checklist:
- Preserve medication action state.
- Bind lab values to units, flags, and collection times.
- Do not treat held doses as administered.
- Keep draft footer superseded.

Family: `medical`

Tags: `multi-page`, `labs`, `med-rec`, `forms`, `timeline`, `source-precedence`, `chart`
