"""Joint map: which part meets which, for the "match 1 to 1" marks.

Derived from the 3D model (faxbox.assembly3d): every finger tab that lands in
another part's slab makes a joint between those two parts.  One joint per pair
of parts.  Each joint gets a name made of the lower part letter and a running
number ("C3" = third joint of part C, in pair order), and the same name goes
on both parts near the joint.  The two drawers are built identically, so the
lower drawer's joints name the upper drawer's too (match within one drawer).

`joint_map()` returns structured data:

    {"joints": [{"id": "C3", "parts": [{"part": "C", "name": "Left wall", "plate": "left",
                                         "edge": "front", "x_mm": ..., "y_mm": ...}, {...}]}],
     "by_plate": {plate: [(id, x_mm, y_mm), ...]}}

x_mm, y_mm are in the part's own zero-kerf local frame (origin at the bottom-left
of the nominal rectangle, x right, y up, the outline as drawn in the cut files).
"""

from __future__ import annotations

from functools import lru_cache

import numpy as np
from shapely.geometry import box as sbox

from faxbox import assembly3d as A


def _letter(pid: str) -> str:
    inv = {p: (letter, name) for letter, p, name, _ in A.INVENTORY}
    return inv[A.source_part(pid)][0]


def _name(pid: str) -> str:
    inv = {p: (letter, name) for letter, p, name, _ in A.INVENTORY}
    return inv[A.source_part(pid)][1]


def _edge(plate, lx: float, ly: float) -> str:
    w, h = plate.part.width, plate.part.height
    d = {"left": lx, "right": w - lx, "bottom": ly, "top": h - ly}
    return min(d, key=d.get)


@lru_cache(maxsize=None)
def joint_map() -> dict:
    plates = A.all_plates()
    lower = [n for n in plates if not n.startswith("T_")]
    G = {n: plates[n].geom for n in plates}
    contacts: dict[frozenset, list] = {}
    for n in lower:
        p = plates[n]
        nominal = sbox(p.ra[0], p.rb[0], p.ra[1], p.rb[1])
        tabs = p.geom.difference(nominal)
        if tabs.is_empty:
            continue
        thick = p.rc[1] - p.rc[0]
        for m in lower:
            q = plates[m]
            if m == n or q.ic == p.ic or q.ic not in (p.ia, p.ib):
                continue
            # the part of the tabs that lies inside q's slab (along q's thickness axis, which is
            # one of p's in-plane axes), then require it to land inside q's outline hull
            lo, hi = q.rc
            big = 1e4
            clip = sbox(lo, -big, hi, big) if q.ic == p.ia else sbox(-big, lo, big, hi)
            inside = tabs.intersection(clip)
            for t in A._polys(inside):
                if t.area < 0.5:
                    continue
                v = A.pair_volume(p, t, q, sbox(*q.geom.bounds))
                if v < 0.9 * t.area * thick:
                    continue
                ct = t.centroid
                box = [0.0, 0.0, 0.0]
                box[p.ia], box[p.ib], box[p.ic] = ct.x, ct.y, (p.rc[0] + p.rc[1]) / 2
                contacts.setdefault(frozenset((n, m)), []).append(box)
    pairs = sorted(contacts, key=lambda s: tuple(sorted((_letter(x), x) for x in s)))
    counters: dict[str, int] = {}
    joints, by_plate = [], {}

    def local_of(plate, box):
        inv = np.linalg.inv(np.asarray(plate.matrix()))
        x, y, _, _ = inv @ np.array([*box, 1.0])
        return float(x), float(y)

    for s in pairs:
        a, b = sorted(s, key=lambda x: (_letter(x), x))
        first = min(_letter(a), _letter(b))
        counters[first] = counters.get(first, 0) + 1
        jid = f"{first}{counters[first]}"
        mean = list(np.mean(contacts[s], axis=0))
        parts = []
        for pid in (a, b):
            lx, ly = local_of(plates[pid], mean)
            parts.append({"part": _letter(pid), "name": _name(pid), "plate": pid, "edge": _edge(plates[pid], lx, ly),
                          "x_mm": round(lx, 2), "y_mm": round(ly, 2)})
            by_plate.setdefault(pid, []).append((jid, lx, ly))
            if pid.startswith("B_"):                    # the upper drawer is identical
                tp = "T_" + pid[2:]
                by_plate.setdefault(tp, []).append((jid, lx, ly))
        joints.append({"id": jid, "parts": parts})
    return {"joints": joints, "by_plate": by_plate}
