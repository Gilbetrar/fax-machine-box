# DESIGN.md — Canonical Geometry

This document is the single source of truth for the Fax Machine Box geometry.
`src/faxbox/config.py` implements these numbers; `tests/test_assembly_fit.py`
enforces the relationships. If code disagrees with this document, the code is
wrong. If this document seems wrong, comment on issue #15 — do not silently
change numbers.

Everything is in **millimeters**. Material is uniform **3.175mm (1/8") plywood**
(`T` below). Laser kerf is handled by Boxes.py's `burn` parameter (0.08mm
starting value — calibrate with a test cut before the real run). Finger holes
and slots are widened by `FINGER_PLAY` (0.1mm) so joints still assemble when
the ply runs thick (nominal 3.175 stock commonly measures 3.0–3.4); this makes
edge-adjacent hole rows break through their part edge by ≤ play/2, which is
sub-kerf and hidden inside joints.

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
  cuts both lines and the mouth opens (one 3.975mm segment double-cut;
  negligible). Leaves a 5.0mm rail above (Z 122 → 127) cantilevered from
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
- ~~No retention along the travel axis~~ **Superseded by "Retention" below
  (issue #20):** each side wall carries a cantilever spring detent whose nub
  pops through a matching notch cut into the lid's side edges when closed,
  holding the lid seated at a 90° front-down tip. The slide is still
  free-running otherwise — this is a detent, not a lock.

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
  exclusive. ~~There is no out-retention~~ **Superseded by "Retention"
  below (issue #20):** each of the two SIDE panels (not the faceplate — see
  the red-team note below) carries a cantilever spring-detent flexure near
  its front (faceplate) end, whose nub snaps into a catch hole cut through
  the bottom panel (bottom drawer) or shelf (top drawer) at the closed
  position, holding the drawer seated.
- Lateral play in the bay is ~4.9mm/side by design — the drawer is guided by
  its opening, not the bay walls; max skew ≈ 1.3°, acceptable for a first cut.

Faceplate (6th piece), glued to the body front:

- Blank: **150.9 (Y) × 53.5 (Z)** = opening − 2 × 0.75 reveal; covers the body
  cross-section exactly in height, +0.95/side in width; flush with the rear
  face when closed (faceplate thickness T fills the rear wall plane). Plain
  edges (glued, not finger-jointed) — **this is the exact original (v1)
  blank.** Issue #20's first iteration briefly gave the faceplate a
  retention nub of its own (a wider drawn/cut blank); red-team review found
  that mechanism geometrically impossible (a Y-Z plate can't cam against
  X-axis drawer travel — see "Retention" below) and it was removed, so the
  faceplate carries **no retention feature at all**. Retention for the whole
  drawer now lives entirely in the SIDE panels (above).
- **Grip slot**: closed rounded slot **30 × 15, r = 7.5**, cut through BOTH
  the faceplate and the body's front wall, aligned, so a finger hooks through
  into the drawer. Centered in Y; slot top edge 8.0 below the part's top edge
  (slot spans 30.5 → 45.5 of the 53.5 height). A closed slot (not a top-edge
  notch) keeps the top edge stiff and the opening reveal continuous.
- Registration: red-engraved outline of the body cross-section on the
  faceplate's back for glue-up alignment.

## Clearance summary (what the tests enforce)

| Interface | Clearance | Rule |
|---|---|---|
| Drawer body ↔ opening width | 3.4 total | ≥ 1.5 per SPEC |
| Drawer body ↔ opening height | 1.5 | ≥ 1.5 |
| Drawer body ↔ slot height | 5.24 | ≥ 1.5 |
| Drawer body ↔ bay length | ~1.1 | > 0 (not a sliding fit) |
| Lid width ↔ slot span | 1.5 total | ≥ 1.5 |
| Lid thickness ↔ slot height | 0.8 | = 0.8 (documented deviation) |
| Faceplate ↔ opening | 0.75/side | reveal 0.5–1.0 |
| Webs in rear wall | 3.175 / 3.7375 | ≥ 3.0 |
| Lid detent nub ↔ slot ceiling | ≥ 1.0 | nub top (Z 119.525) clears slot top (122.0) |
| Drawer detent nub ↔ opening vertical play | ≥ 0.7 | engage (2.2) − opening play (1.5) |
| Catch-hole engaged X-slop | ≤ 0.8 | hole length (10.92) − nub base width (10.12) |

## Retention (iteration 3, issue #20 red-team)

Two in-plane laser-cut cantilever spring detents. All geometry is driven
from `src/faxbox/config.py` constants (see that file's "Retention
(iteration 3, issue #20 red-team)" section) via shared point-generation
helpers in `src/faxbox/detent.py` — no magic numbers in the generators.

**Why iteration 2's drawer mechanism was replaced.** Iteration 2 put a
retention nub on the faceplate (a Y-Z plate — its plane contains Y and Z,
not X). The drawer travels along X, *normal* to that plate. A laser-cut
edge is square through the material's thickness, so a "ramp" drawn on a Y-Z
part's boundary is a ramp in the Y-Z plane — it is never swept by motion
along X. The faceplate nub could only ever meet the rear-wall opening frame
as a **square 0.45mm interference** (a jam, not a cam) — there was no
physical path for it to cam past anything on insertion. This was caught by
red-team review before cutting; the fix is a different mechanism entirely,
not a retuned version of the same one. Mechanism B below replaces it,
cut into the drawer's SIDE walls (an X-Z plane — it contains the travel
axis X *and* the deflection axis Z, so its ramps genuinely cam against
motion along X).

**Shared cantilever proportions**: beam cross-section width 2.5mm in the
flex direction (`DETENT_BEAM_WIDTH`), root fillet ≥1.0mm, 30° ramp angle
(`DETENT_RAMP_DEG`), 1.0mm release-cut width to fully part the beam's free
tip from the surrounding material (`DETENT_SEVER_WIDTH`), and
`DETENT_SEVER_CLEARANCE` = 1.5mm kept between a nub's own (ramped) base
edge and its release/sever cut, so the sever cut cannot undercut the nub's
own base and leave it bridged to the fixed material on its outward side
(this was verified against the ACTUAL drawn geometry, not assumed — see
the "nub bridging" note below). Beam length differs per mechanism (see
each below), driven by the strain formula, not a shared constant.

**Clearance cavity depth is now PER-MECHANISM, not shared** (FIX, issue #20
pass-3 red-team F3): a single shared `DETENT_CLEARANCE` (2.5mm) used to size
the clearance behind/above BOTH beams, sized only to each mechanism's own
nub engagement depth. That undercounts how far the beam's FREE TIP actually
rises, because in both mechanisms the nub sits near, but not exactly at,
the beam's severed free end (`DETENT_SEVER_CLEARANCE` keeps a gap between
the nub's own base and the sever cut) — the tip therefore overhangs past
the nub's own load point, and by ordinary cantilever beam theory a point
further past a load rises MORE than the load point itself:

**tip rise = engage · (1 + 3·overhang / (2·span))**

(`overhang` = distance from the nub's load point to the beam's true
severed free tip; `span` = root-to-nub distance; see `config._tip_rise`).
Each mechanism's cavity must be **≥ its own tip rise + 0.5mm real margin**,
computed via this formula, not assumed equal to the nub's own engagement:

- **Mechanism A (lid, side wall)**: overhang ≈4.85mm, span = 22.0mm ⇒ tip
  rise ≈2.00mm ⇒ `LID_DETENT_CAVITY` = 2.00 + 0.5 = **2.5mm** — unchanged
  from the old shared value. This mechanism's proportions happened to keep
  the tip rise within the old cavity's margin; the formula makes that
  margin explicit instead of accidental.
- **Mechanism B (drawer, side wall)**: overhang ≈6.06mm, span = 26.0mm ⇒
  tip rise ≈2.97mm, which EXCEEDS the old shared 2.5mm cavity — the beam
  would bind against the cavity's far wall at ≈1.85mm of nub lift, short of
  the designed 2.2mm engagement. `DRAWER_DETENT_CAVITY` = 2.97 + 0.5 =
  **≈3.47mm** fixes this. Checked against the drawer side's own 53.5mm
  total height (DESIGN.md #9): the deeper cavity's far edge sits well
  short of the panel's own top edge and every other feature, with no web
  thinner than `MIN_WEB` (3.0mm) introduced — confirmed both by the
  measured constants and by rendering `drawer.svg`.

**Burn (FIX3, red-team)**: every nub/notch/detour shape is drawn
BURN-compensated (see `faxbox.detent`'s module docstring for the exact
model), matching how the rest of the box already compensates finger joints
and holes for kerf — pre-iteration-3, these shapes were burn-*neutral*
while their own release cuts (plain `rectangularHole` calls) WERE
compensated, so drawn interference silently drifted from as-cut
interference as BURN changed from its calibrated starting value. The one
exception, by explicit project rule, is `calibration.py`'s kerf-test
square, which must stay burn-neutral — it measures the real kerf, it
doesn't compensate for it. **If BURN changes after calibration, the
retention coupon (below) must be re-cut too**, for the same reason the
kerf coupon itself must be — see README's cut-day flow.

### A. Side-wall lid detent

Kinematics unchanged from iteration 2 (this mechanism's cam action was
always sound — it's an X-Z part); only the strain (below) was refit.

- Cut into EACH side wall, just below the lid slot floor (Z = 118.025): a
  cantilever beam running parallel to X, 2.5mm wide, with a clearance
  cavity below it and a 1.0mm severing slot at its free (tip) end — see
  `faxbox.detent.release_cut_rects`. The root end (deeper into the wall) is
  left solid.
- **Nub at the beam's free end (FIX2, red-team)**: iteration 2 put the nub
  MID-BEAM at X=20 with the beam spanning 11→29 — the nub's own ramp meant
  the actual strain-bearing span (root to nub, 29−20=9mm) was barely half
  the drawn beam length, giving ε ≈ 6.9% at the root — well above
  plywood's ~1.5–2% crack threshold (SpringFit, UIST 2019). The nub
  position (`LID_DETENT_X` = 20.0, unchanged — the lid notch position is
  unaffected) now sits `DETENT_SEVER_CLEARANCE` + half the nub's own base
  width outward of the release cut's tip (`LID_DETENT_TIP_X` ≈ 14.65),
  clear enough that the sever cut can't undercut the nub's own base, and
  `LID_DETENT_ROOT_X` = `LID_DETENT_X` + `LID_DETENT_NUB_TO_ROOT_SPAN`
  (22.0) = 42.0 — nearly the full beam length now bears load.
  **ε = 3·w·δ/(2·L²)** with w = `DETENT_BEAM_WIDTH` (2.5), δ =
  `LID_DETENT_ENGAGE` (1.5), L = 22.0 (root-to-nub span) → **ε ≈ 1.16%**,
  a real margin below the crack threshold.
- The nub is a ramped bump built into the lid-slot hole's own bottom
  boundary (`faxbox.detent.lid_slot_with_nub_points`), rising from the slot
  floor (118.025) to `LID_DETENT_NUB_TOP_Z` = 119.525 (1.5mm rise —
  exceeds the 0.8mm lid vertical play so the nub stays engaged when the box
  tips and the lid shifts within its play). Top clears the 122.0 slot
  ceiling by 2.475mm. Ramped on both X-faces at 30°, with a 2.5mm flat top;
  base width ≈7.7mm (`LID_DETENT_NUB_BASE_WIDTH`).
- **Mating notch in the lid's side edges** (both long edges, one per wall):
  an edge-open recess (`faxbox.detent.notch_points`) at lid-local X =
  `LID_NOTCH_X` = 19.625 (= `LID_DETENT_X` − `LID_CLOSED_FRONT_X`, where
  `LID_CLOSED_FRONT_X` = 0.375 is the closed lid's front-edge offset from
  the box's front face — DESIGN.md #8). Width ≈8.7mm (nub base + 1mm),
  depth `LID_NOTCH_DEPTH` = **3.5mm** (bumped from 3.0mm — FIX3: once the
  notch is drawn burn-shrunk so its AS-CUT depth matches nominal instead of
  drifting with BURN, 3.0 left only ~0.075mm of real margin over the
  lid-slot-engagement + 0.5mm requirement — less than BURN itself could
  erase; 3.5 restores a real margin), mouth corners eased by a 1.0mm
  chamfer. When closed, the nub pops up through the notch: positive
  retention at a 90° front-down tip.
- Both walls are mirror images (drawn exterior-face-up, left wall mirrored
  in local X) — the nub, release cut, and lid-slot-with-nub polygon are all
  mirrored the same way the plain slot already was, landing both walls'
  nubs at the same real box X.

### B. Drawer side-wall flexure (replaces iteration 2's faceplate detent)

- Cut into EACH of the drawer's two SIDE panels (Left Side, Right Side —
  both, per drawer; the two drawers are identical so this applies to both
  physical drawers), near the FRONT (faceplate) end: a cantilever beam
  running parallel to X (the drawer's travel axis), 2.5mm wide, with a
  clearance cavity above it (into the panel's solid material) and a 1.0mm
  severing slot at its free (tip) end. The nub protrudes DOWN below the
  panel's own bottom edge.
- **Assembly convention (new, this project's own choice)**: since both ends
  of a drawer side panel finger-joint identically to the Front and Back
  panels (nothing else distinguishes them), this design defines
  drawer-local x=0 as the end assembled against the **Front** panel (the
  faceplate end). Both side panels must be installed with their flexure end
  toward Front, not Back — flagged here since pre-iteration-3 parts had no
  such constraint (either end was interchangeable).
- **Nub depth**: `DRAWER_DETENT_ENGAGE` = **2.2mm**, defined as protrusion
  below the drawer's TRUE exterior bottom (where the neighboring finger
  tabs reach) — this must exceed the drawer's own 1.5mm opening vertical
  clearance (`OPENING_HEIGHT` − `DRAWER_BODY["height"]`) by a real margin so
  the nub stays engaged even when the drawer is lifted to the top of that
  clearance band; 2.2 − 1.5 = **0.7mm** headroom. Drawn depth from the
  panel's own local y=0 (the flexure zone's un-tabbed baseline, which sits
  shallower than the tab reach by T since there's no tab there at all) is
  `T + DRAWER_DETENT_ENGAGE` ≈ 5.375mm.
- **Beam sizing by strain**: ε = 3·w·δ/(2·L²), w = `DETENT_BEAM_WIDTH`
  (2.5), δ = `DRAWER_DETENT_ENGAGE` (2.2). Solving ε ≤ 1.5% for L gives
  L ≥ ~23.45mm; `DRAWER_DETENT_NUB_TO_ROOT_SPAN` = **26.0mm** gives
  **ε ≈ 1.22%**, a real margin below the crack threshold. Nub position
  `DRAWER_DETENT_NUB_X` = 24.0 (drawer-local X, front end), release-cut tip
  `DRAWER_DETENT_TIP_X` ≈ 17.44 (nub half-base + `DETENT_SEVER_CLEARANCE`
  outward of the nub, same anti-bridging margin as mechanism A), root
  `DRAWER_DETENT_ROOT_X` = 50.0 — the sever cut sits ≥15mm clear of the
  front finger joints (17.44mm measured).
- **Bottom-edge construction**: the side panel's bottom edge is normally
  fully finger-jointed to the drawer's own Bottom panel along its whole
  length; a Boxes.py finger-joint edge can't locally express the nub's
  protrusion (the same limitation the removed faceplate detent hit), so a
  short PLAIN zone (`DRAWER_DETENT_PLAIN_LO` ≈ 9.44 → `..._PLAIN_HI` =
  52.0) replaces the finger joint there via a 3-segment CompoundEdge
  (finger / purpose-built nub edge / finger — see
  `generate_drawers.py`'s `_DrawerFlexureNubEdge`). The Bottom panel's own
  matching finger-hole row is split to skip the same X-range, so there are
  no unplugged holes. (`PLAIN_LO` moved from ≈15.44 to ≈9.44 as part of the
  bottom-panel clearance slot fix below — the slot is wider than the
  beam's own tip-to-root span, so it, not the beam, now sets this bound.)
- **Bottom-panel clearance slot** (FIX, issue #20 pass-3 red-team F2,
  CRITICAL): the drawer's own Bottom panel sits flush across the drawer's
  FULL exterior footprint (DESIGN.md #9), directly beneath the flexure
  zone — before this fix, that panel was solid there, but the nub needs to
  reach `DRAWER_DETENT_ENGAGE` (2.2mm) PAST it to do anything useful (skipping
  the finger-hole ROW there, as described above, only removes the row's
  individual tab-holes; it does nothing to open the panel's own solid
  field to the nub's swept path). At the nub's WIDEST cross-section — the
  wall plane, where the nub is still flush with the wall's bulk material,
  `NUB_WIDTH_AT_WALL_PLANE` ≈ 21.1mm nominal (≈21.4mm as-cut with BURN) —
  the panel had nowhere for the nub to go. Fix: one rectangular clearance
  hole per side wall, cut through the drawer's Bottom panel
  (`generate_drawers.py`'s `_build_bottom`), sized to:
  - X-length (`DRAWER_BOTTOM_SLOT_X_LENGTH` ≈ 23.1mm): `NUB_WIDTH_AT_WALL_PLANE`
    + 1mm margin on each end, centered on the nub (box X = T +
    `DRAWER_DETENT_NUB_X`).
  - Y-span (`DRAWER_BOTTOM_SLOT_Y_SPAN` ≈ 3.675mm): the wall's own seat
    zone (0 → T) + 0.5mm inboard margin — starts exactly at the panel's
    true edge (nothing is lost outboard of the wall's own footprint) and
    extends 0.5mm inboard for real clearance.
  Because this slot is WIDER than the flexure beam's own tip-to-root span,
  `DRAWER_DETENT_PLAIN_LO`/`..._PLAIN_HI` (above) are now sized to whichever
  requirement is wider on each side — the slot's own X-extent + 3mm margin
  (so the slot doesn't clip the finger-hole row's own teeth where it
  resumes, the same principle `CATCH_HOLE_PLAIN_MARGIN` applies to the
  catch holes below), or the beam's tip-to-root span + 2mm, whichever is
  wider. Hidden under the drawer once assembled (cosmetic underside
  cutout, same visibility caveat as the catch holes below).
- **Kinematics**: on insertion, the drawer (faceplate trailing) has its nub
  cam UP over the rear-wall opening's own sill web (the T=3.175mm-thick
  rear-wall material below the bottom opening / above the top opening's
  shelf-supported web — DESIGN.md #4) as it crosses the opening's own
  X-span near the end of the insertion travel, then rides deflected along
  the bay floor (bottom drawer) or shelf (top drawer) for the remaining
  travel, dropping into a **catch hole** cut through that panel at the
  closed position.
- **Catch holes** (bottom panel for the bottom drawer, shelf for the top
  drawer — 2 holes per panel, one per side wall):
  - X position: `CATCH_HOLE_X` = `DRAWER_FRONT_INNER_FACE_CLOSED_X` −
    `DRAWER_DETENT_NUB_X`, where `DRAWER_FRONT_INNER_FACE_CLOSED_X` =
    `BAY_X1` − `DRAWER_BAY_GAP` (the 0.475mm closed-position reveal,
    DESIGN.md #9) − T (faceplate/Front panel thickness) ≈ 297.975 — i.e.
    derived from the rear wall plane, the closed-position reveal, and the
    drawer body length, per the fix's own instruction, landing at
    `CATCH_HOLE_X` ≈ 273.975 (≈24mm in from the rear wall's interior face —
    matches the drawer's remaining travel after the nub clears the sill).
  - X-length: `CATCH_HOLE_X_LENGTH` = `NUB_WIDTH_AT_FLOOR_PLANE` + 0.8mm,
    keeping engaged X-slop ≤ 0.8mm nominal (≈0.5mm real engaged slop, per
    the independent-datum registration test below). **Nub width naming
    fix (FIX, issue #20 pass-3 red-team F4)**: the taper is linear
    (constant `DETENT_RAMP_DEG`), so its half-width simply grows with
    depth traveled back up the ramp from the narrow tip — this means the
    nub has a DIFFERENT width at every Z/Y level along its length, and the
    previous revision's `DRAWER_DETENT_NUB_BASE_WIDTH` (≈10.12) was
    measured at the FLOOR plane (`DRAWER_DETENT_ENGAGE` above the tip —
    the cross-section that actually threads through this catch hole) while
    being *named* as if it were the nub's "base" (i.e. its widest point, at
    the wall plane, ≈21.1mm nominal / ≈21.4mm as-cut — see the
    bottom-panel clearance slot, above, which DOES need that wider value).
    Renamed to two explicit, correctly-scoped constants:
    `NUB_WIDTH_AT_FLOOR_PLANE` (≈10.12, unchanged value — used here, for
    catch-hole sizing) and `NUB_WIDTH_AT_WALL_PLANE` (≈21.1, new — used for
    the bottom-panel clearance slot).
  - Y-width: `CATCH_HOLE_Y_WIDTH` = T (side thickness) + 2×`DRAWER_LATERAL_GAP`
    (the drawer's own ~4.9mm/side bay float) + 1mm margin ≈ 13.925mm, so the
    nub can't miss the hole even at worst-case drawer skew.
  - **Flagged tension**: sizing the hole to the FULL bay-wide lateral float
    (as specified) puts its edge within ~0.5mm of the bottom panel's own
    finger-jointed edge (the panel's usable Y-range near either bay wall is
    inherently only ~4.9mm, since the drawer already fills all but ~9.75mm
    of the interior width) — short of the general "≥3mm from any panel
    edge" guidance elsewhere in this fix. The mandated Y-span requirement
    (also this fix's own instruction, and the one the mutation-gate test
    enforces) cannot be satisfied simultaneously with 3mm edge clearance
    given the drawer's actual fit; the Y-span requirement was kept as
    specified since narrowing it risks the nub missing the hole at
    worst-case skew, which is the failure mode this hole exists to prevent.
  - Visible from the box underside when the drawer is out (bottom panel
    only) — cosmetic, accepted.
  - **Registration test (FIX, issue #20 pass-3 red-team F4, CRITICAL)**:
    prior to this fix, no test verified the catch hole and the nub actually
    land at the same box X end-to-end — a red-team mutation
    (`CATCH_HOLE_X += 5.0`) stayed green against every existing test,
    since none of them independently recomputed one side's expected
    position from the other. `tests/test_retention.py::
    test_catch_hole_registers_with_nub_via_independent_datums` now
    measures the drawer's own Bottom-panel clearance slot (above, F2 —
    a plain, un-jointed hole with zero tab-position ambiguity, unlike the
    jointed side panel the nub itself is cut into) as an independent proxy
    for the nub's true position, combines it with the rear-wall plane
    (`BAY_X1`) and a MEASURED (not config-echoed) drawer body length, and
    asserts the shell's catch hole X-span contains the computed nub X-span
    with ≤1.0mm total slop — parsed entirely from the generated SVGs, not
    by comparing config constants to themselves.
- Grip slot (Y-centered) and the flexure zone (near each side panel's front
  end) never intersect.

### Nub-bridging note (why `DETENT_SEVER_CLEARANCE` exists)

A nub whose ramped base straddles its own release/sever cut is NOT
fully freed by that cut: the sever cut only removes material in the Z-band
BELOW the nub's own base level (mechanism A) / X-band behind the flexure
(mechanism B) — the nub's own ramped material, sitting ABOVE that band,
remains a single connected shape that bridges from the fixed (outward)
side to the free (beam) side right at its own base, regardless of the
sever cut's position, UNLESS the sever cut sits entirely outward of the
nub's own base footprint. This was verified empirically against the
pre-fix wall geometry (whose nub-to-sever gap happened to be large enough,
by construction of the old mid-beam nub position, to avoid the problem by
accident) before being generalized into the explicit
`DETENT_SEVER_CLEARANCE` constant both mechanisms now use.

### Grain caveat

Plywood cantilevers are ~3× weaker bending across the face-veneer grain than
with it (SpringFit, UIST 2019). `layout.py`'s shelf packer never rotates
parts — each piece keeps the same X/Y orientation from its source SVG onto
the sheet — and this project assumes **grain runs along the sheet's long
(X) axis** (README's cut-day guidance: "Orient sheets with the face grain
running along the sheet's long axis"). Under that assumption, checked
against the ACTUAL `layout.py`/generator orientation (not assumed):

- **Mechanism A (side wall)** is grain-favorable: the wall's long axis
  (298.45mm, local X) maps directly to the sheet's long axis with no
  rotation, and the beam's length (also along X) runs *with* the grain —
  the bending fibers at the beam's root are parallel to grain.
- **Mechanism B (drawer side wall)** is ALSO grain-favorable, unlike the
  removed faceplate mechanism it replaces: the drawer side panel's long
  axis (`BODY_INTERIOR_LENGTH` ≈ 212mm, local X, verified against the
  generated `drawer.svg` — the "Left Side"/"Right Side" pieces measure
  ~218.8mm wide × ~53–56mm tall, i.e. drawn WIDE, matching the sheet's long
  axis with no rotation) maps to the sheet's long axis the same way, and
  the beam (also along X) again runs *with* the grain. This is a genuine
  improvement over the removed mechanism (whose faceplate-mounted beam ran
  along Z, across grain, the weaker direction).

This is exactly why the retention coupon (`faxbox.calibration.RetentionCoupon`,
`output/retention_coupon.svg`) exists regardless: cut every flexure sample on
real stock oriented the same way the real parts will be, and confirm the
snap force is adequate (not brittle, not too stiff) before committing to
the real parts. If either mechanism proves too weak in practice, or the
coupon can't be tuned to a good snap, the documented fallback is **magnets**
(6mm discs in through-holes, 0.3–0.5mm undersize press-fit + CA glue) rather
than forcing a larger interference that risks a snapped-off nub.

### Failure modes (honest, not hidden)

- **Lid detent (mechanism A) snapped flexure**: a fractured tongue drops a
  loose chunk of plywood into the lid's own slot channel — a jam risk.
  Never force the lid if it resists sliding; remove it fully (slide back
  out toward the front) and check the slot channel for debris before
  reinserting, rather than pushing harder.
- **Drawer flexure (mechanism B) fracture**: the affected drawer loses its
  detent (no more positive "seated" feel) but keeps sliding freely — it's a
  retention failure, not a jam, since the flexure zone sits below the
  drawer's own floor/shelf, not in its direct travel path. Safe to keep
  using the drawer; the fallback (magnets, above) is the recorded fix if it
  matters.

## Known deltas from SPEC.md targets

- Drawer external length 221.2 (body 218 + faceplate T) vs SPEC "9.0 external":
  the difference is consumed by the front wall, divider, and rear wall within
  the fixed 12" envelope. SPEC marks drawer dims "to fit" — envelope wins.
- Drawer external width 149.0 vs SPEC "approx 6.3" (160)": constrained by the
  rear-wall opening needing ≥T structural webs at the corners plus pass-through
  clearance. SPEC marks this "to fit".
