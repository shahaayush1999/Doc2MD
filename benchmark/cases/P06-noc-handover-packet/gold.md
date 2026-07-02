# NOC Handover Packet - Week 32

Packet prepared for the 2026-08-03 reliability handoff.

The packet contains a cover page, raster shift Gantt, overlapping GTM timeline, borderless team matrix, and escalation heatmap. Several pages are image exports; some values are visual-only. Preserve page order and reconstruct each artifact where it appears.

## Raster Shift Gantt

# Raster Shift Gantt

| Task | Owner | Start | End | Label |
| --- | --- | --- | --- | --- |
| Dock intake | Noor | 08:00 | 11:00 | Load A-17 |
| Release gate | Ken | 10:00 | 16:30 | REL-82 |
| QA bench | Priya | 12:00 | 15:00 | Lot Q4 |
| Rollback watch | Mira | 16:00 | 18:00 | RB-9 |


## Overlapping GTM Timeline

# Overlapping GTM Timeline Slide

Investor update slide. Read each lane left-to-right; exported cards overlap.

Product lane: Beta signups runs in Aug, owner Maya, target 1,200. Workflow v2 runs Sep-Oct, owner Jon, ship Oct 18.

Security lane: SOC2 audit runs Aug-Oct, owner Priya, fieldwork. HIPAA BAA runs Oct-Nov, owner Lena, legal review.

Sales lane: Design partners runs in Aug, owner Omar, 9 accounts. Enterprise pilots runs Sep-Nov, owner Omar, $4.2M pipeline.

October dependency: HIPAA BAA belongs to Security, not Product. Enterprise pilots depend on BAA legal review.

Footer: Board packet GTM-09. Preserve lane, month span, owner, and dependency.


## Borderless Team Matrix

# Borderless Team Matrix Pitch Slide

Core team: Maya Singh is CEO / Product, ex-Stripe, has 12 yrs product experience, and led Relay launch. Jon Bell is CTO / Infra, ex-Snowflake, owns retrieval infra, and built vector cache. Priya Nair is COO / Ops, ex-Flexport, scaled support, and owns compliance. Omar Haddad is GTM / RevOps, ex-Atlassian, has pipeline $4.2M, and leads enterprise sales.

Advisors: Lena Ortiz - former CISO, Okta. Theo Park - ex-CFO, Datadog.

Hiring next: VP Sales - Q4. Clinical Lead - Q1.

Footer: Deck v12. Advisors are not core team members. Hiring rows are open roles, not current employees.


## Escalation Heatmap

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

