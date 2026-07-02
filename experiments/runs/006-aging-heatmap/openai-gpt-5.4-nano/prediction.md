# Receivables Review Packet

Document ID: F6-AR-FLAGS

This packet tests whether a document conversion model can reconstruct only the flagged cells from a dense visual aging table.

## Heatmap

[Figure: Heatmap table titled “Receivables aging heatmap - AR-77”. Instruction text below the heatmap reads: “Only cells with a red corner flag require extraction. Preserve row and bucket labels.” A table follows with columns for age buckets (0–30, 31–60, 61–90, 91–120, 120+) and rows for account names (Acme North, Beryl Labs, Cinder Ops, Delta Rail, Echo Foods, Fjord Media). Some cells are highlighted in light red and contain invoice identifiers with amounts; the flagged cells are those with a red corner flag.]

**Receivables aging heatmap - AR-77**  
Only cells with a red corner flag require extraction. Preserve row and bucket labels.

| Account | 0-30 | 31-60 | 61-90 | 91-120 | 120+ |
|---|---|---|---|---|---|
| Acme North | INV-104<br>$8.2k | INV-118<br>$6.1k | INV-137<br>$3.4k | INV-162<br>$9.9k | INV-166<br>$2.0k |
| Beryl Labs | INV-209<br>$4.7k | INV-221<br>$7.8k | INV-240<br>$12.4k | INV-255<br>$5.5k | INV-271<br>$18.6k |
| Cinder Ops | INV-305<br>$2.8k | INV-319<br>$9.1k | INV-336<br>$6.6k | INV-348<br>$13.2k | INV-360<br>$4.4k |
| Delta Rail | INV-411<br>$11.7k | INV-426<br>$3.9k | INV-437<br>$8.5k | INV-449<br>$21.3k | INV-462<br>$7.1k |
| Echo Foods | INV-508<br>$5.6k | INV-520<br>$10.2k | INV-533<br>$4.0k | INV-548<br>$6.8k | INV-559<br>$16.9k |
| Fjord Media | INV-604<br>$1.9k | INV-618<br>$8.8k | INV-631<br>$14.5k | INV-647<br>$5.2k | INV-659<br>$22.4k |

[Figure note: A red corner flag marker appears at the bottom-left of the “Fjord Media” row under the 0–30 bucket.]

Instruction: report flagged cells only; do not report unflagged high-dollar cells.

## Action

Review only the seven flagged cells. Do not include unflagged cells.