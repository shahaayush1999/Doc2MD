# Capacity Planning Snapshot

Document ID: E5-CHART-VALUES

This snapshot tests whether a document conversion model can reconstruct exact values from a multi-series visual chart.

## Dashboard

[Image: A multi-series line chart titled “Capacity dashboard - CHART-52” with three series (North, South, West) plotted across months Jan–Apr. Values are shown at each point: North = 42 (Jan), 39 (Feb), 51 (Mar), 48 (Apr); South = 31 (Jan), 44 (Feb), 40 (Mar), 52 (Apr); West = 27 (Jan), 35 (Feb), 46 (Mar), 43 (Apr). There is an alert box stating “South Apr = 52 exceeds cap 50” and a callout stating “LOWEST West Jan = 27 do not round”.]

### Capacity dashboard - CHART-52
Values are in thousands of requests. Preserve each series separately.

**Monthly totals:** Jan 100, Feb 118, Mar 137, Apr 143.

**Note:** South is not always highest; North leads in Jan and Mar.

## Action

Escalate South Apr 52 because it exceeds cap 50. Keep West Jan as 27.