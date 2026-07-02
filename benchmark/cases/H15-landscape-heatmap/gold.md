# Landscape Heatmap Escalation Plan

Page is shown in portrait, but the matrix is a landscape insert.

## Escalation heatmap: color + letter both matter

| Team | Mon | Tue | Wed | Thu | Fri | Sat |
| --- | --- | --- | --- | --- | --- | --- |
| API | G | Y | Y | R with slash | R | Y |
| Data | G | G | Y | Y | R with slash | R |
| Export | Y | Y | R with slash | R | Y | G |
| Billing | G | Y | G | Y | Y | R with slash |

Legend: G green normal; Y yellow watch; R red escalation. A diagonal slash means the owner must page the incident lead.

Reviewer instruction: derive the red slash cells from the matrix itself. Do not infer severity from row totals. Export Friday must be read directly from its cell.

Critical red slash cells: API Thu, Data Fri, Export Wed, and Billing Sat. Export Fri is yellow, not red. Weekend columns are part of the table and must not be dropped.
