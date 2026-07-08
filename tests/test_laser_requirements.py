"""Laser-service compliance tests: every stroke must be cut-blue or
engrave-red, dimensions must be in mm, and engrave (red) content must only
appear where DESIGN.md places it.

See tests/svg_utils.py for the shared parsing helpers and for
`is_reference_mark` / `design_pieces`, which factor out Boxes.py's
auto-generated calibration rectangle (a black-stroked reference ruler drawn
by `Boxes.render()` unless a generator passes `--reference 0` -- none of the
three faxbox generators currently do). That rectangle is not a DESIGN.md
part, but it *is* a real defect (it would get sent to the laser as a black
line) -- see `test_*_zero_black_strokes_strict` below, which checks the
*whole* file including it and is expected to fail until a generator disables
it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import svg_utils as su

pytestmark = [pytest.mark.usefixtures("regenerate_svgs")]

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"
ALL_SVGS = [OUTPUT_DIR / "outer_shell.svg", OUTPUT_DIR / "drawer.svg", OUTPUT_DIR / "lids.svg"]


# =============================================================================
# Dimensions in mm
# =============================================================================

@pytest.mark.parametrize("svg_path", ALL_SVGS, ids=lambda p: p.name)
def test_svg_dimensions_are_in_mm(svg_path):
    width, height = su.get_svg_dimensions_mm(svg_path)
    assert width > 0
    assert height > 0


# =============================================================================
# Zero black strokes
# =============================================================================

# Strict, whole-file version: every single stroke in the document, including
# Boxes.py's own calibration rectangle. This is the check that must be green
# for the generators to be laser-submission-ready. shell_generator.py and
# generate_lids.py now pass --reference 0 (#17), so outer_shell.svg and
# lids.svg are real, unmarked passes; generate_drawers.py does not yet (#18),
# so drawer.svg's instance is still expected to fail on the un-configured
# reference mark (a real, if minor, defect -- not a geometry issue).
@pytest.mark.parametrize(
    "svg_path",
    [
        OUTPUT_DIR / "outer_shell.svg",
        OUTPUT_DIR / "drawer.svg",
        OUTPUT_DIR / "lids.svg",
    ],
    ids=lambda p: p.name,
)
def test_zero_black_strokes_strict(svg_path):
    assert su.any_black_strokes(svg_path) == []


# Design-pieces version: excludes only the calibration mark (identified by
# its fixed 100x10mm geometric signature, not by color -- see
# svg_utils.is_reference_mark) and checks every remaining piece uses only
# cut-blue or engrave-red. This passes today and is the real, currently-
# meaningful regression check (also the target of this issue's negative
# control #2 -- see the issue report for the exact commands).
@pytest.mark.parametrize("svg_path", ALL_SVGS, ids=lambda p: p.name)
def test_design_pieces_use_only_cut_or_engrave_colors(svg_path):
    offenders = []
    for piece in su.design_pieces(svg_path):
        bad = piece.stroke_colors() - {"blue", "red"}
        if bad:
            offenders.append((piece.label, bad))
    assert not offenders, f"non-cut/engrave colors found in {svg_path.name}: {offenders}"


@pytest.mark.parametrize("svg_path", ALL_SVGS, ids=lambda p: p.name)
def test_design_pieces_have_no_unset_stroke(svg_path):
    """Every path on a real part must have an explicit stroke; an unset
    stroke would default to the viewer's/laser software's own black, which
    is exactly the "black strokes must be zero" rule from another angle."""
    for piece in su.design_pieces(svg_path):
        for path in piece.all_paths():
            assert path.stroke is not None, f"{svg_path.name} piece {piece.label!r} has a path with no stroke set"


# =============================================================================
# Every stroke format is recognized as blue/red (no missed color formats)
# =============================================================================

@pytest.mark.parametrize("svg_path", ALL_SVGS, ids=lambda p: p.name)
def test_all_strokes_normalize_to_a_known_color(svg_path):
    """Every stroke value actually present in the file must normalize to
    blue/red/black -- if this ever reports 'other:...' it means the
    generator started using a color format (or color) our normalizer and
    thus every other check in this file doesn't recognize yet."""
    seen = {su.normalize_color(p.stroke) for p in su.iter_paths(svg_path)}
    unknown = {c for c in seen if c.startswith("other:") or c == "none"}
    assert not unknown, f"{svg_path.name} has unrecognized stroke value(s): {unknown}"


# =============================================================================
# Engrave (red) content only where DESIGN.md places it
# =============================================================================
# DESIGN.md: "FAX MACHINE" engraving on the right side wall exterior
# (outer_shell.svg); faceplate registration outline (drawer.svg, part of the
# not-yet-built faceplate); no engraving anywhere on the lid (lids.svg).

def _pieces_with_red(svg_path):
    return {
        piece.label
        for piece in su.design_pieces(svg_path)
        if "red" in piece.stroke_colors()
    }


def test_shell_engrave_only_on_right_wall():
    assert _pieces_with_red(OUTPUT_DIR / "outer_shell.svg") == {"Right Wall"}


def test_drawer_engrave_only_on_faceplate():
    assert _pieces_with_red(OUTPUT_DIR / "drawer.svg") == {"Faceplate"}


def test_lids_have_no_engraving():
    """DESIGN.md's sliding lid has no engraved content; this already holds
    today and should keep holding through the #17 rebuild."""
    assert _pieces_with_red(OUTPUT_DIR / "lids.svg") == set()


# =============================================================================
# Text fill colors are live laser instructions (LEARNINGS.md) -- real parts
# must label in reference-gray only. Red text is allowed solely as a coupon
# title (calibration scrap, engraved deliberately for identification).
# =============================================================================

def _red_text_contents(svg_path):
    root = su.get_svg_root(svg_path)
    out = []
    for el in root.iter(f"{su.SVG_NS}text"):
        style = (el.get("style") or "") + (el.get("fill") or "")
        if "rgb(255,0,0)" in style.replace(" ", ""):
            out.append((el.text or "").strip())
    return out


def test_hardware_labels_never_engrave():
    """The turn button is a real, visible part: any red-filled text on it
    would be burned into the show face (the v1 red-label bug class)."""
    assert _red_text_contents(OUTPUT_DIR / "hardware.svg") == []
