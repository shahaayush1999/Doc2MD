# Table 2. Ablation Results
Caption: Accuracy and calibration error across reconstruction variants.
| Variant | Encoder | OCR source | F1 (%) | ECE (%) | Notes |
| --- | --- | --- | ---: | ---: | --- |
| A0 | ViT-B | native text | 84.2 | 7.1 | baseline |
| A1 | ViT-L | native text | 87.9 | 5.8 | larger encoder |
| A2 | ViT-L | raster only | 81.3 | 9.4 | no text layer |
| A3 | ViT-L | hybrid | 89.1 | 4.9 | best overall |

<!-- page 2 -->

Symbols: ECE means expected calibration error. The dagger marker indicates p < 0.05.
Finding: A3 hybrid has the highest F1 and lowest ECE.
Footnote: Native text is unavailable for scanned documents.
