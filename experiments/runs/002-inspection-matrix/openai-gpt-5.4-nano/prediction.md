# Visual Exception Register

Document ID: B2-MATRIX-DENSE

This register tests whether a document conversion model can reconstruct a compact embedded inspection matrix without confusing visually similar labels.

## Review Rules

- Preserve row identifiers exactly.
- Keep owner names, statuses, severities, and deadlines attached to the correct row.
- Describe the routing note after the matrix.

## Inspection panel - matrix KITE-204

Read each row independently. Similar names are intentional.

| Row  | Exception   | Owner      | Severity | Status   | Deadline |
|------|-------------|-------------|----------|-----------|-----------|
| A-17 | Alpha valve | Mira Chen  | High     | **OPEN**  | Apr-17    |
| A-71 | Alpha value | Noor Iqbal  | Low      | **CLOSED** | May-03    |
| G-17 | Gamma valve | Vale Ortiz  | Medium   | **BLOCKED** | Jun-11    |
| B-19 | Beta gasket | Mira Chen  | High     | **OPEN**  | Jul-02    |

**Legend:**  
**OPEN** escalate now &nbsp;&nbsp; **CLOSED** archive &nbsp;&nbsp; **BLOCKED** needs review

[Figure: A horizontal process flow with four labeled checkpoints—R1 intake, R2 classify, R3 owner check, R4 final queue.]

Routing note: B-19 and A-17 are both high severity but only B-19 is already in R4 final queue.

## Action

Escalate A-17 and B-19. Review G-17. Archive A-71.