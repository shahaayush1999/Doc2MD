# Action Ledger Stamps

Document ID: AG33-ACTION-LEDGER

This packet tests whether a document conversion model preserves row-level checkbox state and visible stamps in an image-only exception ledger.

## Action Ledger

![Exception action ledger titled "Exception action ledger - LEDGER-33". The visible rows are: C-404 Aster Lab meter swap with Review checked, Call unchecked, Defer unchecked, Stamp RUSH; C-440 Aster Labs meter snap with Review unchecked, Call checked, Defer checked, Stamp HOLD; C-414 Beryl Ops seal gap with Review checked, Call checked, Defer unchecked, Stamp none; C-441 Beryl Ops seal cap with Review unchecked, Call unchecked, Defer checked, Stamp REWORK; C-044 Cinder QA label tear with Review unchecked, Call checked, Defer unchecked, Stamp OK; C-404A Cinder AQ label year with Review checked, Call unchecked, Defer checked, Stamp HOLD; C-044A Delta Rail bolt pack with Review unchecked, Call unchecked, Defer unchecked, Stamp none.](non-text-element)

| Case | Client | Issue | Review | Call | Defer | Stamp |
| --- | --- | --- | --- | --- | --- | --- |
| C-404 | Aster Lab | meter swap | checked | unchecked | unchecked | RUSH |
| C-440 | Aster Labs | meter snap | unchecked | checked | checked | HOLD |
| C-414 | Beryl Ops | seal gap | checked | checked | unchecked | none |
| C-441 | Beryl Ops | seal cap | unchecked | unchecked | checked | REWORK |
| C-044 | Cinder QA | label tear | unchecked | checked | unchecked | OK |
| C-404A | Cinder AQ | label year | checked | unchecked | checked | HOLD |
| C-044A | Delta Rail | bolt pack | unchecked | unchecked | unchecked | none |

## Action

Preserve every checked, unchecked, and none state on the row where it appears.
