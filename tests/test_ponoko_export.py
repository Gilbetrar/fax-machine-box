"""Ponoko export mode tests: run `python -m faxbox.ponoko` (subprocess, same
PYTHONPATH-forcing pattern as conftest.py's `regenerate_svgs` fixture and
test_layout.py's own `sheets` fixture) and check the emitted
output/ponoko/sheet_*.svg files against the Ponoko order requirements: sheets
within Ponoko's published birch-plywood workable area, only Ponoko's two
colors present (no gray reference text, no <text> elements at all), the
right part count (21 NYCR parts + 1 turn button + 1 self-calibration
coupon = 23), engrave content only where DESIGN.md places it, the
kerf-square coupon at true nominal 10.0mm, and provider BURN actually
changing drawn geometry relative to the NYCR default.

This fixture is deliberately separate from conftest.py's `regenerate_svgs`
(NYCR-only) and test_layout.py's `sheets` (NYCR-only) fixtures -- Ponoko
generation is only triggered by tests in THIS file explicitly requesting the
`ponoko_sheets` fixture below, never as a side effect of running the rest of
the suite.

See faxbox/config.py's PROVIDERS/PONOKO_* constants for the verified-2026-07-07
source URLs behind every Ponoko-specific number asserted here.
"""

from __future__ import annotations

import subprocess
import sys
from collections import Counter
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest
import svgpathtools

import svg_utils as su
from faxbox import config as c
from faxbox import layout as fl

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = REPO_ROOT / "output"
PONOKO_DIR = OUTPUT_DIR / "ponoko"

PONOKO_CFG = c.PROVIDERS["ponoko"]
NYCR_CFG = c.PROVIDERS["nycr"]


# =============================================================================
# Fixture: regenerate the Ponoko export explicitly (never a side effect of
# any other test file running)
# =============================================================================

@pytest.fixture(scope="session")
def ponoko_sheets(regenerate_svgs):
    """Regenerate the NYCR default sources (regenerate_svgs, from
    conftest.py -- needed by test_burn_actually_changes_drawn_geometry
    below, which compares against the NYCR shell), then run
    `python -m faxbox.ponoko` as a subprocess -- exactly what a human
    ordering from Ponoko would run -- and return the resulting
    output/ponoko/sheet_*.svg paths in sheet-number order."""
    subprocess.run(
        [sys.executable, "-m", "faxbox.ponoko"],
        check=True,
        cwd=REPO_ROOT,
        capture_output=True,
    )
    paths = sorted(PONOKO_DIR.glob("sheet_*.svg"), key=lambda p: int(p.stem.split("_")[1]))
    assert paths, "faxbox.ponoko produced no output/ponoko/sheet_*.svg files"
    return paths


# =============================================================================
# Piece identification on ponoko sheets: layout._emit_piece_group always
# stamps a `data-part="<source>: <label>"` attribute on each piece's <g>,
# regardless of whether that piece's <text> label was stripped (which it is,
# for every Ponoko piece -- config.PONOKO_STRIP_LABELS) -- so pieces are
# still individually identifiable without relying on visible text.
# =============================================================================

class SheetPiece:
    def __init__(self, label: str, bbox: "su.BBox", colors: set[str], has_text: bool):
        self.label = label
        self.bbox = bbox
        self.colors = colors
        self.has_text = has_text


def _sheet_pieces(sheet_path: Path) -> list[SheetPiece]:
    root = ET.parse(sheet_path).getroot()
    pieces: list[SheetPiece] = []
    for g in root.findall(f"{su.SVG_NS}g"):
        path_els = [p for p in g.findall(f"{su.SVG_NS}path") if p.get("d")]
        if not path_els:
            continue
        xs: list[float] = []
        ys: list[float] = []
        colors: set[str] = set()
        for p in path_els:
            x0, x1, y0, y1 = svgpathtools.parse_path(p.get("d")).bbox()
            xs += [x0, x1]
            ys += [y0, y1]
            colors.add(su.normalize_color(p.get("stroke")))
        texts = g.findall(f"{su.SVG_NS}text")
        pieces.append(
            SheetPiece(
                label=g.get("data-part", g.get("id", "")),
                bbox=su.BBox(xmin=min(xs), xmax=max(xs), ymin=min(ys), ymax=max(ys)),
                colors=colors,
                has_text=bool(texts),
            )
        )
    return pieces


def _all_sheet_pieces(sheets: list[Path]) -> list[SheetPiece]:
    pieces: list[SheetPiece] = []
    for sheet in sheets:
        pieces.extend(_sheet_pieces(sheet))
    return pieces


# =============================================================================
# Sheets within Ponoko's published birch-plywood workable area
# (790mm x 384mm -- see config.PONOKO_SHEET_WIDTH/HEIGHT for the source URL)
# =============================================================================

def test_ponoko_sheets_within_size_limit(ponoko_sheets):
    tol = 0.05
    for sheet in ponoko_sheets:
        width, height = su.get_svg_dimensions_mm(sheet)
        assert width <= PONOKO_CFG["sheet_width"] + tol, (
            f"{sheet.name} width {width}mm exceeds Ponoko's {PONOKO_CFG['sheet_width']}mm limit"
        )
        assert height <= PONOKO_CFG["sheet_height"] + tol, (
            f"{sheet.name} height {height}mm exceeds Ponoko's {PONOKO_CFG['sheet_height']}mm limit"
        )


def test_ponoko_kept_to_three_sheets(ponoko_sheets):
    """Not a hard Ponoko requirement, but price scales with material -- the
    re-nest was designed to fit in 3 sheets (see README 'Ordering from
    Ponoko'); assert that stays true so a future geometry change that
    silently spills onto a 4th sheet gets caught here."""
    assert len(ponoko_sheets) == 3, f"expected 3 Ponoko sheets, got {len(ponoko_sheets)}"


# =============================================================================
# Only Ponoko's two colors present anywhere -- no gray reference text
# (there IS no text at all), no stray colors
# =============================================================================

def test_ponoko_sheets_have_no_text_elements(ponoko_sheets):
    for sheet in ponoko_sheets:
        pieces = _sheet_pieces(sheet)
        assert pieces, f"{sheet.name}: no pieces found"
        offenders = [p.label for p in pieces if p.has_text]
        assert not offenders, f"{sheet.name}: pieces still carry <text>: {offenders}"


def test_ponoko_sheets_use_only_the_two_ponoko_colors(ponoko_sheets):
    allowed = {"blue", "red"}
    for sheet in ponoko_sheets:
        offenders = []
        for piece in _sheet_pieces(sheet):
            bad = piece.colors - allowed
            if bad:
                offenders.append((piece.label, bad))
        assert not offenders, f"{sheet.name}: non-Ponoko colors found: {offenders}"


def test_ponoko_sheets_no_gray_anywhere(ponoko_sheets):
    """Defensive, independent of the no-<text> check above: no path or
    element anywhere in a Ponoko sheet should carry the NYCR gray reference-
    label color (rgb(128,128,128))."""
    for sheet in ponoko_sheets:
        text = sheet.read_text()
        assert "128,128,128" not in text, f"{sheet.name}: found NYCR gray reference-label color"


# =============================================================================
# Part count: 21 NYCR parts (8 shell + 12 drawer + 1 lid) + 1 turn button +
# 1 self-calibration coupon = 23
# =============================================================================

def test_ponoko_part_count_matches(ponoko_sheets):
    pieces = _all_sheet_pieces(ponoko_sheets)
    assert len(pieces) == fl.PONOKO_EXPECTED_PARTS + fl.PONOKO_EXPECTED_COUPONS

    by_source = Counter(p.label.split(":", 1)[0] for p in pieces)
    assert by_source["Shell"] == 8
    assert by_source["Drawer 1"] == 6
    assert by_source["Drawer 2"] == 6
    assert by_source["Lid"] == 1
    assert by_source["Hardware"] == 1
    assert by_source["Calibration"] == 1


def test_ponoko_no_overlapping_pieces(ponoko_sheets):
    for sheet in ponoko_sheets:
        pieces = _sheet_pieces(sheet)
        offenders = []
        for i in range(len(pieces)):
            for j in range(i + 1, len(pieces)):
                if pieces[i].bbox.overlaps(pieces[j].bbox):
                    offenders.append((pieces[i].label, pieces[j].label))
        assert not offenders, f"overlapping piece bboxes in {sheet.name}: {offenders}"


# =============================================================================
# Engrave (red) content only where DESIGN.md places it: the right wall's
# "FAX MACHINE" text and each drawer's faceplate registration outline --
# same rule test_laser_requirements.py enforces for the NYCR default.
# =============================================================================

def test_ponoko_engrave_only_on_right_wall_and_faceplates(ponoko_sheets):
    pieces = _all_sheet_pieces(ponoko_sheets)
    red_labels = {p.label for p in pieces if "red" in p.colors}
    assert red_labels == {"Shell: Right Wall", "Drawer 1: Faceplate", "Drawer 2: Faceplate"}


# =============================================================================
# Kerf square: drawn tool path at EXACT nominal 10.0mm (burn-neutral), same
# principle as the NYCR kerf coupon -- see calibration.py's
# PonokoCalibrationCoupon docstring.
# =============================================================================

def test_ponoko_kerf_square_at_exact_nominal(ponoko_sheets):
    square_holes = []
    for sheet in ponoko_sheets:
        for piece in su.get_pieces(sheet):
            square_holes += [h for h in piece.holes if h.bbox.dims_match(10.0, 10.0, tol=0.5)]
    assert len(square_holes) == 1, (
        f"expected exactly 1 ~10x10mm kerf-square hole across all Ponoko sheets, found {len(square_holes)}"
    )
    hole = square_holes[0]
    assert abs(hole.bbox.width - 10.0) <= 0.01, f"kerf square width {hole.bbox.width} != 10.0 nominal"
    assert abs(hole.bbox.height - 10.0) <= 0.01, f"kerf square height {hole.bbox.height} != 10.0 nominal"


def test_ponoko_magnet_gauge_holes_present(ponoko_sheets):
    """4 magnet press-fit gauge holes (5.5/5.65/5.8/5.95mm), burn-
    compensated with the Ponoko provider's own burn -- see
    calibration.PONOKO_MAGNET_DIAMETERS. Scoped to the Calibration coupon
    piece's own bbox: the real parts also carry ~5.65mm magnet holes (the
    divider's 2 + each drawer Back's 1 = 4 more), which must NOT be
    counted here."""
    from faxbox import calibration as cal

    expected_diams = sorted(cal.PONOKO_MAGNET_DIAMETERS)
    drawn_expected = sorted(d - 2 * PONOKO_CFG["burn"] for d in expected_diams)

    # Locate the Calibration coupon's bbox via its <g data-part=...> stamp.
    coupon_bboxes = [
        p.bbox
        for sheet in ponoko_sheets
        for p in _sheet_pieces(sheet)
        if p.label.startswith("Calibration")
    ]
    assert len(coupon_bboxes) == 1, f"expected exactly 1 Calibration piece, found {len(coupon_bboxes)}"
    coupon_bbox = coupon_bboxes[0]

    gauge_holes = []
    for sheet in ponoko_sheets:
        for piece in su.get_pieces(sheet):
            gauge_holes += [
                h for h in piece.holes
                if 4.5 <= h.bbox.width <= 6.5
                and h.bbox.dims_match(h.bbox.width, h.bbox.width, tol=0.05)
                and coupon_bbox.contains(h.bbox, tol=0.2)
            ]
    assert len(gauge_holes) == 4, f"expected 4 magnet gauge holes on the coupon, found {len(gauge_holes)}"
    measured = sorted(h.bbox.width for h in gauge_holes)
    for m, expected in zip(measured, drawn_expected):
        assert abs(m - expected) <= 0.05, (
            f"gauge hole measured {m:.3f}mm, expected ~{expected:.3f}mm (nominal - 2*ponoko_burn)"
        )


# =============================================================================
# Provider BURN is actually applied: a finger-jointed piece's drawn bbox
# (both axes jointed -- e.g. Shell's "Bottom" panel, all 4 edges 'f') grows
# by exactly 2*(ponoko_burn - nycr_burn) per axis relative to the NYCR
# default, since each of the piece's two opposite jointed edges shifts its
# tab tip outward by (ponoko_burn - nycr_burn) -- verified empirically
# against the actual generator output before being encoded as an exact
# assertion here (not assumed from Boxes.py internals).
# =============================================================================

def test_burn_actually_changes_drawn_geometry(ponoko_sheets):
    nycr_shell = OUTPUT_DIR / "outer_shell.svg"
    ponoko_shell = PONOKO_DIR / "outer_shell.svg"
    assert nycr_shell.exists(), "regenerate_svgs should have produced output/outer_shell.svg"
    assert ponoko_shell.exists(), "faxbox.ponoko should have produced output/ponoko/outer_shell.svg"

    nycr_piece = su.find_piece_by_label(su.design_pieces(nycr_shell), "Bottom")
    ponoko_piece = su.find_piece_by_label(su.design_pieces(ponoko_shell), "Bottom")
    assert nycr_piece is not None and ponoko_piece is not None

    expected_delta = 2 * (PONOKO_CFG["burn"] - NYCR_CFG["burn"])
    assert expected_delta > 0, "test assumes Ponoko's burn is larger than NYCR's default (0.10 > 0.08)"

    width_delta = ponoko_piece.bbox.width - nycr_piece.bbox.width
    height_delta = ponoko_piece.bbox.height - nycr_piece.bbox.height
    assert abs(width_delta - expected_delta) <= 0.01, (
        f"Bottom panel width delta {width_delta:.4f}mm != expected {expected_delta:.4f}mm "
        "(2 * (ponoko_burn - nycr_burn)) -- provider BURN may not be reaching the generator"
    )
    assert abs(height_delta - expected_delta) <= 0.01, (
        f"Bottom panel height delta {height_delta:.4f}mm != expected {expected_delta:.4f}mm "
        "(2 * (ponoko_burn - nycr_burn)) -- provider BURN may not be reaching the generator"
    )


# =============================================================================
# The NYCR default path is untouched: output/*.svg (not output/ponoko/*)
# still exists and is what conftest.py's regenerate_svgs always produces.
# =============================================================================

def test_nycr_default_output_dir_unaffected(ponoko_sheets):
    assert (OUTPUT_DIR / "outer_shell.svg").exists()
    assert (OUTPUT_DIR / "drawer.svg").exists()
    assert (OUTPUT_DIR / "lids.svg").exists()
    # The Ponoko run must not have written anything into the plain output/
    # directory itself (only output/ponoko/).
    assert not (OUTPUT_DIR / "calibration_coupon.svg").exists()
