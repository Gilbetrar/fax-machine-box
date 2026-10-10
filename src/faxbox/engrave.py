"""Engraving art for the cut files: load, register to a cut piece, transform.

The art lives in art/code (manifest.json plus out/<face>__<variant>.svg).  Each
art SVG is drawn as the face is SEEN FROM OUTSIDE the finished box: canvas =
the part's nominal rectangle, u right, v down, in mm.  `art_to_local` in the
art manifest maps (u, v) to the part's zero-kerf local frame (origin at the
bottom-left of the nominal rectangle, x right, y up) used by
`faxbox.partgeom`.

The cut files contain the same parts as Boxes.py draws them, with kerf
compensation, in SVG coordinates (y down).  Pieces whose drawn face is the
INTERIOR face (`engrave_part_flipped`) have to lie on the laser bed exterior
face up so the engraving lands on the outside.  For those the cut outline is
mirrored in the cut+engrave files and the art is drawn unmirrored:

  * vertical parts (walls, drawer sides, faceplates): mirror left-right
  * horizontal parts (top panel, lid): mirror front-rear (top-bottom on the
    sheet), so the front stays the front

With the part turned over like that, art (u, v) coordinates equal bed
coordinates up to a translation, which `art_to_bed` returns.

Everything here is pure geometry (no I/O beyond reading the art files) so the
tests can use it to prove the transforms in 3D.
"""

from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
ART_DIR = REPO / "art" / "code"

# Affine as (a, b, c, d, e, f):  x' = a x + c y + e ;  y' = b x + d y + f
Affine = tuple
IDENT: Affine = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def apply(m: Affine, x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = m
    return a * x + c * y + e, b * x + d * y + f


def compose(outer: Affine, inner: Affine) -> Affine:
    """Affine that applies `inner` first, then `outer`."""
    a1, b1, c1, d1, e1, f1 = inner
    a2, b2, c2, d2, e2, f2 = outer
    return (a2 * a1 + c2 * b1, b2 * a1 + d2 * b1,
            a2 * c1 + c2 * d1, b2 * c1 + d2 * d1,
            a2 * e1 + c2 * f1 + e2, b2 * e1 + d2 * f1 + f2)


def det(m: Affine) -> float:
    return m[0] * m[3] - m[1] * m[2]


# --- art manifest -----------------------------------------------------------------------------

@lru_cache(maxsize=None)
def art_manifest() -> dict:
    return json.loads((ART_DIR / "manifest.json").read_text())["faces"]


def faces() -> list[str]:
    return list(art_manifest())


def variants(face: str) -> list[dict]:
    return art_manifest()[face]["variants"]


def default_variant(face: str) -> str:
    vs = variants(face)
    return next(v["id"] for v in vs if v.get("default")) if any(v.get("default") for v in vs) else vs[0]["id"]


def is_flipped(face: str) -> bool:
    return bool(art_manifest()[face]["engrave_part_flipped"])


def flip_kind(face: str) -> str | None:
    """None (drawn face is the exterior), 'v' (mirror left-right) or 'h'
    (mirror top-bottom on the sheet), from the art manifest's affine."""
    f = art_manifest()[face]
    if not f["engrave_part_flipped"]:
        return None
    (a, _, _), (_, e, _) = f["art_to_local"]
    return "v" if a < 0 else "h"


def art_to_local(face: str) -> Affine:
    (a, b, c), (d, e, f) = art_manifest()[face]["art_to_local"]
    return (a, d, b, e, c, f)


# --- SVG path handling ------------------------------------------------------------------------

_TOK = re.compile(r"[A-Za-z]|[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_ARGS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "Z": 0}


def parse_subpaths(d: str) -> list[list[tuple]]:
    """Absolute segments per subpath: ('M', (x, y)), ('L', p), ('C', p1, p2, p3),
    ('Z',).  Handles M L H V C Z in either case with implicit repeats."""
    toks = _TOK.findall(d)
    i = 0
    cmd = None
    cur = start = (0.0, 0.0)
    subs: list[list[tuple]] = []
    seg: list[tuple] | None = None
    while i < len(toks):
        if toks[i].isalpha():
            cmd = toks[i]
            i += 1
            if cmd in "Zz":
                if seg is not None:
                    seg.append(("Z",))
                    cur = start
                continue
        up = cmd.upper()
        if up not in _ARGS or up == "Z":
            raise ValueError(f"unsupported path command {cmd!r}")
        n = _ARGS[up]
        v = [float(t) for t in toks[i:i + n]]
        i += n
        rel = cmd.islower()
        ox, oy = cur if rel else (0.0, 0.0)
        if up == "M":
            cur = start = (ox + v[0], oy + v[1])
            seg = [("M", cur)]
            subs.append(seg)
            cmd = "l" if rel else "L"            # implicit lineto after moveto
        elif up == "L":
            cur = (ox + v[0], oy + v[1])
            seg.append(("L", cur))
        elif up == "H":
            cur = ((cur[0] if rel else 0.0) + v[0], cur[1])
            seg.append(("L", cur))
        elif up == "V":
            cur = (cur[0], (cur[1] if rel else 0.0) + v[0])
            seg.append(("L", cur))
        else:
            p1 = (ox + v[0], oy + v[1])
            p2 = (ox + v[2], oy + v[3])
            p3 = (ox + v[4], oy + v[5])
            seg.append(("C", p1, p2, p3))
            cur = p3
    return subs


def transform_subpaths(subs, m: Affine):
    out = []
    for sp in subs:
        new = []
        for s in sp:
            if s[0] == "Z":
                new.append(s)
            else:
                new.append((s[0],) + tuple(apply(m, *p) for p in s[1:]))
        out.append(new)
    return out


def _fmt(v: float) -> str:
    s = f"{v:.3f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def emit(subs, prec_fix: bool = True) -> str:
    """SVG path data.  The first point of every subpath is absolute, the rest
    are written relative to the previous ROUNDED point so rounding never
    accumulates."""
    parts = []
    for sp in subs:
        prev = None
        for s in sp:
            k = s[0]
            if k == "Z":
                parts.append("z")
                prev = start
                continue
            pts = [(round(x, 3), round(y, 3)) for x, y in s[1:]]
            if k == "M":
                start = pts[0]
                parts.append(f"M{_fmt(pts[0][0])} {_fmt(pts[0][1])}")
                prev = pts[0]
                continue
            cmd = "l" if k == "L" else "c"
            args = []
            for x, y in pts:
                args += [_fmt(x - prev[0]), _fmt(y - prev[1])]
            parts.append(cmd + " ".join(args))
            prev = pts[-1]
    return "".join(parts)


def flatten(subs, tol: float = 0.01) -> list[tuple[list[tuple[float, float]], bool]]:
    """Polylines (points, closed) with at most `tol` mm chord error."""
    out = []
    for sp in subs:
        pts: list[tuple[float, float]] = []
        closed = False
        for s in sp:
            k = s[0]
            if k == "M":
                pts.append(s[1])
            elif k == "L":
                pts.append(s[1])
            elif k == "C":
                p0 = np.array(pts[-1])
                p1, p2, p3 = (np.array(p) for p in s[1:])
                m = max(np.linalg.norm(p0 - 2 * p1 + p2), np.linalg.norm(p1 - 2 * p2 + p3))
                n = max(1, int(math.ceil(math.sqrt(0.75 * m / tol))))
                ts = np.linspace(0, 1, n + 1)[1:]
                for t in ts:
                    q = ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3
                    pts.append((float(q[0]), float(q[1])))
            else:
                closed = True
        if closed and len(pts) > 1 and abs(pts[0][0] - pts[-1][0]) < 1e-9 and abs(pts[0][1] - pts[-1][1]) < 1e-9:
            pts.pop()
        out.append((pts, closed))
    return out


# --- art files --------------------------------------------------------------------------------

@dataclass
class ArtPath:
    kind: str                 # 'fill' (black area engrave) or 'stroke' (red vector engrave)
    subs: list


def _parse_matrix(s: str | None) -> Affine:
    if not s:
        return IDENT
    m = re.match(r"\s*matrix\(([^)]*)\)\s*$", s)
    if not m:
        raise ValueError(f"unsupported transform {s!r}")
    v = [float(t) for t in re.split(r"[,\s]+", m.group(1).strip())]
    return tuple(v)


@lru_cache(maxsize=None)
def load_art(face: str, variant: str) -> tuple[ArtPath, ...]:
    """The art in the art frame (u right, v down, mm), transforms baked in.
    Filled shapes come back as 'fill' (black), stroked shapes as 'stroke'
    (they become red hairlines)."""
    meta = next(v for v in variants(face) if v["id"] == variant)
    root = ET.parse(ART_DIR / meta["svg"]).getroot()
    out: list[ArtPath] = []

    def walk(el, m: Affine, fill: str, stroke: str):
        tag = el.tag.split("}")[-1]
        if tag in ("title", "desc"):
            return
        m = compose(m, _parse_matrix(el.get("transform")))
        fill = el.get("fill", fill)
        stroke = el.get("stroke", stroke)
        if tag == "path" and el.get("d"):
            subs = transform_subpaths(parse_subpaths(el.get("d")), m)
            if stroke not in ("none", ""):
                out.append(ArtPath("stroke", subs))
            elif fill not in ("none", ""):
                out.append(ArtPath("fill", subs))
        for ch in el:
            walk(ch, m, fill, stroke)

    walk(root, IDENT, "#000000", "none")
    return tuple(out)


def art_size(face: str) -> tuple[float, float]:
    w, h = art_manifest()[face]["size_mm"]
    return w, h


# --- registration to the cut pieces -----------------------------------------------------------

def local_to_piece(piece, src_part: str, burn: float) -> Affine:
    """Zero-kerf part-local (x, y) -> the piece's own SVG coordinates (as in
    the Boxes.py file, y down).  The piece outline is the nominal outline grown
    by `burn` on every side; Piece.xmin/ymin/width/height is its bounding
    box, and partgeom's local frame sits `ext` (tab depth) inside the
    bounding box on the sides that carry finger tabs."""
    from faxbox import partgeom as pg
    spec = pg.PART_SPECS[src_part]
    left, right, bottom, top = [pg.T if e else 0.0 for e in spec.ext]
    return (1.0, 0.0, 0.0, -1.0,
            piece.xmin + burn + left,
            piece.ymin + piece.height - bottom - burn)


def bed_flip(piece, face: str | None) -> Affine:
    """Mirror inside the piece's own bounding box (so the bbox stays put)."""
    kind = flip_kind(face) if face else None
    if kind == "v":
        return (-1.0, 0.0, 0.0, 1.0, 2 * piece.xmin + piece.width, 0.0)
    if kind == "h":
        return (1.0, 0.0, 0.0, -1.0, 0.0, 2 * piece.ymin + piece.height)
    return IDENT


def art_to_piece_svg(piece, face: str, src_part: str, burn: float) -> Affine:
    """Art (u, v) -> piece SVG coordinates AFTER the bed flip."""
    m = compose(local_to_piece(piece, src_part, burn), art_to_local(face))
    return compose(bed_flip(piece, face), m)


# --- ink geometry (even-odd nesting of the traced rings) -----------------------------------------

def ink_components(rings):
    """Group closed rings (shapely Polygons, each ring filled) into ink
    components by even-odd nesting.  Returns a list of (polygon, [ring
    indices]) where polygon has the nested rings as holes."""
    from shapely.geometry import Polygon
    from shapely.strtree import STRtree
    n = len(rings)
    tree = STRtree(rings)
    parent = [None] * n
    depth = [0] * n
    for i in range(n):
        best = None
        d = 0
        for j in tree.query(rings[i], predicate="within"):
            j = int(j)
            if j != i:
                d += 1
                if best is None or rings[j].area < rings[best].area:
                    best = j
        depth[i], parent[i] = d, best
    comps = []
    for i in range(n):
        if depth[i] % 2 == 0:
            holes = [j for j in range(n) if parent[j] == i and depth[j] % 2 == 1]
            poly = Polygon(rings[i].exterior.coords, [rings[j].exterior.coords for j in holes])
            comps.append((poly, [i] + holes))
    return comps


def polygon_subpaths(geom, min_area: float = 0.05):
    """Subpaths (M, L..., Z) for the rings of a (Multi)Polygon; fragments
    under `min_area` mm2 are dropped."""
    out = []
    polys = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
    for p in polys:
        if p.geom_type != "Polygon" or p.area < min_area:
            continue
        for ring in [p.exterior] + list(p.interiors):
            xy = list(ring.coords)[:-1]
            out.append([("M", xy[0])] + [("L", q) for q in xy[1:]] + [("Z",)])
    return out


def flatten_simplified(subs, tol: float = 0.03):
    """Polylines for DXF output: chord error and vertex thinning together stay
    within `tol` mm (a laser spot is ~0.1 mm)."""
    from shapely.geometry import LineString
    out = []
    for pts, closed in flatten(subs, tol / 2):
        if len(pts) > 4:
            ls = LineString(pts + ([pts[0]] if closed else [])).simplify(tol / 2, preserve_topology=False)
            q = list(ls.coords)
            if closed:
                q = q[:-1]
            if len(q) >= (3 if closed else 2):
                pts = q
        out.append((pts, closed))
    return out
