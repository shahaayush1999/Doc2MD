# Northwest Pilot Readiness Review

## Executive memo and decision register

The launch covers six stores, two fulfillment nodes, and three payment partners. Friday's activation target is 4,850 devices. Spokane North completed training after the scheduled cutover rehearsal; Bend still has one open POS-to-gateway exception.

Finance approved reserve use for gateway freight and temporary floor support only. The Portland service desk remains above its Tier 2 launch threshold after the weekend migration. Signage reprint is deferred and is not reserve eligible.

Authorize the six-store pilot for the 14 August 2026 launch window, subject to closure of the Bend gateway exception and recovery of Tier 2 service-desk backlog to the approved limit.

Decision: **CONDITIONAL GO**. Hold conditions are Bend open after 2026-08-12 17:00, payment-switch errors above 1.2%, or Tier 2 backlog above 22.

| Item | Owner | Due | State | Condition |
| --- | --- | --- | --- | --- |
| Gateway freight reserve | Iris Wu | 11 Aug | Approved | $18.4k cap |
| Bend POS exception | Mateo Ruiz | 12 Aug 17:00 | Open | close before go |
| Service desk staffing | Priya Nair | 13 Aug 09:00 | Conditional | Tier 2 <= 22 |
| Signage reprint | Noah Klein | Deferred | Not funded | outside reserve |

## Launch metrics

Device activations: Mon 920, Tue 1280, Wed 1740, Thu 2510, Fri 3220.

Backlog values are open / blocked: Tier 1 31 / 12, Tier 2 27 / 8, Partner 9 / 4, Fraud 6 / 2. Blocked counts are subsets of open backlog, not additional queue totals. The traffic-light convention is Inside = limit met, Watch = caution, and Outside = limit missed. Snapshot is through Friday 16:00 PT.

| Guardrail | Current | Limit | State |
| --- | --- | --- | --- |
| Payment-switch errors | 0.9% | <= 1.2% | Inside |
| Tier 2 backlog | 27 | <= 22 | Outside |
| Gateway spare units | 126 | >= 140 | Outside |
| Training completion | 92% | >= 95% | Outside |

## Payment and device dependencies

Required directed edges are POS terminals -> Edge gateway; Handheld scanners -> Edge gateway; Edge gateway -> Payment switch; Payment switch -> Acquirer A, Risk rules, and Settlement ledger; and Risk rules -> Fraud desk. A dashed monitoring-only event-copy path runs from Handheld scanners -> Settlement ledger. EX-214 is the open Bend POS-to-gateway handshake exception.

| Mark | Meaning | State |
| --- | --- | --- |
| Solid | Authorization or control path | Required |
| Dashed | Scanner event copy to settlement | Monitoring only |
| EX-214 | Bend POS-to-gateway handshake | Open |

## Store readiness

| Store | Owner | Training | Gateways | Signage | POS | Staffing | Open item |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PDX-02 Pearl | Lena | OK | 144 | OK | OK | OK | partner token |
| PDX-05 East | Owen | Watch | 148 | OK | OK | OK | coach shift |
| SEA-04 Ballard | Nia | OK | 151 | OK | OK | Watch | late coverage |
| SPK-03 North | Eli | Watch | 146 | OK | OK | OK | retest logged |
| BND-01 Bend | Mateo | OK | 126 | OK | Blocked | OK | EX-214 gateway |
| EUG-02 River | Sara | OK | 143 | Watch | OK | OK | signage ETA |

- PDX-05 coach shift is scheduled before the Thursday close rehearsal.
- SPK-03 training retest is logged; the dashboard still shows the packet-time Watch state.
- BND-01 replacement gateway is staged at the Redmond depot; courier release remains pending EX-214 closure.
- EUG-02 signage ETA does not use gateway reserve funds.

Owners reconvene 13 August at 09:00 PT. Store states are frozen to the 10 August 15:30 PT packet cut; later field updates require an annotated change record.

## Escalation matrix

Legend: G = clear; Y = watch; R = blocked; slash = executive escalation; dot = external-partner action.

| Store | Gateway | POS | Staffing | Partner |
| --- | --- | --- | --- | --- |
| PDX-02 | G | G | G | Y. |
| PDX-05 | Y/ | G | G | G |
| SEA-04 | G | G | Y | G |
| SPK-03 | G | Y | G | G |
| BND-01 | R | R/ | Y | R/. |
| EUG-02 | G | G | G | Y |

## Launch reserve ledger

| Vendor | Purpose | Invoice | Eligibility | Paid | Exposure |
| --- | --- | --- | --- | --- | --- |
| LumenWorks | gateway freight | $12,640 | Eligible | $0 | $12,640 |
| FieldBridge | floor support | $5,760 | Eligible | $2,000 | $3,760 |
| SignPro | signage reprint | $3,480 | Not eligible | $0 | $0 |
| SwitchOps | monitoring cover | $2,900 | Not eligible | $0 | $0 |
| Northstar Print | counter cards | $740 | Not eligible | $740 | $0 |

| Line | Amount |
| --- | --- |
| Eligible invoices before payments | $18,400 |
| FieldBridge payment applied | -$2,000 |
| Remaining eligible exposure | $16,400 |

Partial payment applies only to FieldBridge. Non-eligible invoices do not consume launch reserve.

Finance controller Iris Wu approved the $18,400 eligible invoice base on 9 August. The $2,000 FieldBridge payment posted on 10 August at 12:40 PT; the reconciliation above is after that posting.

## Superseded appendix

Appendix C version 0.7 was superseded in full by OPS-NW-26-08 on 2026-08-10 at 09:15 PT. Its values remain historical and are not current.

| Field | Working value | Status on 7 Aug |
| --- | --- | --- |
| Steering decision | GO | draft |
| Tier 2 backlog | 18 | draft |
| Gateway spare units | 158 | draft |
| Bend POS | OK | draft |
| Reserve exposure | $17,300 | draft |
