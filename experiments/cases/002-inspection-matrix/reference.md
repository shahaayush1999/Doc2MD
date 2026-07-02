# Visual Exception Register

Document ID: B2-MATRIX-DENSE

This register tests whether a document conversion model can reconstruct a compact embedded inspection matrix without confusing visually similar labels.

## Review Rules

- Preserve row identifiers exactly.
- Keep owner names, statuses, severities, and deadlines attached to the correct row.
- Describe the routing note after the matrix.

![Inspection panel titled "Inspection panel - matrix KITE-204". It contains four rows. A-17 is Alpha valve, owner Mira Chen, severity High, status OPEN, deadline Apr-17. A-71 is Alpha value, owner Noor Iqbal, severity Low, status CLOSED, deadline May-03. G-17 is Gamma valve, owner Vale Ortiz, severity Medium, status BLOCKED, deadline Jun-11. B-19 is Beta gasket, owner Mira Chen, severity High, status OPEN, deadline Jul-02. The legend maps OPEN to escalate now, CLOSED to archive, and BLOCKED to needs review. A routing line shows R1 intake, R2 classify, R3 owner check, and R4 final queue. The routing note says B-19 and A-17 are both high severity but only B-19 is already in R4 final queue.](non-text-element)

## Action

Escalate A-17 and B-19. Review G-17. Archive A-71.
