"""Shared SVG measurement helpers for the geometry and laser-requirement test
suites.

These are plain, framework-free functions: they parse a real SVG file (DOM via
`xml.etree.ElementTree`, path geometry via `svgpathtools`) and return small
dataclasses that the test files reason about. Keeping them here (instead of
inline in the test files) lets `tests/test_svg_utils.py` unit-test the
measurement logic itself against tiny synthetic SVG strings, independent of
whatever the real generators currently produce.

Piece model
-----------
Boxes.py emits one `<path>` per closed contour: one big outer boundary per
part, plus zero or more smaller closed paths for holes/cutouts drilled into
it (finger-joint holes, drawer openings, lid slots, engraved-letter pixels,
...). A "piece" is the physical part that boundary represents. We deliberately
do NOT use `<g>` grouping to find pieces (that's a Boxes.py output-structure
detail that the #17/#18 generator rewrite is free to change); instead we
cluster purely on bbox containment, per issue #16: a piece is an outer closed
path plus every other closed path whose bbox falls inside it.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

import svgpathtools

SVG_NS = "{http://www.w3.org/2000/svg}"

# Stroke color spellings we need to recognize, in every format Boxes.py (or a
# hand-authored SVG) might emit them in.
_BLUE = {"rgb(0,0,255)", "#0000ff", "blue"}
_RED = {"rgb(255,0,0)", "#ff0000", "red"}
_BLACK = {"rgb(0,0,0)", "#000000", "black"}

# Boxes.py's built-in calibration/reference rectangle: `Boxes.render()` draws
# a `self.reference` (default 100mm) x 10mm rectangle with a black stroke and
# a "<N>mm, burn:<b>mm" label unless a generator passes `--reference 0`. None
# of the three faxbox generators do, so every current output file carries one.
# It is not a DESIGN.md part; `is_reference_mark` identifies it purely by its
# fixed geometric signature (a single-path rectangle sized reference x 10mm)
# so the check can't be gamed by a generator bug that turns a *real* part
# black -- only a piece that is actually ~100x10mm with no holes matches.
REFERENCE_MARK_SIZE_MM = (100.0, 10.0)


def normalize_color(value: str | None) -> str:
    """Map any stroke value to 'blue' / 'red' / 'black' / 'none' / 'other:<v>'.

    Handles `rgb(r,g,b)`, `#rrggbb` (any case), and CSS color keywords, with
    whitespace tolerance, since a hand-authored or differently-formatted SVG
    could use any of these for the same color.
    """
    if value is None:
        return "none"
    v = "".join(value.split()).lower()
    if v in _BLUE:
        return "blue"
    if v in _RED:
        return "red"
    if v in _BLACK:
        return "black"
    return f"other:{v}"


@dataclass(frozen=True)
class BBox:
    xmin: float
    xmax: float
    ymin: float
    ymax: float

    @property
    def width(self) -> float:
        return self.xmax - self.xmin

    @property
    def height(self) -> float:
        return self.ymax - self.ymin

    @property
    def area(self) -> float:
        return max(self.width, 0.0) * max(self.height, 0.0)

    def dims_match(self, width: float, height: float, tol: float = 1.0) -> bool:
        """True if this bbox is (width x height) within `tol` mm, in either
        orientation (a hole/part may be measured rotated 90 degrees)."""
        a = abs(self.width - width) <= tol and abs(self.height - height) <= tol
        b = abs(self.width - height) <= tol and abs(self.height - width) <= tol
        return a or b

    def contains(self, other: "BBox", tol: float = 1e-3) -> bool:
        return (
            self.xmin - tol <= other.xmin
            and other.xmax <= self.xmax + tol
            and self.ymin - tol <= other.ymin
            and other.ymax <= self.ymax + tol
        )

    def overlaps(self, other: "BBox", tol: float = 1e-3) -> bool:
        """True rectangle overlap (nonzero shared area), not mere edge-touch.

        `tol` shrinks the effective comparison so pieces whose bboxes abut
        (share an edge, as intentionally-adjacent parts sometimes do in a
        packed layout) are not flagged as overlapping.
        """
        return not (
            self.xmax <= other.xmin + tol
            or other.xmax <= self.xmin + tol
            or self.ymax <= other.ymin + tol
            or other.ymax <= self.ymin + tol
        )


@dataclass(frozen=True)
class PathInfo:
    d: str
    stroke: str | None
    bbox: BBox
    label: str | None = None  # nearest <text> in the same <g>, if any


@dataclass
class Piece:
    outer: PathInfo
    holes: list[PathInfo] = field(default_factory=list)

    @property
    def bbox(self) -> BBox:
        return self.outer.bbox

    @property
    def label(self) -> str | None:
        return self.outer.label

    def all_paths(self) -> list[PathInfo]:
        return [self.outer, *self.holes]

    def stroke_colors(self) -> set[str]:
        return {normalize_color(p.stroke) for p in self.all_paths()}

    def holes_matching(self, width: float, height: float, tol: float = 1.0) -> list[PathInfo]:
        return [h for h in self.holes if h.bbox.dims_match(width, height, tol=tol)]


def get_svg_root(svg_path: str | Path) -> ET.Element:
    return ET.parse(svg_path).getroot()


def get_svg_dimensions_mm(svg_path: str | Path) -> tuple[float, float]:
    """Return (width_mm, height_mm) from the SVG root's width/height attrs.

    Raises ValueError if either dimension isn't expressed in millimeters --
    laser services key off these units, so "574.1" (unitless, defaults to px)
    or "574.1in" would silently cut the wrong physical size.
    """
    root = get_svg_root(svg_path)
    width = root.get("width", "")
    height = root.get("height", "")
    if not width.endswith("mm") or not height.endswith("mm"):
        raise ValueError(
            f"{svg_path}: root width/height must be in mm, got "
            f"width={width!r} height={height!r}"
        )
    return float(width[: -len("mm")]), float(height[: -len("mm")])


def iter_paths(svg_path: str | Path) -> list[PathInfo]:
    """Return a PathInfo for every <path> element in the document, in order.

    Each path's `label` is the text of the first `<text>` element found in
    the same immediate parent `<g>` (Boxes.py's convention: one label per
    piece group) -- used only as a human-readable identification aid, never
    as the basis for piece boundary detection (that's bbox containment, see
    `cluster_pieces`).
    """
    root = get_svg_root(svg_path)
    paths: list[PathInfo] = []
    for group in root.iter(f"{SVG_NS}g"):
        text_el = group.find(f"{SVG_NS}text")
        label = text_el.text if text_el is not None else None
        for path_el in group.findall(f"{SVG_NS}path"):
            d = path_el.get("d")
            if not d:
                continue
            parsed = svgpathtools.parse_path(d)
            xmin, xmax, ymin, ymax = parsed.bbox()
            paths.append(
                PathInfo(
                    d=d,
                    stroke=path_el.get("stroke"),
                    bbox=BBox(xmin, xmax, ymin, ymax),
                    label=label,
                )
            )
    # Also pick up any <path> not nested in a <g> (defensive; current output
    # never hits this, but a rewritten generator might not group at all).
    grouped_ids = {id(p) for g in root.iter(f"{SVG_NS}g") for p in g.findall(f"{SVG_NS}path")}
    for path_el in root.findall(f"{SVG_NS}path"):
        if id(path_el) in grouped_ids:
            continue
        d = path_el.get("d")
        if not d:
            continue
        parsed = svgpathtools.parse_path(d)
        xmin, xmax, ymin, ymax = parsed.bbox()
        paths.append(PathInfo(d=d, stroke=path_el.get("stroke"), bbox=BBox(xmin, xmax, ymin, ymax)))
    return paths



# Finger holes widened by FingerJointSettings play may break through an
# adjacent part edge by up to play/2 (e.g. the walls' bottom-panel hole rows).
# Containment during clustering tolerates that much overhang; kept well below
# part spacing so a path can never be claimed by a neighboring piece.
CONTAINMENT_TOL = 0.2

# A path is only treated as a *hole* of a larger containing path -- rather
# than a separate piece in its own right -- if it's meaningfully smaller than
# its container. Real DESIGN.md cutouts (finger-joint hole lines, drawer
# openings, the lid slot, engraved pixels, alignment-tab marks, ...) are all
# well under half their host piece's area (the largest, the rear-wall
# openings, are ~43%). Two full-size pieces whose bboxes happen to nest
# (e.g. a broken `move=` placing "Back Wall" entirely inside "Bottom"'s
# bbox) is exactly the overlap bug this harness exists to catch -- it must
# NOT be silently absorbed as if "Back Wall" were a hole cut into "Bottom".
HOLE_AREA_RATIO = 0.5


def cluster_pieces(paths: list[PathInfo]) -> list[Piece]:
    """Cluster a flat list of PathInfo into Pieces.

    A path is "outer" if no other path's bbox *properly* contains it: strict
    containment (the container's area must be larger, not merely equal, so
    two accidentally-identical bboxes both remain outer) AND the contained
    path must be small relative to the container (see HOLE_AREA_RATIO) --
    otherwise two same-scale pieces whose bboxes happen to nest would be
    silently merged into one "piece plus a giant hole" instead of surfacing
    as the overlap bug it is.
    Every non-outer path is assigned as a hole of the smallest-area outer
    piece whose bbox contains it (handles nested holes-within-holes and,
    defensively, holes ambiguously claimed by more than one outer bbox).
    """
    n = len(paths)

    def properly_contains(a: BBox, b: BBox) -> bool:
        return (a.contains(b, tol=CONTAINMENT_TOL)
                and a.area > b.area + 1e-6
                and b.area <= HOLE_AREA_RATIO * a.area)

    is_outer = [
        not any(i != j and properly_contains(paths[j].bbox, paths[i].bbox) for j in range(n))
        for i in range(n)
    ]
    outer_indices = [i for i in range(n) if is_outer[i]]

    pieces_holes: dict[int, list[PathInfo]] = {i: [] for i in outer_indices}
    for i in range(n):
        if is_outer[i]:
            continue
        candidates = [oi for oi in outer_indices
                      if paths[oi].bbox.contains(paths[i].bbox, tol=CONTAINMENT_TOL)]
        if not candidates:
            # Not contained by anything (shouldn't happen for valid laser
            # output) -- surface it as its own piece rather than silently
            # dropping it.
            pieces_holes[i] = []
            outer_indices.append(i)
            continue
        best = min(candidates, key=lambda oi: paths[oi].bbox.area)
        pieces_holes[best].append(paths[i])

    return [Piece(outer=paths[oi], holes=pieces_holes[oi]) for oi in outer_indices]


def get_pieces(svg_path: str | Path) -> list[Piece]:
    return cluster_pieces(iter_paths(svg_path))


def is_reference_mark(piece: Piece, tol: float = 0.5) -> bool:
    """True if `piece` is Boxes.py's auto-generated calibration rectangle.

    See REFERENCE_MARK_SIZE_MM for why this is safe to key off size alone.
    """
    if piece.holes:
        return False
    return piece.bbox.dims_match(*REFERENCE_MARK_SIZE_MM, tol=tol)


def design_pieces(svg_path: str | Path) -> list[Piece]:
    """All pieces except the Boxes.py reference/calibration mark."""
    return [p for p in get_pieces(svg_path) if not is_reference_mark(p)]


def find_piece_by_label(pieces: list[Piece], *substrings: str) -> Piece | None:
    """Return the first piece whose label contains any of `substrings`
    (case-insensitive). Returns None if no piece matches.
    """
    wanted = [s.lower() for s in substrings]
    for piece in pieces:
        label = (piece.label or "").lower()
        if any(w in label for w in wanted):
            return piece
    return None


def any_black_strokes(svg_path: str | Path) -> list[PathInfo]:
    """All paths anywhere in the file with a black stroke, in any format."""
    return [p for p in iter_paths(svg_path) if normalize_color(p.stroke) == "black"]


def non_cut_engrave_strokes(svg_path: str | Path) -> list[PathInfo]:
    """All paths whose stroke is neither cut-blue nor engrave-red (includes
    black, unset, and anything else)."""
    return [p for p in iter_paths(svg_path) if normalize_color(p.stroke) not in ("blue", "red")]


def hole_line_spans(
    holes: list[PathInfo],
    thickness: float,
    axis: str,
    thickness_tol: float = 0.5,
    group_tol: float = 1.5,
    min_holes: int = 2,
) -> list[float]:
    """Extents of dashed finger-hole rows (Boxes.py `fingerHolesAt` output).

    A finger-hole "line" is a row of separate small holes, each `thickness`
    across in the cross-axis direction, dashed along the row axis.
    axis='x': horizontal rows (hole height ~ thickness) -> returns each row's
    X extent. axis='y': vertical rows (hole width ~ thickness) -> Z extents.
    Rows are grouped by cross-axis center; groups with fewer than `min_holes`
    holes are ignored (a single T-sized hole is not a row).
    """
    if axis not in ("x", "y"):
        raise ValueError(f"axis must be 'x' or 'y', got {axis!r}")
    groups: dict[int, list[BBox]] = {}
    for h in holes:
        cross = h.bbox.height if axis == "x" else h.bbox.width
        if abs(cross - thickness) > thickness_tol:
            continue
        center = (
            (h.bbox.ymin + h.bbox.ymax) / 2 if axis == "x" else (h.bbox.xmin + h.bbox.xmax) / 2
        )
        groups.setdefault(round(center / group_tol), []).append(h.bbox)
    spans = []
    for boxes in groups.values():
        if len(boxes) < min_holes:
            continue
        if axis == "x":
            spans.append(max(b.xmax for b in boxes) - min(b.xmin for b in boxes))
        else:
            spans.append(max(b.ymax for b in boxes) - min(b.ymin for b in boxes))
    return spans


def expected_band(nominal: float, jointed_edges: int, thickness: float, slack: float = 0.5) -> tuple[float, float]:
    """DESIGN.md's per-axis blank-size tolerance band.

    A finger-jointed edge extends a part's blank by up to one material
    `thickness` beyond nominal (Boxes.py tabs/holes both can locally push the
    boundary out by up to T, and we don't know a priori which polarity a
    given rebuild will choose -- see test_svg_geometry.py part comments -- so
    we treat both as "may extend"). `jointed_edges` is how many of the two
    edges bounding this axis are jointed (0, 1, or 2); a plain edge
    contributes 0. `slack` is measurement/kerf tolerance applied on both
    ends regardless of joint type.
    """
    if not 0 <= jointed_edges <= 2:
        raise ValueError(f"jointed_edges must be 0, 1, or 2, got {jointed_edges}")
    return (nominal - slack, nominal + jointed_edges * thickness + slack)
