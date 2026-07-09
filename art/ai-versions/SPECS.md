# Image-generation specs for all art faces

Purpose: exact sizes, aspect ratios, and composition constraints for generating the
AI-restyled artwork (Gemini "Nano Banana Pro" / gemini-3-pro-image, same model that
produced `IMG_4228_ai_v1.jpg`). Works for both paths: Claude calling the API directly,
or Ben generating manually in the Gemini app and handing files back.

All physical dimensions come from `src/faxbox/config.py` via the generator code
(verified 2026-07-08). These are the *visible panel blanks*, not the assembled box
outer dims — e.g. the side wall part is 298.45 mm, not 304.8 mm.

## Universal rules (apply to every face)

- **Model settings (API or app):** aspect ratio per the table below; image size **4K**
  (always — we downsample to need; never accept 1K for the big faces).
- **Style lock:** every generation must attach TWO reference images:
  1. `art/ai-versions/IMG_4228_ai_v1.jpg` — the approved style anchor (pure black/white,
     solid fills + halftone screens + stipple, bold drip lettering).
  2. The face's trimmed source photo from `art/trimmed/` — the content to reinterpret.
  Plus a prompt derived from Ben's original v1 prompt (recorded verbatim below).

  **Ben's original v1 prompt (Gemini app, produced IMG_4228_ai_v1):**
  > "Hi there. This is an illustration that I have that I want to convert into a vector
  > illustration in black and white that I can use. It could also have some rastering,
  > but it's meant to be applied via a laser printer onto wood. The current illustration
  > obviously doesn't work for that, but I want an updated version that's the same
  > dimensions, and it doesn't have to be a printable file. I have software that can
  > convert it into a printable file, but I want something that I can effectively add
  > to a laser image."
- **Output must be laser-native:** pure black and white only, no grays, no gradients —
  mid-tones as halftone dots or hatching, minimum feature size ≥ 2 px at 1024-wide
  equivalent (≈0.6 mm physical). No border/frame rectangle (panel edges are the frame).
- **Safe margins:** keep meaningful art ≥ 4 mm from finger-jointed edges (the joint
  notches eat into the face) and ≥ 2 mm from plain edges. In generation terms: ask for
  ~5% breathing room at the edges; exact enforcement happens at crop/placement time.
- **Aspect note:** Gemini only offers fixed ratios (1:1, 5:4, 4:3, 3:2, 16:9, 21:9 and
  portrait inverses). Generate at the nearest ratio per the table, composed with slack,
  then crop to exact mm ratio in post. Crop direction is specified per face.

## STATUS 2026-07-09 — generation complete after Ben's review round, learnings

All faces generated in the approved **hatch style** (Ben rejected halftone-dot and
stylized variants; loose hand-drawn hatching, solid-black display lettering, direct
translation only). Ben reviewed the first full set 2026-07-09 and flagged: off-white
backgrounds (fixed: deterministic white-point pass at ≥235→255, applied to all, canonical
whitened files live in `art/ai-versions/final/`), 4239 over-beautified (fixed: vH2
regenerated with anti-beautification prompt — naive proportions/wallpaper preserved),
and the 4231 lid art too busy/burn-risky (fixed: regenerated as ONE continuous panorama
for the whole top surface — sliding lid + fixed top panel, field 301.25×158.75mm, seam
at 26.22% from front where the 79mm lid meets the 222.25mm top panel, 5.8mm vertical
step there, zero horizontal gap; lightened shading: outlined scales, mostly-white mosaic
tiles, ~half the flowers; grip-slot capsule reserved ~8% from front edge, width-centered).

Final picks (mirrored to `~/Desktop/Mini/Fax Machine/final-set/`): 4228_vH1, 4229_vH1,
4230_vH2 (style anchor), **4231_vT1_master (split at placement per seam preview)**,
4233_vH1, 4235_vH3, 4236_vH3, 4237_vH1, 4238_vH2, **4239_vH2**. Awaiting sign-off.

Known remaining debts: 4231 master has a small photo-inherited tilt/trapezoid —
straighten DETERMINISTICALLY at placement (measured rotation/quad warp; a model
"straighten" pass just added a border and kept the lean — don't retry that).

## Split-generate-merge (drawer sides, decided by Ben 2026-07-09)

The four drawer sides (4233/4235/4237/4239) were re-done by Ben's split method: cut each
source at a quiet column (4233@50%, 4235@67%, 4237@58%, 4239@64.5%), generate halves
separately (cut edge flush to canvas), butt-join in post. Results:
`IMG_<n>_ai_vS_stitched.png` in final/, ratios 3.3–3.9:1 (vs 2.3:1 of the old
full-frame gens; panels are 4.22:1 — remaining gap closes at placement by fit-to-height).

Learnings that bind future splits:
- Independently generated halves DIVERGE (style, invented suns, duplicated content).
  MUST generate sequentially: right half conditioned on [finished left half (style
  standard + seam reference) + full original photo], with an explicit "do NOT include"
  list of left-half content and a strict left-to-right layout rule.
- Halves still sometimes draw fragments of the other half's content at the cut edge —
  trim those strips in post before butt-joining (art bbox crop + fixed-fraction trims).
- 4239's "PORN"/"PORN 2" book spines are IN Ben's original drawing (verified against
  the source photo) — faithful, do not "fix".
- Seam quality: 4233/4235/4237 good; 4239 acceptable (couch angle steps slightly at the
  seam) — flagged to Ben, worst case is one more conditioned re-roll of the left half.

Pipeline learnings (bind future generations):
- **Padded-canvas direct translation works** (compose source on white canvas with
  margins baked in; model translates rather than follows layout instructions).
- **Do NOT pass a style-anchor image alongside simple sources** (lettering-only or
  sparse faces): the anchor's content bleeds in or fully replaces the source
  (happened to 4235/4236/4238). Anchor image only helps content-rich scenes; for
  simple faces carry style by text description alone.
- **Single-change fix passes work well**: feed the output back with "reproduce
  exactly, change only X" (used for: solid-black title, remove border frame,
  de-colorize).
- Residual color specks/tints survive sometimes — the 1-bit threshold step removes
  them; don't burn generations chasing pure B&W.
- Known cosmetic debts for post-processing: 4228 + 4237 have drawn border frames
  (crop inside or erase; confirm with Ben whether 4237's frame is original art —
  it is: giant kids peek over the gallery walls); 4230_vH2 has faint stray marks at
  top/bottom edges (erase at threshold time); 4233 has a red streak (blood-drag
  joke) that thresholds to black — intended.

## Per-face table

| Face (qty) | Visible blank, W×H mm | Exact ratio | Generate at | Crop in post | 300-DPI target px |
|---|---|---|---|---|---|
| Side wall (2: L+R) | 298.45 × 127.0 | 2.350:1 | **21:9** (2.333) | shave ~0.7% off height | 3525 × 1500 |
| Front wall (1) | 158.75 × 118.025 | 1.345:1 | **4:3** (1.333) | shave ~0.9% off height | 1875 × 1394 |
| Sliding-lid top (1) | 163.6 × 79.0 | 2.071:1 | **21:9** (2.333) | crop ~11% off width | 1932 × 933 |
| Drawer faceplate (2) | 150.9 × 53.5 | 2.821:1 | **21:9** (2.333) | crop ~17% off height | 1782 × 632 |
| Drawer side (4) | 212.25 × 50.325 | 4.218:1 | **21:9** (2.333) | crop ~45% off height — see note | 2507 × 594 |
| Rear wall | 158.75 × 127.0 | 1.25:1 | (5:4 exact) | — | **NO ART** (per FACES.md; also has two drawer cutouts) |

## Per-face composition constraints (put these IN the generation prompt)

**Side walls — parrot/"FAX MACHINE" (IMG_4228, already done as v1) + the other long face
(IMG_4230, "Fun For Terrible Writers & Artists of All Ages"):**
- Keep the top ~10 mm (top ~8% of image height) free of critical detail near the front
  half: the sliding-lid through-slot (76.2 × 4.0 mm) pierces the wall there, top of slot
  5 mm below the top edge, spanning 0–76 mm from the front edge.
- Unavoidable reality: rows of small joint holes cross the face interior (a vertical row
  ~78 mm from the front edge, horizontal rows at mid-height 63.5 mm and near top/bottom).
  These will punch through whatever art is there. Nothing to do at generation time;
  the placement proof must overlay them so Ben sees where they land.
- v1 aspect is 2.52:1 vs needed 2.35:1 — when fitting v1, letterbox/crop decision goes
  to Ben at the proof gate (see BRIEF.md).

**Front wall — rainbow "FAX MACHINE" + fax-control-panel illustration (IMG_4229):**
- Rendered in the B/W style, "rainbow" becomes tonal variation (halftone density steps).
- Keep a ⌀10 mm zone clear at top-center (turn-button pivot hole: exact center of the
  width, 8 mm below the top edge).
- Note the panel is short (118 mm, not 127): the lid slides over its top edge.

**Sliding-lid top — panorama: florals → tabby cat w/ hose → dragon tail → mosaic head
(IMG_4231):**
- The canvas is FAR smaller than the original lid art: 163.6 × 79 mm total. The
  panorama must be radically simplified/condensed — tell the model to compress the
  sequence, not shrink it.
- Grip slot keep-out: 30 × 10 mm stadium slot, centered across the width, centered
  25 mm from the lid's leading edge. That's a dead zone in the left-of-center of the
  composition (as drawn with leading edge on the left). Prompt: "leave an empty
  horizontal capsule-shaped zone" there, or compose so the slot lands in background.
- Orientation: leading edge (the one with the grip) faces the box front.

**Drawer faceplates — "COLORS" (IMG_4236) and "Lines" (IMG_4238):**
- Grip slot keep-out is the dominant constraint: 30 × 15 mm slot, dead center
  horizontally, its top 8 mm below the top edge — i.e., a hole in the upper-middle of
  the face. Compose the lettering AROUND it (e.g. split "COL ORS" flanking the slot, or
  lettering in the lower band with decoration flanking the slot).
- Very shallow face (53.5 mm tall): single-line bold lettering, minimal background.

**Drawer sides — turkeys/desert (IMG_4233), alligator/seagull (IMG_4235),
gallery/audience (IMG_4237), bookshelf/"BLAH BLAH" (IMG_4239):**
- Extreme 4.2:1 band, only 50 mm tall. Generate at 21:9 with the prompt instruction
  "compose the entire scene inside a wide horizontal band occupying the middle half of
  the frame, empty white above and below" — then crop the band out. Do NOT let the
  model fill 21:9 edge-to-edge or the crop will decapitate the scene.
- Clean faces: no holes or slots; three finger-jointed edges (both ends + bottom), so
  keep art 4 mm off those, 2 mm off the open top edge.

## Gemini API cheat-sheet (for the agent running generation)

- Endpoint: `POST https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent`
  with `x-goog-api-key` header. Verify the current pro image model id via the
  `/v1beta/models` list (expected family: `gemini-3-pro-image*`; nickname Nano Banana Pro).
- Request: `contents` = [style-anchor image (inline_data, base64), source photo
  (inline_data), text prompt]; `generationConfig.imageConfig = { "aspectRatio": "21:9",
  "imageSize": "4K" }` (adjust per table); `responseModalities: ["TEXT","IMAGE"]`.
- Key location on this machine (once installed): `~/.config/gemini/api_key` (chmod 600).
- Generate 2–4 candidates per face; save ALL to `art/ai-versions/` as
  `IMG_<num>_ai_v<n>[a-d].png` and mirror proofs to `~/Desktop/Mini/fax-art-proofs/`
  via loopback SSH for Ben to judge. Ben picks; no auto-selection.

## Post-processing (every accepted image)

1. Threshold to true 1-bit (~50%; the v1 pilot's morphological-close trick in
   `art/pilot/extract_lines.py` is available if plain threshold hollows thick strokes).
2. Crop to the exact mm ratio per the table (direction per the table).
3. Resample to the 300-DPI target px (integer-friendly downscale from 4K; never
   upscale a 1K image to hit the target).
4. Then hand off to the BRIEF.md pipeline: panel-overlay proof → Ben gate → trace or
   raster-embed per the Ponoko format decision → sheet integration.
