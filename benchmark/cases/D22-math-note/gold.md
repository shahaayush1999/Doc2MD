# Lecture 12: Alignment Loss
Definition: Let B be a set of gold blocks and P be predicted blocks.
The alignment loss is zero only when every required block is matched once.

<!-- page 2 -->

## Theorem 1
If every block in B has a unique exact textual match in P and the reading order is preserved, then the block-order penalty is zero.
Proof: The monotone alignment maps each gold index to the same predicted index order.

<!-- page 3 -->

## Equations
$$L = 1 - \frac{|M|}{|B|}$$
$$R = \frac{2PR}{P+R}$$
where M is the matched block set, P is precision, and R is recall.
