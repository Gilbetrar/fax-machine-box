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


# --- hole_line_spans -------------------------------------------------------------

def _hole(x0, x1, y0, y1):
    return su.PathInfo(d="", stroke="rgb(0,0,255)", bbox=su.BBox(x0, x1, y0, y1))


def test_hole_line_spans_horizontal_row():
    t = 3.0
    # Dashed row at y=10..13: three dashes spanning x=5..95.
    row = [_hole(5, 25, 10, 13), _hole(40, 60, 10, 13), _hole(75, 95, 10, 13)]
    spans = su.hole_line_spans(row, t, axis="x")
    assert spans == [pytest.approx(90.0)]


def test_hole_line_spans_vertical_row_and_grouping():
    t = 3.0
    # One vertical row at x=10, plus a second distinct row at x=50.
    rows = [
        _hole(10, 13, 0, 20), _hole(10, 13, 30, 50),
        _hole(50, 53, 5, 15), _hole(50, 53, 25, 35),
    ]
    spans = sorted(su.hole_line_spans(rows, t, axis="y"))
    assert spans == [pytest.approx(30.0), pytest.approx(50.0)]


def test_hole_line_spans_ignores_wrong_thickness_and_singletons():
    t = 3.0
    mixed = [
        _hole(0, 40, 10, 25),   # 15 tall: not a finger row (wrong thickness)
        _hole(60, 80, 10, 13),  # right thickness but alone in its row
    ]
    assert su.hole_line_spans(mixed, t, axis="x") == []


# --- hole_line_rows (span + cross-axis center) ------------------------------------

def test_hole_line_rows_horizontal_row_reports_span_and_y_center():
    t = 3.0
    # Dashed row at y=10..13 (cross-axis center 11.5): three dashes x=5..95.
    row = [_hole(5, 25, 10, 13), _hole(40, 60, 10, 13), _hole(75, 95, 10, 13)]
    rows = su.hole_line_rows(row, t, axis="x")
    assert len(rows) == 1
    assert rows[0].span == pytest.approx(90.0)
    assert rows[0].center == pytest.approx(11.5)
    assert rows[0].lo == pytest.approx(5.0)
    assert rows[0].hi == pytest.approx(95.0)


def test_hole_line_rows_vertical_row_reports_span_and_x_center():
    t = 3.0
    rows = su.hole_line_rows(
        [_hole(10, 13, 0, 20), _hole(10, 13, 30, 50)], t, axis="y",
    )
    assert len(rows) == 1
    assert rows[0].span == pytest.approx(50.0)
    assert rows[0].center == pytest.approx(11.5)  # x-center of 10..13


def test_hole_line_rows_distinguishes_rows_by_cross_center():
    t = 3.0
    rows = su.hole_line_rows(
        [
            _hole(10, 13, 0, 20), _hole(10, 13, 30, 50),   # row at x~11.5
            _hole(50, 53, 5, 15), _hole(50, 53, 25, 35),   # row at x~51.5
        ],
        t, axis="y",
    )
    centers = sorted(r.center for r in rows)
    assert centers == [pytest.approx(11.5), pytest.approx(51.5)]


def test_hole_line_spans_still_matches_hole_line_rows_spans():
    """hole_line_spans is now a thin wrapper over hole_line_rows -- the
    original API keeps returning exactly the span list it always did."""
    t = 3.0
    row = [_hole(5, 25, 10, 13), _hole(40, 60, 10, 13), _hole(75, 95, 10, 13)]
    assert su.hole_line_spans(row, t, axis="x") == [r.span for r in su.hole_line_rows(row, t, axis="x")]


# --- edge_teeth_centers -------------------------------------------------------------

def _rect_path(x0, x1, y0, y1):
    return f"M {x0} {y0} H {x1} V {y1} H {x0} Z"


def _fingered_edge_path(y_top, y_bottom, x0, tooth, gap, n_teeth):
    """Build a closed rectangle path whose TOP edge (y=y_top) is a row of
    `n_teeth` square finger tips (width `tooth`, i.e. protruding notches),
    separated by `gap`-wide flat segments at y=y_top - tooth (a crude but
    sufficient synthetic finger-joint boundary for exercising
    edge_teeth_centers: alternating short horizontal runs at the two
    y-levels), so both this fixture and the parser only need Line segments.
    """
    parts = [f"M {x0} {y_bottom}", f"L {x0} {y_top}"]
    x = x0
    for i in range(n_teeth):
        parts.append(f"L {x + tooth} {y_top}")           # tooth top edge
        parts.append(f"L {x + tooth} {y_top - tooth}")   # up into the tooth
        parts.append(f"L {x + tooth + gap} {y_top - tooth}")  # notch bottom
        parts.append(f"L {x + tooth + gap} {y_top}")      # back down
        x += tooth + gap
    parts.append(f"L {x} {y_bottom}")
    parts.append("Z")
    return " ".join(parts)


def test_edge_teeth_centers_finds_top_edge_tooth_tips(tmp_path):
    # A simple rectangle with 3 evenly spaced 4mm-wide tabs sticking up from
    # its top edge (y=0), each centered at x=5, 15, 25.
    path_d = (
        "M 0 20 L 0 0 "
        "L 3 0 L 3 -4 L 7 -4 L 7 0 "
        "L 13 0 L 13 -4 L 17 -4 L 17 0 "
        "L 23 0 L 23 -4 L 27 -4 L 27 0 "
        "L 40 0 L 40 20 Z"
    )
    body = f'<g id="p-0"><path d="{path_d}" stroke="rgb(0,0,255)" /></g>'
    svg = write_svg(tmp_path, body, width="50mm", height="30mm")
    piece = su.get_pieces(svg)[0]
    assert piece.bbox.ymin == pytest.approx(-4.0)
    centers = sorted(su.edge_teeth_centers(piece, "top"))
    assert centers == [pytest.approx(5.0), pytest.approx(15.0), pytest.approx(25.0)]


def test_edge_teeth_centers_ignores_segments_off_the_target_edge(tmp_path):
    # A tooth-like 4mm notch on the RIGHT edge should not show up when
    # asking for the "top" edge's teeth.
    path_d = "M 0 0 H 20 V 8 L 24 8 L 24 12 L 20 12 V 20 H 0 Z"
    body = f'<g id="p-0"><path d="{path_d}" stroke="rgb(0,0,255)" /></g>'
    svg = write_svg(tmp_path, body, width="50mm", height="30mm")
    piece = su.get_pieces(svg)[0]
    assert su.edge_teeth_centers(piece, "top") == []
    right_centers = su.edge_teeth_centers(piece, "right")
    assert right_centers == [pytest.approx(10.0)]  # y-center of the 8..12 notch


def test_edge_teeth_centers_ignores_out_of_band_lengths(tmp_path):
    # A 20mm-long flat run at bbox.ymin is a straight edge, not a tooth tip
    # (well above TOOTH_LENGTH_MAX); a 1mm nub is below TOOTH_LENGTH_MIN.
    # Neither should be reported.
    path_d = "M 0 0 H 20 L 21 0 L 21 -1 L 22 -1 L 22 0 H 30 V 10 H 0 Z"
    body = f'<g id="p-0"><path d="{path_d}" stroke="rgb(0,0,255)" /></g>'
    svg = write_svg(tmp_path, body, width="50mm", height="30mm")
    piece = su.get_pieces(svg)[0]
    assert su.edge_teeth_centers(piece, "top") == []


def test_edge_teeth_centers_rejects_bad_edge_name():
    outer = su.PathInfo(d="M 0 0 H 10 V 10 H 0 Z", stroke="rgb(0,0,255)", bbox=su.BBox(0, 10, 0, 10))
    piece = su.Piece(outer=outer, holes=[])
    with pytest.raises(ValueError):
        su.edge_teeth_centers(piece, "diagonal")


# --- is_reference_mark now requires a black stroke --------------------------------

def test_is_reference_mark_false_for_blue_100x10_part(tmp_path):
    """A real (blue) 100x10mm design part must NOT be swallowed as the
    Boxes.py calibration mark -- only the black-stroked auto-generated
    rectangle is. Regression guard for the red-team's demonstrated failure
    mode (a real part vanishing from design_pieces because it happened to
    match the reference mark's size)."""
    ref = 'M 0 0 H 100 V 10 H 0 Z'
    body = f'<g id="p-0"><path d="{ref}" stroke="rgb(0,0,255)" /></g>'
    path = write_svg(tmp_path, body, width="120mm", height="30mm")
    piece = su.get_pieces(path)[0]
    assert not su.is_reference_mark(piece)
    assert su.design_pieces(path) == [piece]


def test_is_reference_mark_true_only_for_black_100x10_no_holes(tmp_path):
    ref = 'M 0 0 H 100 V 10 H 0 Z'
    body = f'<g id="p-0"><path d="{ref}" stroke="rgb(0,0,0)" /></g>'
    path = write_svg(tmp_path, body, width="120mm", height="30mm")
    piece = su.get_pieces(path)[0]
    assert su.is_reference_mark(piece)
    assert su.design_pieces(path) == []
