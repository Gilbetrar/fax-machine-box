"""Unit tests for tests/svg_utils.py measurement helpers.

These run entirely against small, hand-written synthetic SVG fixtures (never
against output/*.svg) so they exercise the parsing/clustering/color logic in
isolation from whatever the real generators currently produce.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import svg_utils as su


def write_svg(tmp_path: Path, body: str, width: str = "50mm", height: str = "50mm") -> Path:
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 50 50">\n{body}\n</svg>\n'
    )
    path = tmp_path / "synthetic.svg"
    path.write_text(svg)
    return path


# --- normalize_color ----------------------------------------------------------

@pytest.mark.parametrize(
    "value,expected",
    [
        ("rgb(0,0,255)", "blue"),
        ("#0000FF", "blue"),
        ("#0000ff", "blue"),
        ("blue", "blue"),
        ("  rgb(0, 0, 255) ", "blue"),
        ("rgb(255,0,0)", "red"),
        ("#FF0000", "red"),
        ("red", "red"),
        ("rgb(0,0,0)", "black"),
        ("#000000", "black"),
        ("black", "black"),
        (None, "none"),
        ("rgb(0,255,0)", "other:rgb(0,255,0)"),
    ],
)
def test_normalize_color(value, expected):
    assert su.normalize_color(value) == expected


# --- BBox -----------------------------------------------------------------------

def test_bbox_dims_match_exact_and_rotated():
    box = su.BBox(0, 10, 0, 4)
    assert box.dims_match(10, 4)
    assert box.dims_match(4, 10)  # rotated orientation also matches
    assert not box.dims_match(10, 5, tol=0.4)


def test_bbox_dims_match_within_tolerance():
    box = su.BBox(0, 10.3, 0, 4)
    assert box.dims_match(10, 4, tol=0.5)
    assert not box.dims_match(10, 4, tol=0.1)


def test_bbox_contains():
    outer = su.BBox(0, 100, 0, 100)
    inner = su.BBox(10, 20, 10, 20)
    partial = su.BBox(-5, 20, 10, 20)
    assert outer.contains(inner)
    assert not outer.contains(partial)
    assert not inner.contains(outer)


def test_bbox_overlaps_true_for_shared_area():
    a = su.BBox(0, 10, 0, 10)
    b = su.BBox(5, 15, 5, 15)
    assert a.overlaps(b)
    assert b.overlaps(a)


def test_bbox_overlaps_false_for_disjoint():
    a = su.BBox(0, 10, 0, 10)
    b = su.BBox(20, 30, 20, 30)
    assert not a.overlaps(b)


def test_bbox_overlaps_false_for_edge_touch():
    """Two pieces sharing an edge (packed layout, no gap) should not count
    as overlapping -- only genuine shared area is a bug."""
    a = su.BBox(0, 10, 0, 10)
    b = su.BBox(10, 20, 0, 10)
    assert not a.overlaps(b)


# --- get_svg_dimensions_mm -------------------------------------------------------

def test_get_svg_dimensions_mm(tmp_path):
    path = write_svg(tmp_path, "", width="123.4mm", height="56.7mm")
    assert su.get_svg_dimensions_mm(path) == (123.4, 56.7)


def test_get_svg_dimensions_mm_rejects_non_mm_units(tmp_path):
    path = write_svg(tmp_path, "", width="123.4", height="56.7")
    with pytest.raises(ValueError):
        su.get_svg_dimensions_mm(path)


def test_get_svg_dimensions_mm_rejects_inches(tmp_path):
    path = write_svg(tmp_path, "", width="4.86in", height="2.23in")
    with pytest.raises(ValueError):
        su.get_svg_dimensions_mm(path)


# --- iter_paths / cluster_pieces --------------------------------------------------

RECT_OUTER = 'M 0 0 H 40 V 30 H 0 Z'
RECT_HOLE_A = 'M 5 5 H 15 V 10 H 5 Z'
RECT_HOLE_B = 'M 20 15 H 25 V 20 H 20 Z'


def test_iter_paths_finds_all_paths_and_labels(tmp_path):
    body = f'''
    <g id="p-0"><text>Part One</text>
      <path d="{RECT_OUTER}" stroke="rgb(0,0,255)" />
      <path d="{RECT_HOLE_A}" stroke="rgb(0,0,255)" />
    </g>
    '''
    path = write_svg(tmp_path, body)
    paths = su.iter_paths(path)
    assert len(paths) == 2
    assert all(p.label == "Part One" for p in paths)


def test_cluster_pieces_single_piece_with_hole(tmp_path):
    body = f'''
    <g id="p-0">
      <path d="{RECT_OUTER}" stroke="rgb(0,0,255)" />
      <path d="{RECT_HOLE_A}" stroke="rgb(0,0,255)" />
    </g>
    '''
    path = write_svg(tmp_path, body)
    pieces = su.get_pieces(path)
    assert len(pieces) == 1
    piece = pieces[0]
    assert piece.bbox.dims_match(40, 30)
    assert len(piece.holes) == 1
    assert piece.holes[0].bbox.dims_match(10, 5)


def test_cluster_pieces_two_separate_pieces_no_overlap(tmp_path):
    body = f'''
    <g id="p-0"><path d="{RECT_OUTER}" stroke="rgb(0,0,255)" /></g>
    <g id="p-1"><path d="M 50 0 H 60 V 10 H 50 Z" stroke="rgb(0,0,255)" /></g>
    '''
    path = write_svg(tmp_path, body)
    pieces = su.get_pieces(path)
    assert len(pieces) == 2
    a, b = pieces[0].bbox, pieces[1].bbox
    assert not a.overlaps(b)


def test_cluster_pieces_full_size_nested_bbox_stays_two_pieces(tmp_path):
    """A layout bug (missing/short move=) can place one full-size piece's
    bbox entirely inside another's. That must surface as two overlapping
    pieces (so the overlap check catches it), not get silently absorbed as
    one piece with a giant "hole" -- see HOLE_AREA_RATIO."""
    container = 'M 0 0 H 100 V 60 H 0 Z'              # 100 x 60, area 6000
    nested_same_scale = 'M 10 10 H 90 V 50 H 10 Z'    # 80 x 40, area 3200 (>50% of 6000)
    body = f'''
    <g id="p-0"><text>Bottom</text><path d="{container}" stroke="rgb(0,0,255)" /></g>
    <g id="p-1"><text>Back Wall</text><path d="{nested_same_scale}" stroke="rgb(0,0,255)" /></g>
    '''
    path = write_svg(tmp_path, body, width="100mm", height="60mm")
    pieces = su.get_pieces(path)
    assert len(pieces) == 2
    assert pieces[0].bbox.overlaps(pieces[1].bbox)


def test_cluster_pieces_small_hole_still_absorbed(tmp_path):
    """Sanity check that the area-ratio guard doesn't break the ordinary
    case: a genuinely small hole is still folded into its host piece."""
    container = 'M 0 0 H 100 V 60 H 0 Z'          # area 6000
    small_hole = 'M 10 10 H 20 V 20 H 10 Z'       # 10 x 10, area 100 (<50%)
    body = f'''
    <g id="p-0">
      <path d="{container}" stroke="rgb(0,0,255)" />
      <path d="{small_hole}" stroke="rgb(0,0,255)" />
    </g>
    '''
    path = write_svg(tmp_path, body, width="100mm", height="60mm")
    pieces = su.get_pieces(path)
    assert len(pieces) == 1
    assert len(pieces[0].holes) == 1


def test_cluster_pieces_holes_assigned_to_smallest_container(tmp_path):
    """A hole nested inside a hole nested inside the outer boundary should be
    assigned to its *immediate* (smallest) container, not the top-level
    piece directly -- both end up as `holes` of the one piece, but this
    guards against double-counting if clustering logic changes."""
    inner_hole = 'M 6 6 H 9 V 8 H 6 Z'
    body = f'''
    <g id="p-0">
      <path d="{RECT_OUTER}" stroke="rgb(0,0,255)" />
      <path d="{RECT_HOLE_A}" stroke="rgb(0,0,255)" />
      <path d="{inner_hole}" stroke="rgb(0,0,255)" />
    </g>
    '''
    path = write_svg(tmp_path, body)
    pieces = su.get_pieces(path)
    assert len(pieces) == 1
    assert len(pieces[0].holes) == 2


# --- is_reference_mark / design_pieces --------------------------------------------

def test_is_reference_mark_detects_boxes_calibration_rect(tmp_path):
    ref = 'M 0 0 H 100 V 10 H 0 Z'
    body = f'''
    <g id="p-0"><text>100.0mm, burn:0.08mm</text>
      <path d="{ref}" stroke="rgb(0,0,0)" />
    </g>
    <g id="p-1"><path d="{RECT_OUTER}" stroke="rgb(0,0,255)" /></g>
    '''
    path = write_svg(tmp_path, body)
    pieces = su.get_pieces(path)
    marks = [p for p in pieces if su.is_reference_mark(p)]
    assert len(marks) == 1
    assert marks[0].bbox.dims_match(100, 10)

    design = su.design_pieces(path)
    assert len(design) == 1
    assert design[0].bbox.dims_match(40, 30)


def test_is_reference_mark_false_for_normal_part(tmp_path):
    body = f'<g id="p-0"><path d="{RECT_OUTER}" stroke="rgb(0,0,255)" /></g>'
    path = write_svg(tmp_path, body)
    piece = su.get_pieces(path)[0]
    assert not su.is_reference_mark(piece)


def test_is_reference_mark_false_when_piece_has_holes():
    """Even a 100x10mm piece shouldn't be treated as the calibration mark if
    it has interior holes -- the real mark never does."""
    outer = su.PathInfo(d="", stroke="rgb(0,0,0)", bbox=su.BBox(0, 100, 0, 10))
    hole = su.PathInfo(d="", stroke="rgb(0,0,0)", bbox=su.BBox(1, 2, 1, 2))
    piece = su.Piece(outer=outer, holes=[hole])
    assert not su.is_reference_mark(piece)


# --- find_piece_by_label ----------------------------------------------------------

def test_find_piece_by_label_case_insensitive(tmp_path):
    body = f'''
    <g id="p-0"><text>Rear Wall</text><path d="{RECT_OUTER}" stroke="rgb(0,0,255)" /></g>
    '''
    path = write_svg(tmp_path, body)
    pieces = su.get_pieces(path)
    found = su.find_piece_by_label(pieces, "rear wall", "back wall")
    assert found is not None
    assert found.label == "Rear Wall"


def test_find_piece_by_label_returns_none_when_absent(tmp_path):
    body = f'<g id="p-0"><text>Front Wall</text><path d="{RECT_OUTER}" stroke="rgb(0,0,255)" /></g>'
    path = write_svg(tmp_path, body)
    pieces = su.get_pieces(path)
    assert su.find_piece_by_label(pieces, "rear wall") is None


# --- color audit helpers ----------------------------------------------------------

def test_any_black_strokes_detects_black_in_any_format(tmp_path):
    body = f'''
    <g id="p-0">
      <path d="{RECT_OUTER}" stroke="rgb(0,0,255)" />
      <path d="{RECT_HOLE_A}" stroke="#000000" />
    </g>
    '''
    path = write_svg(tmp_path, body)
    black = su.any_black_strokes(path)
    assert len(black) == 1
    assert black[0].bbox.dims_match(10, 5)


def test_any_black_strokes_empty_when_none(tmp_path):
    body = f'<g id="p-0"><path d="{RECT_OUTER}" stroke="rgb(0,0,255)" /></g>'
    path = write_svg(tmp_path, body)
    assert su.any_black_strokes(path) == []


def test_non_cut_engrave_strokes_flags_black_and_other_colors(tmp_path):
    body = f'''
    <g id="p-0">
      <path d="{RECT_OUTER}" stroke="rgb(0,0,255)" />
      <path d="{RECT_HOLE_A}" stroke="rgb(0,0,0)" />
      <path d="{RECT_HOLE_B}" stroke="rgb(0,255,0)" />
    </g>
    '''
    path = write_svg(tmp_path, body)
    bad = su.non_cut_engrave_strokes(path)
    assert len(bad) == 2


def test_non_cut_engrave_strokes_empty_when_all_blue_and_red(tmp_path):
    body = f'''
    <g id="p-0">
      <path d="{RECT_OUTER}" stroke="rgb(0,0,255)" />
      <path d="{RECT_HOLE_A}" stroke="rgb(255,0,0)" />
    </g>
    '''
    path = write_svg(tmp_path, body)
    assert su.non_cut_engrave_strokes(path) == []


# --- expected_band -----------------------------------------------------------------

def test_expected_band_no_jointed_edges_is_slack_only():
    assert su.expected_band(100.0, 0, 3.175) == pytest.approx((99.5, 100.5))


def test_expected_band_one_jointed_edge_adds_one_thickness():
    lo, hi = su.expected_band(100.0, 1, 3.175)
    assert lo == pytest.approx(99.5)
    assert hi == pytest.approx(100.0 + 3.175 + 0.5)


def test_expected_band_two_jointed_edges_adds_two_thicknesses():
    lo, hi = su.expected_band(100.0, 2, 3.175)
    assert lo == pytest.approx(99.5)
    assert hi == pytest.approx(100.0 + 2 * 3.175 + 0.5)


def test_expected_band_rejects_invalid_edge_count():
    with pytest.raises(ValueError):
        su.expected_band(100.0, 3, 3.175)
