# Visualization Rules

When the deliverable supports inline `chart` fences, produce:
1. rate-comparison bar chart for A vs B;
2. daily-rate trend chart(s) using the same rate/window semantics as the headline analysis.

For non-contiguous A/B periods, default to two stacked line charts with the same y-axis scale. Do not draw a continuous line across a calendar gap unless the renderer's gap behavior is explicitly verified.

For contiguous periods, a single continuous date-ordered line is acceptable.

Round chart values to 2 decimals. Do not generate fake CI error bars when the chart format does not support them.

If the environment does not support `chart` fences, omit charts or use the environment's supported visualization mechanism; do not invent PNG paths.
