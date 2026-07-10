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

import subprocess
import sys
from pathlib import Path

import pytest

import svg_utils as su

pytestmark = [pytest.mark.usefixtures("regenerate_svgs")]

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "output"
PONOKO_DIR = OUTPUT_DIR / "ponoko"
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
# Text fill colors are live laser instructions (LEARNINGS.md) -- a <text>
# fill is read by a laser driver exactly like a <path> stroke, so red
# (rgb(255,0,0), this project's engrave color) is banned on every <text>
# element, everywhere, with NO exceptions -- including coupon/panel title
# labels (an earlier version of this comment carved those out as
# deliberately-engraved; that was itself an instance of the v1 red-label bug
# class, confirmed by adversarial QA, and is fixed project-wide by
# faxbox.svglabels.enforce_reference_labels -- see that module's docstring).
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


# =============================================================================
# Generalized guard (issue #25 adversarial QA finding): the check above only
# ever covered hardware.svg, and every OTHER standalone generator (drawers,
# lids, shell, calibration coupons) was still shipping Boxes.py's raw
# engrave-red part-name/title label untouched. This block regenerates every
# generator this project has, in BOTH provider trees (default NYCR
# output/*.svg and output/ponoko/*.svg), and scans every *.svg that comes
# out -- so a future generator that forgets to call
# faxbox.svglabels.enforce_reference_labels fails here immediately, project-
# wide, rather than needing its own hand-added test like the one above.
# =============================================================================

# final_layout.svg is the one file this project deliberately never sends to
# a laser (layout.py's _write_reference_layout: "NOT sized to any real laser
# bed and must NOT be sent for cutting"). Unlike every other <text> in this
# project, its "REFERENCE ONLY" warning banner (fill="#cc0000") and per-sheet
# dimension captions (fill="#333333") are written directly by
# _write_reference_layout, not through _emit_piece_group's per-piece label
# path -- they are not part names and were never Boxes.py's red engrave
# color to begin with, so the data-purpose="reference-label" convention
# (which exists to protect a *laser driver* from misreading a label as an
# engrave) doesn't apply to them. Named explicitly here, with this comment,
# rather than silently skipped -- and the red-fill ban two tests below still
# applies to this file with no carve-out at all.
_FINAL_LAYOUT_EXEMPT_FILLS = {"#cc0000", "#333333"}


@pytest.fixture(scope="session")
def all_generated_svgs(regenerate_svgs):
    """Regenerate every standalone generator not already covered by
    conftest.py's `regenerate_svgs` (shell/drawer/lids only), plus both
    nesting passes, then return every *.svg under output/ and
    output/ponoko/ -- the full set a human could ever open or send to a
    laser."""
    for module in ("faxbox.generate_hardware", "faxbox.calibration", "faxbox.layout", "faxbox.ponoko"):
        subprocess.run([sys.executable, "-m", module], check=True, cwd=REPO_ROOT, capture_output=True)
    paths = sorted(OUTPUT_DIR.glob("*.svg")) + sorted(PONOKO_DIR.glob("*.svg"))
    assert paths, "no *.svg files found under output/ or output/ponoko/"
    return paths


def test_no_text_anywhere_has_red_engrave_fill(all_generated_svgs):
    """No <text> element in ANY generated SVG may carry the engrave-red
    fill (rgb(255,0,0)) -- banned with no exceptions, including
    final_layout.svg (reference-only, but still checked here defensively:
    it should never even come close to this color)."""
    offenders = []
    for svg_path in all_generated_svgs:
        for content in _red_text_contents(svg_path):
            offenders.append((svg_path.relative_to(REPO_ROOT).as_posix(), content))
    assert not offenders, f"red-filled <text> element(s) found: {offenders}"


def test_every_text_element_is_flagged_reference_label(all_generated_svgs):
    """Every <text> element anywhere must carry
    data-purpose="reference-label", except final_layout.svg's own literal
    warning banner/sheet captions (see _FINAL_LAYOUT_EXEMPT_FILLS docstring
    above)."""
    offenders = []
    for svg_path in all_generated_svgs:
        root = su.get_svg_root(svg_path)
        for el in root.iter(f"{su.SVG_NS}text"):
            if el.get("data-purpose") == "reference-label":
                continue
            if svg_path.name == "final_layout.svg" and el.get("fill") in _FINAL_LAYOUT_EXEMPT_FILLS:
                continue
            offenders.append((svg_path.relative_to(REPO_ROOT).as_posix(), el.attrib))
    assert not offenders, f"<text> missing data-purpose=reference-label: {offenders}"
