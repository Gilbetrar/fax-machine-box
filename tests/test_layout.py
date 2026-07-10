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

import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import pytest

import svg_utils as su
from faxbox import config
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
    from faxbox import calibration as cal

    pieces = su.get_pieces(kerf_coupon_svg)
    assert len(pieces) == 1, f"expected exactly 1 piece on the coupon, found {len(pieces)}"
    expected_holes = len(cal.SLOT_WIDTHS) + 1  # 5 fit-test slots + 1 kerf-test hole
    assert len(pieces[0].holes) == expected_holes, (
        f"expected {len(cal.SLOT_WIDTHS)} fit-test slots + 1 kerf-test hole = "
        f"{expected_holes} holes, found {len(pieces[0].holes)}"
    )


def test_kerf_coupon_slot_widths_widened_to_five_gauges():
    """Adversarial-QA fix: the original 3-slot gauge (3.05 / T / 3.30) left
    real stock measuring 3.35-3.4mm -- squarely inside the documented
    3.0-3.4mm plywood band (DESIGN.md) -- fitting NO slot at all. The gauge
    now spans strictly past both ends of that documented band."""
    from faxbox import calibration as cal
    from faxbox import config as c

    assert cal.SLOT_WIDTHS == (2.95, 3.05, c.MATERIAL_THICKNESS, 3.30, 3.40)


def test_kerf_coupon_slot_widths_match_burn_compensated_nominal(kerf_coupon_svg):
    """5 thickness slots, each measured flat-to-flat on the generated SVG,
    must equal (label - 2*burn) -- i.e. the physical (post-kerf) width
    equals the labeled nominal, same burn-compensated-hole relationship the
    magnet gauge coupon uses (see calibration.py's magnet-coupon docstring)."""
    from faxbox import calibration as cal
    from faxbox import config as c

    T = c.MATERIAL_THICKNESS
    piece = su.get_pieces(kerf_coupon_svg)[0]
    slot_holes = sorted(piece.holes, key=lambda h: h.bbox.xmin)[: len(cal.SLOT_WIDTHS)]
    assert len(cal.SLOT_WIDTHS) == 5
    assert len(slot_holes) == 5
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


# =============================================================================
# Bed-size parameterization (defect: generate_layout() used to hardcode the
# NYC Resistor bed and take no arguments, so rebuilding for a different laser
# bed required editing source). generate_layout() now resolves
# sheet_width/sheet_height/margin/spacing as: explicit kwarg >
# FAXBOX_SHEET_WIDTH/FAXBOX_SHEET_HEIGHT env var (width/height only) >
# resolved provider's config.PROVIDERS[...] entry (width/height only) > this
# module's SHEET_WIDTH_MM/SHEET_HEIGHT_MM/MARGIN_MM/SPACING_MM defaults --
# see generate_layout()'s docstring.
#
# Largest single part (Shell: Bottom) measures 304.96mm x 165.26mm (three
# panels -- Bottom, Left Wall, Right Wall -- share the 304.96mm length,
# confirmed by direct measurement below); with this module's 10mm margins on
# both sides, 324.96mm x 185.26mm is the smallest bed that can cut every
# part at all. _pack_pieces must keep failing loudly (ValueError naming the
# offending part) below that, per its own docstring contract.
# =============================================================================

MIN_VIABLE_BED_WIDTH = 324.96
MIN_VIABLE_BED_HEIGHT = 185.26


def _all_source_pieces() -> list[fl.Piece]:
    """Load all 21 real pieces (no packing/nesting) straight from the
    regenerated source SVGs -- for tests that only care about _pack_pieces'
    behavior at a given bed size, not the full sheet_*.svg pipeline."""
    shell_svg, drawer_svg, lids_svg = fl._require_source_svgs(OUTPUT_DIR)
    pieces: list[fl.Piece] = []
    pieces += fl._load_pieces(shell_svg, "Shell")
    pieces += fl._load_pieces(drawer_svg, "Drawer 1")
    pieces += fl._load_pieces(drawer_svg, "Drawer 2")
    pieces += fl._load_pieces(lids_svg, "Lid")
    return pieces


def _assert_no_overlaps_and_margins_held(sheets: list[list[fl.Placement]], margin: float) -> None:
    tol = 1e-6
    for placements in sheets:
        for p in placements:
            assert p.x >= margin - tol, f"{p.piece.label!r} x={p.x} violates {margin}mm margin"
            assert p.y >= margin - tol, f"{p.piece.label!r} y={p.y} violates {margin}mm margin"
        for i in range(len(placements)):
            a = placements[i]
            a_box = (a.x, a.y, a.x + a.piece.width, a.y + a.piece.height)
            for j in range(i + 1, len(placements)):
                b = placements[j]
                b_box = (b.x, b.y, b.x + b.piece.width, b.y + b.piece.height)
                overlap = not (
                    a_box[2] <= b_box[0] + tol
                    or b_box[2] <= a_box[0] + tol
                    or a_box[3] <= b_box[1] + tol
                    or b_box[3] <= a_box[1] + tol
                )
                assert not overlap, f"overlap: {a.piece.label!r} vs {b.piece.label!r}"


def test_largest_part_measures_304_96_by_165_26mm(regenerate_svgs):
    pieces = _all_source_pieces()
    largest = max(pieces, key=lambda p: p.width * p.height)
    assert largest.source == "Shell" and largest.label == "Bottom"
    assert largest.width == pytest.approx(304.96, abs=0.01)
    assert largest.height == pytest.approx(165.26, abs=0.01)


def test_pack_pieces_at_reduced_bed_places_all_21_no_overlap(regenerate_svgs):
    pieces = _all_source_pieces()
    sheets = fl._pack_pieces(pieces, sheet_width=458.0, sheet_height=304.0)
    assert sum(len(s) for s in sheets) == 21
    _assert_no_overlaps_and_margins_held(sheets, fl.MARGIN_MM)


def test_pack_pieces_at_exact_minimum_viable_bed_places_all_21_no_overlap(regenerate_svgs):
    pieces = _all_source_pieces()
    sheets = fl._pack_pieces(pieces, sheet_width=MIN_VIABLE_BED_WIDTH, sheet_height=MIN_VIABLE_BED_HEIGHT)
    assert sum(len(s) for s in sheets) == 21
    _assert_no_overlaps_and_margins_held(sheets, fl.MARGIN_MM)


def test_pack_pieces_one_epsilon_below_minimum_bed_raises_naming_part(regenerate_svgs):
    pieces = _all_source_pieces()
    with pytest.raises(ValueError, match="Bottom"):
        fl._pack_pieces(pieces, sheet_width=MIN_VIABLE_BED_WIDTH - 0.1, sheet_height=MIN_VIABLE_BED_HEIGHT)


def test_pack_pieces_300x200_bed_raises(regenerate_svgs):
    pieces = _all_source_pieces()
    with pytest.raises(ValueError):
        fl._pack_pieces(pieces, sheet_width=300.0, sheet_height=200.0)


def test_resolve_dimension_precedence_explicit_beats_env_beats_provider_beats_default(monkeypatch):
    provider_cfg = {"sheet_width": 111.0}
    monkeypatch.setenv("FAXBOX_SHEET_WIDTH", "222.0")
    # explicit kwarg wins over everything
    assert fl._resolve_dimension(333.0, "FAXBOX_SHEET_WIDTH", provider_cfg, "sheet_width", 999.0) == 333.0
    # env wins over provider
    assert fl._resolve_dimension(None, "FAXBOX_SHEET_WIDTH", provider_cfg, "sheet_width", 999.0) == 222.0
    monkeypatch.delenv("FAXBOX_SHEET_WIDTH")
    # provider wins over default
    assert fl._resolve_dimension(None, "FAXBOX_SHEET_WIDTH", provider_cfg, "sheet_width", 999.0) == 111.0
    # default when nothing else is set
    assert fl._resolve_dimension(None, "FAXBOX_SHEET_WIDTH", {}, "sheet_width", 999.0) == 999.0


def test_generate_layout_bed_size_precedence_explicit_beats_env_beats_provider(tmp_path, monkeypatch, regenerate_svgs):
    """End-to-end version of the precedence test above: drives the real
    generate_layout() (redirected to a scratch output dir so this never
    touches the shared output/ directory other tests read) and checks which
    sheet_width/sheet_height/margin/spacing actually reach _pack_pieces."""
    for name in ("outer_shell.svg", "drawer.svg", "lids.svg"):
        shutil.copy(OUTPUT_DIR / name, tmp_path / name)
    monkeypatch.setattr(fl, "OUTPUT_DIR", str(tmp_path))

    orig_pack = fl._pack_pieces
    captured: dict[str, float] = {}

    def fake_pack(pieces, sheet_width=fl.SHEET_WIDTH_MM, sheet_height=fl.SHEET_HEIGHT_MM,
                  margin=fl.MARGIN_MM, spacing=fl.SPACING_MM):
        captured.update(sheet_width=sheet_width, sheet_height=sheet_height, margin=margin, spacing=spacing)
        return orig_pack(pieces, sheet_width=sheet_width, sheet_height=sheet_height, margin=margin, spacing=spacing)

    monkeypatch.setattr(fl, "_pack_pieces", fake_pack)

    fake_providers = dict(config.PROVIDERS)
    fake_providers["_test_provider"] = {**config.PROVIDERS["nycr"], "sheet_width": 500.0, "sheet_height": 400.0}
    monkeypatch.setattr(config, "PROVIDERS", fake_providers)

    # provider only (no explicit kwarg, no env var)
    fl.generate_layout(provider="_test_provider")
    assert (captured["sheet_width"], captured["sheet_height"]) == (500.0, 400.0)

    # env var beats provider
    monkeypatch.setenv("FAXBOX_SHEET_WIDTH", "550.0")
    monkeypatch.setenv("FAXBOX_SHEET_HEIGHT", "450.0")
    fl.generate_layout(provider="_test_provider")
    assert (captured["sheet_width"], captured["sheet_height"]) == (550.0, 450.0)

    # explicit kwarg beats env var; margin/spacing are explicit-or-default only
    fl.generate_layout(provider="_test_provider", sheet_width=600.0, sheet_height=490.0, margin=12.0, spacing=6.0)
    assert (captured["sheet_width"], captured["sheet_height"]) == (600.0, 490.0)
    assert (captured["margin"], captured["spacing"]) == (12.0, 6.0)


# =============================================================================
# Unknown provider fails loudly (defect: layout.py's __main__ used to
# silently ignore an unrecognized FAXBOX_PROVIDER and run the default nycr
# path instead of raising, unlike every faxbox.generate_*() entry point).
# =============================================================================

def test_generate_layout_unknown_provider_raises_keyerror():
    with pytest.raises(KeyError):
        fl.generate_layout(provider="definitely-not-a-real-provider")


def test_main_fails_loudly_on_unknown_provider():
    env = dict(os.environ)
    env["FAXBOX_PROVIDER"] = "definitely-not-a-real-provider"
    result = subprocess.run(
        [sys.executable, "-m", "faxbox.layout"],
        cwd=REPO_ROOT,
        capture_output=True,
        env=env,
    )
    assert result.returncode != 0, "unknown provider must fail loudly, not silently fall back to nycr"
    assert "definitely-not-a-real-provider" in result.stderr.decode()


# =============================================================================
# Stale-sheet purge (defect found in adversarial pass 2: a rebuild for a
# smaller bed writes MORE sheets, and a later default rebuild wrote only
# sheet_1..3 while leaving sheet_4..N from the previous run on disk --
# stale, cut-ready-looking files next to fresh ones, which also
# contaminated every test that globs output/sheet_*.svg).
# =============================================================================

def test_generate_layout_purges_stale_sheets_from_previous_run():
    out = REPO_ROOT / "output"
    # A small bed legitimately produces more than 3 sheets...
    many = fl.generate_layout(sheet_width=458.0, sheet_height=304.0)
    assert len(many) > 3
    # ...and a subsequent default run must leave ONLY its own sheets behind.
    default = fl.generate_layout()
    on_disk = sorted(p.name for p in out.glob("sheet_*.svg"))
    assert on_disk == sorted(p.name for p in default), (
        f"stale sheets from a previous nesting survived a rebuild: {on_disk}"
    )
