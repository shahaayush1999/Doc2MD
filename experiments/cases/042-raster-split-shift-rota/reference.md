# Raster Split-Shift Rota

Document ID: AP42-SPLIT-SHIFT-ROTA

This packet tests whether a model can reconstruct a raster-only rota where day/shift placement and small conflict flags carry the document meaning.

## Split-Shift Rota Board

![Split-shift rota board titled "Split-shift rota board - ROTA-42". Days Mon 06 through Thu 09 are split into Early and Late columns. Rows are Nova Ops, Nova Ops East, Quarry Desk, Quarry Dock, and Rift QA. Red corner flags indicate conflict.](non-text-element)

| Resource | Assignment | Start | End | Flag |
| --- | --- | --- | --- | --- |
| Nova Ops | dock A1 | Mon 06 Early | Mon 06 Early | none |
| Nova Ops | kit R7 | Tue 07 Late | Wed 08 Early | none |
| Nova Ops | red flag C2 | Thu 09 Late | Thu 09 Late | conflict |
| Nova Ops East | scan B4 | Mon 06 Late | Tue 07 Early | none |
| Nova Ops East | hold Z9 | Wed 08 Late | Wed 08 Late | conflict |
| Nova Ops East | pack M3 | Thu 09 Early | Thu 09 Late | none |
| Quarry Desk | audit Q1 | Mon 06 Early | Mon 06 Late | none |
| Quarry Desk | swap N5 | Tue 07 Late | Tue 07 Late | conflict |
| Quarry Desk | seal L8 | Thu 09 Early | Thu 09 Early | none |
| Quarry Dock | load P6 | Tue 07 Early | Wed 08 Late | none |
| Quarry Dock | close V2 | Thu 09 Late | Thu 09 Late | none |
| Rift QA | case T2 | Mon 06 Late | Mon 06 Late | conflict |
| Rift QA | review D6 | Tue 07 Early | Tue 07 Late | none |
| Rift QA | close X4 | Thu 09 Late | Thu 09 Late | none |

## Action

Reconstruct Resource, Assignment, Start, End, and Flag. Include Early or Late in every time cell.
