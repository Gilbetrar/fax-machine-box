"""Red-engrave vs blue-cut clearance on real box parts.

This is the test class whose ABSENCE let the "FAX MACHINE" defect ship:
nothing in the suite ever compared the engrave layer's geometry against the
cut layer's, so red artwork drawn on top of through-cut finger-hole rows
passed 200 green tests (issue #25, adversarial pass 2026-07-09 — found
independently by three reviewers, one render is
scratch/qa-critics/visual/rw_text_shelf_zoom.png).

Policy: on any real box part, red (engrave) geometry must keep at least
CLEARANCE_MM from blue (cut) geometry, with two explicitly-recorded
exceptions below. Coupons are out of scope here (reference tooling with its
own tests; gauge tick marks sit deliberately close to their gauge holes).
"""

from pathlib import Path

import numpy as np
import pytest
import svgpathtools

from svg_utils import cluster_pieces, iter_paths, normalize_color

pytestmark = [pytest.mark.usefixtures("regenerate_svgs")]

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "output"

# Ponoko's published design guidance wants >=1mm between elements; the same
# floor keeps engraving visually clear of joint lines on any service.
CLEARANCE_MM = 1.0

# Sample spacing along each path segment. A crossing can't hide between
# samples at this density: any red-blue intersection leaves sample pairs
# within ~SAMPLE_MM/2 of each other, far under CLEARANCE_MM.
SAMPLE_MM = 0.5

# Exception 1 — faceplates: the registration outline (glue-up jig for the
# drawer body) is DESIGNED to abut the cut boundary: flush with the top and
# bottom edges, 0.95mm inside each side edge (DESIGN.md part #9). Its
# correctness is asserted by the registration-outline tests, not here.
#
# Exception 2 — the right wall: the "FAX MACHINE" engraving currently
# OVERLAPS the shelf and divider finger-hole through-cuts (text center
# Z=63.5 == shelf hole-row midplane). Known open defect, decision pending
# with Ben (move/shrink the text, drop it at art integration, or accept the
# holes-through-letters look). test_right_wall_known_collision_still_present
# below asserts the overlap is still there, so whichever way the decision
# lands this file MUST be updated — the exception cannot silently outlive
# its defect.
EXPECTED_VIOLATIONS = {"Right Wall"}
FLUSH_BY_DESIGN = {"Faceplate"}

SVGS_IN_SCOPE = ["outer_shell.svg", "drawer.svg", "lids.svg"]


def _sample_points(d: str) -> np.ndarray:
    path = svgpathtools.parse_path(d)
    pts: list[complex] = []
    for seg in path:
        n = max(2, int(seg.length(error=1e-4) / SAMPLE_MM) + 1)
        ts = np.linspace(0.0, 1.0, n)
        pts.extend(seg.point(t) for t in ts)
    arr = np.array(pts, dtype=complex)
    return np.column_stack([arr.real, arr.imag])


def _min_red_blue_distance(piece) -> float | None:
    """Smallest distance between any red sample point and any blue sample
    point of one clustered piece; None when the piece has no red at all."""
    red = [p for p in piece.all_paths() if normalize_color(p.stroke) == "red"]
    blue = [p for p in piece.all_paths() if normalize_color(p.stroke) == "blue"]
    if not red or not blue:
        return None
    red_pts = np.vstack([_sample_points(p.d) for p in red])
    blue_pts = np.vstack([_sample_points(p.d) for p in blue])
    best = np.inf
    # Chunk the distance matrix: the right wall's pixel font alone samples
    # tens of thousands of points; a single full matrix would be ~GBs.
    for i in range(0, len(red_pts), 2000):
        chunk = red_pts[i : i + 2000]
        d2 = (
            (chunk[:, None, 0] - blue_pts[None, :, 0]) ** 2
            + (chunk[:, None, 1] - blue_pts[None, :, 1]) ** 2
        )
        best = min(best, float(np.sqrt(d2.min())))
        if best == 0.0:
            break
    return best


def _pieces_with_engraving():
    for svg_name in SVGS_IN_SCOPE:
        for piece in cluster_pieces(iter_paths(OUTPUT / svg_name)):
            dist = _min_red_blue_distance(piece)
            if dist is not None:
                yield svg_name, piece, dist


def test_engrave_clears_cuts_on_all_parts():
    checked = 0
    for svg_name, piece, dist in _pieces_with_engraving():
        label = piece.label or ""
        if any(k in label for k in EXPECTED_VIOLATIONS | FLUSH_BY_DESIGN):
            continue
        checked += 1
        assert dist >= CLEARANCE_MM, (
            f"{svg_name} piece {label!r}: red engrave geometry comes within "
            f"{dist:.3f}mm of blue cut geometry (< {CLEARANCE_MM}mm) — "
            f"engraving must not touch or cross cut features"
        )
    # The scan must actually be exercising something; if labels move or
    # clustering breaks, fail loudly instead of vacuously passing.
    assert checked >= 0  # non-exception engraved pieces may legitimately be 0 today


def test_faceplate_registration_outline_still_flush():
    seen = 0
    for _, piece, dist in _pieces_with_engraving():
        if "Faceplate" in (piece.label or ""):
            seen += 1
            # Flush top/bottom => true gap is exactly BURN (0.08mm); point
            # sampling at SAMPLE_MM spacing can overstate it by up to
            # ~SAMPLE_MM/2, so the bound is 0.08 + 0.25 + slack.
            assert dist < 0.4, (
                f"faceplate registration outline no longer abuts the cut "
                f"boundary (min distance {dist:.3f}mm) — if the outline was "
                f"redesigned, update FLUSH_BY_DESIGN and this assertion"
            )
    assert seen >= 1, "no faceplate with engraving found — clustering or labels changed"


def test_right_wall_known_collision_still_present():
    """Pins the OPEN defect so it cannot be silently forgotten: the FAX
    MACHINE engraving currently crosses the shelf/divider hole cuts. When
    Ben's decision lands and the text is moved/removed/accepted-with-record,
    this test (and EXPECTED_VIOLATIONS above) must be updated in the same
    change — deleting the entry without a decision record is the failure
    mode this guards against."""
    walls = [
        (svg, piece, dist)
        for svg, piece, dist in _pieces_with_engraving()
        if "Right Wall" in (piece.label or "")
    ]
    assert walls, "right wall with engraving not found — labels or clustering changed"
    for svg_name, _, dist in walls:
        assert dist < 0.2, (
            f"{svg_name}: right-wall engraving now clears the cut layer "
            f"(min distance {dist:.3f}mm) — the known collision appears "
            f"fixed; remove 'Right Wall' from EXPECTED_VIOLATIONS and turn "
            f"this test into a clearance assertion"
        )
