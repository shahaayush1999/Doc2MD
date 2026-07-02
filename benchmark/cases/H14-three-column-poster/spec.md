# Borderless Team Matrix Pitch Slide

Purpose: Recover a borderless pitch-deck team matrix by binding facts under each name column.

Source modality: Raster-only pitch slide with names as column headers, unlabeled visual alignment, advisor sidebar, and open-role box.

Expected gold objects:
- person-to-fact bindings
- row label semantics
- advisors separate from core team
- hiring roles separate from employees
- footer

Scoring checklist:
- Bind each person to role, former company, proof, and ownership facts.
- Do not merge row-wise facts across people.
- Do not treat advisors or open roles as core team members.

Family: `layout`

Tags: `raster-only`, `pitch-slide`, `borderless-table`, `team-matrix`, `advisor-sidebar`
