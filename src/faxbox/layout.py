"""Nest all fax machine box parts onto laser-bed-sized sheets.

Combines output/outer_shell.svg (8 pieces, once) + output/drawer.svg (6
pieces, cut TWICE -- the box needs two identical drawers) + output/lids.svg
(1 piece) into output/sheet_1.svg, sheet_2.svg, ... -- each sheet sized to
fit within the verified NYC Resistor bed constraint (see
docs/service-comparison.md, "NYC Resistor cutting constraints"), with a
>=10mm margin from the sheet edge and >=5mm spacing between parts. A
combined output/final_layout.svg is also emitted for quick visual review in
a browser -- it is NOT sized to any real bed and must NOT be sent to the
laser; only the sheet_*.svg files are cut-ready.

Piece model: each of the three source SVGs (Boxes.py output) wraps one part
per top-level <g>, containing that part's cut/engrave <path> elements plus
one <text> label -- see the real files for the ground truth. This module
reads that structure directly (rather than importing tests/svg_utils.py's
bbox-clustering helpers, which exist to be robust to a *future* change in
that structure for the test harness) and re-emits each piece's original
<path>/<text> elements, translated into its assigned sheet position, with
stroke colors and geometry preserved exactly.

Packing: a deterministic shelf (row) packer -- pieces are sorted tallest
first and each is placed into the shortest existing shelf (row) that still
has both enough height and enough remaining width, opening a new shelf (same
sheet if there's vertical room left, otherwise a new sheet) when none fits.
No piece is ever rotated or split, so every piece lands on exactly one sheet
as a single rigid rectangle.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape, quoteattr

import svgpathtools

from faxbox import config
from faxbox.config import OUTPUT_DIR

SVG_NS = "{http://www.w3.org/2000/svg}"

# --- Sheet / bed constraints -------------------------------------------------
# NYC Resistor's own laser page and wiki state a 32in x 20in bed (Epilog
# Fusion 32, 60W), but a comment on that same page disputes the real
# *cuttable* area is smaller (12in x 24in), and no NYC Resistor page
# reconciles the two figures. Per issue #19's explicit instruction for an
# ambiguous bed size, this project falls back to a conservative planning
# size rather than trusting either disputed number. See
# docs/service-comparison.md ("NYC Resistor cutting constraints", verified
# 2026-07-07) for the full writeup and sources; update these two constants
# if the real bed is confirmed before cut day.
SHEET_WIDTH_MM = 609.6  # 24in, conservative fallback
SHEET_HEIGHT_MM = 457.2  # 18in, conservative fallback
MARGIN_MM = 10.0  # clearance from sheet edge (issue #19 requirement)
SPACING_MM = 5.0  # clearance between parts (issue #19 requirement)


# --- Piece model --------------------------------------------------------------

@dataclass
class SourcePath:
    """One <path> element from a source piece, minus its 'd' (kept
    separately so it can be re-translated per placement)."""

    attrib: dict[str, str]
    d: str


@dataclass
class Piece:
    """A single physical part, as found in a source SVG's top-level <g>."""

    source: str  # human label for where this came from, e.g. "Drawer 1"
    label: str  # Boxes.py's own part label, e.g. "Bottom", "Right Wall"
    width: float
    height: float
    xmin: float  # bbox origin in the SOURCE file's coordinate space
    ymin: float
    group_style: str
    svg_paths: list[SourcePath] = field(default_factory=list)
    text_attrib: dict[str, str] | None = None
    text_content: str | None = None


@dataclass
class Placement:
    """A Piece assigned an (x, y) top-left position within one output sheet
    (sheet-space coordinates, i.e. already includes the sheet margin)."""

    piece: Piece
    x: float
    y: float


def _load_pieces(svg_path: Path, source: str, strip_labels: bool = False) -> list[Piece]:
    """Read every top-level <g> (one per Boxes.py part) from svg_path.

    `strip_labels`: when True, the piece's `<text>` label (if any) is used
    only to compute a human-readable `label` for identification, and is
    NOT carried into the Piece's text_attrib/text_content -- so
    _emit_piece_group later emits no <text> element at all for this piece.
    Used by the Ponoko path (config.PONOKO_STRIP_LABELS), which strips
    reference labels entirely rather than re-coloring them gray like the
    default NYCR path.
    """
    root = ET.parse(svg_path).getroot()
    pieces: list[Piece] = []
    for g in root.findall(f"{SVG_NS}g"):
        path_els = [p for p in g.findall(f"{SVG_NS}path") if p.get("d")]
        if not path_els:
            continue
        xmin = ymin = math.inf
        xmax = ymax = -math.inf
        svg_paths = []
        for p in path_els:
            d = p.get("d")
            x0, x1, y0, y1 = svgpathtools.parse_path(d).bbox()
            xmin, xmax = min(xmin, x0), max(xmax, x1)
            ymin, ymax = min(ymin, y0), max(ymax, y1)
            svg_paths.append(SourcePath(attrib={k: v for k, v in p.attrib.items() if k != "d"}, d=d))

        text_el = g.find(f"{SVG_NS}text")
        label = (text_el.text or "").strip() if text_el is not None and text_el.text else g.get("id", "piece")

        pieces.append(
            Piece(
                source=source,
                label=label,
                width=xmax - xmin,
                height=ymax - ymin,
                xmin=xmin,
                ymin=ymin,
                group_style=g.get("style", ""),
                svg_paths=svg_paths,
                text_attrib=None if strip_labels or text_el is None else dict(text_el.attrib),
                text_content=None if strip_labels or text_el is None else text_el.text,
            )
        )
    return pieces


# --- Packing --------------------------------------------------------------

def _pack_pieces(
    pieces: list[Piece],
    sheet_width: float = SHEET_WIDTH_MM,
    sheet_height: float = SHEET_HEIGHT_MM,
    margin: float = MARGIN_MM,
    spacing: float = SPACING_MM,
) -> list[list[Placement]]:
    """Shelf (row) packer. See module docstring for the algorithm.

    `sheet_width`/`sheet_height`/`margin`/`spacing` default to this
    project's NYC Resistor planning constants; the Ponoko path passes
    config.PROVIDERS["ponoko"]'s sheet limit instead (same margin/spacing,
    which are already well over Ponoko's published ~1mm minimum).

    Returns one list of Placement per sheet, in sheet order. Raises
    ValueError if any single piece is too big to ever fit a sheet.
    """
    usable_w = sheet_width - 2 * margin
    usable_h = sheet_height - 2 * margin

    for p in pieces:
        if p.width > usable_w + 1e-6 or p.height > usable_h + 1e-6:
            raise ValueError(
                f"{p.source}: {p.label!r} ({p.width:.1f}x{p.height:.1f}mm) does not fit "
                f"within a single {sheet_width:.1f}x{sheet_height:.1f}mm sheet "
                f"(usable {usable_w:.1f}x{usable_h:.1f}mm after {margin}mm margins) -- "
                f"bed size too small for this part"
            )

    ordered = sorted(pieces, key=lambda p: p.height, reverse=True)

    # sheets[si] is a list of shelf dicts: {"y", "height", "x_cursor",
    # "items": [Placement, ...]}, all coordinates relative to the sheet's
    # usable area (margin added only when a Placement is recorded).
    sheets: list[list[dict]] = [[]]

    for piece in ordered:
        best: tuple[int, int] | None = None
        for si, shelves in enumerate(sheets):
            for hi, shelf in enumerate(shelves):
                if shelf["height"] + 1e-6 < piece.height:
                    continue
                gap = spacing if shelf["items"] else 0.0
                if shelf["x_cursor"] + gap + piece.width > usable_w + 1e-6:
                    continue
                if best is None or shelf["height"] < sheets[best[0]][best[1]]["height"]:
                    best = (si, hi)

        if best is None:
            # No existing shelf fits -- open a new one, preferring vertical
            # room on the current (last) sheet before starting a new sheet.
            si = len(sheets) - 1
            shelves = sheets[si]
            y_cursor = sum(s["height"] + spacing for s in shelves)
            if y_cursor + piece.height > usable_h + 1e-6:
                sheets.append([])
                si = len(sheets) - 1
                shelves = sheets[si]
                y_cursor = 0.0
            shelves.append({"y": y_cursor, "height": piece.height, "x_cursor": 0.0, "items": []})
            best = (si, len(shelves) - 1)

        si, hi = best
        shelf = sheets[si][hi]
        gap = spacing if shelf["items"] else 0.0
        x = shelf["x_cursor"] + gap
        shelf["x_cursor"] = x + piece.width
        shelf["items"].append(Placement(piece=piece, x=margin + x, y=margin + shelf["y"]))

    return [[placement for shelf in shelves for placement in shelf["items"]] for shelves in sheets]


def _sheet_content_bounds(placements: list[Placement], margin: float = MARGIN_MM) -> tuple[float, float]:
    """Sheet dimensions trimmed to just fit the placed content plus the far
    margin (so real material bought for cutting isn't bigger than needed)."""
    max_x = max(p.x + p.piece.width for p in placements)
    max_y = max(p.y + p.piece.height for p in placements)
    return max_x + margin, max_y + margin


# --- SVG emission ------------------------------------------------------------

_NUM_RE = re.compile(r"-?\d+\.\d+(?:[eE][+-]?\d+)?|-?\d+(?:[eE][+-]?\d+)?")


def _round_numbers(text: str, precision: int = 3) -> str:
    return _NUM_RE.sub(lambda m: f"{float(m.group()):.{precision}f}", text)


_MATRIX_RE = re.compile(r"matrix\(\s*([^)]+)\)")

# NYC Resistor's workflow wants hairline cut lines (0.216pt = 0.0762mm) so
# CorelDraw doesn't rasterize the paths instead of vector-cutting them; the
# Boxes.py source SVGs carry a thicker 0.16mm stroke-width, so every
# re-serialized path is forced to this value regardless of what it inherited.
HAIRLINE_STROKE_WIDTH_MM = "0.0762"

# Part-name labels (Boxes.py's own `Color.ANNOTATIONS`, which renders as
# red -- identical to ENGRAVE_COLOR) must read as reference-only text, never
# as a red engrave path. Re-colored to gray and flagged with a
# data-purpose attribute here, at the point each label is re-serialized.
_LABEL_FILL_RE = re.compile(r"fill:\s*rgb\(255,\s*0,\s*0\)")
LABEL_FILL_GRAY = "fill: rgb(128,128,128)"


def _shift_transform(transform: str, dx: float, dy: float) -> str:
    """Add (dx, dy) to an existing 'matrix(...)' transform's translation
    component, or prepend a translate() if there's no matrix to adjust."""
    m = _MATRIX_RE.search(transform or "")
    if not m:
        prefix = f"translate({dx:.3f},{dy:.3f})"
        return f"{prefix} {transform}".strip()
    nums = [float(x) for x in m.group(1).split()]
    if len(nums) != 6:
        prefix = f"translate({dx:.3f},{dy:.3f})"
        return f"{prefix} {transform}".strip()
    a, b, c, d, tx, ty = nums
    new_matrix = f"matrix( {a:.3f} {b:.3f} {c:.3f} {d:.3f} {tx + dx:.3f} {ty + dy:.3f} )"
    return _MATRIX_RE.sub(new_matrix, transform)


def _emit_piece_group(piece: Piece, target_x: float, target_y: float, group_id: str) -> str:
    """Re-emit a piece's original <path>/<text> elements translated so the
    piece's bbox top-left lands at (target_x, target_y). Stroke colors and
    all other path/text attributes are copied through unchanged."""
    dx = target_x - piece.xmin
    dy = target_y - piece.ymin
    offset = complex(dx, dy)
    label_full = f"{piece.source}: {piece.label}"

    lines = [f"<g id={quoteattr(group_id)} data-part={quoteattr(label_full)} style={quoteattr(piece.group_style)}>"]
    for sp in piece.svg_paths:
        new_d = _round_numbers(svgpathtools.parse_path(sp.d).translated(offset).d())
        attrib = dict(sp.attrib)
        attrib["stroke-width"] = HAIRLINE_STROKE_WIDTH_MM
        attr_str = " ".join(f"{k}={quoteattr(v)}" for k, v in attrib.items())
        lines.append(f"<path {attr_str} d={quoteattr(new_d)} />")
    if piece.text_attrib is not None:
        attrs = dict(piece.text_attrib)
        attrs["transform"] = _shift_transform(attrs.get("transform", ""), dx, dy)
        if "style" in attrs:
            attrs["style"] = _LABEL_FILL_RE.sub(LABEL_FILL_GRAY, attrs["style"])
        attrs["data-purpose"] = "reference-label"
        attr_str = " ".join(f"{k}={quoteattr(v)}" for k, v in attrs.items())
        lines.append(f"<text {attr_str}>{escape(label_full)}</text>")
    lines.append("</g>")
    return "\n".join(lines)


def _write_sheet_svg(
    placements: list[Placement],
    width: float,
    height: float,
    output_path: Path,
    sheet_number: int,
    total_sheets: int,
    header_comment: str | None = None,
    title: str | None = None,
) -> None:
    groups = [
        _emit_piece_group(placement.piece, placement.x, placement.y, f"sheet{sheet_number}-p{i}")
        for i, placement in enumerate(placements)
    ]
    body = "\n".join(groups)
    if header_comment is None:
        # Note: XML comments may not contain "--", so the comment body below
        # uses single hyphens only (unlike the surrounding Python docstrings).
        header_comment = f"""Fax Machine Box - Sheet {sheet_number} of {total_sheets}. Ready for laser
cutting (NYC Resistor or any service with an equal or larger bed).
Material: 3.175mm (1/8 inch) plywood.

Color coding: Blue (#0000FF) = cut, Red (#FF0000) = engrave. The gray
(rgb(128,128,128)) part-name text on each piece is reference-only, purely to
identify the part for a human; it carries data-purpose="reference-label" on
its <text> element and must NOT be mapped to any cut or engrave operation in
the laser driver.
Margins: {MARGIN_MM:.0f}mm from sheet edge; {SPACING_MM:.0f}mm between parts."""
    if title is None:
        title = f"Fax Machine Box - Sheet {sheet_number} of {total_sheets}"
    svg = f"""<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
    width="{width:.2f}mm" height="{height:.2f}mm"
    viewBox="0 0 {width:.2f} {height:.2f}">
<!--
{header_comment}
-->
<title>{title}</title>
{body}
</svg>
"""
    output_path.write_text(svg)


def _write_reference_layout(sheets: list[list[Placement]], sheet_dims: list[tuple[float, float]], output_path: Path) -> None:
    """Combine every sheet into one oversized drawing, side by side at true
    scale, purely for a quick visual sanity check in a browser. This file is
    NOT sized to any real laser bed and must NOT be sent for cutting --
    send sheet_1.svg, sheet_2.svg, ... instead."""
    gap = 20.0
    cols = 2 if len(sheets) > 1 else 1
    rows = (len(sheets) + cols - 1) // cols
    positions = [(i % cols, i // cols) for i in range(len(sheets))]

    col_widths = [0.0] * cols
    row_heights = [0.0] * rows
    for i, (col, row) in enumerate(positions):
        col_widths[col] = max(col_widths[col], sheet_dims[i][0])
        row_heights[row] = max(row_heights[row], sheet_dims[i][1])

    col_x = [0.0] * cols
    for c in range(1, cols):
        col_x[c] = col_x[c - 1] + col_widths[c - 1] + gap
    header_height = 20.0
    row_y = [0.0] * rows
    for r in range(1, rows):
        row_y[r] = row_y[r - 1] + row_heights[r - 1] + gap

    body_parts = []
    for i, placements in enumerate(sheets):
        col, row = positions[i]
        ox, oy = col_x[col], header_height + row_y[row]
        for j, placement in enumerate(placements):
            body_parts.append(_emit_piece_group(placement.piece, placement.x + ox, placement.y + oy, f"ref-s{i + 1}-p{j}"))
        w, h = sheet_dims[i]
        body_parts.append(
            f'<rect x="{ox:.2f}" y="{oy:.2f}" width="{w:.2f}" height="{h:.2f}" '
            f'fill="none" stroke="#999999" stroke-width="0.5" stroke-dasharray="4,2" />'
        )
        body_parts.append(
            f'<text x="{ox:.2f}" y="{oy - 3:.2f}" font-size="6" fill="#333333">'
            f"Sheet {i + 1} ({w:.0f}mm x {h:.0f}mm)</text>"
        )

    total_width = sum(col_widths) + gap * (cols - 1)
    total_height = header_height + sum(row_heights) + gap * (rows - 1)
    body = "\n".join(body_parts)
    # Note: XML comments may not contain "--", so the comment body below
    # uses single hyphens only (unlike the surrounding Python docstrings).
    svg = f"""<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
    width="{total_width:.2f}mm" height="{total_height:.2f}mm"
    viewBox="0 0 {total_width:.2f} {total_height:.2f}">
<!--
Fax Machine Box - COMBINED REFERENCE LAYOUT - NOT FOR CUTTING.

Lays every sheet_*.svg out side by side at true scale so a human can eyeball
the whole nesting in one browser tab. Its overall dimensions
({total_width:.0f}mm x {total_height:.0f}mm) exceed the laser bed by design.
Send the individual sheet_1.svg, sheet_2.svg, ... files to the laser -
never this file.
-->
<title>Fax Machine Box - REFERENCE ONLY, NOT FOR CUTTING</title>
<text x="4" y="12" font-size="10" fill="#cc0000" font-weight="bold">REFERENCE ONLY - NOT FOR CUTTING (combines all sheets; exceeds bed size)</text>
{body}
</svg>
"""
    output_path.write_text(svg)


# --- Orchestration ------------------------------------------------------------

def _require_source_svgs(output_path: Path) -> tuple[Path, Path, Path]:
    shell_svg = output_path / "outer_shell.svg"
    drawer_svg = output_path / "drawer.svg"
    lids_svg = output_path / "lids.svg"
    missing = [p.name for p in (shell_svg, drawer_svg, lids_svg) if not p.exists()]
    if missing:
        print("Error: Missing source SVG files. Generate them first:")
        for name in missing:
            print(f"  - {name}")
        print("\nRun these commands:")
        print("  python3 -m faxbox.shell_generator")
        print("  python3 -m faxbox.generate_drawers")
        print("  python3 -m faxbox.generate_lids")
        raise FileNotFoundError(f"Missing: {', '.join(missing)}")
    return shell_svg, drawer_svg, lids_svg


def generate_layout() -> list[Path]:
    """Nest outer_shell.svg + drawer.svg (x2, cut twice) + lids.svg onto
    sheet_1.svg, sheet_2.svg, ... plus a reference-only final_layout.svg.

    Returns the list of sheet_N.svg paths, in order.
    """
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)

    shell_svg, drawer_svg, lids_svg = _require_source_svgs(output_path)

    pieces: list[Piece] = []
    pieces += _load_pieces(shell_svg, "Shell")
    pieces += _load_pieces(drawer_svg, "Drawer 1")
    pieces += _load_pieces(drawer_svg, "Drawer 2")
    pieces += _load_pieces(lids_svg, "Lid")

    sheets = _pack_pieces(pieces)

    sheet_paths: list[Path] = []
    sheet_dims: list[tuple[float, float]] = []
    for i, placements in enumerate(sheets, start=1):
        width, height = _sheet_content_bounds(placements)
        sheet_path = output_path / f"sheet_{i}.svg"
        _write_sheet_svg(placements, width, height, sheet_path, i, len(sheets))
        sheet_paths.append(sheet_path)
        sheet_dims.append((width, height))

    _write_reference_layout(sheets, sheet_dims, output_path / "final_layout.svg")

    total_parts = sum(len(p) for p in sheets)
    print(f"Generated {len(sheets)} sheet(s) in {output_path.absolute()}:")
    for path, (w, h) in zip(sheet_paths, sheet_dims):
        print(f"  {path.name}: {w:.1f}mm x {h:.1f}mm ({w / 25.4:.1f}in x {h / 25.4:.1f}in)")
    print(f"Total parts placed: {total_parts} (expected 21: 8 shell + 12 drawer + 1 lid)")
    print(
        f"Bed limit used for packing: {SHEET_WIDTH_MM:.1f}mm x {SHEET_HEIGHT_MM:.1f}mm "
        f"(conservative fallback -- see docs/service-comparison.md)"
    )
    print(f"Reference-only combined view: {(output_path / 'final_layout.svg').absolute()}")
    print("NOTE: final_layout.svg is for visual review ONLY -- it is larger than the")
    print("      laser bed and must NOT be sent for cutting. Send sheet_*.svg instead.")

    return sheet_paths


# --- Ponoko export mode (additive; never touches the NYCR path above) --------

# 21 NYCR parts (8 shell + 12 drawer + 1 lid) + the turn-button hardware
# piece, which the NYCR default path deliberately keeps standalone (see
# generate_layout's docstring / DESIGN.md section B) but the Ponoko path
# nests like every other part, since a single Ponoko order should carry
# every laser-cut piece the box needs.
PONOKO_EXPECTED_PARTS = 22
# The combined kerf-square + magnet-gauge-row self-calibration coupon
# (faxbox.calibration.generate_ponoko_coupon) -- see README "Ordering from
# Ponoko" for why Ponoko orders need this nested onto the real sheet rather
# than cut on scrap first (unlike NYC Resistor, there is no walk-up scrap
# test cut available before a Ponoko order ships).
PONOKO_EXPECTED_COUPONS = 1


def _ponoko_header_comment(sheet_number: int, total_sheets: int) -> str:
    # Note: XML comments may not contain "--" (same constraint documented on
    # _write_sheet_svg's default header comment), so the text below uses
    # single hyphens and colons only.
    return f"""Fax Machine Box - PONOKO order - Sheet {sheet_number} of {total_sheets}.
Material: 3.2mm birch plywood (Ponoko's nominal size for 1/8in stock).

Verified against Ponoko's own current help pages (2026-07-07):
  Color coding: Blue (#0000FF) = cut, Red (#FF0000) = line/vector engrave.
  Source: https://help.ponoko.com/en/articles/2688732-how-should-i-specify-laser-actions
  Kerf 0.20mm, so BURN = 0.10mm (this project's per-side kerf compensation).
  Source: https://www.ponoko.com/materials/birch-plywood
  Sheet nested within the 790mm x 384mm max DESIGN area (not the 795x395mm
  raw max sheet size; the gap is Ponoko's own sheet-edge margin).
  Source: https://help.ponoko.com/en/articles/2688726-what-size-can-i-make-my-part-what-material-sizes-are-available

No reference-only labels on this sheet: Ponoko's file-prep docs require
text be outlined/converted before upload or it "will not be read" as a
laser instruction at all (source: https://help.ponoko.com/en/articles/2688477-what-design-software-file-type-should-i-use).
Rather than outline part names into visible engrave-red paths, this sheet
omits them entirely; see README "Ordering from Ponoko" for part
identification instead.
Margins: {MARGIN_MM:.0f}mm from sheet edge; {SPACING_MM:.0f}mm between parts
(Ponoko's own published minimum is ~1mm; kept at this project's existing,
more conservative NYCR values)."""


def generate_ponoko_layout(provider: str | None = None) -> list[Path]:
    """Regenerate every part with Ponoko's provider settings (kerf-derived
    BURN, Ponoko's cut/vector-engrave colors, no reference labels -- see
    config.PROVIDERS["ponoko"]) and re-nest ALL of them -- the 21 NYCR parts,
    the turn-button hardware piece, and a small self-calibration coupon
    (kerf square + magnet press-fit gauge row) -- onto sheets sized within
    Ponoko's published birch-plywood workable area. Output:
    config.PROVIDERS["ponoko"]["output_dir"] (output/ponoko/).

    This is entirely additive: it never touches output/*.svg (the NYCR
    default path generate_layout() produces) and is only invoked via
    faxbox.ponoko or FAXBOX_PROVIDER=ponoko.

    Returns the list of sheet_N.svg paths, in order.
    """
    name = config.resolve_provider(provider)
    if name != "ponoko":
        raise ValueError(f"generate_ponoko_layout only supports provider='ponoko', got {name!r}")
    provider_cfg = config.PROVIDERS[name]
    output_path = Path(provider_cfg["output_dir"])
    output_path.mkdir(parents=True, exist_ok=True)

    # Regenerate every ponoko-flavored source SVG. Imported here (not at
    # module level) purely to keep this Ponoko-only dependency scoped to
    # where it's used -- these modules only import faxbox.config, so there
    # is no import cycle either way.
    from faxbox import calibration, generate_drawers, generate_hardware, generate_lids, shell_generator

    shell_svg = shell_generator.generate_shell(provider=name)
    drawer_svg = generate_drawers.generate_drawer(provider=name)
    lids_svg = generate_lids.generate_lids(provider=name)
    hardware_svg = generate_hardware.generate_hardware(provider=name)
    coupon_svg = calibration.generate_ponoko_coupon(provider=name)

    strip = provider_cfg["strip_labels"]
    pieces: list[Piece] = []
    pieces += _load_pieces(shell_svg, "Shell", strip_labels=strip)
    pieces += _load_pieces(drawer_svg, "Drawer 1", strip_labels=strip)
    pieces += _load_pieces(drawer_svg, "Drawer 2", strip_labels=strip)
    pieces += _load_pieces(lids_svg, "Lid", strip_labels=strip)
    pieces += _load_pieces(hardware_svg, "Hardware", strip_labels=strip)
    pieces += _load_pieces(coupon_svg, "Calibration", strip_labels=strip)

    sheets = _pack_pieces(
        pieces,
        sheet_width=provider_cfg["sheet_width"],
        sheet_height=provider_cfg["sheet_height"],
    )

    sheet_paths: list[Path] = []
    sheet_dims: list[tuple[float, float]] = []
    for i, placements in enumerate(sheets, start=1):
        width, height = _sheet_content_bounds(placements)
        sheet_path = output_path / f"sheet_{i}.svg"
        _write_sheet_svg(
            placements, width, height, sheet_path, i, len(sheets),
            header_comment=_ponoko_header_comment(i, len(sheets)),
            title=f"Fax Machine Box - PONOKO order - Sheet {i} of {len(sheets)}",
        )
        sheet_paths.append(sheet_path)
        sheet_dims.append((width, height))

    _write_reference_layout(sheets, sheet_dims, output_path / "final_layout.svg")

    total_parts = sum(len(p) for p in sheets)
    print(f"Generated {len(sheets)} Ponoko sheet(s) in {output_path.absolute()}:")
    for path, (w, h) in zip(sheet_paths, sheet_dims):
        print(f"  {path.name}: {w:.1f}mm x {h:.1f}mm")
    print(
        f"Total parts placed: {total_parts} (expected "
        f"{PONOKO_EXPECTED_PARTS + PONOKO_EXPECTED_COUPONS}: {PONOKO_EXPECTED_PARTS} real parts "
        "[21 NYCR parts + 1 turn button] + "
        f"{PONOKO_EXPECTED_COUPONS} self-calibration coupon)"
    )
    print(
        f"Ponoko sheet limit used: {provider_cfg['sheet_width']:.1f}mm x "
        f"{provider_cfg['sheet_height']:.1f}mm (verified 2026-07-07, see config.py PONOKO_* constants)"
    )
    print(f"Reference-only combined view: {(output_path / 'final_layout.svg').absolute()}")

    return sheet_paths


if __name__ == "__main__":
    if config.resolve_provider() == "ponoko":
        generate_ponoko_layout()
    else:
        generate_layout()
