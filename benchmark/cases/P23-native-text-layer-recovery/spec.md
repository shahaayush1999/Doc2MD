# Northstar Cold Chain Supplier Cutover Authorization

Report title: Broken-layout and native-layer recovery

Report category: malformed export recovery and reading order

Report summary: Measures whether a model reconstructs logical reading order after font substitution, page spill, overlapping boxes, detached labels, shuffled PDF objects, fragmented cross-page connectors, and mixed native and raster evidence.

Modality profile: a 7-physical-page malformed office export produced from 5 logical pages; native text, raster evidence, and object coordinates each supply incomplete pieces

Report capabilities: native-layer recovery, malformed layout, reading order, mixed-modality fusion, detached labels, overlapping text, cross-page joins, source precedence

Source modality: five logical presentation pages exported through LibreOffice Writer as a seven-physical-page mixed native/raster PDF. Logical page 4 catastrophically spills: its title remains on physical page 4, the Draw graph lands on physical page 5, and the detached exception register lands on physical page 6. The clean 220-DPI executed form still prints logical 5/5 but appears on physical page 7.

Family: `office export recovery`

Purpose: recover the intended logical packet after a realistic Slides/PowerPoint-style office round trip substitutes missing condensed fonts, inflates runs, decomposes tables into independently positioned cells, detaches headers, changes object order, overlaps native text, breaks logical pagination, and collides graphic groups with register content across several pages. The native PDF object stream is intentionally shuffled rather than an intact row-wise table export; visible coordinates and row IDs preserve the bindings. On the dependency spread, native connector-ID/label fragments split across physical pages 5-6 must be joined to visible raster arrow endpoints and direction on physical page 5, while the associated exception register has also spilled to physical page 6, so neither modality nor page is a complete answer key. Physical page 7 remains the clean executed source of truth.

Every scored fact is directly present in a visible or native PDF object. No answer-key-only value, hidden text, arithmetic inference, tiny-font needle, blur, or arbitrary image degradation is used. The gold document reconstructs bindings, reading order, directed edges, superseded/current values, and executed states from those objects.

The source PDF contains the office export's own text and image objects. Container normalization changes metadata and serialization only; it does not add, hide, or replace page content.

Tags: `native-pdf`, `libreoffice-export`, `malformed-layout`, `cross-office-conversion`, `overlapping-text-boxes`, `font-substitution`, `detached-labels`, `scrambled-reading-order`, `broken-object-stacking`, `native-text-recovery`, `mixed-modality`, `tables`, `source-precedence`, `reading-order`
