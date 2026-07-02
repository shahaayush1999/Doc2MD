# Model Calibration Under Label Drift

Authors: A. Rao, L. Chen, M. Iqbal.

Abstract: The paper evaluates calibration under label drift using ten bins and a drift prior. Replay buffer improves F1 while lowering ECE.

Equation: ECE = sum_b (n_b / n) * |acc(b) - conf(b)|, with B = 10.

| Method | ECE down | F1 up |
| --- | ---: | ---: |
| Baseline | 0.087 | 0.781 |
| + temperature scaling | 0.041 | 0.779 |
| + drift prior | 0.033 | 0.802 |
| + replay buffer | 0.029 | 0.817 |

Sidebar note: do not read this before the ablation table. It explains why the replay buffer row is kept despite higher storage cost.

Figure 2: dashed diagonal is perfect calibration. The model curve falls below the diagonal above confidence 0.75 and is annotated "over-confident above 0.75."

## Supplement Table S1

| Cohort | Shift | n | ECE | F1 | Note |
| --- | --- | ---: | ---: | ---: | --- |
| A | none | 1200 | 0.029 | 0.817 | baseline final |
| B | mild | 840 | 0.034 | 0.804 | uses drift prior |
| C | moderate | 610 | 0.052 | 0.781 | see footnote 1 |
| D | severe | 455 | 0.071 | 0.744 | fails threshold |
| E | recovered | 500 | 0.038 | 0.799 | replay restored |
| Total | | 3605 | | | do not average ECE from this row |

Footnote 1: Cohort C excludes 17 records with missing confidence, so reported n is after exclusion. The total row is a count total, not an ECE average.

## Supplement Figure S2 - Drift Error Matrix

Legend: L means low error, M means medium error, and H means high error. A slash means manual review required.

| Cohort | 0.50 | 0.60 | 0.70 | 0.80 | 0.90 |
| --- | --- | --- | --- | --- | --- |
| A none | L | L | M | M | H |
| B mild | L | M | M | H | H |
| C moderate | M | M | H | H with slash | H |
| D severe | M | H | H with slash | H | H |
| E recovered | L | M with slash | M | H | M |

Cohort D has high error in every bin from 0.60 through 0.90. E recovered at 0.90 is medium, not high.
