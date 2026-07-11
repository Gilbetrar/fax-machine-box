#!/usr/bin/env python3
"""Placement-proof renderer (issue: art-integration placement gate).

Composites each of the 11 finished 1-bit engrave-art files in art/engrave/
onto the REAL cut geometry of its target part (regenerated fresh from the
faxbox generators), at true scale, so Ben can approve exactly where every
cut feature (finger holes, slots, openings, magnet holes...) punches through
the art before anything is sent to a laser service.

Deterministic, no args. Run: `.venv/bin/python scripts/art_proofs.py`

Output: scratch/art-proofs/*.png + scratch/art-proofs/PROOFS.md.

Coordinate/orientation approach (see PROOFS.md for the full per-part
derivation): every part is rendered directly from its own SVG piece bbox,
with NO horizontal flip ever applied (Boxes.py's own mirror=True drawing for
the Left Wall already bakes the mirror into the local path coordinates, so
re-flipping here would double-mirror it). A per-part `flip_y` cosmetically
orients "up" in the rendered proof; it never affects left/right.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import svgpathtools
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tests"))
sys.path.insert(0, str(REPO / "src"))

from svg_utils import (  # noqa: E402
    BBox,
    Piece,
    PathInfo,
    design_pieces,
    find_piece_by_label,
    normalize_color,
)
from faxbox.config import MATERIAL_THICKNESS  # noqa: E402

ART_DIR = REPO / "art" / "engrave"
OUT_DIR = REPO / "scratch" / "art-proofs"
OUTPUT_SVG_DIR = REPO / "output"

PX_PER_MM = 20.0
PAD_MM = 12.0           # white margin around the drawn part bbox
CAPTION_H_MM = 34.0      # caption band height below the part
SCALEBAR_MM = 10.0

BLUE = (0, 40, 255, 255)
RED = (230, 0, 0, 255)
FAINT_RED = (255, 170, 170, 255)
BLACK = (0, 0, 0, 255)
DASH_GRAY = (120, 120, 120, 255)


def regenerate_svgs() -> None:
    from faxbox.shell_generator import generate_shell
    from faxbox.generate_drawers import generate_drawer
    from faxbox.generate_lids import generate_lids

    generate_shell()
    generate_drawer()
    generate_lids()


# --------------------------------------------------------------------------
# Part specs
# --------------------------------------------------------------------------


@dataclass
class PartSpec:
    key: str
    svg_file: str
    label: str                # substring to find the piece by (svg_utils label)
    art_file: str
    nominal_mm: tuple[float, float]   # (width, height) in the piece's own local frame
    flip_y: bool               # cosmetic vertical orientation only, never affects L/R
    rotate: str | None = None  # None | "CCW" | "CW" | "180"
    title: str | None = None   # display title override (e.g. "Drawer 1 - Left Side")
    jointed_note: str = ""
    x_jointed: bool = False    # True if EITHER x-edge (left/right in local frame) is finger-jointed
    y_jointed: bool = False    # True if EITHER y-edge (top/bottom in local frame) is finger-jointed


PART_SPECS = [
    PartSpec(
        key="left_wall", svg_file="outer_shell.svg", label="Left Wall",
        art_file="left_wall.png", nominal_mm=(298.45, 127.0), flip_y=False,
        jointed_note="front/rear edges (x, both) finger-jointed; top/bottom (y) plain",
        x_jointed=True, y_jointed=False,
    ),
    PartSpec(
        key="right_wall", svg_file="outer_shell.svg", label="Right Wall",
        art_file="right_wall.png", nominal_mm=(298.45, 127.0), flip_y=False,
        jointed_note="front/rear edges (x, both) finger-jointed; top/bottom (y) plain",
        x_jointed=True, y_jointed=False,
    ),
    PartSpec(
        key="right_wall_nofunfor", svg_file="outer_shell.svg", label="Right Wall",
        art_file="right_wall_VARIANT_NOFUNFOR.png", nominal_mm=(298.45, 127.0),
        flip_y=False,
        title="Right Wall -- VARIANT: 'Fun For' lead-in removed (feedback #4 option)",
        jointed_note="front/rear edges (x, both) finger-jointed; top/bottom (y) plain",
        x_jointed=True, y_jointed=False,
    ),
    PartSpec(
        key="front_wall", svg_file="outer_shell.svg", label="Front Wall",
        art_file="front_wall.png", nominal_mm=(158.75, 118.025), flip_y=False,
        jointed_note="left/right edges (x, both) finger-jointed; top/bottom (y) plain",
        x_jointed=True, y_jointed=False,
    ),
    PartSpec(
        key="top_panel", svg_file="outer_shell.svg", label="Top Panel",
        art_file="top_panel.png", nominal_mm=(222.25, 158.75), flip_y=False,
        jointed_note="front (x=0) plain, rear (x=max) finger-jointed; both side edges (y) "
                      "finger-jointed over the bay span",
        x_jointed=True, y_jointed=True,
    ),
    PartSpec(
        key="sliding_lid", svg_file="lids.svg", label="Sliding Lid",
        art_file="sliding_lid.png", nominal_mm=(79.0, 163.6), flip_y=False,
        rotate="CCW",
        jointed_note="all edges plain (no finger joints)",
        x_jointed=False, y_jointed=False,
    ),
    PartSpec(
        key="faceplate_colors", svg_file="drawer.svg", label="Faceplate",
        art_file="faceplate_colors.png", nominal_mm=(150.9, 53.5), flip_y=False,
        jointed_note="all edges plain (glued, not finger-jointed)",
        x_jointed=False, y_jointed=False,
    ),
    PartSpec(
        key="faceplate_lines", svg_file="drawer.svg", label="Faceplate",
        art_file="faceplate_lines.png", nominal_mm=(150.9, 53.5), flip_y=False,
        jointed_note="all edges plain (glued, not finger-jointed)",
        x_jointed=False, y_jointed=False,
    ),
    PartSpec(
        key="drawer_side_1", svg_file="drawer.svg", label="Left Side",
        art_file="drawer_side_1.png", nominal_mm=(212.25, 50.325), flip_y=False,
        title="Left Side (Drawer 1 of 2 -- template cut twice)",
        jointed_note="front/back edges (x, both) finger-jointed; bottom (y=0) finger-jointed, top plain",
        x_jointed=True, y_jointed=True,
    ),
    PartSpec(
        key="drawer_side_2", svg_file="drawer.svg", label="Right Side",
        art_file="drawer_side_2.png", nominal_mm=(212.25, 50.325), flip_y=False,
        title="Right Side (Drawer 1 of 2 -- template cut twice)",
        jointed_note="front/back edges (x, both) finger-jointed; bottom (y=0) finger-jointed, top plain",
        x_jointed=True, y_jointed=True,
    ),
    PartSpec(
        key="drawer_side_3", svg_file="drawer.svg", label="Left Side",
        art_file="drawer_side_3.png", nominal_mm=(212.25, 50.325), flip_y=False,
        title="Left Side (Drawer 2 of 2 -- template cut twice)",
        jointed_note="front/back edges (x, both) finger-jointed; bottom (y=0) finger-jointed, top plain",
        x_jointed=True, y_jointed=True,
    ),
    PartSpec(
        key="drawer_side_4", svg_file="drawer.svg", label="Right Side",
        art_file="drawer_side_4.png", nominal_mm=(212.25, 50.325), flip_y=False,
        title="Right Side (Drawer 2 of 2 -- template cut twice)",
        jointed_note="front/back edges (x, both) finger-jointed; bottom (y=0) finger-jointed, top plain",
        x_jointed=True, y_jointed=True,
    ),
]

# Assignment of the 4 drawer-side art files to (Left Side/Right Side) x 2
# drawers is NOT specified by DESIGN.md/PLACEMENTS.md (both drawers' side
# panels are cut from one identical template -- see generate_drawers.py,
# _build_side("Left Side")/_build_side("Right Side") are byte-identical
# geometry). Arbitrary assignment used here, in PLACEMENTS.md file order:
# side_1->Drawer1 Left, side_2->Drawer1 Right, side_3->Drawer2 Left,
# side_4->Drawer2 Right. Flagged in PROOFS.md -- swap freely, geometry is
# the same for either side.


# --------------------------------------------------------------------------
# SVG path sampling / drawing helpers
# --------------------------------------------------------------------------


def sample_path_points(d: str, mm_per_sample: float = 0.4) -> list[complex]:
    path = svgpathtools.parse_path(d)
    pts: list[complex] = []
    for seg in path:
        length = seg.length()
        n = max(2, int(length / mm_per_sample) + 1)
        n = min(n, 2000)
        for i in range(n):
            t = i / (n - 1)
            pts.append(seg.point(t))
    return pts


class Transform:
    """Maps a piece's own local (design/SVG) mm coordinates to output pixels.

    No horizontal flip is ever applied (see module docstring). `flip_y` is a
    purely cosmetic up/down choice.
    """

    def __init__(self, bbox: BBox, flip_y: bool, pad_mm: float = PAD_MM):
        self.bbox = bbox
        self.flip_y = flip_y
        self.pad = pad_mm

    def px(self, x: float, y: float) -> tuple[float, float]:
        px = (x - self.bbox.xmin + self.pad) * PX_PER_MM
        if self.flip_y:
            py = (self.bbox.ymax - y + self.pad) * PX_PER_MM
        else:
            py = (y - self.bbox.ymin + self.pad) * PX_PER_MM
        return px, py

    def canvas_size_px(self) -> tuple[int, int]:
        w = (self.bbox.width + 2 * self.pad) * PX_PER_MM
        h = (self.bbox.height + 2 * self.pad + CAPTION_H_MM) * PX_PER_MM
        return int(round(w)), int(round(h))


def draw_path(draw: ImageDraw.ImageDraw, t: Transform, path_info: PathInfo,
              color: tuple, width: int = 3) -> None:
    pts = sample_path_points(path_info.d)
    xy = [t.px(p.real, p.imag) for p in pts]
    if len(xy) >= 2:
        draw.line(xy, fill=color, width=width, joint="curve")


def draw_dashed_rect(draw: ImageDraw.ImageDraw, x0, y0, x1, y1, color, dash=8, gap=6, width=2):
    def dashed_line(ax, ay, bx, by):
        length = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
        if length < 1e-6:
            return
        n = max(1, int(length / (dash + gap)))
        ux, uy = (bx - ax) / length, (by - ay) / length
        d = 0.0
        while d < length:
            d2 = min(d + dash, length)
            draw.line([(ax + ux * d, ay + uy * d), (ax + ux * d2, ay + uy * d2)], fill=color, width=width)
            d += dash + gap

    dashed_line(x0, y0, x1, y0)
    dashed_line(x1, y0, x1, y1)
    dashed_line(x1, y1, x0, y1)
    dashed_line(x0, y1, x0, y0)


def load_font(size: int) -> ImageFont.ImageFont:
    for candidate in [
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]:
        p = Path(candidate)
        if p.exists():
            try:
                return ImageFont.truetype(str(p), size)
            except Exception:
                pass
    return ImageFont.load_default()


FONT = load_font(22)
FONT_SMALL = load_font(16)


# --------------------------------------------------------------------------
# Hole classification (for the PROOFS.md write-up)
# --------------------------------------------------------------------------


def classify_hole(h: PathInfo) -> str:
    w, hh = h.bbox.width, h.bbox.height
    def close(a, b, tol=0.7):
        return abs(a - b) <= tol

    if h.bbox.dims_match(30.0, 15.0, tol=1.0):
        return f"drawer grip slot ({w:.1f}x{hh:.1f}mm, r7.5)"
    if h.bbox.dims_match(30.0, 10.0, tol=1.0):
        return f"lid grip slot ({w:.1f}x{hh:.1f}mm, r5)"
    if h.bbox.dims_match(152.4, 55.0, tol=2.0):
        return f"rear-wall drawer opening ({w:.1f}x{hh:.1f}mm)"
    if h.bbox.dims_match(76.2, 3.975, tol=1.5):
        return f"lid through-slot mouth ({w:.1f}x{hh:.1f}mm)"
    if close(w, hh, tol=1.0) and close(w, 5.65, tol=1.2):
        return f"magnet hole (~{w:.1f}mm dia)"
    if close(w, hh, tol=1.0) and close(w, 3.2, tol=1.0):
        return f"turn-button pivot hole (~{w:.1f}mm dia)"
    if min(w, hh) < 4.5:
        return f"finger-hole dash ({w:.1f}x{hh:.1f}mm)"
    return f"cutout {w:.1f}x{hh:.1f}mm"


def summarize_hole_rows(holes: list[PathInfo]) -> list[str]:
    """Group finger-hole dashes into rows (span + cross-axis center) for a
    compact PROOFS.md summary, rather than listing every single dash."""
    small = [h for h in holes if min(h.bbox.width, h.bbox.height) < 4.5
             and normalize_color(h.stroke) == "blue"]
    horiz = [h for h in small if h.bbox.width > h.bbox.height]
    vert = [h for h in small if h.bbox.height >= h.bbox.width]

    def group(items, cross_attr):
        groups: dict[int, list] = {}
        for h in items:
            c = getattr(h.bbox, cross_attr)
            groups.setdefault(round(c / 1.5), []).append(h)
        return groups

    lines = []
    hgroups = group(horiz, "ymin")
    for _, items in hgroups.items():
        if len(items) < 2:
            continue
        xs = [i.bbox.xmin for i in items] + [i.bbox.xmax for i in items]
        ys = [i.bbox.ymin for i in items]
        lines.append(f"horizontal finger-hole row, {len(items)} holes, "
                      f"x-span {min(xs):.1f}-{max(xs):.1f}mm, y~{sum(ys)/len(ys):.1f}mm")
    vgroups = group(vert, "xmin")
    for _, items in vgroups.items():
        if len(items) < 2:
            continue
        ys = [i.bbox.ymin for i in items] + [i.bbox.ymax for i in items]
        xs = [i.bbox.xmin for i in items]
        lines.append(f"vertical finger-hole column, {len(items)} holes, "
                      f"y-span {min(ys):.1f}-{max(ys):.1f}mm, x~{sum(xs)/len(xs):.1f}mm")
    return lines


# --------------------------------------------------------------------------
# Core render
# --------------------------------------------------------------------------


@dataclass
class RenderResult:
    spec: PartSpec
    piece: Piece
    out_path: Path
    margins: dict
    overlaps: list[str]
    art_size_mm: tuple[float, float]
    nominal_rect_local: tuple[float, float, float, float]  # x0,y0,x1,y1 in local mm


def load_art(spec: PartSpec) -> Image.Image:
    img = Image.open(ART_DIR / spec.art_file).convert("L")
    if spec.rotate == "CCW":
        img = img.transpose(Image.ROTATE_90)
    elif spec.rotate == "CW":
        img = img.transpose(Image.ROTATE_270)
    elif spec.rotate == "180":
        img = img.transpose(Image.ROTATE_180)
    return img


def render_part(spec: PartSpec) -> RenderResult:
    svg_path = OUTPUT_SVG_DIR / spec.svg_file
    pieces = design_pieces(svg_path)
    piece = find_piece_by_label(pieces, spec.label)
    if piece is None:
        raise RuntimeError(f"Piece labeled {spec.label!r} not found in {svg_path}")

    bbox = piece.bbox
    t = Transform(bbox, spec.flip_y)
    w_px, h_px = t.canvas_size_px()
    canvas = Image.new("RGBA", (w_px, h_px), (255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)

    # --- art ---
    art_img = load_art(spec)
    nom_w, nom_h = spec.nominal_mm
    cx = (bbox.xmin + bbox.xmax) / 2
    cy = (bbox.ymin + bbox.ymax) / 2
    x0, y0 = cx - nom_w / 2, cy - nom_h / 2
    x1, y1 = cx + nom_w / 2, cy + nom_h / 2
    p0 = t.px(x0, y0)
    p1 = t.px(x1, y1)
    left, top = min(p0[0], p1[0]), min(p0[1], p1[1])
    right, bottom = max(p0[0], p1[0]), max(p0[1], p1[1])
    art_w_px, art_h_px = int(round(right - left)), int(round(bottom - top))
    art_resized = art_img.resize((max(1, art_w_px), max(1, art_h_px)), Image.LANCZOS)
    art_rgba = Image.new("RGBA", art_resized.size, (0, 0, 0, 0))
    art_arr = np.array(art_resized)
    alpha = 255 - art_arr  # black ink -> opaque, white -> transparent
    art_rgba.putdata(list(zip([0] * art_arr.size, [0] * art_arr.size, [0] * art_arr.size, alpha.flatten().tolist())))
    canvas.alpha_composite(art_rgba, (int(round(left)), int(round(top))))
    draw = ImageDraw.Draw(canvas)

    # --- dashed nominal-blank rectangle ---
    draw_dashed_rect(draw, left, top, right, bottom, DASH_GRAY, dash=10, gap=7, width=2)

    # --- cut geometry (blue) + engraves (red), drawn ON TOP of the art ---
    is_right_wall = spec.label == "Right Wall"
    for h in [piece.outer, *piece.holes]:
        color = normalize_color(h.stroke)
        if color == "blue":
            draw_path(draw, t, h, BLUE, width=3)
        elif color == "red":
            # Right Wall's "FAX MACHINE" pixel engrave is being REMOVED at
            # integration (superseded by the new wall art) -- draw faintly.
            if is_right_wall:
                draw_path(draw, t, h, FAINT_RED, width=1)
            else:
                draw_path(draw, t, h, RED, width=2)

    # --- scale bar + caption band ---
    band_y0 = int(round((bbox.height + 2 * PAD_MM) * PX_PER_MM))
    bar_x0 = int(PAD_MM * PX_PER_MM * 0.5)
    bar_y = band_y0 + 14
    bar_len = int(SCALEBAR_MM * PX_PER_MM)
    draw.line([(bar_x0, bar_y), (bar_x0 + bar_len, bar_y)], fill=BLACK, width=4)
    draw.text((bar_x0, bar_y + 8), f"{SCALEBAR_MM:.0f}mm", fill=BLACK, font=FONT_SMALL)

    title = spec.title or spec.label
    draw.text((bar_x0 + bar_len + 30, band_y0 + 4), f"{title}", fill=BLACK, font=FONT)
    draw.text((bar_x0 + bar_len + 30, band_y0 + 32), f"art: {spec.art_file}   "
              f"drawn part {bbox.width:.1f}x{bbox.height:.1f}mm   "
              f"nominal {nom_w:.1f}x{nom_h:.1f}mm   blue=cut  red=engrave  gray dash=nominal blank",
              fill=(60, 60, 60, 255), font=FONT_SMALL)
    if is_right_wall:
        draw.text((bar_x0 + bar_len + 30, band_y0 + 56),
                  "NOTE: faint pink = existing 'FAX MACHINE' pixel-font engrave in the SVG -- "
                  "being REMOVED at integration (superseded by this wall art).",
                  fill=(160, 0, 0, 255), font=FONT_SMALL)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{spec.key}.png"
    canvas.convert("RGB").save(out_path)

    # --- margins & overlap analysis ---
    margins = {
        "x_each_side": max(0.0, (bbox.width - nom_w) / 2),
        "y_each_side": max(0.0, (bbox.height - nom_h) / 2),
        "drawn_w": bbox.width, "drawn_h": bbox.height,
        "nominal_w": nom_w, "nominal_h": nom_h,
    }
    nominal_bbox_local = BBox(x0, x1, y0, y1)
    overlaps = []
    for h in piece.holes:
        if normalize_color(h.stroke) != "blue":
            continue
        if nominal_bbox_local.overlaps(h.bbox, tol=0.0):
            overlaps.append(classify_hole(h))
    row_summaries = summarize_hole_rows([h for h in piece.holes if nominal_bbox_local.overlaps(h.bbox, tol=0.0)])

    return RenderResult(
        spec=spec, piece=piece, out_path=out_path, margins=margins,
        overlaps=row_summaries + [o for o in overlaps if "finger-hole dash" not in o],
        art_size_mm=(nom_w, nom_h),
        nominal_rect_local=(x0, y0, x1, y1),
    )


# --------------------------------------------------------------------------
# Assembled lid+top-panel seam strip
# --------------------------------------------------------------------------


def _paste_seam_canvas(lid_img: Image.Image, panel_img: Image.Image, caption: str,
                        out_name: str) -> Path:
    """Shared seam-strip compositor: paste a lid image (offset down by the
    DESIGN.md-adjacent seam step) next to a panel image, with a green seam
    line + caption. Used by both the canonical (geometry-composited) seam
    strip and the minimal VARIANT_B raw-art seam strip."""
    step_mm = 5.8  # lid rides in through-slots above the front-wall top;
    # the top panel sits at TOP_PANEL_Z0 -- drawn here as a simple visual
    # offset marker, not a precise re-derivation of the through-slot geometry.
    gap_px = 40
    step_px = int(step_mm * PX_PER_MM)

    h = max(lid_img.height, panel_img.height) + step_px + 60
    w = lid_img.width + gap_px + panel_img.width
    canvas = Image.new("RGB", (w, h), (255, 255, 255))
    canvas.paste(lid_img, (0, step_px))
    canvas.paste(panel_img, (lid_img.width + gap_px, 0))
    draw = ImageDraw.Draw(canvas)
    seam_x = lid_img.width + gap_px // 2
    draw.line([(seam_x, 0), (seam_x, h)], fill=(0, 150, 0), width=2)
    draw.text((10, h - 40), caption, fill=(0, 100, 0), font=FONT_SMALL)
    out_path = OUT_DIR / out_name
    canvas.save(out_path)
    return out_path


def render_seam_strip(results_by_key: dict) -> Path:
    lid_res = results_by_key["sliding_lid"]
    panel_res = results_by_key["top_panel"]
    lid_img = Image.open(lid_res.out_path)
    panel_img = Image.open(panel_res.out_path)
    step_mm = 5.8
    return _paste_seam_canvas(
        lid_img, panel_img,
        "Lid + Top Panel seam-continuity check "
        f"(lid drawn offset down {step_mm}mm -- visual step marker, "
        "front-to-rear panorama should read continuously left-to-right)",
        "lid_top_panel_seam.png")


VARIANT_DESCRIPTIONS = {
    "B": "VARIANT B (centered-window)",
    "C": "VARIANT C (cat-end-anchored window: full cat kept, snake head trimmed)",
}


def render_variant_seam(label: str) -> Path | None:
    """Rev-3+: minimal seam-continuity proof for a trim-judgment variant pair
    (sliding_lid_VARIANT_<label>.png / top_panel_VARIANT_<label>.png -- see
    art_postprocess.py's process_4231). These files have no PartSpec /
    cut-geometry overlay (they're a trim-judgment comparison, not a candidate
    to actually cut) -- reuses load_art()'s rotation convention and
    _paste_seam_canvas() directly rather than the full render_part() geometry
    pipeline, per BRIEF's 'minimal code' instruction."""
    lid_path = ART_DIR / f"sliding_lid_VARIANT_{label}.png"
    panel_path = ART_DIR / f"top_panel_VARIANT_{label}.png"
    if not lid_path.exists() or not panel_path.exists():
        return None
    lid_spec = next(s for s in PART_SPECS if s.key == "sliding_lid")
    lid_img = Image.open(lid_path).convert("L")
    if lid_spec.rotate == "CCW":
        lid_img = lid_img.transpose(Image.ROTATE_90)
    elif lid_spec.rotate == "CW":
        lid_img = lid_img.transpose(Image.ROTATE_270)
    elif lid_spec.rotate == "180":
        lid_img = lid_img.transpose(Image.ROTATE_180)
    panel_img = Image.open(panel_path).convert("L")
    return _paste_seam_canvas(
        lid_img.convert("RGB"), panel_img.convert("RGB"),
        f"{VARIANT_DESCRIPTIONS[label]} seam-continuity check -- "
        "trim-judgment comparison only, not a cut candidate; canonical A "
        "files (sliding_lid.png/top_panel.png, head-anchored) are what "
        "art_proofs.py's main per-part renders use.",
        f"lid_top_panel_seam_VARIANT_{label}.png")


def render_contact_sheet(paths: list[Path]) -> Path:
    imgs = [Image.open(p) for p in paths]
    thumb_w = 520
    thumbs = []
    for im in imgs:
        ratio = thumb_w / im.width
        thumbs.append(im.resize((thumb_w, max(1, int(im.height * ratio)))))
    cols = 3
    rows = (len(thumbs) + cols - 1) // cols
    row_h = max(t.height for t in thumbs) + 10
    sheet = Image.new("RGB", (cols * (thumb_w + 10), rows * row_h), (255, 255, 255))
    for i, th in enumerate(thumbs):
        r, c = divmod(i, cols)
        sheet.paste(th, (c * (thumb_w + 10) + 5, r * row_h + 5))
    out_path = OUT_DIR / "contact_sheet.png"
    sheet.save(out_path)
    return out_path


# --------------------------------------------------------------------------
# PROOFS.md
# --------------------------------------------------------------------------


def write_proofs_md(results: list[RenderResult], seam_path: Path, contact_path: Path,
                     variant_seam_paths: dict[str, Path] | None = None) -> None:
    variant_seam_paths = variant_seam_paths or {}
    lines = []
    lines.append("# Placement proofs -- art-integration gate\n")
    lines.append("Generated by `scripts/art_proofs.py` (deterministic, no args). "
                  "All part geometry regenerated fresh from `faxbox.shell_generator` / "
                  "`faxbox.generate_drawers` / `faxbox.generate_lids` immediately before "
                  "rendering.\n")
    lines.append("Rendering convention: 20px/mm, black = art (what will burn), "
                  "vivid blue = every cut path (outline + holes/slots/fingers) for that "
                  "part, vivid red = a real engrave that stays, faint pink = an engrave "
                  "being removed at integration, gray dashed rectangle = the DESIGN.md "
                  "nominal blank (art is centered on this). NO horizontal flip is ever "
                  "applied when rendering -- see the wall-orientation derivation below.\n")

    lines.append("## Wall orientation derivation (Left/Right Wall)\n")
    lines.append(
        "DESIGN.md coordinate convention: origin at the exterior front-left-bottom "
        "corner, X front(0)->rear(304.8), Y left(0)->right(165.1), Z bottom(0)->top(127). "
        "Left/Right wall labels are only meaningful relative to a viewer standing at the "
        "box's front facing the rear (the standard 'driver's seat' convention any door/"
        "wall left-right label implicitly assumes) -- i.e. facing +X with +Z up, that "
        "viewer's right hand is +Y (confirmed: the right wall IS the higher-Y wall, "
        "Y=161.9->165.1). For a right-handed (X,Y,Z) frame this fixes X x Y = Z.\n\n"
        "Viewing the LEFT wall's exterior from outside the box: the viewer stands at "
        "Y<0 looking toward +Y (gaze F=+Y), up U=+Z. For this handedness, "
        "Right = U x F = Z x Y = -X (front direction, since X increases toward rear). "
        "So **on the Left Wall exterior, FRONT is on the viewer's RIGHT.**\n\n"
        "Viewing the RIGHT wall's exterior from outside: viewer stands at Y>165.1 "
        "looking toward -Y (gaze F=-Y). Right = U x F = Z x (-Y) = +X (rear direction). "
        "So **on the Right Wall exterior, FRONT is on the viewer's LEFT.**\n\n"
        "This matches a flat-pattern sanity check: `shell_generator._build_side_wall` "
        "draws both walls exterior-face-up; erecting a flat, exterior-up panel by "
        "hinging it up about its own bottom (horizontal) edge into a vertical wall does "
        "not mirror left/right (the hinge axis is parallel to local-x), so the flat "
        "pattern's local-x, rendered directly with no flip, already IS the 'viewed from "
        "outside' image.\n\n"
        "In the generated SVG (`shell_generator.py::_build_side_wall`), the Right Wall "
        "is drawn `mirror=False` with front at local x=0 (the lid-slot mouth is drawn "
        "flush with local x=0); the Left Wall is drawn `mirror=True`, which the "
        "generator's own `mirror_point()`/`mirror_start()` helpers use to reflect every "
        "feature in local-x, putting the Left Wall's front at local x=length instead. "
        "Rendering local-x directly to pixel-x (no flip, per above) therefore already "
        "gives: Right Wall front at pixel-LEFT, Left Wall front at pixel-RIGHT -- "
        "exactly the required real-world relationship. **No mirroring of the cut-"
        "geometry render is needed for either wall.**\n\n"
        "Art placement: `left_wall.png`/`right_wall.png` are direct photographs (IMG_4228, "
        "IMG_4230) of those exact wall exteriors (not a shared/mirrored source graphic), "
        "cropped/thresholded but never flipped (checked against PLACEMENTS.md's processing "
        "log for both files -- crop + threshold + downscale only). A photograph is "
        "already a 'viewed from outside' image, so placing it unflipped/unrotated, "
        "centered on the nominal rectangle, is consistent with the geometry above. "
        "**No mirror/rotation applied to either wall's art; visually confirmed by reading "
        "the rendered proofs (text and character orientation read normally, not mirrored).**\n"
    )

    lines.append("## Sliding Lid rotation derivation\n")
    lines.append(
        "**REV-3 NOTE**: the axis-convention conclusion below (which 90-degree "
        "rotation direction fits the file to the portrait SVG piece) is a property "
        "of `art_postprocess.py`'s field construction (rows/cols indexing), NOT of "
        "specific art content -- it is UNCHANGED by rev 3's head-anchored placement "
        "(same `np.rot90(k=-1)` baked into the file, reused deliberately, per "
        "PLACEMENTS.md). The *evidence* cited below (floral border position, the "
        "cat's hose flowing into the tail-curl) describes the OLD rev-2 "
        "capsule-registered content at that seam and no longer matches what's in "
        "`sliding_lid.png`/`top_panel.png` today (rev 3's seam now falls inside the "
        "scale pattern, not the floral border) -- kept here as the historical "
        "record of how the rotation direction was validated; re-verify against "
        "`lid_top_panel_seam.png` directly for current content.\n"
    )
    lines.append(
        "The SVG piece (`generate_lids.py`) is drawn PORTRAIT: local x = 0->79mm is "
        "depth/front-rear (grip slot's `center_from_front`=25mm is a literal local-x "
        "value), local y = 0->163.6mm is box-Y width. The stored `sliding_lid.png` "
        "(1932x933px) is LANDSCAPE (163.6mm horizontal x 79mm vertical) -- PLACEMENTS.md "
        "confirms an internal `np.rot90` was applied during generation, so the file needs "
        "a 90-degree rotation to fit the portrait SVG piece; PLACEMENTS.md itself flagged "
        "the rotation *direction* (CW vs CCW) as unverified.\n\n"
        "Resolved empirically, not assumed: the lid and top-panel art were cut from the "
        "same continuous panorama field, split at the lid/panel boundary (PLACEMENTS.md: "
        "`split_x=1443px`=79mm from front). The correct rotation is whichever one makes "
        "the lid's cut edge continue seamlessly into `top_panel.png`'s front (left) edge. "
        "Both 90-degree rotations were rendered and compared directly "
        "(scratch/art-proofs working files during development): rotating "
        "`PIL.Image.ROTATE_90` (counter-clockwise) lines up the floral border at the same "
        "vertical position in both images AND the hose held by the cat's paw flows "
        "directly into the tail-curl that opens `top_panel.png` -- a clean continuation. "
        "The other rotation (ROTATE_270/CW) puts the cat upside-down relative to the top "
        "panel and the floral border on the opposite edge -- clearly wrong. "
        "**Chosen: `ROTATE_90` (CCW). See `lid_top_panel_seam.png` for the assembled "
        "continuity check.**\n"
    )

    lines.append("## Grip-capsule verdict (Sliding Lid) -- SUPERSEDED BY REV 3\n")
    lines.append(
        "**REV-3 NOTE**: this whole section describes rev 2's CAPSULE-REGISTERED "
        "placement, which rev 3 replaced entirely (head-anchored panorama window, "
        "no reserved blank capsule -- Ben explicitly accepted the grip slot cutting "
        "into drawn art). Kept below only as the historical record of the rev-2 "
        "finding that motivated the rev-3 rework. **For the CURRENT grip-slot "
        "placement, see `art/engrave/PLACEMENTS.md`'s `sliding_lid.png` entry "
        "('GRIP SLOT LOCATION') -- the slot now lands in the front third of the "
        "snake-head mosaic, between the two eyes, crossing mosaic-tile boundary "
        "lines but not a drawn eye.**\n"
    )
    lines.append(
        "The art reserves a blank rounded-capsule zone for the grip slot (measured "
        "directly in the art, connected-component analysis): after the CCW rotation "
        "above, the capsule sits centered at local x ~= 39.0mm (depth), width-axis "
        "center ~= 81.0mm, dimensions ~9.2 x 28.5mm (long axis along depth). "
        "The REAL grip slot (`LID_GRIP_SLOT` in config.py) is 30x10mm (long axis also "
        "along depth), centered at local x = 25.0mm (depth, `center_from_front`), "
        "y = 81.8mm (width) -- i.e. spanning depth 10.0-40.0mm.\n\n"
        "**Width-axis (side-to-side) centering matches well** (81.0mm measured vs 81.8mm "
        "nominal, ~0.8mm off). **Depth-axis position does NOT match**: the art's reserved "
        "capsule spans depth ~24.7-53.3mm, centered ~39.0mm from front, while the real "
        "slot spans depth 10.0-40.0mm, centered at 25.0mm -- the art's blank zone sits "
        "roughly **14mm further from the front (toward the rear) than the actual cut "
        "slot**. Consequence: the real slot's front ~14mm (depth 10-24.7mm) will cut "
        "through DRAWN linework (the hose/paint-brush area), not through the reserved "
        "blank -- visible directly in `sliding_lid.png`'s blue overlay. "
        "**This should block sign-off until Ben confirms** whether to accept the slot "
        "cutting into that linework, or whether the art's capsule was meant to mark a "
        "different (aesthetic-only) reference and the real slot's placement is what "
        "actually governs.\n"
    )
    lines.append(
        "**Separate finding -- front-edge content gap (ALSO SUPERSEDED BY REV 3)**: "
        "rev 2's `sliding_lid.png` had its front-most ~16mm completely blank (no ink). "
        "Rev 3's head-anchored placement was designed specifically to fix this: the "
        "snake head's linework now reaches the front edge (row 0 of the current file "
        "carries ink -- verified directly), though the head's rounded/tapered outline "
        "means coverage at the extreme front edge is still partial (~7% of the width "
        "inked at row 0, growing quickly inward; PLACEMENTS.md's sliding_lid entry "
        "quantifies this under 'Front-edge white-run search'). The residual "
        "partial-coverage question at the very front lip is flagged there for Ben "
        "-- an 8mm-capped forward nudge could not fully clear the head's diagonal "
        "boundary.\n"
    )

    lines.append("## Top Panel seam derivation\n")
    lines.append(
        "`shell_generator.py::_build_top_panel`: front edge (the divider side) is the "
        "plain edge at local x=0; rear (rear-wall side) is finger-jointed at local "
        "x=nominal. PLACEMENTS.md: `top_panel.png` was cut from the SAME field as the "
        "lid, starting exactly at the lid/panel split (front-most column of the top-panel "
        "half = the split boundary = adjacent to the lid). Placing `top_panel.png` "
        "directly (pixel-x=0 -> local x=0, no flip/rotate) puts its front edge at the "
        "correct (divider) side and was confirmed by the same lid-seam continuity check "
        "above (`lid_top_panel_seam.png`).\n"
    )

    lines.append("## Per-part details\n")
    for r in results:
        s = r.spec
        title = s.title or s.label
        lines.append(f"### {title} -- `{s.art_file}`\n")
        m = r.margins
        lines.append(f"- Drawn part bbox: {m['drawn_w']:.2f} x {m['drawn_h']:.2f}mm. "
                      f"Nominal (art canvas): {m['nominal_w']:.2f} x {m['nominal_h']:.2f}mm.")
        lines.append(f"- Margin from art edge to drawn-part edge (art is bbox-centered): "
                      f"{m['x_each_side']:.2f}mm each side in x, {m['y_each_side']:.2f}mm each side in y.")
        lines.append(f"- Edge joint note: {s.jointed_note}.")
        if r.overlaps:
            lines.append("- Cut features overlapping the art:")
            for o in r.overlaps:
                lines.append(f"  - {o}")
        else:
            lines.append("- Cut features overlapping the art: none detected inside the nominal rectangle "
                          "(only the outer boundary's own finger notches near the margins, if any -- see margin note).")
        MARGIN_WARN_MM = 4.0  # DESIGN.md's own "4mm from jointed edges" guideline
        if m["x_each_side"] < MARGIN_WARN_MM and s.x_jointed:
            lines.append(f"- **MARGIN FLAG**: x-margin ({m['x_each_side']:.2f}mm) is under the {MARGIN_WARN_MM:.0f}mm "
                          f"finger-notch clearance guideline, and an x-edge here IS finger-jointed -- finger "
                          f"notches (up to {MATERIAL_THICKNESS:.3f}mm deep) may reach into or very close to the art.")
        if m["y_each_side"] < MARGIN_WARN_MM and s.y_jointed:
            lines.append(f"- **MARGIN FLAG**: y-margin ({m['y_each_side']:.2f}mm) is under the {MARGIN_WARN_MM:.0f}mm "
                          f"finger-notch clearance guideline, and a y-edge here IS finger-jointed -- finger "
                          f"notches (up to {MATERIAL_THICKNESS:.3f}mm deep) may reach into or very close to the art.")
        lines.append(f"- Proof: `{r.out_path.name}`\n")

    lines.append("## Drawer-side art-to-part assignment (arbitrary, flagged)\n")
    lines.append(
        "`drawer.svg` contains ONE 'Left Side' and ONE 'Right Side' piece (a template, "
        "physically cut twice -- once per drawer; both are geometrically IDENTICAL, "
        "`generate_drawers.py::_build_side` uses the same edge codes for both, only the "
        "label differs). Nothing in DESIGN.md/PLACEMENTS.md specifies which of the 4 "
        "drawer-side art files (turkeys/desert, alligator/seagull, gallery/audience, "
        "bookshelf/BLAH) goes on which drawer or which side. Assignment used here is "
        "arbitrary (file order): drawer_side_1->Drawer1 Left, _2->Drawer1 Right, "
        "_3->Drawer2 Left, _4->Drawer2 Right. Swap freely -- the geometry is identical "
        "either way, so this is purely a content-pairing decision for Ben.\n"
    )

    lines.append("## Right Wall engrave removal\n")
    lines.append(
        "The regenerated `outer_shell.svg` still contains the old red 'FAX MACHINE' "
        "pixel-font engrave on the Right Wall (`shell_generator.py::_engrave_fax_machine`, "
        "still called from `_build_side_wall(..., engrave=True)`). This is drawn faintly "
        "(light pink) in `right_wall.png`'s proof and is expected to be REMOVED from the "
        "generator once the new right_wall.png art (which already carries its own title "
        "lettering) is integrated -- flagging so it isn't mistaken for a second engrave "
        "layer that will actually ship.\n"
    )

    if variant_seam_paths:
        lines.append("## Lid/top-panel trim-judgment VARIANTS\n")
        lines.append(
            "`art_postprocess.py`'s process_4231 produces alternative window "
            "pairs alongside the canonical head-anchored A pair, so Ben can "
            "compare trim judgments at this gate: B = centered window "
            "(rejected by Ben 2026-07-11, kept for reference), C = cat-end-"
            "anchored window (Ben's 2026-07-11 request: the FULL cat + floral "
            "border survive at the panel's rear; the snake-head end is "
            "trimmed instead; lid carries the region just past the trimmed "
            "head). Variants have no PartSpec / cut-geometry overlay (not "
            "cut candidates); each gets a minimal seam-continuity strip "
            "only. See art/engrave/PLACEMENTS.md's sliding_lid.png entry "
            "('VARIANT B'/'VARIANT C') for exact window numbers and what "
            "each variant trims. NOTE for variant C: the source art's "
            "baked-in reserved grip capsule (a blank white pill, a leftover "
            "of the abandoned rev-2 composition) falls INSIDE the kept "
            "window and reads as an empty patch in the panel art -- if Ben "
            "picks C, that region gets a one-shot infill pass before "
            "tracing.\n"
        )

    lines.append("## Files\n")
    lines.append(f"- `{seam_path.name}` -- lid+top-panel seam continuity strip.")
    for label, p in sorted(variant_seam_paths.items()):
        lines.append(f"- `{p.name}` -- {VARIANT_DESCRIPTIONS[label]} "
                      "seam continuity strip, trim-judgment comparison only.")
    lines.append(f"- `{contact_path.name}` -- contact sheet of all proofs.")
    for r in results:
        lines.append(f"- `{r.out_path.name}`")

    (OUT_DIR / "PROOFS.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    print("Regenerating SVGs...")
    regenerate_svgs()

    results = []
    results_by_key = {}
    for spec in PART_SPECS:
        print(f"Rendering {spec.key} ...")
        r = render_part(spec)
        results.append(r)
        results_by_key[spec.key] = r

    print("Rendering lid/top-panel seam strip...")
    seam_path = render_seam_strip(results_by_key)

    variant_seam_paths = {}
    for label in VARIANT_DESCRIPTIONS:
        print(f"Rendering VARIANT {label} seam strip (if present)...")
        p = render_variant_seam(label)
        if p is not None:
            variant_seam_paths[label] = p

    print("Rendering contact sheet...")
    all_part_paths = [r.out_path for r in results] + [seam_path]
    contact_path = render_contact_sheet(all_part_paths)

    print("Writing PROOFS.md...")
    write_proofs_md(results, seam_path, contact_path, variant_seam_paths)

    print(f"Done. Output in {OUT_DIR}")


if __name__ == "__main__":
    main()
