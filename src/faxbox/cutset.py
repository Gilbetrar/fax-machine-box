"""One complete set of cut files for one stock thickness.

Run in a process whose FAXBOX_THICKNESS is set (faxbox.config reads it at
import time):

    FAXBOX_THICKNESS=3.2 python -m faxbox.cutset OUTDIR

Writes into OUTDIR, for every bed in BEDS, `<bed>_sheet_N.svg` and
`<bed>_sheet_N.dxf`, plus `coupon.svg` / `coupon.dxf`, and `set.json`
(what is on which sheet).  The parts come from the Ponoko provider
generators (kerf compensation BURN = PONOKO_BURN, blue cut, red engrave, no
text), then are nested by rectangle packing (90 degree rotation allowed;
these files carry no artwork, so grain and engrave orientation do not
matter).  Finger holes are T + FINGER_PLAY wide for this T because the
generators are run with --thickness T; FINGER_PLAY is an absolute 0.1 mm, so
the joint play is the same at every thickness.

DXF is written by hand (R12 ASCII, closed POLYLINE per contour, layers CUT
and ENGRAVE, units mm) so the repo needs no extra dependency.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import quoteattr

import numpy as np
from shapely.geometry import LineString, Polygon, box as sbox
from svgpathtools import Path as SPath, parse_path

from faxbox import config as c
from faxbox.layout import HAIRLINE_STROKE_WIDTH_MM, Piece, SourcePath, _load_pieces, _round_numbers

T = c.T
BURN = c.PONOKO_BURN

# name -> (width, height, margin, spacing) in mm
BEDS = {
    "ponoko": (c.PONOKO_SHEET_WIDTH, c.PONOKO_SHEET_HEIGHT, 10.0, 5.0),
    "xtool_s1": (498.0, 319.0, 5.0, 3.5),
    "xtool_p2": (600.0, 305.0, 5.0, 3.5),
    "glowforge_pro": (495.0, 279.0, 5.0, 3.5),
    "generic_600x400": (600.0, 400.0, 5.0, 3.5),
    "coupon": (215.0, 150.0, 5.0, 3.5),
}
HOBBY_AND_SERVICE_BEDS = ("ponoko", "xtool_s1", "xtool_p2", "glowforge_pro", "generic_600x400")

CUT = "rgb(0,0,255)"
ENGRAVE = "rgb(255,0,0)"

SHELL_NAMES = [("A", "Bottom panel"), ("B", "Right wall"), ("C", "Left wall"), ("D", "Front wall"),
               ("E", "Rear wall"), ("F", "Divider"), ("G", "Shelf"), ("H", "Top panel")]
DRAWER_NAMES = [("K", "Drawer front"), ("L", "Drawer back"), ("M", "Drawer left side"),
                ("N", "Drawer right side"), ("O", "Drawer bottom"), ("P", "Drawer faceplate")]


@dataclass
class Item:
    letter: str
    name: str
    piece: Piece


def generate_items(workdir: Path) -> list[Item]:
    """Every laser-cut part of one box (22 pieces), Ponoko provider."""
    from faxbox import generate_drawers, generate_hardware, generate_lids, shell_generator
    cwd = os.getcwd()
    os.chdir(workdir)
    try:
        shell = shell_generator.generate_shell(provider="ponoko")
        drawer = generate_drawers.generate_drawer(provider="ponoko")
        lid = generate_lids.generate_lids(provider="ponoko")
        btn = generate_hardware.generate_hardware(provider="ponoko")
        files = [Path(workdir) / p for p in (shell, drawer, lid, btn)]
    finally:
        os.chdir(cwd)
    items: list[Item] = []
    for (letter, name), p in zip(SHELL_NAMES, _load_pieces(files[0], "Shell", strip_labels=True)):
        items.append(Item(letter, name, p))
    for tag in ("lower", "upper"):
        for (letter, name), p in zip(DRAWER_NAMES, _load_pieces(files[1], "Drawer", strip_labels=True)):
            items.append(Item(letter, f"{name} ({tag})", p))
    items.append(Item("I", "Sliding lid", _load_pieces(files[2], "Lid", strip_labels=True)[0]))
    items.append(Item("J", "Turn button", _load_pieces(files[3], "Button", strip_labels=True)[0]))
    return items


# --- test-fit coupon ----------------------------------------------------------------------

def _poly_d(poly: Polygon) -> list[str]:
    out = []
    for ring in [poly.exterior] + list(poly.interiors):
        pts = list(ring.coords)
        out.append("M " + " L ".join(f"{x:.4f},{y:.4f}" for x, y in pts[:-1]) + " Z")
    return out


def _circle(cx, cy, d, n=96):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return Polygon(np.column_stack([cx + d / 2 * np.cos(a), cy + d / 2 * np.sin(a)]))


def _piece_from(polys_cut=(), lines_engrave=(), holes_as_paths=()) -> Piece:
    """Piece from burn-compensated drawn geometry (shapely, y down)."""
    paths = []
    allx, ally = [], []
    for g in polys_cut:
        for d in _poly_d(g):
            paths.append(SourcePath({"stroke": CUT, "fill": "none"}, d))
        allx += [g.bounds[0], g.bounds[2]]
        ally += [g.bounds[1], g.bounds[3]]
    for (x0, y0, x1, y1) in lines_engrave:
        paths.append(SourcePath({"stroke": ENGRAVE, "fill": "none"}, f"M {x0:.4f},{y0:.4f} L {x1:.4f},{y1:.4f}"))
        allx += [x0, x1]
        ally += [y0, y1]
    xmin, ymin = min(allx), min(ally)
    return Piece(source="Coupon", label="coupon", width=max(allx) - xmin, height=max(ally) - ymin,
                 xmin=xmin, ymin=ymin, group_style="", svg_paths=paths)


def coupon_items(workdir: Path) -> list[Item]:
    """Calibration / test-fit coupon, burn-compensated like the real parts:
    1  panel with kerf square, thickness gauge slots 2.8-3.5, magnet holes
    2  three-finger corner (finger piece + hole-row piece, as the walls)
    3  lid-in-slot strip (slot block + a lid strip)"""
    from boxes import Boxes, edges
    items: list[Item] = []
    b = BURN

    # 1. gauge panel -------------------------------------------------------------------
    widths = [round(2.8 + 0.1 * i, 1) for i in range(8)]
    mags = (5.5, 5.65, 5.8, 5.95)
    pw, ph = 118.0, 62.0
    material = sbox(0, 0, pw, ph)
    cut_holes = []
    ticks = []
    # kerf square: drawn at exactly 10 mm (no compensation) -> measures kerf
    cut_holes.append(sbox(8, 8, 18, 18))
    x = 26.0
    for i, w in enumerate(widths):
        # slot: physical width w  ->  drawn path inset by burn per side
        cut_holes.append(sbox(x + b, 8 + b, x + w - b, 8 + 14 - b))
        for k in range(i + 1):               # i+1 engraved ticks = nth gauge (2.8 = 1)
            ticks.append((x + w / 2 - 2.0, 25.5 + 1.4 * k, x + w / 2 + 2.0, 25.5 + 1.4 * k))
        x += w + 2.2
    gx = 10.0
    for d in mags:
        cut_holes.append(_circle(gx + d / 2, 46, d - 2 * b))
        gx += d + 6.0
    panel = material.buffer(b, join_style=2)
    for h in cut_holes:
        panel = panel.difference(h)
    items.append(Item("Q", "Coupon: kerf square, thickness slots 2.8-3.5 (1-8 ticks), magnet holes 5.5-5.95",
                      _piece_from([panel], ticks)))

    # 2. three-finger corner --------------------------------------------------------------
    # finger count is chosen by Boxes from the edge length; find the length giving 3.
    class Joint(Boxes):
        def __init__(self):
            Boxes.__init__(self)
            self.addSettingsArgs(edges.FingerJointSettings)

    def render(draw):
        j = Joint()
        out = str(Path(workdir) / "joint.svg")
        j.parseArgs(["--output", out, "--thickness", str(T), "--burn", str(b), "--reference", "0",
                     "--FingerJoint_play", str(c.FINGER_PLAY_RELATIVE)])
        j.open()
        j.set_source_color(c.PONOKO_CUT_COLOR)
        draw(j)
        data = j.close()
        Path(out).write_bytes(data.getvalue())
        return _load_pieces(Path(out), "Coupon", strip_labels=True)[0]

    length = 14.3 * T               # Boxes: (length - 2T) // 4T = 3 fingers
    fingers = render(lambda j: j.rectangularWall(length, 28, "feee", move="right"))
    holes = render(lambda j: j.rectangularWall(
        length, 28, "eeee", callback=[lambda: j.fingerHolesAt(0, T / 2, length, angle=0), None, None, None],
        move="right"))
    items.append(Item("R", "Coupon: three-finger corner, finger piece", fingers))
    items.append(Item("R", "Coupon: three-finger corner, hole piece", holes))

    # 3. lid in slot --------------------------------------------------------------------------
    slot_h = c.LID_SLOT_HEIGHT
    rail = c.LID_RAIL_HEIGHT
    block = sbox(0, 0, 70, 10 + slot_h + rail)
    block = block.difference(sbox(-1, 10, 45, 10 + slot_h))      # open-mouthed slot, 45 deep
    block_drawn = block.buffer(b, join_style=2)
    strip = sbox(0, 0, 60, 14).buffer(b, join_style=2)
    items.append(Item("S", "Coupon: lid slot block (slot T + clearance)", _piece_from([block_drawn])))
    items.append(Item("S", "Coupon: lid strip", _piece_from([strip])))
    return items


# --- nesting ---------------------------------------------------------------------------------------

def _maxrects(sizes, bw, bh, spacing):
    """MaxRects best-short-side-fit with rotation.  sizes: list of (w, h).
    Returns (placements [(index, x, y, rotated)] or None if something does
    not fit)."""
    free = [(0.0, 0.0, bw + spacing, bh + spacing)]
    out = []
    for i, (w, h) in sizes:
        w2, h2 = w + spacing, h + spacing
        best = None
        for fx, fy, fw, fh in free:
            for rot, (pw, ph) in ((False, (w2, h2)), (True, (h2, w2))):
                if pw <= fw + 1e-9 and ph <= fh + 1e-9:
                    score = (min(fw - pw, fh - ph), max(fw - pw, fh - ph))
                    if best is None or score < best[0]:
                        best = (score, fx, fy, pw, ph, rot)
        if best is None:
            return None
        _, x, y, pw, ph, rot = best
        out.append((i, x, y, rot))
        new = []
        for fx, fy, fw, fh in free:
            if x >= fx + fw or x + pw <= fx or y >= fy + fh or y + ph <= fy:
                new.append((fx, fy, fw, fh))
                continue
            if x > fx:
                new.append((fx, fy, x - fx, fh))
            if x + pw < fx + fw:
                new.append((x + pw, fy, fx + fw - x - pw, fh))
            if y > fy:
                new.append((fx, fy, fw, y - fy))
            if y + ph < fy + fh:
                new.append((fx, y + ph, fw, fy + fh - y - ph))
        free = [r for r in new if not any(
            o is not r and o[0] <= r[0] + 1e-9 and o[1] <= r[1] + 1e-9
            and o[0] + o[2] >= r[0] + r[2] - 1e-9 and o[1] + o[3] >= r[1] + r[3] - 1e-9 for o in new)]
    return out


def nest(items: list[Item], bed: str):
    """Pack items on as few sheets as possible.  Returns a list of sheets,
    each a list of (item, x, y, rotated) with x, y the top-left of the
    placed bounding box in sheet coordinates."""
    bw, bh, margin, spacing = BEDS[bed]
    uw, uh = bw - 2 * margin, bh - 2 * margin
    sizes = [(i, (it.piece.width, it.piece.height)) for i, it in enumerate(items)]
    for _, (w, h) in sizes:
        if not ((w <= uw and h <= uh) or (h <= uw and w <= uh)):
            raise ValueError(f"part {w:.1f}x{h:.1f} does not fit bed {bed}")
    orders = [
        sorted(sizes, key=lambda s: -s[1][0] * s[1][1]),
        sorted(sizes, key=lambda s: -max(s[1])),
        sorted(sizes, key=lambda s: -s[1][1]),
        sorted(sizes, key=lambda s: -s[1][0]),
    ]
    best = None
    for order in orders:
        remaining = list(order)
        sheets = []
        while remaining:
            placed_sheet = []
            left = []
            # greedy fill one sheet: try adding parts in order, keep those that fit
            trial = []
            for s in remaining:
                cand = trial + [s]
                if _maxrects(cand, uw, uh, spacing) is not None:
                    trial = cand
                else:
                    left.append(s)
            res = _maxrects(trial, uw, uh, spacing)
            for i, x, y, rot in res:
                placed_sheet.append((items[i], x + margin, y + margin, rot))
            sheets.append(placed_sheet)
            remaining = left
        key = (len(sheets), sum(max(p[1] + (p[0].piece.height if p[3] else p[0].piece.width) for p in sh) for sh in sheets))
        if best is None or key < best[0]:
            best = (key, sheets)
    return best[1]


# --- writers ------------------------------------------------------------------------------------------

def _placed_paths(item: Item, x: float, y: float, rot: bool):
    """(stroke, SPath) of the item translated so its bbox top-left is (x, y);
    rotated 90 degrees first when rot."""
    pc = item.piece
    out = []
    for sp in pc.svg_paths:
        path = parse_path(sp.d)
        path = path.translated(complex(-pc.xmin, -pc.ymin))
        if rot:
            path = path.rotated(90, origin=0j)
            path = path.translated(complex(pc.height, 0))
        path = path.translated(complex(x, y))
        out.append((sp.attrib.get("stroke", CUT), path))
    return out


def _sample(path: SPath):
    pts = []
    for seg in path:
        n = 1 if seg.__class__.__name__ == "Line" else max(2, int(abs(seg.length()) / 0.15) + 1)
        for t in np.linspace(0, 1, n, endpoint=False):
            z = seg.point(t)
            pts.append((z.real, z.imag))
    z = path[-1].point(1.0)
    closed = abs(path[-1].end - path[0].start) < 1e-6
    if not closed:
        pts.append((z.real, z.imag))
    return pts, closed


def write_sheet(sheet, bed: str, n: int, total: int, out_svg: Path, out_dxf: Path, title: str):
    bw, bh, margin, spacing = BEDS[bed]
    w = max(x + (it.piece.height if rot else it.piece.width) for it, x, y, rot in sheet) + margin
    h = max(y + (it.piece.width if rot else it.piece.height) for it, x, y, rot in sheet) + margin
    groups, dxf_items = [], []
    for k, (it, x, y, rot) in enumerate(sheet):
        lines = [f'<g id="s{n}p{k}" data-part={quoteattr(it.letter + " " + it.name)}>']
        for stroke, path in _placed_paths(it, x, y, rot):
            lines.append(f'<path d={quoteattr(_round_numbers(path.d(), 3))} fill="none" stroke="{stroke}" stroke-width="{HAIRLINE_STROKE_WIDTH_MM}" />')
            dxf_items.append((stroke, *_sample(path)))
        lines.append("</g>")
        groups.append("\n".join(lines))
    svg = f"""<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{w:.2f}mm" height="{h:.2f}mm" viewBox="0 0 {w:.2f} {h:.2f}">
<!--
Fax Machine Box, plywood {T:.2f} mm. {title}: sheet {n} of {total}, bed {bed} ({bw:.0f} x {bh:.0f} mm).
Blue (#0000FF) = cut, red (#FF0000) = engrave. Kerf compensation {BURN:.2f} mm per side, finger holes
{T:.2f} + {c.FINGER_PLAY:.2f} mm. Margin {margin:.0f} mm, {spacing:.1f} mm between parts. No text.
-->
<title>{title} sheet {n} of {total} ({bed}, {T:.2f} mm)</title>
{chr(10).join(groups)}
</svg>
"""
    out_svg.write_text(svg)
    out_dxf.write_text(dxf_text(dxf_items, h))


def dxf_text(items, height: float) -> str:
    """R12 ASCII DXF.  items: (stroke, points, closed) in SVG coordinates
    (y down); y is flipped so the drawing is upright."""
    L = ["0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1009", "9", "$INSUNITS", "70", "4",
         "0", "ENDSEC",
         "0", "SECTION", "2", "TABLES", "0", "TABLE", "2", "LAYER", "70", "2",
         "0", "LAYER", "2", "CUT", "70", "0", "62", "5", "6", "CONTINUOUS",
         "0", "LAYER", "2", "ENGRAVE", "70", "0", "62", "1", "6", "CONTINUOUS",
         "0", "ENDTAB", "0", "ENDSEC",
         "0", "SECTION", "2", "ENTITIES"]
    for stroke, pts, closed in items:
        layer = "ENGRAVE" if stroke == ENGRAVE else "CUT"
        L += ["0", "POLYLINE", "8", layer, "66", "1", "70", "1" if closed else "0"]
        for x, y in pts:
            L += ["0", "VERTEX", "8", layer, "10", f"{x:.4f}", "20", f"{height - y:.4f}", "30", "0.0"]
        L += ["0", "SEQEND", "8", layer]
    L += ["0", "ENDSEC", "0", "EOF"]
    return "\n".join(L) + "\n"


def build_set(out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        items = generate_items(td)
        coupon = coupon_items(td)
    assert len(items) == 22, len(items)
    info = {"thickness": T, "beds": {}, "files": []}
    for bed in HOBBY_AND_SERVICE_BEDS:
        sheets = nest(items, bed)
        info["beds"][bed] = {"sheets": len(sheets), "parts": [[f"{it.letter} {it.name}" for it, *_ in s] for s in sheets]}
        for n, s in enumerate(sheets, 1):
            svg, dxf = out / f"{bed}_sheet_{n}.svg", out / f"{bed}_sheet_{n}.dxf"
            write_sheet(s, bed, n, len(sheets), svg, dxf, "Fax Machine Box")
            info["files"] += [svg.name, dxf.name]
    # coupon on its own small sheet
    csheets = nest(coupon, "coupon")
    assert len(csheets) == 1
    write_sheet(csheets[0], "coupon", 1, 1, out / "coupon.svg", out / "coupon.dxf", "Test-fit coupon")
    info["files"] += ["coupon.svg", "coupon.dxf"]
    info["coupon_parts"] = [f"{it.letter} {it.name}" for it, *_ in csheets[0]]
    (out / "set.json").write_text(json.dumps(info, indent=1) + "\n")
    return info


if __name__ == "__main__":
    build_set(Path(sys.argv[1]))
    print(f"cut set for T={T} written to {sys.argv[1]}")
