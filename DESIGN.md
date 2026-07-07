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
- ~~No retention along the travel axis~~ **Superseded by "Retention (iteration
  2)" below (issue #20):** each side wall now carries a cantilever spring
  detent whose nub pops through a matching notch cut into the lid's side
  edges when closed, holding the lid seated at a 90° front-down tip. The
  slide is still free-running otherwise — this is a detent, not a lock.

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
  exclusive. ~~There is no out-retention~~ **Superseded by "Retention
  (iteration 2)" below (issue #20):** each faceplate now carries a cantilever
  spring detent per Y edge whose nub snaps behind the rear-wall opening's
  side edge on close, holding the drawer seated at a 90° rear-down tip.
- Lateral play in the bay is ~4.9mm/side by design — the drawer is guided by
  its opening, not the bay walls; max skew ≈ 1.3°, acceptable for a first cut.

Faceplate (6th piece), glued to the body front:

- Blank: **150.9 (Y) × 53.5 (Z)** = opening − 2 × 0.75 reveal; covers the body
  cross-section exactly in height, +0.95/side in width; flush with the rear
  face when closed (faceplate thickness T fills the rear wall plane). As of
  iteration 2 (issue #20), the DRAWN/cut blank is wider than this: see
  "Retention (iteration 2)" below — the retention nubs make the true drawn
  width 150.9 + 2×DRAWER_DETENT_PROTRUDE (153.3), protruding past this
  nominal footprint by design.
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
| Faceplate nub ↔ opening (per side) | 0.45 interference | protrusion (1.2) − reveal (0.75) |

## Retention (iteration 2, issue #20)

Two in-plane laser-cut cantilever spring detents, adapted from Boxes.py's own
precedents (`boxes/edges.py` `SlideOnLidSettings`/`LidRight`: spring length
`min(6t, ...)`, 30° tip ramp, 0.4t catch depth; `boxes/generators/
dinrailbox.py`: a cantilever tongue with a nub cut into a panel). This
project adapts their *proportions*, not their play values — those precedents
assume ~0.3mm clearance; this design's slide clearances (`SLIDE_CLEARANCE` =
1.5, `LID_SLOT_VERTICAL_CLEARANCE` = 0.8) are deliberately looser, so the
nub/notch interference has to do more work to stay engaged through that play.
All new geometry is driven from `src/faxbox/config.py` constants (see that
file's "Retention (iteration 2, issue #20)" section) via shared point-
generation helpers in `src/faxbox/detent.py` — no magic numbers in the
generators.

**Shared cantilever proportions** (both mechanisms): beam length 18.0mm,
beam cross-section width 2.5mm in the flex direction, root fillet ≥1.0mm,
≥2.5mm clearance behind/below the beam so it can deflect its engagement
depth without bottoming out, 30° ramp angle (matching `LidRight`'s barb
angle), 1.0mm release-cut width to fully part the beam's free tip from the
surrounding material. All shapes are drawn **burn-neutral** (raw ctx path,
no Boxes.py burn compensation) — a deliberate simplification, since the two
interference values below are explicitly meant to be tuned against the
retention coupon (see `src/faxbox/calibration.py`'s `RetentionCoupon`)
before cutting real parts; kerf's ~0.1–0.2mm effect is small next to the
1.2–1.5mm interference margins.

### A. Side-wall lid detent

- Cut into EACH side wall, just below the lid slot floor (Z = 118.025): a
  cantilever beam running parallel to X, Z-span 115.525 → 118.025 (2.5mm
  wide), with a clearance cavity below it (Z 113.025 → 115.525) and a 1.0mm
  severing slot at its free (tip) end — see `faxbox.detent.release_cut_rects`.
  The root end (deeper into the wall) is left solid.
- Beam spans box X 11.0 → 29.0 (`LID_DETENT_TIP_X` → `LID_DETENT_ROOT_X`,
  18mm, centered on `LID_DETENT_X` = 20.0) — clear of the front-edge finger
  joints (a vertical edge feature, unrelated to this X range) and ≥40mm from
  the divider hole line (79.375–82.55).
- The nub is a ramped bump built into the lid-slot hole's own bottom
  boundary (`faxbox.detent.lid_slot_with_nub_points`), centered at
  `LID_DETENT_X`, rising from the slot floor (118.025) to `LID_DETENT_NUB_TOP_Z`
  = 119.525 (1.5mm rise — exceeds the 0.8mm lid vertical play so the nub
  stays engaged when the box tips and the lid shifts within its play). Top
  clears the 122.0 slot ceiling by 2.475mm. Ramped on both X-faces at 30°,
  with a 2.5mm flat top (a flat land rather than a knife edge, since a bare
  wedge would concentrate stress in cross-grain plywood — see the Grain
  caveat below); base width ≈7.7mm (`LID_DETENT_NUB_BASE_WIDTH`).
- **Mating notch in the lid's side edges** (both long edges, one per wall):
  an edge-open recess (`faxbox.detent.notch_points`) at lid-local X =
  `LID_NOTCH_X` = 19.625 (= `LID_DETENT_X` − `LID_CLOSED_FRONT_X`, where
  `LID_CLOSED_FRONT_X` = 0.375 is the closed lid's front-edge offset from
  the box's front face — DESIGN.md #8). Width ≈8.7mm (nub base + 1mm), depth
  3.0mm (exceeds the lid's 2.425mm slot engagement with margin), mouth
  corners eased by a 1.0mm chamfer. When closed, the nub pops up through the
  notch: positive retention at a 90° front-down tip.
- Both walls are mirror images (per the existing convention: drawn
  exterior-face-up, left wall mirrored in local X) — the nub, release cut,
  and lid-slot-with-nub polygon are all mirrored the same way the plain slot
  already was, landing both walls' nubs at the same real box X.

### B. Drawer faceplate detent

- Cut into EACH faceplate, near BOTH Y side edges: a vertical cantilever
  (along Z), 18mm long, Z-span 17.75 → 35.75 (`DRAWER_DETENT_ROOT_Z` →
  `DRAWER_DETENT_TIP_Z`, centered on `DRAWER_DETENT_Z` = 26.75, the
  faceplate's mid-height), 2.5mm wide in the flex direction, with the same
  clearance-cavity + severing-slot release cut as mechanism A (transposed:
  "along" is Z, "across" is the faceplate's drawn-x).
- The nub protrudes `DRAWER_DETENT_PROTRUDE` = 1.2mm beyond the faceplate's
  nominal edge (0.45mm interference past the 0.75mm `FACEPLATE_REVEAL` when
  centered in its opening), ramped at 30° on both Y-faces with a 2.5mm flat
  top, base width ≈6.66mm (`DRAWER_DETENT_NUB_BASE_WIDTH`).
- Because this nub protrudes past the faceplate's own outer edge (there is
  no pre-existing void to poke into, unlike mechanism A's lid slot), the
  faceplate's outer boundary is hand-drawn (`faxbox.detent.edge_nub_detour`)
  instead of Boxes.py's automatic straight "e" edges, which can't express a
  local protrusion. This makes the faceplate's true drawn/measured footprint
  `FACEPLATE_DRAWN_WIDTH` = 150.9 + 2×1.2 = 153.3mm rather than the plain
  150.9mm nominal — **flagged deviation**: this legitimately changed
  `tests/test_svg_geometry.py::test_faceplate_blank_size`'s measured
  quantity (see that test's comment) and, since the faceplate no longer
  calls `rectangularWall(..., "eeee", ...)` at all,
  `test_edge_polarity_literals_present`'s literal count. Both were the
  minimal, unavoidable, documented consequence of adding a REAL protruding
  interference feature — there is no way to add retention here without the
  physical part becoming physically bigger at the nub, and svg_utils's
  bbox-based piece detection can't distinguish that from "a bigger nominal
  blank" for the same connected outer path.
- Grip slot (Y-centered, ~60mm from either edge) and the nub (near each Y
  edge, Z-centered at mid-height) never intersect — their Y ranges are
  disjoint regardless of Z overlap.
- Snaps past the rear-wall opening's side edge on close (the opening's
  interior corner, 3.175mm deep per DESIGN.md #4); the grip-slot pull cams
  it back through on deliberate removal.

### Grain caveat

Plywood cantilevers are ~3× weaker bending across the face-veneer grain than
with it (SpringFit, UIST 2019). `layout.py`'s shelf packer never rotates
parts — each piece keeps the same X/Y orientation from its source SVG onto
the sheet — and this project assumes **grain runs along the sheet's long
(X) axis** (already README's cut-day guidance: "Orient sheets with the face
grain running along the sheet's long axis"). Under that assumption:

- **Mechanism A (side wall)** is grain-favorable: the wall's long axis
  (298.45mm, local X) maps directly to the sheet's long axis with no
  rotation, and the beam's length (also along X) runs *with* the grain —
  the bending fibers at the beam's root are parallel to grain.
- **Mechanism B (faceplate)** is grain-adverse: the faceplate's long axis
  (150.9mm, local X = box Y) also maps to the sheet's long axis, but the
  beam runs *perpendicular* to it (along Z) — the beam bends *across* grain,
  the weaker direction.

This is exactly why the retention coupon (`faxbox.calibration.RetentionCoupon`,
`output/retention_coupon.svg`) exists: cut both flexure samples on real stock
oriented the same way the real parts will be, and confirm the faceplate
sample's snap force is still adequate (not brittle) before committing to
DRAWER_DETENT_PROTRUDE = 1.2 on the real faceplates. If it proves too weak,
the documented fallback is magnets (issue #20's "Ideas to evaluate") rather
than forcing a larger interference that risks a snapped-off nub.

## Known deltas from SPEC.md targets

- Drawer external length 221.2 (body 218 + faceplate T) vs SPEC "9.0 external":
  the difference is consumed by the front wall, divider, and rear wall within
  the fixed 12" envelope. SPEC marks drawer dims "to fit" — envelope wins.
- Drawer external width 149.0 vs SPEC "approx 6.3" (160)": constrained by the
  rear-wall opening needing ≥T structural webs at the corners plus pass-through
  clearance. SPEC marks this "to fit".
