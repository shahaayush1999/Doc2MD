# Release Routing Appendix

Document ID: H8-ROUTE-TOPOLOGY

This appendix tests whether a document conversion model can reconstruct a routing diagram without relying on surrounding text to reveal the selected path.

## Routing Diagram

![Release routing diagram titled "Release routing diagram - ROUTE-19". The selected route is SRC-01 -> AUTH-7A -> PACK-L3 -> QA-02 -> REL-5. Blocked nodes are AUTH-A7 and QA-20. Fallback-only dashed edges are PACK-3L -> QA-02 and AUTH-A7 -> PACK-L3. Other non-selected edges include SRC-01 -> AUTH-A7, AUTH-A7 -> PACK-3L, PACK-3L -> QA-20, AUTH-7A -> PACK-3L, PACK-L3 -> QA-20, and QA-20 -> REL-5. The diagram warns that AUTH-A7 is not AUTH-7A, PACK-3L is not PACK-L3, and QA-20 is not QA-02.](non-text-element)

## Action

Use the selected route shown in the diagram. Do not use blocked nodes.
