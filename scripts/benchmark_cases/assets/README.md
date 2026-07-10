# Benchmark image assets

These seven project-owned raster assets were generated for Doc2MD on 10 July 2026 with OpenAI's built-in image-generation tool. They replace low-fidelity procedural illustrations while keeping benchmark generation deterministic: the committed PNG bytes are resized and annotated by the Python case builders, never regenerated during a benchmark build.

- `p20-field-cutout.png`: overcast utility field photo; centered pole and visibly split/charred cutout.
- `p20-field-clear-span.png`: two-pole distribution span with vegetation clear of the conductors.
- `p20-field-open-switch.png`: visibly open pole-top switch with a blank yellow hold tag.
- `p21-sem-flake.png`: grayscale SEM-style field with one large and one adjacent small metal flake.
- `p21-sem-scratch.png`: grayscale SEM-style field with a long diagonal scratch and faint parallel abrasion.
- `p21-sem-edge.png`: grayscale SEM-style wafer edge with irregular bead deposits.
- `p21-sem-clean.png`: grayscale SEM-style clean reference field with sparse background specks.

Generation constraints for every asset prohibited logos, watermarks, captions, timestamps, and pre-rendered labels. Case builders add the exact review annotations and scale bars from deterministic code. The assets are synthetic benchmark fixtures, not measurements or evidence from a real utility, wafer lot, or facility.
