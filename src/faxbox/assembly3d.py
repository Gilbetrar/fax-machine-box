"""Virtual assembly of the box from the zero-kerf part outlines.

Every part is a flat plate: a 2D outline with holes (from
`faxbox.partgeom`) extruded by the material thickness and placed in box
coordinates by a 4x4 transform.

Box coordinates (mm), origin at the exterior front-left-bottom corner:
    X  front -> rear (0 .. 304.8)
    Y  left -> right (0 .. 165.1), as seen by someone standing at the front
    Z  up (0 .. 127)
Seen as a coordinate frame X, Y, Z is LEFT-handed.  A right-handed viewer
(three.js: x right, y up, z toward the camera) maps a box point to
(Y, Z, -X); that mapping is a reflection, so triangle winding flips with it.

Part-local frame (`PartGeom`): origin at the bottom-left of the part's
nominal rectangle, x right, y up, z = thickness direction 0..T.  The
transform of a part maps local (x, y, z, 1) to box coordinates.  Local z+
is the face a person sees when looking at the outline as drawn.

This module holds
  * PLATES: the placed parts (transform, thickness slab, exterior face),
  * collision / sweep tests used by tests/test_assembly3d.py,
  * ASSEMBLY_STEPS: the verified assembly order with the insertion direction
    of every step (the direction the part moves while going in).
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np
import shapely
from shapely.affinity import affine_transform
from shapely.geometry import box as sbox

from faxbox import config as c
from faxbox import partgeom as pg

T = c.T
X, Y, Z = 0, 1, 2
AXNAME = "XYZ"
L = c.SHELL_EXT["length"]
W = c.SHELL_EXT["width"]
H = c.SHELL_EXT["height"]


# --- placement table -----------------------------------------------------------

@dataclass(frozen=True)
class Placement:
    """Part id -> where the part sits.  (ia, ra): box axis the local x axis
    runs along and the nominal range it covers; (ib, rb) likewise for local
    y; (ic, rc): thickness axis and the slab's range.  flip=(fx, fy)
    reverses local x / y along their box axes."""
    pid: str
    ia: int
    ra: tuple
    ib: int
    rb: tuple
    ic: int
    rc: tuple
    flip: tuple = (0, 0)
    group: str = "shell"
    step: str = ""            # key into ASSEMBLY_STEPS
    color: str = "wood"


def _placements() -> dict[str, Placement]:
    P = {}
    add = lambda *a, **k: P.__setitem__(a[0], Placement(*a, **k))
    fl, w_in = c.FLOOR_TOP, W - T
    add("bottom", X, (T, L - T), Y, (T, w_in), Z, (0, T), step="bottom")
    add("right", X, (T, L - T), Z, (0, H), Y, (w_in, W), step="right")
    add("left", X, (T, L - T), Z, (0, H), Y, (0, T), flip=(1, 0), step="left")
    add("front", Y, (T, w_in), Z, (0, c.FRONT_WALL_TOP), X, (0, T), step="front")
    add("rear", Y, (T, w_in), Z, (0, H), X, (L - T, L), step="rear")
    add("divider", Y, (T, w_in), Z, (fl, c.TOP_PANEL_Z0), X, (c.DIVIDER_X0, c.DIVIDER_X1), step="frame")
    add("shelf", X, (c.BAY_X0, c.BAY_X1), Y, (T, w_in), Z, (c.SHELF_Z0, c.SHELF_Z1), step="frame")
    add("top", X, (c.DIVIDER_X0, c.BAY_X1), Y, (T, w_in), Z, (c.TOP_PANEL_Z0, H), step="frame")
    lid_len, lid_w = c.SLIDING_LID["length"], c.SLIDING_LID["width"]
    add("lid", X, (c.DIVIDER_X0 - lid_len, c.DIVIDER_X0), Y, ((W - lid_w) / 2, (W + lid_w) / 2),
        Z, (c.LID_SLOT_BOTTOM, c.LID_SLOT_BOTTOM + T), step="lid")
    # turn button, pointing down: local x runs along -Z, pivot at local (r, r)
    r = c.TURN_BUTTON["pivot_from_blunt_end"]
    zp, yp = c.TURN_BUTTON_PIVOT_BOX_Z, c.TURN_BUTTON_PIVOT_BOX_Y
    add("button", Z, (zp + r - c.TURN_BUTTON["length"], zp + r), Y, (yp - r, yp + r), X, (-T, 0),
        flip=(1, 0), group="hardware", step="button", color="accent")
    D = c.DRAWER_BODY
    yc = W / 2
    y0, y1 = yc - D["width"] / 2, yc + D["width"] / 2
    xb0 = c.BAY_X0
    xb1 = xb0 + D["length"]
    for tag, z0 in (("B", c.FLOOR_TOP), ("T", c.SHELF_Z1)):
        zt = z0 + D["height"]
        add(f"{tag}_back", Y, (y0 + T, y1 - T), Z, (z0 + T, zt), X, (xb0, xb0 + T), group="drawer", step=f"drawer_{tag}")
        add(f"{tag}_front", Y, (y0 + T, y1 - T), Z, (z0 + T, zt), X, (xb1 - T, xb1), group="drawer", step=f"drawer_{tag}")
        add(f"{tag}_left", X, (xb0 + T, xb1 - T), Z, (z0 + T, zt), Y, (y0, y0 + T), group="drawer", step=f"drawer_{tag}")
        add(f"{tag}_right", X, (xb0 + T, xb1 - T), Z, (z0 + T, zt), Y, (y1 - T, y1), group="drawer", step=f"drawer_{tag}")
        add(f"{tag}_bottom", X, (xb0, xb1), Y, (y0, y1), Z, (z0, z0 + T), group="drawer", step=f"drawer_{tag}")
        fw, fh = c.FACEPLATE["width"], c.FACEPLATE["height"]
        add(f"{tag}_face", Y, (yc - fw / 2, yc + fw / 2), Z, (z0, z0 + fh), X, (xb1, xb1 + T),
            group="drawer", step=f"drawer_{tag}")
    return P


_PART_OF = {"B_back": "d_back", "B_front": "d_front", "B_left": "d_left", "B_right": "d_right",
            "B_bottom": "d_bottom", "B_face": "d_face"}


def source_part(pid: str) -> str:
    """Generator part id (partgeom) that supplies this plate's outline."""
    if pid[:2] in ("B_", "T_"):
        return _PART_OF["B_" + pid[2:]]
    return pid


class Plate:
    """A placed part.  `geom` is the plate's solid cross-section in the
    (ia, ib) plane of box coordinates; `rc` its slab along ic."""

    def __init__(self, pid: str, flip: tuple | None = None, placement: Placement | None = None):
        pl = placement or _PLACEMENTS()[pid]
        self.pid = pid
        self.pl = pl
        self.flip = pl.flip if flip is None else flip
        self.ia, self.ib, self.ic = pl.ia, pl.ib, pl.ic
        self.ra, self.rb, self.rc = pl.ra, pl.rb, pl.rc
        g = pg.load_all()[source_part(pid)]
        self.part = g
        assert abs((self.ra[1] - self.ra[0]) - g.width) < 1e-3 and abs((self.rb[1] - self.rb[0]) - g.height) < 1e-3, (
            pid, self.ra, self.rb, g.width, g.height)
        self.local = g.solid
        self.holes_local = g.holes
        self.outer_local = g.outer

    # -- in-plane transform ----------------------------------------------------
    def tf(self, geom):
        fx, fy = self.flip
        sx = -1 if fx else 1
        sy = -1 if fy else 1
        ox = self.ra[1] if fx else self.ra[0]
        oy = self.rb[1] if fy else self.rb[0]
        return affine_transform(geom, [sx, 0, 0, sy, ox, oy])

    @property
    def geom(self):
        return self.tf(self.local)

    @property
    def hole_polys(self):
        return [self.tf(h) for h in self.holes_local]

    # -- 4x4 transform (local x,y,z,1 -> box) -----------------------------------
    def matrix(self) -> np.ndarray:
        """Local (x, y, z, 1) -> box.  Box axes are a left-handed frame, so
        a part placed as a physical (unmirrored) object has a 3x3 block with
        determinant -1.  The model above was verified by volumes only, so a
        plate may come out mirrored; in that case the thickness axis is
        reversed (same slab, other face up) to make the transform a true
        rigid motion."""
        fx, fy = self.flip
        m = np.eye(4)
        m[:3, :3] = 0
        m[self.ia, 0] = -1 if fx else 1
        m[self.ib, 1] = -1 if fy else 1
        m[self.ic, 2] = 1
        m[self.ia, 3] = self.ra[1] if fx else self.ra[0]
        m[self.ib, 3] = self.rb[1] if fy else self.rb[0]
        m[self.ic, 3] = self.rc[0]
        if np.linalg.det(m[:3, :3]) > 0:      # mirrored: turn the part over
            m[self.ic, 2] = -1
            m[self.ic, 3] = self.rc[1]
        return m

    def outward_sign(self, ref=None) -> int:
        """+1 if the part's local +z face (the face seen when the outline is
        viewed as drawn) points away from `ref` (a box point; default the
        box centre) along its slab axis, -1 if it points toward it."""
        m = self.matrix()
        centre = (ref if ref is not None else (L / 2, W / 2, H / 2))[self.ic]
        mid = (self.rc[0] + self.rc[1]) / 2
        return 1 if (mid - centre) * m[self.ic, 2] > 0 else -1

    def box_bounds(self):
        b = self.geom.bounds
        r = {self.ia: (b[0], b[2]), self.ib: (b[1], b[3]), self.ic: self.rc}
        return [r[a] for a in range(3)]


@lru_cache(maxsize=None)
def _PLACEMENTS_CACHED():
    return _placements()


def _PLACEMENTS():
    return _PLACEMENTS_CACHED()


def all_plates(flips: dict | None = None) -> dict[str, Plate]:
    flips = flips or {}
    return {pid: Plate(pid, flips.get(pid)) for pid in _PLACEMENTS()}


def moved(p: Plate, axis: int, d: float) -> Plate:
    q = copy.copy(p)
    sh = lambda r: (r[0] + d, r[1] + d)
    if p.ia == axis:
        q.ra = sh(p.ra)
    if p.ib == axis:
        q.rb = sh(p.rb)
    if p.ic == axis:
        q.rc = sh(p.rc)
    return q


# --- interference volume ------------------------------------------------------------

def _polys(g):
    ps = list(g.geoms) if hasattr(g, "geoms") else [g]
    return [p for p in ps if p.geom_type == "Polygon" and not p.is_empty]


def pair_volume(PA: Plate, gA, PB: Plate, gB) -> float:
    """Volume (mm^3) of the intersection of two extruded plates.  gA/gB are
    shapely geometries in each plate's own (ia, ib) plane."""
    if PA.ic == PB.ic:
        ov = min(PA.rc[1], PB.rc[1]) - max(PA.rc[0], PB.rc[0])
        if ov <= 1e-9:
            return 0.0
        if (PA.ia, PA.ib) == (PB.ia, PB.ib):
            return gA.intersection(gB).area * ov
        if (PA.ia, PA.ib) == (PB.ib, PB.ia):
            return gA.intersection(affine_transform(gB, [0, 1, 1, 0, 0, 0])).area * ov
        raise ValueError("unsupported parallel plates")
    d = 3 - PA.ic - PB.ic

    def to_dy(P, g, yax):
        if P.ia == d and P.ib == yax:
            return g
        if P.ia == yax and P.ib == d:
            return affine_transform(g, [0, 1, 1, 0, 0, 0])
        raise ValueError((P.pid, P.ia, P.ib, d, yax))

    A2 = to_dy(PA, gA, PB.ic).intersection(sbox(-1e4, PB.rc[0], 1e4, PB.rc[1]))
    B2 = to_dy(PB, gB, PA.ic).intersection(sbox(-1e4, PA.rc[0], 1e4, PA.rc[1]))
    if not _polys(A2) or not _polys(B2):
        return 0.0
    lo = max(A2.bounds[0], B2.bounds[0])
    hi = min(A2.bounds[2], B2.bounds[2])
    if hi - lo <= 1e-9:
        return 0.0
    bp = {lo, hi}
    for g in (A2, B2):
        for p in _polys(g):
            for ring in [p.exterior] + list(p.interiors):
                for x, _ in ring.coords:
                    if lo < x < hi:
                        bp.add(round(x, 9))
    bp = sorted(bp)

    def lens(g, xs):
        ls = shapely.linestrings(np.array([[[x, -1e4], [x, 1e4]] for x in xs]))
        return shapely.length(shapely.intersection(ls, g))

    e = 1e-7
    a = np.array(bp[:-1])
    b = np.array(bp[1:])
    keep = (b - a) > 2e-7
    a, b = a[keep], b[keep]
    m = (a + b) / 2
    f = lambda xs: lens(A2, xs) * lens(B2, xs)
    return float(((b - a) / 6 * (f(a + e) + 4 * f(m) + f(b - e))).sum())


def interferences(plates: dict[str, Plate], thr: float = 0.01) -> list:
    out = []
    names = list(plates)
    G = {n: plates[n].geom for n in names}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            v = pair_volume(plates[a], G[a], plates[b], G[b])
            if v > thr:
                out.append((round(v, 3), a, b))
    return sorted(out, reverse=True)


def finger_hole_fill(plates: dict[str, Plate], lo: float = 5.0, hi: float = 260.0):
    """For every finger-hole-sized hole: (part, hole bounds, empty volume).
    Empty volume is the part of the hole no other part's material fills."""
    G = {n: p.geom for n, p in plates.items()}
    rows = []
    for n, p in plates.items():
        for h in p.hole_polys:
            if not (lo < h.area < hi):
                continue
            vol = h.area * (p.rc[1] - p.rc[0])
            f = sum(pair_volume(p, h, plates[m], G[m]) for m in plates if m != n)
            rows.append((n, tuple(round(v, 2) for v in h.bounds), max(0.0, vol - f), vol))
    return rows


def first_block(A: Plate, B: Plate, axis: int, sgn: int, dmax: float = 350, thr: float = 0.3, gB=None):
    """Smallest travel of A along sgn*axis at which it overlaps B by more
    than thr mm^3 (None when it never does)."""
    gB = gB if gB is not None else B.geom
    ga = A.geom
    ba, bb = A.box_bounds(), B.box_bounds()
    for ax in range(3):
        lo, hi = ba[ax]
        if ax == axis:
            lo, hi = (lo, hi + dmax) if sgn > 0 else (lo - dmax, hi)
        if hi <= bb[ax][0] + 1e-6 or lo >= bb[ax][1] - 1e-6:
            return None
    steps = [0.0] + list(np.arange(0.05, 6.0, 0.05)) + list(np.arange(6.0, dmax, 0.5))
    for d in steps:
        Q = moved(A, axis, sgn * d)
        if pair_volume(Q, Q.geom, B, gB) > thr:
            return d
    return None


# --- verified assembly order ---------------------------------------------------------

DIRNAME = {(X, 1): "+X", (X, -1): "-X", (Y, 1): "+Y", (Y, -1): "-Y", (Z, 1): "+Z", (Z, -1): "-Z"}
DIRVEC = {"+X": (1, 0, 0), "-X": (-1, 0, 0), "+Y": (0, 1, 0), "-Y": (0, -1, 0), "+Z": (0, 0, 1), "-Z": (0, 0, -1)}

# Each step: id, plain description, the parts that go in, the direction they
# move while going in.  tests/test_assembly3d.py re-derives from collisions
# that every step is possible in this order and in this direction.
ASSEMBLY_STEPS = [
    dict(id="frame", parts=["divider", "shelf", "top"], direction="+X",
         text="Join the top panel and the shelf to the divider: slide the divider toward the rear until its tabs seat in the top panel and shelf slots."),
    dict(id="right", parts=["right"], direction="-Y",
         text="Fit the right wall onto the frame from the right."),
    dict(id="rear", parts=["rear"], direction="-X",
         text="Fit the rear wall from the rear."),
    dict(id="left", parts=["left"], direction="+Y",
         text="Fit the left wall from the left."),
    dict(id="front", parts=["front"], direction="+X",
         text="Fit the front wall from the front."),
    dict(id="bottom", parts=["bottom"], direction="+Z",
         text="Turn the box over and press the bottom panel in from below."),
    dict(id="button", parts=["button"], direction="+X",
         text="Bolt the turn button to the front wall (M3 bolt, washers, nyloc nut inside the paper compartment)."),
    dict(id="lid", parts=["lid"], direction="+X",
         text="Slide the lid into its slots from the front."),
]


# --- checks -----------------------------------------------------------------------------

def _is_hardware_hole(bounds) -> bool:
    """Magnet and pivot holes stay empty on purpose: not finger holes."""
    w, h = bounds[2] - bounds[0], bounds[3] - bounds[1]
    dia = max(w, h)
    return abs(w - h) < 0.1 and (abs(dia - c.MAGNET_HOLE_DIA) < 0.3
                                 or abs(dia - c.TURN_BUTTON["pivot_hole_dia"]) < 0.3)


def unfilled_finger_holes(plates: dict[str, Plate], frac: float = 0.07):
    """Finger holes that no mating part fills (more than `frac` of the hole
    volume empty)."""
    out = []
    for n, bounds, empty, vol in finger_hole_fill(plates):
        if _is_hardware_hole(bounds):
            continue
        if empty > frac * vol:
            out.append((n, bounds, round(empty, 2)))
    return out


def tab_report(plates: dict[str, Plate]):
    """Every finger tab (outline material outside the nominal rectangle)
    must lie inside another part's slab and clear of that part's material.
    Returns (tabs checked, failures)."""
    names = list(plates)
    bad, total = [], 0
    for n in names:
        p = plates[n]
        nominal = sbox(p.ra[0], p.rb[0], p.ra[1], p.rb[1])
        for t in _polys(p.geom.difference(nominal)):
            if t.area < 0.5:
                continue
            total += 1
            vol = t.area * (p.rc[1] - p.rc[0])
            inhull = solid = 0.0
            for m in names:
                if m == n:
                    continue
                q = plates[m]
                inhull += pair_volume(p, t, q, sbox(*q.geom.bounds))
                solid += pair_volume(p, t, q, q.geom)
            if inhull / vol < 0.97 or solid > 1e-3:
                bad.append((n, tuple(round(x, 2) for x in t.bounds), round(inhull / vol, 3), round(solid, 4)))
    return total, bad


# Drawer: walls first (back and front stand up), the sides slide in across,
# the bottom goes on from below.  The faceplate is glued on afterwards.
DRAWER_STEPS = [
    dict(id="walls", parts=["back", "front"], direction="+Z",
         text="Stand the drawer back and front panels upright."),
    dict(id="left_side", parts=["left"], direction="+Y", text="Slide in the left side."),
    dict(id="right_side", parts=["right"], direction="-Y", text="Slide in the right side."),
    dict(id="bottom", parts=["bottom"], direction="+Z", text="Press the bottom panel on from below."),
    dict(id="face", parts=["face"], direction="-X", text="Glue the faceplate to the front."),
]


# Parts inventory: one letter per distinct cut part (the drawer parts come
# twice, lower "B" and upper "T").  Used on the parts list and the site.
INVENTORY = [
    ("A", "bottom", "Bottom panel", 1),
    ("B", "right", "Right wall", 1),
    ("C", "left", "Left wall", 1),
    ("D", "front", "Front wall", 1),
    ("E", "rear", "Rear wall", 1),
    ("F", "divider", "Divider", 1),
    ("G", "shelf", "Shelf", 1),
    ("H", "top", "Top panel", 1),
    ("I", "lid", "Sliding lid", 1),
    ("J", "button", "Turn button", 1),
    ("K", "d_front", "Drawer front", 2),
    ("L", "d_back", "Drawer back", 2),
    ("M", "d_left", "Drawer left side", 2),
    ("N", "d_right", "Drawer right side", 2),
    ("O", "d_bottom", "Drawer bottom", 2),
    ("P", "d_face", "Drawer faceplate", 2),
]
_COLORS = {"shell": "#e0c79b", "drawer": "#ecd8b4", "hardware": "#c8553d"}


def _plain_rings(poly, nd=3):
    simp = poly.simplify(0.0005, preserve_topology=True)
    ring = lambda r: [[round(x, nd), round(y, nd)] for x, y in list(r.coords)[:-1]]
    return ring(simp.exterior), [ring(i) for i in simp.interiors]


def _view_reference(pid: str):
    """Point the 'outer' face looks away from.  Walls, top, bottom, lid,
    faceplates: the box centre.  Divider: its visible face is toward the
    paper compartment (away from the rear).  Shelf: the upper face.  Drawer
    panels: away from the drawer's own centre."""
    if pid == "divider":
        return (L, W / 2, H / 2)
    if pid == "shelf":
        return (L / 2, W / 2, 0.0)
    if pid[:2] in ("B_", "T_") and not pid.endswith("_face"):
        z0 = c.FLOOR_TOP if pid[0] == "B" else c.SHELF_Z1
        D = c.DRAWER_BODY
        return (c.BAY_X0 + D["length"] / 2, W / 2, z0 + D["height"] / 2)
    return None


def site_data() -> dict:
    """Everything the site build needs, deterministic."""
    plates = all_plates()
    letter_of = {src: (ltr, nm, q) for ltr, src, nm, q in INVENTORY}
    drawer_steps, box_steps = DRAWER_STEPS, ASSEMBLY_STEPS
    steps, step_of = [], {}

    def add(phase, st, parts, **extra):
        steps.append(dict(n=len(steps) + 1, id=f"{phase}_{st['id']}", phase=phase, parts=parts,
                          direction=st["direction"], insert_direction=list(DIRVEC[st["direction"]]),
                          text=st["text"], **extra))
        for p in parts:
            step_of.setdefault(p, len(steps))

    for st in drawer_steps:
        add("drawer", st, [f"{t}_{p}" for t in "BT" for p in st["parts"]])
    for st in box_steps:
        add("box", st, list(st["parts"]))
    steps.append(dict(n=len(steps) + 1, id="drawers_in", phase="box", parts=[p for p in plates if p[:2] in ("B_", "T_")],
                      direction="-X", insert_direction=[-1, 0, 0],
                      text="Slide both drawers in through the rear openings until the magnets catch."))
    parts = []
    for pid, p in plates.items():
        g = p.part
        solid = g.solid
        polys = [q for q in (list(solid.geoms) if hasattr(solid, "geoms") else [solid]) if q.area > 1]
        assert len(polys) == 1, pid
        outline, holes = _plain_rings(polys[0])
        src = source_part(pid)
        ltr, nm, qty = letter_of[src]
        step = step_of[pid]
        d = steps[step - 1]["insert_direction"]
        m = p.matrix()
        sign = p.outward_sign(_view_reference(pid))
        parts.append(dict(
            id=pid, name=nm if qty == 1 else f"{nm} ({'lower' if pid[0] == 'B' else 'upper'})",
            letter=ltr, quantity_per_box=qty,
            outline=outline, holes=holes, thickness=T,
            transform=[[round(float(v), 6) for v in row] for row in m],
            color=_COLORS[p.pl.group], assembly_step=step, insert_direction=d,
            exterior_face="+" if sign > 0 else "-",
            internal=pid in ("divider", "shelf") or pid[:2] in ("B_", "T_") and not pid.endswith("_face"),
            outline_mirrored_when_viewed_from_exterior=sign < 0,
        ))
    return dict(
        box=dict(length=L, width=W, height=H, thickness=T, interior=[c.INTERIOR_LENGTH, c.INTERIOR_WIDTH, c.BAY_INTERIOR_HEIGHT],
                 units="mm",
                 axes="X front->rear, Y left->right (seen from the front), Z up; origin at the exterior front-left-bottom corner",
                 handedness="left",
                 three_js="three = (Y, Z, -X): a reflection, so flip triangle winding",
                 transform="row-major 4x4, local (x, y, z, 1) column vector -> box; local z+ is the face seen when the outline is viewed as drawn",
                 finger_play=c.FINGER_PLAY),
        parts=parts, steps=steps,
        inventory=[dict(letter=a, name=n, quantity=q) for a, _, n, q in INVENTORY],
    )


def sweep_collision(plates, names, axis, sgn, dmax, others, dz=0.0, thr=0.05):
    """Move `names` together along sgn*axis for 0..dmax (and dz up in Z);
    return (worst overlap volume, first hit) against `others`."""
    worst, first = 0.0, None
    ds = list(np.arange(0, min(dmax, 10), 0.25)) + list(np.arange(10, dmax, 1.0))
    for d in ds:
        for a in names:
            Q = moved(plates[a], axis, sgn * d)
            if dz:
                Q = moved(Q, Z, dz)
            for b in others:
                v = pair_volume(Q, Q.geom, plates[b], plates[b].geom)
                if v > thr:
                    worst = max(worst, v)
                    if first is None:
                        first = (round(d, 2), a, b, round(v, 3))
    return worst, first


def leaves_freely(plates, group, present, axis, sgn, dmax=350):
    """True when `group` (moved rigidly along sgn*axis) never overlaps the
    other plates in `present`."""
    for a in group:
        for b in present:
            if b in group:
                continue
            if first_block(plates[a], plates[b], axis, sgn, dmax=dmax) is not None:
                return False
    return True


def verify_steps(plates, steps=None):
    """Re-derive from collisions that every step of the assembly order is
    possible.  Returns a list of (step id, ok, free insertion directions)."""
    steps = steps or ASSEMBLY_STEPS
    present: list[str] = []
    out = []
    for st in steps:
        present = present + st["parts"]
        free = []
        for (ax, s), name in DIRNAME.items():
            if leaves_freely(plates, st["parts"], present, ax, s):
                free.append(DIRNAME[(ax, -s)])
        out.append((st["id"], st["direction"] in free, free))
    return out
