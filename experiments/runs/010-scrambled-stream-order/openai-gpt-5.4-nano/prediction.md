# Dispatch Runbook Sheet

Document ID: J10-STREAM-ORDER

This sheet tests whether a document conversion model preserves the visible reading order of extractable PDF text even when the PDF content stream is not in visual order.

## Dispatch Board

| Step | Code | Queue | Owner | Time  | Instruction |
|---:|:-----|:-------|:------|:------|:-------------|
| 5 | E-118 | QA | Atlas | 09:10 | Run the spot audit. |
| 2 | B-219 | Validate | Harbor | 08:25 | Check the manifest checksum. |
| 8 | H-906 | Notify | Vela | 09:55 | Notify the downstream owner. |
| 1 | A-104 | Intake | Redwood | 08:10 | Open the intake lane. |
| 6 | F-604 | Release | North | 09:25 | Release the approved set. |
| 3 | C-033 | Assign | Delta | 08:40 | Assign the review pair. |
| 7 | G-441 | Archive | Echo | 09:40 | Archive the signed copy. |
| 4 | D-772 | Pack | Solstice | 08:55 | Seal package batch four. |

## Action

Execute the rows in visible order from step 1 through step 8.

Do not reorder them by PDF extraction order.