"""One complete set of cut files for one stock thickness and one laser kerf.

Run in a process whose FAXBOX_THICKNESS is set (faxbox.config reads it at
import time):

    FAXBOX_THICKNESS=3.2 python -m faxbox.cutset OUTDIR [KERF ...]

`build_set(out, kerf)` writes into OUT, for every bed in BEDS:

  <bed>_sheet_N.svg|dxf            CUT ONLY: blue cut lines and nothing else, so
                                   a service that cuts every line cuts exactly
                                   the parts
  labels/<bed>_sheet_N.svg|dxf     CUT + LABELS (for your own laser): parts lie
                                   inside face up; gray part labels (layer
                                   LABELS) and the faceplate glue-up lines (red)
  <bed>_sheet_N_engrave.svg|dxf    CUT + ENGRAVE: parts lie outside face up with
                                   the art (default variants)
  coupon.svg|dxf, coupon_marked.svg|dxf   test-fit coupon (see COUPON_GUIDE)
  set.json                         what is on which sheet, and the guides

`build_parts(out)` writes zero-kerf single-part files (service applies kerf), and
faces/<face>__<variant>.svg|dxf: one art-bearing part with one art variant, every
variant (15), outside face up.

The parts come from the Ponoko provider generators with the kerf passed as
Boxes.py's per-side compensation (BURN = kerf / 2), then are nested by
rectangle packing (90 degree rotation allowed, except for parts that carry art,
which stay upright so the art reads on the sheet).  Finger holes are
T + FINGER_PLAY wide; FINGER_PLAY is an absolute 0.1 mm, so the joint play is
the same at every thickness AS LONG AS the compensation matches the laser's
real kerf.  That is why there is one file set per kerf: the along-the-finger
fit changes by 2 x (2 x BURN - kerf) when it does not, and no thickness file
can fix that.

Engraving (cut + engrave): parts whose drawn outline shows the INTERIOR face
are mirrored so every part lies on the bed with its OUTSIDE face up; the art is
drawn unmirrored.  Colours: cut = blue #0000FF hairline, area engrave = filled
black #000000, line engrave = red #FF0000 hairline, labels = gray #808080.
Only cuts are kerf-offset.  Engraving keeps at least CLEARANCE_MIN from every
cut (art is trimmed back where a thickness moves a slot under it).

DXF is written by hand (R2000 ASCII, units millimetres via $INSUNITS = 4, one
LWPOLYLINE per contour, layers CUT, ENGRAVE and LABELS) so the repo needs no
extra dependency.  Filled art is closed polylines on ENGRAVE, so the laser
software must be set to fill / raster that layer.
"""

from __future__ import annotations

import json
import math
import os
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import quoteattr

import numpy as np
from shapely.geometry import LineString, Polygon, box as sbox

from faxbox import config as c
from faxbox import engrave as eg
from faxbox import labels as lb
from faxbox.layout import HAIRLINE_STROKE_WIDTH_MM, Piece, SourcePath, _load_pieces

T = c.T
BURN = c.PONOKO_BURN            # default compensation (Ponoko 0.20 mm kerf), kept for callers
DEFAULT_KERF = c.PONOKO_KERF

# Laser kerf variants (total width of the cut).  One file set each.
KERFS = {"diode": 0.12, "co2": 0.18, "ponoko": 0.20}
KERF_LABELS = {
    "diode": "Diode laser (about 0.12 mm kerf)",
    "co2": "CO2 laser (about 0.18 mm kerf)",
    "ponoko": "Ponoko and other services (0.20 mm kerf)",
}

# name -> (width, height, margin, spacing) in mm
BEDS = {
    "ponoko": (c.PONOKO_SHEET_WIDTH, c.PONOKO_SHEET_HEIGHT, 10.0, 5.0),
    "xtool_s1": (498.0, 301.6, 5.0, 3.5),
    "xtool_p2": (594.9, 301.6, 5.0, 3.5),
    "glowforge_pro": (495.0, 279.0, 5.0, 3.5),
    "generic_600x400": (600.0, 400.0, 5.0, 3.5),
    "nycr_32x20": (812.8, 508.0, 5.0, 3.5),
    "coupon": (190.0, 125.0, 5.0, 3.5),
    "face": (0.0, 0.0, 10.0, 5.0),            # single-part files; only the margin is used
}
HOBBY_AND_SERVICE_BEDS = ("ponoko", "xtool_s1", "xtool_p2", "glowforge_pro", "generic_600x400", "nycr_32x20")
WOODPECKERS_12X24 = (301.6, 606.4)        # TRUE size of 12 x 24 in Baltic birch sheets (mm)
BED_INFO = {
    "ponoko": {"label": "Ponoko (design area 790 x 384 mm)", "kerfs": ["ponoko"], "engrave_kerfs": ["ponoko"],
               "stock": {"name": "Ponoko supplies the sheet", "width_mm": None, "height_mm": None},
               "note": "Kerf is fixed by the service; upload the Ponoko file."},
    "xtool_s1": {"label": "xTool S1 (498 x 319 mm bed; layout 498 x 301.6 mm, cut from 12 x 24 in stock)", "kerfs": ["diode", "co2", "ponoko"],
                 "engrave_kerfs": ["diode", "co2"],
                 "stock": {"name": "12 x 24 in sheet, cut to 498 mm long", "width_mm": 498.0, "height_mm": 301.6},
                 "note": "Layout is 498 x 301.6 mm so one 12 x 24 in sheet cut in two serves two runs."},
    "xtool_p2": {"label": "xTool P2 bed and 12 x 24 in stock (594.9 x 301.6 mm)", "kerfs": ["diode", "co2", "ponoko"],
                 "engrave_kerfs": ["co2"],
                 "stock": {"name": "12 x 24 in sheet (301.6 x 606.4 mm true size)", "width_mm": 606.4, "height_mm": 301.6},
                 "note": "Fits a whole 12 x 24 in sheet (those are really 11-7/8 x 23-7/8 in) and the xTool P2's 600 x 308 mm bed."},
    "glowforge_pro": {"label": "Glowforge Pro pass-through (495 x 279 mm)", "kerfs": ["diode", "co2", "ponoko"],
                      "engrave_kerfs": ["co2"],
                      "stock": {"name": "sheet at least 495 x 279 mm", "width_mm": 495.0, "height_mm": 279.0},
                      "note": "A 12 x 24 in sheet is too tall for the bed's 279 mm: cut it to 495 x 279 first."},
    "generic_600x400": {"label": "Any 600 x 400 mm bed", "kerfs": ["diode", "co2", "ponoko"],
                        "engrave_kerfs": ["diode", "co2", "ponoko"],
                        "stock": {"name": "sheet at least 600 x 400 mm", "width_mm": 600.0, "height_mm": 400.0},
                        "note": "For beds and sheet sizes not listed."},
    "nycr_32x20": {"label": "NYC Resistor laser bed (32 x 20 in)", "kerfs": ["diode", "co2", "ponoko"],
                   "engrave_kerfs": ["co2"],
                   "stock": {"name": "sheet at least 32 x 20 in", "width_mm": 812.8, "height_mm": 508.0},
                   "note": "For the shop's large-format CO2 laser."},
}

CUT = "rgb(0,0,255)"
ENGRAVE = "rgb(255,0,0)"
LABEL_GRAY = "#808080"
ENGRAVE_FILL = "#000000"
CLEARANCE_MIN = 0.35        # mm, engrave to nearest cut (asserted per part)
LABEL_CLEARANCE = 3.0       # mm, label text to the nearest cut
DXF_ART_TOL = 0.1           # mm, chord error + vertex thinning of art polylines in DXF

SHELL_NAMES = [("A", "Bottom panel"), ("B", "Right wall"), ("C", "Left wall"), ("D", "Front wall"),
               ("E", "Rear wall"), ("F", "Divider"), ("G", "Shelf"), ("H", "Top panel")]
# cut-set letter -> engraving-art face id (art/code/manifest.json)
SHELL_FACES = {"B": "right", "C": "left", "D": "front", "H": "top"}
DRAWER_FACES = {"M": "left", "N": "right", "P": "face"}      # prefixed B_ (lower) / T_ (upper)
DRAWER_NAMES = [("K", "Drawer front"), ("L", "Drawer back"), ("M", "Drawer left side"),
                ("N", "Drawer right side"), ("O", "Drawer bottom"), ("P", "Drawer faceplate")]
SHELL_PLATES = {"A": "bottom", "B": "right", "C": "left", "D": "front", "E": "rear", "F": "divider",
                "G": "shelf", "H": "top"}
DRAWER_PLATES = {"K": "front", "L": "back", "M": "left", "N": "right", "O": "bottom", "P": "face"}
SHORT_NAMES = {"A": "BOTTOM", "B": "RIGHT WALL", "C": "LEFT WALL", "D": "FRONT WALL", "E": "REAR WALL",
               "F": "DIVIDER", "G": "SHELF", "H": "TOP PANEL", "I": "LID",
               "K": "DRAWER FRONT", "L": "DRAWER BACK", "M": "DRAWER LEFT SIDE",
               "N": "DRAWER RIGHT SIDE", "O": "DRAWER BOTTOM", "P": "FACEPLATE"}


@dataclass
class Item:
    letter: str
    name: str
    piece: Piece
    face: str | None = None      # engraving-art face id (art/code/manifest.json), None = plain part
    src: str | None = None       # partgeom id that supplies the outline
    plate: str | None = None     # assembly3d plate id (None for coupon pieces)
    burn: float = BURN           # kerf compensation per side this piece was generated with
    qty: int = 1


def _clean_piece(p: Piece) -> Piece:
    """Drop the zero-length corner loops Boxes.py writes at inner corners."""
    new = []
    for sp in p.svg_paths:
        subs = eg.drop_degenerate_loops(eg.parse_subpaths(sp.d))
        new.append(SourcePath(sp.attrib, eg.emit(subs)))
    p.svg_paths = new
    return p


def generate_items(workdir: Path, kerf: float = DEFAULT_KERF) -> list[Item]:
    """Every laser-cut part of one box (21 pieces), Ponoko provider colours,
    kerf compensation `kerf / 2` per side."""
    from faxbox import generate_drawers, generate_lids, shell_generator
    from faxbox.assembly3d import source_part
    burn = kerf / 2
    cwd = os.getcwd()
    os.chdir(workdir)
    try:
        shell = shell_generator.generate_shell(provider="ponoko", burn=burn)
        drawer = generate_drawers.generate_drawer(provider="ponoko", burn=burn)
        lid = generate_lids.generate_lids(provider="ponoko", burn=burn)
        files = [Path(workdir) / p for p in (shell, drawer, lid)]
    finally:
        os.chdir(cwd)
    items: list[Item] = []
    for (letter, name), p in zip(SHELL_NAMES, _load_pieces(files[0], "Shell", strip_labels=True)):
        face = SHELL_FACES.get(letter)
        items.append(Item(letter, name, _clean_piece(p), face, source_part(face) if face else None,
                          SHELL_PLATES[letter], burn))
    for tag in ("lower", "upper"):
        pre = "B" if tag == "lower" else "T"
        for (letter, name), p in zip(DRAWER_NAMES, _load_pieces(files[1], "Drawer", strip_labels=True)):
            suffix = DRAWER_FACES.get(letter)
            face = f"{pre}_{suffix}" if suffix else None
            items.append(Item(letter, f"{name} ({tag})", _clean_piece(p), face, source_part(face) if face else None,
                              f"{pre}_{DRAWER_PLATES[letter]}", burn))
    items.append(Item("I", "Sliding lid", _clean_piece(_load_pieces(files[2], "Lid", strip_labels=True)[0]),
                      "lid", "lid", "lid", burn))
    return items


# --- test-fit coupon ----------------------------------------------------------------------

GAUGE_WIDTHS = [round(2.8 + 0.1 * i, 1) for i in range(8)]
MAGNET_DRAWN = (5.3, 5.4, 5.5, 5.6)
JOINT_TESTS = (("diode", 18.0), ("co2", 22.0), ("ponoko", 26.0))     # kerf id, piece height (mm)


def _poly_d(poly: Polygon) -> list[str]:
    out = []
    for ring in [poly.exterior] + list(poly.interiors):
        pts = list(ring.coords)
        out.append("M " + " L ".join(f"{x:.4f},{y:.4f}" for x, y in pts[:-1]) + " Z")
    return out


def _circle(cx, cy, d, n=96):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    return Polygon(np.column_stack([cx + d / 2 * np.cos(a), cy + d / 2 * np.sin(a)]))


def _piece_from(polys_cut=(), lines_engrave=()) -> Piece:
    """Piece from drawn geometry (shapely, y down)."""
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
    """Test-fit coupon.  The measuring features are drawn with NO kerf
    compensation, so what you measure is the laser's kerf; the joint tests are
    compensated for each kerf variant.

    K  10 mm square piece: kerf = 10 - measured width
    Q  panel with eight thickness slots (drawn 2.8 ... 3.5 mm) and four magnet
       holes (drawn 5.3 ... 5.6 mm)
    R  three-finger corner (finger piece + hole piece) per kerf variant:
       diode 0.12 (smallest pair, 1 tick in the marked file), CO2 0.18
       (middle, 2 ticks), Ponoko 0.20 (largest, 3 ticks)
    S  lid slot block and strip (compensated for the CO2 kerf)"""
    from boxes import Boxes, edges
    items: list[Item] = []

    # K. kerf square --------------------------------------------------------------------
    items.append(Item("K", "Coupon: kerf square, 10 mm piece", _piece_from([sbox(0, 0, 10, 10)])))

    # Q. gauge panel -------------------------------------------------------------------------
    pw, ph = 118.0, 40.0
    panel = sbox(0, 0, pw, ph)
    ticks = []
    x = 8.0
    for i, w in enumerate(GAUGE_WIDTHS):
        panel = panel.difference(sbox(x, 6, x + w, 6 + 14))             # drawn exactly w wide
        for k in range(i + 1):               # i+1 engraved ticks = nth gauge (2.8 = 1)
            ticks.append((x + w / 2 - 2.0, 23.0 + 1.4 * k, x + w / 2 + 2.0, 23.0 + 1.4 * k))
        x += w + 2.2
    gx = 10.0
    for d in MAGNET_DRAWN:
        panel = panel.difference(_circle(gx + d / 2, 33, d))
        gx += d + 7.0
    items.append(Item("Q", "Coupon: thickness slots 2.8-3.5 (1-8 ticks), magnet holes 5.3-5.6",
                      _piece_from([panel], ticks)))

    # R. three-finger corners, one pair per kerf variant ------------------------------------
    class Joint(Boxes):
        def __init__(self):
            Boxes.__init__(self)
            self.addSettingsArgs(edges.FingerJointSettings)

    def render(draw, burn):
        j = Joint()
        out = str(Path(workdir) / f"joint_{burn:.3f}.svg")
        j.parseArgs(["--output", out, "--thickness", str(T), "--burn", str(burn), "--reference", "0",
                     "--FingerJoint_play", str(c.FINGER_PLAY_RELATIVE)])
        j.open()
        j.set_source_color(c.PONOKO_CUT_COLOR)
        draw(j)
        data = j.close()
        Path(out).write_bytes(data.getvalue())
        return _clean_piece(_load_pieces(Path(out), "Coupon", strip_labels=True)[0])

    def ticked(piece: Piece, n: int) -> Piece:
        """n short engraved ticks near the top of a piece (marked coupon only)."""
        cx = piece.xmin + piece.width / 2
        for k in range(n):
            y = piece.ymin + 5.0 + 1.4 * k
            piece.svg_paths.append(SourcePath({"stroke": ENGRAVE, "fill": "none"},
                                              f"M {cx - 2:.4f},{y:.4f} L {cx + 2:.4f},{y:.4f}"))
        return piece

    length = 14.3 * T               # Boxes: (length - 2T) // 4T = 3 fingers
    for idx, (kid, hgt) in enumerate(JOINT_TESTS, 1):
        burn = KERFS[kid] / 2
        fingers = render(lambda j: j.rectangularWall(length, hgt, "feee", move="right"), burn)
        holes = render(lambda j: j.rectangularWall(
            length, hgt, "eeee", callback=[lambda: j.fingerHolesAt(0, T / 2, length, angle=0), None, None, None],
            move="right"), burn)
        items.append(Item("R", f"Coupon: three-finger corner, kerf {KERFS[kid]:.2f}, finger piece", ticked(fingers, idx), burn=burn))
        items.append(Item("R", f"Coupon: three-finger corner, kerf {KERFS[kid]:.2f}, hole piece", ticked(holes, idx), burn=burn))

    # S. lid in slot -------------------------------------------------------------------------
    b = KERFS["co2"] / 2
    slot_h = c.LID_SLOT_HEIGHT
    rail = c.LID_RAIL_HEIGHT
    block = sbox(0, 0, 70, 10 + slot_h + rail)
    block = block.difference(sbox(-1, 10, 45, 10 + slot_h))      # open-mouthed slot, 45 deep
    block_drawn = block.buffer(b, join_style=2)
    strip = sbox(0, 0, 60, 14).buffer(b, join_style=2)
    items.append(Item("S", "Coupon: lid slot block (slot T + clearance)", _piece_from([block_drawn]), burn=b))
    items.append(Item("S", "Coupon: lid strip", _piece_from([strip]), burn=b))
    return items


def coupon_guide() -> dict:
    """How to read the coupon, as data the site can draw."""
    return {
        "order": ["Cut the coupon first, on a scrap of your real plywood.",
                  "Measure the kerf square, pick the kerf file set that matches, and try the joints.",
                  "Measure the plywood thickness with calipers or from the slot gauge."],
        "features": [
            {"id": "kerf_square", "part": "K", "drawn_mm": 10.0,
             "measure": "outside width of the cut square, with calipers",
             "formula": "kerf = 10.00 - measured width",
             "choose": [{"kerf_mm": v, "set": k} for k, v in KERFS.items()],
             "then": "Use the file set whose kerf is closest to the number you measured."},
            {"id": "thickness_slots", "part": "Q", "count": len(GAUGE_WIDTHS), "drawn_widths_mm": GAUGE_WIDTHS,
             "reading": "the narrowest slot your plywood slides into without force",
             "formula": "thickness is about drawn width + kerf, rounded to 0.05",
             "ticks": "the marked coupon has i engraved ticks above slot i (1 = 2.8 mm); on the plain coupon "
                      "the slots run from the narrowest to the widest in a row: count them in order",
             "then": "Pick the thickness set (2.8 ... 3.5 mm) nearest your plywood."},
            {"id": "magnet_holes", "part": "Q", "drawn_diameters_mm": list(MAGNET_DRAWN),
             "formula": "cut hole = drawn diameter + kerf; the box wants a 5.65 mm hole for a 6.0 mm magnet",
             "reading": "the hole a 6 x 2 mm magnet pushes into with firm finger pressure and stays in",
             "then": "If that is the smallest hole, the plywood's hole is running big: nothing to change in the "
                     "box files, but use a drop of glue. If the largest hole is still tight, the hole is "
                     "running small: file or ream the 4 magnet holes."},
            {"id": "finger_joints", "part": "R", "pairs": [{"kerf_mm": KERFS[k], "set": k, "piece_height_mm": h}
                                                           for k, h in JOINT_TESTS],
             "identify": "the pairs differ in size: the smallest pair is the diode set, the middle one CO2, the "
                         "largest Ponoko; the marked coupon also has 1, 2 or 3 engraved ticks on both pieces of a pair",
             "reading": "press each finger piece into the hole piece of the same size",
             "right": "goes together with firm hand pressure, no gap, no rattle",
             "tight_along_the_finger": "tight when sliding along the length of the fingers: your kerf is "
                                       "smaller than that set assumes; use the next smaller kerf set",
             "loose_along_the_finger": "loose or rattling: your kerf is larger; use the next larger kerf set",
             "tight_through_the_slot": "the fingers will not go through the plywood thickness of the slot: "
                                       "your plywood is thicker than the set; use the next thickness"},
            {"id": "lid_slot", "part": "S",
             "reading": "slide the lid strip into the slot block",
             "right": "slides freely with a little vertical play (about 1.2 mm total)"},
        ],
    }


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


# --- geometry of a part on the bed ---------------------------------------------------------------------

MODES = {"cut": "drawn", "labels": "interior", "engrave": "exterior"}


def bed_up(item: Item, mode: str) -> str:
    """Which face of the part is up on the bed: cut = as drawn; labels = the
    inside; engrave = the outside for parts that carry art, the inside for the
    rest (their joint labels go there, and nothing is ever engraved on a
    visible face without art)."""
    if mode == "engrave" and not item.face:
        return "interior"
    return MODES[mode]
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
            trimmed.extend(eg.polygon_subpaths(poly.intersection(material).difference(keepout).simplify(0.02)))
    return kept + trimmed, n_trim


def _text_subpaths(text: str, h: float, x: float, y: float):
    subs = []
    for line in lb.stroke_text(text, h):
        pts = [(x + px, y + h - py) for px, py in line]     # y down
        subs.append([("M", pts[0])] + [("L", q) for q in pts[1:]])
    return subs


def _label_subpaths(item: Item, cuts, kind: str | None):
    """Gray labels on the part, in the piece's own SVG coordinates: the part
    letter and name on a clear spot, and every joint name (faxbox.joints) near
    its joint, 2.5 mm tall and at least 1 mm from any cut.  Returns
    (subpaths, placed) where placed lists (joint id, x, y) of the joint labels
    that found room."""
    if item.plate is None:
        return [], []
    import shapely
    from faxbox import joints as jt
    from faxbox.assembly3d import source_part
    material, cut_geom = cut_geometry(cuts)
    safe = material.buffer(-LABEL_CLEARANCE).difference(cut_geom.buffer(LABEL_CLEARANCE))
    subs, placed = [], []
    lab_box = None
    if not safe.is_empty:
        x0, y0, x1, y1 = safe.bounds
        from shapely.prepared import prep
        ps = prep(safe)
        done = False
        for text, h in ((f"{item.letter}  {SHORT_NAMES[item.letter]}", 4.0), (f"{item.letter}  {SHORT_NAMES[item.letter]}", 3.0),
                        (item.letter, 6.0), (item.letter, 4.0)):
            w = lb.text_width(text, h)
            y = y1 - h
            while y >= y0 and not done:
                x = x0
                while x + w <= x1:
                    if ps.contains(sbox(x, y, x + w, y + h)):
                        subs += _text_subpaths(text, h, x, y)
                        lab_box = sbox(x - 1, y - 1, x + w + 1, y + h + 1)
                        done = True
                        break
                    x += 2.0
                y -= 2.0
            if done:
                break
    # joint names
    jm = jt.joint_map()["by_plate"].get(item.plate, [])
    if jm:
        pc = item.piece
        m = eg.compose(eg.flip_affine(pc, kind), eg.local_to_piece(pc, source_part(item.plate), item.burn))
        safe_j = material.buffer(-1.0).difference(cut_geom.buffer(1.0))
        if lab_box is not None:
            safe_j = safe_j.difference(lab_box)          # keep clear of the part label
        h = 2.5
        for jid, lx, ly in jm:
            tx, ty = eg.apply(m, lx, ly)
            w = lb.text_width(jid, h)
            r = 45.0
            gx = np.arange(tx - r, tx + r, 1.0)
            gy = np.arange(ty - r, ty + r, 1.0)
            X, Y = np.meshgrid(gx, gy)
            boxes = shapely.box(X.ravel(), Y.ravel(), X.ravel() + w, Y.ravel() + h)
            ok = shapely.contains(safe_j, boxes)
            if not ok.any():
                continue
            cx, cy = X.ravel()[ok] + w / 2, Y.ravel()[ok] + h / 2
            k = int(np.argmin((cx - tx) ** 2 + (cy - ty) ** 2))
            bx, by = X.ravel()[ok][k], Y.ravel()[ok][k]
            subs += _text_subpaths(jid, h, bx, by)
            safe_j = safe_j.difference(sbox(bx - 1.0, by - 1.0, bx + w + 1.0, by + h + 1.0))
            placed.append((jid, round(float(bx), 2), round(float(by), 2)))
    return subs, placed


def bed_subpaths(item: Item, variant: str | None = None, mode: str = "engrave"):
    """The part as it lies on the bed, in the piece's own SVG coordinates (y
    down, kerf-compensated cuts).

    mode 'cut': outline as drawn, cut lines only.
    mode 'labels': inside face up; cuts, gray label, and the generator's own
      red lines (the faceplate glue-up registration lines).
    mode 'engrave': outside face up; cuts and the art of `variant`.

    Returns (cut_subpaths, engrave) with engrave a list of (kind, subpaths),
    kind 'fill', 'stroke' or 'label'.  Parts that are flipped to put the right
    face up are mirrored (see faxbox.engrave); the art is not."""
    key = (item.letter, item.name, item.burn, variant, mode)
    if key in _BED_CACHE:
        return _BED_CACHE[key]
    pc = item.piece
    kind = eg.flip_for(item.plate, bed_up(item, mode))
    flip = eg.flip_affine(pc, kind)
    cuts, red = [], []
    for sp in pc.svg_paths:
        subs = eg.transform_subpaths(eg.parse_subpaths(sp.d), flip)
        (red if sp.attrib.get("stroke") == ENGRAVE else cuts).extend(subs)
    engrave = []
    if mode == "engrave" and item.face and variant:
        m = eg.art_to_piece_svg(pc, item.face, item.src, item.burn)
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
    elif mode == "labels" or (mode == "engrave" and not item.face):
        # parts without art lie inside face up and carry the labels; parts with art
        # carry nothing on the outside
        if mode == "labels":
            engrave.extend(("stroke", [sp]) for sp in red)
        lab, _ = _label_subpaths(item, cuts, kind)
        if lab:
            engrave.append(("label", lab))
    _BED_CACHE[key] = (cuts, engrave)
    return cuts, engrave


def default_variants() -> dict[str, str]:
    return {f: eg.default_variant(f) for f in eg.faces()}


def clearance(item: Item, variant: str) -> dict:
    """Engrave-to-cut geometry of the part as exported: minimum distance from
    any inked area (or engraved line) to any cut line, how much ink lies
    outside the part's material, and ink area."""
    from shapely.ops import unary_union
    cuts, engrave = bed_subpaths(item, variant, "engrave")
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


# --- writers ------------------------------------------------------------------------------------------

def _sheet_affine(it: Item, x: float, y: float, rot: bool) -> eg.Affine:
    """Piece SVG coordinates -> sheet coordinates."""
    pc = it.piece
    m = (1.0, 0.0, 0.0, 1.0, -pc.xmin, -pc.ymin)
    if rot:
        m = eg.compose((0.0, 1.0, -1.0, 0.0, pc.height, 0.0), m)
    return eg.compose((1.0, 0.0, 0.0, 1.0, x, y), m)


def dxf_text(items, height: float) -> str:
    """R2000 ASCII DXF, units millimetres ($INSUNITS 4).  items: (layer,
    points, closed) in SVG coordinates (y down); y is flipped so the drawing is
    upright.  One LWPOLYLINE per contour; layers CUT (blue), ENGRAVE (red),
    LABELS (gray)."""
    layers = [("CUT", 5), ("ENGRAVE", 1), ("LABELS", 8)]
    h = [0x10]

    def hd() -> str:
        h[0] += 1
        return f"{h[0]:X}"

    L = ["0", "SECTION", "2", "HEADER", "9", "$ACADVER", "1", "AC1015", "9", "$INSUNITS", "70", "4",
         "9", "$MEASUREMENT", "70", "1", "0", "ENDSEC",
         "0", "SECTION", "2", "TABLES",
         "0", "TABLE", "2", "LTYPE", "5", hd(), "100", "AcDbSymbolTable", "70", "1",
         "0", "LTYPE", "5", hd(), "100", "AcDbSymbolTableRecord", "100", "AcDbLinetypeTableRecord",
         "2", "CONTINUOUS", "70", "0", "3", "Solid line", "72", "65", "73", "0", "40", "0.0",
         "0", "ENDTAB",
         "0", "TABLE", "2", "LAYER", "5", hd(), "100", "AcDbSymbolTable", "70", str(len(layers))]
    for name, color in layers:
        L += ["0", "LAYER", "5", hd(), "100", "AcDbSymbolTableRecord", "100", "AcDbLayerTableRecord",
              "2", name, "70", "0", "62", str(color), "6", "CONTINUOUS"]
    L += ["0", "ENDTAB", "0", "ENDSEC", "0", "SECTION", "2", "ENTITIES"]
    for layer, pts, closed in items:
        if len(pts) < 2:
            continue
        L += ["0", "LWPOLYLINE", "5", hd(), "100", "AcDbEntity", "8", layer, "100", "AcDbPolyline",
              "90", str(len(pts)), "70", "1" if closed else "0"]
        for x, y in pts:
            L += ["10", f"{x:.3f}", "20", f"{height - y:.3f}"]
    L += ["0", "ENDSEC", "0", "EOF"]
    return "\n".join(L) + "\n"


MODE_TEXT = {
    "cut": "Cut only: blue hairline (#0000FF) = cut, nothing else. Parts lie as drawn.",
    "labels": "Cut + labels: blue = cut, gray (#808080, layer LABELS) = part letter and joint numbers, red "
              "(#FF0000) = faceplate glue-up lines. Every part lies INSIDE face up, so the labels and lines go "
              "on the inside.",
    "engrave": "Cut + engrave: blue hairline (#0000FF) = cut, filled black (#000000) = area engrave, gray "
               "(#808080, layer LABELS) = part letter and joint numbers. Parts with art lie OUTSIDE face up (those "
               "whose drawn face would be the inside are mirrored, data-mirrored, the art is not) and carry no "
               "marks; parts without art lie INSIDE face up and carry the gray labels.",
}


def write_sheet(sheet, bed: str, n: int, total: int, out_svg: Path, out_dxf: Path, title: str,
                mode: str = "cut", variants: dict[str, str] | None = None, kerf: float | None = None):
    """Write one sheet as SVG and DXF.  mode: 'cut', 'labels' or 'engrave'."""
    bw, bh, margin, spacing = BEDS[bed]
    variants = variants or {}
    w = max(x + (it.piece.height if rot else it.piece.width) for it, x, y, rot in sheet) + margin
    h = max(y + (it.piece.width if rot else it.piece.height) for it, x, y, rot in sheet) + margin
    groups, dxf_items = [], []
    for k, (it, x, y, rot) in enumerate(sheet):
        var = variants.get(it.face) if (it.face and mode == "engrave") else None
        m = _sheet_affine(it, x, y, rot)
        cuts, engrave = bed_subpaths(it, var, mode)
        attrs = f'id="s{n}p{k}" data-part={quoteattr(it.letter + " " + it.name)}'
        if var:
            attrs += f' data-engrave={quoteattr(it.face + "/" + var)}'
        if eg.flip_for(it.plate, bed_up(it, mode)):
            attrs += ' data-mirrored="outline mirrored so the right face is up"'
        lines = [f"<g {attrs}>"]
        for sp in cuts:
            placed = eg.transform_subpaths([sp], m)
            lines.append(f'<path d={quoteattr(eg.emit(placed))} fill="none" stroke="{CUT}" '
                         f'stroke-width="{HAIRLINE_STROKE_WIDTH_MM}" />')
            dxf_items += [("CUT", pts, closed) for pts, closed in eg.flatten(placed, 0.005)]
        fills, strokes, labs = [], [], []
        for kind, subs in engrave:
            {"fill": fills, "stroke": strokes, "label": labs}[kind].extend(eg.transform_subpaths(subs, m))
        if fills:
            lines.append(f'<path d={quoteattr(eg.emit(fills, 2))} fill="{ENGRAVE_FILL}" fill-rule="evenodd" />')
            dxf_items += [("ENGRAVE", pts, True) for pts, closed in eg.flatten_simplified(fills, DXF_ART_TOL)]
        for sub in strokes:
            lines.append(f'<path d={quoteattr(eg.emit([sub]))} fill="none" stroke="{ENGRAVE}" '
                         f'stroke-width="{HAIRLINE_STROKE_WIDTH_MM}" />')
            dxf_items += [("ENGRAVE", pts, closed) for pts, closed in eg.flatten([sub], 0.01)]
        for sub in labs:
            lines.append(f'<path d={quoteattr(eg.emit([sub]))} fill="none" stroke="{LABEL_GRAY}" '
                         f'stroke-width="{HAIRLINE_STROKE_WIDTH_MM}" />')
            dxf_items += [("LABELS", pts, closed) for pts, closed in eg.flatten([sub], 0.01)]
        lines.append("</g>")
        groups.append("\n".join(lines))
    label = f"bed {bed} ({bw:.0f} x {bh:.0f} mm)" if bed not in ("face", "coupon") else bed
    kerf_txt = (f"Kerf compensation {kerf / 2:.2f} mm per side (for a {kerf:.2f} mm kerf) on cuts only. "
                if kerf else "")
    svg = f"""<?xml version="1.0" encoding="utf-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{w:.2f}mm" height="{h:.2f}mm" viewBox="0 0 {w:.2f} {h:.2f}">
<!--
Fax Machine Box, plywood {T:.2f} mm. {title}: sheet {n} of {total}, {label}.
{MODE_TEXT[mode]}
{kerf_txt}Engraving is not offset. Units are millimetres; the canvas is the size of the content, not of the bed.
Finger holes {T:.2f} + {c.FINGER_PLAY:.2f} mm. Margin {margin:.0f} mm, {spacing:.1f} mm between parts. No text.
-->
<title>{title} sheet {n} of {total} ({bed}, {T:.2f} mm)</title>
{chr(10).join(groups)}
</svg>
"""
    out_svg.write_text(svg)
    out_dxf.write_text(dxf_text(dxf_items, h))


# --- README texts ------------------------------------------------------------------------------------

README_COMMON = """Fax Machine Box - plywood {T:.2f} mm, laser kerf {kerf:.2f} mm ({kerf_id})

Units: millimetres. SVG: 1 unit = 1 mm, the canvas is the size of the drawing (not of your
bed). DXF: R2000, units millimetres ($INSUNITS 4), one polyline per contour.
Kerf: every cut line is drawn {burn:.2f} mm per side off the part, which assumes your laser
removes {kerf:.2f} mm. If yours removes a different amount use the file set for the nearest
kerf: the joints are tight or loose along the fingers by about 2 x (assumed - real kerf) and no
thickness file can fix that. Cut the coupon first.
Files: <bed>_sheet_N for your bed (see the bed list on the site). Sheets are nested for
the bed named in the file. Instructions, parts list and assembly guide: bjblabs.com/fax-machine/
"""

README_KINDS = {
    "cut": """CUT ONLY
Blue hairline (#0000FF) is the only line colour: cut through. Nothing is engraved, so a
service that cuts every line cuts exactly the parts. Parts lie as drawn.
""",
    "labels": """CUT + LABELS
For your own laser. Blue = cut. Gray (#808080, DXF layer LABELS) = single-line part labels
(letter and name) you can engrave on the INSIDE face to tell look-alike parts apart. Red
(#FF0000) = the drawer faceplate glue-up lines (left side, right side and top edge of the drawer
body; the body's bottom edge sits 0.75 mm below the plate). Every part lies INSIDE face up, so
engraving the labels puts them on the inside. If you skip the gray and red layers you get a plain
cut.
""",
    "engrave": """CUT + ENGRAVE
Blue hairline = cut. Filled black (#000000) = area engrave (the art). DXF has no fill attribute:
the art is closed polylines on layer ENGRAVE, so set that layer to fill / raster in the laser
software. Parts with art lie OUTSIDE face up and carry nothing else on that face. Parts whose outline in the cut-only files shows the
inside face (top panel, sliding lid, both faceplates, both left drawer sides) are mirrored here
so the outside face is up; the art is not mirrored. Do not flip any part in the laser software.
The mirrored parts are the same physical parts turned over, so the finger joints mate as usual.
Only cuts carry the kerf offset. Engraving stays at least 0.35 mm away from every cut.
The faceplate glue-up lines of the cut + labels files are not here (the plate is engraved
outside up); use the cut + labels faceplate for them, or align the grip slots and keep the plate
0.75 mm above the body's bottom edge, 0.95 mm in from each side.
Alternate art: the parts zip holds one file per art variant.
Parts without art lie INSIDE face up and carry gray joint labels (layer LABELS): the part letter and
a number next to each joint; the matching edge of the mating part carries the same number. Engrave
them or leave the layer off. Parts with art carry no marks on the outside.
""",
    "parts": """SINGLE PARTS, ZERO KERF
For services that apply their own kerf compensation (SendCutSend and similar): one file per
distinct part, drawn exactly to size with no offset. Quantity is in the file name (x2 = cut two).
Blue = cut, nothing else. Do not use these on your own laser unless it compensates kerf.
""",
}


README_FACES = """ART PARTS (faces/)
faces/<face>__<variant>.svg|dxf: the 11 parts that carry art, one file per art variant, at zero kerf
(your service applies its own). Blue = cut, filled black (#000000) = area engrave; in the DXF the
art is closed polylines on layer ENGRAVE, so set that layer to fill / raster. The part lies OUTSIDE
face up: parts whose outline in the plain part files shows the inside face are mirrored here, the
art is not. Do not flip anything. Engraving stays at least 0.35 mm from every cut.
"""


def readme_text(kind: str, kerf: float, kerf_id: str) -> str:
    return (README_COMMON.format(T=T, kerf=kerf, burn=kerf / 2, kerf_id=kerf_id) + "\n" + README_KINDS[kind])


# --- building a set --------------------------------------------------------------------------------------

def wall_id() -> dict:
    """Divider-column hole counts of the two side walls at this thickness (they
    differ with T; the left wall always has exactly one more)."""
    from faxbox import partgeom as pg
    out = {}
    lo, hi = c.DIVIDER_X0 - T, c.DIVIDER_X1
    for pid in ("right", "left"):
        g = pg.load_part(pid)
        n = 0
        for h in g.holes:
            b = h.bounds
            cx = (b[0] + b[2]) / 2
            # the divider row: narrow holes (width ~ T + play) in the divider column; for the left wall
            # the part is drawn mirrored, so its column sits at the mirrored x
            col = (c.DIVIDER_X0 + c.DIVIDER_X1) / 2 - T
            colx = col if pid == "right" else g.width - col
            if abs(cx - colx) < 0.5 and abs((b[2] - b[0]) - (T + c.FINGER_PLAY)) < 0.05:
                n += 1
        out[pid] = n
    assert out["left"] == out["right"] + 1, out
    return {"left_divider_holes": out["left"], "right_divider_holes": out["right"],
            "rule": "The wall with ONE MORE hole in its divider column is the left wall."}


def joint_map_data(items) -> dict:
    """Structured joint map plus which joint names ended up engraved on which
    physical part (labels set, inside face up; engrave set, parts without art)."""
    from faxbox import joints as jt
    jm = jt.joint_map()
    placed = {}
    for it in items:
        if it.plate is None:
            continue
        cuts, engrave = bed_subpaths(it, None, "labels")
        kind = eg.flip_for(it.plate, "interior")
        _, pl = _label_subpaths(it, cuts, kind)
        placed.setdefault(f"{it.letter}", sorted({p[0] for p in pl}))
    return {"joints": jm["joints"],
            "labelled_on_inside_face": placed,
            "art_parts_unlabelled": sorted({it.letter for it in items if it.face}),
            "note": "x_mm, y_mm: part-local zero-kerf frame, origin bottom-left of the nominal rectangle, "
                    "y up, outline as drawn. Parts with exterior art carry no marks on the outside."}


def build_set(out: Path, kerf: float = DEFAULT_KERF, kerf_id: str | None = None) -> dict:
    """Write one (thickness, kerf) set into `out`; see the module docstring."""
    out.mkdir(parents=True, exist_ok=True)
    kerf_id = kerf_id or next((k for k, v in KERFS.items() if abs(v - kerf) < 1e-9), f"k{kerf:.2f}")
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        items = generate_items(td, kerf)
        coupon = coupon_items(td)
    assert len(items) == 21, len(items)
    (out / "labels").mkdir(exist_ok=True)
    variants = default_variants()
    info = {"thickness": T, "kerf": kerf, "kerf_id": kerf_id, "burn": kerf / 2, "beds": {},
            "files": [], "label_files": [], "engrave_files": {}}
    for bed in HOBBY_AND_SERVICE_BEDS:
        if bed == "ponoko" and kerf_id != "ponoko":
            continue
        sheets = nest(items, bed)
        info["beds"][bed] = {"sheets": len(sheets), "parts": [[f"{it.letter} {it.name}" for it, *_ in s] for s in sheets]}
        info["engrave_files"][bed] = []
        for n, s in enumerate(sheets, 1):
            svg, dxf = out / f"{bed}_sheet_{n}.svg", out / f"{bed}_sheet_{n}.dxf"
            write_sheet(s, bed, n, len(sheets), svg, dxf, "Fax Machine Box", "cut", kerf=kerf)
            info["files"] += [svg.name, dxf.name]
            lsvg, ldxf = out / "labels" / f"{bed}_sheet_{n}.svg", out / "labels" / f"{bed}_sheet_{n}.dxf"
            write_sheet(s, bed, n, len(sheets), lsvg, ldxf, "Fax Machine Box, cut + labels", "labels", kerf=kerf)
            info["label_files"] += [f"labels/{svg.name}", f"labels/{dxf.name}"]
            if kerf_id in BED_INFO[bed]["engrave_kerfs"]:
                esvg, edxf = out / f"{bed}_sheet_{n}_engrave.svg", out / f"{bed}_sheet_{n}_engrave.dxf"
                write_sheet(s, bed, n, len(sheets), esvg, edxf, "Fax Machine Box, cut + engrave", "engrave", variants, kerf)
                info["engrave_files"][bed] += [esvg.name, edxf.name]
    # coupon on its own small sheet (plain, and marked with the thickness ticks)
    csheets = nest(coupon, "coupon")
    assert len(csheets) == 1
    write_sheet(csheets[0], "coupon", 1, 1, out / "coupon.svg", out / "coupon.dxf", "Test-fit coupon", "cut")
    write_sheet(csheets[0], "coupon", 1, 1, out / "coupon_marked.svg", out / "coupon_marked.dxf",
                "Test-fit coupon, with thickness ticks", "labels")
    info["files"] += ["coupon.svg", "coupon.dxf", "coupon_marked.svg", "coupon_marked.dxf"]
    info["coupon_parts"] = [f"{it.letter} {it.name}" for it, *_ in csheets[0]]
    info["coupon_layout"] = [{"part": f"{it.letter} {it.name}", "x_mm": round(x, 2), "y_mm": round(y, 2),
                              "width_mm": round(it.piece.height if rot else it.piece.width, 2),
                              "height_mm": round(it.piece.width if rot else it.piece.height, 2), "rotated": rot}
                             for it, x, y, rot in csheets[0]]
    info["coupon_guide"] = coupon_guide()
    info["engrave"] = {"default_variants": variants, "clearance_required_mm": CLEARANCE_MIN}
    info["wall_id"] = wall_id()
    info["joint_map"] = joint_map_data(items)
    for kind, name in (("cut", "README.txt"), ("labels", "labels/README.txt"), ("engrave", "README_engrave.txt")):
        (out / name).write_text(readme_text(kind, kerf, kerf_id))
    info["engrave_readme"] = "README_engrave.txt"
    (out / "set.json").write_text(json.dumps(info, indent=1) + "\n")
    return info


def build_parts(out: Path) -> dict:
    """Zero-kerf single-part files, one per distinct part (the service applies
    its own kerf): parts/<letter>_<name>[_x2].svg|dxf, plus README."""
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        items = generate_items(Path(td), 0.0)
    seen, files, listing = set(), [], []
    for it in items:
        if it.letter in seen:
            continue
        seen.add(it.letter)
        qty = 2 if it.letter in "KLMNOP" else 1
        base = it.name.replace(" (lower)", "")
        slug = "".join(ch if ch.isalnum() else "_" for ch in base).strip("_").lower()
        stem = f"{it.letter}_{slug}" + (f"_x{qty}" if qty > 1 else "")
        one = Item(it.letter, base, it.piece, None, None, it.plate, 0.0, qty)
        write_sheet([(one, 5.0, 5.0, False)], "face", 1, 1, out / f"{stem}.svg", out / f"{stem}.dxf", base, "cut")
        files += [f"{stem}.svg", f"{stem}.dxf"]
        listing.append({"letter": it.letter, "name": base, "qty": qty, "stem": stem})
    # one file per art variant: the part at zero kerf, outside face up, with that art
    (out / "faces").mkdir(exist_ok=True)
    face_files, clear = [], {}
    for it in items:
        if not it.face:
            continue
        for v in eg.variants(it.face):
            tag = f"{it.face}__{v['id']}"
            clear[f"{it.face}/{v['id']}"] = round(_check_clearance(it, v["id"]), 3)
            svg, dxf = out / "faces" / f"{tag}.svg", out / "faces" / f"{tag}.dxf"
            write_sheet([(it, 5.0, 5.0, False)], "face", 1, 1, svg, dxf, f"{it.name}, {v['label']}", "engrave",
                        {it.face: v["id"]})
            face_files += [f"faces/{svg.name}", f"faces/{dxf.name}"]
    (out / "README.txt").write_text(
        f"Fax Machine Box - plywood {T:.2f} mm\n\nUnits: millimetres (SVG user unit = 1 mm; DXF R2000, "
        f"$INSUNITS 4).\n\n" + README_KINDS["parts"] + "\n" + README_FACES)
    return {"thickness": T, "files": files + face_files + ["README.txt"], "parts": listing,
            "face_files": face_files, "min_clearance_mm": clear, "clearance_required_mm": CLEARANCE_MIN}


def main(argv: list[str]) -> None:
    out = Path(argv[1])
    kerfs = [float(k) for k in argv[2:]] or [DEFAULT_KERF]
    master = {"thickness": T, "kerfs": {}}
    for k in kerfs:
        kid = next((n for n, v in KERFS.items() if abs(v - k) < 1e-9), f"k{k:.2f}")
        master["kerfs"][f"{k:.2f}"] = build_set(out / f"k{k:.2f}" if len(kerfs) > 1 else out, k, kid)
    if len(kerfs) > 1:
        master["parts"] = build_parts(out / "parts")
        (out / "set.json").write_text(json.dumps({"thickness": T, "kerfs": list(master["kerfs"]),
                                                   "parts": master["parts"]}, indent=1) + "\n")
    print(f"cut sets for T={T} written to {out}")


if __name__ == "__main__":
    main(sys.argv)
