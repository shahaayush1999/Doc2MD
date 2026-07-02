# Rasterized Rota Table

**Document ID:** AS45-RASTERIZED-ROTA-TABLE

This packet tests reconstruction of a normal table when the table is image-only.

## Rota Table Image

![Image of the rota table titled “Rasterized rota answer table - TABLE-45” showing a note that the table is image-only and a table with columns Resource, Assignment, Start, and End. The table rows list repeated resource names with their corresponding assignments and start/end times.](inline)

---

**Rasterized rota answer table - TABLE-45**  
This table is image-only. Preserve every row, resource, assignment, and Early/Late time cell.

| Resource    | Assignment | Start        | End          |
|-------------|------------|---------------|--------------|
| Nova Ops    | dock A1    | Mon 06 Early | Mon 06 Early |
| Nova Ops    | kit R7     | Tue 07 Late  | Wed 08 Early |
| Quarry Desk | audit Q1   | Mon 06 Early | Mon 06 Late  |
| Quarry Desk | swap N5    | Tue 07 Late  | Tue 07 Late  |
| Quarry Desk | seal L8    | Wed 08 Late  | Wed 08 Late  |
| Ritt QA      | case T2     | Mon 06 Late  | Mon 06 Late  |
| Ritt QA      | review D6   | Tue 07 Early | Tue 07 Late  |
| Ritt QA      | close X4    | Wed 08 Late  | Wed 08 Late  |

## Action

Convert the image table into Markdown. Do not drop repeated resource names.