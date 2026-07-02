# Acme Operations Memo
Document ID: D01-POL-447
Effective date: 2026-08-01
Owner: Revenue Operations

## Purpose
This memo defines the weekly close procedure for partner-sourced revenue.
The close owner must preserve ticket IDs, exception labels, and approval notes exactly.

## Procedure
1. Export the source ledger by 10:00 UTC each Monday.
2. Reconcile Stripe, reseller, and manual invoice totals.
3. Mark unresolved deltas as Exception R-7, Exception R-8, or Exception R-9.
4. Send the final Markdown close note to #revops-close.

### Required approvals
- Finance reviewer: Priya Menon
- Data reviewer: Omar Chen
- Executive reviewer: Lina Patel

> Boxed note: Do not summarize partner exceptions; copy the exception labels exactly.

<!-- page 2 -->

# Acme Operations Memo
## Appendix A: Exception Labels

| Label | Meaning | Default owner | SLA |
| --- | --- | --- | --- |
| Exception R-7 | Currency mismatch | Finance reviewer | 24h |
| Exception R-8 | Missing reseller remittance | Partner ops | 48h |
| Exception R-9 | Manual invoice not linked | Revenue systems | 24h |

Footer policy: page numbers and the document ID may be preserved once, but repeated boilerplate should not replace body content.
