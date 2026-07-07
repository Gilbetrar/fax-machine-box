"""Geometry tests: parse output/*.svg with a real path parser (svgpathtools +
xml.etree, via tests/svg_utils.py) and check it against DESIGN.md, using
faxbox.config's NEW constants (never the DEPRECATED legacy alias block).

Piece identification: `svg_utils.get_pieces()` clusters raw <path> elements
into physical pieces purely by bbox containment (see svg_utils.py docstring),
independent of Boxes.py's current <g>-per-part output structure. Once a piece
is identified, we use its Boxes.py `label=...` text (also captured by
svg_utils, but *not* used for piece-boundary detection) only to figure out
*which* DESIGN.md part it's supposed to be -- see PART_LABEL_SYNONYMS below.
If a rebuild renames a wall's `label=`, update the synonym list; the
containment-based piece detection itself does not depend on labels.

Blank-size tolerance bands: `svg_utils.expected_band(nominal, jointed_edges,
T)` implements DESIGN.md's "[nominal, nominal + 2T] per axis according to its
jointed edges" rule (see DESIGN.md's parts-list intro). For each part below,
`jointed_edges` per axis is derived from DESIGN.md's prose description of
that part's edges (comments on each entry cite the sentence). We count an
edge as "jointed" if DESIGN.md says it finger-joints/fingers-into anything,
even partially (a partial finger-jointed edge can still push the local bbox
boundary out by up to T over the jointed portion); "plain" edges contribute
0. Since DESIGN.md never specifies whether a given joint's tabs (which
extend the blank) live on this part or its mate (which wouldn't), we
conservatively treat every jointed edge as potentially tab-bearing -- this
can only make the upper bound looser, never tighter, so it can't mask a
genuine oversize defect while still ruling out "hand-waved" huge tolerances.

Generators were known-broken pre-#17/#18 (wrong wall assignments, wrong sizes
inherited from the DEPRECATED legacy SHELL/DRAWER constants, missing top
panel, missing faceplate). During that period every check below that failed
against the not-yet-rebuilt output was marked `xfail(strict=False)` with a
reason citing the specific defect and the rebuild issue, while checks that
already held were left as ordinary (non-xfail) assertions on purpose, so the
suite would still catch a regression in what already worked. #17 (shell +
sliding lid) and #18 (drawers) are now closed and every check below holds
against current output for real; the xfail markers were removed once each
rebuild landed, and the comments on individual checks below (e.g. "NOT
xfail: ...") are kept as historical context for *why* a given check was
never marked xfail even during the pre-rebuild period.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from faxbox import config as c

import svg_utils as su

pytestmark = [pytest.mark.usefixtures("regenerate_svgs")]

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
SHELL_SVG = OUTPUT_DIR / "outer_shell.svg"
DRAWER_SVG = OUTPUT_DIR / "drawer.svg"
LIDS_SVG = OUTPUT_DIR / "lids.svg"

T = c.MATERIAL_THICKNESS


def _piece(svg_path, *synonyms):
    pieces = su.design_pieces(svg_path)
    found = su.find_piece_by_label(pieces, *synonyms)
    assert found is not None, (
        f"no piece labeled like {synonyms!r} found in {svg_path.name}; "
        f"labels present: {[p.label for p in pieces]}"
    )
    return found


def _assert_band(piece, axis_name, measured, nominal, jointed_edges):
    lo, hi = su.expected_band(nominal, jointed_edges, T)
    assert lo <= measured <= hi, (
        f"{piece.label!r} {axis_name}={measured:.2f} outside band "
        f"[{lo:.2f}, {hi:.2f}] for nominal {nominal} with {jointed_edges} "
        f"jointed edge(s)"
    )


def _cut_holes_matching(piece, width, height, tol=1.0):
    """Holes that are actual cuts (blue), not engraving (red) -- a decorative
    red pixel square geometrically inside a wall's bbox is not a hole."""
    return [
        h
        for h in piece.holes
        if su.normalize_color(h.stroke) == "blue" and h.bbox.dims_match(width, height, tol=tol)
    ]


# =============================================================================
# Piece counts
# =============================================================================
# DESIGN.md target piece counts (post #17/#18): shell = bottom + 2 side walls
# + front + rear + divider + shelf + fixed top panel = 8. drawer.svg = one
# drawer's worth = 5 body walls + 1 faceplate = 6 (DESIGN.md part 9: "2x
# identical, 6 pieces each"). lids.svg = sliding lid alone (DESIGN.md: "Fixed
# top panel... not a removable lid" -- the old flat/tabbed lid concept is
# gone; #17 explicitly moves the top panel into outer_shell.svg and leaves
# lids.svg with only the sliding lid panel).

def test_shell_piece_count():
    assert len(su.design_pieces(SHELL_SVG)) == 8


def test_drawer_piece_count():
    assert len(su.design_pieces(DRAWER_SVG)) == 6


def test_lids_piece_count():
    assert len(su.design_pieces(LIDS_SVG)) == 1


# =============================================================================
# No two pieces' bboxes overlap
# =============================================================================
# This is a real, currently-meaningful check on all three files (not merely a
# consequence of wrong-but-internally-consistent geometry): a `move=`
# omission or wrong direction produces genuine bbox overlap regardless of
# whether the *sizes* being moved are DESIGN.md-correct.

def _assert_no_piece_overlaps(svg_path):
    pieces = su.get_pieces(svg_path)
    offenders = []
    for i in range(len(pieces)):
        for j in range(i + 1, len(pieces)):
            if pieces[i].bbox.overlaps(pieces[j].bbox):
                offenders.append((pieces[i].label, pieces[j].label))
    assert not offenders, f"overlapping piece bboxes in {svg_path.name}: {offenders}"


def test_shell_pieces_do_not_overlap():
    _assert_no_piece_overlaps(SHELL_SVG)


def test_drawer_pieces_do_not_overlap():
    _assert_no_piece_overlaps(DRAWER_SVG)


def test_lids_pieces_do_not_overlap():
    """Currently passes -- see LEARNINGS.md / issue report for the negative
    control that exercises this exact check by breaking a `move=` value."""
    _assert_no_piece_overlaps(LIDS_SVG)


# =============================================================================
# Per-part blank size bands
# =============================================================================

# --- Shell parts -------------------------------------------------------------
# DESIGN.md #1 (as amended 2026-07-07): bottom panel is INSET between
# full-height walls, nominal INTERIOR_LENGTH x INTERIOR_WIDTH with edge
# fingers on all four edges -> 2 jointed edges per axis. Historically NOT
# xfail (pre-#17 rebuild): the pre-rebuild generator's full-footprint Bottom
# (304.8 x 165.1) sat exactly at nominal + 2T on both axes, which is this
# band's upper bound -- a real (maximal) pass under the DESIGN.md tolerance
# rule, same situation as the divider tests below. The rebuilt generator's
# inset Bottom passes the same band for the ordinary reason (it's built to
# nominal, extended by real edge fingers).
def test_bottom_panel_blank_size():
    piece = _piece(SHELL_SVG, "bottom")
    _assert_band(piece, "X", piece.bbox.width, c.INTERIOR_LENGTH, jointed_edges=2)
    _assert_band(piece, "Y", piece.bbox.height, c.INTERIOR_WIDTH, jointed_edges=2)


# DESIGN.md #2 (amended): nominal 298.45 (X) x 127.0 (Z), full height.
# X-axis: front edge jointed "only up to Z=118.025" (partial, still counts)
# + rear edge jointed "full height" -> 2 jointed edges. Z-axis: bottom AND
# top edges are straight (panel joints are interior hole lines, which are
# cutouts and don't extend the blank) -> 0 jointed. This tight Z band is
# deliberate: an edge-jointed top would protrude past the 127mm top plane
# (the defect caught in #17 review) and must fail here.
@pytest.mark.parametrize("side", ["left wall", "right wall"])
def test_side_wall_blank_size(side):
    piece = _piece(SHELL_SVG, side)
    _assert_band(piece, "X", piece.bbox.width, c.INTERIOR_LENGTH, jointed_edges=2)
    _assert_band(piece, "Z", piece.bbox.height, c.WALL_HEIGHT, jointed_edges=0)


# DESIGN.md #3 (amended): nominal 158.75 (Y) x 118.025 (Z), running from
# Z=0. Y-axis: both vertical edges finger-joint to side walls -> 2. Z-axis:
# bottom straight (hole line only), top plain (lid slides over it) -> 0.
def test_front_wall_blank_size():
    piece = _piece(SHELL_SVG, "front wall")
    _assert_band(piece, "Y", piece.bbox.width, c.INTERIOR_WIDTH, jointed_edges=2)
    _assert_band(piece, "Z", piece.bbox.height, c.FRONT_WALL_HEIGHT, jointed_edges=0)


# DESIGN.md #4 (amended): nominal 158.75 (Y) x 127.0 (Z), full height.
# Y-axis: sides -> side walls -> 2. Z-axis: bottom straight (hole line
# only), top -> top panel -> 1.
def test_rear_wall_blank_size():
    piece = _piece(SHELL_SVG, "rear wall", "back wall")
    _assert_band(piece, "Y", piece.bbox.width, c.INTERIOR_WIDTH, jointed_edges=2)
    # Z jointed_edges=0 for the same reason as the side walls: top-panel and
    # bottom-panel joints are interior hole lines, so nothing may extend the
    # blank past the 127mm top plane.
    _assert_band(piece, "Z", piece.bbox.height, c.WALL_HEIGHT, jointed_edges=0)


# DESIGN.md #5: nominal 158.75 (Y) x 120.65 (Z). Both axes fully captive
# ("Fully captive on 4 edges") -> 2 jointed edges each.
# Kept as two assertions because the two axes had different pre-rebuild
# histories worth documenting separately:
# Historically NOT xfail on Y (pre-#17 rebuild): the pre-rebuild generator
# passed the *full exterior* Y (165.1mm, from the legacy SHELL dict) straight
# through, uncorrected for joints. But nominal(158.75) + 2*T ==
# SHELL_EXT["width"] exactly (algebra: INTERIOR_WIDTH is defined as
# SHELL_EXT width - 2T), so a full-exterior-width blank sat right at this
# axis's max-jointed-edges upper bound and passed under the DESIGN.md-
# prescribed tolerance -- a real (if maximal) pass, not a coincidence worth
# hiding behind xfail. The rebuilt generator passes the same band for the
# ordinary reason.
def test_divider_blank_size_y():
    piece = _piece(SHELL_SVG, "vertical divider", "divider")
    _assert_band(piece, "Y", piece.bbox.width, c.INTERIOR_WIDTH, jointed_edges=2)


# Z: same story as Y above. DIVIDER_HEIGHT(120.65) + 2*T == SHELL_EXT height
# (127.0) exactly (DIVIDER_HEIGHT is TOP_PANEL_Z0 - WALL_Z0 == 127 - 2T), so
# the pre-rebuild generator's full-127mm divider height also landed exactly
# on this axis's max-jointed-edges upper bound: a real pass under the
# DESIGN.md-prescribed [nominal, nominal + 2T] band even then, not weakened
# to fit.
def test_divider_blank_size_z():
    piece = _piece(SHELL_SVG, "vertical divider", "divider")
    _assert_band(piece, "Z", piece.bbox.height, c.DIVIDER_HEIGHT, jointed_edges=2)


# DESIGN.md #6: nominal 219.075 (X) x 158.75 (Y). X-axis: front edge jointed
# into divider, rear edge "plain, butting the rear wall" -> 1. Y-axis: "Side
# edges finger into side-wall hole lines" (both) -> 2.
def test_shelf_blank_size():
    piece = _piece(SHELL_SVG, "horizontal shelf", "shelf")
    _assert_band(piece, "X", piece.bbox.width, c.BAY_LENGTH, jointed_edges=1)
    _assert_band(piece, "Y", piece.bbox.height, c.INTERIOR_WIDTH, jointed_edges=2)


# DESIGN.md #7: nominal X = 79.375 -> 301.625 = 222.25 (includes divider
# cover strip), Y = 158.75. X-axis: front edge explicitly "plain", rear edge
# finger-joints into rear wall top edge -> 1. Y-axis: "Side... edges finger-
# joint into the side... wall top edges" -> 2.
def test_top_panel_blank_size():
    piece = _piece(SHELL_SVG, "top panel")
    nominal_x = c.BAY_X1 - c.DIVIDER_X0  # 222.25
    _assert_band(piece, "X", piece.bbox.width, nominal_x, jointed_edges=1)
    _assert_band(piece, "Y", piece.bbox.height, c.INTERIOR_WIDTH, jointed_edges=2)


# --- Drawer parts --------------------------------------------------------------
# DESIGN.md #9 body external: width 149.0 (Y), length 218.0 (X), height 53.5
# (Z). Front/back panels span Y x Z (both Y edges finger-joint to the side
# panels -> 2; bottom edge jointed into the bottom panel -> 1, top open/plain
# for the open-top box). Side panels span X x Z (both X edges finger-joint
# to front/back -> 2; same Z treatment -> 1). Bottom spans X x Y, captive
# (holes only, doesn't extend) -> 0 jointed both axes.
@pytest.mark.parametrize("side", ["front", "back"])
def test_drawer_front_back_blank_size(side):
    piece = _piece(DRAWER_SVG, side)
    _assert_band(piece, "Y", piece.bbox.width, c.DRAWER_BODY["width"], jointed_edges=2)
    _assert_band(piece, "Z", piece.bbox.height, c.DRAWER_BODY["height"], jointed_edges=1)


@pytest.mark.parametrize("side", ["left side", "right side"])
def test_drawer_left_right_blank_size(side):
    piece = _piece(DRAWER_SVG, side)
    _assert_band(piece, "X", piece.bbox.width, c.DRAWER_BODY["length"], jointed_edges=2)
    _assert_band(piece, "Z", piece.bbox.height, c.DRAWER_BODY["height"], jointed_edges=1)


def test_drawer_bottom_blank_size():
    piece = _piece(DRAWER_SVG, "bottom")
    _assert_band(piece, "X", piece.bbox.width, c.DRAWER_BODY["length"], jointed_edges=0)
    _assert_band(piece, "Y", piece.bbox.height, c.DRAWER_BODY["width"], jointed_edges=0)


# DESIGN.md #9 faceplate: "glued to the body front" (not finger-jointed) ->
# 0 jointed edges both axes.
#
# FLAGGED DEVIATION (issue #20, retention iteration 2): the Y-axis nominal
# below is c.FACEPLATE_DRAWN_WIDTH (150.9 + 2*DRAWER_DETENT_PROTRUDE), not
# the plain c.FACEPLATE["width"] this test used pre-#20. The faceplate now
# carries a real cantilever nub that protrudes DRAWER_DETENT_PROTRUDE past
# each Y edge (see generate_drawers.py's _build_faceplate and DESIGN.md's
# "Retention (iteration 2)" section) -- svg_utils's bbox-based piece
# detection has no way to distinguish "a bigger nominal blank" from "a real
# protruding feature on the same connected piece", so a genuinely larger
# physical part is the only way to add real interference retention here,
# and this test's *measurement* (piece.bbox.width) legitimately grew. The
# tolerance slack (0.5mm) is unchanged from before -- this updates the
# nominal being measured against, not the rigor of the check.
def test_faceplate_blank_size():
    piece = _piece(DRAWER_SVG, "faceplate")
    _assert_band(piece, "Y", piece.bbox.width, c.FACEPLATE_DRAWN_WIDTH, jointed_edges=0)
    _assert_band(piece, "Z", piece.bbox.height, c.FACEPLATE["height"], jointed_edges=0)


# --- Sliding lid ---------------------------------------------------------------
# DESIGN.md #8: "Blank: 79.0 (X) x 163.6 (Y), plain edges, plus a grip slot."
def test_sliding_lid_blank_size():
    piece = _piece(LIDS_SVG, "sliding lid")
    _assert_band(piece, "X", piece.bbox.width, c.SLIDING_LID["length"], jointed_edges=0)
    _assert_band(piece, "Y", piece.bbox.height, c.SLIDING_LID["width"], jointed_edges=0)


# =============================================================================
# Interior cutouts
# =============================================================================

# --- Rear wall: exactly 2 drawer openings, 152.4 x 55.0 (OPENING_WIDTH x
# OPENING_HEIGHT) --------------------------------------------------------------
def test_rear_wall_has_two_drawer_openings():
    piece = _piece(SHELL_SVG, "rear wall", "back wall")
    matches = _cut_holes_matching(piece, c.OPENING_WIDTH, c.OPENING_HEIGHT)
    assert len(matches) == 2, (
        f"expected 2 openings ~{c.OPENING_WIDTH}x{c.OPENING_HEIGHT}mm on the rear wall, "
        f"found {len(matches)}; all cut holes: "
        f"{[(round(h.bbox.width,2), round(h.bbox.height,2)) for h in piece.holes if su.normalize_color(h.stroke)=='blue']}"
    )


# --- Side walls: lid through-slot + divider finger-hole line + shelf finger-
# hole line ---------------------------------------------------------------------
# The lid slot must be open at the wall's front edge (a closed slot could
# never admit the lid). Construction (DESIGN.md #2, amended): the slot is
# drawn as a closed rectangularHole whose front boundary exactly coincides
# with the blank's front edge -- the laser cuts both lines and the mouth
# opens (one 3.975mm segment is double-cut; negligible). This keeps the slot
# detectable as an ordinary hole. Front-vs-rear mouth placement is
# position-blind here; checked visually per #17.
LID_SLOT_LENGTH = c.LID_SLOT_X_END - T                          # 76.2

# Finger-hole lines are DASHED rows of separate T-wide holes (Boxes.py
# fingerHolesAt), not single continuous slots -- detected as grouped rows
# via svg_utils.hole_line_spans. A row's dashes don't reach the very ends of
# its nominal span, so we accept >= 75% coverage; the upper bound rules out
# some unrelated full-width row being mistaken for the target.
DIVIDER_LINE_NOMINAL = c.DIVIDER_HEIGHT                          # 120.65 (vertical)
SHELF_LINE_NOMINAL = c.BAY_LENGTH                                # 219.075 (horizontal)


@pytest.mark.parametrize("side", ["left wall", "right wall"])
def test_side_wall_has_lid_slot(side):
    piece = _piece(SHELL_SVG, side)
    matches = _cut_holes_matching(piece, LID_SLOT_LENGTH, c.LID_SLOT_HEIGHT, tol=0.5)
    assert len(matches) == 1, (
        f"expected 1 lid slot hole ~{LID_SLOT_LENGTH}x{c.LID_SLOT_HEIGHT}mm "
        f"(front boundary flush with the blank's front edge) in {side}, found {len(matches)}"
    )


def _blue_holes(piece):
    return [h for h in piece.holes if su.normalize_color(h.stroke) == "blue"]


@pytest.mark.parametrize("side", ["left wall", "right wall"])
def test_side_wall_has_divider_hole_line(side):
    piece = _piece(SHELL_SVG, side)
    spans = su.hole_line_spans(_blue_holes(piece), T, axis="y")
    hits = [s for s in spans if 0.75 * DIVIDER_LINE_NOMINAL <= s <= DIVIDER_LINE_NOMINAL + 1.0]
    assert len(hits) == 1, (
        f"expected 1 vertical divider finger-hole row spanning ~{DIVIDER_LINE_NOMINAL}mm "
        f"in {side}; vertical row spans found: {[round(s, 1) for s in spans]}"
    )


@pytest.mark.parametrize("side", ["left wall", "right wall"])
def test_side_wall_has_shelf_and_top_panel_hole_lines(side):
    """Each side wall carries TWO horizontal bay-length hole rows: the shelf
    line (mid-height) and the top-panel line (just below the top edge). Both
    span ~BAY_LENGTH; the near-full-width bottom-panel row is longer and must
    not land in this band."""
    piece = _piece(SHELL_SVG, side)
    spans = su.hole_line_spans(_blue_holes(piece), T, axis="x")
    hits = [s for s in spans if 0.75 * SHELF_LINE_NOMINAL <= s <= SHELF_LINE_NOMINAL + 1.0]
    assert len(hits) == 2, (
        f"expected 2 horizontal bay-length finger-hole rows (shelf + top panel) "
        f"in {side}; horizontal row spans found: {[round(s, 1) for s in spans]}"
    )


def test_rear_wall_has_top_panel_hole_line():
    """Rear wall carries two full-interior-width horizontal rows: bottom
    panel (near bottom edge) and top panel (near top edge)."""
    piece = _piece(SHELL_SVG, "rear wall", "back wall")
    spans = su.hole_line_spans(_blue_holes(piece), T, axis="x")
    hits = [s for s in spans if 0.7 * c.INTERIOR_WIDTH <= s <= c.INTERIOR_WIDTH + 1.0]
    assert len(hits) == 2, (
        f"expected 2 horizontal interior-width finger-hole rows (bottom + top panel) "
        f"in rear wall; spans found: {[round(s, 1) for s in spans]}"
    )


# --- Drawer: grip slot through BOTH faceplate and body front, aligned
# (DESIGN.md #9, amended: a closed 30x15 r7.5 slot replaced the old top-edge
# notch -- a closed hole keeps the top edge stiff and stays detectable) ---------
GRIP_SLOT_SIZE = (c.DRAWER_GRIP_SLOT["width"], c.DRAWER_GRIP_SLOT["height"])  # 30 x 15


def test_faceplate_has_grip_slot():
    piece = _piece(DRAWER_SVG, "faceplate")
    matches = _cut_holes_matching(piece, *GRIP_SLOT_SIZE, tol=1.0)
    assert len(matches) == 1


# Historically NOT xfail: even the pre-#18-rebuild generator's "notch" was
# implemented as a rounded 30x15 rectangularHole in the body Front --
# dimensionally identical to the DESIGN.md grip slot (position differs,
# which this size-based check doesn't see), so this passed for real before
# the rebuild too. #18 (now closed) kept it passing.
def test_drawer_body_front_has_matching_grip_slot():
    piece = _piece(DRAWER_SVG, "front")
    blue = _blue_holes(piece)
    matches = _cut_holes_matching(piece, *GRIP_SLOT_SIZE, tol=1.0)
    assert len(matches) == 1 and len(blue) == 1, (
        f"body Front should carry exactly one cut hole, the {GRIP_SLOT_SIZE} grip slot; "
        f"found {[(round(h.bbox.width, 1), round(h.bbox.height, 1)) for h in blue]}"
    )


# =============================================================================
# Positional / mating assertions (red-team gap closure)
# =============================================================================
# Everything above this line checks SIZE (bbox dims, hole dims, row spans) --
# it can't tell a correctly-sized part/hole from one that's been slid a few
# mm off its mating position, because a size-only check by construction
# ignores WHERE a hole sits within its host's bbox. The red-team review
# demonstrated exactly that gap: shifting the lid slot toward the box
# interior, or dropping it vertically, or moving both rear-wall drawer
# openings, or swapping the top panel's mating CompoundEdge for a plain
# full edge, all left every test above green while producing hardware that
# cannot physically assemble (a slot that never reaches the wall's front
# edge can't admit the sliding lid; a top panel with the wrong edge type
# has no fingers to align with the walls' hole rows at all).
#
# Frame mapping. Every generated piece is placed by Boxes.py's `move=`
# layout at an arbitrary offset from the *design* origin DESIGN.md's numbers
# describe -- there is no single global affine transform recorded anywhere
# in the SVG. Per-piece we recover one from an ANCHOR: some already-verified
# feature of the piece whose DESIGN.md box coordinate we know, so
# `wall_offset = measured_anchor_position - known_box_position` maps every
# other measurement on that same piece into box coordinates. This was
# prototype-validated (see PR discussion) against the current known-good
# output before being encoded below:
#   - Side walls: the divider finger-hole COLUMN's X center is box X
#     DIVIDER_MID_BOX_X (80.9625) on both walls (same physical divider
#     location). The left wall is drawn as the right wall's mirror image in
#     local X (DESIGN.md #2), so the map isn't a pure shift for the left
#     wall -- it's a reflection through the anchor.
#   - Side/rear walls, Z axis: piece bbox.ymin is box Z = WALL_HEIGHT (top);
#     SVG is y-down and neither wall's top/bottom edge is finger-jointed
#     (no protrusion), so this holds directly off the bbox with only
#     sub-0.1mm burn slop.
#   - Top panel / shelf: their PLAIN (non-jointed, non-protruding) edge is
#     a clean anchor -- top panel's front edge is box X DIVIDER_X0
#     (79.375); shelf's rear edge is box X BAY_X1 (301.625).
# Every check below was derived by measuring today's known-good output,
# cross-checking the measured number against a hand-computed config
# expression, THEN encoding that expression -- never a bare measured
# constant (see module docstring / issue instructions).

DIVIDER_MID_BOX_X = (c.DIVIDER_X0 + c.DIVIDER_X1) / 2  # 80.9625, the anchor
WALL_SIDES = [("right wall", False), ("left wall", True)]  # (label, mirror)


def _wall_divider_row(wall):
    """The wall's vertical divider finger-hole column, as a HoleRow (its
    `.center` is the anchor -- see module-level comment above)."""
    rows = su.hole_line_rows(_blue_holes(wall), T, axis="y")
    hits = [r for r in rows if 0.75 * DIVIDER_LINE_NOMINAL <= r.span <= DIVIDER_LINE_NOMINAL + 1.0]
    assert len(hits) == 1, (
        f"expected exactly 1 divider finger-hole column on {wall.label!r}, found {len(hits)}"
    )
    return hits[0]


def _wall_frame(wall, mirror):
    """Return a function mapping this wall piece's raw SVG X -> box X, using
    the divider finger-hole column as the anchor. `mirror` flips the sign:
    the left wall is the right wall's mirror image in local X."""
    col = _wall_divider_row(wall).center
    sign = -1.0 if mirror else 1.0

    def to_box_x(x: float) -> float:
        return DIVIDER_MID_BOX_X + sign * (x - col)

    return to_box_x


def _wall_box_z(wall, y: float) -> float:
    """SVG y -> box Z on a full-height wall (side or rear wall): bbox.ymin
    is box Z = WALL_HEIGHT (top), SVG is y-down, neither the top nor bottom
    edge is finger-jointed on these walls so there's no protrusion to
    correct for."""
    return c.WALL_HEIGHT - (y - wall.bbox.ymin)


def _assert_teeth_match(teeth, targets, what, tol=0.6):
    assert teeth, f"{what}: found no candidate teeth (edge_teeth_centers returned nothing)"
    assert targets, f"{what}: found no target dash centers to compare against"
    offenders = []
    for t in teeth:
        nearest = min(abs(t - x) for x in targets)
        if nearest > tol:
            offenders.append((round(t, 2), round(nearest, 2)))
    assert not offenders, (
        f"{what}: tooth centers with no matching target within {tol}mm "
        f"(tooth, nearest-miss): {offenders}; targets: {sorted(round(x, 2) for x in targets)}"
    )


def _row_dash_positions(piece, cross_axis_thickness, row, row_axis, to_coord, tol=1.0):
    """Individual dash centers (not just the row's aggregate span/center)
    for one hole_line_rows row, mapped through `to_coord`.

    row_axis='x': row is horizontal (dashes vary in X); returns mapped
    X-centers. row_axis='y': row is vertical (dashes vary in Y); returns
    mapped Y-centers (via `to_coord`, e.g. a Z-mapping function).
    """
    out = []
    for h in _blue_holes(piece):
        if row_axis == "x":
            if abs(h.bbox.height - cross_axis_thickness) > 0.5:
                continue
            cross = (h.bbox.ymin + h.bbox.ymax) / 2
            along = (h.bbox.xmin + h.bbox.xmax) / 2
        else:
            if abs(h.bbox.width - cross_axis_thickness) > 0.5:
                continue
            cross = (h.bbox.xmin + h.bbox.xmax) / 2
            along = (h.bbox.ymin + h.bbox.ymax) / 2
        if abs(cross - row.center) < tol:
            out.append(to_coord(along))
    return out


# --- 1. Lid slot: mouth at the front, correct vertical position --------------------

@pytest.mark.parametrize("side,mirror", WALL_SIDES)
def test_side_wall_lid_slot_mouth_reaches_front_edge(side, mirror):
    """Red-team M1a: shifting the slot 3mm toward the interior (slot_cx +3
    in shell_generator._build_side_wall) leaves the slot's SIZE untouched
    (test_side_wall_has_lid_slot stays green) but the mouth no longer
    reaches the wall's front edge -- the lid could never be inserted."""
    piece = _piece(SHELL_SVG, side)
    matches = _cut_holes_matching(piece, LID_SLOT_LENGTH, c.LID_SLOT_HEIGHT, tol=0.5)
    assert len(matches) == 1
    slot = matches[0].bbox
    gap = (slot.xmin - piece.bbox.xmin) if not mirror else (piece.bbox.xmax - slot.xmax)
    assert gap <= T + 0.4, (
        f"{side}: lid slot mouth sits {gap:.2f}mm inside the wall's front edge "
        f"(must be <= T+0.4={T + 0.4:.2f} for the slot to actually open at the front); "
        f"slot bbox {slot}, piece bbox {piece.bbox}"
    )


@pytest.mark.parametrize("side,mirror", WALL_SIDES)
def test_side_wall_lid_slot_vertical_position(side, mirror):
    """Red-team M1b: lowering the slot 10mm (slot_cz -10) keeps the mouth at
    the front edge (test above stays green) but drops the lid below its
    LID_RAIL_HEIGHT rail -- catch the vertical position directly."""
    piece = _piece(SHELL_SVG, side)
    matches = _cut_holes_matching(piece, LID_SLOT_LENGTH, c.LID_SLOT_HEIGHT, tol=0.5)
    assert len(matches) == 1
    slot = matches[0].bbox
    dy = slot.ymin - piece.bbox.ymin
    assert abs(dy - c.LID_RAIL_HEIGHT) <= 0.4, (
        f"{side}: lid slot top is {dy:.2f}mm below the wall's top edge, "
        f"expected LID_RAIL_HEIGHT={c.LID_RAIL_HEIGHT} +/-0.4"
    )


# --- 2. Rear wall drawer openings: exact Z placement + X-centering -----------------

def test_rear_wall_opening_positions():
    """Red-team M3: shifting both opening centers +5mm keeps their SIZE
    correct (test_rear_wall_has_two_drawer_openings stays green) but
    misaligns them with the drawer bay's actual bottom/shelf/top-panel
    split."""
    piece = _piece(SHELL_SVG, "rear wall", "back wall")
    matches = _cut_holes_matching(piece, c.OPENING_WIDTH, c.OPENING_HEIGHT)
    assert len(matches) == 2
    expected_spans = [
        (c.BOTTOM_OPENING_Z0, c.BOTTOM_OPENING_Z1),
        (c.TOP_OPENING_Z0, c.TOP_OPENING_Z1),
    ]

    def expected_dy(z0, z1):
        return c.WALL_HEIGHT - (z0 + z1) / 2

    piece_cx = (piece.bbox.xmin + piece.bbox.xmax) / 2
    remaining = list(expected_spans)
    for hole in matches:
        dy = ((hole.bbox.ymin + hole.bbox.ymax) / 2) - piece.bbox.ymin
        best = min(remaining, key=lambda e: abs(dy - expected_dy(*e)))
        exp_dy = expected_dy(*best)
        assert abs(dy - exp_dy) <= 0.6, (
            f"rear wall opening center is {dy:.2f}mm from the wall's top edge; "
            f"nearest expected Z span {best} wants {exp_dy:.2f} (+/-0.6)"
        )
        remaining.remove(best)
        hx = (hole.bbox.xmin + hole.bbox.xmax) / 2
        assert abs(hx - piece_cx) <= 0.6, (
            f"rear wall opening x-center {hx:.2f} is not centered on the wall "
            f"(piece x-center {piece_cx:.2f})"
        )

    # Loose plausibility net on top of the tight center check above: derive
    # the webs actually implied by the measured edges (not the DESIGN.md
    # table -- see issue instructions) and confirm none has collapsed below
    # a structurally real thickness.
    by_z = sorted(matches, key=lambda h: (h.bbox.ymin + h.bbox.ymax) / 2)
    top_opening, bottom_opening = by_z[0], by_z[1]  # smaller SVG y = higher Z
    web_top = top_opening.bbox.ymin - piece.bbox.ymin
    web_bottom = piece.bbox.ymax - bottom_opening.bbox.ymax
    web_between = bottom_opening.bbox.ymin - top_opening.bbox.ymax
    for name, web in (("top", web_top), ("bottom", web_bottom), ("between", web_between)):
        assert web >= c.MIN_WEB - 0.3, f"rear wall {name} web collapsed to {web:.2f}mm (< MIN_WEB-0.3)"


# --- 3. Side wall hole-row Z-planes + divider column vs. slot cross-check ----------

@pytest.mark.parametrize("side,mirror", WALL_SIDES)
def test_side_wall_hole_row_planes(side, mirror):
    piece = _piece(SHELL_SVG, side)
    holes = _blue_holes(piece)
    to_box_x = _wall_frame(piece, mirror)

    rows_x = su.hole_line_rows(holes, T, axis="x")
    bottom_hits = [r for r in rows_x if r.span > 0.9 * c.INTERIOR_LENGTH]
    assert len(bottom_hits) == 1, f"{side}: expected 1 near-full-width bottom-panel row"
    bottom_z = _wall_box_z(piece, bottom_hits[0].center)
    assert abs(bottom_z - T / 2) <= 0.6, f"{side}: bottom-panel row at Z={bottom_z:.2f}, expected T/2"

    bay_hits = [r for r in rows_x if 0.75 * SHELF_LINE_NOMINAL <= r.span <= SHELF_LINE_NOMINAL + 1.0]
    assert len(bay_hits) == 2, f"{side}: expected 2 bay-length rows (shelf + top panel)"
    shelf_row = max(bay_hits, key=lambda r: r.center)  # larger SVG y = lower Z
    top_row = min(bay_hits, key=lambda r: r.center)
    shelf_mid_z = c.SHELF_Z0 + T / 2
    shelf_z = _wall_box_z(piece, shelf_row.center)
    top_z = _wall_box_z(piece, top_row.center)
    assert abs(shelf_z - shelf_mid_z) <= 0.6, f"{side}: shelf row at Z={shelf_z:.2f}, expected {shelf_mid_z:.2f}"
    assert abs(top_z - c.TOP_PANEL_HOLE_Z) <= 0.6, (
        f"{side}: top-panel row at Z={top_z:.2f}, expected {c.TOP_PANEL_HOLE_Z:.2f}"
    )

    # Divider column position, cross-checked (via the same anchor frame)
    # against the lid slot's own closed end rather than against itself.
    matches = _cut_holes_matching(piece, LID_SLOT_LENGTH, c.LID_SLOT_HEIGHT, tol=0.5)
    assert len(matches) == 1
    slot = matches[0].bbox
    closed_end_x = slot.xmax if not mirror else slot.xmin
    mapped = to_box_x(closed_end_x)
    assert abs(mapped - c.LID_SLOT_X_END) <= 0.6, (
        f"{side}: divider column vs. slot closed end maps to box X={mapped:.2f}, "
        f"expected LID_SLOT_X_END={c.LID_SLOT_X_END}"
    )


# --- 4. Rear wall hole-row Z-planes -------------------------------------------------

def test_rear_wall_hole_row_planes():
    piece = _piece(SHELL_SVG, "rear wall", "back wall")
    rows = su.hole_line_rows(_blue_holes(piece), T, axis="x")
    hits = [r for r in rows if 0.7 * c.INTERIOR_WIDTH <= r.span <= c.INTERIOR_WIDTH + 1.0]
    assert len(hits) == 2, f"expected 2 interior-width rows (bottom + top panel), found {len(hits)}"
    bottom_row = max(hits, key=lambda r: r.center)  # larger SVG y = nearer piece bottom
    top_row = min(hits, key=lambda r: r.center)

    bottom_from_edge = piece.bbox.ymax - bottom_row.center
    top_from_edge = top_row.center - piece.bbox.ymin
    assert abs(bottom_from_edge - T / 2) <= 0.6
    expected_top_from_edge = c.WALL_HEIGHT - c.TOP_PANEL_HOLE_Z
    assert abs(top_from_edge - expected_top_from_edge) <= 0.6, (
        f"rear wall top-panel row is {top_from_edge:.2f}mm from the top edge, "
        f"expected {expected_top_from_edge:.2f}"
    )


# --- 5. Counterpart divider rows on Bottom / Divider / Top Panel -------------------

def test_bottom_panel_divider_row_position():
    piece = _piece(SHELL_SVG, "bottom")
    rows = su.hole_line_rows(_blue_holes(piece), T, axis="y")
    hits = [r for r in rows if 0.75 * c.INTERIOR_WIDTH <= r.span <= c.INTERIOR_WIDTH + 1.0]
    assert len(hits) == 1
    # Bottom panel's fingers protrude T on ALL 4 edges, so its bbox.xmin
    # sits at box X = 0 (not T) -- the row's box-X position is directly its
    # distance from bbox.xmin.
    dx = hits[0].center - piece.bbox.xmin
    assert abs(dx - DIVIDER_MID_BOX_X) <= 0.6, (
        f"bottom panel divider row is {dx:.2f}mm from bbox.xmin, expected {DIVIDER_MID_BOX_X}"
    )


def test_divider_shelf_row_position():
    piece = _piece(SHELL_SVG, "vertical divider", "divider")
    rows = su.hole_line_rows(_blue_holes(piece), T, axis="x")
    # The divider's own shelf row spans INTERIOR_WIDTH (full Y), unlike the
    # side walls' shelf row which spans only BAY_LENGTH (X) -- see
    # shell_generator._build_divider's callback.
    hits = [r for r in rows if 0.75 * c.INTERIOR_WIDTH <= r.span <= c.INTERIOR_WIDTH + 1.0]
    assert len(hits) == 1
    dy_from_bottom = piece.bbox.ymax - hits[0].center
    shelf_mid_local_y = (c.SHELF_Z0 + T / 2) - c.FLOOR_TOP  # shell_generator's own formula
    # The divider's bottom edge also fingers (all 4 edges captive), so its
    # bbox.ymax extends T beyond the nominal bottom edge.
    expected = shelf_mid_local_y + T
    assert abs(dy_from_bottom - expected) <= 0.6, (
        f"divider shelf row is {dy_from_bottom:.2f}mm from bbox.ymax, expected {expected:.2f}"
    )


def test_top_panel_divider_row_position():
    piece = _piece(SHELL_SVG, "top panel")
    rows = su.hole_line_rows(_blue_holes(piece), T, axis="y")
    hits = [r for r in rows if 0.75 * c.INTERIOR_WIDTH <= r.span <= c.INTERIOR_WIDTH + 1.0]
    assert len(hits) == 1
    # Top panel's front edge is plain (no protrusion) -> bbox.xmin is a
    # clean box-X=DIVIDER_X0 anchor with no T correction needed.
    dx = hits[0].center - piece.bbox.xmin
    assert abs(dx - T / 2) <= 0.6, f"top panel divider row is {dx:.2f}mm from bbox.xmin, expected T/2"


# --- 6. Tooth alignment: the assembly-impossible mutation class --------------------
# A hole-ROW's aggregate span/center (checks above) can be right while the
# INDIVIDUAL dash pitch is wrong, or while the mating part's edge teeth
# don't line up with those dashes at all -- e.g. red-team M4 (top panel side
# edge changed from the BAY_LENGTH-pitched CompoundEdge to a plain full 'f'
# edge) still produces *some* finger teeth on that edge, just at the wrong
# pitch/count/position, invisible to every check above that never compares
# individual tooth positions between two different parts.

def test_top_panel_teeth_align_with_wall_top_panel_rows():
    tp = _piece(SHELL_SVG, "top panel")
    tp_offset = tp.bbox.xmin - c.DIVIDER_X0  # plain front edge anchor
    teeth = [
        x - tp_offset
        for x in su.edge_teeth_centers(tp, "top") + su.edge_teeth_centers(tp, "bottom")
    ]

    wall_dashes = []
    for side, mirror in WALL_SIDES:
        wall = _piece(SHELL_SVG, side)
        to_box_x = _wall_frame(wall, mirror)
        rows = su.hole_line_rows(_blue_holes(wall), T, axis="x")
        bay_hits = [r for r in rows if 0.75 * SHELF_LINE_NOMINAL <= r.span <= SHELF_LINE_NOMINAL + 1.0]
        top_row = min(bay_hits, key=lambda r: r.center)
        wall_dashes += _row_dash_positions(wall, T, top_row, "x", to_box_x)

    _assert_teeth_match(teeth, wall_dashes, "top panel side-edge teeth vs. wall top-panel rows")


def test_shelf_teeth_align_with_wall_shelf_rows():
    shelf = _piece(SHELL_SVG, "horizontal shelf", "shelf")
    shelf_offset = shelf.bbox.xmax - c.BAY_X1  # plain rear edge anchor
    teeth = [
        x - shelf_offset
        for x in su.edge_teeth_centers(shelf, "top") + su.edge_teeth_centers(shelf, "bottom")
    ]

    wall_dashes = []
    for side, mirror in WALL_SIDES:
        wall = _piece(SHELL_SVG, side)
        to_box_x = _wall_frame(wall, mirror)
        rows = su.hole_line_rows(_blue_holes(wall), T, axis="x")
        bay_hits = [r for r in rows if 0.75 * SHELF_LINE_NOMINAL <= r.span <= SHELF_LINE_NOMINAL + 1.0]
        shelf_row = max(bay_hits, key=lambda r: r.center)
        wall_dashes += _row_dash_positions(wall, T, shelf_row, "x", to_box_x)

    _assert_teeth_match(teeth, wall_dashes, "shelf side-edge teeth vs. wall shelf rows")


def test_divider_teeth_align_with_wall_divider_columns():
    """Vertical variant of the two checks above: the divider's own left/
    right edge teeth (Z-direction) must land on the walls' divider
    finger-hole COLUMN dashes."""
    divider = _piece(SHELL_SVG, "vertical divider", "divider")
    teeth = [
        divider.bbox.ymax - y
        for y in su.edge_teeth_centers(divider, "left") + su.edge_teeth_centers(divider, "right")
    ]

    wall_dashes = []
    for side, _mirror in WALL_SIDES:
        wall = _piece(SHELL_SVG, side)
        row = _wall_divider_row(wall)
        wall_dashes += _row_dash_positions(
            wall, T, row, "y", lambda y, wall=wall: _wall_box_z(wall, y)
        )

    _assert_teeth_match(teeth, wall_dashes, "divider side-edge teeth vs. wall divider columns")


# --- 7. Grip slot positions ---------------------------------------------------------

def test_lid_grip_slot_position():
    piece = _piece(LIDS_SVG, "sliding lid")
    matches = _cut_holes_matching(piece, c.LID_GRIP_SLOT["width"], c.LID_GRIP_SLOT["height"], tol=1.0)
    assert len(matches) == 1
    slot = matches[0].bbox
    dx = ((slot.xmin + slot.xmax) / 2) - piece.bbox.xmin
    assert abs(dx - c.LID_GRIP_SLOT["center_from_front"]) <= 0.6, (
        f"lid grip slot is {dx:.2f}mm from the front edge, expected "
        f"{c.LID_GRIP_SLOT['center_from_front']} (+/-0.6)"
    )
    piece_cy = (piece.bbox.ymin + piece.bbox.ymax) / 2
    slot_cy = (slot.ymin + slot.ymax) / 2
    assert abs(slot_cy - piece_cy) <= 0.6, "lid grip slot is not Y-centered on the lid"


@pytest.mark.parametrize("synonym", ["faceplate", "front"])
def test_drawer_grip_slot_position(synonym):
    piece = _piece(DRAWER_SVG, synonym)
    matches = _cut_holes_matching(piece, *GRIP_SLOT_SIZE, tol=1.0)
    assert len(matches) == 1
    slot = matches[0].bbox
    top_below = slot.ymin - piece.bbox.ymin
    assert abs(top_below - c.DRAWER_GRIP_SLOT["top_below_edge"]) <= 0.6, (
        f"{synonym}: grip slot is {top_below:.2f}mm below the top edge, expected "
        f"{c.DRAWER_GRIP_SLOT['top_below_edge']} (+/-0.6)"
    )
    piece_cx = (piece.bbox.xmin + piece.bbox.xmax) / 2
    slot_cx = (slot.xmin + slot.xmax) / 2
    assert abs(slot_cx - piece_cx) <= 0.6, f"{synonym}: grip slot is not X-centered"


# --- 8. Engraving position -----------------------------------------------------------

def test_engrave_position_on_right_wall():
    piece = _piece(SHELL_SVG, "right wall")
    reds = [h for h in piece.holes if su.normalize_color(h.stroke) == "red"]
    assert reds, "expected red engraving paths on the right wall"
    xs = [p.bbox.xmin for p in reds] + [p.bbox.xmax for p in reds]
    ys = [p.bbox.ymin for p in reds] + [p.bbox.ymax for p in reds]
    red_cx, red_cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2

    to_box_x = _wall_frame(piece, mirror=False)
    box_x = to_box_x(red_cx)
    box_z = _wall_box_z(piece, red_cy)
    assert abs(box_x - c.ENGRAVE_CENTER["x"]) <= 2.0, f"engrave center X={box_x:.2f}, expected {c.ENGRAVE_CENTER['x']}"
    assert abs(box_z - c.ENGRAVE_CENTER["z"]) <= 2.0, f"engrave center Z={box_z:.2f}, expected {c.ENGRAVE_CENTER['z']}"


# --- 9. Edge-polarity tripwire -------------------------------------------------------
# Not a geometric proof -- the checks above already prove the geometry.
# This is a cheap grep-level guard against a typo'd edge-type string (e.g.
# "eFeF" -> "eeee") landing on a part whose resulting misalignment happens
# not to trip any single positional tolerance above.

def test_edge_polarity_literals_present():
    shell_src = (
        Path(__file__).resolve().parent.parent / "src" / "faxbox" / "shell_generator.py"
    ).read_text()
    drawer_src = (
        Path(__file__).resolve().parent.parent / "src" / "faxbox" / "generate_drawers.py"
    ).read_text()

    # Front wall AND rear wall: full-height finger joints on both vertical
    # edges, plain top/bottom.
    assert shell_src.count('"eFeF"') == 2, "expected front wall + rear wall both using \"eFeF\""
    # Side wall front-edge CompoundEdge (finger below FRONT_WALL_TOP, plain
    # above it) -- both direction variants.
    assert '["e", "f"]' in shell_src
    assert '["f", "e"]' in shell_src
    # Bottom panel AND divider: fully captive on all 4 edges.
    assert shell_src.count('"ffff"') == 2, "expected bottom panel + divider both using \"ffff\""
    # Horizontal shelf: side edges finger, rear edge plain, front edge finger.
    assert '["f", "e", "f", "f"]' in shell_src

    # Drawer Front AND Back: side edges finger, bottom fingers, top open.
    assert drawer_src.count('"fFeF"') == 2, "expected drawer Front + Back both using \"fFeF\""
    # Drawer side walls: front/back-mating edges finger, bottom fingers, top open.
    assert '"ffef"' in drawer_src
    # Drawer Bottom: plain all around. (Faceplate was also a plain "eeee"
    # rectangularWall pre-#20; retention iteration 2 gave it a real
    # protruding nub on both Y edges, which Boxes.py's edge classes can't
    # express -- generate_drawers.py now hand-draws its whole outer boundary
    # instead of calling rectangularWall with an edge-type string at all, so
    # there is no "eeee" literal left to find for it. See the flagged
    # deviation on test_faceplate_blank_size above for the same root cause.)
    assert drawer_src.count('"eeee"') == 1, "expected drawer Bottom using \"eeee\""
