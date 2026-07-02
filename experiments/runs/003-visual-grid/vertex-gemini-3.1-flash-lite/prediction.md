# Grid Audit Notice

**Document ID:** C3-GRID-MARKS

This notice tests whether a document conversion model can read a dense visual grid and preserve only the important marked cells.

## Instructions
- Describe the embedded board inline.
- Preserve the board identifier.
- List every red-bordered rewrite cell.
- Preserve the blue anchor path order.

## Visual grid audit - board GRID-913

Only red-bordered cells require rewrite. Blue cells define the anchor path.

[A 5x6 grid containing cells C01 through C30. Cells C02, C07, C13, C19, C24, and C30 have red borders. Cells C01, C08, C15, C22, and C29 have blue backgrounds and are marked with the text "PATH".]

| | | | | | |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **C01** (PATH) | **C02** (REWRITE) | **C03** | **C04** | **C05** | **C06** |
| **C07** (REWRITE) | **C08** (PATH) | **C09** | **C10** | **C11** | **C12** |
| **C13** (REWRITE) | **C14** | **C15** (PATH) | **C16** | **C17** | **C18** |
| **C19** (REWRITE) | **C20** | **C21** | **C22** (PATH) | **C23** | **C24** (REWRITE) |
| **C25** | **C26** | **C27** | **C28** | **C29** (PATH) | **C30** (REWRITE) |

[Legend: Red-bordered box labeled "red border = requires rewrite"; Light blue box labeled "blue fill = anchor path"]

Anchor path order: C01 -> C08 -> C15 -> C22 -> C29. Do not add C30 to the path.

## Action
Rewrite C02, C07, C13, C19, C24, and C30.
Keep the anchor path as C01 -> C08 -> C15 -> C22 -> C29.