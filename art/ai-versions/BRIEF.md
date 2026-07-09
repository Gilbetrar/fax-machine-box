# Brief: Convert AI-restyled artwork into laser-ready engrave layers

**How to use this file:** Point an agent at this brief ("Read art/ai-versions/BRIEF.md in
~/AI/Projects/fax-machine-box and execute it"). It is self-contained but assumes the agent
will also read HANDOFF.md, art/FACES.md, and art/pilot/PARAMS.md before starting.

## Context

Ben ran the trimmed original photo of the pilot face (art/trimmed/IMG_4228.jpeg — parrot
spraying "FAX MACHINE" graffiti) through an AI image model and got a much cleaner,
laser-native reinterpretation: `art/ai-versions/IMG_4228_ai_v1.jpg` (1024×407, JPEG,
effectively 1-bit black/white with halftone screens for mid-tones).

This changes the pipeline. The old plan was two layers per face (potrace line trace + a
future color→burn-tone raster layer). The AI version bakes tone in as halftone/hatch
patterns, so each face needs only ONE engrave layer derived from a single 1-bit image.
The pilot potrace candidates (art/pilot/candidate_*.svg) are superseded for this face.

## Target

- Panel: long side wall of the outer shell, **304.8 × 127.0 mm** (12" × 5", aspect 2.4:1).
  Geometry source of truth: `src/faxbox/config.py` (SHELL_EXT) and the generated
  `output/.../outer_shell.svg`.
- Material: 3.2 mm Baltic birch, cut/engraved by **Ponoko** (CO2, Speedy-class).
- Repo color convention: blue #0000FF = cut, red #FF0000 = vector engrave line,
  hairline 0.0762 mm strokes. Raster/area engraving convention for Ponoko is NOT yet
  established in this repo — verifying it is part of this task (step 3).

## Hard constraints (from HANDOFF.md — do not violate)

1. **No LLM-freehand vector art.** Path data may only come from tracing tools
   (potrace/vtracer) or programmatic geometry. You prep parameters and judge results.
2. **No fabrication ordering.** Quote configuration is fine; ordering is Ben's.
3. Do not touch open PR #22 (experimental). Work on a fresh branch off main.
4. Art must never be engraved from the raw photos; the AI image is the new source.

## The job, in order

### 1. Audit the source image at physical scale
- Confirm effective bit depth (threshold the JPEG at ~50% to true 1-bit; check nothing
  meaningful lives in the grays/JPEG artifacts).
- At 304.8 mm target width the image is ~85 DPI: 1 px ≈ 0.30 mm. Measure the finest
  features (feather stipple, crosshatch line weight, halftone dot pitch) and report
  anything under ~0.3 mm — a Speedy-class CO2 spot is ~0.2 mm and birch chars, so
  sub-0.3 mm marks will fill in or vanish.
- Aspect check: 1024×407 = 2.52:1 vs panel 2.4:1. Decide crop vs letterbox (see step 2 —
  the drawn border frame is probably the slack to absorb this).

### 2. Fit to the real panel
- Extract the actual panel outline + keep-out zones from the generated SVG: finger joints
  on all edges, and critically the **sliding-lid through-slot** near the top of the side
  walls — art must not cross it (the original photo had a floral strip at the top edge in
  roughly this zone; the AI version's lettering rides high — verify clearance).
- Decide what to do with the image's drawn rectangular border: recommend dropping it
  (panel edges + joints already frame the face) and using the reclaimed margin to fix the
  aspect mismatch. Also drop the stray sparkle glyph at bottom-right.
- Produce an **overlay proof PNG** (art on top of the real panel outline with joints and
  slot visible, at correct scale) and copy it to `~/Desktop/Mini/fax-art-proofs/` via
  loopback SSH for Ben's sign-off. **GATE: do not proceed past here until Ben approves
  placement.**

### 3. Establish the Ponoko engrave format (research, then decide)
- Verify from Ponoko's current making guidelines how they accept area/raster engraving
  (black-filled vectors? embedded raster images? required DPI?) and how they price it —
  large solid fills are machine-time and may dominate cost on a 12×5" face.
- Recommend one of:
  a. **Raster engrave layer**: upscale the 1-bit image to ≥300 DPI at physical size
     (~3600×1500 px, same canvas as the pilot) and embed per Ponoko spec. Upscaling a
     1-bit image needs edge-preserving handling (trace-then-rasterize, or 2×/4× integer
     scale + re-threshold) — naive bicubic will gray the halftones.
  b. **Vector engrave**: potrace the solids/lettering into filled paths; keep halftone
     regions raster (hybrid) or trace the dots too (watch file size/path count — Ponoko
     may choke on tens of thousands of dot paths).
- Whichever wins, get a **quote delta** (sheets with vs without the engrave layer) so Ben
  sees the cost before committing to this density of artwork on 9 faces.

### 4. Integrate
- Add the engrave layer to the panel in the generator (`src/faxbox/`) or the Ponoko sheet
  assembly (`src/faxbox/ponoko.py`), consistent with how the existing "FAX MACHINE"
  letter engraving is layered. Regenerate sheets; confirm the engrave layer lands on the
  correct face, correct orientation (mirror-check: Left vs Right wall are mirror images,
  and engraving must end up on the EXTERIOR surface as oriented on the sheet).
- Render a final full-sheet proof PNG to `~/Desktop/Mini/fax-art-proofs/`.

### 5. Report back (do NOT batch other faces)
- This is a one-face pilot of the new pipeline. Write findings (feature-size audit,
  Ponoko raster spec, quote delta, chosen pipeline params) into art/pilot/PARAMS.md or a
  sibling doc, update HANDOFF.md, commit + push the branch.
- The other ~8 faces wait until (a) Ben approves this face end-to-end and (b) Ben
  generates matching-style AI versions of the remaining faces with the same model/prompt
  so the box is stylistically coherent.

## Open questions for Ben (ask before the gate if unclear)

- Keep or drop the drawn border frame? (Recommendation: drop.)
- Confirm which physical wall this face goes on (FACES.md says "Long side 1 / Left Wall";
  current code engraves only the Right Wall — reconcile).
