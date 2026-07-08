"""Retention (iteration 3, issue #20 red-team) tests: parse the ACTUAL SVGs
the same way test_svg_geometry.py does (never trusting a predefined mental
model of the geometry). Rewritten wholesale for the iteration-3 mechanisms
(mutation testing on the iteration-2 version of this file let 3 of 8 fatal
mutations through -- see the mutation-gate table in the PR description).

Rules this rewrite follows throughout:
- EXISTENCE first: every check parses the real SVG and asserts the feature
  (nub, ramp, release cut, catch hole) actually exists on the actual part
  before measuring it -- a part drawn as a plain rectangle must fail, not
  vacuously pass a conditional.
- FIXED PHYSICAL BOUNDS, not config echoes: assertions compare a measured
  SVG quantity against a LITERAL (0.8, 1.5, 2.0, 4.9, ...) or an
  independently-derived quantity, never the same config constant the
  generator itself drew from -- comparing a measurement to the value that
  produced it can't catch a wrong value, only a crashed generator.
- BLANK INVARIANTS: the faceplate is back to its exact v1 blank (no nub);
  test_svg_geometry.py's restored test_faceplate_blank_size covers the
  overall dimension, this file adds a shape-level check (no ramp/diagonal
  segments at all) that a size-only check can't express.
"""

from __future__ import annotations

import math
import subprocess
import sys
from pathlib import Path

import pytest
import svgpathtools

from faxbox import config as c

import svg_utils as su

pytestmark = [pytest.mark.usefixtures("regenerate_svgs")]

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "output"
SHELL_SVG = OUTPUT_DIR / "outer_shell.svg"
DRAWER_SVG = OUTPUT_DIR / "drawer.svg"
LIDS_SVG = OUTPUT_DIR / "lids.svg"

T = c.MATERIAL_THICKNESS
LID_SLOT_LENGTH = c.LID_SLOT_X_END - T
WALL_SIDES = [("right wall", False), ("left wall", True)]
DRAWER_SIDES = ["left side", "right side"]

# Physical literals this file measures against (never a config echo of the
# same value the generator used to draw the feature):
LID_VERTICAL_PLAY = 0.8          # DESIGN.md: LID_SLOT_VERTICAL_CLEARANCE
DRAWER_OPENING_VERTICAL_PLAY = 1.5  # DESIGN.md: drawer body <-> opening height clearance
DRAWER_LATERAL_FLOAT_PER_SIDE = 4.9  # DESIGN.md: "~4.9mm/side by design"
MAX_STRAIN_PCT = 2.0             # plywood cracks ~1.5-2% (DESIGN.md, FIX1)
MIN_RAMP_DEG = 20.0
MAX_RAMP_DEG = 60.0


@pytest.fixture(scope="session")
def retention_coupon_svg():
    subprocess.run(
        [sys.executable, "-m", "faxbox.calibration"],
        check=True, cwd=REPO_ROOT, capture_output=True,
    )
    path = OUTPUT_DIR / "retention_coupon.svg"
    assert path.exists(), "faxbox.calibration did not produce output/retention_coupon.svg"
    return path


def _piece(svg_path, *synonyms):
    pieces = su.design_pieces(svg_path)
    found = su.find_piece_by_label(pieces, *synonyms)
    assert found is not None, f"no piece labeled like {synonyms!r} found in {svg_path.name}"
    return found


def _blue_holes(piece):
    return [h for h in piece.holes if su.normalize_color(h.stroke) == "blue"]


def _cut_holes_matching(piece, width, height, tol=1.0):
    return [h for h in _blue_holes(piece) if h.bbox.dims_match(width, height, tol=tol)]


def _wall_box_z(wall, y: float) -> float:
    """Same anchor-free mapping as test_svg_geometry.py's _wall_box_z: the
    side walls' top/bottom edges are never jointed, so bbox.ymin is exactly
    box Z = WALL_HEIGHT with no correction needed."""
    return c.WALL_HEIGHT - (y - wall.bbox.ymin)


def _wall_frame(wall, mirror: bool):
    """Same anchor as test_svg_geometry.py's _wall_frame: the divider
    finger-hole column's X center is box X DIVIDER_MID_BOX_X on both walls."""
    rows = su.hole_line_rows(_blue_holes(wall), T, axis="y")
    divider_nominal = c.DIVIDER_HEIGHT
    hits = [r for r in rows if 0.75 * divider_nominal <= r.span <= divider_nominal + 1.0]
    assert len(hits) == 1
    col = hits[0].center
    divider_mid_box_x = (c.DIVIDER_X0 + c.DIVIDER_X1) / 2
    sign = -1.0 if mirror else 1.0

    def to_box_x(x: float) -> float:
        return divider_mid_box_x + sign * (x - col)

    return to_box_x


def _lines(path_d: str) -> list[svgpathtools.Line]:
    return [seg for seg in svgpathtools.parse_path(path_d) if isinstance(seg, svgpathtools.Line)]


def _nub_bump_geometry(path_d: str) -> dict:
    """Extract a ramped-nub bump's geometry from ANY closed path that
    contains it -- a hole (mechanism A's lid-slot-with-nub) or an outer
    boundary (mechanism B's drawer-side nub) -- by finding the exactly-2
    non-axis-aligned ("diagonal") Line segments on the path: these are the
    nub's two ramps, since every OTHER segment on these designs (slot/
    panel edges, finger teeth, rounded corners drawn as arcs) is axis-
    aligned or not a Line at all. Fails loudly (assertion) if that
    assumption doesn't hold -- e.g. a squared-off nub (no ramp) or a
    missing nub leaves 0 or the wrong count of diagonal segments.

    Returns a dict with base_left/base_right/top_left/top_right (X coords,
    SVG space), base_y/top_y (SVG Y of the flat base plane / bump peak),
    and ramp1_len/ramp2_len (the two ramp segment lengths, for slope
    checks).
    """
    all_lines = _lines(path_d)
    diagonal = [
        s for s in all_lines
        if abs(s.start.real - s.end.real) > 1e-6 and abs(s.start.imag - s.end.imag) > 1e-6
    ]
    assert len(diagonal) == 2, (
        f"expected exactly 2 ramp (non-axis-aligned) segments forming a nub, "
        f"found {len(diagonal)} -- a squared-off nub or a missing nub would both "
        f"fail this differently than intended, so this must be exactly 2"
    )
    d1, d2 = diagonal
    if (d1.start.real + d1.end.real) > (d2.start.real + d2.end.real):
        d1, d2 = d2, d1

    # Each ramp's own two endpoints are exactly {base_y, top_y} -- both
    # ramps share the SAME pair, so set intersection can't tell them apart.
    # Instead, count how often each Y value shows up across every
    # HORIZONTAL segment on the whole path: the flat baseline (floor runs,
    # finger teeth, ...) repeats at base_y many times, while the short flat
    # top of the bump is the only thing at top_y -- so top_y is the value
    # from this ramp's own endpoint pair that appears LESS often overall.
    horizontal_ys = [
        round(s.start.imag, 3) for s in all_lines if abs(s.start.imag - s.end.imag) < 1e-6
    ]
    y_counts: dict[float, int] = {}
    for y in horizontal_ys:
        y_counts[y] = y_counts.get(y, 0) + 1

    candidate_ys = {round(d1.start.imag, 3), round(d1.end.imag, 3)}
    top_y = min(candidate_ys, key=lambda y: y_counts.get(y, 0))

    def split(seg):
        pts = [(seg.start.real, seg.start.imag), (seg.end.real, seg.end.imag)]
        base = max(pts, key=lambda p: abs(round(p[1], 3) - top_y))
        top = min(pts, key=lambda p: abs(round(p[1], 3) - top_y))
        return base, top

    (base_left_x, base_y), (top_left_x, _) = split(d1)
    (base_right_x, base_y2), (top_right_x, _) = split(d2)

    return {
        "base_left": base_left_x, "base_right": base_right_x,
        "top_left": top_left_x, "top_right": top_right_x,
        "base_y": base_y, "base_y2": base_y2, "top_y": top_y,
        "ramp1_len": d1.length(), "ramp2_len": d2.length(),
    }


def _deepest_y_excluding_nub(path_d: str, top_y: float, tol: float = 0.5) -> float:
    """Max SVG-y (deepest point) across every Line segment's endpoints,
    excluding anything within `tol` of the nub's own peak (top_y) -- i.e.
    the next-deepest real feature on the boundary (for the drawer side
    wall, the finger tabs' own reach)."""
    ys = [
        y for seg in _lines(path_d) for y in (seg.start.imag, seg.end.imag)
        if abs(y - top_y) > tol
    ]
    assert ys, "no boundary points found outside the nub's own peak"
    return max(ys)


def _ramp_slope_degrees(bump: dict) -> tuple[float, float]:
    """Slope angle (from the flat base plane) of each ramp, in degrees."""
    rise = abs(bump["top_y"] - bump["base_y"])
    run1 = abs(bump["top_left"] - bump["base_left"])
    run2 = abs(bump["base_right"] - bump["top_right"])
    return math.degrees(math.atan2(rise, run1)), math.degrees(math.atan2(rise, run2))


# =============================================================================
# 1. Wall lid detent (mechanism A): existence, fixed bounds, ramp, mirror
# =============================================================================

def _find_wall_slot(side: str) -> tuple:
    piece = _piece(SHELL_SVG, side)
    matches = _cut_holes_matching(piece, LID_SLOT_LENGTH, c.LID_SLOT_HEIGHT, tol=0.5)
    assert len(matches) == 1, f"{side}: expected exactly 1 lid-slot hole, found {len(matches)}"
    return piece, matches[0]


@pytest.mark.parametrize("side,mirror", WALL_SIDES)
def test_wall_nub_exists_with_ramp_and_rises_past_lid_play(side, mirror):
    """EXISTENCE + FIXED BOUNDS: the wall's lid-slot hole must carry a real
    ramped nub (not a plain rectangle -- mutation (i)-equivalent for this
    mechanism), whose rise clears the lid's own 0.8mm vertical play by a
    real margin (mutation (a): LID_DETENT_ENGAGE 1.5->0.5 must fail this),
    and whose ramp is a genuine slope, not a squared-off nub (mutation
    (h): DETENT_RAMP_DEG->90)."""
    piece, slot = _find_wall_slot(side)
    bump = _nub_bump_geometry(slot.d)

    base_top_width = abs(bump["top_right"] - bump["top_left"])
    base_width = abs(bump["base_right"] - bump["base_left"])
    assert base_width > base_top_width, (
        f"{side}: nub base width ({base_width:.2f}) is not wider than its top "
        f"({base_top_width:.2f}) -- no ramp"
    )

    for angle in _ramp_slope_degrees(bump):
        assert MIN_RAMP_DEG <= angle <= MAX_RAMP_DEG, (
            f"{side}: ramp angle {angle:.1f} deg outside [{MIN_RAMP_DEG}, {MAX_RAMP_DEG}] "
            f"-- mutation-detectable square nub or too-shallow ramp"
        )

    floor_z = _wall_box_z(piece, bump["base_y"])
    nub_z = _wall_box_z(piece, bump["top_y"])
    rise = nub_z - floor_z
    assert rise >= LID_VERTICAL_PLAY + 0.4, (
        f"{side}: nub rise {rise:.2f}mm above the measured slot floor does not clear "
        f"the lid's own {LID_VERTICAL_PLAY}mm vertical play + 0.4mm margin"
    )
    # Direction sanity: the nub must rise INTO the slot (toward the ceiling),
    # not the reverse (mutation (b): wall nub flipped downward).
    ceiling_z = _wall_box_z(piece, slot.bbox.ymin)
    assert floor_z < ceiling_z, "sanity: measured floor should read a lower Z than the ceiling"
    assert floor_z < nub_z < ceiling_z, (
        f"{side}: nub top Z={nub_z:.2f} is not between the measured floor "
        f"({floor_z:.2f}) and ceiling ({ceiling_z:.2f}) -- nub may be inverted"
    )


@pytest.mark.parametrize("side,mirror", WALL_SIDES)
def test_wall_release_cut_exists_and_leaves_root_solid(side, mirror):
    """EXISTENCE: the cantilever release cut (cavity + severing slot) must
    actually exist near the nub (mutation (f): delete the wall release cut
    must fail this)."""
    piece = _piece(SHELL_SVG, side)
    _, slot = _find_wall_slot(side)
    bump = _nub_bump_geometry(slot.d)
    nub_cx = (bump["top_left"] + bump["top_right"]) / 2

    # The release cut sits just below the slot floor (smaller box Z, larger
    # SVG y): small rectangular holes within a few mm of the nub's own X,
    # spanning a compact Z band below the slot.
    floor_y = slot.bbox.ymax
    candidates = [
        h for h in _blue_holes(piece)
        if h.bbox.ymin >= floor_y - 0.5
        and abs((h.bbox.xmin + h.bbox.xmax) / 2 - nub_cx) <= 25.0
        and h.bbox.height <= 12.0
    ]
    assert len(candidates) >= 2, (
        f"{side}: expected >= 2 release-cut holes (cavity + sever) below the slot "
        f"floor near the nub, found {len(candidates)}"
    )
    widths = sorted(h.bbox.width for h in candidates)
    assert widths[0] <= 3.0, f"{side}: no narrow (sever) release-cut hole found: widths {widths}"
    assert widths[-1] >= 10.0, f"{side}: no wide (cavity) release-cut hole found: widths {widths}"


def test_wall_detents_are_true_mirrors():
    box_x_by_side = {}
    for side, mirror in WALL_SIDES:
        piece, slot = _find_wall_slot(side)
        bump = _nub_bump_geometry(slot.d)
        nub_x_svg = (bump["top_left"] + bump["top_right"]) / 2
        to_box_x = _wall_frame(piece, mirror)
        box_x_by_side[side] = to_box_x(nub_x_svg)

    right_x, left_x = box_x_by_side["right wall"], box_x_by_side["left wall"]
    assert abs(right_x - left_x) <= 0.6, (
        f"wall nubs land at different box X positions: right={right_x:.2f}, "
        f"left={left_x:.2f} -- mirroring is broken (mutation (d))"
    )


@pytest.mark.parametrize("side,mirror", WALL_SIDES)
def test_wall_nub_strain_within_crack_threshold(side, mirror):
    """Beam strain formula eps = 3*w*delta/(2*L^2), computed ENTIRELY from
    measured SVG dimensions (root-to-nub span from the release cut's own
    measured extent, rise from the nub bump itself), not config echoes."""
    piece = _piece(SHELL_SVG, side)
    _, slot = _find_wall_slot(side)
    bump = _nub_bump_geometry(slot.d)
    nub_cx = (bump["top_left"] + bump["top_right"]) / 2
    floor_y = slot.bbox.ymax

    cavity_candidates = [
        h for h in _blue_holes(piece)
        if h.bbox.ymin >= floor_y - 0.5
        and abs((h.bbox.xmin + h.bbox.xmax) / 2 - nub_cx) <= 25.0
        and h.bbox.width >= 10.0
    ]
    assert len(cavity_candidates) == 1, (
        f"{side}: expected exactly 1 wide (cavity) release-cut hole, found {len(cavity_candidates)}"
    )
    cavity = cavity_candidates[0].bbox
    root_x = cavity.xmax if abs(cavity.xmax - nub_cx) > abs(cavity.xmin - nub_cx) else cavity.xmin
    span = abs(root_x - nub_cx)
    assert span > 5.0, f"{side}: measured root-to-nub span implausibly small ({span:.2f})"

    rise = abs(bump["top_y"] - bump["base_y"])
    w = cavity.height  # measured beam/cavity cross-section width
    eps = 3 * w * rise / (2 * span ** 2) * 100
    assert eps <= MAX_STRAIN_PCT, (
        f"{side}: measured beam strain {eps:.2f}% exceeds the {MAX_STRAIN_PCT}% "
        f"plywood crack threshold (span={span:.2f}, rise={rise:.2f}, w={w:.2f})"
    )


# =============================================================================
# 2. Lid mating notch
# =============================================================================

def test_lid_notch_aligns_with_wall_nub_when_closed():
    lid = _piece(LIDS_SVG, "sliding lid")
    notch_matches = [
        h for h in _blue_holes(lid)
        if abs(h.bbox.width - c.LID_NOTCH_WIDTH) <= 1.0
        and (abs(h.bbox.ymin - lid.bbox.ymin) <= 0.3 or abs(h.bbox.ymax - lid.bbox.ymax) <= 0.3)
    ]
    assert len(notch_matches) == 2, (
        f"expected 2 edge-open notches (one per long edge) on the sliding lid, "
        f"found {len(notch_matches)}"
    )

    piece, slot = _find_wall_slot("right wall")
    bump = _nub_bump_geometry(slot.d)
    to_box_x = _wall_frame(piece, mirror=False)
    nub_box_x = to_box_x((bump["top_left"] + bump["top_right"]) / 2)

    for notch in notch_matches:
        notch_cx = (notch.bbox.xmin + notch.bbox.xmax) / 2
        lid_local_x = notch_cx - lid.bbox.xmin
        box_x_when_closed = lid_local_x + c.LID_CLOSED_FRONT_X
        assert abs(box_x_when_closed - nub_box_x) <= 0.6, (
            f"notch maps to box X={box_x_when_closed:.2f} when closed, but the "
            f"MEASURED wall nub is at box X={nub_box_x:.2f} (mutation (c): notch "
            f"shifted +5mm must fail this independent-datum comparison)"
        )

        lid_slot_engagement = (c.SLIDING_LID["width"] - c.INTERIOR_WIDTH) / 2
        depth = notch.bbox.height
        assert depth >= lid_slot_engagement + 0.5, (
            f"notch depth {depth:.2f} does not clear lid-slot engagement "
            f"{lid_slot_engagement:.2f} + 0.5mm margin"
        )


# =============================================================================
# 3. Drawer side-wall flexure (mechanism B, iteration 3)
# =============================================================================

@pytest.mark.parametrize("side", DRAWER_SIDES)
def test_drawer_side_nub_exists_with_ramp_and_clears_opening_play(side):
    """EXISTENCE + FIXED BOUNDS: each drawer side wall must carry a real
    ramped nub protruding past its own bottom edge (mutation (i): a plain
    rectangle must fail), whose protrusion clears the drawer's own 1.5mm
    opening vertical clearance by a real margin (mutation (e):
    DRAWER_DETENT_ENGAGE 2.2->1.0 must fail this)."""
    piece = _piece(DRAWER_SVG, side)
    bump = _nub_bump_geometry(piece.outer.d)

    base_top_width = abs(bump["top_right"] - bump["top_left"])
    base_width = abs(bump["base_right"] - bump["base_left"])
    assert base_width > base_top_width, (
        f"{side}: nub base width ({base_width:.2f}) is not wider than its top "
        f"({base_top_width:.2f}) -- no ramp"
    )
    for angle in _ramp_slope_degrees(bump):
        assert MIN_RAMP_DEG <= angle <= MAX_RAMP_DEG, (
            f"{side}: ramp angle {angle:.1f} deg outside [{MIN_RAMP_DEG}, {MAX_RAMP_DEG}]"
        )

    # The nub's own protrusion BEYOND the neighboring finger tabs' own reach
    # (the piece's deepest point EXCLUDING the nub itself, since the nub is
    # now the overall bbox extreme) is what matters -- not the nub's total
    # depth from the plain zone's local y=0 baseline (bump["base_y"], which
    # sits ABOVE (shallower than) the tab reach, since the plain zone has
    # no tab there at all -- see generate_drawers.py's _build_side).
    tab_reach_y = _deepest_y_excluding_nub(piece.outer.d, bump["top_y"])
    protrusion = bump["top_y"] - tab_reach_y
    assert protrusion > 0, (
        f"{side}: nub top is not deeper than the piece's own tab reach "
        f"(top_y={bump['top_y']:.2f}, tab_reach={tab_reach_y:.2f}) -- nub may be inverted"
    )
    assert protrusion >= DRAWER_OPENING_VERTICAL_PLAY + 0.5, (
        f"{side}: measured nub protrusion past the piece's own tab-reach depth "
        f"({protrusion:.2f}mm) does not clear the drawer's {DRAWER_OPENING_VERTICAL_PLAY}mm "
        f"opening vertical clearance + 0.5mm margin"
    )


@pytest.mark.parametrize("side", DRAWER_SIDES)
def test_drawer_side_release_cut_exists(side):
    """EXISTENCE: the cantilever release cut (cavity + sever) near the nub
    (mutation (i) catch, distinct from the boundary-shape check above)."""
    piece = _piece(DRAWER_SVG, side)
    bump = _nub_bump_geometry(piece.outer.d)
    nub_cx = (bump["top_left"] + bump["top_right"]) / 2

    candidates = [
        h for h in _blue_holes(piece)
        if abs((h.bbox.xmin + h.bbox.xmax) / 2 - nub_cx) <= 30.0
        and h.bbox.height <= 12.0
    ]
    assert len(candidates) >= 2, (
        f"{side}: expected >= 2 release-cut holes (cavity + sever) near the nub, "
        f"found {len(candidates)}"
    )
    widths = sorted(h.bbox.width for h in candidates)
    assert widths[0] <= 3.0, f"{side}: no narrow (sever) release-cut hole found: widths {widths}"
    assert widths[-1] >= 15.0, f"{side}: no wide (cavity) release-cut hole found: widths {widths}"


@pytest.mark.parametrize("side", DRAWER_SIDES)
def test_drawer_side_nub_clear_of_front_finger_joints(side):
    """The nub (and its release cut) must stay >= 15mm clear of the
    front-edge finger joints (the vertical edge at the piece's own X
    extreme nearest the nub)."""
    piece = _piece(DRAWER_SVG, side)
    bump = _nub_bump_geometry(piece.outer.d)
    nub_cx = (bump["top_left"] + bump["top_right"]) / 2

    dist_from_left_edge = nub_cx - piece.bbox.xmin
    dist_from_right_edge = piece.bbox.xmax - nub_cx
    nearest_edge_dist = min(dist_from_left_edge, dist_from_right_edge)
    assert nearest_edge_dist >= 15.0, (
        f"{side}: nub is only {nearest_edge_dist:.2f}mm from the nearest end of the "
        f"panel -- must clear the front finger joints by >= 15mm"
    )


@pytest.mark.parametrize("side", DRAWER_SIDES)
def test_drawer_side_strain_within_crack_threshold(side):
    """Beam strain formula, computed from measured SVG dimensions."""
    piece = _piece(DRAWER_SVG, side)
    bump = _nub_bump_geometry(piece.outer.d)
    nub_cx = (bump["top_left"] + bump["top_right"]) / 2

    cavity_candidates = [
        h for h in _blue_holes(piece)
        if abs((h.bbox.xmin + h.bbox.xmax) / 2 - nub_cx) <= 30.0
        and h.bbox.width >= 15.0
    ]
    assert len(cavity_candidates) == 1, (
        f"{side}: expected exactly 1 wide (cavity) release-cut hole, found {len(cavity_candidates)}"
    )
    cavity = cavity_candidates[0].bbox
    root_x = cavity.xmax if abs(cavity.xmax - nub_cx) > abs(cavity.xmin - nub_cx) else cavity.xmin
    span = abs(root_x - nub_cx)
    assert span > 5.0, f"{side}: measured root-to-nub span implausibly small ({span:.2f})"

    # The strain-relevant deflection is the nub's protrusion PAST the
    # surrounding tab reach -- the beam only has to flex that far to become
    # flush with its neighbors, not all the way from the (already-recessed)
    # plain-zone baseline -- see the protrusion test above for the same
    # reasoning.
    tab_reach_y = _deepest_y_excluding_nub(piece.outer.d, bump["top_y"])
    rise = bump["top_y"] - tab_reach_y
    assert rise > 0
    w = cavity.height
    eps = 3 * w * rise / (2 * span ** 2) * 100
    assert eps <= MAX_STRAIN_PCT, (
        f"{side}: measured beam strain {eps:.2f}% exceeds the {MAX_STRAIN_PCT}% "
        f"plywood crack threshold (span={span:.2f}, rise={rise:.2f}, w={w:.2f})"
    )


def _measured_tip_rise(engage: float, overhang: float, span: float) -> float:
    """Local (test-only) re-implementation of config._tip_rise's formula --
    deliberately NOT imported from faxbox.config, so this test's oracle is
    independent of the helper that sizes DRAWER_DETENT_CAVITY (issue #20
    pass-3 F3: comparing a measurement to the value that produced it can't
    catch a wrong value)."""
    return engage * (1 + 3 * overhang / (2 * span))


@pytest.mark.parametrize("side", DRAWER_SIDES)
def test_drawer_side_cavity_clears_measured_tip_rise(side):
    """F3 (issue #20 pass-3, MAJOR): the drawer flexure's free tip rises
    MORE than the nub's own designed engagement, because the severed free
    tip overhangs past the nub's own load point toward the beam's free end
    -- a beam-deflection effect the previous revision's shared
    DETENT_CLEARANCE (2.5mm, sized only to the nub's own rise) did not
    account for: computed tip rise ~2.97mm > that 2.5mm cavity, so the beam
    would BIND against the cavity's far wall at ~1.85mm of nub lift,
    short of the designed 2.2mm engagement (test_drawer_side_strain_
    within_crack_threshold, above, only checks bending STRAIN -- it does
    not catch a too-shallow cavity, since the beam can be well within its
    crack threshold and still physically bind).

    Computes the tip rise ENTIRELY from measured SVG dimensions (nub
    position, root position, severed free-tip position, nub's own rise)
    via a LOCAL copy of the tip-rise formula (not importing DRAWER_DETENT_
    CAVITY / DRAWER_DETENT_TIP_RISE from config), then asserts the beam's
    own measured clearance cavity is deep enough that it won't bind --
    catches e.g. a reversion of DRAWER_DETENT_CAVITY back to the old
    shared 2.5mm value.
    """
    piece = _piece(DRAWER_SVG, side)
    bump = _nub_bump_geometry(piece.outer.d)
    nub_cx = (bump["top_left"] + bump["top_right"]) / 2

    cavity_candidates = [
        h for h in _blue_holes(piece)
        if abs((h.bbox.xmin + h.bbox.xmax) / 2 - nub_cx) <= 30.0
        and h.bbox.width >= 15.0
    ]
    assert len(cavity_candidates) == 1, (
        f"{side}: expected exactly 1 wide (cavity) release-cut hole, found {len(cavity_candidates)}"
    )
    cavity = cavity_candidates[0].bbox
    root_x = cavity.xmax if abs(cavity.xmax - nub_cx) > abs(cavity.xmin - nub_cx) else cavity.xmin
    span = abs(root_x - nub_cx)
    assert span > 5.0, f"{side}: measured root-to-nub span implausibly small ({span:.2f})"

    sever_candidates = [
        h for h in _blue_holes(piece)
        if abs((h.bbox.xmin + h.bbox.xmax) / 2 - nub_cx) <= 30.0
        and h.bbox.width <= 3.0
    ]
    assert len(sever_candidates) == 1, (
        f"{side}: expected exactly 1 narrow (sever) release-cut hole, found {len(sever_candidates)}"
    )
    sever = sever_candidates[0].bbox
    # The beam's TRUE free tip is the sever cut's edge CLOSER to the root --
    # the opposite edge disconnects into non-load-bearing material (see
    # config._tip_rise's docstring / DESIGN.md's "Retention" section).
    free_tip_x = sever.xmax if abs(sever.xmax - root_x) < abs(sever.xmin - root_x) else sever.xmin
    overhang = abs(nub_cx - free_tip_x)
    assert overhang > 0.5, f"{side}: measured tip overhang implausibly small ({overhang:.2f})"

    tab_reach_y = _deepest_y_excluding_nub(piece.outer.d, bump["top_y"])
    engage = bump["top_y"] - tab_reach_y
    assert engage > 0

    computed_tip_rise = _measured_tip_rise(engage, overhang, span)
    available_clearance = cavity.height
    assert available_clearance >= computed_tip_rise - 0.1, (
        f"{side}: measured cavity clearance ({available_clearance:.2f}mm) is less "
        f"than the computed free-tip rise ({computed_tip_rise:.2f}mm at engage="
        f"{engage:.2f}, overhang={overhang:.2f}, span={span:.2f}) -- the beam "
        f"would BIND against the cavity's far wall before reaching full engagement"
    )


# =============================================================================
# 4. Faceplate BLANK INVARIANT: back to the exact v1 plain rectangle
# =============================================================================

def test_faceplate_has_no_nub_or_ramp():
    """The faceplate's iteration-2 detent is REMOVED entirely (FIX1): its
    outer boundary must be a plain rectangle with zero diagonal (ramp)
    segments -- test_svg_geometry.py's restored test_faceplate_blank_size
    covers the overall v1 dimension (150.9mm); this covers the SHAPE, which
    a size-only check can't (a reintroduced nub whose footprint still fits
    inside a slightly-loose band would pass a size check but not this)."""
    piece = _piece(DRAWER_SVG, "faceplate")
    diagonal = [
        s for s in _lines(piece.outer.d)
        if abs(s.start.real - s.end.real) > 1e-6 and abs(s.start.imag - s.end.imag) > 1e-6
    ]
    assert diagonal == [], (
        f"faceplate outer boundary has {len(diagonal)} non-axis-aligned segment(s) -- "
        f"expected a plain v1 rectangle with none"
    )


def test_drawer_side_blank_height_excluding_nub_matches_v1():
    """BLANK INVARIANT: the side wall's height, EXCLUDING the nub's own
    local protrusion (i.e. up to the finger tabs' own reach, the v1 value),
    measured in SVG-space -- distinct from test_svg_geometry.py's
    tolerance-banded bbox check (which the nub-inclusive height also
    happens to pass, since the band's slack absorbs it)."""
    for side in DRAWER_SIDES:
        piece = _piece(DRAWER_SVG, side)
        bump = _nub_bump_geometry(piece.outer.d)
        # The tab-reach boundary (v1's own bottom edge, the SAME depth the
        # neighboring finger tabs reach) is the deepest point on the
        # boundary EXCLUDING the nub itself (which is now the overall bbox
        # extreme) -- NOT bump["base_y"], the plain zone's own local y=0
        # baseline, which sits shallower still (no tab there at all).
        tab_reach_y = _deepest_y_excluding_nub(piece.outer.d, bump["top_y"])
        height_excl_nub = tab_reach_y - piece.bbox.ymin
        v1_band_lo, v1_band_hi = su.expected_band(c.DRAWER_BODY["height"], jointed_edges=1, thickness=T)
        assert v1_band_lo <= height_excl_nub <= v1_band_hi, (
            f"{side}: blank height excluding the nub ({height_excl_nub:.2f}) outside "
            f"the v1 band [{v1_band_lo:.2f}, {v1_band_hi:.2f}]"
        )


# =============================================================================
# 5. Catch holes (bottom panel + shelf)
# =============================================================================

@pytest.mark.parametrize("host,synonyms", [
    ("bottom panel", ("bottom",)),
    ("shelf", ("horizontal shelf", "shelf")),
])
def test_catch_holes_exist_with_fixed_y_span(host, synonyms):
    """EXISTENCE + FIXED BOUNDS: two catch holes per host panel (one per
    drawer side), each with Y-span >= nub thickness + both drawers' full
    lateral float (LITERALS, mutation (j): catch hole Y-width halved must
    fail this)."""
    piece = _piece(SHELL_SVG, *synonyms)
    min_span = T + 2 * DRAWER_LATERAL_FLOAT_PER_SIDE
    candidates = [
        h for h in _blue_holes(piece)
        if h.bbox.width < h.bbox.height  # narrow-X, wide-Y (unlike finger-hole rows)
        and 8.0 <= h.bbox.width <= 16.0
        and h.bbox.height >= min_span
    ]
    assert len(candidates) == 2, (
        f"{host}: expected exactly 2 catch holes with Y-span >= {min_span:.2f}mm "
        f"(T + 2*{DRAWER_LATERAL_FLOAT_PER_SIDE}mm), found {len(candidates)}"
    )


def test_catch_holes_at_same_box_x_on_both_panels():
    """The bottom panel's and shelf's catch holes must land at the SAME box
    X (both drawers are identical, closed at the same relative position)."""
    bottom = _piece(SHELL_SVG, "bottom")
    shelf = _piece(SHELL_SVG, "horizontal shelf", "shelf")
    min_span = T + 2 * DRAWER_LATERAL_FLOAT_PER_SIDE

    def catch_holes(piece):
        return [
            h for h in _blue_holes(piece)
            if h.bbox.width < h.bbox.height and 8.0 <= h.bbox.width <= 16.0
            and h.bbox.height >= min_span
        ]

    bottom_holes = catch_holes(bottom)
    shelf_holes = catch_holes(shelf)
    assert len(bottom_holes) == 2 and len(shelf_holes) == 2

    # Bottom panel: fingers protrude T on all 4 edges (DESIGN.md #1), so
    # bbox.xmin sits at box X = 0 exactly (same anchor as
    # test_svg_geometry.py's test_bottom_panel_divider_row_position) -- box
    # X = measured - bbox.xmin directly.
    # Shelf: the REAR edge (local x=BAY_LENGTH) is plain ("e", DESIGN.md
    # #6 -- "rear edge plain, butting the rear wall"), so bbox.xmax sits at
    # box X = BAY_X1 exactly with no tab to correct for (the FRONT/divider
    # edge is the jointed one here, so bbox.xmin is not a clean anchor).
    bottom_box_xs = sorted((h.bbox.xmin + h.bbox.xmax) / 2 - bottom.bbox.xmin for h in bottom_holes)
    shelf_box_xs = sorted(
        c.BAY_X1 - (shelf.bbox.xmax - (h.bbox.xmin + h.bbox.xmax) / 2) for h in shelf_holes
    )
    for bx, sx in zip(bottom_box_xs, shelf_box_xs):
        assert abs(bx - sx) <= 0.6, (
            f"bottom-panel catch hole at box X={bx:.2f} does not match shelf's "
            f"catch hole at box X={sx:.2f} -- both drawers close to the same position"
        )


def test_catch_hole_registers_with_nub_via_independent_datums():
    """F4 (issue #20 pass-3, CRITICAL): catch-hole <-> nub registration was
    previously untested end-to-end -- the pass-2 critic's mutation
    `CATCH_HOLE_X += 5.0` stayed green against every other test in this
    file, because nothing computed the nub's closed-position box-X
    INDEPENDENTLY of the very formula (DRAWER_FRONT_INNER_FACE_CLOSED_X -
    DRAWER_DETENT_NUB_X) that drew the catch hole -- comparing a
    measurement to the config value that produced it can't catch a wrong
    value, only a crashed generator.

    Datums, matching DESIGN.md's own registration derivation, but each
    combined from a MEASUREMENT (not a config echo of CATCH_HOLE_X or
    DRAWER_DETENT_NUB_X, the two values a registration bug would touch)
    plus stable, unrelated bay-fit constants (BAY_X1 "rear-wall plane",
    BAY_LENGTH -- shell/bay geometry with nothing to do with retention
    specifically):
    - drawer body length: MEASURED from drawer.svg's own "Bottom" piece (a
      plain, un-jointed "eeee" rectangle -- generate_drawers.py -- so its
      bbox is the body's true external footprint with zero tab-protrusion
      ambiguity, unlike the finger-jointed side panels the nub itself is
      cut into).
    - flexure X-position within the side (the faceplate-recess-relative
      "nub position" datum): MEASURED as that SAME Bottom piece's own
      nub-clearance slot center (F2 fix, generate_drawers.py) -- also a
      plain, un-jointed rectangularHole, anchored to the exact same
      unambiguous local x=0 as the body-length measurement above. The slot
      is deliberately centered on the nub, so its measured center is a
      legitimate, precise stand-in for the nub's own X position that
      avoids the jointed side panel's up-to-T tab-position ambiguity.

    Asserts the SHELL's catch hole X-span CONTAINS the independently-
    computed nub X-span (at the nub's floor-plane cross-section --
    NUB_WIDTH_AT_FLOOR_PLANE, the fixed physical width that actually
    threads through the hole, not a mutation target) with <= 1.0mm total
    slop.
    """
    bottom_drawer = _piece(DRAWER_SVG, "bottom")
    body_length = bottom_drawer.bbox.width  # measured, NOT c.DRAWER_BODY["length"]

    slot_candidates = [
        h for h in _blue_holes(bottom_drawer)
        if h.bbox.width > h.bbox.height
        and 15.0 <= h.bbox.width <= 35.0
        and 2.0 <= h.bbox.height <= 6.0
    ]
    assert len(slot_candidates) == 2, (
        f"expected 2 nub-clearance slots (F2) on the drawer's Bottom panel, "
        f"found {len(slot_candidates)} -- can't independently locate the nub "
        f"without them"
    )

    measured_bay_gap = c.BAY_LENGTH - body_length  # independent stand-in for
                                                    # DRAWER_BAY_GAP, using the
                                                    # MEASURED body length

    nub_box_xs = []
    for slot in slot_candidates:
        slot_center_x_local = (slot.bbox.xmin + slot.bbox.xmax) / 2 - bottom_drawer.bbox.xmin
        flexure_x_from_front_inner_face = slot_center_x_local - T
        nub_box_xs.append(c.BAY_X1 - measured_bay_gap - T - flexure_x_from_front_inner_face)

    assert max(nub_box_xs) - min(nub_box_xs) <= 0.6, (
        f"the two side walls' flexure slots don't land at the same box X: {nub_box_xs}"
    )

    bottom_shell = _piece(SHELL_SVG, "bottom")
    min_span = T + 2 * DRAWER_LATERAL_FLOAT_PER_SIDE
    catch_holes = [
        h for h in _blue_holes(bottom_shell)
        if h.bbox.width < h.bbox.height and 8.0 <= h.bbox.width <= 16.0
        and h.bbox.height >= min_span
    ]
    assert len(catch_holes) == 2, f"expected 2 catch holes on the bottom panel, found {len(catch_holes)}"

    half_floor_width = c.NUB_WIDTH_AT_FLOOR_PLANE / 2

    for nub_box_x in nub_box_xs:
        nub_lo = nub_box_x - half_floor_width
        nub_hi = nub_box_x + half_floor_width
        # Both catch holes should sit at the same box X (only Y differs);
        # pick the nearest one so a symmetric X-shift of both is still caught.
        best = min(
            catch_holes,
            key=lambda h: abs((h.bbox.xmin + h.bbox.xmax) / 2 - bottom_shell.bbox.xmin - nub_box_x),
        )
        catch_lo = best.bbox.xmin - bottom_shell.bbox.xmin
        catch_hi = best.bbox.xmax - bottom_shell.bbox.xmin
        lo_slack = max(0.0, catch_lo - nub_lo)
        hi_slack = max(0.0, nub_hi - catch_hi)
        total_slop = lo_slack + hi_slack
        assert total_slop <= 1.0, (
            f"catch hole X-span [{catch_lo:.2f}, {catch_hi:.2f}] does not contain the "
            f"independently-computed nub X-span [{nub_lo:.2f}, {nub_hi:.2f}] (combined "
            f"slop {total_slop:.2f}mm > 1.0mm) -- registration broken (e.g. mutation "
            f"CATCH_HOLE_X += 5.0 must fail this)"
        )


# =============================================================================
# 6. Retention coupon pieces present (5 now: wall sample, lid notch strip,
#    drawer-side sample, mock sill edge, mock floor strip)
# =============================================================================

def test_retention_coupon_has_all_five_pieces(retention_coupon_svg):
    pieces = su.design_pieces(retention_coupon_svg)
    labels = {p.label for p in pieces}
    expected = {
        "Retention: Wall Flexure Sample",
        "Retention: Lid Notch Strip",
        "Retention: Drawer-Side Flexure Sample",
        "Retention: Mock Sill Edge",
        "Retention: Mock Floor Strip",
    }
    assert expected <= labels, f"missing retention coupon pieces: {expected - labels}; found: {labels}"


def test_retention_coupon_wall_sample_has_nub_and_release_cut(retention_coupon_svg):
    pieces = su.design_pieces(retention_coupon_svg)
    sample = su.find_piece_by_label(pieces, "Wall Flexure Sample")
    assert sample is not None
    assert len(sample.holes) >= 3, (
        f"expected >= 3 holes (slot-with-nub + cavity + severing slot) on the wall "
        f"flexure sample, found {len(sample.holes)}"
    )


def test_retention_coupon_drawer_sample_has_nub_and_release_cut(retention_coupon_svg):
    pieces = su.design_pieces(retention_coupon_svg)
    sample = su.find_piece_by_label(pieces, "Drawer-Side Flexure Sample")
    assert sample is not None
    bump = _nub_bump_geometry(sample.outer.d)
    assert abs(bump["base_right"] - bump["base_left"]) > abs(bump["top_right"] - bump["top_left"]), (
        "drawer-side flexure sample's nub has no ramp"
    )
    assert len(sample.holes) >= 2, (
        f"expected >= 2 holes (cavity + severing slot) on the drawer-side flexure "
        f"sample, found {len(sample.holes)}"
    )


def test_retention_coupon_floor_strip_has_catch_hole(retention_coupon_svg):
    pieces = su.design_pieces(retention_coupon_svg)
    strip = su.find_piece_by_label(pieces, "Mock Floor Strip")
    assert strip is not None
    assert len(strip.holes) >= 1, "mock floor strip has no catch hole"
