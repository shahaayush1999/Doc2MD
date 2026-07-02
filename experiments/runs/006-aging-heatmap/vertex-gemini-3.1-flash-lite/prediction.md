# Receivables Review Packet

Document ID: F6-AR-FLAGS

This packet tests whether a document conversion model can reconstruct only the flagged cells from a dense visual aging table.

## Heatmap

### Receivables aging heatmap - AR-77
Only cells with a red corner flag require extraction. Preserve row and bucket labels.

[A table showing an aging heatmap for six companies across five time buckets. Selected cells contain a red corner flag indicating they require extraction.]

| Account | 0-30 | 31-60 | 61-90 | 91-120 | 120+ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Acme North** | INV-104 $8.2k | INV-118 $6.1k | INV-137 $3.4k | INV-152 $9.9k | **INV-166 $2.0k** |
| **Beryl Labs** | INV-209 $4.7k | INV-221 $7.8k | INV-240 $12.4k | INV-255 $5.5k | **INV-271 $18.6k** |
| **Cinder Ops** | INV-305 $2.8k | INV-319 $9.1k | INV-336 $6.6k | INV-348 $13.2k | **INV-360 $4.4k** |
| **Delta Rail** | **INV-411 $11.7k** | INV-426 $3.9k | INV-437 $8.5k | INV-449 $21.3k | **INV-462 $7.1k** |
| **Echo Foods** | INV-508 $5.6k | INV-520 $10.2k | INV-533 $4.0k | INV-548 $6.8k | **INV-559 $16.9k** |
| **Fjord Media** | INV-604 $1.9k | INV-618 $8.8k | INV-631 $14.5k | INV-647 $5.2k | **INV-659 $22.4k** |

*Legend: [Red corner flag] = extraction required*

Instruction: report flagged cells only; do not report unflagged cells.

## Action

Review only the seven flagged cells. Do not include unflagged cells.