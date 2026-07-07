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
- No retention along the travel axis in v1: the divider stops rearward
  motion but nothing stops the lid sliding out the front when the box tips
  forward. **Iteration 2 (below) adds a pair of turn-buttons at the slot
  mouths to fix this** — see "Retention (iteration 2, magnets + turn-buttons)".

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
  divider's nearer Y-edge and the Back panel's nearer finger edge either way
  — the choice of +40 vs. −40 is arbitrary given that margin; +40 (toward
  increasing Y) was picked with no other reasoning.
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
  N52 or 3mm-thick discs instead, no geometry change. 2mm-thick magnets sit
  1.2mm recessed in 3.175mm ply (fine, glue backfills); 3mm sit near-flush.

### B. Lid retention — turn-buttons at the slot mouths

A rounded paddle ("stadium": rectangle + full semicircular end caps,
`~22mm × 9mm`, `TURN_BUTTON` in config.py) pivots on an M3 bolt through each
side wall, just below/behind its lid slot mouth, and turns up to physically
block the slot's own cut opening (caging the lid between the button and the
divider stop) or down to clear it.

- Pivot hole Ø3.2 (M3 clearance) on each side wall at box **X = 8.0, Z =
  112.0** — MIRRORED on the two walls, following `shell_generator.py`'s
  existing per-wall mirroring convention (same `mirror_point()` helper used
  for the lid slot/divider column/shelf rows).
  - X = 8.0 sits **inside the lid slot's own X-span** (`T .. LID_SLOT_X_END`
    = 3.175 → 79.375), not at its mouth — this is what lets the button block
    the lid by sweeping its paddle across the slot's actual cut opening
    (where the lid rides) without ever needing to overhang past the wall's
    front edge. Clears the front-edge finger-joint zone (box X `0 → T`) by
    `8.0 − T = 4.825mm` (≥ the required 3mm).
  - Z = 112.0 clears the slot floor (`LID_SLOT_BOTTOM = 118.025`) by
    6.025mm (≥ 3mm).
- Reach: the button's pivot sits `pivot_from_blunt_end = 4.5mm` (= half its
  own width, the blunt end's own rounded-cap center) from its blunt end, so
  pivot→tip reach = `22.0 − 4.5 = 17.5mm`. Required reach for the tip to
  clear the slot's top edge by ≥3mm when rotated to vertical:
  `(LID_SLOT_TOP + 3) − TURN_BUTTON_PIVOT_Z = (122.0 + 3) − 112.0 = 13.0mm`
  — the button's actual 17.5mm exceeds this.
  - **Flagged deviation, minimal and sound**: rotated fully vertical, the
    tip lands at box Z = 112 + 17.5 = 129.5 — 2.5mm *above* the wall's own
    top edge (127.0), into open air above the box, not merely "into the
    rail zone" as first anticipated. This is accepted as harmless (a turn-
    button knob poking slightly above the box when engaged is normal
    hardware behavior, and nothing structural sits there) rather than
    shortening the button, since a shorter button would cut the achieved
    margin close to the 13.0mm minimum with no benefit.
  - Rotated fully down (180° from vertical), the tip hangs at box Z = 112 −
    17.5 = 94.5, clear of the slot floor (118.025) by a wide margin and
    clear of every other wall feature at that X (the divider/shelf/top-panel
    hole rows all sit at box X ≥ 80, far from X ≈ 8).
- Engraving check: the pivot hole (box X=8, Z=112) is far from the "FAX
  MACHINE" engrave zone (centered X=152.4, Z=63.5, ~240×28) on the right
  wall — asserted in tests anyway per project policy.
- Hardware (documented, not laser-cut): 2× M3×12 button-head bolt, 2× M3
  nyloc nut, 4× M3 washer — nyloc tensioned so the button holds position by
  friction, not a spring.
- The 2 button pieces are cut from `output/hardware.svg`
  (`generate_hardware.py`), standalone like the calibration coupons — not
  nested into any `sheet_*.svg` (they're both symmetric about their own long
  axis, so one design serves both walls with no mirroring needed).

### C. Magnet press-fit coupon

`output/magnet_coupon.svg` (`calibration.py`'s `generate_magnet_coupon()`):
a row of 4 holes at **drawn** (burn-neutral, like the kerf square) diameters
5.5 / 5.65 / 5.8 / 5.95mm, each labeled in gray reference-only text. Press a
real 6mm disc magnet into each on scrap; whichever seats snugly (not loose,
not forced) sets `MAGNET_PRESS_FIT = MAGNET_DIA − <snuggest diameter>` in
config.py. Cut this coupon (and the kerf coupon) again any time `BURN`
changes — both coupons' readings depend on it.

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
| Magnet hole (drawer Back) ↔ its own edges | ≥ 20 | ≥ 3.0 |
| Magnet hole (divider) ↔ edges / shelf row | ≥ 23 | ≥ 8.0 (structural) |
| Turn-button pivot ↔ front joint zone | 4.825 | ≥ 3.0 |
| Turn-button pivot ↔ lid slot floor | 6.025 | ≥ 3.0 |
| Turn-button reach ↔ required reach | 17.5 vs. 13.0 | ≥ required |

## Known deltas from SPEC.md targets

- Drawer external length 221.2 (body 218 + faceplate T) vs SPEC "9.0 external":
  the difference is consumed by the front wall, divider, and rear wall within
  the fixed 12" envelope. SPEC marks drawer dims "to fit" — envelope wins.
- Drawer external width 149.0 vs SPEC "approx 6.3" (160)": constrained by the
  rear-wall opening needing ≥T structural webs at the corners plus pass-through
  clearance. SPEC marks this "to fit".
