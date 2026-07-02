# Action Ledger Stamps

**Document ID:** AG33-ACTION-LEDGER

This packet tests row-level checkbox states and visible stamps in an image-only ledger.

## Action Ledger

![Image: An “Exception action ledger - LEDGER-33” table showing columns Case, Client, Issue, Review, Call, Defer, and Stamp. Each row contains checkbox states (checked/unchecked/none) and a colored stamp label in the Stamp column for certain cases (e.g., RUSH, HOLD, REWORK, OK, none).]

**Exception action ledger - LEDGER-33**  
Checkbox state and row stamp are part of each exception record. Similar case IDs are intentional.

| Case | Client | Issue | Review | Call | Defer | Stamp |
|---|---|---|---|---|---|---|
| C-404 | Aster Lab | meter swap | ✅ | ⬜ | ⬜ | **RUSH** |
| C-440 | Aster Labs | meter snap | ⬜ | ✅ | ✅ | **HOLD** |
| C-414 | Beryl Ops | seal gap | ✅ | ✅ | ⬜ | none |
| C-441 | Beryl Ops | seal cap | ⬜ | ⬜ | ✅ | **REWORK** |
| C-044 | Cinder QA | label tear | ⬜ | ✅ | ⬜ | **OK** |
| C-404A | Cinder AQ | label year | ✅ | ⬜ | ✅ | **HOLD** |
| C-044A | Delta Rail | bolt pack | ⬜ | ⬜ | ⬜ | none |

**Rule:** preserve every checked, unchecked, and none state on the row where it appears.

## Action

Preserve every checked, unchecked, and none state on the row where it appears.