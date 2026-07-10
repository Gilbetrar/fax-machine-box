#!/usr/bin/env python3
"""Render QA images of every Ponoko sheet SVG + every part on those sheets,
so a vision-capable reviewer can visually inspect the actual laser-cut
output before it goes to a fabricator.

For each sheet SVG (default: output/ponoko/sheet_1.svg, sheet_2.svg,
sheet_3.svg) this produces, under scratch/qa-renders/<sheet>/:

  <sheet>_overview.png          whole sheet, fit to ~2000px wide, true stroke
  <sheet>_full_20pxmm.png       whole sheet at ~20 px/mm, true stroke
  <sheet>_full_20pxmm_thick.png whole sheet at ~20 px/mm, thickened stroke (bonus)
  <part-slug>.png               part bbox + 5mm margin, cropped from the
                                 20px/mm sheet render, true stroke width
  <part-slug>_thick.png         same crop, stroke thickened to 0.15mm
  <part-slug>_corner_{nw,ne,sw,se}.png        15x15mm window at each bbox
                                                corner, ~40 px/mm, true width
  <part-slug>_corner_{nw,ne,sw,se}_thick.png  same, thickened stroke

A manifest.json at scratch/qa-renders/manifest.json lists every PNG produced,
with its sheet, part label (if any), crop type, and mm region.

Why "thickened" renders exist at all: this project's cut/engrave strokes are
laser-hairline width (0.0762mm == 0.003in), which is at or below one pixel
even at 20-40 px/mm and can vanish or alias badly when downsampled for
review. The thickened copies (stroke-width overridden to 0.15mm) are
rendered from an in-memory string-patched copy of the SVG -- nothing under
output/ is ever modified on disk.

Geometry note: every sheet SVG in this project uses `width="<N>mm"
height="<M>mm"` with a matching `viewBox="0 0 <N> <M>"` -- i.e. 1 SVG user
unit == 1mm. This script assumes that (and asserts it) rather than doing
general unit conversion.

Path commands: every part group's paths in this project's current output
use only absolute M/L/C (verified by grep before writing this). This parser
also handles the relative lowercase forms (m/l/c), H/V/h/v, and Z/z, and
approximates cubic Bezier extents by sampling, per the task spec. Any other
command (arcs, S/Q/T) is not expected; if encountered, the part is flagged
as "suspicious" in the final report rather than silently mis-measured.

Usage:
    .venv/bin/python scripts/qa_render.py
    .venv/bin/python scripts/qa_render.py --sheets output/ponoko/sheet_2.svg
    .venv/bin/python scripts/qa_render.py --out scratch/qa-renders
"""

from __future__ import annotations

import argparse
import gc
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

import cairosvg
from PIL import Image

# These sheets are large (up to ~110M px at 20px/mm); disable Pillow's
# decompression-bomb guard rather than silently downscaling or warning on
# every run -- these are legitimate, locally-generated renders.
Image.MAX_IMAGE_PIXELS = None

SVG_NS = "{http://www.w3.org/2000/svg}"

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SHEETS = [
    REPO_ROOT / "output" / "ponoko" / "sheet_1.svg",
    REPO_ROOT / "output" / "ponoko" / "sheet_2.svg",
    REPO_ROOT / "output" / "ponoko" / "sheet_3.svg",
]
DEFAULT_OUT = REPO_ROOT / "scratch" / "qa-renders"

OVERVIEW_WIDTH_PX = 2000
HIGH_RES_PX_PER_MM = 20.0
CORNER_PX_PER_MM = 40.0
CORNER_SIZE_MM = 15.0
PART_MARGIN_MM = 5.0
THICK_STROKE_MM = 0.15
BEZIER_SAMPLES = 24

_STROKE_WIDTH_RE = re.compile(r'stroke-width="[^"]*"')
_VIEWBOX_RE = re.compile(r'viewBox="[^"]*"')
_WIDTH_ATTR_RE = re.compile(r'(<svg[^>]*\bwidth=")[^"]*(")')
_HEIGHT_ATTR_RE = re.compile(r'(<svg[^>]*\bheight=")[^"]*(")')

_TOKEN_RE = re.compile(r"([MmLlHhVvCcSsQqTtAaZz])|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)")
_HANDLED = set("MmLlHhVvCcZz")


# --- geometry / path parsing ------------------------------------------------


def slugify(label: str) -> str:
    s = label.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def cubic_bezier_points(p0, p1, p2, p3, n=BEZIER_SAMPLES):
    pts = []
    for i in range(1, n + 1):
        t = i / n
        mt = 1 - t
        x = (mt**3) * p0[0] + 3 * (mt**2) * t * p1[0] + 3 * mt * (t**2) * p2[0] + (t**3) * p3[0]
        y = (mt**3) * p0[1] + 3 * (mt**2) * t * p1[1] + 3 * mt * (t**2) * p2[1] + (t**3) * p3[1]
        pts.append((x, y))
    return pts


def parse_path_points(d: str, warnings: list[str], context: str) -> list[tuple[float, float]]:
    """Return a list of (x, y) sample points (in the path's own coordinate
    space) approximating the path's true extents, tolerant of both absolute
    and relative M/L/H/V/C/Z. Any other command triggers a warning and a
    best-effort fallback (treat its numeric args pairwise as absolute
    points, which over-estimates rather than silently under-estimates the
    bbox)."""
    tokens = _TOKEN_RE.findall(d)
    ops: list[tuple[str, list[float]]] = []
    cmd = None
    nums: list[float] = []
    for letter, num in tokens:
        if letter:
            if cmd is not None:
                ops.append((cmd, nums))
            cmd = letter
            nums = []
        else:
            nums.append(float(num))
    if cmd is not None:
        ops.append((cmd, nums))

    pts: list[tuple[float, float]] = []
    cur = (0.0, 0.0)
    subpath_start = (0.0, 0.0)

    for cmd, nums in ops:
        is_rel = cmd.islower()
        C = cmd.upper()
        if C == "M":
            i = 0
            first = True
            while i < len(nums):
                x, y = nums[i], nums[i + 1]
                if is_rel:
                    x, y = cur[0] + x, cur[1] + y
                cur = (x, y)
                if first:
                    subpath_start = cur
                    first = False
                pts.append(cur)
                i += 2
        elif C == "L":
            i = 0
            while i < len(nums):
                x, y = nums[i], nums[i + 1]
                if is_rel:
                    x, y = cur[0] + x, cur[1] + y
                cur = (x, y)
                pts.append(cur)
                i += 2
        elif C == "H":
            for x in nums:
                nx = (cur[0] + x) if is_rel else x
                cur = (nx, cur[1])
                pts.append(cur)
        elif C == "V":
            for y in nums:
                ny = (cur[1] + y) if is_rel else y
                cur = (cur[0], ny)
                pts.append(cur)
        elif C == "C":
            i = 0
            while i < len(nums):
                x1, y1, x2, y2, x, y = nums[i : i + 6]
                if is_rel:
                    x1, y1 = cur[0] + x1, cur[1] + y1
                    x2, y2 = cur[0] + x2, cur[1] + y2
                    x, y = cur[0] + x, cur[1] + y
                pts.extend(cubic_bezier_points(cur, (x1, y1), (x2, y2), (x, y)))
                cur = (x, y)
                i += 6
        elif C == "Z":
            pts.append(subpath_start)
            cur = subpath_start
        else:
            warnings.append(f"{context}: unhandled path command {cmd!r} -- using raw numeric pairs as fallback")
            i = 0
            while i + 1 < len(nums):
                x, y = nums[i], nums[i + 1]
                if is_rel:
                    x, y = cur[0] + x, cur[1] + y
                pts.append((x, y))
                cur = (x, y)
                i += 2
    return pts


@dataclass
class Part:
    sheet: str
    group_id: str
    label: str
    slug: str
    bbox: tuple[float, float, float, float]  # xmin, ymin, xmax, ymax (mm)
    n_paths: int
    suspicious: list[str] = field(default_factory=list)


def load_sheet_dims(svg_text: str) -> tuple[float, float]:
    root = ET.fromstring(svg_text)
    w = root.get("width", "").strip()
    h = root.get("height", "").strip()
    assert w.endswith("mm") and h.endswith("mm"), f"expected mm units, got width={w!r} height={h!r}"
    width_mm = float(w[:-2])
    height_mm = float(h[:-2])
    vb = root.get("viewBox")
    if vb:
        parts = [float(x) for x in vb.split()]
        vb_w, vb_h = parts[2], parts[3]
        assert abs(vb_w - width_mm) < 0.01 and abs(vb_h - height_mm) < 0.01, (
            f"viewBox {vb!r} does not match width/height {width_mm}x{height_mm}mm -- "
            "1 unit == 1mm assumption violated, script needs updating"
        )
    return width_mm, height_mm


def load_parts(svg_text: str, sheet_name: str) -> list[Part]:
    root = ET.fromstring(svg_text)
    parts: list[Part] = []
    used_slugs: set[str] = set()
    for gi, g in enumerate(root.findall(f"{SVG_NS}g")):
        label = g.get("data-part")
        group_id = g.get("id", f"g{gi}")
        if not label:
            continue  # e.g. non-part groups, if any ever appear
        paths = g.findall(f"{SVG_NS}path")
        warnings: list[str] = []
        xs: list[float] = []
        ys: list[float] = []
        for pi, p in enumerate(paths):
            d = p.get("d")
            if not d:
                continue
            pts = parse_path_points(d, warnings, context=f"{sheet_name}/{label}/path#{pi}")
            for x, y in pts:
                xs.append(x)
                ys.append(y)
        if not xs:
            warnings.append("no points extracted from any path in this group")
            bbox = (0.0, 0.0, 0.0, 0.0)
        else:
            bbox = (min(xs), min(ys), max(xs), max(ys))
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            if w < 1.0 or h < 1.0:
                warnings.append(f"unusually small bbox {w:.3f}mm x {h:.3f}mm")
            if w > 1000 or h > 1000:
                warnings.append(f"unusually large bbox {w:.3f}mm x {h:.3f}mm")

        slug = slugify(label)
        base_slug = slug
        n = 2
        while slug in used_slugs:
            slug = f"{base_slug}-{n}"
            n += 1
        used_slugs.add(slug)

        parts.append(
            Part(
                sheet=sheet_name,
                group_id=group_id,
                label=label,
                slug=slug,
                bbox=bbox,
                n_paths=len(paths),
                suspicious=warnings,
            )
        )
    return parts


# --- rendering ---------------------------------------------------------------


def thicken_svg(svg_text: str) -> str:
    return _STROKE_WIDTH_RE.sub(f'stroke-width="{THICK_STROKE_MM}"', svg_text)


def render_full(svg_text: str, output_width: int, output_height: int) -> Image.Image:
    png_bytes = cairosvg.svg2png(
        bytestring=svg_text.encode("utf-8"),
        output_width=output_width,
        output_height=output_height,
        background_color="white",
    )
    import io

    return Image.open(io.BytesIO(png_bytes)).convert("RGB")


def render_region(svg_text: str, x: float, y: float, w: float, h: float, px_per_mm: float) -> Image.Image:
    """Re-render just the given mm region (in the sheet's own 1-unit==1mm
    coordinate space) by patching the SVG's viewBox/width/height, so the
    rasterized canvas is only as big as the crop itself (cheap even on a
    huge sheet) rather than materializing the whole sheet at high DPI."""
    patched = _VIEWBOX_RE.sub(f'viewBox="{x} {y} {w} {h}"', svg_text, count=1)
    patched = _WIDTH_ATTR_RE.sub(rf"\g<1>{w}mm\g<2>", patched, count=1)
    patched = _HEIGHT_ATTR_RE.sub(rf"\g<1>{h}mm\g<2>", patched, count=1)
    ow = max(1, round(w * px_per_mm))
    oh = max(1, round(h * px_per_mm))
    png_bytes = cairosvg.svg2png(
        bytestring=patched.encode("utf-8"),
        output_width=ow,
        output_height=oh,
        background_color="white",
    )
    import io

    return Image.open(io.BytesIO(png_bytes)).convert("RGB")


def clip_rect(x0, y0, x1, y1, width_mm, height_mm):
    return (max(0.0, x0), max(0.0, y0), min(width_mm, x1), min(height_mm, y1))


# --- main ----------------------------------------------------------------


def process_sheet(svg_path: Path, out_dir: Path, manifest: list[dict]) -> tuple[list[Part], list[str]]:
    sheet_name = svg_path.stem
    sheet_dir = out_dir / sheet_name
    sheet_dir.mkdir(parents=True, exist_ok=True)

    svg_text = svg_path.read_text()
    width_mm, height_mm = load_sheet_dims(svg_text)
    thick_svg_text = thicken_svg(svg_text)

    parts = load_parts(svg_text, sheet_name)
    all_warnings: list[str] = []

    print(f"[{sheet_name}] {width_mm:.2f}mm x {height_mm:.2f}mm, {len(parts)} parts")

    # 1. overview render (fit to ~2000px wide), true stroke
    ow = OVERVIEW_WIDTH_PX
    oh = round(height_mm * ow / width_mm)
    overview_img = render_full(svg_text, ow, oh)
    overview_path = sheet_dir / f"{sheet_name}_overview.png"
    overview_img.save(overview_path)
    manifest.append(
        {
            "file": str(overview_path.relative_to(out_dir)),
            "sheet": sheet_name,
            "part": None,
            "crop_type": "sheet_overview",
            "mm_region": [0, 0, round(width_mm, 3), round(height_mm, 3)],
            "px_size": [ow, oh],
        }
    )
    del overview_img

    # 2. high-res whole-sheet render (~20 px/mm), true stroke -- required deliverable
    hi_w = round(width_mm * HIGH_RES_PX_PER_MM)
    hi_h = round(height_mm * HIGH_RES_PX_PER_MM)
    scale_x = hi_w / width_mm
    scale_y = hi_h / height_mm
    print(f"  rendering full-sheet high-res true ({hi_w}x{hi_h}px)...")
    sheet_hi_true = render_full(svg_text, hi_w, hi_h)
    full_true_path = sheet_dir / f"{sheet_name}_full_20pxmm.png"
    sheet_hi_true.save(full_true_path)
    manifest.append(
        {
            "file": str(full_true_path.relative_to(out_dir)),
            "sheet": sheet_name,
            "part": None,
            "crop_type": "sheet_full",
            "mm_region": [0, 0, round(width_mm, 3), round(height_mm, 3)],
            "px_size": [hi_w, hi_h],
        }
    )

    # 3. high-res whole-sheet render, thickened stroke (bonus deliverable + crop source)
    print(f"  rendering full-sheet high-res thick ({hi_w}x{hi_h}px)...")
    sheet_hi_thick = render_full(thick_svg_text, hi_w, hi_h)
    full_thick_path = sheet_dir / f"{sheet_name}_full_20pxmm_thick.png"
    sheet_hi_thick.save(full_thick_path)
    manifest.append(
        {
            "file": str(full_thick_path.relative_to(out_dir)),
            "sheet": sheet_name,
            "part": None,
            "crop_type": "sheet_full_thick",
            "mm_region": [0, 0, round(width_mm, 3), round(height_mm, 3)],
            "px_size": [hi_w, hi_h],
        }
    )

    # 4/5. per-part crops (from the high-res sheet renders) + corner crops (re-rendered)
    for part in parts:
        if part.suspicious:
            all_warnings.append(f"{sheet_name}/{part.label} ({part.slug}): {'; '.join(part.suspicious)}")

        x0, y0, x1, y1 = part.bbox
        crop_mm = clip_rect(x0 - PART_MARGIN_MM, y0 - PART_MARGIN_MM, x1 + PART_MARGIN_MM, y1 + PART_MARGIN_MM, width_mm, height_mm)

        px_box = (
            round(crop_mm[0] * scale_x),
            round(crop_mm[1] * scale_y),
            round(crop_mm[2] * scale_x),
            round(crop_mm[3] * scale_y),
        )
        for suffix, src_img in (("", sheet_hi_true), ("_thick", sheet_hi_thick)):
            crop_img = src_img.crop(px_box)
            crop_path = sheet_dir / f"{part.slug}{suffix}.png"
            crop_img.save(crop_path)
            manifest.append(
                {
                    "file": str(crop_path.relative_to(out_dir)),
                    "sheet": sheet_name,
                    "part": part.label,
                    "crop_type": "part" if suffix == "" else "part_thick",
                    "mm_region": [round(c, 3) for c in crop_mm],
                    "px_size": [px_box[2] - px_box[0], px_box[3] - px_box[1]],
                }
            )

        # corners: 15x15mm window centered on each bbox corner, ~40px/mm, re-rendered
        half = CORNER_SIZE_MM / 2
        corner_points = {
            "nw": (x0, y0),
            "ne": (x1, y0),
            "sw": (x0, y1),
            "se": (x1, y1),
        }
        for corner_name, (cx, cy) in corner_points.items():
            rect = clip_rect(cx - half, cy - half, cx + half, cy + half, width_mm, height_mm)
            rw, rh = rect[2] - rect[0], rect[3] - rect[1]
            if rw <= 0 or rh <= 0:
                all_warnings.append(f"{sheet_name}/{part.label}: corner {corner_name} degenerate rect {rect}")
                continue
            for suffix, src_text in (("", svg_text), ("_thick", thick_svg_text)):
                corner_img = render_region(src_text, rect[0], rect[1], rw, rh, CORNER_PX_PER_MM)
                corner_path = sheet_dir / f"{part.slug}_corner_{corner_name}{suffix}.png"
                corner_img.save(corner_path)
                manifest.append(
                    {
                        "file": str(corner_path.relative_to(out_dir)),
                        "sheet": sheet_name,
                        "part": part.label,
                        "crop_type": f"corner_{corner_name}" if suffix == "" else f"corner_{corner_name}_thick",
                        "mm_region": [round(c, 3) for c in rect],
                        "px_size": list(corner_img.size),
                    }
                )

    del sheet_hi_true, sheet_hi_thick
    gc.collect()

    return parts, all_warnings


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sheets", nargs="+", default=None, help="sheet SVG paths (default: output/ponoko/sheet_{1,2,3}.svg)")
    ap.add_argument("--out", default=None, help="output directory (default: scratch/qa-renders)")
    args = ap.parse_args(argv)

    sheets = [Path(s) for s in args.sheets] if args.sheets else DEFAULT_SHEETS
    out_dir = Path(args.out) if args.out else DEFAULT_OUT
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest: list[dict] = []
    all_parts_by_sheet: dict[str, list[Part]] = {}
    all_warnings: list[str] = []

    for svg_path in sheets:
        if not svg_path.exists():
            print(f"!! MISSING: {svg_path}", file=sys.stderr)
            continue
        parts, warnings = process_sheet(svg_path, out_dir, manifest)
        all_parts_by_sheet[svg_path.stem] = parts
        all_warnings.extend(warnings)

    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    print("\n" + "=" * 78)
    print(f"Manifest: {manifest_path}  ({len(manifest)} PNG entries)")
    for sheet_name, parts in all_parts_by_sheet.items():
        print(f"\n{sheet_name}: {len(parts)} parts")
        for p in parts:
            flag = "  [SUSPICIOUS: " + "; ".join(p.suspicious) + "]" if p.suspicious else ""
            w = p.bbox[2] - p.bbox[0]
            h = p.bbox[3] - p.bbox[1]
            print(f"    {p.slug:35s} bbox=({p.bbox[0]:.2f},{p.bbox[1]:.2f})-({p.bbox[2]:.2f},{p.bbox[3]:.2f}) size={w:.2f}x{h:.2f}mm{flag}")

    if all_warnings:
        print(f"\n{len(all_warnings)} suspicious bbox warning(s):")
        for w in all_warnings:
            print(f"  - {w}")
    else:
        print("\nNo suspicious bboxes.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
