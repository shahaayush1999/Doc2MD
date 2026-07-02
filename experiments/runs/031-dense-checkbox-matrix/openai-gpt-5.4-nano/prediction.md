# Dense Checkbox Matrix

**Document ID:** AE31-CHECKBOX-MATRIX

This packet tests checked and unchecked states in an image-only matrix.

## Checkbox Matrix

[Image: A dense checkbox matrix labeled “Dense checkbox matrix - CHECK-31”, containing a table with columns Ticket, Account, Finding, Approve, Hold, Escalate, Notify. Rows T-221, T-212, T-122, T-121, T-312, and T-321 show combinations of checked/unchecked boxes in the action columns.]

**Dense checkbox matrix - CHECK-31**  
Checked boxes are part of the record. Similar ticket labels are intentional.

| Ticket | Account | Finding | Approve | Hold | Escalate | Notify |
|---|---|---|---|---|---|---|
| T-221 | Aster Lab | temp drift |  | ☑ |  | ☑ |
| T-212 | Aster Labs | temp draft | ☑ |  |  |  |
| T-122 | Beryl Ops | seal gap |  | ☑ | ☑ | ☑ |
| T-121 | Beryl Ops | seal cap | ☑ |  |  | ☑ |
| T-312 | Cinder QA | label tear |  | ☑ |  |  |
| T-321 | Cinder AQ | label year |  |  | ☑ | ☑ |

**Instruction:** preserve checked and unchecked states for each row; do not infer from nearby rows.  
Rows may have multiple checked boxes or none in a given action column.

## Action

Preserve checked and unchecked states for each row exactly.