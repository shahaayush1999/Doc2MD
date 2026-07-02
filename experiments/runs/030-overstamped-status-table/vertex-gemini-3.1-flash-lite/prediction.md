# Overstamped Status Table

Document ID: AD30-STAMP-STATUS

This packet tests row-specific visible stamps in an image-only table.

## Status Table

[A table titled "Overstamped status table - STAMP-30" showing six rows of data. Each row contains columns for Lot, Owner, Item, Printed status, Visible stamp, and Final visible state. The table includes visual stamps colored red for "HOLD", green for "RELEASE", and yellow for "RECHECK", which override or confirm the printed status in the final state column.]

| Lot | Owner | Item | Printed | Visible stamp | Final visible state |
| :--- | :--- | :--- | :--- | :--- | :--- |
| LOT-88A | Iris Shah | Valve A | READY | HOLD | HOLD |
| LOT-88B | Iris Shah | Valve B | HOLD | RELEASE | RELEASE |
| LOT-8BA | Noor Vale | Seal kit | READY | none | READY |
| LOT-8AB | Noor Vale | Seal kite | HOLD | RECHECK | RECHECK |
| LOT-80A | Mira Chen | Cap ring | READY | HOLD | HOLD |
| LOT-08A | Mira Chan | Cup ring | HOLD | none | HOLD |

> Rule: a stamp changes only the row it appears on. Rows with stamp none keep the printed status. Near-duplicate lot IDs and owner names are intentional.

## Action

Preserve each row's printed status, visible stamp, and final visible state.