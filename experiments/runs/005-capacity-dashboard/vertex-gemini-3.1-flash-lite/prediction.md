# Capacity Planning Snapshot

**Document ID:** E5-CHART-VALUES

This snapshot tests whether a document conversion model can reconstruct exact values from a multi-series visual chart.

## Dashboard

### Capacity dashboard - CHART-52
Values are in thousands of requests. Preserve each series separately.

[Line chart showing request volumes for North, South, and West regions from January to April. The North series starts at 42, moves to 39, rises to 51, and ends at 48. The South series starts at 31, rises to 44, drops to 40, and rises to 52. The West series starts at 27, rises to 35, rises to 46, and drops to 43.]

*   **ALERT:** South Apr = 52 exceeds cap 50
*   **LOWEST:** West Jan = 27 do not round

Monthly totals: Jan 100, Feb 118, Mar 137, Apr 143.
Note: South is not always highest; North leads in Jan and Mar.

## Action
Escalate South Apr 52 because it exceeds cap 50. Keep West Jan as 27.