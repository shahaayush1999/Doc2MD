# Layout-Aware Markdown Reconstruction
Authors: Mira Halden, Arun Dev, Keiko Sato

## Abstract
We evaluate whether multimodal models can recover document reading order, table structure, and inline visual references from born-digital PDFs.
The proposed metric, Doc2MD-F, combines block alignment with visual fact checks.

Keywords: document parsing; Markdown; multimodal evaluation

<!-- page 2 -->

## 1. Introduction
Faithful document conversion is different from question answering. A model can answer a local question while omitting most of the document.
Our benchmark asks for a single Markdown artifact, not a summary.

Footnote 1: We treat repeated page numbers as optional boilerplate.

<!-- page 3 -->

## 2. Method
The block alignment score is defined as:
$$S = 0.25T + 0.20R + 0.20Q + 0.10F + 0.10V + 0.10M + 0.05C$$
where T is text fidelity, R is reading order, Q is table quality, F is form quality, V is visual fact quality, M is math/code quality, and C is Markdown cleanliness.

![Diagram: Figure 1. Evaluation pipeline. Flow: PDF input > model conversion > Markdown parse > block alignment > family score. The family score prevents a high text score from hiding poor visual reconstruction.]

<!-- page 4 -->

## 3. Results
| Model | Text | Tables | Visuals | Overall |
| --- | ---: | ---: | ---: | ---: |
| Model A | 93.1 | 71.4 | 64.0 | 81.2 |
| Model B | 90.5 | 88.2 | 52.5 | 82.6 |
| Model C | 86.0 | 79.0 | 76.5 | 80.5 |

Model B has the highest overall score but the lowest visual score.

<!-- page 5 -->

## References
[1] Clark et al. Structured document evaluation. 2024.
[2] Lin et al. Table grid similarity. 2025.
[3] Nair and Gomez. Visual fact extraction for charts. 2026.
