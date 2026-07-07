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
