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
.venv/bin/python -m faxbox.generate_drawers   # one drawer's 6 pieces -> output/drawer.svg (cut TWICE)
.venv/bin/python -m faxbox.generate_lids      # sliding lid: 1 piece -> output/lids.svg
.venv/bin/python -m faxbox.layout             # nests all of the above onto output/sheet_1.svg, sheet_2.svg, ...
.venv/bin/python -m faxbox.calibration        # kerf/thickness coupon + magnet-fit coupon -> output/kerf_coupon.svg, output/magnet_coupon.svg (cut BOTH on scrap FIRST, see "Cut-day checklist")
.venv/bin/python -m faxbox.generate_hardware  # iteration-2 lid turn-button: 1 piece -> output/hardware.svg
```

**Iteration 2 (retention, issue #20):** `shell_generator.py`/`generate_drawers.py`
also cut the retention holes described below (magnet holes in the divider +
each drawer's leading wall, ONE turn-button pivot hole on the front wall —
see "Know before you build" for why it's on the front wall and not the side
walls) — they're part of the same generator runs above, not a separate step.
`generate_hardware.py` and the magnet coupon are the only genuinely new
outputs.

`layout.py` also writes `output/final_layout.svg` — a combined, true-scale
view of every sheet side by side, for eyeballing the whole nesting in a
browser in one shot. **`final_layout.svg` is bigger than any real laser bed
and must never be sent for cutting** — send `sheet_1.svg`, `sheet_2.svg`,
... individually. Each `sheet_N.svg` is itself real, complete, laser-ready
input: the right SVG to open and inspect before cutting is one of those, not
`final_layout.svg`.

## Cut files for every stock thickness

    .venv/bin/python scripts/export_cutfiles.py        # site/downloads/
    .venv/bin/python scripts/export_site_data.py       # site/data/parts.json

`export_cutfiles.py` writes full sets for 2.8 to 3.5 mm in 0.1 mm steps
(SVG and DXF), a zip per thickness, a test-fit coupon, and layouts for the
Ponoko sheet (790 x 384 mm), xTool S1 (498 x 319), xTool P2/P2S (600 x 305),
Glowforge Pro (495 x 279) and a generic 600 x 400 bed. `manifest.json` lists
the files and the sheet count per bed. Kerf compensation is 0.10 mm per side
(Ponoko); finger holes are T + 0.1 mm at every thickness. Geometry reads
`FAXBOX_THICKNESS` (mm) at import time, so one process makes one thickness.
The generated files are not committed when they pass 30 MB (the folder's
`.gitignore` then keeps only the manifest). DXF is written without extra
dependencies (R12 ASCII, layers CUT and ENGRAVE, mm).

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
│   ├── calibration.py       # kerf/ply-thickness coupon + magnet press-fit coupon (+ Ponoko combined coupon)
│   ├── generate_hardware.py # iteration-2 lid turn-button (1 piece) -> output/hardware.svg
│   └── ponoko.py            # Ponoko export mode -> output/ponoko/ (see "Ordering from Ponoko")
├── tests/                   # pytest harness: geometry, laser-compliance, and layout checks
├── docs/service-comparison.md  # laser service comparison + verified NYC Resistor constraints
├── DESIGN.md                # canonical geometry — the source of truth for every number
└── output/                  # generated SVGs (gitignored)
```

## Color coding

- **Blue (`#0000FF`)** = cut line
- **Red (`#FF0000`)** = engrave line (the faceplate glue-up registration
  outlines; wall art arrives from the art pipeline).
- **Gray** = reference-only text (part labels, sheet numbers). These are
  *not* laser instructions — ignore/skip this color when setting up the job.
  Sheet cut/engrave strokes themselves are drawn hairline-weight (0.0762mm)
  so they don't get mistaken for fills.

This is a convention this project chose (see DESIGN.md's "Decisions"
section), not a documented NYC Resistor requirement — no color convention
could be confirmed on their site. See `docs/service-comparison.md` for
details.

## Parts checklist

22 pieces total (8 shell, 12 drawer, 1 lid, 1 turn button), all cut from
uniform plywood 2.8-3.5 mm thick (3.175 mm / 1/8" by default; pick the cut-file
set that matches the sheet you measure), plus standalone calibration coupons
(none are box parts, see "Cut-day checklist"). Matches DESIGN.md's parts list.

**Outer shell — `output/sheet_*.svg`, 8 pieces, cut once (from
`outer_shell.svg`):**

- [ ] 1× Bottom panel (inset between the four walls)
- [ ] 1× Left Wall
- [ ] 1× Right Wall
- [ ] 1× Front Wall — iteration 2: carries the sole lid-retention
  turn-button pivot hole (see "Know before you build")
- [ ] 1× Rear Wall (two drawer openings)
- [ ] 1× Vertical Divider (separates paper compartment from drawer bay;
  iteration 2: 2× magnet holes, one per drawer)
- [ ] 1× Horizontal Shelf (splits the drawer bay into upper/lower slots)
- [ ] 1× Top Panel (fixed, over the drawer bay — **not** a removable lid)

**Drawers — 6 pieces × 2 identical sets = 12 pieces (from `drawer.svg`, cut
the same sheet TWICE):**

- [ ] 2× Front (body)
- [ ] 2× Back (body) — iteration 2: this is the drawer's LEADING wall,
  carries the magnet hole (see "Iteration-2 retention hardware")
- [ ] 2× Left Side (body)
- [ ] 2× Right Side (body)
- [ ] 2× Bottom (body)
- [ ] 2× Faceplate (glued to the body front, not finger-jointed)

Drawer body external dimensions at 3.175 mm stock: 149.0mm (Y) × **218.6mm
(X, pull direction)** × 53.5mm (Z) (width and length follow the stock
thickness, see DESIGN.md v2). The divider is the drawer's in-stop (see "Know
before you build").

**Lid — 1 piece (from `lids.svg`):**

- [ ] 1× Sliding Lid (rides in through-slots cut into both side walls)

There is **no separate flat/tabbed lid** — that part doesn't exist in this
design. The drawer bay is covered by the fixed Top Panel above, not a
removable cover.

**Iteration-2 hardware — 1 piece (from `hardware.svg`), standalone, not
part of the shell/drawer/lid sheets:**

- [ ] 1× Turn Button (mounts on the front wall). Pivot hole Ø3.2mm. See
  "Iteration-2 retention hardware" for the M3 hardware and install order.

**Calibration — standalone, not part of the box:**

- [ ] 1× Kerf/thickness coupon (from `kerf_coupon.svg`) — five
  ply-thickness gauge slots (2.95 / 3.05 / 3.175 / 3.30 / 3.40mm, spanning
  past both ends of the 3.0–3.4mm stock band) and a 10mm reference square.
  Cut this on scrap *before* cutting any real part; see "Cut-day checklist"
  step 3.
- [ ] 1× Magnet press-fit coupon (from `magnet_coupon.svg`) — 4
  burn-compensated gauge holes, physically identical to same-labeled real
  part holes (5.5 / 5.65 / 5.8 / 5.95mm). Cut on scrap right after the kerf
  coupon; see "Cut-day checklist" step 3a.

## Hardware list, finishing, paper

**Hardware (not laser cut), exact specs:**

| Qty | Item | Spec |
|---|---|---|
| 1 | Bolt | M3 x 14 button head (ISO 7380), A2 stainless |
| 2 | Washers | M3 flat, ISO 7089: 3.2 ID x 7 OD x 0.5 thick |
| 1 | Nut | M3 nyloc, DIN 985: 5.5 mm across flats, 4.0 mm tall |
| 4 (buy 6) | Magnets | 6 x 2 mm disc, N35 neodymium (N52 or 3 mm thick for a stronger pull) |

Stack on the front wall: bolt head outside, washer, turn button, front wall,
washer, nyloc nut inside the paper compartment. The stack is 5.0 mm plus two
sheet thicknesses (11.35 mm at 3.175 mm stock, 12.0 mm at 3.5 mm). An M3 x 12
bolt is flush with the nut face at 3.5 mm stock, so the nylon insert has no
thread to grip. M3 x 14 leaves 2.0 to 3.4 mm of thread past the nut. Bolt and
nut stand 6.5 to 7.9 mm out from the front wall's inner face at about Z = 107,
centered side to side.

**Finishing:**

1. Sand lightly with 220 grit to remove the laser char from the faces you can
   touch (the edges stay dark unless you wipe them with a damp cloth).
2. Seal with a thin coat of clear water-based polyurethane or shellac, then
   scuff lightly. Keep finish off the finger joints before glue-up.
3. Rub paraffin wax or candle stub on the drawers' bottoms and sides and on
   the lid edges and slot floors. Waxing is what makes them slide.
4. Do not wax or seal the faces that get glued.

**Paper:** quarter letter, 4.25 x 5.5 in (107.95 x 139.7 mm), stands on edge in
the paper compartment with the 5.5 in side across the box. At 3.175 mm stock
the compartment is 111.95 mm tall under the lid, so the paper has 4.0 mm of
headroom (3.35 mm at 3.5 mm stock). It is 158.75 mm wide inside, so there is
19.05 mm of spare width (18.4 mm at 3.5 mm stock). Depth is 76.2 mm less the
bolt (up to 7.9 mm), so 68 mm of paper stack fits, several hundred sheets.
Letter paper cut in four gives quarter-letter pages.

## Wall identification (read this before assembly)

The left and right side walls are **mirror images**, not identical parts, and
the sheet labels are not cut or engraved, so identify a wall by its features:

1. Hold the wall with the **lid slot notch near the top edge** and its **open
   mouth** (the notch reaches the edge of the wall) pointing left. The mouth
   end is the wall's front.
2. Look at the vertical divider hole column, about 3 in (79.4 mm) in from the
   mouth, just behind the closed end of the slot. Count the holes. The
   **left wall has 8 holes, the right wall has 7** (the divider is keyed this
   way).

Getting this wrong puts the slot mouths at opposite ends of the box and
nothing dry-fits: check before step 5.

## Assembly steps

This is the order checked in 3D by `src/faxbox/assembly3d.py`
(`ASSEMBLY_STEPS`, re-derived from collisions in `tests/test_assembly3d.py`).
Some older orders cannot be done: with the bottom panel in, the divider
cannot get in, and the divider, shelf and top panel cannot all be pushed into
one flat side wall and closed with the other. Follow this order.

Use slow-set PVA, a little on finger joints only. Dry-fit every step before
gluing it. Have clamps staged. Wipe squeeze-out inside the drawer bay at once.

**Identify the parts first.** The side walls are mirror images, see "Wall
identification". The divider only fits one way (see step 4).

**Drawers (make two, identical).**

1. Stand the drawer back (the one with the magnet hole) and the drawer front
   (the one with the grip slot) upright, finger edges facing each other.
2. Slide the left side in from the left, then the right side from the right.
   The four vertical corners close together.
3. Press the drawer bottom on from below. Its edges are plain; the walls' tabs
   go through its hole rows.
4. Glue the faceplate to the front. Put the red-engraved rectangle on the glue
   side, center the body on it, and line up the two grip slots so a finger
   reaches through both. Clamp. Do not glue the drawers anywhere else.

**Box.**

5. **Frame.** Lay the top panel and the shelf in their relative positions and
   push the divider toward the rear (+X) into them: the divider's top tabs go
   into the top panel's front hole row, the shelf's front tabs into the
   divider's hole row. The divider fits only one way: its two side edges are
   different lengths (the long finger run goes with the left wall, the side
   with the shorter run goes with the right wall). If it will not seat, it is
   turned the wrong way, so turn it; do not force it.
6. **Right wall.** Move it onto the frame from the right (toward -Y). Lid slot
   mouth to the front.
7. **Rear wall.** Fit it from the rear (toward -X).
8. **Left wall.** Fit it from the left (toward +Y).
9. **Front wall.** Fit it from the front (toward +X).
10. **Bottom panel.** Turn the box over and press the bottom in from below. Its
    rear edge is plain and sits against the rear wall.
11. Square the box (equal diagonals) and clamp. Check with the drawers: a
    square bay lets both drawers slide into their openings without binding.
12. **Turn button.** Bolt it to the front wall (see "Hardware list").
13. **Lid.** Slide it in from the front, over the front wall, into both slots,
    until it stops at the divider. Never glue the lid or its slots.
14. **Drawers.** Slide them in from the rear. Install the magnets as described
    in "Iteration-2 retention hardware".

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

- **The sliding lid has no retention along its travel axis in v1** (no
  turn-button installed yet). The divider stops it from sliding in too far
  (rearward), but nothing stops it sliding back *out* the front. Tip the box
  front-down and the lid will slide out. This is an accepted cost of the
  front-insert design (the slots have to be open at the front edge for the
  lid to go in at all) — **carry the box level**, especially with the lid
  closed, until the iteration-2 turn-button (below) is installed.
- **The drawers have no out-stop either in v1** (no magnets installed yet).
  Nothing prevents a drawer from sliding fully out its rear-wall opening.
  Tip the box rear-down and a drawer will slide free. Don't rely on friction
  to keep drawers seated in transit until the iteration-2 magnets (below)
  are installed.
- **Iteration 2 (issue #20) adds retention for both**: a magnet pair per
  drawer (drawer leading wall ↔ divider) and a single turn-button mounted on
  the FRONT WALL's exterior face (an earlier side-wall version was found in
  review to be geometrically incapable of retention and was replaced before
  any part was cut — see DESIGN.md's "Retention (iteration 2...)" section B
  for the proof). See "Iteration-2 retention hardware" below for the
  shopping list and install order — **install AFTER the full dry-fit and
  glue-up**, never before (the magnet holes and the pivot hole are already
  cut into the shell/drawer parts above; only the hardware itself goes in
  later).
- **Drawer magnet lateral float, honestly stated.** The drawer is guided by
  its rear-wall opening, not the bay walls, so it has up to ±4.9mm of
  lateral play in the bay — the two magnet holes (drawer Back wall ↔
  divider) are not guaranteed dead-center-coaxial the instant the magnets
  come close; true centering only happens in the drawer's final ~2.4mm of
  travel, as the faceplate itself enters its snug rear-wall opening. See
  "Iteration-2 retention hardware" below for the self-registering install
  step this implies (mark the actual contact point before gluing, don't
  just trust the two holes' nominal positions).
- **Drawers close flush by bottoming out on the divider, not the rear
  wall.** The inset faceplate never bears against the rear-wall opening
  frame — the drawer body's front face is what stops against the divider
  at the far end of its travel. If a drawer doesn't sit flush, check for
  glue or debris on the divider face, not the rear-wall opening.
- **The 7.5 mm rail above each lid slot is still the most fragile feature.**
  It is a thin cantilevered strip of ply above the slot, unsupported along
  most of its length. **Never force the lid.** If it binds, stop and look for a
  swollen or misaligned joint. Never pick the box up by the lid. Hand it over
  from the bottom.
- **The rear wall's strip under the lower drawer opening is a plain 3.175 mm
  web** (v2 removed the bottom-panel hole row that used to chop it into
  chips). It is still thin; handle the rear wall by its edges before glue-up.
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

## Iteration-2 retention hardware (issue #20)

Not cut from plywood — buy these separately, and don't fit any of it until
after the box is fully glued up and dry-fit (see "Assembly steps" above);
the holes are already in the parts, this is a final, non-structural step.

**Shopping list:**
- 6× disc magnets, 6mm diameter × 2mm thick, N35 grade (4 needed — one
  attracting pair per drawer, 2 drawers — **plus 2 spares** for a dropped/
  chipped magnet or a scrap test-fit; recommended starting point — gentler
  pull, ~0.5–0.7kg at contact, one-finger openable). **The quoted pull
  assumes the magnets are pressed FLUSH with the two mating faces** (the
  drawer Back's rear face and the divider's facing surface) — a 2mm disc
  centered or recessed on its mating side leaves an air gap between the
  pair, and a ~2.4mm total pole gap collapses the pull to roughly
  0.1–0.17kg (see DESIGN.md "Retention" §A). Recess only on the far side;
  glue backfills there. Force is tunable with no geometry change: buy N52
  for a stronger pull, or 3mm-thick discs — the low-risk choice, since they
  sit near-flush on both sides and can't be recessed wrong.
- 1× M3×14 button-head bolt (turn-button pivot), see "Hardware list".
- 1× M3 nyloc nut.
- 2× M3 washer.

**Install order:**
1. Full dry-fit and glue-up first (see "Assembly steps"). The magnet holes
   (divider + each drawer's leading wall) and the turn-button pivot hole
   (front wall) are already cut into those parts — nothing extra to drill.
2. **Magnets — self-registering install (don't just trust the nominal
   hole positions):** with the box fully assembled and each drawer's
   faceplate seated in its opening (fully closed, dry — no glue yet), glue
   the DIVIDER-side magnet into its divider hole first. Then, with the
   drawer held fully closed against the divider, reach through the
   drawer's own Back-wall hole and mark the magnet's true contact point
   (a pencil/scribe mark, or press a bit of clay/putty through to record
   it) — this accounts for the drawer's own lateral float in the bay
   (up to ±4.9mm, only narrowed down once the faceplate enters its
   opening in the final ~2.4mm of travel), rather than assuming the two
   holes are dead-center-coaxial on paper. THEN press-fit and CA-glue the
   drawer-side magnet at the marked/confirmed position, polarity oriented
   to attract (test with the two magnets before gluing either). **Press
   each magnet in until it is flush with its MATING face** — both magnets'
   working faces must be able to touch through the closed joint (see the
   shopping-list note above; a recessed mating face collapses the pull).
   Repeat per drawer.
3. **Turn-button**: bolt the `Turn Button` piece (`output/hardware.svg`)
   through the front wall's pivot hole with the M3 bolt (button head on the
   OUTSIDE, so it's the piece you turn), a washer on each side, nyloc nut
   snugged just tight enough that the button holds a rotated position by
   friction alone (not spring-loaded) — don't overtighten to the point it
   can't rotate by hand. The nut lands INSIDE the paper compartment — it's
   reachable with the lid off, before the lid is slid in for the last time.
4. Test both mechanisms: drawers should pull closed and require a
   deliberate one-finger pull to open; the turn-button, rotated up, should
   block the lid from sliding out the front, and rotated down, should swing
   fully clear so the lid slides freely.
5. **Magnet press-fit calibration**: `MAGNET_PRESS_FIT` in `config.py` (and
   thus the drawer/divider hole diameters) is a starting guess like
   `BURN`/`FINGER_PLAY` — cut `output/magnet_coupon.svg` on scrap (see
   "Cut-day checklist" step 3 below) and press a real magnet into its 4
   gauge holes before trusting the fit on real parts.

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
   docs/service-comparison.md). This project's three sheets measure
   ~**21.8"×14.0"**, **21.6"×17.1"**, and **21.6"×9.8"** — all fit with
   room to spare. A five-second look at the machine confirms it (the
   Fusion 32 bed is visibly ~2.5ft wide). If it somehow isn't that machine,
   re-nest: change `SHEET_WIDTH_MM` / `SHEET_HEIGHT_MM` in
   `src/faxbox/layout.py`, rerun `.venv/bin/python -m faxbox.layout`, and
   re-check the printed sheet dimensions.
2. **Material.** Bring **Baltic Birch specifically**, not generic/cheap
   plywood — cheap ply's interior voids can blow out this design's thinnest
   features (the 3.175mm webs in the rear-wall drawer openings and the
   7.5mm cantilevered lid rail) when the laser hits a void instead of solid
   wood. Bring at least **three sheets, each at least 22"×15"**, plus extra
   scrap for the kerf coupon and the magnet-fit coupon (steps 3/3a). Orient
   sheets with the **face grain running along the sheet's long axis** for
   stiffness on the long spans.
3. **Cut `output/kerf_coupon.svg` on scrap FIRST, before any real part.**
   It has five ply-thickness gauge slots (2.95 / 3.05 / 3.175 / 3.30 /
   3.40mm) and a 10mm reference square. Find which gauge slot *your actual sheet* fits
   into snugly, and measure the cut size of the 10mm square with calipers.
   If either is off from nominal, adjust `BURN` (kerf compensation) and/or
   `FINGER_PLAY` (thickness compensation) in `src/faxbox/config.py` and
   regenerate **everything** (`shell_generator`, `generate_drawers`,
   `generate_lids`, `layout`, and `calibration` — then RE-CUT the coupon to
   confirm before trusting the gauge slots) before cutting real parts. Do not skip this
   because `BURN`/`FINGER_PLAY` already have values in the repo — those are
   starting values, not calibrated ones.
3a. **Cut `output/magnet_coupon.svg` on scrap right after the kerf coupon
   (iteration 2, issue #20)** — same closed-loop rule applies: it has 4
   burn-COMPENSATED gauge holes (5.5 / 5.65 / 5.8 / 5.95mm — drawn smaller
   so the physical hole equals its label, exactly like the real part
   holes; unlike the kerf square, which stays burn-neutral). Press a
   real 6mm disc magnet into each; whichever seats snugly sets
   `MAGNET_PRESS_FIT = MAGNET_DIA - <snuggest diameter>` in `config.py`.
   **If you change `BURN` per step 3, re-cut this coupon too** before
   trusting its readings — like the kerf coupon's own gauge slots, this
   coupon's holes only read true once `BURN` matches the real kerf.
4. **CorelDraw import.** NYC Resistor's workflow is CorelDraw-based; their
   tips page warns Inkscape's raw SVG export can get corrupted there and
   recommends exporting PDF instead. On import: set all strokes to
   **hairline** if the importer doesn't respect the file's native
   0.0762mm hairline stroke width. Color mapping: **blue = vector cut**,
   **red = engrave**, **gray text = ignore** (reference-only part/sheet
   labels — not a cut or engrave instruction). The "FAX MACHINE" letters
   are hatched engrave strokes, not filled shapes — engrave them at vector
   (stroke) settings, same as the other red lines. If the SVG import gets
   mangled, run `.venv/bin/python scripts/export_pdf.py` to export
   PDF versions of the sheets and coupon (same folder, same names) as a
   fallback — the PDF page size matches each SVG's declared mm dimensions
   exactly, so physical scale carries over.
5. **Cut order: engrave first, then interior holes, then part outlines
   (inside-out), and set this explicitly** — don't assume the driver
   preserves file order. Engrave the red "FAX MACHINE" text and faceplate
   registration outlines while the sheet is still whole and flat, then cut
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
8. **Cut all sheets, both coupons, and `output/hardware.svg` (1 turn-button
   piece), then dry-fit before gluing anything** — see "Assembly steps"
   above. Don't fit the magnets/turn-button bolts until after glue-up (see
   "Iteration-2 retention hardware" above).

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

- **Kerf compensation:** `BURN = 0.10` (half Ponoko's published 0.20mm birch
  kerf), vs. the NYCR default 0.08.
- **Sheets re-nested** to fit Ponoko's published 790×384mm max design area
  for birch plywood (the NYCR sheet 2 at ~549×434mm is too tall for it).
  Still 3 sheets — price scales with material.
- **All 22 real parts on the sheets** — the 21 NYCR parts plus the
  turn-button (standalone `hardware.svg` on the NYCR path) — **plus a
  self-calibration coupon** (kerf square + 4-hole magnet press-fit gauge
  row) nested into spare space, since Ponoko has no "cut a coupon on scrap
  first" step: your first order IS the test cut.
- **No gray reference text** — Ponoko requires text converted to outlines
  (it isn't read otherwise), and outlined part names would engrave onto
  visible faces. Identify parts by size against the "Parts checklist" above
  (each `<g>` also carries a `data-part` attribute if you open the SVG).
- Colors are blue=cut / red=vector-engrave — Ponoko's recommended convention,
  which happens to match this project's own.

**Placing the order:** upload the three `output/ponoko/sheet_*.svg` files at
ponoko.com, pick **Birch Plywood, 3.2mm** (their 1/8" stock — within this
design's 3.0–3.4mm tolerance band), one sheet each. Their quote is instant
at upload. Typical turnaround is roughly ~8 business days production +
shipping to NYC (check the quote page for current dates).

**Calibrate from the first order** (closes the loop for order #2+):

1. Find the small 110×25mm coupon strip. Measure its square hole with
   calipers. Its tool path is drawn at exactly 10.0mm (burn-neutral), so:
   `PONOKO_BURN = (measured − 10.0) / 2` — update it in
   `src/faxbox/config.py` if it differs from the current 0.10.
2. Press a real 6mm disc magnet into the 4 gauge holes (5.5 / 5.65 / 5.8 /
   5.95mm, left to right after the square). Whichever seats snugly sets
   `MAGNET_PRESS_FIT = MAGNET_DIA − <snuggest diameter>`.
3. If the first order's finger joints are loose/tight, the kerf-square
   reading from step 1 is the fix — regenerate and the next order is dialed
   in. (If joints on the FIRST order don't assemble at all, that's a
   thickness problem, not kerf — check the delivered ply with calipers
   against the 3.0–3.4mm band.)

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
