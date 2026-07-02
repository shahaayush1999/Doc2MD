# Capacity Planning Snapshot

Document ID: E5-CHART-VALUES

This snapshot tests whether a document conversion model can reconstruct exact values from a multi-series visual chart.

## Dashboard

![Capacity dashboard titled "Capacity dashboard - CHART-52". Values are in thousands of requests. The legend has three series: North, South, and West. North values are Jan 42, Feb 39, Mar 51, and Apr 48. South values are Jan 31, Feb 44, Mar 40, and Apr 52. West values are Jan 27, Feb 35, Mar 46, and Apr 43. The alert says South Apr = 52 exceeds cap 50. The lowest callout says West Jan = 27 and says do not round. Monthly totals are Jan 100, Feb 118, Mar 137, and Apr 143. The note says South is not always highest; North leads in Jan and Mar.](non-text-element)

## Action

Escalate South Apr 52 because it exceeds cap 50. Keep West Jan as 27.
