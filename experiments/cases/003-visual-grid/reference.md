# Grid Audit Notice

Document ID: C3-GRID-MARKS

This notice tests whether a document conversion model can read a dense visual grid and preserve only the important marked cells.

## Instructions

- Describe the embedded board inline.
- Preserve the board identifier.
- List every red-bordered rewrite cell.
- Preserve the blue anchor path order.

![Visual grid audit titled "Visual grid audit - board GRID-913". Red-bordered rewrite cells are C02 ZN-104, C07 MX-219, C13 QH-550, C19 HG-017, C24 PR-605, and C30 ZR-038. Blue anchor path cells are C01 VA-201, C08 FO-118, C15 OP-314, C22 BM-221, and C29 ND-777. The legend says red border = requires rewrite and blue fill = anchor path. The anchor path order is C01 -> C08 -> C15 -> C22 -> C29. It explicitly says not to add C30 to the path.](non-text-element)

## Action

Rewrite C02, C07, C13, C19, C24, and C30. Keep the anchor path as C01 -> C08 -> C15 -> C22 -> C29.
