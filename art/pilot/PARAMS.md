# Fax Machine Box — Line-Art Tracing Pilot

Source photo: `art/originals/IMG_4228.jpeg` (5712x4284, JPEG) — long side face of the
hand-drawn cardboard box: yellow ground, colored-pencil parrot, black marker
"FAX MACHINE" drip lettering. Goal: a clean vector line-art layer (marker
lettering + parrot outlines) for laser engraving. Colored-pencil tonal layer
is out of scope for this pass.

All vector data in this folder was produced by `potrace` and/or `vtracer` —
no path data was hand-authored or hand-edited.

## Tool versions

- ImageMagick: 7.1.2-27 (installed via `brew install imagemagick`)
- potrace: 1.16 (installed via `brew install potrace`)
- vtracer: 0.6.5 (installed via `cargo install vtracer`; brew has no formula —
  `brew install vtracer` fails with "No available formula", so it was built
  from source with cargo instead. Binary lives at `~/.cargo/bin/vtracer`.)
- Python: repo venv `.venv/bin/python` (3.14) + `opencv-python-headless`
  (pip-installed into the venv for this pilot) and `numpy`/`Pillow` (already present).

No install failures blocked the pipeline; all three tools ended up available.

## Step 1 — Perspective correction

Corner pixel coordinates were located by eye on the original 5712x4284 photo
(cropping small 400-700px windows around each corner and reading them back to
pin down sub-pixel-ish locations, then verifying with a marked-up overlay
render before committing):

| Corner | Pixel (x, y) |
|---|---|
| Top-left     | (170, 1330) |
| Top-right    | (5350, 1255) |
| Bottom-right | (5180, 3200) |
| Bottom-left  | (460, 3345) |

Target aspect ratio: 12:5 (2.4:1), matching `SHELL_EXT["length"]=304.8mm (12")`
and `SHELL_EXT["height"]=127.0mm (5")` from `src/faxbox/config.py` (the long
side face of the shell). Output canvas: 3600x1500px (exactly 2.4:1).

Command:

```
magick art/originals/IMG_4228.jpeg -alpha Set -virtual-pixel white \
  -distort Perspective \
  "170,1330 0,0  5350,1255 3600,0  5180,3200 3600,1500  460,3345 0,1500" \
  +repage art/pilot/_persp_full.png

magick art/pilot/_persp_full.png -crop 3600x1500+0+0 +repage art/pilot/corrected_original.png
```

The first pass left a thin sliver of the box's top floral-trim edge visible
across the top ~30px (an artifact of the corner points sitting a few px
outside the true face-top on the physical box's slightly rounded edge).
Fixed by cropping 30px off the top and rescaling back to 3600x1500:

```
magick art/pilot/corrected_original.png -crop 3600x1465+0+30 +repage \
  -resize 3600x1500! art/pilot/corrected_original.png
```

Checked all four edges afterward via narrow strip crops (top/bottom/left/right
100px bands) — all clean, no countertop/kitchen background bleed-in. The
taped-over circular repair hole in the upper-left corner is retained in frame
per instructions (it's a real repair on the box, not a photo artifact).

Result: `corrected_original.png` (3600x1500) — straight edges, correct 12:5
aspect ratio.

## Step 2 — Line extraction (`extract_lines.py`)

A simple global or local-mean adaptive threshold does **not** work here: the
black marker letters are thick (~100-150px stroke width at this resolution),
so any local neighborhood inside a big solid letter is itself dark — the
letter interior reads as "background" under local-mean thresholding and only
the stroke *edges* pop out as hollow rings (this was the first failed
attempt, kept as a lesson, not shipped).

Working approach, in `extract_lines.py`:

1. `value = max(B, G, R)` per pixel. Any bright channel (yellow ground's R/G,
   green/red/purple pencil fill) keeps `value` high; only true black marker
   ink is low in all three channels, so `value` isolates ink regardless of
   the hue behind/around it.
2. `value = medianBlur(value, 9)` — suppresses colored-pencil grain/texture
   speckle (isolated dark pixels inside green/purple fill areas dip nearly as
   low as real ink on a per-pixel basis; the pencil texture is *sparse*
   though, so a median blur over a 9px neighborhood erases it while leaving
   contiguous ink strokes intact).
3. Estimate the local background illumination (the yellow ground's lighting
   gradient — brighter camera-left, dimmer camera-right) via a large
   grayscale morphological **close** (`MORPH_ELLIPSE`, 251x251): closing
   fills in dark valleys (ink) up to ~251px wide while tracking the slow
   lighting gradient, giving a background estimate with the letters
   effectively erased.
4. `diff = background − value`; threshold `diff > 55` → ink. (Tried 35/50/70
   against a cropped test region of the parrot's vest+wing — 35 let a lot of
   colored-pencil texture noise through as false "ink" speckle; 55–70 cleaned
   it up while keeping every real black-ink stroke, since true ink pixels are
   near-black regardless of local background, giving `diff` well over 100 in
   letter interiors.)
5. Morphological open (3x3 ellipse) to trim single-pixel speckle, then drop
   connected components smaller than 25px area outright.
6. Small morphological close (3x3) to patch any 1px gaps in strokes.
7. Invert to standard white-background/black-ink convention.

```
.venv/bin/python art/pilot/extract_lines.py \
  art/pilot/corrected_original.png art/pilot/linework_mask.png 251 55 25
# args: src dst close_ksize diff_thresh min_area
```

Result: `linework_mask.png` — solid black "FAX MACHINE" lettering with drips
intact, parrot outline (cap, eyes, beak, vest seam, feather hatching, jacket
buttons) captured as clean black linework, yellow ground dropped to white.

**Known artifacts in the mask** (carried through to all 3 candidates):
- Upper-left: the taped-over circular repair hole renders as a dark
  scribbly blob — expected/acceptable per the task brief (it's a real
  feature of the box, not a defect in the pipeline).
- Upper-right: a small dark smudge from tape glare/wrinkle reflection near
  the top trim edge (not real ink). Minor, cosmetic, localized to a ~150x100px
  area outside the letters/parrot — flagged here for a future pass (could be
  masked out manually with a paint-out rectangle before tracing, but left as
  legitimate "trace whatever the mask says" output for this pilot since the
  task scope is pipeline validation, not final cleanup).

## Step 3 — Tracing (3 candidates)

`potrace` doesn't read PNG directly (only pnm/pbm/pgm/ppm/bmp), so the mask
was thresholded to 1-bit PBM first:

```
magick art/pilot/linework_mask.png -threshold 50% art/pilot/linework_mask.pbm
```

**Candidate A — potrace, low detail / cleanest (aggressive despeckle):**
```
potrace art/pilot/linework_mask.pbm --svg -o art/pilot/candidate_a.svg \
  --turdsize 80 --alphamax 1.3 --opttolerance 0.8 -W 12in -H 5in
```

**Candidate B — potrace, medium/balanced:**
```
potrace art/pilot/linework_mask.pbm --svg -o art/pilot/candidate_b.svg \
  --turdsize 15 --alphamax 1.0 --opttolerance 0.3 -W 12in -H 5in
```

**Candidate C — vtracer, high detail (polygon mode, distinct algorithm):**
```
~/.cargo/bin/vtracer --input art/pilot/linework_mask.png \
  --output art/pilot/candidate_c.svg \
  --colormode bw --mode polygon --filter_speckle 8 --corner_threshold 60 \
  --segment_length 4 --splice_threshold 45
```

Path counts: A=52 paths, B=57 paths, C=52 paths (compact multi-subpath
polygon output). Because the mask was already heavily denoised in step 2,
A and B end up visually very close — the despeckle/alphamax spread mostly
shows up in how many tiny leftover specks survive, and there were few left
to begin with. C (vtracer) uses a genuinely different algorithm (region
polygon tracing vs potrace's outline+bezier fit), giving straighter/more
faceted edges instead of potrace's smoothed bezier curves — a real
stylistic/technical difference worth keeping as the third option even though
overall "detail" looks similar at this mask quality. If more differentiation
is wanted later, feed candidate C from a less-aggressively-denoised mask
(lower `min_area` / skip the morphological open in `extract_lines.py`).

## Step 4 — Renders and comparisons

Each SVG rendered back to a 3600x1500 PNG (matching `corrected_original.png`):

```
magick -density 300 -background white art/pilot/candidate_X.svg \
  -resize 3600x1500! art/pilot/candidate_X.png
```

Side-by-side comparisons (original on top, candidate below, each labeled)
built with ImageMagick `-append` + `-annotate` (font explicitly set to
`/System/Library/Fonts/Helvetica.ttc` — ImageMagick's font list was empty by
default on this machine, so `-annotate` fails silently/loudly without an
explicit `-font`):

- `compare_a.png`, `compare_b.png`, `compare_c.png` — original vs each candidate
- `compare_all.png` — original + all three candidates stacked, for at-a-glance judging

## Quality self-assessment

Visually reviewed `compare_all.png` at 1400px width:
- Lettering: legible and fully solid in all three candidates, drips preserved
  down to the fine drip tails.
- Parrot: recognizable silhouette, cap, eyes, beak, vest seam/buttons, and
  feather hatching all present as clean line art in all three.
- No candidate is speckle-garbage or lost the lettering — all three clear
  the quality bar. Candidate A is recommended as the primary/default for
  laser engraving (cleanest, fewest stray micro-paths); B is a very close
  second; C (vtracer) is a legitimate stylistic alternative with slightly
  more faceted edges.

## Known issues / follow-ups for a non-pilot pass

1. Tape-glare smudge near the top-right trim edge (see above) — could be
   manually painted out of the mask before tracing.
2. The taped-over circular repair hole (upper-left) traces as a dark
   scribbly blob in all candidates; if the final engraving should omit it
   entirely, it should be masked out explicitly (it was left in per this
   pilot's instructions).
3. Candidates A/B are very similar because the mask was already well
   denoised upstream (in `extract_lines.py`) rather than relying on potrace's
   despeckle to do that work. This is a robustness choice (keeps tracer
   params portable across tools) but means the "3 detail levels" mostly show
   up in candidate C's algorithm choice rather than a strong A→B→C gradient.
   A future pass could derive A/B/C from three different mask-denoising
   strengths to get a more pronounced detail gradient.
