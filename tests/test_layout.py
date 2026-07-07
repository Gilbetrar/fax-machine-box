"""Layout/nesting tests: run `python -m faxbox.layout` (module subprocess,
same pattern as conftest.py's `regenerate_svgs` fixture) and check the
emitted output/sheet_*.svg files against issue #19's release-gate
requirements: every part appears exactly once, no overlaps, everything
inside the sheet margins, sheets within the verified bed size, and only
cut-blue/engrave-red strokes.

Reuses tests/svg_utils.py's measurement helpers (the same ones
test_svg_geometry.py and test_laser_requirements.py use) since sheet_*.svg
keeps the same "one <g> per piece, containing its <path>s and one <text>
label" structure Boxes.py itself uses -- see src/faxbox/layout.py's module
docstring for why layout.py reads/writes that structure directly instead of
importing this module.
"""

from __future__ import annotations

import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

import svg_utils as su
from faxbox import layout as fl

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "output"

# The 21 parts issue #19 expects, keyed exactly as src/faxbox/layout.py
# labels them ("<source>: <Boxes.py label>") -- 8 shell (once each), 6
# drawer labels x2 (Drawer 1 and Drawer 2, cut twice), 1 lid.
SHELL_LABELS = [
    "Bottom", "Right Wall", "Left Wall", "Front Wall", "Rear Wall",
    "Vertical Divider", "Horizontal Shelf", "Top Panel",
]
DRAWER_LABELS = ["Front", "Back", "Left Side", "Right Side", "Bottom", "Faceplate"]

EXPECTED_LABELS = (
    [f"Shell: {name}" for name in SHELL_LABELS]
    + [f"Drawer 1: {name}" for name in DRAWER_LABELS]
    + [f"Drawer 2: {name}" for name in DRAWER_LABELS]
    + ["Lid: Sliding Lid"]
)
assert len(EXPECTED_LABELS) == 21  # 8 shell + 12 drawer (6x2) + 1 lid


@pytest.fixture(scope="session")
def sheets(regenerate_svgs):
    """Regenerate the 3 source SVGs (regenerate_svgs, from conftest.py),
    then run `python -m faxbox.layout` as a subprocess -- exactly what the
    README/issue verification procedure runs -- and return the resulting
    sheet_*.svg paths in sheet-number order."""
    subprocess.run(
        [sys.executable, "-m", "faxbox.layout"],
        check=True,
        cwd=REPO_ROOT,
        capture_output=True,
    )
    paths = sorted(OUTPUT_DIR.glob("sheet_*.svg"), key=lambda p: int(p.stem.split("_")[1]))
    assert paths, "faxbox.layout produced no sheet_*.svg files"
    return paths


def _all_pieces(sheets: list[Path]) -> list[su.Piece]:
    pieces = []
    for sheet in sheets:
        pieces.extend(su.design_pieces(sheet))
    return pieces


# =============================================================================
# Every part appears exactly once, across all sheets
# =============================================================================

def test_every_part_appears_expected_number_of_times(sheets):
    labels = [piece.label for piece in _all_pieces(sheets)]
    assert Counter(labels) == Counter(EXPECTED_LABELS), (
        f"got: {sorted(labels)}\nexpected: {sorted(EXPECTED_LABELS)}"
    )


def test_total_part_count_is_21(sheets):
    assert len(_all_pieces(sheets)) == 21


# =============================================================================
# No overlapping piece bboxes on any sheet
# =============================================================================

def test_no_overlapping_pieces_on_any_sheet(sheets):
    for sheet in sheets:
        pieces = su.get_pieces(sheet)
        offenders = []
        for i in range(len(pieces)):
            for j in range(i + 1, len(pieces)):
                if pieces[i].bbox.overlaps(pieces[j].bbox):
                    offenders.append((pieces[i].label, pieces[j].label))
        assert not offenders, f"overlapping piece bboxes in {sheet.name}: {offenders}"


# =============================================================================
# Every piece inside sheet bounds minus the required margin
# =============================================================================

def test_every_piece_within_sheet_margin(sheets):
    tol = 0.05  # rounding slack from the layout module's float formatting
    for sheet in sheets:
        width, height = su.get_svg_dimensions_mm(sheet)
        for piece in su.design_pieces(sheet):
            bbox = piece.bbox
            assert bbox.xmin >= fl.MARGIN_MM - tol, f"{sheet.name} {piece.label!r} xmin {bbox.xmin} < margin"
            assert bbox.ymin >= fl.MARGIN_MM - tol, f"{sheet.name} {piece.label!r} ymin {bbox.ymin} < margin"
            assert bbox.xmax <= width - fl.MARGIN_MM + tol, (
                f"{sheet.name} {piece.label!r} xmax {bbox.xmax} exceeds sheet width {width} minus margin"
            )
            assert bbox.ymax <= height - fl.MARGIN_MM + tol, (
                f"{sheet.name} {piece.label!r} ymax {bbox.ymax} exceeds sheet height {height} minus margin"
            )


# =============================================================================
# Sheet dimensions within the verified (or conservative-fallback) bed size
# =============================================================================

def test_sheet_dims_within_bed_size(sheets):
    tol = 0.05
    for sheet in sheets:
        width, height = su.get_svg_dimensions_mm(sheet)
        assert width <= fl.SHEET_WIDTH_MM + tol, f"{sheet.name} width {width} exceeds bed {fl.SHEET_WIDTH_MM}"
        assert height <= fl.SHEET_HEIGHT_MM + tol, f"{sheet.name} height {height} exceeds bed {fl.SHEET_HEIGHT_MM}"


# =============================================================================
# Only cut-blue / engrave-red strokes, mm units
# =============================================================================

def test_sheets_use_only_cut_or_engrave_colors(sheets):
    for sheet in sheets:
        offenders = []
        for piece in su.design_pieces(sheet):
            bad = piece.stroke_colors() - {"blue", "red"}
            if bad:
                offenders.append((piece.label, bad))
        assert not offenders, f"non-cut/engrave colors found in {sheet.name}: {offenders}"


def test_sheets_have_no_black_strokes(sheets):
    for sheet in sheets:
        assert su.any_black_strokes(sheet) == []


def test_sheet_dimensions_are_in_mm(sheets):
    for sheet in sheets:
        width, height = su.get_svg_dimensions_mm(sheet)
        assert width > 0
        assert height > 0


# =============================================================================
# Inter-piece spacing (issue #19 requirement: >= SPACING_MM=5.0 between parts)
# =============================================================================
# test_no_overlapping_pieces_on_any_sheet (above) only catches pieces that
# actually touch/overlap; a packer bug that leaves two bboxes 1mm apart
# (rather than the intended 5mm) passes that check cleanly while still
# being too tight for a laser kerf + real-world material handling.

def _bbox_gap(a: su.BBox, b: su.BBox) -> float:
    """Shortest distance between two axis-aligned rectangles; 0 if they
    touch or overlap on at least one axis with overlap on the other."""
    dx = max(b.xmin - a.xmax, a.xmin - b.xmax, 0.0)
    dy = max(b.ymin - a.ymax, a.ymin - b.ymax, 0.0)
    return (dx**2 + dy**2) ** 0.5


def test_inter_piece_spacing_at_least_4_5mm(sheets):
    min_gap = 4.5  # packer targets fl.SPACING_MM (5.0mm); slack for rounding
    for sheet in sheets:
        pieces = su.design_pieces(sheet)
        offenders = []
        for i in range(len(pieces)):
            for j in range(i + 1, len(pieces)):
                gap = _bbox_gap(pieces[i].bbox, pieces[j].bbox)
                if gap < min_gap:
                    offenders.append((pieces[i].label, pieces[j].label, round(gap, 2)))
        assert not offenders, f"{sheet.name}: piece pairs closer than {min_gap}mm: {offenders}"


# =============================================================================
# Reference-label <text>: gray, reference-only, correctly flagged
# =============================================================================
# layout._emit_piece_group re-colors Boxes.py's part-name labels from red
# (Color.ANNOTATIONS, identical to ENGRAVE_COLOR) to gray and stamps
# data-purpose="reference-label" so a laser driver never mistakes a part
# name for an engrave path. A regression here would silently reintroduce a
# red (or otherwise ambiguous) text element that non-cut/engrave-color
# checks elsewhere don't look at (they only walk <path>, not <text>).

def test_sheet_text_labels_are_gray_reference_only(sheets):
    for sheet in sheets:
        root = su.get_svg_root(sheet)
        texts = root.findall(f".//{su.SVG_NS}text")
        assert texts, f"{sheet.name} has no <text> labels"
        for t in texts:
            style = t.get("style", "")
            assert "rgb(128,128,128)" in style, f"{sheet.name}: text style not gray: {style!r}"
            assert "rgb(255,0,0)" not in style, f"{sheet.name}: text style still red (engrave color): {style!r}"
            assert "rgb(0,0,255)" not in style, f"{sheet.name}: text style is cut-blue: {style!r}"
            assert t.get("data-purpose") == "reference-label", (
                f"{sheet.name}: text missing data-purpose=reference-label: {t.attrib}"
            )


# =============================================================================
# Path stroke-width: forced hairline for every re-serialized cut/engrave path
# =============================================================================

def test_sheet_path_strokes_are_hairline(sheets):
    max_stroke_width = 0.1
    for sheet in sheets:
        root = su.get_svg_root(sheet)
        paths = root.findall(f".//{su.SVG_NS}path")
        assert paths, f"{sheet.name} has no <path> elements"
        for p in paths:
            sw = p.get("stroke-width")
            assert sw is not None, f"{sheet.name}: path missing stroke-width: {p.attrib}"
            assert float(sw) <= max_stroke_width, (
                f"{sheet.name}: stroke-width {sw} exceeds {max_stroke_width}mm (not hairline)"
            )


# =============================================================================
# Kerf/fit calibration coupon (independent of the shell/drawer/lid/layout
# pipeline above -- generated by faxbox.calibration, never nested onto a
# sheet_*.svg)
# =============================================================================

@pytest.fixture(scope="session")
def kerf_coupon_svg():
    subprocess.run(
        [sys.executable, "-m", "faxbox.calibration"],
        check=True,
        cwd=REPO_ROOT,
        capture_output=True,
    )
    path = OUTPUT_DIR / "kerf_coupon.svg"
    assert path.exists(), "faxbox.calibration did not produce output/kerf_coupon.svg"
    return path


def test_kerf_coupon_piece_and_hole_count(kerf_coupon_svg):
    pieces = su.get_pieces(kerf_coupon_svg)
    assert len(pieces) == 1, f"expected exactly 1 piece on the coupon, found {len(pieces)}"
    assert len(pieces[0].holes) == 4, (
        f"expected 3 fit-test slots + 1 kerf-test hole = 4 holes, found {len(pieces[0].holes)}"
    )


def test_kerf_coupon_slot_widths_match_burn_compensated_nominal(kerf_coupon_svg):
    from faxbox import calibration as cal
    from faxbox import config as c

    T = c.MATERIAL_THICKNESS
    piece = su.get_pieces(kerf_coupon_svg)[0]
    slot_holes = sorted(piece.holes, key=lambda h: h.bbox.xmin)[:3]
    assert len(cal.SLOT_WIDTHS) == 3
    for hole, nominal in zip(slot_holes, cal.SLOT_WIDTHS):
        measured = hole.bbox.width
        expected = nominal - 2 * c.BURN
        assert abs(measured - expected) <= 0.1, (
            f"slot nominal {nominal}mm: measured width {measured:.3f}mm, "
            f"expected ~{expected:.3f}mm (nominal - 2*burn, +/-0.1)"
        )
    assert T in cal.SLOT_WIDTHS, "expected one slot at nominal MATERIAL_THICKNESS"


def test_kerf_coupon_all_strokes_blue(kerf_coupon_svg):
    for p in su.iter_paths(kerf_coupon_svg):
        assert su.normalize_color(p.stroke) == "blue", (
            f"kerf coupon has a non-blue stroke: {p.stroke!r} (nothing on this coupon is engraved)"
        )


def test_kerf_coupon_dims_in_mm(kerf_coupon_svg):
    width, height = su.get_svg_dimensions_mm(kerf_coupon_svg)
    assert width > 0
    assert height > 0
