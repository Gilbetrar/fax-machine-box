# Fax Machine Box

A laser-cut, fax-machine-themed desktop organizer, generated from
[Boxes.py](https://github.com/florianfesti/boxes) finger-joint parametric
box code. `DESIGN.md` is the canonical geometry reference — read it before
touching any dimension. This README covers building, testing, and cutting.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

(A `.venv/` already exists in this repo checkout — use it directly, e.g.
`.venv/bin/python`, rather than re-creating it, unless it's missing or
broken.)

## Build

Generate every part, then nest them onto cut-ready sheets:

```bash
.venv/bin/python -m faxbox.shell_generator    # outer shell: 8 pieces -> output/outer_shell.svg
.venv/bin/python -m faxbox.generate_drawers   # one drawer's 6 pieces -> output/drawer.svg (cut TWICE); also output/guides.svg (the 4 drawer guides)
.venv/bin/python -m faxbox.generate_lids      # sliding lid: 1 piece (78.0 mm long) -> output/lids.svg
.venv/bin/python -m faxbox.layout             # nests all of the above onto output/sheet_1.svg, sheet_2.svg, ...
.venv/bin/python -m faxbox.calibration        # legacy kerf/thickness and magnet coupons -> output/kerf_coupon.svg, output/magnet_coupon.svg (the test-fit coupon in "Downloads" replaces them)
```

**Retention (issue #20):** `shell_generator.py` and `generate_drawers.py` also
cut the magnet holes (two in the divider, one in each drawer back) in the same
runs. The turn-button lid lock was removed on 2026-10-10 (Ben's decision): there
is no button part, no front-wall pivot hole and no hardware generator. The lid is
held by friction in its slots only.

`layout.py` also writes `output/final_layout.svg` — a combined, true-scale
view of every sheet side by side, for eyeballing the whole nesting in a
browser in one shot. **`final_layout.svg` is bigger than any real laser bed
and must never be sent for cutting** — send `sheet_1.svg`, `sheet_2.svg`,
... individually. Each `sheet_N.svg` is itself real, complete, laser-ready
input: the right SVG to open and inspect before cutting is one of those, not
`final_layout.svg`.

## Downloads (cut files for every thickness and kerf)

    .venv/bin/python scripts/export_cutfiles.py        # site/downloads/
    .venv/bin/python scripts/export_site_data.py       # site/data/parts.json

`export_cutfiles.py` builds, for every thickness T from 2.8 to 3.5 mm in 0.1 mm
steps and for each laser kerf (diode 0.12, CO2 0.18, Ponoko 0.20 mm), the files
below into `site/downloads/`. Only `manifest.json`, `README.md` and `.gitignore`
are committed there; the zips and the coupon files are built. `manifest.json`
and `site/downloads/README.md` (written by the script) describe the schema.
Geometry reads `FAXBOX_THICKNESS` (mm) at import time, so one process makes one
thickness. Finger holes are T + 0.1 mm wide at every thickness. Finger-slot breakouts
through an edge (the 0.05 mm hole-row breakouts) are merged into the outline in
every file, so each such slot is one notch contour with no hairline strip left
between the slot's cut and the outline's cut. Corner loops are removed, and
every cut contour is a valid simple closed shape.

| file | contents |
|---|---|
| `fax-machine-box_T<T>_k<kerf>_cut.zip` | Cut only. Blue lines only, so a service that cuts every line cuts exactly the parts. One set per layout, plus the coupon files. `coupon_marked.svg` / `.dxf` has red tick marks (engrave); the plain coupon is blue only |
| `fax-machine-box_T<T>_k<kerf>_labels.zip` | Cut + labels, for your own laser. Parts lie inside face up. Red labels (part letter and name, plus joint numbers) and the red faceplate glue-up lines, all on layer LABELS |
| `fax-machine-box_T<T>_k<kerf>_engrave_<layout>.zip` | Cut + engrave, one zip per layout. Parts with art lie OUTSIDE face up with the art as gray filled shapes (DXF: closed polylines on layer ENGRAVE; set that layer to fill / raster). Parts whose outline in the plain files shows the inside face (top panel, sliding lid, both faceplates, both left drawer sides) are mirrored here so the outside is up; the art is not mirrored. Parts without art lie inside face up and carry the red joint labels. Parts with art carry no marks, so a joint between a marked part and an art part is numbered only on the marked part; match those by the part letter and the edge, or use the cut + labels files. Never flip a part to engrave a second side |
| `fax-machine-box_T<T>_parts.zip` | One zero-kerf file per distinct part, for services that apply their own kerf, plus `faces/` with the 11 art parts in 15 variants |
| `coupon/T<T>_coupon[_marked].svg` and `.dxf` | The test-fit coupon, loose (it is also inside every cut zip). See "Test-fit coupon" |

**Colours.** Cut is a blue stroke `#0000FF`. The art (area engrave) is a gray
fill `#808080`. Every single-line mark is a red stroke `#FF0000` (DXF layers: CUT blue,
ENGRAVE gray, LABELS red): the part
letters, the joint numbers, the faceplate glue-up lines and the coupon ticks.
This is Ponoko's recommendation (blue stroke = cut, red stroke = line engrave,
gray fill = area engrave; https://help.ponoko.com/en/articles/2688732-how-should-i-specify-laser-actions ,
checked 2026-10-10). Ponoko assigns a laser function to each line and fill
colour at upload, so check the colour-to-function assignment on the upload page
before you order. Only cuts are kerf-offset.
Engraving stays at least 0.35 mm from every cut (art is trimmed back where a
thickness moves a slot under it).

**Formats.** DXF is R2000, units millimetres (INSUNITS 4), layers CUT, ENGRAVE
and LABELS. SVG: 1 unit = 1 mm and the canvas is the size of the content, not of
the bed.

**Layouts and the stock each needs.**

| layout | size (mm) | stock | kerf sets | engrave sets |
|---|---|---|---|---|
| `ponoko` | 790 x 384 | Ponoko supplies the sheet | 0.20 | 0.20 |
| `xtool_s1` | 498 x 301.6 | each S1 sheet is one 12 x 24 in sheet cut to 498 mm long (108 mm offcut); the layout needs 4 sheets | all three | diode, CO2 |
| `xtool_p2` | 594.9 x 301.6 (3 mm margin, 3 mm spacing) | whole 12 x 24 in sheets (really 301.6 x 606.4 mm, 11-7/8 x 23-7/8 in); the layout needs 3 sheets | all three | CO2 |
| `glowforge_pro` | 495 x 279 | a sheet at least 495 x 279 mm (a 12 x 24 in sheet is too tall; cut it to 495 x 279 first) | all three | CO2 |
| `generic_600x400` | 600 x 400 | a sheet at least 600 x 400 mm | all three | all three |
| `nycr_32x20` | 812.8 x 508 | a sheet at least 32 x 20 in; the layout needs 2 sheets | all three | CO2 |

Sheets per box: `glowforge_pro` 5, `generic_600x400` 3, `ponoko` 2, `xtool_s1` 4,
`xtool_p2` 3, `nycr_32x20` 2. The canonical figure for 12 x 24 in stock is 3
sheets per box (`xtool_p2`), recorded in `site/downloads/manifest.json` as
`stock_12x24_sheets_per_box`.

**Match marks.** Joints are numbered so assembly is "match 1 to 1". Each finger
joint has a name made of the lower part letter and a number (for example C3),
and the same name is engraved near the joint on both parts (on the inside face
of parts without art). A joint between a marked part and an art part is marked only on the marked part; match those by the part letter and the edge, or use the cut + labels files. There are 25 joints. The bottom panel's rear edge and the
faceplates are glued and carry no number. Parts with exterior art carry no marks
on the outside. The structured joint map (part, edge, position) is in
`manifest.json`.

**Mirror note.** Every flat part can be turned over, so a box built with both
side walls swapped and the divider turned left for right is a valid mirror-image
box with all the engraved faces inside. The instructions say engraved face out;
the labels on the inside faces make it obvious when something is inside out.

## Test-fit coupon

`coupon.svg` / `coupon.dxf` and `coupon_marked.svg` / `coupon_marked.dxf`. The
marked coupon is the one with engraved ticks 1 to 10 between the thickness slots
and the magnet holes. Cut it on a scrap of your real plywood before any real
part. Every measurement on it is taken with calipers. Read it in this order:
kerf square, then thickness, then the kerf set from the finger pairs. In every
formula below, k is the kerf you measured from the kerf square (k = 10.00 -
measured width), never the kerf of a file set. The coupon
is in every zip type (loose per kerf under `coupon/`, and on a sheet of each bed
layout where there was room).

- **K, kerf square.** A 10 mm square piece drawn with no kerf compensation.
  Kerf k = 10.00 - measured width. Measure two directions and average them.
  Kerf varies along the bed, so measure where the box will be cut. The kerf
  sets are 0.12, 0.18 and 0.20 mm; the set nearest to k is only the first
  guess, and the finger pairs (R) decide.
- **Q, thickness slots and magnet holes.** The panel has a clipped top-left
  corner as an orientation mark. Ten slots run from the narrowest (2.5 mm
  drawn) to the widest (3.4 mm) from left to right, in 0.1 mm steps. The cut
  slot is the drawn width plus k, so plywood from 2.8 to 3.5 mm shows up at any
  kerf from 0.10 to 0.22 mm. Find the narrowest slot the plywood slides into
  without force; if it falls between two slots, take the tighter one. With W
  the drawn width of that slot, the estimate is W + k - 0.05. Round the
  estimate to 0.1 mm, half up (3.35 goes to 3.4); that is the thickness set.
  Examples: k = 0.15 and W = 2.9 give 3.00, set 3.0; k = 0.10 and W = 3.3 give
  3.35, set 3.4. If the plywood enters the first slot with room to spare, use
  the 2.8 set. The engraved ticks 1 to 10 sit between the slots and the magnet
  holes. Four magnet holes are drawn 5.3, 5.4, 5.5 and 5.6 mm; the cut hole is
  the drawn size plus the kerf. The box wants a 5.65 mm hole for a 6.0 mm
  magnet.
- **R, finger joints.** Three pairs of three-finger corners (a finger piece and
  a hole piece) that differ in size, left to right: the smallest is compensated
  for the diode kerf (0.12, 1 tick), the middle for CO2 (0.18, 2 ticks) and the
  largest for Ponoko (0.20, 3 ticks). They have the same finger width, play
  (0.1 mm) and kerf compensation as the box joints. Take the pair that goes
  together with firm hand pressure and no rattle. If two pairs do, take the
  tighter one as long as it still goes together by hand without a tool. If none
  goes together by hand, take the smallest set and file the fingers. A pair made
  for kerf s on a laser with measured kerf k has 0.1 + 2 x (k - s) mm of
  clearance along the fingers: k = 0.15 picks the CO2 0.18 set with 0.04 mm of
  clearance, and k = 0.10 picks the diode 0.12 set with 0.06 mm. Joint
  looseness has two independent directions. Along the fingers it depends on
  kerf, as above. Through the thickness, tight means the plywood will not slide
  through the slot and the fingers end below the surface: the plywood is
  thicker than the set, so use the next thicker set. Loose means it rattles and
  the fingers stand proud of the surface: the plywood is thinner, so use the
  next thinner set.
- **S, lid slot.** A lid slot block and a strip, cut for the kerf of the set the
  coupon came from.

Tuning for kerf means choosing a kerf file set. The files do not need editing,
and `BURN` in `config.py` does not need to change.

## Test

```bash
.venv/bin/python -m pytest tests/ -v
```

The test suite regenerates `output/*.svg` from current source before
checking it (see `tests/conftest.py`), so it always measures what the code
*currently* produces, not stale files. All tests must be green with zero
`xfail`s before cutting anything — this is the project's standing policy
(see `LEARNINGS.md`).

**Render-based visual QA** (the check class that catches what geometry
tests can't — issue #25): `scripts/qa_render.py` renders every sheet, every
part, and every part corner to PNGs under `scratch/qa-renders/` (whole-sheet
overviews, per-part crops, 15×15mm corner windows, plus `_thick` variants
with strokes fattened to 0.15mm for legibility). Re-run it after ANY
generator change and actually look at the parts you touched — the one real
defect an outside reviewer caught (issue #25) was visible in seconds in a
render and invisible to 200 green tests. A laser operator's eyes see the
rendered file, not the path data.

## Project Structure

```
fax-machine-box/
├── src/faxbox/
│   ├── config.py            # single source of truth for all dimensions (implements DESIGN.md)
│   ├── shell_generator.py   # outer shell: bottom, 4 walls, divider, shelf, top panel (8 pieces)
│   ├── generate_drawers.py  # one drawer's 6 pieces (body x5 + faceplate); cut this sheet twice
│   ├── generate_lids.py     # sliding lid (1 piece)
│   ├── layout.py            # nests all parts onto bed-sized sheets for cutting
│   ├── calibration.py       # legacy kerf/ply-thickness coupon + magnet press-fit coupon (+ Ponoko combined coupon)
│   ├── cutset.py            # per-thickness, per-kerf cut/label/engrave sets and the test-fit coupon (used by scripts/export_cutfiles.py)
│   └── ponoko.py            # Ponoko export mode -> output/ponoko/ (see "Ordering from Ponoko")
├── tests/                   # pytest harness: geometry, laser-compliance, and layout checks
├── docs/service-comparison.md  # laser service comparison + verified NYC Resistor constraints
├── DESIGN.md                # canonical geometry — the source of truth for every number
└── output/                  # generated SVGs (gitignored)
```

## Color coding

- **Blue stroke (`#0000FF`)** = cut line
- **Gray fill (`#808080`)** = area engrave (the wall and panel art, in the
  cut + engrave files). In the DXF files this is layer ENGRAVE; set it to fill /
  raster.
- **Red stroke (`#FF0000`)** = line engrave: every single-line mark (part
  letters, joint numbers, the faceplate glue-up lines and the coupon ticks). In
  the DXF files this is layer LABELS. Skip it if you do not want the marks
  engraved. Strokes are drawn hairline-weight (0.0762mm) so they don't get
  mistaken for fills.

This follows Ponoko's recommended colours (see "Downloads"). Ponoko users should
check the colour-to-function assignment at upload.

NYC Resistor documents no colour convention that could be confirmed on their
site (see DESIGN.md's "Decisions" section and `docs/service-comparison.md`).

## Parts checklist

25 laser-cut pieces (8 shell, 12 drawer, 1 lid, 4 drawer guides), all cut from
uniform plywood 2.8-3.5 mm thick (3.175 mm / 1/8" by default; pick the cut-file
set that matches the sheet you measure), plus the test-fit coupon
(not a box part, see "Test-fit coupon"). Matches DESIGN.md's parts list.

**Outer shell — `output/sheet_*.svg`, 8 pieces, cut once (from
`outer_shell.svg`):**

- [ ] 1× Bottom panel (inset between the four walls)
- [ ] 1× Left Wall
- [ ] 1× Right Wall
- [ ] 1× Front Wall
- [ ] 1× Rear Wall (two drawer openings)
- [ ] 1× Vertical Divider (separates paper compartment from drawer bay;
  2× magnet holes, one per drawer, on the box centre line)
- [ ] 1× Horizontal Shelf (splits the drawer bay into upper/lower slots)
- [ ] 1× Top Panel (fixed, over the drawer bay — **not** a removable lid)

**Drawers — 6 pieces × 2 identical sets = 12 pieces (from `drawer.svg`, cut
the same sheet TWICE):**

- [ ] 2× Front (body)
- [ ] 2× Back (body) — the drawer's LEADING wall; carries the magnet
  hole, centred, so the part is mirror-symmetric and cannot go in turned round
  (see "Magnets")
- [ ] 2× Left Side (body)
- [ ] 2× Right Side (body)
- [ ] 2× Bottom (body)
- [ ] 2× Faceplate (glued to the body front, not finger-jointed; glued 0.75 mm
  above the body's bottom edge so it is centred in the rear-wall opening)

Drawer body external dimensions at 3.175 mm stock: 149.0mm (Y) × **218.6mm
(X, pull direction)** × 53.5mm (Z) (width and length follow the stock
thickness, see DESIGN.md v2). The divider is the drawer's in-stop (see "Know
before you build").

**Lid — 1 piece (from `lids.svg`):**

- [ ] 1× Sliding Lid, 78.0 mm long (rides in through-slots cut into both side
  walls)

There is **no separate flat/tabbed lid** — that part doesn't exist in this
design. The drawer bay is covered by the fixed Top Panel above, not a
removable cover.

**Drawer guides — part J, 4 pieces (from `guides.svg`):**

- [ ] 4× Drawer Guide, a flat rib T wide x T high x 40 mm long, plain edges
  except the leading end, which is cut at 30 degrees in plan down to a 0.8 mm
  tip. Glued flat on the bottom panel (lower pair) or on the shelf (upper pair)
  against the side edge, two per drawer slot (see "Assembly steps"). It has no
  part label, because it is only T wide.

**Test-fit coupon — standalone, not part of the box:**

- [ ] 1× coupon (from `coupon.svg`, or `coupon_marked.svg`) with parts K, Q,
  R and S. Cut it on scrap before any real part. See "Test-fit coupon" above.

## Hardware list, finishing, paper

**Hardware (not laser cut):** magnets only.

| Qty | Item | Spec |
|---|---|---|
| 4 (buy 6) | Magnets | 6 x 2 mm disc, N52 neodymium |

The turn-button lid lock (M3 bolt, washers, nyloc nut) was removed on 2026-10-10.
The lid is held by friction in its slots, and nothing else is bought.

**Finishing.** Assemble first and finish after.

1. Dry-fit and glue the box and the drawers as described under "Assembly steps".
   Keep the finger joints and every glue face free of finish before gluing, so
   no finish goes on until the glue has cured.
2. When the glue has cured, wipe a thin coat of finish onto the assembled box
   (clear water-based polyurethane or shellac), and scuff lightly. Keep it off
   the lid slots and the faces the drawers ride on.
3. Wax last. Rub paraffin wax or a candle stub on the lid slots and lid edges
   and on the drawer runners (the drawers' bottoms and sides). Waxing is what
   makes them slide.

**Paper:** quarter letter, 4.25 x 5.5 in (107.95 x 139.7 mm), stands on edge in
the paper compartment with the 5.5 in side across the box. At 3.175 mm stock
the compartment is 111.95 mm tall under the lid, so the paper has 4.0 mm of
headroom (3.35 mm at 3.5 mm stock). It is 158.75 mm wide inside, so there is
19.05 mm of spare width (18.4 mm at 3.5 mm stock). Depth is 76.2 mm (the divider
sits 76.2 mm behind the front wall's inner face at every thickness), which holds
about 760 sheets of 20 lb paper at the 10 sheets per mm DESIGN.md assumes.
Letter paper cut in four gives quarter-letter pages.

## Wall identification (read this before assembly)

The left and right side walls are **mirror images**, not identical parts. In the
plain cut files the part names are only in the manifest, so identify a wall by its
features (the labels files and the engrave files also name each part):

1. Hold the wall with the **lid slot notch near the top edge** and its **open
   mouth** (the notch reaches the edge of the wall) pointing left. The mouth
   end is the wall's front.
2. Look at the vertical divider hole column, about 3 in (79.4 mm) in from the
   mouth, just behind the closed end of the slot. Count the holes. The wall with
   **one more hole** in that column is the **left wall** (the divider is keyed
   this way). The counts depend on the plywood thickness:

   | thickness | left wall | right wall |
   |---|---|---|
   | 2.8 to 2.9 mm | 9 | 8 |
   | 3.0 to 3.2 mm | 8 | 7 |
   | 3.3 to 3.5 mm | 7 | 6 |

Getting this wrong puts the slot mouths at opposite ends of the box and
nothing dry-fits: check before step 6.

## Assembly steps

This is the order checked in 3D by `src/faxbox/assembly3d.py`
(`ASSEMBLY_STEPS`, re-derived from collisions in `tests/test_assembly3d.py`).
Some older orders cannot be done: with the bottom panel in, the divider
cannot get in, and the divider, shelf and top panel cannot all be pushed into
one flat side wall and closed with the other. Follow this order.

Use slow-set PVA, a little on finger joints only. Dry-fit every step before
gluing it. Have clamps staged. Wipe squeeze-out inside the drawer bay at once.

**Identify the parts first.** The side walls are mirror images, see "Wall
identification". The divider only fits one way (see step 5).

**Drawers (make two, identical).**

1. Stand the drawer back (the one with the magnet hole) and the drawer front
   (the one with the grip slot) upright, finger edges facing each other.
2. Slide the left side in from the left, then the right side from the right.
   The four vertical corners close together.
3. Press the drawer bottom on from below. Its edges are plain; the walls' tabs
   go through its hole rows.
4. Glue the faceplate to the front. Center the body on the plate and glue the
   plate 0.75 mm ABOVE the body's bottom edge, so that it sits centred in the
   rear-wall opening with a 0.75 mm reveal on all four sides (the body's bottom
   edge then sticks out 0.75 mm below the plate, and the body is 0.95 mm in from
   each side edge of the plate). Line up the two grip slots so a finger reaches
   through both (the plate's slot sits 8.75 mm below its top edge, the body
   front's slot 8.0 mm below its own). In the cut + labels files the plate
   carries red glue-up lines for the body's left edge, right edge and top edge;
   there is no bottom line. Clamp. Do not glue the drawers anywhere else.

**Box.**

5. **Frame.** First glue the two upper guides to the shelf. Each lies flat on
   the shelf against its side edge (the edge that meets the wall's inner face),
   with its rear end flush with the shelf's own front edge (X = 82.55, ignoring
   the tabs) and its tapered end toward the rear of the box. Then lay the top
   panel and the shelf in their relative positions and
   push the divider toward the rear (+X) into them: the divider's top tabs go
   into the top panel's front-edge holes (a single row of 10 to 13 holes,
   depending on thickness, along its plain front edge; the top panel's side and
   rear edges carry fingers), the shelf's front tabs into the divider's hole
   row. The divider fits only one way: its two side edges are
   different lengths (the long finger run goes with the left wall, the side
   with the shorter run goes with the right wall). If it will not seat, it is
   turned the wrong way, so turn it; do not force it.
6. **Right wall.** Move it onto the frame
   from the right (toward -Y). Lid slot mouth to the front.
7. **Rear wall.** Fit it from the rear (toward -X).
8. **Left wall.** Fit it from the left
   (toward +Y).
9. **Front wall.** Fit it from the front (toward +X).
10. **Bottom panel.** Glue the two lower guides to the bottom panel first.
    Each lies flat on the panel against its side edge (the edge that meets the
    wall's inner face), with its rear end flush with the rear edge of the row
    of divider slots and its tapered end toward the rear of the box. Then turn
    the box over and press the bottom in from below, carrying its two guides.
    Its rear edge is plain and sits against the rear wall.
11. Square the box (equal diagonals) and clamp. Check with the drawers: a
    square bay lets both drawers slide into their openings without binding.
12. **Lid.** Slide it in from the front, over the front wall, into both slots,
    until it stops at the divider. Never glue the lid or its slots. Nothing
    locks it in place; it stays by friction in the slots.
13. **Drawers.** Slide them in from the rear. The magnets are already in the
    parts (see "Magnets"). Before the glue sets, slide each drawer in and check
    that it pulls shut against the divider (the magnets attract). If a drawer is
    pushed away, a magnet is the wrong way round; turn it over while the glue is
    still wet. Support the drawer with your other hand when you pull it out past
    halfway. There is no stop, and a drawer pulled out further than about 110 mm
    tips and drops.

**Match marks.** In the cut + labels and cut + engrave files every finger joint
is numbered: the lower part letter plus a number (for example C3), engraved near
the joint on both parts, except that parts with art carry no marks (see "Downloads"; a joint between a marked part and an art part is marked only on the marked part, so match those by the part letter and the edge). Assembly is "match 1 to 1". The bottom panel's rear
edge and the faceplates are glued and have no number.

**Glue guidance.**

- PVA, applied sparingly, on finger joints only.
- Never glue the drawers' outer faces, the inside of the drawer bay, the lid,
  or the lid slots.
- The top panel is held by glue as well as geometry: its holes in the walls
  open at the top edge, so do not skip glue on that row.

## Know before you build (honest limitations)

This design accepts some real tradeoffs to hit the SPEC envelope and the
front-insert lid concept. None of these are bugs — they're documented so
nobody "fixes" them mid-build or is surprised later:

- **The lid is 78 mm long and the box has drawer guides.** The lid (78.0 mm)
  stops 1.0 mm short of the end of its slot, so it never touches the 1.0 mm
  rounded corners at the rail's root. Four drawer guides (part J), flat ribs glued to the bottom panel and the shelf, narrow the
  drawer channel so the drawers cannot wander far enough to lose their magnets.
- **The sliding lid is held by friction in its slots only.** The turn-button
  lock was removed on 2026-10-10 (Ben's decision), so there is no button,
  pivot hole, bolt or nut. The divider stops the lid from sliding in too far
  (rearward), but nothing stops it sliding back *out* the front. Tip the box
  front-down and the lid can slide out. This is an accepted cost of the
  front-insert design (the slots have to be open at the front edge for the lid
  to go in at all). **Carry the box level**, especially with the lid closed.
- **The drawers are held shut by magnets.** One magnet pair per drawer (drawer
  back to divider) holds each drawer closed; press them into the loose parts before assembly (see
  "Magnets"). Without the magnets, nothing prevents a drawer from sliding fully
  out its rear-wall opening when the box is tipped rear-down.
- **Drawer magnet lateral float.** The drawer is guided by its rear-wall
  opening and by the four drawer guides. The guides (flat ribs, with a 30 degree lead-in at the rear end that funnels in a drawer corner arriving slightly yawed) narrow the channel to
  INTERIOR_WIDTH - 2T (152.4 mm at T = 3.175, the same as the rear-wall
  opening), so a drawer (149.0 mm wide) floats at most 1.7 mm each way at its
  far end. Without the guides it floated 4.9 mm each way ((158.75 - 149.0) / 2),
  and the magnet pull is zero or negative beyond 4.5 mm. With N52 6 x 2 mm discs
  (the grade the pull figures are for; weaker grades hold less) the pull at 1.7 to 2.0 mm lateral offset is above 3 N. Widening the drawer is
  not an option: it has to pass the rear-wall opening, whose posts must stay at
  least 3.0 mm wide.
- **Drawers close flush by bottoming out on the divider, not the rear
  wall.** The inset faceplate never bears against the rear-wall opening
  frame — the drawer back (its leading wall) is what stops against the
  divider's rear face (box X = 82.55) at the far end of its travel. If a
  drawer doesn't sit flush, check for glue or debris on the divider face, not the rear-wall opening.
- **The 7.5 mm rail above each lid slot is still the most fragile feature.**
  It is a thin cantilevered strip of ply above the slot, unsupported along
  most of its length. **Never force the lid.** If it binds, stop and look for a
  swollen or misaligned joint. Never pick the box up by the lid. Hand it over
  from the bottom.
- **The rear-wall posts either side of a drawer opening are at least 3.0 mm
  wide** (MIN_WEB) at every thickness: OPENING_WIDTH = INTERIOR_WIDTH - 2 *
  max(T, 3.0), which is 152.4 mm at T = 3.175 and 153.5 mm at 2.8. The drawer
  and faceplate widths follow from the opening, so they are 0.4 mm narrower at
  T = 2.8.
- **The lid slot's two rear inside corners are rounded** with a 1.0 mm radius to
  remove the stress concentration at the rail's root.
- **The rear wall's strip under the lower drawer opening is a plain web of at
  least 3.0 mm** (v2 removed the bottom-panel hole row that used to chop it into
  chips). The lower drawer and its opening sit at Z = max(T, 3.0), so the strip
  is T tall from 3.0 mm plywood up, and 3.0 mm at 2.8 and 2.9 mm plywood (where
  the lower drawer then sits 0.2 and 0.1 mm above the bay floor). It is still
  thin; handle the rear wall by its edges before glue-up.
- **The "fixed" Top Panel is fixed by glue, not geometry.** Its finger
  holes in the walls break through the walls' top edge by design (see
  DESIGN.md), so before the PVA cures the panel can lift straight out —
  fingers-in-notches, not fingers-in-holes. Normal finger-joint look once
  assembled; just don't skip glue on the top-panel rows.
- **The lid slot's vertical clearance is 1.2 mm, not the SPEC's 1.5 mm.**
  This is a documented deviation (DESIGN.md), not an error. 1.2 mm absorbs
  warped sheets and thickness variation without letting the lid rattle. The
  SPEC's 1.5 mm play is still kept in-plane (lid width vs. slot span, drawer
  vs. opening).

## Magnets (issue #20)

The magnets are the only hardware to buy. Press them into the loose parts
BEFORE assembly. The holes are already in the parts.

**Shopping list:**
- 6 disc magnets, 6 mm diameter x 2 mm thick, N52 neodymium (the grade the pull figures are for; weaker grades hold less). Four are needed
  (one attracting pair per drawer, 2 drawers); buy 6 so there are 2 spares for a
  dropped or chipped magnet or a scrap test-fit. **Press each magnet FLUSH with
  the mating face** (the drawer Back's rear face and the divider's surface that
  faces it). A 2 mm disc recessed on its mating side leaves an air gap between
  the pair, and the gap weakens the pull a lot (see DESIGN.md "Retention" §A).
  Recess only on the far side, where the glue backfills.

**Install order (before assembly):**
1. Stack all four magnets in one column and mark a dot on the top face of the
   stack. They then all have the same pole up.
2. Identify each part's inside and outside face by the labels. The joint labels
   and part letters are engraved on the inside face of parts without art; in the
   cut + labels files every part is engraved inside.
3. Press each divider magnet into its hole with its dot facing OUT, toward the
   drawers (the rear of the box). Press each drawer-back magnet in with its dot
   facing INTO the drawer, away from the divider. In the finished box every dot
   faces the rear of the box. Because all four are marked from the same stack,
   each drawer magnet then attracts the divider magnet it meets, and either
   drawer works in either bay. Use a drop of glue on each.
4. Assemble the box and drawers as described under "Assembly steps".
5. Test: each drawer should pull closed and need a deliberate one-finger pull to
   open. Do this before the glue sets, while you can still turn a magnet over:
   slide each drawer in and check that it pulls shut against the divider (the
   magnets attract). If a drawer is pushed away, a magnet is the wrong way
   round; turn it over while the glue is still wet. Support the drawer with your
   other hand when you pull it out past halfway. There is no stop, and a drawer
   pulled out further than about 110 mm tips and drops.
6. **Magnet hole fit:** the box wants a 5.65 mm hole for the 6.0 mm magnet. The
   coupon's four magnet holes (drawn 5.3 to 5.6 mm, cut size drawn + kerf) show
   which size your laser and magnets want; see "Test-fit coupon".

## Cut-day checklist (NYC Resistor)

See `docs/service-comparison.md` → "NYC Resistor cutting constraints
(verified 2026-07-07)" for the full writeup and sources. That doc is also
where the pre-2026-07-07 service comparison lives — it's marked superseded;
this checklist is current.

1. **Bed size: resolved (2026-07-07 research), verify with a glance at the
   machine.** The "12"×24"" claim was a stale 2013 page comment describing
   NYC Resistor's previous laser (their 2008 Epilog Mini 24, 35W). The
   current machine is an **Epilog Fusion 32 60W — 32"×20" (812×508mm) work
   area**, confirmed by their wiki (edited 2026), 2025–26 class listings,
   and Epilog's spec sheet for that exact model (sources in
   docs/service-comparison.md). The `nycr_32x20` layout (812.8 x 508 mm)
   puts the whole box on 2 sheets, each at most 32 x 20 in, so it fits with
   room to spare. A five-second look at the machine confirms it (the
   Fusion 32 bed is visibly ~2.5ft wide). If it somehow isn't that machine,
   re-nest: change `SHEET_WIDTH_MM` / `SHEET_HEIGHT_MM` in
   `src/faxbox/layout.py`, rerun `.venv/bin/python -m faxbox.layout`, and
   re-check the printed sheet dimensions.
2. **Material.** Bring **Baltic Birch specifically**, not generic/cheap
   plywood — cheap ply's interior voids can blow out this design's thinnest
   features (the 3.175mm webs in the rear-wall drawer openings and the
   7.5mm cantilevered lid rail) when the laser hits a void instead of solid
   wood. Bring **2 sheets of 32"×20"**, plus extra
   scrap for the test-fit coupon (step 3). Orient
   sheets with the **face grain running along the sheet's long axis** for
   stiffness on the long spans.
3. **Cut the test-fit coupon on scrap FIRST, before any real part** (`coupon.svg`
   or `coupon_marked.svg` from the downloads; see "Test-fit coupon"). Measure the
   kerf square, pick the kerf file set (diode 0.12, CO2 0.18, Ponoko 0.20 mm),
   then read the thickness slots and pick the thickness, then try the finger
   joints. Choosing a kerf file set replaces any editing of `BURN` or
   `FINGER_PLAY` in `config.py`. The `nycr_32x20` layout (812.8 x 508 mm) is the
   ready-made file set for this laser.
4. **CorelDraw import.** NYC Resistor's workflow is CorelDraw-based; their
   tips page warns Inkscape's raw SVG export can get corrupted there and
   recommends exporting PDF instead. On import: set all strokes to
   **hairline** if the importer doesn't respect the file's native
   0.0762mm hairline stroke width. Color mapping: **blue = vector cut**,
   **red = line engrave** (part letters, joint numbers, glue-up lines),
   **gray fill = area engrave**. In the cut + engrave files the art
   is gray filled shapes: engrave it as a raster / fill, and engrave any red
   line at vector (stroke) settings. If the SVG import gets
   mangled, run `.venv/bin/python scripts/export_pdf.py` to export
   PDF versions of the sheets and coupon (same folder, same names) as a
   fallback — the PDF page size matches each SVG's declared mm dimensions
   exactly, so physical scale carries over.
5. **Cut order: engrave first, then interior holes, then part outlines
   (inside-out), and set this explicitly** — don't assume the driver
   preserves file order. Engrave the art (and the faceplate glue-up lines or the
   joint labels, if you use them) while the sheet is still whole and flat, then cut
   interior finger-joint holes and slots, then cut part outlines free last.
   Cutting outlines before interior holes risks a loose piece shifting
   under the head before its holes are cut.
6. **Handle cut side walls flat.** The 7.5mm rail above each lid slot is
   thin and cantilevered — it can snap if a side wall is picked up by an
   edge or flexed. Lift and carry side walls flat, supported across their
   full face, until assembly.
7. **Take the laser class first** if you haven't (required for the $1/min
   self-serve rate; runs ~monthly). Operator-assisted time is $75/hr +
   $2/min if you skip it.
8. **Cut all sheets, then dry-fit before gluing anything** — see "Assembly
   steps" above. Press the magnets into the loose parts before assembly (see
   "Magnets").

## Ordering from Ponoko

> **⏸️ FABRICATION IS PAUSED (Ben, 2026-07-08) — gated on artwork.**
> The plan is to order online (the held Ponoko quote) rather than a friend's
> laser, but **not until the exterior engrave artwork is finalized** and
> baked into the order files (see `art/FACES.md`). Do not pay the held
> quote or regenerate/upload order files for fabrication until the art
> workstream signs off — otherwise box #1 ships without its art.

The NYC Resistor path above **remains the default** — nothing about it
changes unless you explicitly opt in. Ponoko export is an alternate,
mail-order way to get the same box cut without a laser class or a Brooklyn
craft night.

**Regenerate for Ponoko** (either command; they're equivalent):

```bash
.venv/bin/python -m faxbox.ponoko
# or: FAXBOX_PROVIDER=ponoko .venv/bin/python -m faxbox.layout
```

This writes `output/ponoko/sheet_1.svg`, `sheet_2.svg`, `sheet_3.svg` (plus
a reference-only `final_layout.svg` — never upload that one). Differences
from the NYCR sheets, all verified against Ponoko's own current docs on
2026-07-07 (source URLs in `src/faxbox/config.py`'s `PONOKO_*` constants):

- **Kerf compensation:** 0.10 mm per side (half Ponoko's published 0.20 mm birch
  kerf); the downloads' `ponoko` layout is built only for the 0.20 kerf set.
- **Sheets re-nested** to fit Ponoko's published 790×384mm max design area
  for birch plywood (the NYCR sheet 2 at ~549×434mm is too tall for it).
  The legacy `faxbox.ponoko` export (25 parts plus its coupon) comes to 3 sheets;
  the downloads' `ponoko` layout of the cut files needs 2. Price scales with material.
- **All 25 parts on the sheets**, plus (in the legacy `faxbox.ponoko`
  export) a small self-calibration coupon nested into spare space, since Ponoko
  has no "cut a coupon on scrap first" step: your first order IS the test cut.
  With the downloads, add `coupon.svg` (it is inside the cut zip) to the order
  as its own small part.
- **No label text** — Ponoko requires text converted to outlines
  (it isn't read otherwise), and outlined part names would engrave onto
  visible faces. Identify parts by size against the "Parts checklist" above
  (each `<g>` also carries a `data-part` attribute if you open the SVG).
- Colors are blue stroke = cut, red stroke = line engrave, gray fill = area
  engrave: Ponoko's recommended convention, which this project follows. Check
  the colour-to-function assignment at upload.

**Placing the order:** upload the three `output/ponoko/sheet_*.svg` files at
ponoko.com, pick **Birch Plywood, 3.2mm** (their 1/8" stock — within this
design's 2.8–3.5 mm range; measure it and use the matching thickness set), one
sheet each. Their quote is instant
at upload. Typical turnaround is roughly ~8 business days production +
shipping to NYC (check the quote page for current dates).

**Calibrate from the first order** (closes the loop for order #2+):

1. Find the coupon (see "Test-fit coupon"). Measure the kerf square (part K,
   drawn 10 mm with no kerf compensation) with calipers: kerf = 10.00 −
   measured width. If it is not close to 0.20 mm, use the file set whose kerf
   is nearest for the next order.
2. Press a real 6 mm disc magnet into the four magnet holes (drawn 5.3, 5.4,
   5.5 and 5.6 mm; cut size = drawn + kerf, left to right). The box wants a
   5.65 mm hole.
3. If the first order's finger joints are loose or tight, the kerf-square
   reading from step 1 and the three-finger corner pairs (part R) say which
   kerf set to use for the next order. (If joints on the FIRST order don't assemble at all, that's a
   thickness problem, not kerf — check the delivered ply with calipers
   against the 2.8–3.5 mm range of the thickness sets.)

## Rebuilding sheets for a different laser bed

**Hard floor first: the minimum viable bed is 324.96 × 185.26mm** (with the
standard 10mm margins). The largest *drawn* part is `Shell: Bottom` at
**304.96 × 165.26mm** — that's the 304.8mm exterior length plus finger
protrusion and kerf compensation, so don't size a bed or buy stock off the
often-quoted 298.45mm *interior* figure. Three parts (Bottom, both side
walls) are ~305mm long: **a 300×200mm K40-class bed cannot cut this box**,
no rotation or re-nesting helps, and the packer will tell you so loudly
(a `ValueError` naming the first part that doesn't fit — it never silently
drops or truncates parts).

For any bed at or above the floor, no source edit is needed:

```bash
# one-off, env vars (mm):
FAXBOX_SHEET_WIDTH=458 FAXBOX_SHEET_HEIGHT=304 .venv/bin/python -m faxbox.layout

# or from Python, kwargs win over env over provider defaults:
.venv/bin/python -c "from faxbox.layout import generate_layout; \
generate_layout(sheet_width=458, sheet_height=304)"
```

A new recurring service deserves a proper `PROVIDERS` entry in
`src/faxbox/config.py` (burn, colors, `sheet_width`/`sheet_height`,
label policy) — see the `nycr`/`ponoko` entries for the pattern; then
`FAXBOX_PROVIDER=<name> .venv/bin/python -m faxbox.layout`. Precedence:
explicit kwarg > `FAXBOX_SHEET_*` env > provider entry > NYCR default
(609.6 × 457.2). Small beds just mean more sheets (458×304 → 7 sheets;
the 324.96×185.26 minimum → 14).

Verify before cutting — exact commands, and **order matters**:

```bash
# 1. tests FIRST (the suite regenerates output/ with DEFAULT settings,
#    overwriting any custom-bed sheets):
.venv/bin/python -m pytest tests/ -q
# 2. THEN rebuild for your bed (again):
FAXBOX_SHEET_WIDTH=458 FAXBOX_SHEET_HEIGHT=304 .venv/bin/python -m faxbox.layout
# 3. render YOUR sheets (qa_render defaults to the ponoko set, not yours):
.venv/bin/python scripts/qa_render.py --sheets output/sheet_*.svg
```

Look at every rendered sheet before sending anything to a laser. The sheet
files on disk are always exactly one run's output (stale sheets from a
previous nesting are purged automatically).
