"""Zero-kerf part outlines as shapely geometry.

Every laser-cut part of the box is regenerated through the same generator
classes the cut files use, with Boxes.py's `burn` set to 0.  The result is
the *nominal* outline of each part (what the CAD model says), without kerf
compensation.  Tests use it to check ligaments and connectivity, and
`faxbox.assembly3d` places the outlines in box coordinates.

Each part is returned in a local frame: origin at the bottom-left corner of
the part's *nominal* rectangle (finger tabs stick out of it into negative or
over-size coordinates), x to the right, y up.  This matches the way
DESIGN.md describes the parts ("exterior face up").
"""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import Polygon
from shapely.ops import unary_union
from svgpathtools import parse_path

from faxbox import config
from faxbox.config import (
    FINGER_PLAY_RELATIVE,
    LID_GRIP_SLOT,
    MATERIAL_THICKNESS,
    SLIDING_LID,
)
from faxbox.generate_drawers import DrawerBox
from faxbox.generate_hardware import TurnButton
from faxbox.generate_lids import LidGenerator
from faxbox.shell_generator import OuterShell

T = MATERIAL_THICKNESS


@dataclass(frozen=True)
class PartSpec:
    id: str
    name: str
    cls: type
    build: object          # callable(generator) that draws the part
    ext: tuple             # (left, right, bottom, top): sides extended by fingers


def _lid(o) -> None:
    length, width, s = SLIDING_LID["length"], SLIDING_LID["width"], LID_GRIP_SLOT
    o.rectangularWall(
        length, width, "eeee",
        callback=[lambda: o.rectangularHole(
            s["center_from_front"], width / 2, s["width"], s["height"], r=s["radius"]),
            None, None, None],
        move="right", label="Sliding Lid")


PART_SPECS: dict[str, PartSpec] = {p.id: p for p in [
    PartSpec("bottom", "Bottom", OuterShell, lambda o: o._build_bottom(), (1, 1, 1, 1)),
    PartSpec("right", "Right Wall", OuterShell, lambda o: o._build_side_wall(False, "Right Wall"), (1, 1, 0, 0)),
    PartSpec("left", "Left Wall", OuterShell, lambda o: o._build_side_wall(True, "Left Wall"), (1, 1, 0, 0)),
    PartSpec("front", "Front Wall", OuterShell, lambda o: o._build_front_wall(), (1, 1, 0, 0)),
    PartSpec("rear", "Rear Wall", OuterShell, lambda o: o._build_rear_wall(), (1, 1, 0, 0)),
    PartSpec("divider", "Vertical Divider", OuterShell, lambda o: o._build_divider(), (1, 1, 1, 1)),
    PartSpec("shelf", "Horizontal Shelf", OuterShell, lambda o: o._build_shelf(), (1, 0, 1, 1)),
    PartSpec("top", "Top Panel", OuterShell, lambda o: o._build_top_panel(), (0, 1, 1, 1)),
    PartSpec("d_front", "Drawer Front", DrawerBox, lambda o: o._build_front(), (1, 1, 1, 0)),
    PartSpec("d_back", "Drawer Back", DrawerBox, lambda o: o._build_back(), (1, 1, 1, 0)),
    PartSpec("d_left", "Drawer Left Side", DrawerBox, lambda o: o._build_side("Left Side"), (1, 1, 1, 0)),
    PartSpec("d_right", "Drawer Right Side", DrawerBox, lambda o: o._build_side("Right Side"), (1, 1, 1, 0)),
    PartSpec("d_bottom", "Drawer Bottom", DrawerBox, lambda o: o._build_bottom(), (0, 0, 0, 0)),
    PartSpec("d_face", "Drawer Faceplate", DrawerBox, lambda o: o._build_faceplate(), (0, 0, 0, 0)),
    PartSpec("lid", "Sliding Lid", LidGenerator, _lid, (0, 0, 0, 0)),
    PartSpec("button", "Turn Button", TurnButton, lambda o: o._build_button("Turn Button"), (0, 0, 0, 0)),
]}


@dataclass
class PartGeom:
    id: str
    name: str
    outer: Polygon              # outer outline (local frame, see module doc)
    holes: list[Polygon]        # every closed inner contour (incl. breakouts)
    width: float                # nominal size
    height: float
    engrave: list[list[tuple]]  # red engrave polylines (local frame)

    @property
    def solid(self):
        """Material as a (Multi)Polygon: outline minus holes."""
        g = self.outer
        if self.holes:
            g = g.difference(unary_union(self.holes))
        return g


_PATH_RE = re.compile(r'<path d="([^"]+)"[^>]*?stroke="(rgb\([^)]*\))"')


def _sample(d: str) -> list[list[tuple]]:
    rings = []
    for sp in parse_path(d).continuous_subpaths():
        pts = []
        for seg in sp:
            n = 1 if seg.__class__.__name__ == "Line" else 24
            for t in np.linspace(0, 1, n, endpoint=False):
                z = seg.point(t)
                pts.append((z.real, z.imag))
        z = sp[-1].point(1.0)
        pts.append((z.real, z.imag))
        rings.append(pts)
    return rings


def _render(spec: PartSpec, burn: float) -> str:
    gen = spec.cls()
    with tempfile.TemporaryDirectory() as td:
        out = str(Path(td) / "p.svg")
        gen.parseArgs([
            "--output", out, "--thickness", str(T), "--burn", str(burn),
            "--reference", "0", "--FingerJoint_play", str(FINGER_PLAY_RELATIVE)])
        gen.open()
        gen.set_source_color(gen.cut_color)
        spec.build(gen)
        data = gen.close()
        return data.getvalue().decode()


def load_part(part_id: str, burn: float = 0.0) -> PartGeom:
    """Zero-kerf (burn=0) outline of one part in its local frame."""
    spec = PART_SPECS[part_id]
    svg = _render(spec, burn)
    polys, engrave = [], []
    for m in _PATH_RE.finditer(svg):
        d, stroke = m.group(1), m.group(2).replace(" ", "")
        for ring in _sample(d):
            if stroke == "rgb(0,0,255)" and len(ring) >= 4:
                polys.append(Polygon(ring).buffer(0))
            elif stroke == "rgb(255,0,0)":
                engrave.append(ring)
    polys.sort(key=lambda p: -p.area)
    outer, holes = polys[0], polys[1:]
    minx, miny, maxx, maxy = outer.bounds
    left, right, bottom, top = [T if e else 0 for e in spec.ext]
    width = maxx - minx - left - right
    height = maxy - miny - bottom - top

    def tr_xy(a):
        return np.column_stack([a[:, 0] - minx - left, maxy - a[:, 1] - bottom])

    def tr(g):
        return shapely.transform(g, tr_xy)

    eng = [[(x - minx - left, maxy - y - bottom) for x, y in r] for r in engrave]
    return PartGeom(part_id, spec.name, tr(outer), [tr(h) for h in holes], width, height, eng)


@lru_cache(maxsize=None)
def load_all(burn: float = 0.0) -> dict[str, PartGeom]:
    return {pid: load_part(pid, burn) for pid in PART_SPECS}


# --- Analysis helpers ----------------------------------------------------------

def _rings(g):
    polys = list(g.geoms) if hasattr(g, "geoms") else [g]
    out = []
    for p in polys:
        if p.is_empty:
            continue
        out.append(list(p.exterior.coords))
        out.extend(list(i.coords) for i in p.interiors)
    return out


def thin_ligaments(solid, limit: float = 1.5, min_arc: float = 5.0):
    """Material necks narrower than `limit` mm.

    Returns a list of (distance, (x, y)) for places where two boundary
    points of `solid` are closer than `limit` mm in the plane, the point
    midway between them is material (not void), and the two points are more
    than `min_arc` mm apart along the boundary (or on different rings).
    Corners and sub-`limit` features that are merely neighbours along the
    outline are ignored.
    """
    from shapely.geometry import LineString, Point
    from shapely.strtree import STRtree

    rings = _rings(solid)
    segs, meta = [], []
    for ri, r in enumerate(rings):
        cum = [0.0]
        for a, b in zip(r[:-1], r[1:]):
            cum.append(cum[-1] + ((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5)
        total = cum[-1]
        for i in range(len(r) - 1):
            if cum[i + 1] - cum[i] < 1e-9:
                continue
            segs.append(LineString([r[i], r[i + 1]]))
            meta.append((ri, cum[i], cum[i + 1], total))
    tree = STRtree(segs)
    found = {}
    for ri, r in enumerate(rings):
        cum = 0.0
        for k in range(len(r) - 1):
            p = r[k]
            if k:
                a = r[k - 1]
                cum += ((p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2) ** 0.5
            pt = Point(p)
            for j in tree.query(pt.buffer(limit)):
                rj, c0, c1, total = meta[j]
                d = segs[j].distance(pt)
                if d >= limit - 1e-9:
                    continue
                if rj == ri:
                    # arc distance from vertex to the nearest point of the segment
                    q = segs[j].project(pt)
                    arc = c0 + q
                    delta = abs(arc - cum)
                    delta = min(delta, total - delta)
                    if delta <= min_arc:
                        continue
                near = segs[j].interpolate(segs[j].project(pt))
                mid = Point((p[0] + near.x) / 2, (p[1] + near.y) / 2)
                if not solid.contains(mid) and d > 1e-9:
                    continue          # a narrow void, not a narrow web
                key = (round(p[0], 1), round(p[1], 1))
                if key not in found or d < found[key][0]:
                    found[key] = (d, (p[0], p[1]))
    return sorted(found.values())


def kerf_pieces(part: PartGeom, kerf: float = 0.2):
    """Pieces of a part after the laser removes `kerf` mm along every cut
    line (material shrinks by kerf/2 on both sides of every contour)."""
    e = part.solid.buffer(-kerf / 2)
    geoms = list(e.geoms) if hasattr(e, "geoms") else [e]
    return [g for g in geoms if not g.is_empty]
