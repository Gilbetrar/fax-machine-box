# DESIGN.md — Canonical Geometry

This document is the single source of truth for the Fax Machine Box geometry.
`src/faxbox/config.py` implements these numbers; `tests/test_assembly_fit.py`
enforces the relationships. If code disagrees with this document, the code is
wrong. If this document seems wrong, comment on issue #15 — do not silently
change numbers.

Everything is in **millimeters**. Material is uniform **3.175mm (1/8") plywood**
by default (`T` below; `FAXBOX_THICKNESS` overrides, see v2). Laser kerf is handled by Boxes.py's `burn` parameter (kerf / 2). The downloads are
built for three kerfs (diode 0.12, CO2 0.18, Ponoko 0.20 mm); the test-fit coupon says which
one to use. Finger holes
and slots are widened by `FINGER_PLAY` (0.1mm), giving a physical hole
through-dimension of `T + play` = 3.275mm at 3.175 stock. Real sheets vary, so
the downloads cover 2.8 to 3.5 mm in 0.1 mm steps, each with finger holes
T + 0.1 wide, and the coupon's thickness slots say which set to use.
This makes edge-adjacent hole rows
break through their part edge by ≤ play/2, which is sub-kerf and hidden
inside joints — **except the walls' top-panel hole row, whose slots open through
the visible top edge of the side and rear walls (see part #7 below).**

**Contents fit:** the SPEC envelope and compartment dimensions come from
Ben's fully functional cardboard prototype of this exact box (confirmed
2026-07-07) — the game's components are known to fit these interior volumes.
No separate component-dimension check is needed.

## Revision v2 (2026-10-10) — geometry fixes and thickness sets

This section is authoritative where it disagrees with the older text below
(the older sections are patched to match, but read this first).

| Item | Before | After | Why |
|---|---|---|---|
| Rear wall, strip under the lower drawer opening | bottom-panel hole row (Z −0.05→3.225) overlapped the opening floor (Z 3.175): the strip fell out as 11 chips | no bottom hole row on the rear wall; the bottom panel's rear edge is plain (`"feff"`) and is glued to the wall's inner face. Strip is one solid web of at least 3.0 mm (see round 2 below) | a T-tall strip cannot carry a hole row |
| Lid slot at the side-wall front edge | closed rectangular hole whose front line coincided with the blank's edge (0.0 mm web, doubled cut line) | the slot is an open notch in the outline (`SlotMouthEdge`) | no coincident lines |
| Divider hole row vs lid slot | top divider hole 0.5 mm below the slot floor (0.5 mm web) | rows stop at the slot floor (`DIVIDER_ROW_TOP_Z` = 115.125); nearest hole ≥ 6.3 mm below the slot | min web 1.5 mm |
| Lid rail above the slot | 5.0 mm | 7.5 mm | fragile cantilever |
| Lid slot vertical clearance | 0.8 mm | 1.2 mm | Ponoko panels warp |
| Front wall top / slot floor | 118.025 | 115.125 (= 127 − 7.5 − (T + 1.2)) | follows rail and clearance |
| Turn-button pivot Z | 110.0 | removed 2026-10-10 | the lid lock is gone, see "Decision: lid lock removed" |
| Divider orientation | fitted all four ways (upside down its magnet holes missed by 5.24 mm) | fits one way only (keyed, see "Divider keying") | foolproof assembly |
| Bolt | M3×12 | removed 2026-10-10 | no turn button, so no bolt, washers or nut |
| Material thickness | fixed 3.175 | `FAXBOX_THICKNESS` (2.8–3.5); external envelope fixed, interior follows T | real 3.2 mm birch measures 2.8–3.5 |

**Thickness parametrisation.** `config.T` reads `FAXBOX_THICKNESS` (default
3.175). The 12 × 6.5 × 5 in envelope stays fixed, so a thicker sheet makes
the interior smaller. Derived changes: drawer body length = `BAY_LENGTH` −
0.475 (bay gap, constant), drawer width = `OPENING_WIDTH` − 3.4, lid length =
divider face − 1.375 (78.0 at 3.175; see "Sliding lid"), rear-wall posts at least 3.0 mm wide
(`OPENING_WIDTH = INTERIOR_WIDTH − 2 * max(T, 3.0)`: 152.4 at 3.175, 153.5 at 2.8, so the drawer and faceplate are 0.4 mm narrower at 2.8). At
3.175 every number equals the v1 value. `FINGER_PLAY` is an absolute 0.1 mm
(`FINGER_PLAY_RELATIVE = FINGER_PLAY / T` is what Boxes.py receives), so
finger holes are T + 0.1 wide at every thickness; `BURN` (kerf per side) is
independent of T. Checked at 2.8, 3.0, 3.2 and 3.5 mm: one-piece parts,
minimum web ≥ 1.5 mm, all 3D checks (`tests/test_assembly3d.py` at 2.8 and
3.5).

**Divider keying.** The walls' divider hole rows stop at the lid-slot floor,
and the RIGHT wall's row is `DIVIDER_KEY_DROP` = 4T (one finger pitch)
shorter than the left wall's. The divider's side edges are compound edges
with matching lengths (fingers up to 115.125 on the left, 12.7 mm lower on
the right, plain above). Turned left-right, upside down, or both, its
fingers land on wall material (interference 64 mm³ left-right, 670 mm³
upside down; `tests/test_assembly3d.py::test_divider_fits_only_one_way`).
Unglued assembly therefore cannot go together wrong.

**Assembly order (verified in 3D, `faxbox.assembly3d.ASSEMBLY_STEPS`).**
Drawers first: back and front stand up, left side slides in (+Y), right side
(−Y), bottom from below (+Z), faceplate glued on. Box: top panel + shelf (carrying its two upper drawer guides) +
divider as one unit (the divider moves +X into the top panel and shelf);
right wall (moves −Y); rear wall (−X);
left wall (+Y); front wall (+X);
bottom panel from below (+Z), carrying its two lower drawer guides; lid from the front (+X); drawers
in from the rear (−X). Bottom-panel-first and "all captive parts into one
wall" orders are not possible. The order depends on the 0.05 mm
finger-hole breakouts at the part edges, which stay open. In the cut files each
breakout through an edge is merged into the outline, so each such slot is one notch
contour (before, a 0.07 to 0.15 mm hairline strip remained between the slot's cut and
the outline's cut).

**Minimum web.** Every part is checked in `tests/test_geometry_v2.py`: one
piece after a 0.16 / 0.2 / 0.3 mm kerf, no material web under 1.5 mm, and
only finger holes may break through an outline (by ≤ play/2 + 0.02 mm).

**Hardware.** Magnets only: 6 x 2 mm N52 neodymium discs, 4 needed, buy 6
(`HARDWARE` in config.py). The turn-button lid lock (M3 bolt, 2 washers, nyloc
nut) was removed on 2026-10-10.

**Paper.** Quarter letter, 4.25 × 5.5 in = 107.95 × 139.7 mm, stands on edge
with the 5.5 in side along Y. Compartment height under the lid = slot floor −
floor top = 111.95 mm (3.175), so headroom is 4.0 mm (3.35 at T = 3.5, 4.75 at
2.8); side room 19.05 mm total (9.5 per side; 18.4 at T = 3.5). Depth is the full 76.2 mm
(the divider sits 76.2 mm behind the front wall's inner face at every thickness),
about 760 sheets of 20 lb paper at the 10 sheets per mm the earlier 68 mm / 680
sheet figure used.

## Revision v2, round 2 (2026-10-10)

**Decision: lid lock removed.** Ben removed the turn-button lid lock on 2026-10-10.
The sliding lid is held by friction in its slots only. There is no button part
(its letter J now belongs to the drawer guides), no pivot hole in the front wall, and no M3 bolt, washers
or nyloc nut; the paper compartment no longer has a bolt intruding into it. The box
is 25 laser-cut pieces (8 shell, 12 drawer, 1 lid, 4 drawer guides). The only hardware to buy is magnets:
6 x 2 mm N52 neodymium discs, 4 needed, buy 6.

Geometry changes in this round:

- **Drawer magnet holes are centred** (`MAGNET_Y_OFFSET = 0`, was 40 mm). The
  drawer back is mirror-symmetric, so it cannot go in turned round. Both divider
  holes sit on the box centre line (box Y = 82.55).
- **Lower drawer height.** The lower drawer and its rear-wall opening sit at
  Z = max(T, 3.0) (`BOTTOM_DRAWER_Z0`) instead of exactly the bay floor, so the strip of
  rear wall under the opening is at least 3.0 mm (`MIN_WEB`) at every thickness. At T ≥ 3.0
  nothing changes. At T = 2.8 and 2.9 the lower drawer sits 0.2 and 0.1 mm above the bay
  floor (a tilt of about 0.05 degrees at 2.8; it rests on the strip at the faceplate end and
  on the bay floor at the far end).
- **Faceplate height.** The drawer faceplate is glued 0.75 mm ABOVE the drawer body's
  bottom edge (`FACEPLATE_Z_OFFSET`), so it is centred in the rear-wall opening with a
  0.75 mm reveal on all four sides (it was 0 at the bottom and 1.5 mm at the top). Its grip
  slot sits 8.75 mm below the plate's top edge (8.0 + 0.75, `FACEPLATE_SLOT_TOP_BELOW_EDGE`)
  so it lines up with the body front's slot. The red registration lines on the faceplate
  are only the body's left edge, right edge and top edge (0.95 mm in from the sides,
  0.75 mm below the top); there is no bottom line because the body's bottom edge sits
  0.75 mm below the plate. All lines stay at least 0.5 mm from every cut.
- **Corner loops.** Boxes.py writes a zero-length self-looping curve at inner corners when the
  kerf offset is non-zero; the cut files drop them (`_clean_piece` in `cutset.py`). Every cut
  contour is a valid simple closed shape.
- **Rear-wall posts.** The posts either side of a drawer opening are at least 3.0 mm wide
  (`MIN_WEB`) at every thickness: `OPENING_WIDTH = INTERIOR_WIDTH − 2 * max(T, 3.0)` (152.4 at
  T = 3.175, 153.5 at 2.8). Drawer width and faceplate width follow from the opening, so they
  are 0.4 mm narrower at T = 2.8.
- **Drawer guides (part J, 4 pieces).** See part #10.
- **Lid.** The lid is 78.0 mm long (was 79.0) and the two rear corners of its slot are
  rounded; see part #8.
- **Colours.** In every file cut = blue stroke `#0000FF`, the art = gray fill `#808080`
  (it was black `#000000`), and every single-line mark (part letters, joint numbers,
  faceplate glue-up lines, coupon ticks) = red stroke `#FF0000` (the labels were gray
  strokes). DXF layers: CUT, ENGRAVE (the art; set it to fill / raster), LABELS (all the
  red marks).
- **Finishing order.** Assemble first and finish after: wipe-on finish goes on the
  assembled box. Finger joints and glue faces stay free of finish until the glue has
  cured. Wax or paraffin on the lid slots and the drawer runners goes on last.

**Cut files.** `scripts/export_cutfiles.py` builds the sets described in README.md
("Downloads"): cut only, cut + labels, cut + engrave, a zero-kerf parts zip, and the
test-fit coupon, for every thickness 2.8 to 3.5 mm and kerf 0.12 / 0.18 / 0.20 mm.
Engraving is not kerf-offset and stays at least 0.35 mm from every cut. Joints are
numbered for assembly: 25 joints, each named by the lower part letter and a number
(for example C3) and engraved on both parts, except that parts with art carry no marks: a joint between a marked part and an art part is marked only on the marked part (match those by the part letter and the edge, or use the cut + labels files). The wall with one more hole in its
divider-hole column is the left wall (left/right counts 9/8 at 2.8 to 2.9 mm, 8/7 at
3.0 to 3.2, 7/6 at 3.3 to 3.5). Every flat part can be turned over, so a box built with
both side walls swapped and the divider turned left for right is a valid mirror-image
box with all the engraved faces inside.

## Decisions this design implements (Ben, 2026-07-07)

- Drawers open from the **rear** 6.5"×5" end face (SPEC "Rear Drawer Housing").
- ~~**"FAX MACHINE"** pixel-font engraving on the **right side wall** exterior.~~
  *(Superseded 2026-07-10, Ben: pixel text removed entirely — full-panel wall
  art from art/FACES.md replaces it; see part #2's engraving note.)*
- **Fixed top panel** over the drawer bay (not a removable lid).
- Sliding lid rides in **through-slots** cut through both side walls, open at
  the front edge; lid inserts from the front. Slot ends visible outside = accepted.
- Target service: NYC Resistor. Colours follow Ponoko's recommendation
  (https://help.ponoko.com/en/articles/2688732-how-should-i-specify-laser-actions ,
  checked 2026-10-10): blue stroke `#0000FF` = cut, red stroke `#FF0000` = line
  engrave, gray fill `#808080` = area engrave. Ponoko assigns a laser function to each
  line and fill colour at upload, so check the assignment there.

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
| Front wall top edge | 115.125 | = lid slot bottom; lid slides over it |
| Lid slot (through side walls) | 115.125 → 119.5 | height 4.375 = T + 1.2 |
| Side-wall rail above slot | 119.5 → 127.0 | 7.5 tall, spans slot X range |
| Divider top edge | 123.825 | = top panel underside |
| Top panel (over bay) | 123.825 → 127.0 | fixed, finger-jointed |
| Bay interior height | 3.175 → 123.825 | 120.65 |
| Bottom drawer slot | 3.175 → 61.9125 | clear height 58.7375 |
| Horizontal shelf | 61.9125 → 65.0875 | T thick |
| Top drawer slot | 65.0875 → 123.825 | clear height 58.7375 |

**Lid slot vertical clearance is 1.2mm (v2; was 0.8, SPEC says 1.5).** Deliberate
deviation: the SPEC's 1.5mm play is applied in the sliding *plane* (lid width,
drawer fits). Across the lid's thickness, 1.5mm would rattle; 1.2mm
absorbs plywood thickness variation and warp. Recorded here so tests can
assert 1.2 without someone "fixing" it back.

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
- **v2:** the rear edge is plain (no fingers). The rear wall has no
  bottom-panel hole row (see v2 table); the panel's rear edge butts the wall
  face and is glued. Front and side edges keep their fingers.

### 2. Side walls — 2× (left Y=0→3.175, right Y=161.925→165.1)

**The two side walls are mirror images, not identical parts** — the lid slot
sits at the front only, so a single cut pattern cannot serve both sides.
Convention: draw both with the **exterior face up**; the left wall's features
are the right wall's mirrored in X.

- Nominal: **298.45 (X) × 127.0 (Z)**, full height.
- Vertical edges: finger joints to front wall (only up to Z=115.125 on the
  front edge — above that is the lid slot mouth and rail end, plain) and rear
  wall (full height).
- Bottom edge: straight, with a through-hole line just above it (midplane
  Z = 1.5875) receiving the bottom panel's edge fingers.
- Top edge: plain, full height, entire length. The top panel joins through a
  **finger-hole line** below the top edge (midplane Z = 125.4125, X = 82.55 →
  301.625) — an edge-to-edge finger joint here would stand proud of the 127mm
  top plane (defect caught in #17 review).
- **Lid through-slot** (v2): X = 3.175 → 79.375 within the wall, Z =
  115.125 → 119.5, **open at the wall's front edge**. It is an open notch in
  the outline (`SlotMouthEdge` in `shell_generator.py`), not a closed hole, so
  no cut line coincides with another. The two inside corners at the rail's root (X = 79.375) are rounded with a 1.0 mm radius
  (`LID_SLOT_CORNER_R`). Leaves a 7.5 mm rail above
  (Z 119.5 → 127) cantilevered from X = 79.375 — handle gently until
  assembled.
- **Divider finger-hole line** (v2): vertical, X = 79.375 → 82.55, from
  Z = 3.175 up to the slot floor (115.125) on the left wall and 12.7 mm lower
  on the right wall (keying). A Boxes.py `fingerHolesAt` line, a dashed row of
  T-wide holes. The highest hole ends ≥ 6.3 mm below the slot floor.
- **Shelf finger-hole line**: horizontal, Z = 61.9125 → 65.0875, X = 82.55 →
  301.625. (Dashed row, as above.)
- **Engraving: wall art only (as of 2026-07-10).** The original "FAX MACHINE" 5×7
  pixel-font engraving (centered X = 152.4, Z = 63.5 on the right wall
  exterior) was removed by Ben's decision (issue #25 open-item 1): its
  centerline sat exactly on the shelf finger-hole cut row, and the wall
  artwork from art/FACES.md supersedes it (both walls get full-panel art
  via the art-integration pipeline; Ben has accepted that art crosses the
  joint-hole rows). The art is engraved from the cut + engrave file sets.

### 3. Front wall — 1×

- Nominal: **158.75 (Y) × 115.125 (Z)** (Z = 0 → 115.125; v2, was 118.025).
- Bottom-panel hole line near the bottom edge (midplane Z = 1.5875); vertical
  edges finger-joint to side walls; top edge plain (the lid slides over it).
- No pivot hole: the turn-button lid lock was removed on 2026-10-10 (see
  "Retention", section B).

### 4. Rear wall — 1×

- Nominal: **158.75 (Y) × 127.0 (Z)**, full height.
- Top edge plain, with a top-panel finger-hole line at midplane Z = 125.4125;
  sides → side walls. **v2: no bottom-panel hole row** (it cut the strip under
  the lower opening into 11 chips).
- **Two drawer openings**, each **152.4 wide (= W_INT − 2·max(T, 3.0); 153.5 at T = 2.8) × 55.0 tall**,
  centered in Y (0.875mm inside each interior corner joint; visible frame from
  outside ≈ 6.35mm per side):
  - Bottom opening: Z = max(T, 3.0) → +55.0 (3.175 → 58.175 at T = 3.175;
    sill-free: bottom edge = the lower drawer's floor; the solid web below it
    is at least 3.0 mm tall at every thickness).
  - Top opening: Z = 65.0875 → 120.0875 (sill-free: bottom edge = shelf top).
  - Webs remaining (at T = 3.175): 3.175 below the bottom opening (max(T, 3.0)),
    3.7375 below the shelf line, 3.7375 above the top opening — each ≥ 3.0
    (`MIN_WEB`); do not enlarge openings.

### 5. Vertical divider — 1×

- Nominal: **158.75 (Y) × 120.65 (Z)** (Z = 3.175 → 123.825, standing on the
  bottom panel).
- Bottom edge fingers down through the bottom panel's hole line; side edges
  finger into side-wall hole lines **up to the lid-slot floor only, plain
  above, with the right edge's fingers 4T shorter than the left's (keying, see
  v2)**; top edge fingers up into top panel holes. Captive on 4 edges →
  carries the structural load the SPEC requires.
- Its front face (X = 79.375) is the sliding lid's end stop. Its REAR face
  (X = 82.55) is where the drawer backs stop.
- Two magnet holes (Ø5.65), one per drawer, on the box centre line (box Y =
  82.55) at the drawers' mid-heights (see "Retention" §A).

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
- Measured with `partgeom.load_part('top')`: the top panel has a single row of
  holes, all along its plain front edge (one hole per divider finger): 12 at
  T = 3.175, 13 at 2.8 to 2.9, 12 at 3.0 to 3.1, 11 at 3.2 to 3.4 and 10 at 3.5.
  The side and rear edges carry fingers and no holes.
- **The walls' top-panel hole row's breakthrough is NOT hidden like the other edge-adjacent
  rows** (see the material note near the top of this document): the row's
  midplane (Z = 125.4125) sits close enough to the wall top edge (Z = 127.0)
  that the hole top (127.05) breaks through the visible top edge itself,
  rather than staying buried inside the joint. The holes read as open-top
  notches along the top edge until glue-up — cosmetically a normal
  finger-joint look, but the top panel's actual uplift fixity depends on the
  specified PVA glue-up (README's glue step), not on geometry alone.

### 8. Sliding lid — 1×

- Blank: **78.0 (X) × 163.6 (Y)** (was 79.0), plain edges, plus a grip slot.
- Width 163.6 = 165.1 − 1.5 sliding clearance; edges engage 2.425mm into each
  side-wall through-slot (slots are through-cuts, so the slot floor is the
  full exterior width).
- The two rear inside corners of the lid slot (at the rail's root, X = 79.375) are
  rounded with a 1.0 mm radius (`LID_SLOT_CORNER_R`) to remove the stress
  concentration. The lid stops 1.0 mm short of the end of the slot: its rear end is at
  X = 78.375 (`LID_REAR_X`) and its front edge is 0.375 mm behind the front wall plane
  (`LID_FRONT_RECESS`), so it never touches the arcs, even if it is lifted against the
  rail. Travel: slides in from the front, over the front wall top edge.
- Grip: rounded through-slot **30 × 10, r = 5**, centered in Y, slot center
  25mm from the front edge (10mm ligament to the edge; at 15mm the ligament
  was ~0.2mm and would have broken into a notch — red-team finding).
- The lid is held by friction in its slots only. The divider stops rearward
  motion, and nothing stops the lid sliding out the front when the box tips
  forward. The turn-button lock that would have done this was removed on
  2026-10-10 (Ben's decision; see "Retention", section B).

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
  exclusive. A magnet pair per drawer holds it closed (see "Retention" §A);
  without the magnets a drawer slides free if the box is tipped rear-down.
- Lateral play in the bay is limited by the drawer guides (part #10) to
  about 1.7 mm each way at the far end (1.8 mm at T 2.9, 1.9 mm at T 2.8). Without the guides it was 4.9 mm/side; the drawer
  was guided by its opening alone.

Faceplate (6th piece), glued to the body front:

- Blank: **150.9 (Y) × 53.5 (Z)** = opening − 2 × 0.75 reveal; same height as
  the body, +0.95/side in width. It is glued 0.75 mm ABOVE the body's bottom
  edge (`FACEPLATE_Z_OFFSET`), so it is centred in the opening with a 0.75 mm
  reveal on all four sides; flush with the rear face when closed (faceplate
  thickness T fills the rear wall plane).
- **Grip slot**: closed rounded slot **30 × 15, r = 7.5**, cut through BOTH
  the faceplate and the body's front wall, aligned, so a finger hooks through
  into the drawer. Centered in Y; on the body front the slot top edge is 8.0 below the part's
  top edge (slot spans 30.5 → 45.5 of the 53.5 height). On the faceplate it is
  8.75 below the plate's top edge (8.0 + `FACEPLATE_Z_OFFSET`), so the two slots line up. A closed slot (not a top-edge
  notch) keeps the top edge stiff and the opening reveal continuous.
- Registration: red-engraved lines on the faceplate's back for glue-up
  alignment: the body's left edge, right edge and top edge (0.95 mm in from
  the sides, 0.75 mm below the top; no bottom line, because the body's bottom
  edge sits 0.75 mm below the plate). They stay at least 0.5 mm from every cut.

### 10. Drawer guides — 4× (part J)

- Four flat plywood ribs, each **T wide × T high × 40 mm long** (`DRAWER_GUIDE`: length
  40, taper 30 degrees, tip width 0.8 mm). They lie flat on the bottom panel (lower pair)
  or on the shelf (upper pair), against the side edge of that panel (the edge that meets
  the wall's inner face), two per drawer slot.
- Each rib's FRONT end (its square end, toward the paper slot) is flush with the line where the divider's rear face stands: for the
  shelf that is the shelf's own front edge (X = 82.55, ignoring the tabs); for the bottom
  panel it is the rear edge of the row of divider slots.
- The end that faces the rear opening (the leading end, at the rear of the box) is cut at
  30 degrees in plan down to a 0.8 mm tip, so a drawer corner that arrives slightly yawed
  is funnelled in instead of butting the end face. Flat laser parts can taper in plan; an
  upright strip could not.
- Glue the two upper ribs to the shelf before the frame step (top panel + shelf +
  divider), and the two lower ribs to the bottom panel before the bottom-panel step (the
  bottom panel goes in from below carrying its two ribs). The wall steps do not involve
  guides.
- Each rib is only T wide, so it has no room for a part label; it is the only part
  without one.
- The channel between the ribs is `INTERIOR_WIDTH − 2T` (152.4 mm at T = 3.175, the same as
  the rear-wall opening), so a drawer (149.0 mm wide) floats at most 1.7 mm each way at
  its far end (1.8 mm at T 2.9, 1.9 mm at T 2.8). Without the ribs it floated 4.9 mm each way ((158.75 − 149.0) / 2), and
  the magnet pull is zero or negative beyond 4.5 mm. With N52 6 × 2 mm discs the pull at
  1.7 to 2.0 mm lateral offset is above 3 N.
- Widening the drawer is not an option: the drawer must pass the rear-wall opening,
  whose posts must stay at least 3.0 mm wide (`MIN_WEB`).

## Retention (magnets; the lid lock was removed)

Decision record (Ben, 2026-07-07, issue #20): v1 shipped with no retention.
Iteration 2 added a magnet pair per drawer (section A) and a turn-button lid
lock (section B). On 2026-10-10 Ben removed the turn-button lid lock (section B);
the magnets stay.

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
  back out to `MAGNET_HOLE_DIA`. Check the fit with the
  coupon's magnet holes (section C) before cutting real parts; they show what your
  laser and magnets want.
- Position: `MAGNET_Y_OFFSET = 0.0` (config.py; was 40.0 mm). The hole is
  centred on the drawer back, which is therefore mirror-symmetric and cannot go
  in turned round, and a mirror-built box still lines the magnets up. Each drawer
  is Y-centered in its rear-wall opening at closed position, so the drawer's
  Back-wall hole and both divider holes share one box Y = `T + INTERIOR_WIDTH/2`
  = 82.55, the box centre line.
- Z: "drawer mid-height" (`DRAWER_BODY['height']/2`) is a property of the
  drawer body alone; on the divider (a fixed part) it is projected via each
  slot's own resting datum — the lower drawer sits at `BOTTOM_DRAWER_Z0 =
  max(T, 3.0)`, the top drawer on the shelf top (`SHELF_Z1`) — giving two
  divider holes: `MAGNET_BOTTOM_DRAWER_Z = BOTTOM_DRAWER_Z0 + height/2 = 29.925`
  (at T = 3.175), `MAGNET_TOP_DRAWER_Z = SHELF_Z1 + height/2 = 91.8375`.
- Clearances (measured with `partgeom` at T = 3.175): both divider holes sit
  ≥23mm from every divider edge and ≥23mm from the divider's own shelf
  finger-hole row — comfortably over the 8mm structural-clearance target for
  this fully-captive, 4-edge load-bearing panel (part #5). The drawer
  Back-wall hole sits ≥20mm (20.75 measured) from every one of its own edges (well over the
  general 3mm minimum).
- Install BEFORE assembly, into the loose parts. Use **6×2mm N52 discs** (4 needed, buy
  6). Stack all four magnets in one column and mark a dot on the top face of the stack;
  they then all have the same pole up. Identify each part's inside and outside face by the
  labels (the joint labels and part letters are engraved on the inside face of parts
  without art; in the cut + labels files every part is engraved inside). Press every
  divider magnet in with its dot facing OUT, toward the drawers (the rear of the box), and
  every drawer-back magnet with its dot facing INTO the drawer, away from the divider
  (so in the finished box every dot faces the rear). Because all four
  are marked from the same stack, each drawer magnet attracts the divider magnet it meets,
  and either drawer works in either bay. Use a drop of glue. **Install the magnets FLUSH
  with the two MATING faces** (the drawer-Back's rear face and the divider's REAR face,
  X = 82.55 — the faces that actually close the gap), recessing only on the far
  (non-mating) side where the glue backfills; a 2mm disc recessed on its *mating* side,
  mirrored on both parts, would leave a pole-to-pole air gap across the joint that
  collapses the pull. The pull figures quoted for N35 discs in earlier revisions
  (0.5–0.7 kg flush, roughly 0.1–0.17 kg recessed) do not apply to N52 and have not been
  re-measured. N52 6 × 2 mm is the grade the pull figures are for; weaker grades hold less.
- **Assembly cautions.** Before the glue sets, slide each drawer in and check that it pulls
  shut against the divider (the magnets attract). If a drawer is pushed away, a magnet is
  the wrong way round; turn it over while the glue is still wet. Support the drawer with
  your other hand when you pull it out past halfway. There is no stop, and a drawer pulled
  out further than about 110 mm tips and drops.
- **Lateral float at the magnet end.** The magnet sits on the drawer's Back (leading)
  wall, at the far end of the drawer from the faceplate. The faceplate seated in its
  rear-wall opening holds its own end to ±0.75 mm, and the drawer is 218.6 mm long, so
  the Back end can still swing sideways. The drawer guides (part #10, flat ribs) narrow the channel
  at the divider end to 152.4 mm, so the drawer (149.0 mm wide) floats at most 1.7 mm each
  way there. Without the guides the float was 4.9 mm each way
  ((158.75 − 149.0) / 2), and the magnet pull is zero or negative beyond 4.5 mm. With N52
  6 × 2 mm discs the pull at 1.7 to 2.0 mm lateral offset is above 3 N. The earlier claim
  of about ±2.9 mm with the faceplate seated is withdrawn; 1.7 mm is the figure with the
  guides. Widening the drawer is not an option, because it must pass the rear-wall
  opening, whose posts must stay at least 3.0 mm wide.
- `test_magnet_holes_coaxial_at_closed_position` (`tests/test_retention.py`) checks the
  two drilled hole positions against the numbers in this document (a drafting check). It
  does not claim the assembled drawer sits dead-centre.

### B. Lid lock — removed 2026-10-10

Decision record: the turn-button lid lock was removed on 2026-10-10. This was
Ben's call; the lid stays in its slots by friction. Removed with it: the button
part (letter J), the Ø3.2 pivot hole in the front wall, the M3 bolt, two washers
and the nyloc nut, and the bolt that intruded into the paper compartment.

History, for the record: the first design (REV.A, a pivoting paddle on each side
wall) was found in review on 2026-07-07 to be geometrically incapable of
retention, because a side-wall paddle sweeps that wall's exterior plane while the
lid exits along X through the slot. It was replaced before any part was cut by
REV.B, a single button on the front wall, which is the mechanism that was then
removed. Nothing in the current geometry depends on either design.

### C. Test-fit coupon

`coupon.svg` / `coupon.dxf` and `coupon_marked.svg` / `coupon_marked.dxf`, built by
`coupon_items()` in `cutset.py` for every thickness. The marked coupon is the one with
engraved ticks 1 to 10 between the thickness slots and the magnet holes (they used to touch
the holes) and red line-engrave marks. The coupon is in every zip type (loose per kerf
under `coupon/`, and on a sheet of each bed layout where there was room). All parts are
measured with calipers; read them in this order: kerf square, thickness, then the kerf set
from the finger pairs. In every formula, k is the kerf MEASURED from the kerf square
(k = 10.00 − measured width), never the kerf of a file set.

- **K**, a 10 mm square piece drawn with no kerf compensation: k = 10.00 − measured
  width. Measure two directions and average. Kerf varies along the bed, so measure where
  the box will be cut. The sets are 0.12, 0.18 and 0.20 mm; the set nearest to k is only
  the first guess, and the finger pairs decide.
- **Q**, a panel with a clipped top-left corner as an orientation mark, ten thickness
  slots (`GAUGE_WIDTHS`) running from the narrowest (2.5 mm drawn) to the widest (3.4 mm)
  from left to right in 0.1 mm steps, and four magnet holes (drawn 5.3, 5.4, 5.5, 5.6 mm;
  cut hole = drawn + kerf; the box wants 5.65 mm for a 6.0 mm magnet). The cut slot is the
  drawn width plus k, so plywood from 2.8 to 3.5 mm shows up at any kerf from 0.10 to
  0.22 mm. Find the narrowest slot the plywood slides into without force (between two,
  take the tighter one). With W the drawn width of that slot, estimate = W + k − 0.05;
  round to 0.1 mm, half up (3.35 goes to 3.4); that is the thickness set. Examples: k =
  0.15 and W = 2.9 give 3.00, set 3.0; k = 0.10 and W = 3.3 give 3.35, set 3.4. If the
  plywood enters the first slot with room to spare, use the 2.8 set.
- **R**, three pairs of three-finger corners (finger piece + hole piece) that differ in
  size: the smallest is compensated for the diode kerf (0.12, 1 tick), the middle for CO2
  (0.18, 2 ticks) and the largest for Ponoko (0.20, 3 ticks). They have the same finger
  width, play (0.1 mm) and kerf compensation as the box joints. Take the pair that goes
  together with firm hand pressure and no rattle. If two pairs do, take the tighter one as
  long as it still goes together by hand without a tool. If none goes together by hand,
  take the smallest set and file the fingers. A pair made for kerf s on a laser with
  measured kerf k has 0.1 + 2 × (k − s) mm of clearance along the fingers: k = 0.15 picks
  the CO2 0.18 set (0.04 mm), and k = 0.10 picks the diode 0.12 set (0.06 mm). Joint
  looseness has two independent directions. Along the fingers it depends on kerf, as
  above. Through the thickness, tight means the plywood will not slide through the slot and
  the fingers end below the surface (plywood thicker than the set: next thicker set);
  loose means it rattles and the fingers stand proud of the surface (thinner: next thinner
  set).
- **S**, a lid slot block and strip, cut for the kerf of the set the coupon came from.

Choosing a kerf file set replaces the earlier practice of tuning `BURN` by editing
config constants. The older `calibration.py` coupons (`kerf_coupon.svg`,
`magnet_coupon.svg`) remain only for the legacy single-set path.

## Clearance summary (what the tests enforce)

| Interface | Clearance | Rule |
|---|---|---|
| Drawer body ↔ opening width | 3.4 total (opening 152.4 at T = 3.175, 153.5 at 2.8) | ≥ 1.5 per SPEC |
| Drawer body ↔ opening height | 1.5 | ≥ 1.5 |
| Drawer body ↔ slot height | 5.24 | ≥ 1.5 |
| Drawer body ↔ bay length | 0.475 | > 0 (not a sliding fit) |
| Lid width ↔ slot span | 1.5 total | ≥ 1.5 |
| Drawer lateral float at the divider end (with guide ribs) | 1.7 each way | magnet pull above 3 N (zero beyond 4.5 mm) |
| Lid thickness ↔ slot height | 1.2 | = 1.2 (documented deviation, v2) |
| Faceplate ↔ opening | 0.75/side | reveal 0.5–1.0 |
| Webs and posts in rear wall | 3.175 / 3.7375 (≥ 3.0 at every thickness; posts beside the openings are at least 3.0 wide) | ≥ 3.0 (`MIN_WEB`) |
| Magnet hole (drawer Back) ↔ its own edges | ≥ 20 | ≥ 3.0 |
| Magnet hole (divider) ↔ edges / shelf row | ≥ 23 | ≥ 8.0 (structural) |

### QA notes (2026-07-09 adversarial pass)

- The largest **drawn** part is the Shell Bottom at **304.96 × 165.26mm**
  (full footprint including finger extensions and burn compensation) — not
  the oft-quoted 298.45 (X) × 158.75 (Y) interior figure (`L_INT`/`W_INT`
  above), which is the interior span, not the cut blank's bounding box.
- Minimum viable laser bed, allowing a 10mm margin on all four sides of that
  part: **324.96 × 185.26mm**.
- v2: the rear wall's web below the bottom drawer opening is one solid 3.175mm
  strip (no hole row). The largest drawn part is now a side wall at 304.96 ×
  127.16mm; the bottom/top/shelf panels are 165.26mm deep. Minimum bed is
  unchanged at 324.96 × 185.26mm.

## Known deltas from SPEC.md targets

- Drawer external length 221.775 (body 218.6 + faceplate T) vs SPEC "9.0 external":
  the difference is consumed by the front wall, divider, and rear wall within
  the fixed 12" envelope. SPEC marks drawer dims "to fit" — envelope wins.
- Drawer external width 149.0 vs SPEC "approx 6.3" (160)": constrained by the
  rear-wall opening needing ≥T structural webs at the corners plus pass-through
  clearance. SPEC marks this "to fit".
