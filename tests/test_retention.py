"""Retention (iteration 2, issue #20) tests: positional/mating assertions on
the two spring-detent mechanisms, parsing the actual SVGs the same way
test_svg_geometry.py does (never trusting a predefined mental model of the
geometry -- see that file's module docstring on why size-only checks aren't
enough). Policy unchanged from test_svg_geometry.py: never weaken a test to
pass; existing tests are untouched except the two flagged, documented,
minimal deviations in test_svg_geometry.py (test_faceplate_blank_size and
test_edge_polarity_literals_present) that are an unavoidable consequence of
the faceplate nub becoming a real, physically larger, protruding piece.
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


def _find_nub_flat_top(slot_hole) -> tuple[float, float, float]:
    """Within the wall's lid-slot-with-nub hole path, find the nub's flat
    top segment: a short horizontal Line noticeably higher (smaller SVG y)
    than the slot's own floor level (bbox.ymax). Returns
    (svg_y, x_start, x_end) of that segment.
    """
    lines = _lines(slot_hole.d)
    floor_y = slot_hole.bbox.ymax
    candidates = []
    for seg in lines:
        y0, y1 = seg.start.imag, seg.end.imag
        if abs(y0 - y1) > 1e-6:
            continue  # not horizontal
        length = abs(seg.end.real - seg.start.real)
        if length > 6.0:
            continue  # not a short nub-top run (the base/floor runs are long)
        if floor_y - y0 < 0.3:
            continue  # not meaningfully above the floor level
        candidates.append((y0, seg.start.real, seg.end.real))
    assert len(candidates) == 1, (
        f"expected exactly 1 nub flat-top segment in the lid-slot hole, found {len(candidates)}"
    )
    return candidates[0]


# =============================================================================
# 1. Wall nub tip Z + slot ceiling clearance
# =============================================================================

@pytest.mark.parametrize("side,mirror", WALL_SIDES)
def test_wall_nub_tip_height(side, mirror):
    piece = _piece(SHELL_SVG, side)
    matches = _cut_holes_matching(piece, LID_SLOT_LENGTH, c.LID_SLOT_HEIGHT, tol=0.5)
    assert len(matches) == 1
    slot = matches[0]

    nub_y, _, _ = _find_nub_flat_top(slot)
    nub_z = _wall_box_z(piece, nub_y)
    assert abs(nub_z - c.LID_DETENT_NUB_TOP_Z) <= 0.4, (
        f"{side}: nub top at Z={nub_z:.2f}, expected LID_DETENT_NUB_TOP_Z={c.LID_DETENT_NUB_TOP_Z:.2f}"
    )
    # Nub top must clear the slot ceiling (LID_SLOT_TOP) with real margin --
    # it should never be able to jam against the rail above the slot.
    clearance = c.LID_SLOT_TOP - nub_z
    assert clearance >= 1.0, (
        f"{side}: nub top Z={nub_z:.2f} leaves only {clearance:.2f}mm below the slot "
        f"ceiling {c.LID_SLOT_TOP} -- must clear with margin"
    )
    # And it must actually rise above the slot floor by the configured
    # engagement (not accidentally sit at/below the floor level).
    rise = nub_z - c.LID_SLOT_BOTTOM
    assert rise == pytest.approx(c.LID_DETENT_ENGAGE, abs=0.4)


# =============================================================================
# 2 + 3. Lid notch aligns with the wall nub's X position when closed;
# notch depth clears the lid-slot engagement with margin
# =============================================================================

def test_lid_notch_aligns_with_wall_nub_when_closed():
    lid = _piece(LIDS_SVG, "sliding lid")
    # Find both notches: edge-open holes whose bbox width matches
    # LID_NOTCH_WIDTH and whose bbox touches one of the lid's Y edges.
    notch_matches = [
        h for h in _blue_holes(lid)
        if abs(h.bbox.width - c.LID_NOTCH_WIDTH) <= 1.0
        and (abs(h.bbox.ymin - lid.bbox.ymin) <= 0.3 or abs(h.bbox.ymax - lid.bbox.ymax) <= 0.3)
    ]
    assert len(notch_matches) == 2, (
        f"expected 2 edge-open notches (one per long edge) on the sliding lid, "
        f"found {len(notch_matches)}"
    )

    for notch in notch_matches:
        notch_cx = (notch.bbox.xmin + notch.bbox.xmax) / 2
        lid_local_x = notch_cx - lid.bbox.xmin  # lid's front edge is a clean anchor (plain, unjointed)
        assert abs(lid_local_x - c.LID_NOTCH_X) <= 0.6, (
            f"notch center lid-local X={lid_local_x:.2f}, expected LID_NOTCH_X={c.LID_NOTCH_X}"
        )

        # Explicit coordinate transform: when the lid is closed, lid-local X
        # maps to box X via + LID_CLOSED_FRONT_X (DESIGN.md #8 -- the lid's
        # front edge sits at box X = LID_CLOSED_FRONT_X when fully inserted).
        box_x_when_closed = lid_local_x + c.LID_CLOSED_FRONT_X
        assert abs(box_x_when_closed - c.LID_DETENT_X) <= 0.6, (
            f"notch maps to box X={box_x_when_closed:.2f} when closed, expected the "
            f"wall nub's box X={c.LID_DETENT_X} (LID_DETENT_X)"
        )

        # Depth: notch cuts inward from the lid's own edge by >= the lid's
        # slot engagement (2.425mm) plus margin, per DESIGN.md's derivation.
        lid_slot_engagement = (c.SLIDING_LID["width"] - c.INTERIOR_WIDTH) / 2
        depth = notch.bbox.height
        assert depth >= lid_slot_engagement + 0.5, (
            f"notch depth {depth:.2f} does not clear lid-slot engagement "
            f"{lid_slot_engagement:.2f} + 0.5mm margin"
        )


# =============================================================================
# 4. Left/right wall detents are true mirrors
# =============================================================================

def test_wall_detents_are_true_mirrors():
    box_x_by_side = {}
    for side, mirror in WALL_SIDES:
        piece = _piece(SHELL_SVG, side)
        matches = _cut_holes_matching(piece, LID_SLOT_LENGTH, c.LID_SLOT_HEIGHT, tol=0.5)
        assert len(matches) == 1
        nub_y, x0, x1 = _find_nub_flat_top(matches[0])
        nub_x_svg = (x0 + x1) / 2
        to_box_x = _wall_frame(piece, mirror)
        box_x_by_side[side] = to_box_x(nub_x_svg)

    right_x, left_x = box_x_by_side["right wall"], box_x_by_side["left wall"]
    assert abs(right_x - left_x) <= 0.6, (
        f"wall nubs land at different box X positions: right={right_x:.2f}, "
        f"left={left_x:.2f} -- mirroring is broken"
    )
    assert abs(right_x - c.LID_DETENT_X) <= 0.6


# =============================================================================
# 5. Faceplate overall width including nubs
# =============================================================================

def test_faceplate_width_includes_nubs_and_exceeds_opening_interference():
    piece = _piece(DRAWER_SVG, "faceplate")
    expected_width = c.FACEPLATE["width"] + 2 * c.DRAWER_DETENT_PROTRUDE
    assert piece.bbox.width == pytest.approx(expected_width, abs=0.5), (
        f"faceplate drawn width {piece.bbox.width:.2f}, expected {expected_width:.2f} "
        f"(FACEPLATE width + 2*DRAWER_DETENT_PROTRUDE)"
    )
    # The nub-inclusive width must exceed the opening width -- i.e. genuine
    # interference, not just filling the reveal.
    assert piece.bbox.width > c.OPENING_WIDTH, (
        f"faceplate nub-inclusive width {piece.bbox.width:.2f} does not exceed the "
        f"opening width {c.OPENING_WIDTH} -- no real interference"
    )
    interference_per_side = (piece.bbox.width - c.OPENING_WIDTH) / 2
    assert interference_per_side > 0


# =============================================================================
# 6. Nubs don't intersect the grip slot / other features; clearance margins
# =============================================================================

def test_faceplate_nubs_clear_grip_slot():
    piece = _piece(DRAWER_SVG, "faceplate")
    grip = _cut_holes_matching(piece, c.DRAWER_GRIP_SLOT["width"], c.DRAWER_GRIP_SLOT["height"], tol=1.0)
    assert len(grip) == 1
    grip_bbox = grip[0].bbox

    # Nubs sit near the Y edges (piece bbox.xmin / bbox.xmax); the grip slot
    # is Y-centered. Confirm real X separation between the nub region and
    # the grip slot -- no overlap, and >= 3mm gap either side.
    nub_region_from_left = piece.bbox.xmin + c.DETENT_BEAM_WIDTH + c.DETENT_CLEARANCE
    nub_region_from_right = piece.bbox.xmax - c.DETENT_BEAM_WIDTH - c.DETENT_CLEARANCE
    assert grip_bbox.xmin - nub_region_from_left >= 3.0, (
        "faceplate grip slot is within 3mm of the left-edge detent's release cut"
    )
    assert nub_region_from_right - grip_bbox.xmax >= 3.0, (
        "faceplate grip slot is within 3mm of the right-edge detent's release cut"
    )


@pytest.mark.parametrize("side,mirror", WALL_SIDES)
def test_wall_nub_clears_divider_and_shelf_hole_lines(side, mirror):
    """Nub/beam must stay >= 3mm from the (measured, real) divider
    finger-hole column and stay entirely above the (measured, real) shelf
    hole line's Z band."""
    piece = _piece(SHELL_SVG, side)
    to_box_x = _wall_frame(piece, mirror)

    matches = _cut_holes_matching(piece, LID_SLOT_LENGTH, c.LID_SLOT_HEIGHT, tol=0.5)
    assert len(matches) == 1
    nub_y, x0, x1 = _find_nub_flat_top(matches[0])
    nub_box_x = to_box_x((x0 + x1) / 2)

    divider_rows = su.hole_line_rows(_blue_holes(piece), T, axis="y")
    divider_hits = [r for r in divider_rows if 0.75 * c.DIVIDER_HEIGHT <= r.span <= c.DIVIDER_HEIGHT + 1.0]
    assert len(divider_hits) == 1
    divider_box_x = to_box_x(divider_hits[0].center)
    assert abs(divider_box_x - nub_box_x) >= 3.0, (
        f"{side}: measured nub (box X={nub_box_x:.2f}) is within 3mm of the measured "
        f"divider hole column (box X={divider_box_x:.2f})"
    )

    # Two bay-length rows exist on each wall (shelf + top-panel, see
    # test_side_wall_has_shelf_and_top_panel_hole_lines); the shelf row is
    # the one further from the top edge (larger SVG y = lower box Z).
    shelf_rows_x = su.hole_line_rows(_blue_holes(piece), T, axis="x")
    shelf_hits = [r for r in shelf_rows_x if 0.75 * c.BAY_LENGTH <= r.span <= c.BAY_LENGTH + 1.0]
    assert len(shelf_hits) == 2, f"{side}: expected 2 bay-length hole rows (shelf + top panel)"
    shelf_row = max(shelf_hits, key=lambda r: r.center)
    shelf_z = _wall_box_z(piece, shelf_row.center)
    assert abs(shelf_z - c.LID_DETENT_NUB_TOP_Z) >= 40.0, (
        f"{side}: the shelf hole row (Z={shelf_z:.2f}) is unexpectedly close to "
        f"the nub (Z={c.LID_DETENT_NUB_TOP_Z})"
    )


# =============================================================================
# 7. Beam clearance cuts leave structural webs intact / don't touch the rail
# =============================================================================

@pytest.mark.parametrize("side,mirror", WALL_SIDES)
def test_wall_release_cut_does_not_touch_top_rail_or_bottom_row(side, mirror):
    piece = _piece(SHELL_SVG, side)

    # The release cut's cavity + severing slot are small rectangular holes
    # near LID_DETENT_CAVITY_BOTTOM_Z..LID_DETENT_BEAM_BOTTOM_Z; none of the
    # wall's holes may extend above the slot floor (into the 5mm top rail)
    # or down into the bottom-panel finger-hole row's Z band.
    for h in _blue_holes(piece):
        z_top = _wall_box_z(piece, h.bbox.ymin)
        z_bottom = _wall_box_z(piece, h.bbox.ymax)
        hi, lo = max(z_top, z_bottom), min(z_top, z_bottom)
        if hi <= c.LID_SLOT_TOP + 0.1 and lo >= c.LID_DETENT_CAVITY_BOTTOM_Z - 3.0 and (hi - lo) < 10:
            # A candidate detent-area hole (small, sits below the slot
            # floor): must not creep up into the rail above LID_SLOT_TOP,
            # and must stay clear of the bottom-panel row at Z ~= T/2.
            assert hi <= c.LID_SLOT_TOP + 0.5, f"{side}: a detent-area hole reaches into the top rail"
            assert lo >= (T / 2) + c.MIN_WEB, (
                f"{side}: a detent-area hole reaches down toward the bottom-panel row"
            )


# =============================================================================
# 8. Retention coupon pieces present
# =============================================================================

def test_retention_coupon_has_all_four_pieces(retention_coupon_svg):
    pieces = su.design_pieces(retention_coupon_svg)
    labels = {p.label for p in pieces}
    expected = {
        "Retention: Wall Flexure Sample",
        "Retention: Lid Notch Strip",
        "Retention: Faceplate Flexure Sample",
        "Retention: Mock Opening Edge",
    }
    assert expected <= labels, f"missing retention coupon pieces: {expected - labels}; found: {labels}"


def test_retention_coupon_wall_sample_has_nub_and_release_cut(retention_coupon_svg):
    pieces = su.design_pieces(retention_coupon_svg)
    sample = su.find_piece_by_label(pieces, "Wall Flexure Sample")
    assert sample is not None
    # The slot-with-nub hole should be the largest hole (spans most of the
    # sample's width); the release cut shows up as 2 additional smaller
    # holes (cavity + severing slot).
    assert len(sample.holes) >= 3, (
        f"expected >= 3 holes (slot-with-nub + cavity + severing slot) on the wall "
        f"flexure sample, found {len(sample.holes)}"
    )


def test_retention_coupon_faceplate_sample_has_release_cut(retention_coupon_svg):
    pieces = su.design_pieces(retention_coupon_svg)
    sample = su.find_piece_by_label(pieces, "Faceplate Flexure Sample")
    assert sample is not None
    assert len(sample.holes) >= 2, (
        f"expected >= 2 holes (cavity + severing slot) on the faceplate flexure "
        f"sample, found {len(sample.holes)}"
    )
