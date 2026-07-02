# Dense Checkbox Matrix

Document ID: AE31-CHECKBOX-MATRIX

This packet tests whether a document conversion model preserves checked and unchecked states in an image-only matrix with near-duplicate row labels.

## Checkbox Matrix

![Dense checkbox matrix titled "Dense checkbox matrix - CHECK-31". The visible rows are: T-221 Aster Lab temp drift with Approve unchecked, Hold checked, Escalate unchecked, Notify checked; T-212 Aster Labs temp draft with Approve checked, Hold unchecked, Escalate unchecked, Notify unchecked; T-122 Beryl Ops seal gap with Approve unchecked, Hold checked, Escalate checked, Notify checked; T-121 Beryl Ops seal cap with Approve checked, Hold unchecked, Escalate unchecked, Notify checked; T-312 Cinder QA label tear with Approve unchecked, Hold checked, Escalate unchecked, Notify unchecked; T-321 Cinder AQ label year with Approve unchecked, Hold unchecked, Escalate checked, Notify checked.](non-text-element)

| Ticket | Account | Finding | Approve | Hold | Escalate | Notify |
| --- | --- | --- | --- | --- | --- | --- |
| T-221 | Aster Lab | temp drift | unchecked | checked | unchecked | checked |
| T-212 | Aster Labs | temp draft | checked | unchecked | unchecked | unchecked |
| T-122 | Beryl Ops | seal gap | unchecked | checked | checked | checked |
| T-121 | Beryl Ops | seal cap | checked | unchecked | unchecked | checked |
| T-312 | Cinder QA | label tear | unchecked | checked | unchecked | unchecked |
| T-321 | Cinder AQ | label year | unchecked | unchecked | checked | checked |

## Action

Preserve checked and unchecked states for each row exactly.
