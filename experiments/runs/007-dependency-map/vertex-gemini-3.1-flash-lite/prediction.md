# Dependency Review Brief

Document ID: G7-DEP-MAP

This brief tests whether a document conversion model can reconstruct a dependency diagram with near-duplicate node codes and visual edge state.

## Dependency Map

**Dependency map - DEP-44**
*Green arrows show the selected path. Dashed gray arrow is fallback only. Red diamonds mark blocked nodes.*

[Diagram: A flow chart showing two parallel paths. The top path starts at REQ-014, leads to VAL-08B (marked with a red diamond labeled "BLOCKED"), then to MAP-713, and finally to HOLD-22 (marked with a red diamond labeled "BLOCKED"). The connection between MAP-713 and HOLD-22 is a dashed gray line. The bottom path starts at REQ-014, leads to VAL-0B8, then to MAP-731, and finally to SHIP-22. All nodes and paths in the bottom sequence are outlined in green.]

| | |
| :--- | :--- |
| **Selected path:** | REQ-014 -> VAL-0B8 -> MAP-731 -> SHIP-22 |
| **Blocked nodes:** | VAL-08B and HOLD-22 |
| **Fallback only:** | MAP-713 -> HOLD-22 is dashed and not selected |

*Important: VAL-08B and VAL-0B8 are different codes; MAP-713 and MAP-731 are different nodes.*

## Action

Proceed on REQ-014 -> VAL-0B8 -> MAP-731 -> SHIP-22.
Do not use blocked VAL-08B or HOLD-22.