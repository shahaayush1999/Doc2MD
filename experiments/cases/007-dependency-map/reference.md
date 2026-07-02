# Dependency Review Brief

Document ID: G7-DEP-MAP

This brief tests whether a document conversion model can reconstruct a dependency diagram with near-duplicate node codes and visual edge state.

## Dependency Map

![Dependency map titled "Dependency map - DEP-44". The selected path is REQ-014 -> VAL-0B8 -> MAP-731 -> SHIP-22. Blocked nodes are VAL-08B and HOLD-22. A dashed gray fallback-only edge goes from MAP-713 to HOLD-22 and is not selected. Other non-selected dependencies are REQ-014 -> VAL-08B, VAL-08B -> MAP-713, VAL-0B8 -> MAP-713, and MAP-731 -> HOLD-22. The diagram warns that VAL-08B and VAL-0B8 are different codes, and MAP-713 and MAP-731 are different nodes.](non-text-element)

## Action

Proceed on REQ-014 -> VAL-0B8 -> MAP-731 -> SHIP-22. Do not use blocked VAL-08B or HOLD-22.
