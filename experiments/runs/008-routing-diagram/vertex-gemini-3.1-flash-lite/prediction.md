# Release Routing Appendix

Document ID: H8-ROUTE-TOPOLOGY

This appendix tests whether a document conversion model can reconstruct a routing diagram without relying on surrounding text to reveal the selected path.

## Routing Diagram

**Release routing diagram - ROUTE-19**
*Recover the selected route, blocked nodes, and fallback-only edges from the diagram.*

[Diagram description: A flow chart consisting of nodes labeled SRC-01, AUTH-A7, PACK-3L, QA-20, AUTH-7A, PACK-L3, QA-02, and REL-5. The nodes are connected by various arrows. A green arrow indicates the selected route, gray arrows indicate paths not selected, and dashed gray lines indicate fallback-only edges. Red "BLOCKED" text labels appear under the AUTH-A7 and QA-20 nodes.]

**Legend:**
*   **green arrows** = selected route; **gray arrows** = not selected; **dashed gray** = fallback only
*   **Fallback only:** PACK-3L -> QA-02 and AUTH-A7 -> PACK-L3
*   **Warning:** AUTH-A7 is not AUTH-7A; PACK-3L is not PACK-L3; QA-20 is not QA-02.

*Do not infer route from position alone; use green arrows only.*

## Action

Use the selected route shown in the diagram. Do not use blocked nodes.