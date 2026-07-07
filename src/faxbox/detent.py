"""Shared point-list geometry for the iteration-2 retention detents (issue
#20). Pure functions only -- no Boxes.py/cairo calls here, so the shapes are
independently checkable and reused across shell_generator.py (wall lid
detent), generate_lids.py (mating notch), generate_drawers.py (faceplate
detent), and calibration.py (retention coupon).

All functions return points as (x, y) tuples in whatever *local* frame the
caller already draws in (see each call site) -- callers are responsible for
any mirroring/offset before/after calling these, exactly like the existing
lid-slot code in shell_generator.py mirrors `slot_cx`.

Every shape drawn from these points is closed via the caller doing
`ctx.move_to(*pts[0]); for p in pts[1:]: ctx.line_to(*p); ctx.close_path();
ctx.stroke()` -- burn-neutral (raw ctx path, no Boxes.py burn compensation),
matching this project's existing convention for exact/non-rectangular
features (calibration.py's kerf-test square, shell_generator.py's pixel-font
engraving). The two interference values these shapes encode
(LID_DETENT_ENGAGE, DRAWER_DETENT_PROTRUDE) are explicitly meant to be tuned
against the retention coupon before cutting real parts, so drawing them
burn-neutral is a deliberate simplification, not an oversight -- see
DESIGN.md's "Retention (iteration 2)" section.
"""

from __future__ import annotations

import math

from faxbox.config import DETENT_NUB_TOP_WIDTH, DETENT_RAMP_DEG


def ramp_run(rise: float) -> float:
    """Horizontal run of a DETENT_RAMP_DEG ramp climbing `rise` mm."""
    return rise / math.tan(math.radians(DETENT_RAMP_DEG))


def nub_base_width(rise: float) -> float:
    return DETENT_NUB_TOP_WIDTH + 2 * ramp_run(rise)


def bump_profile(center: float, base_half: float, top_half: float,
                  base_level: float, top_level: float) -> list[tuple[float, float]]:
    """Four points tracing a single ramped bump along one axis: base-left,
    top-left, top-right, base-right. `center`/`base_half`/`top_half` are
    positions along the "along" axis; `base_level`/`top_level` are the two
    "across" axis levels (base_level is the surrounding flat plane, top_level
    is the bump's peak) -- caller decides which tuple element is x vs y (the
    wall nub bumps in (u, z), the faceplate nub bumps in (y, x); see call
    sites), by passing `along_first=True/False`.

    Returns points as (along, across) pairs; callers that need (across,
    along) should swap each tuple themselves.
    """
    return [
        (center - base_half, base_level),
        (center - top_half, top_level),
        (center + top_half, top_level),
        (center + base_half, base_level),
    ]


def lid_slot_with_nub_points(
    u0: float, u1: float, z0: float, z1: float,
    nub_center: float, nub_top_z: float,
) -> list[tuple[float, float]]:
    """Closed polygon for the wall's lid-through-slot hole, with a ramped
    nub bump built into its bottom (z0) boundary at `nub_center`.

    (u0, z0)-(u1, z1) is the plain slot rectangle (DESIGN.md #2); the nub
    rises from z0 to nub_top_z over a small u-range centered on nub_center
    (base width from LID_DETENT_ENGAGE = nub_top_z - z0). Traced
    counterclockwise starting bottom-left; caller mirrors every point's u
    coordinate for the mirrored (left) wall, same convention as the existing
    plain-rectangle slot code.
    """
    rise = nub_top_z - z0
    half_base = nub_base_width(rise) / 2
    half_top = DETENT_NUB_TOP_WIDTH / 2
    bump = bump_profile(nub_center, half_base, half_top, z0, nub_top_z)
    return [
        (u0, z0),
        *bump,
        (u1, z0),
        (u1, z1),
        (u0, z1),
    ]


def edge_nub_detour(
    along_lo: float, along_hi: float, rest_level: float, peak_level: float,
) -> list[tuple[float, float]]:
    """The ramped detour a piece's OUTER boundary takes at one edge nub: a
    small run of points to splice into an otherwise-straight edge, going
    rest_level -> peak_level -> rest_level as `along` increases through
    [along_lo, along_hi]. Returns (along, across) pairs; the faceplate nub
    (drawer_detent_outline below) is the one caller today.
    """
    rise = abs(peak_level - rest_level)
    center = (along_lo + along_hi) / 2
    half_base = nub_base_width(rise) / 2
    half_top = DETENT_NUB_TOP_WIDTH / 2
    return bump_profile(center, half_base, half_top, rest_level, peak_level)


def release_cut_rects(
    tip: float, root: float, beam_bottom: float, cavity_bottom: float,
    sever_width: float, floor: float,
) -> tuple[tuple[float, float, float, float], tuple[float, float, float, float]]:
    """Two axis-aligned rectangles (cx, cy, width, height) -- matching
    Boxes.py's rectangularHole(cx, cy, dx, dy) signature -- that together
    free a cantilever beam on 3 sides while leaving its root (the `root` end)
    solid:

    - clearance cavity: spans the full beam length [tip, root] at
      [cavity_bottom, beam_bottom] (below/behind the beam's rest position),
      giving it room to deflect without bottoming out.
    - tip-severing slot: a thin `sever_width` slot at the `tip` end, spanning
      [cavity_bottom, floor] (floor = the beam's flush-with-surroundings top,
      e.g. the lid slot floor or a faceplate edge), fully parting the beam's
      tip from the fixed material beyond it. The root end is deliberately
      left uncut on both rectangles -- see module docstring.

    `tip`/`root` and `beam_bottom`/`cavity_bottom`/`floor` may each be either
    sign of "low to high" -- the wall (along=X increasing away from the
    mouth, across=Z DEcreasing away from the slot floor) and the faceplate
    (along=Z increasing away from the root, across=drawn-x INcreasing away
    from a left edge but DEcreasing away from a right edge) use opposite
    conventions, so every pair below is min/max-normalized rather than
    assumed ordered.
    """
    lo, hi = min(tip, root), max(tip, root)
    cavity_cx = (lo + hi) / 2
    cavity_w = hi - lo
    across_lo, across_hi = min(beam_bottom, cavity_bottom), max(beam_bottom, cavity_bottom)
    cavity_cy = (across_lo + across_hi) / 2
    cavity_h = across_hi - across_lo

    sever_cx = tip
    sever_lo, sever_hi = min(cavity_bottom, floor), max(cavity_bottom, floor)
    sever_cy = (sever_lo + sever_hi) / 2
    sever_h = sever_hi - sever_lo

    return (
        (cavity_cx, cavity_cy, cavity_w, cavity_h),
        (sever_cx, sever_cy, sever_width, sever_h),
    )


def notch_points(
    center: float, width: float, depth: float, chamfer: float,
    edge_level: float, inward_sign: float,
) -> list[tuple[float, float]]:
    """Closed polygon for an edge-open notch (used for the lid's mating
    notch): a recess cut INTO a straight edge at `edge_level`, `width` wide
    (centered on `center`), `depth` deep, with the two mouth corners eased by
    a `chamfer` x `chamfer` 45-degree cut instead of a sharp corner.

    `inward_sign` is +1 if the part's interior is at coordinates greater than
    edge_level (recessing increases the across-axis value) or -1 if the
    interior is at lesser values -- i.e. which way "deeper" points.

    Returns (along, across) pairs, open toward the edge (the caller draws
    this polygon so its along-edge_level boundary coincides with the part's
    own outer edge, exactly like the existing lid-slot-mouth precedent in
    shell_generator.py -- the laser cuts both lines and the notch opens).
    """
    half = width / 2
    floor = edge_level + inward_sign * depth
    chamfer_floor = edge_level + inward_sign * chamfer
    return [
        (center - half, edge_level),
        (center - half, chamfer_floor),
        (center - half + chamfer, floor),
        (center + half - chamfer, floor),
        (center + half, chamfer_floor),
        (center + half, edge_level),
    ]
