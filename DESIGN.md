# DESIGN.md — Canonical Geometry

This document is the single source of truth for the Fax Machine Box geometry.
`src/faxbox/config.py` implements these numbers; `tests/test_assembly_fit.py`
enforces the relationships. If code disagrees with this document, the code is
wrong. If this document seems wrong, comment on issue #15 — do not silently
change numbers.

Everything is in **millimeters**. Material is uniform **3.175mm (1/8") plywood**
(`T` below). Laser kerf is handled by Boxes.py's `burn` parameter (0.08mm
starting value — calibrate with a test cut before the real run). Finger holes
and slots are widened by `FINGER_PLAY` (0.1mm), giving a physical hole
through-dimension of `T + play` = 3.275mm — this covers nominal 3.175 stock
measuring up to ~3.275mm, but thicker stock (3.3–3.4mm, within the normal
3.0–3.4 range this ply is sold at) interferes by up to ~0.125mm (at 3.4) and
requires recalibrating `FINGER_PLAY` from the thickness coupon (which now
carries 3.30/3.40 gauges) before cutting. This makes edge-adjacent hole rows
break through their part edge by ≤ play/2, which is sub-kerf and hidden
inside joints — **except the top-panel hole row, see part #7 below.**

**Contents fit:** the SPEC envelope and compartment dimensions come from
Ben's fully functional cardboard prototype of this exact box (confirmed
2026-07-07) — the game's components are known to fit these interior volumes.
No separate component-dimension check is needed.

## Decisions this design implements (Ben, 2026-07-07)

- Drawers open from the **rear** 6.5"×5" end face (SPEC "Rear Drawer Housing").
- **"FAX MACHINE"** pixel-font engraving on the **right side wall** exterior.
- **Fixed top panel** over the drawer bay (not a removable lid).
- Sliding lid rides in **through-slots** cut through both side walls, open at
  the front edge; lid inserts from the front. Slot ends visible outside = accepted.
- Target service: NYC Resistor; blue `#0000FF` = cut, red `#FF0000` = engrave.

## Coordinate convention

Origin at the box's **exterior front-left-bottom corner**.

- **X**: length, 0 at front face → 304.8 at rear face (12")
- **Y**: width, 0 at left face → 165.1 at right face (6.5")
- **Z**: height, 0 at underside → 127.0 at top (5")

"Front" = the paper-compartment end. "Rear" = the drawer end.

## Global derived values

| Quantity | Value | Derivation |
|---|---|---|
| `T` material thickness | 3.175 | 1/8" ply |
| Interior length `L_INT` | 298.45 | 304.8 − 2T |
| Interior width `W_INT` | 158.75 | 165.1 − 2T |
| Wall base plane | Z = 0 | walls run full height; bottom panel inset between them |
| Interior floor top | Z = 3.175 | top surface of the inset bottom panel |
| Full wall height | 127.0 | exterior height |
| Sliding clearance | ≥ 1.5 | SPEC: min 1/16" on sliding interfaces |
| Faceplate reveal | 0.75/side | flush faceplate gap in its opening |

> **Amendment (2026-07-07, issue #17 prep):** the first revision stood the
> walls on top of a full-footprint bottom panel. That construction makes the
> rear wall's sill-free openings open-bottomed (no material below them —
> fragile free-standing legs). Current revision: full-height walls with the
> bottom panel inset between them (standard finger-box construction), giving
> a solid T-thick web under the bottom openings. All interior numbers are
> unchanged.

## Longitudinal layout (X axis)

| Region | X span | Size |
|---|---|---|
| Front wall | 0 → 3.175 | T |
| Paper compartment (interior) | 3.175 → 79.375 | 76.2 (3") |
| Vertical divider | 79.375 → 82.55 | T |
| Drawer bay (interior) | 82.55 → 301.625 | **219.075** |
| Rear wall | 301.625 → 304.8 | T |

## Vertical layout (Z axis)

| Feature | Z span | Notes |
|---|---|---|
| Bottom panel | 0 → 3.175 | inset between the walls |
| Front wall top edge | 118.025 | = lid slot bottom; lid slides over it |
| Lid slot (through side walls) | 118.025 → 122.0 | height 3.975 = T + 0.8 |
| Side-wall rail above slot | 122.0 → 127.0 | 5.0 tall, spans slot X range |
| Divider top edge | 123.825 | = top panel underside |
| Top panel (over bay) | 123.825 → 127.0 | fixed, finger-jointed |
| Bay interior height | 3.175 → 123.825 | 120.65 |
| Bottom drawer slot | 3.175 → 61.9125 | clear height 58.7375 |
| Horizontal shelf | 61.9125 → 65.0875 | T thick |
| Top drawer slot | 65.0875 → 123.825 | clear height 58.7375 |

**Lid slot vertical clearance is 0.8mm (not the SPEC's 1.5mm).** Deliberate
deviation: the SPEC's 1.5mm play is applied in the sliding *plane* (lid width,
drawer fits). Across the lid's thickness, 1.5mm would rattle; 0.8mm still
absorbs plywood thickness variation (+0.2 typical). Recorded here so tests can
assert 0.8 without someone "fixing" it back.

## Parts list

Nominal dimensions below are **interior-face spans**; finger joints extend a
part up to T beyond nominal on each jointed edge (Boxes.py handles this). The
SVG harness (#16) checks each part's bounding box is within
[nominal, nominal + 2T] per axis according to its jointed edges.

### 1. Bottom panel — 1×

- Nominal: **298.45 (X) × 158.75 (Y)**, inset between the walls at Z = 0 →
  3.175 (bottom face flush with the wall bottom edges). Edge fingers extend
  into hole lines cut through the four walls near their bottom edges
  (hole-line midplane at Z = 1.5875).
- Through-hole line for the divider's bottom-edge fingers at X = 79.375 →
  82.55 (midplane X = 80.9625).

### 2. Side walls — 2× (left Y=0→3.175, right Y=161.925→165.1)

**The two side walls are mirror images, not identical parts** — the lid slot
sits at the front only, so a single cut pattern cannot serve both sides.
Convention: draw both with the **exterior face up**; the left wall's features
are the right wall's mirrored in X. Engraving goes on the right wall only.

- Nominal: **298.45 (X) × 127.0 (Z)**, full height.
- Vertical edges: finger joints to front wall (only up to Z=118.025 on the
  front edge — above that is the lid slot mouth and rail end, plain) and rear
  wall (full height).
- Bottom edge: straight, with a through-hole line just above it (midplane
  Z = 1.5875) receiving the bottom panel's edge fingers.
- Top edge: plain, full height, entire length. The top panel joins through a
  **finger-hole line** below the top edge (midplane Z = 125.4125, X = 82.55 →
  301.625) — an edge-to-edge finger joint here would stand proud of the 127mm
  top plane (defect caught in #17 review).
- **Lid through-slot**: X = 3.175 → 79.375 within the wall, **open at the
  wall's front edge** (the lid could never be inserted otherwise),
  Z = 118.025 → 122.0. Construction: drawn as a closed rectangular hole whose
  front boundary exactly coincides with the blank's front edge — the laser
  cuts both lines and the mouth opens (in the kerf-compensated output the
  hole's front boundary and the blank's own front edge are not one
  coincident line but a parallel pair, 0.11mm apart for the NYC Resistor
  cut and 0.15mm for Ponoko, overlapping along ~3.1mm of the 3.975mm mouth
  — the laser burns that gap as a single ~0.3mm channel; still negligible,
  and since the two lines aren't coincident, Ponoko's doubled-line objection
  doesn't apply here). Leaves a 5.0mm rail above (Z 122 → 127) cantilevered from
  X = 79.375 — handle gently until assembled.
- **Divider finger-hole line**: vertical, X = 79.375 → 82.55, Z = 3.175 →
  123.825. (A Boxes.py `fingerHolesAt` line — a dashed row of T-wide holes,
  not one continuous slot.)
- **Shelf finger-hole line**: horizontal, Z = 61.9125 → 65.0875, X = 82.55 →
  301.625. (Dashed row, as above.)
- **Right wall only**: "FAX MACHINE" engraving (red), 5×7 pixel font,
  pixel size 4.0mm → text ≈ 240 × 28, centered at X = 152.4, Z = 63.5.
  Engrave on the exterior face (the drawn face, per the convention above).

### 3. Front wall — 1×

- Nominal: **158.75 (Y) × 118.025 (Z)** (Z = 0 → 118.025).
- Bottom-panel hole line near the bottom edge (midplane Z = 1.5875); vertical
  edges finger-joint to side walls; top edge plain (the lid slides over it).
- **Iteration 2**: carries the sole lid-retention turn-button pivot hole
  (Ø3.2, box Y = 82.55, box Z = 110.0) on its exterior face — see
  "Retention (iteration 2, magnets + turn-buttons)" section B.

### 4. Rear wall — 1×

- Nominal: **158.75 (Y) × 127.0 (Z)**, full height.
- Bottom-panel hole line near the bottom edge; sides → side walls; top edge
  plain, with a top-panel finger-hole line at midplane Z = 125.4125.
- **Two drawer openings**, each **152.4 wide (= W_INT − 2T) × 55.0 tall**,
  centered in Y (0.875mm inside each interior corner joint; visible frame from
  outside ≈ 6.35mm per side):
  - Bottom opening: Z = 3.175 → 58.175 (sill-free: bottom edge = floor top;
    the solid web below it, Z = 0 → 3.175, is exactly the inset bottom
    panel's edge zone).
  - Top opening: Z = 65.0875 → 120.0875 (sill-free: bottom edge = shelf top).
  - Webs remaining: 3.175 below the bottom opening, 3.7375 below the shelf
    line, 3.7375 above the top opening — each ≥ 3.0; do not enlarge openings.

### 5. Vertical divider — 1×

- Nominal: **158.75 (Y) × 120.65 (Z)** (Z = 3.175 → 123.825, standing on the
  bottom panel).
- Bottom edge fingers down through the bottom panel's hole line; side edges
  finger into side-wall hole lines; top edge fingers up into top panel holes.
  Fully captive on 4 edges → carries the structural load the SPEC requires.
- Its front face (X = 79.375) is the sliding lid's end stop.

### 6. Horizontal shelf — 1×

- Nominal: **219.075 (X) × 158.75 (Y)** at Z = 61.9125 → 65.0875.
- Side edges finger into side-wall hole lines (SPEC requirement); front edge
  fingers into a hole line in the divider; rear edge plain, butting the rear
  wall's interior face.

### 7. Top panel (drawer bay) — 1×

- Nominal: **222.25 (X, spanning 79.375 → 301.625 including the divider
  cover strip) × 158.75 (Y)** at Z = 123.825 → 127.
- Side and rear edges carry fingers that pass **through hole lines** in the
  side/rear walls (midplane Z = 125.4125), tips flush with the exterior
  faces — same joint style as the shelf and divider. Front edge plain,
  extending flush over the divider, with a finger-hole line receiving the
  divider's top-edge fingers at the divider midplane.
- **This hole row's breakthrough is NOT hidden like the other edge-adjacent
  rows** (see the material note near the top of this document): the row's
  midplane (Z = 125.4125) sits close enough to the wall top edge (Z = 127.0)
  that the hole top (127.05) breaks through the visible top edge itself,
  rather than staying buried inside the joint. The holes read as open-top
  notches along the top edge until glue-up — cosmetically a normal
  finger-joint look, but the top panel's actual uplift fixity depends on the
  specified PVA glue-up (README's glue step), not on geometry alone.

### 8. Sliding lid — 1×

- Blank: **79.0 (X) × 163.6 (Y)**, plain edges, plus a grip slot.
- Width 163.6 = 165.1 − 1.5 sliding clearance; edges engage 2.425mm into each
  side-wall through-slot (slots are through-cuts, so the slot floor is the
  full exterior width).
- Length 79.0 stops against the divider with the front edge ~0.4mm shy of the
  front face. Travel: slides in from the front, over the front wall top edge.
- Grip: rounded through-slot **30 × 10, r = 5**, centered in Y, slot center
  25mm from the front edge (10mm ligament to the edge; at 15mm the ligament
  was ~0.2mm and would have broken into a notch — red-team finding).
- No retention along the travel axis in v1: the divider stops rearward
  motion but nothing stops the lid sliding out the front when the box tips
  forward. **Iteration 2 (below) adds a single turn-button on the front
  wall to fix this** — see "Retention (iteration 2, magnets + turn-buttons)".

### 9. Drawers — 2× identical, 6 pieces each

Body = open-top finger-jointed box, captive bottom:

- Body external: **149.0 (Y) × 218.6 (X) × 53.5 (Z)**.
- Body interior: 142.65 × 212.25 × 50.325.
- Fit checks: passes its opening with ≥1.5mm on every edge (152.4−149.0 = 3.4
  across width; 55.0−53.5 = 1.5 in height); slides in a 58.7375 slot
  (5.24 headroom); bay length gap when closed ≈ 0.475 — **the divider is the
  drawer's in-stop** (the inset faceplate never bears on the rear-wall frame;
  red-team finding). Closed, the faceplate sits recessed by the 0.475 slide
  gap — near-flush, since true flush and slide clearance are mutually
  exclusive. There is no out-retention in v1: a drawer slides free if the
  box is tipped rear-down. **Iteration 2 (below) adds a magnet pair per
  drawer to fix this** — see "Retention (iteration 2, magnets + turn-buttons)".
- Lateral play in the bay is ~4.9mm/side by design — the drawer is guided by
  its opening, not the bay walls; max skew ≈ 1.3°, acceptable for a first cut.

Faceplate (6th piece), glued to the body front:

- Blank: **150.9 (Y) × 53.5 (Z)** = opening − 2 × 0.75 reveal; covers the body
  cross-section exactly in height, +0.95/side in width; flush with the rear
  face when closed (faceplate thickness T fills the rear wall plane).
- **Grip slot**: closed rounded slot **30 × 15, r = 7.5**, cut through BOTH
  the faceplate and the body's front wall, aligned, so a finger hooks through
  into the drawer. Centered in Y; slot top edge 8.0 below the part's top edge
  (slot spans 30.5 → 45.5 of the 53.5 height). A closed slot (not a top-edge
  notch) keeps the top edge stiff and the opening reveal continuous.
- Registration: red-engraved outline of the body cross-section on the
  faceplate's back for glue-up alignment.

## Retention (iteration 2, magnets + turn-buttons)

Decision record (Ben, 2026-07-07, issue #20): v1 ships from `main` with no
retention, as already decided above. This is the **recommended** iteration-2
mechanism — rigid, tolerance-insensitive, minimal parts — chosen over the
experimental spring-detent alternative (PR #22) for being the most-likely-
to-work path. Two independent mechanisms, one per moving part class.

> **Revision note (adversarial review, 2026-07-07):** the lid mechanism
> below is **REV.B**. The original design (REV.A: a pivoting paddle on
> EACH side wall) was found in review to be geometrically incapable of
> retaining the lid — the paddle's sweep plane and the lid's travel band
> never intersect, at any pivot position — and was replaced with REV.B (one
> button on the front wall) before any part was cut. See section B below
> for the full proof. The drawer-magnet mechanism (section A) was not
> affected by that finding, but section A below has also been amended with
> an honest accounting of the drawer's leading-end lateral float
> (adversarial-review finding #4) and its mitigation.

### A. Drawer retention — magnet pair per drawer

One 6mm-nominal disc magnet, press-fit into a through-hole in the drawer's
**leading body wall** (the "Back" piece in `generate_drawers.py` — the deep
end opposite the faceplate/grip-slot end) and a matching coaxial hole in the
**divider**, at the drawer's fully-closed position (the divider is the
drawer's in-stop, contact gap 0 — part #9 above). An attracting pair pulls
the drawer closed.

- New config constants: `MAGNET_DIA = 6.0`, `MAGNET_PRESS_FIT = 0.35`,
  `MAGNET_HOLE_DIA = MAGNET_DIA - MAGNET_PRESS_FIT = 5.65`.
- **BURN/press-fit interaction** (researched against Boxes.py's own
  `gridfinitybase.py` generator, which drills its own magnet holes via plain
  `self.hole(x, y, d=dia)` with a `dia - 0.5` press-fit variant — same
  pattern used here): `self.hole()` burn-compensates the drawn tool path the
  same way every other hole in this project is compensated, so the physical
  (post-kerf) hole size is governed by `MAGNET_PRESS_FIT` alone, as long as
  `BURN` stays calibrated via the kerf coupon. The two constants are not
  redundant: `MAGNET_PRESS_FIT` sets size relative to the magnet;
  `BURN` is what makes the *drawn* path smaller so the laser's kerf widens it
  back out to `MAGNET_HOLE_DIA`. Recalibrate `MAGNET_PRESS_FIT` via the
  magnet-fit coupon (below) before cutting real parts — it is a starting
  guess with the same status as `BURN`/`FINGER_PLAY`.
- Position: offset from the drawer's own Y-center by `MAGNET_Y_OFFSET =
  40.0mm` (config.py) — clear of the grip-slot zone (30mm wide, Y-centered,
  though on the OTHER end panel). Both drawers use the same offset; since
  each drawer is Y-centered in its rear-wall opening at closed position, the
  drawer's Back-wall hole and both divider holes share one box Y = `T +
  INTERIOR_WIDTH/2 + 40.0 = 122.55`. Checked: this sits ~39mm from the
  divider's nearer Y-edge (half its 158.75 width, minus the 40mm offset) and
  34.5mm from the Back panel's nearer finger edge (half its narrower 149.0
  width, minus the same 40mm offset) — both ≫ the 3mm minimum, so the choice
  of +40 vs. −40 is arbitrary given either margin; +40 (toward increasing Y)
  was picked with no other reasoning.
- Z: "drawer mid-height" (`DRAWER_BODY['height']/2`) is a property of the
  drawer body alone; on the divider (a fixed part) it is projected via each
  slot's own resting datum — the bottom drawer rests on the bay floor
  (sill-free, `BOTTOM_OPENING_Z0 = FLOOR_TOP`), the top drawer on the shelf
  top (`TOP_OPENING_Z0 = SHELF_Z1`) — giving two divider holes:
  `MAGNET_BOTTOM_DRAWER_Z = FLOOR_TOP + height/2 = 29.925`,
  `MAGNET_TOP_DRAWER_Z = SHELF_Z1 + height/2 = 91.8375`.
- Clearances (measured from the generated SVGs): both divider holes sit
  ≥23mm from every divider edge and ≥23mm from the divider's own shelf
  finger-hole row — comfortably over the 8mm structural-clearance target for
  this fully-captive, 4-edge load-bearing panel (part #5). The drawer
  Back-wall hole sits ≥20mm from every one of its own edges (well over the
  general 3mm minimum).
- Install AFTER assembly test-fit: pair the two magnets stuck together, mark
  the outward faces with a sharpie before separating, press-fit each into
  its hole, then CA glue. Recommend **6×2mm N35 discs** (gentler pull,
  ~0.5–0.7kg at contact — one-finger openable); force is tunable by buying
  N52 or 3mm-thick discs instead, no geometry change. **Install the magnets
  FLUSH with the two MATING faces** (the drawer-Back's rear face and the
  divider's front face — the faces that actually close the gap), recessing
  only on the far (non-mating) side where the glue backfills; a 2mm disc
  recessed 1.2mm on its *mating* side, mirrored on both parts, would leave
  a ~2.4mm pole-to-pole gap across the joint that collapses the quoted
  0.5–0.7kg pull to roughly 0.1–0.17kg — an easy mistake to make since
  "recessed, glue backfills" is fine for a joint that only needs to look
  clean, but not for a magnetic joint that needs the poles to meet. **6×3mm
  discs are the low-risk alternative**: at 3mm they sit near-flush on both
  sides regardless of which face is nominally "mating," so a flush-vs-
  recessed install mistake can't collapse the pull as badly.
- **Leading-end float, honestly stated (adversarial-review finding #4):**
  the magnet sits on the drawer's Back (leading) wall, where lateral play in
  the bay is **±4.9mm/side** (part #9 above — the drawer is guided by its
  rear-wall opening, not the bay walls). At the moment the magnets first
  come into proximity, nothing has yet centered the drawer to better than
  that ±4.9mm bay float — the divider hole and the Back-wall hole are NOT
  guaranteed coaxial at first approach.
  - **Capture sequence**: true Y-centering only happens in the drawer's
    **final ~2.4mm of travel** (`FACEPLATE_thickness − FACEPLATE_REVEAL` =
    `T − 0.75 = 2.425mm`, i.e. the last stretch where the faceplate itself is
    entering its snug rear-wall opening, ≥1.5mm total clearance
    width-wise) — the faceplate's own fit against its opening is what
    narrows the drawer's lateral position, but the magnet hole sits at the
    OPPOSITE (Back/leading) end of the drawer, 218.6mm away from that
    faceplate datum: over that lever arm, the ≈±0.75mm the faceplate itself
    resolves at its own end translates to a residual yaw of up to 0.57°
    with the faceplate seated, which reopens to **≈±2.9mm** of lateral
    play at the magnet end — not the faceplate's own ±0.75mm. Before that
    final stretch, the drawer body alone (loose in the ±4.9mm bay float) is
    doing the guiding, not the faceplate.
  - **Residual worst case**: at the moment the faceplate starts entering its
    opening (magnet gap closing to contact), the drawer could still be
    off-center by close to the bay's own float before the faceplate's fit
    takes over and narrows it — i.e. the magnets are relying on the
    faceplate/opening fit, not the magnet holes' own placement tolerance, to
    do the fine centering. The magnet pair's pull (a few mm of magnetic
    reach at contact) is what closes the last bit of any residual
    misalignment once the faceplate has already done the coarse centering.
  - **Mitigation — self-registering install, not a geometry fix:** install
    the magnets AFTER a full dry test-fit (already required — see "Install
    order" below), and **mark the drawer-side magnet's actual contact point
    through the divider hole while the drawer is closed**, rather than
    trusting the two holes' nominal coaxiality on paper. Concretely: with
    the drawer fully closed (faceplate seated in its opening) and the
    divider-side magnet already glued in place, hold the drawer-side magnet
    (or a scribe) through the Back-wall hole and mark/scribe its true
    contact point against the (temporarily uninstalled or masked) divider
    face before final placement — this makes the install self-correcting
    for whatever the real, as-built float turns out to be (the ±2.9mm yaw
    residual at the magnet end even with the faceplate seated, or the full
    ±4.9mm bay float before it engages), instead of depending on either
    number never mattering on paper. README's install steps (below) state
    this explicitly.
  - This is why `test_magnet_holes_coaxial_at_closed_position`
    (`tests/test_retention.py`) is checked against a **0.6mm** tolerance
    band, not the bay's full ±4.9mm float: that test asserts the two
    *drilled hole positions* agree with the DESIGN.md numbers (a drafting
    check), not that the assembled drawer will actually make contact
    dead-center on first try — the self-registering install above is what
    reconciles the two.

### B. Lid retention — ONE turn-button on the FRONT WALL

**Adversarial-review finding #1 (critical): the original mechanism below
(REV.A) was geometrically incapable of retention and was caught before any
part was cut.** REV.A put a pivoting paddle on each SIDE wall, just
below/behind that wall's lid-slot mouth. The proof it could never work: on
a side wall, the paddle sweeps that wall's own **exterior plane** (e.g. the
left wall's exterior sits at box Y −3.175 → 0), while the lid's edge riding
in that same wall's through-slot occupies box Y 0.75 → 3.175 and **exits by
travelling along X** — axially past the paddle's sweep plane, never through
it. The paddle's swept volume and the lid's travel band are disjoint at
*every* pivot position and paddle length; no parameter tweak (moving the
pivot, lengthening the paddle) could have fixed it, because the two moving
parts don't occupy overlapping space at any point in the mechanism's own
rotation. The side-wall pivot holes have been **removed entirely** — the
side walls are now byte-identical to `main`'s v1 geometry (verified by
diffing the regenerated SVG against `main`'s own output; see
`test_side_wall_matches_main_footprint` in `tests/test_retention.py`).

**REV.B (current): a single button on the FRONT WALL's exterior face**
(box X=0 plane) — the plane the lid's own front edge physically crosses on
its way out, so the paddle's sweep and the lid's exit band now genuinely
overlap.

A rounded paddle ("stadium": rectangle + full semicircular end caps,
`~22mm × 9mm`, `TURN_BUTTON` in config.py — unchanged from REV.A, only its
mounting location/orientation moved) pivots on an M3 bolt through the front
wall, and turns up to physically block the lid's exit cross-section
(caging the lid between the button and the divider stop) or down to clear
it entirely.

- Pivot hole Ø3.2 (M3 clearance) on the front wall's exterior face at box
  **Y = 82.55 (wall center), Z = 110.0** (`TURN_BUTTON_PIVOT_BOX_Y/Z` in
  config.py). No mirroring — there is only one front wall and only one
  button.
  - Y = wall center (`SHELL_EXT["width"]/2` = 82.55) sits `INTERIOR_WIDTH/2
    = 79.375mm` from either vertical (side-wall) finger-joint zone — far
    past the required 3mm.
  - Z = 110.0 clears the bottom-panel hole line (Z ≈ 1.5875) by
    a huge margin and clears the wall's own plain top edge
    (`FRONT_WALL_TOP = 118.025`) by 8.025mm (≥ 3mm).
- **Blocking slop**: the sliding lid's front edge, at full rearward travel,
  sits at box X ≈ 0.375 — recessed ~0.4mm behind the front wall's own
  exterior plane (X=0), since `SLIDING_LID` length (79.0) is ~0.4mm short of
  the 79.375mm travel to the divider stop. This means there is a small
  (~0.4mm) free-slide gap before the lid's edge makes contact with a
  lowered button — negligible next to the ≥1mm blocking margins below, but
  stated here so it isn't mistaken for a fit defect.
- **Reach and the blocking geometry** (this is what REV.A's design notes
  never actually verified — see the note on the blocking TEST below): the
  lid, resting under gravity on its slot floor, occupies the bottom `T` of
  the slot's vertical clearance band when it crosses the front wall's
  plane: box Z `LID_SLOT_BOTTOM (118.025) → LID_SLOT_BOTTOM + T (121.2)`
  (`LID_FRONT_BAND_Z0/Z1` in config.py) — not the full
  `LID_SLOT_BOTTOM..LID_SLOT_TOP` clearance span (that extra 0.8mm is slop
  *above* the lid, not lid material). The button's pivot sits
  `pivot_from_blunt_end = 4.5mm` (= half its own width, the blunt end's own
  rounded-cap center) from its blunt end, so pivot→tip reach =
  `22.0 − 4.5 = 17.5mm`.
  - **Rotated UP** (paddle pointing +Z): the button's blunt-cap rear sits at
    box Z = `110 − 4.5 = 105.5` (below the lid band already) and the tip
    reaches box Z = `110 + 17.5 = 127.5` — comfortably past the required
    `(121.2 + 1) = 122.2` (5.3mm of margin), standing proud in open air
    above/in front of the lid-slot region where nothing else is present to
    hit. In Y, the paddle's ±4.5mm half-width band (box Y 78.05 → 87.05)
    sits well inside the lid's own Y-span (0.75 → 164.35), so a single
    button blocking one point along the lid's rigid width is sufficient —
    it doesn't need to span the whole 163.6mm lid width, any more than a
    door's single deadbolt needs to span the whole door.
  - **Rotated DOWN** (180° from vertical): the button's now-topmost point
    (the blunt cap) sits at box Z = `110 + 4.5 = 114.5`, which is 3.525mm
    *below* `FRONT_WALL_TOP = 118.025` — the whole paddle clears the lid's
    travel path so the lid slides freely when the button is disengaged.
- **The blocking test** (`test_button_up_envelope_blocks_lid_exit` in
  `tests/test_retention.py`) is the assertion whose ABSENCE let REV.A ship:
  it computes, from independent datums (`SHELL_EXT`/`SLIDE_CLEARANCE` for
  the lid's Y-span; `LID_SLOT_BOTTOM`/`T` for its Z-band; the pivot position
  plus the *measured* paddle reach off the real `hardware.svg` piece — not
  assumed from config), whether the button-up envelope actually overlaps
  the lid's exit cross-section in BOTH Y and Z, with ≥1mm margin. Moving the
  pivot to a non-blocking Z, shrinking the paddle so its measured reach came
  up short, or re-siting the whole mechanism onto a wall the lid never
  crosses would all fail this test — a purely positional "hole exists at
  (X,Z)" check (which REV.A had, and which passed) would not have caught
  any of those.
- Hardware (documented, not laser-cut): **1× M3×12 button-head bolt, 1× M3
  nyloc nut, 2× M3 washer** — nyloc tensioned so the button holds position
  by friction, not a spring. The nut lands inside the paper compartment,
  reachable with the lid off.
- The single button piece is cut from `output/hardware.svg`
  (`generate_hardware.py`), standalone like the calibration coupons — not
  nested into any `sheet_*.svg`.

### C. Magnet press-fit coupon

`output/magnet_coupon.svg` (`calibration.py`'s `generate_magnet_coupon()`):
a row of 4 holes labeled 5.5 / 5.65 / 5.8 / 5.95mm, each with a gray
reference-only text label. **Adversarial-review finding #3 (fixed):** these
gauge holes are now drawn through the SAME burn-**compensated** `self.hole()`
path the real divider/drawer part holes use — a labeled 5.65mm gauge hole
here is now physically identical to what a labeled-5.65mm PART hole
actually gets. Previously the gauge holes were drawn burn-**neutral** (like
the kerf square below), which measures a *different* physical diameter than
the part will ever get: a burn-neutral hole labeled 5.65 cuts out at
physical `5.65 + 2×BURN` (≈5.81mm at `BURN=0.08`), while a burn-compensated
PART hole labeled 5.65 cuts out at physical 5.65 exactly — the old coupon
was silently reading ~0.16mm oversize, eating **~46%** of the whole 0.35mm
press-fit budget before a magnet was ever pressed in.

**Do NOT apply this fix to the kerf square** in the same file
(`CalibrationCoupon`/`generate_calibration()`): that square exists
specifically to *measure the kerf itself*, so it must stay burn-neutral
(drawn tool path = exactly 10.0mm, physical = 10.0 + 2×real-kerf) — see
`calibration.py`'s own module comment for why burn-compensating it would be
self-defeating (it would just report how close the *current, unvalidated*
`BURN` guess is to itself). The magnet coupon and the kerf square measure
two different things and must stay on two different code paths; the
distinction is documented in `calibration.py`'s docstring.

Press a real 6mm disc magnet into each of the 4 gauge holes on scrap;
whichever seats snugly (not loose, not forced) sets `MAGNET_PRESS_FIT =
MAGNET_DIA − <snuggest diameter>` in config.py. Cut this coupon (and the
kerf coupon) again any time `BURN` changes — both coupons' readings depend
on it.

## Clearance summary (what the tests enforce)

| Interface | Clearance | Rule |
|---|---|---|
| Drawer body ↔ opening width | 3.4 total | ≥ 1.5 per SPEC |
| Drawer body ↔ opening height | 1.5 | ≥ 1.5 |
| Drawer body ↔ slot height | 5.24 | ≥ 1.5 |
| Drawer body ↔ bay length | 0.475 | > 0 (not a sliding fit) |
| Lid width ↔ slot span | 1.5 total | ≥ 1.5 |
| Lid thickness ↔ slot height | 0.8 | = 0.8 (documented deviation) |
| Faceplate ↔ opening | 0.75/side | reveal 0.5–1.0 |
| Webs in rear wall | 3.175 / 3.7375 | ≥ 3.0 |
| Magnet hole (drawer Back) ↔ its own edges | ≥ 20 | ≥ 3.0 |
| Magnet hole (divider) ↔ edges / shelf row | ≥ 23 | ≥ 8.0 (structural) |
| Turn-button pivot (front wall) ↔ side joint zones | ≥ 79.375 each side | ≥ 3.0 |
| Turn-button pivot (front wall) ↔ wall top edge | 8.025 | ≥ 3.0 |
| Turn-button reach ↔ required reach (up, blocking) | 17.5 vs. 12.2 | ≥ required |
| Turn-button-up envelope ↔ lid exit band (Y, Z) | wide margin both axes | ≥ 1.0 each axis (the blocking test) |
| Turn-button-down top ↔ front wall top edge | 3.525 | ≥ 1.0 |

### QA notes (2026-07-09 adversarial pass)

- The largest **drawn** part is the Shell Bottom at **304.96 × 165.26mm**
  (full footprint including finger extensions and burn compensation) — not
  the oft-quoted 298.45 (X) × 158.75 (Y) interior figure (`L_INT`/`W_INT`
  above), which is the interior span, not the cut blank's bounding box.
- Minimum viable laser bed, allowing a 10mm margin on all four sides of that
  part: **324.96 × 185.26mm**.
- The rear wall's bottom web (below the bottom drawer opening) measures
  **3.27mm** in the generated SVG, and is perforated by the bottom panel's
  finger-hole row (part #4's through-hole line near the bottom edge) — it is
  structurally sound per the ≥3.0 rule above, but is a thin, hole-perforated
  strip; handle the rear wall gently before assembly (glue-up) locks it in.

## Known deltas from SPEC.md targets

- Drawer external length 221.775 (body 218.6 + faceplate T) vs SPEC "9.0 external":
  the difference is consumed by the front wall, divider, and rear wall within
  the fixed 12" envelope. SPEC marks drawer dims "to fit" — envelope wins.
- Drawer external width 149.0 vs SPEC "approx 6.3" (160)": constrained by the
  rear-wall opening needing ≥T structural webs at the corners plus pass-through
  clearance. SPEC marks this "to fit".
