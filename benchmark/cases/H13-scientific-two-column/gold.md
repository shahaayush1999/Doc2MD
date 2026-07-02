# Sparse Retrieval With Patch Reranking

Abstract: We evaluate a patch reranker that improves table-region recall without changing OCR. The main result is a 6.3 point F1 gain on scanned appendices.

## 1. Method

The parser emits candidate blocks, then applies a patch reranker only to regions marked table-like or figure-like.

Equation 1: score = 0.62*T + 0.28*V + 0.10*R.

Table 1. Ablation: base recall 71.4 and F1 68.2; +patch recall 80.1 and F1 74.5; +caption recall 82.0 and F1 75.1.

## 2. Results

The caption-aware variant is strongest, but most of the gain comes from patch reranking. Failure cases cluster around equation/table boundaries.

Figure 2 retrieval path: PDF page -> patch grid -> reranker -> Markdown blocks. Caption: patch grid feeds the reranker before Markdown block assembly.

## 3. Limitations

The model still confuses marginal notes with captions when the note touches a figure border. Rotated labels were excluded from the pilot.

Reviewer note: Do not read this box before the Results section; it comments on Figure 2.

Footnote 1: F1 is macro-averaged over pages, not documents.
