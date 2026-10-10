"""Wrong-way and swapped assemblies (red-team G11, G12, G16, G17).

The earlier tests turn one part at a time.  These also swap the two side
walls and turn the divider, and turn the drawer back round.

Finding (kept as a decision record): the box is mirror-symmetric apart from
the divider key, so swapping the walls AND turning the divider left-for-right
is a legitimate mirror-image box, not a collision.  It cannot be prevented by
outlines, because every flat part can be turned over to build the mirror.
Each wall then sits turned over, so its engraved (outside) face looks into the
box.  What goes wrong in such a build is only that the art is inside.  What these tests pin down:

  * swapping the walls alone, or turning the divider alone, collides;
  * the mirror build is the only clean variant, and in it the drawer magnets
    still meet the divider magnets (they are centred);
  * a drawer back turned round (mirror-symmetric now, hole centred) still
    meets its magnet.
"""

import itertools
from dataclasses import replace

import numpy as np
import pytest

from faxbox import assembly3d as a3
from faxbox import config as c


@pytest.fixture(scope="module")
def plates():
    return a3.all_plates()


def _swapped(plates, divider_flip):
    Q = dict(plates)
    pl = a3._PLACEMENTS()
    # each wall goes to the other side with its front still at the front and
    # upright: that is the part turned over, i.e. installed inside out
    Q["right"] = a3.Plate("right", pl["right"].flip, replace(pl["right"], rc=pl["left"].rc))
    Q["left"] = a3.Plate("left", pl["left"].flip, replace(pl["left"], rc=pl["right"].rc))
    Q["divider"] = a3.Plate("divider", divider_flip)
    return Q


def _bad(Q, who):
    return sum(v for v, *names in a3.interferences(Q, thr=1.0) if any(n in who for n in names[0:2]))


@pytest.mark.parametrize("swap,flip", [(s, f) for s in (False, True) for f in itertools.product((0, 1), (0, 1))])
def test_wall_swap_and_divider_turn_matrix(plates, swap, flip):
    Q = _swapped(plates, flip) if swap else dict(plates, divider=a3.Plate("divider", flip))
    clash = a3.interferences(Q, thr=1.0)
    mirror_build = swap and flip == (1, 0)
    unmodified = (not swap) and flip == plates["divider"].flip
    if mirror_build or unmodified:
        assert clash == [], clash
    else:
        assert sum(v for v, *_ in clash) > 10.0, (swap, flip, clash)


def test_mirror_build_keeps_the_magnets_aligned(plates):
    """Centred magnet holes: the divider's holes sit on the box centre line, so
    the mirror build and a turned divider leave them in the same place."""
    Q = _swapped(plates, (1, 0))
    mid = c.SHELL_EXT["width"] / 2
    def ys(p):
        out = []
        for h in p.hole_polys:
            b = h.bounds
            if abs(b[2] - b[0] - c.MAGNET_HOLE_DIA) < 0.15 and abs(b[3] - b[1] - c.MAGNET_HOLE_DIA) < 0.15:
                ct = h.centroid
                out.append({p.ia: ct.x, p.ib: ct.y}[a3.Y])
        return out
    assert ys(Q["divider"]) and all(abs(y - mid) < 0.02 for y in ys(Q["divider"]))
    assert ys(plates["B_back"]) and all(abs(y - mid) < 0.02 for y in ys(plates["B_back"]))


@pytest.mark.parametrize("tag", ["B", "T"])
def test_drawer_back_turned_round_still_fits_and_meets_its_magnet(plates, tag):
    back = plates[f"{tag}_back"]
    turned = a3.Plate(f"{tag}_back", (1 - back.flip[0], back.flip[1]))
    Q = dict(plates)
    Q[f"{tag}_back"] = turned
    assert not [i for i in a3.interferences(Q, thr=1.0) if f"{tag}_back" in i[1:]]
    assert len(a3.unfilled_finger_holes(Q)) == len(a3.unfilled_finger_holes(plates))
    ys = []
    for h in turned.hole_polys:
        b = h.bounds
        if abs(b[2] - b[0] - c.MAGNET_HOLE_DIA) < 0.15:
            ys.append({turned.ia: h.centroid.x, turned.ib: h.centroid.y}[a3.Y])
    assert ys and abs(ys[0] - c.SHELL_EXT["width"] / 2) < 0.02
