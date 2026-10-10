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
import math
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
from faxbox import engrave as eg
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
# cut-set letter -> engraving-art face id (art/code/manifest.json)
SHELL_FACES = {"B": "right", "C": "left", "D": "front", "H": "top"}
DRAWER_FACES = {"M": "left", "N": "right", "P": "face"}      # prefixed B_ (lower) / T_ (upper)
DRAWER_NAMES = [("K", "Drawer front"), ("L", "Drawer back"), ("M", "Drawer left side"),
                ("N", "Drawer right side"), ("O", "Drawer bottom"), ("P", "Drawer faceplate")]


@dataclass
class Item:
    letter: str
    name: str
    piece: Piece
    face: str | None = None      # engraving-art face id (art/code/manifest.json), None = plain part
    src: str | None = None       # partgeom id that supplies the outline


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
    from faxbox.assembly3d import source_part
    items: list[Item] = []
    for (letter, name), p in zip(SHELL_NAMES, _load_pieces(files[0], "Shell", strip_labels=True)):
        face = SHELL_FACES.get(letter)
        items.append(Item(letter, name, p, face, source_part(face) if face else None))
    for tag in ("lower", "upper"):
        for (letter, name), p in zip(DRAWER_NAMES, _load_pieces(files[1], "Drawer", strip_labels=True)):
            suffix = DRAWER_FACES.get(letter)
            face = f"{'B' if tag == 'lower' else 'T'}_{suffix}" if suffix else None
            items.append(Item(letter, f"{name} ({tag})", p, face, source_part(face) if face else None))
    items.append(Item("I", "Sliding lid", _load_pieces(files[2], "Lid", strip_labels=True)[0], "lid", "lid"))
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

def _maxrects(sizes, bw, bh, spacing, norot=frozenset()):
    """MaxRects best-short-side-fit with rotation (except for the indices in
    `norot`, which keep their orientation).  sizes: list of (index, (w, h)).
    Returns placements [(index, x, y, rotated)] or None if something does
    not fit."""
    free = [(0.0, 0.0, bw + spacing, bh + spacing)]
    out = []
    for i, (w, h) in sizes:
        w2, h2 = w + spacing, h + spacing
        best = None
        for fx, fy, fw, fh in free:
            for rot, (pw, ph) in ((False, (w2, h2)), (True, (h2, w2))):
                if rot and i in norot:
                    continue
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
    # parts that carry engraving stay upright on the sheet so the art reads
    norot = frozenset(i for i, it in enumerate(items) if it.face)
    for i, (w, h) in sizes:
        if not ((w <= uw and h <= uh) or (i not in norot and h <= uw and w <= uh)):
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
                if _maxrects(cand, uw, uh, spacing, norot) is not None:
                    trial = cand
                else:
                    left.append(s)
            res = _maxrects(trial, uw, uh, spacing, norot)
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


# --- cut + engrave -------------------------------------------------------------------------------

ENGRAVE_FILL = "#000000"
CLEARANCE_MIN = 0.35        # mm, engrave to nearest cut (asserted per part)
BEDS["face"] = (0.0, 0.0, 10.0, 5.0)        # single-part files; only the margin is used


def default_variants() -> dict[str, str]:
    return {f: eg.default_variant(f) for f in eg.faces()}


_BED_CACHE: dict = {}
KEEPOUT = 0.40          # mm; art closer than CLEARANCE_MIN to a cut is trimmed back to this


def cut_geometry(cuts):
    """(material polygon, all cut lines) from cut subpaths."""
    from shapely.ops import unary_union
    flat = eg.flatten(cuts, 0.005)
    lines = [LineString(p + ([p[0]] if closed else [])) for p, closed in flat if len(p) > 1]
    rings = sorted((Polygon(p).buffer(0) for p, closed in flat if closed and len(p) > 2), key=lambda r: -r.area)
    material = rings[0]
    for h in rings[1:]:
        material = material.difference(h)
    return material, unary_union(lines)


def _keep_clear(cuts, fills):
    """Art subpaths -> art subpaths with every ink component that comes
    closer than CLEARANCE_MIN to a cut line (or leaves the material) trimmed
    back to KEEPOUT.  The art is drawn for one stock thickness; at other
    thicknesses finger slots and the lid slot move by a fraction of a mm, so
    the trim is only ever a sliver and most sets need none."""
    from shapely.prepared import prep
    material, cut_geom = cut_geometry(cuts)
    flat = [eg.flatten([sp], 0.005)[0] for sp in fills]
    rings = [Polygon(pts).buffer(0) for pts, _ in flat]
    comps = eg.ink_components(rings)
    keepout = cut_geom.buffer(KEEPOUT)
    pm, pc = prep(material), prep(cut_geom.buffer(CLEARANCE_MIN + 0.02))
    kept, trimmed, n_trim = [], [], 0
    for poly, idx in comps:
        if pm.contains(poly) and not pc.intersects(poly):
            kept.extend(fills[i] for i in idx)
        else:
            n_trim += 1
            trimmed.extend(eg.polygon_subpaths(poly.intersection(material).difference(keepout).simplify(0.01)))
    return kept + trimmed, n_trim


def bed_subpaths(item: Item, variant: str | None = None):
    """The part as it lies on the bed (exterior face up), in the piece's own
    SVG coordinates (y down, kerf-compensated cuts).

    Returns (cut_subpaths, engrave) with engrave a list of (kind, subpaths),
    kind 'fill' or 'stroke'.  For parts whose drawn outline shows the interior
    face, the cut outline is mirrored (see faxbox.engrave) and the art is not.
    The generator's own red engrave lines (faceplate glue-up outline) are
    kept only on parts without art: they mark the inside face, and a part
    lies on the bed with one face up."""
    key = (item.letter, item.name, variant)
    if key in _BED_CACHE:
        return _BED_CACHE[key]
    pc = item.piece
    flip = eg.bed_flip(pc, item.face)
    cuts, red = [], []
    for sp in pc.svg_paths:
        subs = eg.transform_subpaths(eg.parse_subpaths(sp.d), flip)
        (red if sp.attrib.get("stroke") == ENGRAVE else cuts).extend(subs)
    engrave = []
    if item.face and variant:
        m = eg.art_to_piece_svg(pc, item.face, item.src, BURN)
        fills = []
        for ap in eg.load_art(item.face, variant):
            placed = eg.transform_subpaths(ap.subs, m)
            if ap.kind == "fill":
                fills.extend(placed)
            else:
                engrave.append(("stroke", placed))
        if fills:
            fills, _ = _keep_clear(cuts, fills)
            engrave.insert(0, ("fill", fills))
    elif red:
        engrave.extend(("stroke", [sp]) for sp in red)
    _BED_CACHE[key] = (cuts, engrave)
    return cuts, engrave


def clearance(item: Item, variant: str) -> dict:
    """Engrave-to-cut geometry of the part as exported: minimum distance from
    any inked area (or engraved line) to any cut line, how much ink lies
    outside the part's material, and ink area."""
    from shapely.ops import unary_union
    cuts, engrave = bed_subpaths(item, variant)
    material, cut_geom = cut_geometry(cuts)
    polys, lines = [], []
    for kind, subs in engrave:
        flat = eg.flatten(subs, 0.005)
        if kind == "fill":
            rings = [Polygon(pts).buffer(0) for pts, _ in flat if len(pts) > 2]
            polys += [p for p, _ in eg.ink_components(rings)]
        else:
            lines += [LineString(pts) for pts, _ in flat if len(pts) > 1]
    ink = unary_union(polys + lines)
    return {
        "min_distance": float(cut_geom.distance(ink)) if not ink.is_empty else math.inf,
        "outside_material": float(ink.difference(material).area),
        "ink_area": float(unary_union(polys).area) if polys else 0.0,
        "material": material, "ink": ink, "cuts": cut_geom,
    }


def _check_clearance(item: Item, variant: str) -> float:
    r = clearance(item, variant)
    assert r["outside_material"] < 1e-4, (item.name, variant, r["outside_material"])
    assert r["min_distance"] >= CLEARANCE_MIN, (item.name, variant, r["min_distance"])
    return r["min_distance"]


def _sheet_affine(it: Item, x: float, y: float, rot: bool) -> eg.Affine:
    """Piece SVG coordinates -> sheet coordinates (same as _placed_paths)."""
    pc = it.piece
    m = (1.0, 0.0, 0.0, 1.0, -pc.xmin, -pc.ymin)
    if rot:
        m = eg.compose((0.0, 1.0, -1.0, 0.0, pc.height, 0.0), m)
    return eg.compose((1.0, 0.0, 0.0, 1.0, x, y), m)


def write_engrave_sheet(sheet, bed: str, n: int, total: int, out_svg: Path, out_dxf: Path, title: str,
                        variants: dict[str, str]):
    """Like write_sheet, with the engraving art (variant per face from
    `variants`) and the flipped parts mirrored so they lie exterior face up."""
    bw, bh, margin, spacing = BEDS[bed]
    w = max(x + (it.piece.height if rot else it.piece.width) for it, x, y, rot in sheet) + margin
    h = max(y + (it.piece.width if rot else it.piece.height) for it, x, y, rot in sheet) + margin
    groups, dxf_items = [], []
    for k, (it, x, y, rot) in enumerate(sheet):
        var = variants.get(it.face) if it.face else None
        m = _sheet_affine(it, x, y, rot)
        cuts, engrave = bed_subpaths(it, var)
        attrs = f'id="s{n}p{k}" data-part={quoteattr(it.letter + " " + it.name)}'
        if var:
            attrs += f' data-engrave={quoteattr(it.face + "/" + var)}'
        if it.face and eg.is_flipped(it.face):
            attrs += ' data-mirrored="outline mirrored so the outside face is up"'
        lines = [f"<g {attrs}>"]
        for sp in cuts:
            placed = eg.transform_subpaths([sp], m)
            lines.append(f'<path d={quoteattr(eg.emit(placed))} fill="none" stroke="{CUT}" '
                         f'stroke-width="{HAIRLINE_STROKE_WIDTH_MM}" />')
            dxf_items += [(CUT, pts, closed) for pts, closed in eg.flatten(placed, 0.005)]
        fills, strokes = [], []
        for kind, subs in engrave:
            (fills if kind == "fill" else strokes).extend(eg.transform_subpaths(subs, m))
        if fills:
            lines.append(f'<path d={quoteattr(eg.emit(fills))} fill="{ENGRAVE_FILL}" fill-rule="evenodd" />')
            dxf_items += [(ENGRAVE, pts, True) for pts, closed in eg.flatten_simplified(fills, 0.03)]
        for sub in strokes:
            lines.append(f'<path d={quoteattr(eg.emit([sub]))} fill="none" stroke="{ENGRAVE}" '
                         f'stroke-width="{HAIRLINE_STROKE_WIDTH_MM}" />')
            dxf_items += [(ENGRAVE, pts, closed) for pts, closed in eg.flatten_simplified([sub], 0.03)]
        lines.append("</g>")
        groups.append("\n".join(lines))
    label = f"bed {bed} ({bw:.0f} x {bh:.0f} mm)" if bed != "face" else "single part"
    svg = f"""<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{w:.2f}mm" height="{h:.2f}mm" viewBox="0 0 {w:.2f} {h:.2f}">
<!--
Fax Machine Box, plywood {T:.2f} mm. {title}: sheet {n} of {total}, {label}.
Blue hairline (#0000FF) = cut, filled black (#000000) = area engrave, red hairline (#FF0000) = line engrave.
Lay every part on the bed with the face that will be the OUTSIDE of the box facing up. Parts whose drawn
face would be the inside are already mirrored here (data-mirrored); the art is not mirrored.
Kerf compensation {BURN:.2f} mm per side on cuts only; engraving is not offset.
Finger holes {T:.2f} + {c.FINGER_PLAY:.2f} mm. Margin {margin:.0f} mm, {spacing:.1f} mm between parts. No text.
-->
<title>{title} sheet {n} of {total} ({bed}, {T:.2f} mm)</title>
{chr(10).join(groups)}
</svg>
"""
    out_svg.write_text(svg)
    out_dxf.write_text(dxf_text(dxf_items, h))


README_ENGRAVE = """Fax Machine Box, cut + engrave files, plywood {T:.2f} mm

Colours
  blue hairline   #0000FF   cut through
  filled black    #000000   area engrave (raster / fill)
  red hairline    #FF0000   line engrave (none in the current art)

Orientation
  Lay every part on the bed with the face that becomes the OUTSIDE of the box facing up.
  Parts whose outline in the cut-only files shows the inside face (top panel, sliding lid,
  both drawer faceplates, both left drawer sides) are mirrored in these files so the outside
  face is up. The art is not mirrored. Do not flip any part in the laser software.
  The mirrored parts are the same physical parts turned over, so the finger joints mate as usual.

DXF
  Layers CUT and ENGRAVE, millimetres. Engraved art is closed polylines on ENGRAVE, so set
  that layer to fill / raster in the laser software. A DXF has no fill attribute.

Offsets
  Only cuts carry the kerf offset ({burn:.2f} mm per side). Engraving is not offset.
  Engraving stays at least {clear:.2f} mm away from every cut.

Drawer faceplates
  The glue-up outline that the cut-only files engrave on the inside of each faceplate is left
  out here, because the faceplate lies outside-up with its art. Use the cut-only faceplate
  files if you want that outline.

Alternate art
  faces/<face>__<variant>.svg|dxf holds one part with one art variant, same conventions.
"""


def build_set(out: Path) -> dict:
    """Write one thickness set into `out`:

    <bed>_sheet_N.svg|dxf            cut only (blue)
    <bed>_sheet_N_engrave.svg|dxf    cut + engrave: same layout, parts that
                                     carry art lie exterior face up (mirrored
                                     outlines), default art variants
    faces/<face>__<variant>.svg|dxf  one part with one art variant, for every
                                     variant (to swap in an alternate)
    coupon.svg|dxf, set.json
    """
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        items = generate_items(td)
        coupon = coupon_items(td)
    assert len(items) == 22, len(items)
    variants = default_variants()
    info = {"thickness": T, "beds": {}, "files": [], "engrave_files": [], "face_files": []}
    for bed in HOBBY_AND_SERVICE_BEDS:
        sheets = nest(items, bed)
        info["beds"][bed] = {"sheets": len(sheets), "parts": [[f"{it.letter} {it.name}" for it, *_ in s] for s in sheets]}
        for n, s in enumerate(sheets, 1):
            svg, dxf = out / f"{bed}_sheet_{n}.svg", out / f"{bed}_sheet_{n}.dxf"
            write_sheet(s, bed, n, len(sheets), svg, dxf, "Fax Machine Box")
            info["files"] += [svg.name, dxf.name]
            esvg, edxf = out / f"{bed}_sheet_{n}_engrave.svg", out / f"{bed}_sheet_{n}_engrave.dxf"
            write_engrave_sheet(s, bed, n, len(sheets), esvg, edxf, "Fax Machine Box, cut + engrave", variants)
            info["engrave_files"] += [esvg.name, edxf.name]
    # coupon on its own small sheet
    csheets = nest(coupon, "coupon")
    assert len(csheets) == 1
    write_sheet(csheets[0], "coupon", 1, 1, out / "coupon.svg", out / "coupon.dxf", "Test-fit coupon")
    info["files"] += ["coupon.svg", "coupon.dxf"]
    info["coupon_parts"] = [f"{it.letter} {it.name}" for it, *_ in csheets[0]]
    # one file per art variant (the part, mirrored if needed, with that art)
    (out / "faces").mkdir(exist_ok=True)
    margin = BEDS["face"][2]
    clear = {}
    for it in items:
        if not it.face:
            continue
        for v in eg.variants(it.face):
            tag = f"{it.face}__{v['id']}"
            clear[f"{it.face}/{v['id']}"] = round(_check_clearance(it, v["id"]), 3)
            svg, dxf = out / "faces" / f"{tag}.svg", out / "faces" / f"{tag}.dxf"
            write_engrave_sheet([(it, margin, margin, False)], "face", 1, 1, svg, dxf,
                                f"{it.name}, {v['label']}", {it.face: v["id"]})
            info["face_files"] += [f"faces/{svg.name}", f"faces/{dxf.name}"]
    info["engrave"] = {"default_variants": variants, "min_clearance_mm": clear,
                       "clearance_required_mm": CLEARANCE_MIN}
    (out / "README_engrave.txt").write_text(README_ENGRAVE.format(T=T, burn=BURN, clear=CLEARANCE_MIN))
    info["engrave_files"].append("README_engrave.txt")
    (out / "set.json").write_text(json.dumps(info, indent=1) + "\n")
    return info


if __name__ == "__main__":
    build_set(Path(sys.argv[1]))
    print(f"cut set for T={T} written to {sys.argv[1]}")
