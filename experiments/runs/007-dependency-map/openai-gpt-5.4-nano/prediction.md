# Dependency Review Brief

**Document ID:** G7-DEP-MAP

This brief tests whether a document conversion model can reconstruct a dependency diagram with near-duplicate node codes and visual edge state.

## Dependency Map

*Dependency map diagram present (DEP-44):* A directed graph with nodes **REQ-014**, **VAL-08B** (blocked), **VAL-0B8**, **MAP-731** (with both blocked/selected edge states shown), **HOLD-22** (blocked), and **SHIP-22**.  
- A **fallback-only** path is indicated with **dashed** edges.  
- **Red diamond** callouts mark **blocked** nodes/edges.

*Legend shown in the diagram:*  
**Green arrows** show the selected path. **Red diamonds** mark blocked nodes.

*Diagram details (as shown):*  
- **Selected path** runs: **REQ-014 → VAL-0B8 → MAP-731 → SHIP-22**.  
- **Blocked nodes**: **VAL-0B8** and **HOLD-22** are marked as blocked in the diagram.  
- **Fallback only**: **MAP-731 → HOLD-22** is dashed and not selected.

*Callout box text in the diagram:*  
- **Selected path:** REQ-014 → VAL-0B8 → MAP-731 → SHIP-22  
- **Blocked nodes:** VAL-08B and HOLD-22  
- **Fallback only:** MAP-713 → HOLD-22 is dashed and not selected  

*Additional note under the diagram:*  
**Important:** VAL-08B and VAL-0B8 are different codes; MAP-713 and MAP-731 are different nodes.

## Action

Proceed on **REQ-014 → VAL-0B8 → MAP-731 → SHIP-22**.  
Do not use blocked **VAL-08B** or **HOLD-22**.