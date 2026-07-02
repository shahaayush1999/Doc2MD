# Claims Processing Attachment

**Document ID:** D4-FORM-STATES

This attachment tests whether a document conversion model can reconstruct a visual form with checked boxes, unchecked boxes, and a selected radio decision.

## Form Screenshot

### Claims triage form - FORM-88Q
Checkbox state is part of the record. Do not infer unchecked options.

| Claim ID | Member | Plan | Visit date |
| :--- | :--- | :--- | :--- |
| CLM-2026-0719 | Iris Shah | Silver HSA | 2026-06-14 |
| **Provider NPI** | **Amount** | **Reviewer** | **Queue** |
| NPI-4410-77 | $1,284.60 | L. Rao | North-7 |

**Triage flags**
* [x] Address mismatch
* [ ] Duplicate claim
* [x] Manual review required
* [ ] Fraud suspected
* [x] Expedite within 48h
* [ ] Normal queue

**Decision**
* ( ) Approve
* ( ) Deny
* (◉) Hold

> **Reviewer note:**
> Needs W-9 before release; call member after address verification.

[A rectangular green stamp box containing the text "STAMP: HOLD UNTIL W-9"]

## Action
Hold CLM-2026-0719 until W-9 is received. Do not mark Fraud suspected.