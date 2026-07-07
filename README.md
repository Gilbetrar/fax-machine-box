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
.venv/bin/python -m faxbox.calibration        # kerf/thickness test coupon -> output/kerf_coupon.svg (cut on scrap FIRST, see "Cut-day checklist")
```

`layout.py` also writes `output/final_layout.svg` — a combined, true-scale
view of every sheet side by side, for eyeballing the whole nesting in a
browser in one shot. **`final_layout.svg` is bigger than any real laser bed
and must never be sent for cutting** — send `sheet_1.svg`, `sheet_2.svg`,
... individually. Each `sheet_N.svg` is itself real, complete, laser-ready
input: the right SVG to open and inspect before cutting is one of those, not
`final_layout.svg`.

## Test

```bash
.venv/bin/python -m pytest tests/ -v
```

The test suite regenerates `output/*.svg` from current source before
checking it (see `tests/conftest.py`), so it always measures what the code
*currently* produces, not stale files. All tests must be green with zero
`xfail`s before cutting anything — this is the project's standing policy
(see `LEARNINGS.md`).

## Project Structure

```
fax-machine-box/
├── src/faxbox/
│   ├── config.py            # single source of truth for all dimensions (implements DESIGN.md)
│   ├── shell_generator.py   # outer shell: bottom, 4 walls, divider, shelf, top panel (8 pieces)
│   ├── generate_drawers.py  # one drawer's 6 pieces (body x5 + faceplate); cut this sheet twice
│   ├── generate_lids.py     # sliding lid (1 piece)
│   ├── layout.py            # nests all parts onto bed-sized sheets for cutting
│   └── calibration.py       # kerf/ply-thickness test coupon -> output/kerf_coupon.svg
├── tests/                   # pytest harness: geometry, laser-compliance, and layout checks
├── docs/service-comparison.md  # laser service comparison + verified NYC Resistor constraints
├── DESIGN.md                # canonical geometry — the source of truth for every number
└── output/                  # generated SVGs (gitignored)
```

## Color coding

- **Blue (`#0000FF`)** = cut line
- **Red (`#FF0000`)** = engrave line (the "FAX MACHINE" text on the right
  wall, and the faceplate glue-up registration outlines) — the "FAX MACHINE"
  letters are hatched engrave strokes, cut at vector/engrave settings, not
  filled.
- **Gray** = reference-only text (part labels, sheet numbers). These are
  *not* laser instructions — ignore/skip this color when setting up the job.
  Sheet cut/engrave strokes themselves are drawn hairline-weight (0.0762mm)
  so they don't get mistaken for fills.

This is a convention this project chose (see DESIGN.md's "Decisions"
section), not a documented NYC Resistor requirement — no color convention
could be confirmed on their site. See `docs/service-comparison.md` for
details.

## Parts checklist

21 pieces total, all cut from uniform 3.175mm (1/8") plywood, plus one
standalone calibration coupon (not a box part — see "Cut-day checklist").
Matches DESIGN.md's parts list exactly.

**Outer shell — `output/sheet_*.svg`, 8 pieces, cut once (from
`outer_shell.svg`):**

- [ ] 1× Bottom panel (inset between the four walls)
- [ ] 1× Left Wall
- [ ] 1× Right Wall (carries the "FAX MACHINE" engraving)
- [ ] 1× Front Wall
- [ ] 1× Rear Wall (two drawer openings)
- [ ] 1× Vertical Divider (separates paper compartment from drawer bay)
- [ ] 1× Horizontal Shelf (splits the drawer bay into upper/lower slots)
- [ ] 1× Top Panel (fixed, over the drawer bay — **not** a removable lid)

**Drawers — 6 pieces × 2 identical sets = 12 pieces (from `drawer.svg`, cut
the same sheet TWICE):**

- [ ] 2× Front (body)
- [ ] 2× Back (body)
- [ ] 2× Left Side (body)
- [ ] 2× Right Side (body)
- [ ] 2× Bottom (body)
- [ ] 2× Faceplate (glued to the body front, not finger-jointed)

Drawer body external dimensions: 149.0mm (Y) × **218.6mm (X, pull
direction)** × 53.5mm (Z). The divider is the drawer's in-stop (see "Know
before you build").

**Lid — 1 piece (from `lids.svg`):**

- [ ] 1× Sliding Lid (rides in through-slots cut into both side walls)

There is **no separate flat/tabbed lid** — that part doesn't exist in this
design. The drawer bay is covered by the fixed Top Panel above, not a
removable cover.

**Calibration — standalone, not part of the box (from `kerf_coupon.svg` and
`retention_coupon.svg`):**

- [ ] 1× Kerf/thickness coupon — three ply-thickness gauge slots (3.05 /
  3.175 / 3.30mm) and a 10mm reference square. Cut this on scrap *before*
  cutting any real part; see "Cut-day checklist" step 3.
- [ ] 4× Retention coupon pieces (issue #20) — Wall Flexure Sample, Lid
  Notch Strip, Faceplate Flexure Sample, Mock Opening Edge. Cut on scrap
  *before* the real iteration-2 parts; see "Cut-day checklist" step 3b.

## Wall identification (read this before assembly)

The Left and Right side walls are **mirror images**, not identical parts —
and after sheet labels were recolored gray (reference-only, ignored by the
laser), there's no printed "LEFT"/"RIGHT" callout on the cut piece itself.
Identify a wall by its features:

1. Hold the wall with the **lid slot near the top edge** and the slot's
   **open mouth pointing left**. The open mouth end is the wall's **front**.
2. Look at the **divider finger-hole column** — the vertical dashed row
   about 3" (79.4mm) in from the mouth end. If that column sits **just right
   of the slot's closed (rear) end**, and the "FAX MACHINE" **engraving
   faces you**, you're looking at the **Right Wall's exterior** (engraving
   only ever goes on the right wall's outside face).
3. The other wall — same silhouette, no engraving — is the **Left Wall**.
   It's a true mirror image, not the same part flipped over: don't try to
   flip the engraved wall to "make" a left wall.

Getting this wrong means the lid slot mouths end up on opposite ends of the
box and nothing will dry-fit — check this *before* the dry-fit in step (a)
below.

## Assembly steps

This is the *current* (post-rebuild) design: fixed top panel, through-slot
sliding lid, glued faceplate drawers, inset bottom panel. See DESIGN.md for
every number and the reasoning behind each joint.

**The captive-parts problem.** The Divider, Shelf, and Top Panel are each
captive on *both* side walls — their fingers seat into dashed
`fingerHolesAt` hole rows cut into both the Left and Right walls. Fingers
only seat with straight-in, perpendicular motion, and the two side walls
need that motion from *opposite* directions. That means you **cannot**
glue up all four walls into a box first and then try to drop the Divider,
Shelf, or Top Panel in afterward — there is no gap they could enter
through. Everything captive on both side walls has to go in while one side
wall is still off, then the second side wall closes over all of it at once.
That drives the whole order below.

**(a) Full dry-fit — always, no glue.**
   Before any glue touches anything, dry-fit the *entire* box: both side
   walls, front wall, rear wall, bottom panel, divider, shelf, top panel,
   both drawer bodies, both faceplates, and the lid. Confirm the Wall
   identification step above got Left/Right right — everything should sit
   together with hand pressure, no forcing. Take it back apart.

**(b) Lay one side wall flat, interior face up.**
   Pick either side wall (see "Wall identification" above) and lay it flat
   on the bench with its interior (hole-row) face up. This wall is your
   fixture for the next step — everything else pilots into it.

**(c) Insert every captive part into that one wall, simultaneously.**
   Working on the flat wall, seat all of the following into their hole
   rows/edges at once:
   - the **bottom panel**'s edge fingers into the wall's bottom hole row,
   - the **divider**'s fingers into the wall's vertical divider hole
     column,
   - the **shelf**'s and **top panel**'s fingers into the wall's horizontal
     hole rows,
   - the **front wall** and **rear wall**'s corner fingers into the wall's
     front/rear edges,
   - and, at the same time, the **top panel**'s rear fingers into the
     **rear wall**'s top hole row (the top panel bridges both the side wall
     and the rear wall, so this joint has to close together with the rest).
   This is fiddly with six parts converging on one wall — that's expected.
   Get everything seated square before moving to (d); nothing is glued yet.

**(d) Close the second side wall down over all of it — one motion.**
   Lower the other side wall (the mirror twin) straight down onto all the
   protruding fingers from step (c) at once. This is the highest-stress step
   in the build: every captive joint closes simultaneously and there's no
   way to adjust one joint without disturbing the others.
   - **Dry-fit this closing motion twice**, fully, before any glue is
     involved — you want the exact path memorized.
   - Use a **slow-set (not fast-tack) PVA** wood glue so you have working
     time if a joint needs coaxing while others are already engaging.
   - **Have clamps staged and ready** (across both side walls, front-to-rear
     and top-to-bottom) before you start — you will not have a free hand to
     go find them mid-close.

**(e) Square up and clamp.**
   With both side walls closed over the captive parts, square the box (measure
   diagonals) and clamp while the glue sets. **Check squareness using the
   drawers**: a properly square bay lets both drawer bodies dry-slide into
   their rear-wall openings evenly on both sides with no binding; if one
   side drags and the other doesn't, the box is out of square — adjust
   clamping before the glue sets, not after.

**(f) Assemble both drawers (×2, identical), separately.**
   For each drawer: finger-joint Front + Back + Left Side + Right Side at
   the vertical corners, then slide the Bottom panel into the hole lines at
   the base (captive, not edge-jointed). Test-fit each body in its rear-wall
   opening before gluing the faceplate on.

**(g) Glue on the faceplates (×2).**
   Each Faceplate glues flush to its drawer body's front face — align it
   using the **red-engraved registration rectangle** on the faceplate's
   back (it traces the drawer body's front cross-section: center the body
   on the rectangle, don't just eyeball edges), clamp, and check that the
   faceplate's grip slot lines up with the body Front's grip slot before
   the glue sets — a finger needs to reach through both into the drawer.
   Faceplates sit flush with the rear wall's exterior plane when the drawer
   is closed (closed = bottomed out against the divider, see "Know before
   you build").

**(h) Slide in the Sliding Lid — last.**
   Insert the Sliding Lid from the front, over the Front Wall's top edge and
   into the through-slots cut into both side walls. It travels until it
   stops against the Vertical Divider's front face. The slots are open at
   the walls' front edge specifically so the lid *can* be inserted this way
   — there's no other assembly order that works for this part. **Never
   glue the lid or its slots** (see "Know before you build" — it's designed
   to slide, not be fixed).

**Glue guidance:**
- **PVA wood glue, applied sparingly**, on finger joints only.
- **Never glue:** the drawers' sliding faces, the inside of the drawer bay,
  the lid, or the lid slots. Anything meant to slide must stay unglued and
  clean.
- **Wipe squeeze-out inside the bay immediately** — dried glue in the
  drawer bay is the single easiest way to seize a drawer that should slide
  freely.
- Faceplate-to-body glue-up is the one exception where alignment matters
  more than a light touch: see step (g) above.

## Know before you build (honest limitations)

This design accepts some real tradeoffs to hit the SPEC envelope and the
front-insert lid concept. None of these are bugs — they're documented so
nobody "fixes" them mid-build or is surprised later:

- **The sliding lid has spring-detent retention (iteration 2, issue #20),
  not a lock.** Each side wall carries a cantilever nub that pops through a
  matching notch in the lid's side edges when it's closed, holding it
  seated if the box tips 90° front-down. It's still a light detent, not a
  latch — don't rely on it against a hard drop, and it still slides free
  with normal one-finger effort when you want it to. See DESIGN.md
  "Retention (iteration 2)" for the mechanism; **tune the fit on the
  retention coupon before cutting real parts** (see the checklist below).
- **The drawers have the same kind of detent, not a hard stop.** Each
  faceplate carries a cantilever nub per side that snaps behind the
  rear-wall opening's edge on close, holding the drawer seated if the box
  tips 90° rear-down. Same caveat: a detent, not a latch — pull with the
  grip slot as usual to open.
- **Drawers close flush by bottoming out on the divider, not the rear
  wall.** The inset faceplate never bears against the rear-wall opening
  frame — the drawer body's front face is what stops against the divider
  at the far end of its travel. If a drawer doesn't sit flush, check for
  glue or debris on the divider face, not the rear-wall opening.
- **The 5mm rail above each lid slot is permanently fragile.** It's a thin
  (5.0mm) cantilevered strip of ply above the slot cut, unsupported along
  most of its length. **Never force the lid** — if it binds, stop and check
  for a swollen/misaligned joint rather than pushing through.
- **The lid slot's vertical clearance is 0.8mm, not the SPEC's 1.5mm.**
  This is a deliberate, documented deviation (see DESIGN.md), not an error:
  applying the SPEC's full 1.5mm play across the lid's *thickness* would
  make it rattle in the slot. The 1.5mm sliding play the SPEC calls for is
  still honored **in-plane** (lid width vs. slot span, drawer body vs.
  opening) — it's only the through-thickness clearance on the lid slot that
  is intentionally tighter, at 0.8mm.

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
   5.0mm cantilevered lid rail) when the laser hits a void instead of solid
   wood. Bring at least **three sheets, each at least 22"×15"**, plus extra
   scrap for the kerf coupon (step 3). Orient sheets with the **face grain
   running along the sheet's long axis** for stiffness on the long spans.
3. **Cut `output/kerf_coupon.svg` on scrap FIRST, before any real part.**
   It has three ply-thickness gauge slots (3.05 / 3.175 / 3.30mm) and a
   10mm reference square. Find which gauge slot *your actual sheet* fits
   into snugly, and measure the cut size of the 10mm square with calipers.
   If either is off from nominal, adjust `BURN` (kerf compensation) and/or
   `FINGER_PLAY` (thickness compensation) in `src/faxbox/config.py` and
   regenerate **everything** (`shell_generator`, `generate_drawers`,
   `generate_lids`, `layout`, and `calibration` — then RE-CUT the coupon to
   confirm before trusting the gauge slots) before cutting real parts. Do not skip this
   because `BURN`/`FINGER_PLAY` already have values in the repo — those are
   starting values, not calibrated ones.
3b. **Cut `output/retention_coupon.svg` on scrap NEXT, before the real
   iteration-2 parts** (issue #20's spring-detent lid/drawer retention — see
   DESIGN.md "Retention (iteration 2)"). Four small pieces: a Wall Flexure
   Sample + Lid Notch Strip (press the notch over the sample's nub and feel
   it snap in/out), and a Faceplate Flexure Sample + Mock Opening Edge
   (slide the mock edge across the sample's nub the way a real close would).
   Too loose (pops out with a light nudge) or too stiff (won't seat without
   force, or feels like it might snap the nub off) — adjust
   `LID_DETENT_ENGAGE` and/or `DRAWER_DETENT_PROTRUDE` in
   `src/faxbox/config.py`, regenerate `calibration` (and everything else,
   since those constants also drive the real wall/lid/faceplate geometry),
   and re-cut before trusting the real parts' fit. Cut both flexure samples
   with the same grain orientation the real parts will have (see DESIGN.md's
   Grain caveat) — the faceplate sample bends across grain, the weaker
   direction, so it's the one most likely to need tuning or a fallback to
   magnets if the ply proves too brittle.
4. **CorelDraw import.** NYC Resistor's workflow is CorelDraw-based; their
   tips page warns Inkscape's raw SVG export can get corrupted there and
   recommends exporting PDF instead. On import: set all strokes to
   **hairline** if the importer doesn't respect the file's native
   0.0762mm hairline stroke width. Color mapping: **blue = vector cut**,
   **red = engrave**, **gray text = ignore** (reference-only part/sheet
   labels — not a cut or engrave instruction). The "FAX MACHINE" letters
   are hatched engrave strokes, not filled shapes — engrave them at vector
   (stroke) settings, same as the other red lines.
5. **Cut order: engrave first, then interior holes, then part outlines
   (inside-out), and set this explicitly** — don't assume the driver
   preserves file order. Engrave the red "FAX MACHINE" text and faceplate
   registration outlines while the sheet is still whole and flat, then cut
   interior finger-joint holes and slots, then cut part outlines free last.
   Cutting outlines before interior holes risks a loose piece shifting
   under the head before its holes are cut.
6. **Handle cut side walls flat.** The 5.0mm rail above each lid slot is
   thin and cantilevered — it can snap if a side wall is picked up by an
   edge or flexed. Lift and carry side walls flat, supported across their
   full face, until assembly.
7. **Take the laser class first** if you haven't (required for the $1/min
   self-serve rate; runs ~monthly). Operator-assisted time is $75/hr +
   $2/min if you skip it.
8. **Cut all sheets and the coupon, then dry-fit before gluing anything** —
   see "Assembly steps" above.
