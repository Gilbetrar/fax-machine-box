"""v2 geometry guards (2026-10-10): decision records as tests.

Measured on the zero-kerf outlines from faxbox.partgeom, which come from the
same generator classes as the cut files.

- Every part must survive the laser as ONE piece (no loose chips).  The v1
  rear wall failed this: the T-tall strip under the lower drawer opening was
  cut into 11 chips by the bottom-panel finger-hole row.
- No material web thinner than MIN_LIGAMENT anywhere.  v1 had a 0.5 mm web
  between the lid-slot corner and the first divider hole.
- Holes that break through a part's outline are allowed only for finger-hole
  rows (breakout <= play/2 + 0.02); nothing else may touch the outline.
"""

import pytest

from faxbox import config as c
from faxbox import partgeom as pg

KERF = 0.2            # Ponoko birch; NYCR is 0.16
MIN_LIGAMENT = 1.5    # mm of material, physical (before kerf)

# part id -> {(x, y) rounded: reason}.  Empty on purpose: add an entry only
# with a written reason.
LIGAMENT_ALLOW = {}

ALL = list(pg.PART_SPECS)


@pytest.fixture(scope="module")
def parts():
    return pg.load_all()


@pytest.mark.parametrize("pid", ALL)
@pytest.mark.parametrize("kerf", [0.16, KERF, 0.3])
def test_part_is_one_piece_after_kerf(parts, pid, kerf):
    pieces = pg.kerf_pieces(parts[pid], kerf)
    assert len(pieces) == 1, (
        f"{pid}: {len(pieces)} pieces after a {kerf} mm kerf; areas "
        f"{sorted(round(p.area, 1) for p in pieces)}")


@pytest.mark.parametrize("pid", ALL)
def test_minimum_ligament(parts, pid):
    found = [(round(d, 2), (round(x, 1), round(y, 1)))
             for d, (x, y) in pg.thin_ligaments(parts[pid].solid, MIN_LIGAMENT)
             if (round(x, 1), round(y, 1)) not in LIGAMENT_ALLOW.get(pid, {})]
    assert not found, f"{pid}: material web < {MIN_LIGAMENT} mm at {found[:6]}"


@pytest.mark.parametrize("pid", ALL)
def test_only_finger_rows_break_through_the_outline(parts, pid):
    p = parts[pid]
    outer_in = p.outer.buffer(1e-6)
    play = c.FINGER_PLAY
    for h in p.holes:
        if outer_in.contains(h):
            continue
        w = h.bounds[2] - h.bounds[0]
        ht = h.bounds[3] - h.bounds[1]
        short = min(w, ht)
        assert short == pytest.approx(c.T + play, abs=0.02), (
            f"{pid}: hole {tuple(round(v, 2) for v in h.bounds)} touches the outline but is not a finger hole")
        depth = h.difference(p.outer).area / max(w, ht)
        assert depth <= play / 2 + 0.02, f"{pid}: finger hole breaks out {depth:.3f} mm"


def test_rear_wall_strip_under_lower_opening_is_solid(parts):
    """The web below the lower drawer opening spans the whole opening width
    with no hole in it."""
    from shapely.geometry import box
    p = parts["rear"]
    x0 = (c.INTERIOR_WIDTH - c.OPENING_WIDTH) / 2
    strip = box(x0, 0.0, x0 + c.OPENING_WIDTH, c.BOTTOM_OPENING_Z0)
    assert p.solid.contains(strip.buffer(-0.01))


def test_bottom_panel_rear_edge_is_plain(parts):
    p = parts["bottom"]
    # nominal X extent: rear edge x == nominal width everywhere
    xs = [x for x, _ in p.outer.exterior.coords]
    assert max(xs) == pytest.approx(p.width, abs=1e-6)
