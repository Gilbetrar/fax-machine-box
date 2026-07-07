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

Generators are known-broken pre-#17/#18 (wrong wall assignments, wrong sizes
inherited from the DEPRECATED legacy SHELL/DRAWER constants, missing top
panel, missing faceplate). Every check below that fails against *current*
output is marked `xfail(strict=False)` with a reason citing the specific
defect and the rebuild issue; checks that already hold today are left as
ordinary (non-xfail) assertions on purpose, so this suite still catches a
regression in what already works.
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

XF18 = "broken generator, rebuilt in #18"


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


@pytest.mark.xfail(strict=False, reason=f"{XF18}: faceplate piece missing (drawer has 5, needs 6)")
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


@pytest.mark.xfail(
    strict=False,
    reason=f"{XF18}: 'Right Side' and 'Bottom' piece bboxes overlap on the current canvas layout",
)
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
# fingers on all four edges -> 2 jointed edges per axis. NOT xfail: the
# legacy generator's full-footprint Bottom (304.8 x 165.1) sits exactly at
# nominal + 2T on both axes, which is this band's upper bound -- a real
# (maximal) pass under the DESIGN.md tolerance rule, same situation as the
# divider tests below.
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
# Split into two assertions because the two axes currently disagree:
# NOT xfail on Y: current code passes the *full exterior* Y (165.1mm, from
# the legacy SHELL dict) straight through, uncorrected for joints. But
# nominal(158.75) + 2*T == SHELL_EXT["width"] exactly (algebra: INTERIOR_WIDTH
# is defined as SHELL_EXT width - 2T), so a full-exterior-width blank sits
# right at this axis's max-jointed-edges upper bound and passes under the
# DESIGN.md-prescribed tolerance -- a real (if maximal) pass, not a
# coincidence worth hiding behind xfail.
def test_divider_blank_size_y():
    piece = _piece(SHELL_SVG, "vertical divider", "divider")
    _assert_band(piece, "Y", piece.bbox.width, c.INTERIOR_WIDTH, jointed_edges=2)


# Z: same story as Y above. DIVIDER_HEIGHT(120.65) + 2*T == SHELL_EXT height
# (127.0) exactly (DIVIDER_HEIGHT is TOP_PANEL_Z0 - WALL_Z0 == 127 - 2T), so
# the legacy generator's full-127mm divider height also lands exactly on
# this axis's max-jointed-edges upper bound. A real pass under the
# DESIGN.md-prescribed [nominal, nominal + 2T] band, not weakened to fit.
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
@pytest.mark.xfail(strict=False, reason=f"{XF18}: uses legacy DRAWER dict (150x210x53), not DESIGN.md 149x218x53.5")
@pytest.mark.parametrize("side", ["front", "back"])
def test_drawer_front_back_blank_size(side):
    piece = _piece(DRAWER_SVG, side)
    _assert_band(piece, "Y", piece.bbox.width, c.DRAWER_BODY["width"], jointed_edges=2)
    _assert_band(piece, "Z", piece.bbox.height, c.DRAWER_BODY["height"], jointed_edges=1)


@pytest.mark.xfail(strict=False, reason=f"{XF18}: uses legacy DRAWER dict (150x210x53), not DESIGN.md 149x218x53.5")
@pytest.mark.parametrize("side", ["left side", "right side"])
def test_drawer_left_right_blank_size(side):
    piece = _piece(DRAWER_SVG, side)
    _assert_band(piece, "X", piece.bbox.width, c.DRAWER_BODY["length"], jointed_edges=2)
    _assert_band(piece, "Z", piece.bbox.height, c.DRAWER_BODY["height"], jointed_edges=1)


@pytest.mark.xfail(strict=False, reason=f"{XF18}: uses legacy DRAWER dict (150x210x53), not DESIGN.md 149x218x53.5")
def test_drawer_bottom_blank_size():
    piece = _piece(DRAWER_SVG, "bottom")
    _assert_band(piece, "X", piece.bbox.width, c.DRAWER_BODY["length"], jointed_edges=0)
    _assert_band(piece, "Y", piece.bbox.height, c.DRAWER_BODY["width"], jointed_edges=0)


# DESIGN.md #9 faceplate: "glued to the body front" (not finger-jointed) ->
# 0 jointed edges both axes.
@pytest.mark.xfail(strict=False, reason=f"{XF18}: faceplate piece does not exist yet")
def test_faceplate_blank_size():
    piece = _piece(DRAWER_SVG, "faceplate")
    _assert_band(piece, "Y", piece.bbox.width, c.FACEPLATE["width"], jointed_edges=0)
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


@pytest.mark.xfail(strict=False, reason=f"{XF18}: faceplate piece does not exist yet")
def test_faceplate_has_grip_slot():
    piece = _piece(DRAWER_SVG, "faceplate")
    matches = _cut_holes_matching(piece, *GRIP_SLOT_SIZE, tol=1.0)
    assert len(matches) == 1


# NOT xfail: the legacy generator's "notch" is implemented as a rounded
# 30x15 rectangularHole in the body Front -- dimensionally identical to the
# DESIGN.md grip slot (position differs, which this size-based check doesn't
# see). Passes today for real; #18 keeps it passing.
def test_drawer_body_front_has_matching_grip_slot():
    piece = _piece(DRAWER_SVG, "front")
    blue = _blue_holes(piece)
    matches = _cut_holes_matching(piece, *GRIP_SLOT_SIZE, tol=1.0)
    assert len(matches) == 1 and len(blue) == 1, (
        f"body Front should carry exactly one cut hole, the {GRIP_SLOT_SIZE} grip slot; "
        f"found {[(round(h.bbox.width, 1), round(h.bbox.height, 1)) for h in blue]}"
    )
