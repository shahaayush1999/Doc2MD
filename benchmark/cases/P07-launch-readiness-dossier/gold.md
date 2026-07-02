# Northwest Pilot Launch Dossier

Prepared for the Retail Operations Steering Committee. Packet date: 2026-08-10. Status: conditional go.

## Executive Memo

The Northwest pilot is a conditional go. The visible steering decision supersedes the draft appendix. Hold criteria are: Bend POS exception open after 2026-08-12 17:00, payment-switch error rate above 1.2%, or Tier 2 backlog above 22 at launch review.

| Decision item | Owner | Due | State | Condition |
| --- | --- | --- | --- | --- |
| Gateway freight reserve | Iris | 2026-08-11 | Approved | $18.4k cap |
| Bend POS exception | Mateo | 2026-08-12 17:00 | Open | must close before go |
| Service desk staffing | Priya | 2026-08-13 09:00 | Conditional | Tier 2 backlog <= 22 |
| Signage reprint | Noah | deferred | Not funded | do not include in reserve |

## Launch Metrics Dashboard

Device activations by day: Monday 920, Tuesday 1280, Wednesday 1740, Thursday 2510, Friday 3220.

Backlog by queue: Tier 1 has 31 open and 12 blocked; Tier 2 has 19 open and 8 blocked; Partner has 9 open and 4 blocked; Fraud has 6 open and 2 blocked.

| Guardrail | Limit | Current | State |
| --- | --- | --- | --- |
| Payment-switch error rate | <=1.2% | 0.9% | OK |
| Tier 2 backlog | <=22 | 27 | At risk |
| Gateway inventory buffer | >=140 | 126 | Breach |
| Store training completion | >=95% | 92% | At risk |

Dashboard warning: review the guardrail table before launch review. From the guardrail table, gateway inventory buffer is breached at 126 and Tier 2 backlog is at risk at 27. Conditional go remains valid only if Bend POS closes and service-desk load returns inside threshold.

## Dependency Map

Required solid dependencies: POS terminals to Edge gateway; Handheld scanners to Edge gateway; Edge gateway to Payment switch; Payment switch to Acquirer A; Payment switch to Risk rules; Risk rules to Fraud desk; Payment switch to Settlement ledger. A dashed fallback path runs from Handheld scanners to Settlement ledger, but it does not satisfy payment authorization.

Bend POS exception is on the POS terminals to Edge gateway dependency.

## Store Readiness Register

| Store | Mgr | Training | Gateways | Signage | POS | Staffing | Open issue |
| --- | --- | --- | ---: | --- | --- | --- | --- |
| SEA-01 Pike | Mina | OK | 148 | OK | OK | OK | none |
| SEA-04 Ballard | Ravi | OK | 136 | OK | OK | AR | temp floor support |
| PDX-02 Pearl | Jon | OK | 142 | OK | OK | OK | none |
| PDX-05 East | Lena | AR | 131 | OK | OK | OK | training makeup Thu |
| BND-01 Bend | Mateo | OK | 126 | OK | BLK | OK | gateway exception |
| SPK-03 North | Asha | AR | 144 | OK | OK | AR | late completion |

BND-01 Bend is the only blocked POS row and has the lowest gateway count at 126. PDX-05 East and SPK-03 North are training risks. SEA-04 Ballard has staffing risk but training is OK.

## Escalation Matrix

Legend: G green clear; Y yellow watch; R red blocked. Slash means executive escalation. Dot means external partner required.

| Store | Training | Gateway | POS | Staffing | Partner |
| --- | --- | --- | --- | --- | --- |
| SEA-01 | G | G | G | G | G |
| SEA-04 | G | Y | G | Y | G |
| PDX-02 | G | G | G | G | Y with dot |
| PDX-05 | Y | Y with slash | G | G | G |
| BND-01 | G | R | R with slash | Y | R with slash and dot |
| SPK-03 | Y | G | G | Y | G |

Matrix reconstruction: BND-01 has red Gateway, red POS with slash, and red Partner with slash and dot. PDX-05 Gateway is yellow with slash, not red.

## Procurement and Reserve Ledger

| Line | Vendor | Purpose | Amount | Reserve eligible | Paid |
| --- | --- | --- | ---: | --- | --- |
| 1 | LumenWorks | gateway freight expedite | $12,640 | Yes | No |
| 2 | FieldBridge | temporary floor support | $5,760 | Yes | Partial $2,000 |
| 3 | SignPro | signage reprint | $3,480 | No | No |
| 4 | SwitchOps | payment monitor extension | $2,900 | Yes | No |
| 5 | Northstar Print | training packet reprint | $740 | No | Paid |

Reserve subtotal before payment is $21,300. FieldBridge partial payment is -$2,000. Remaining eligible reserve exposure is $19,300. PARTIAL PAID applies only to FieldBridge, not to the whole ledger. Signage reprint is not reserve eligible.

## Draft Appendix

The draft appendix is superseded and retained only for audit context. Draft GO, Tier 2 backlog 18, gateway inventory 158, Bend POS OK, and reserve exposure $17,300 must not replace final visible values: CONDITIONAL GO, Tier 2 backlog 27, gateway inventory 126, Bend POS BLK/open exception, and reserve exposure $19,300.
