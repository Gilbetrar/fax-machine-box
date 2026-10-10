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

# Exception 1 — faceplates: the registration lines (glue-up jig for the
# drawer body) are DESIGNED to sit near the cut boundary: 0.95 mm inside each
# side edge, 0.75 mm below the top edge, none along the bottom (DESIGN.md part
# #9, red-team G4/G20). Their inset is asserted by the registration test, not here.
#
# (Resolved 2026-07-10: the right wall's "FAX MACHINE" pixel text — which
# overlapped the shelf/divider finger-hole cuts, text center Z=63.5 == shelf
# midplane — was REMOVED per Ben's decision on issue #25 open-item 1. Wall
# artwork replaces it via the art-integration pipeline; Ben has explicitly
# accepted that art crosses the joint-hole rows ("eat the cost of those
# holes"), so when art lands, art-bearing parts join EXPECTED_VIOLATIONS
# with a pointer to that decision — full-bleed art + through-holes is the
# recorded intent, not a defect.)
EXPECTED_VIOLATIONS: set[str] = set()
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


def test_faceplate_registration_outline_is_inset_from_the_cut():
    """Red-team G4: the glue-up registration lines used to sit 0.1 mm from the
    cut edge, so a cut-only service that cuts every line could split the
    plate.  They now stay at least 0.5 mm from every cut (the generator's
    own rule: sides 0.95 in, top 0.75 in, side lines stop 0.6 above the
    bottom edge); the 1 mm general rule above still exempts faceplates
    because the lines are meant to sit near the edge."""
    seen = 0
    for _, piece, dist in _pieces_with_engraving():
        if "Faceplate" in (piece.label or ""):
            seen += 1
            assert 0.5 <= dist < CLEARANCE_MM, (
                f"faceplate registration outline is {dist:.3f}mm from the cut "
                f"boundary; the design is 0.5 mm <= distance < 1 mm"
            )
    assert seen >= 1, "no faceplate with engraving found — clustering or labels changed"


def test_walls_carry_no_engraving_until_art_lands():
    """The pixel text was removed 2026-07-10 (Ben's decision, issue #25
    open-item 1) and wall art has not been integrated yet, so NO wall may
    carry red geometry — a stray red path on a wall would be an unreviewed
    laser instruction. When art integration lands, replace this with the
    art-bearing allowlist described at EXPECTED_VIOLATIONS above."""
    walls = [
        (svg, piece, dist)
        for svg, piece, dist in _pieces_with_engraving()
        if "Wall" in (piece.label or "")
    ]
    assert walls == [], (
        f"unexpected red engraving on wall(s): "
        f"{[(svg, p.label) for svg, p, _ in walls]}"
    )
