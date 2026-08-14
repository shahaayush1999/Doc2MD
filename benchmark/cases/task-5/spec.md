# Northstar Cold Chain Supplier Cutover Authorization

Report title: Broken-layout and native-layer recovery

Report category: malformed export recovery and reading order

Report summary: Measures whether a model reconstructs logical reading order after font substitution, overlapping boxes, detached labels, shuffled PDF objects, and mixed native and raster evidence.

Modality profile: a 5-page malformed office export; native text, raster evidence, and object coordinates each supply incomplete pieces

Report capabilities: native-layer recovery, malformed layout, reading order, mixed-modality fusion, detached labels, overlapping text, source precedence

Source modality: five logical presentation pages exported through LibreOffice Writer as a five-page mixed native/raster PDF. Page 4 contains the damaged Draw graph, detached native connector labels, and exception register on one landscape page. The clean 220-DPI executed form remains logical and physical page 5.

Family: `office export recovery`

Purpose: recover the intended logical packet after a realistic Slides/PowerPoint-style office round trip substitutes missing condensed fonts, inflates runs, decomposes tables into independently positioned cells, detaches headers, changes object order, and overlaps native text. The native PDF object stream is intentionally shuffled rather than an intact row-wise table export; visible coordinates and row IDs preserve the bindings. On page 4, native connector-ID/label fragments must be joined to visible raster arrow endpoints and direction, while the damaged exception register preserves its bindings through coordinates and row IDs. Physical page 5 remains the clean executed source of truth.

Every scored fact is directly present in a visible or native PDF object. No answer-key-only value, hidden text, arithmetic inference, tiny-font needle, blur, or arbitrary image degradation is used. The gold document reconstructs bindings, reading order, directed edges, superseded/current values, and executed states from those objects.

The source PDF contains the office export's own text and image objects. Container normalization changes metadata and serialization only; it does not add, hide, or replace page content.

Tags: `native-pdf`, `libreoffice-export`, `malformed-layout`, `cross-office-conversion`, `overlapping-text-boxes`, `font-substitution`, `detached-labels`, `scrambled-reading-order`, `broken-object-stacking`, `native-text-recovery`, `mixed-modality`, `tables`, `source-precedence`, `reading-order`
