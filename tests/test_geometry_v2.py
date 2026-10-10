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


# --- hardware and paper -----------------------------------------------------------------

def test_only_magnets_are_hardware():
    """The turn-button lock (bolt, washers, nyloc nut) was removed on 2026-10-10."""
    assert set(c.HARDWARE) == {"magnet", "magnet_thickness", "magnets_needed", "magnets_to_buy"}
    assert "N52" in c.HARDWARE["magnet"]
    assert c.HARDWARE["magnets_needed"] == 4


def test_quarter_letter_paper_stands_on_edge_with_clearance():
    assert c.PAPER["height"] == pytest.approx(4.25 * 25.4)
    assert c.PAPER["width"] == pytest.approx(5.5 * 25.4)
    assert c.PAPER_HEADROOM >= 3.0, c.PAPER_HEADROOM       # under the lid
    assert c.PAPER_SIDE_ROOM >= 15.0, c.PAPER_SIDE_ROOM    # between the side walls


def test_lid_rail_and_clearance_v2():
    assert c.LID_RAIL_HEIGHT >= 7.0
    assert c.LID_SLOT_VERTICAL_CLEARANCE >= 1.2 - 1e-9


# --- red-team pass 1 fixes (G17, G20, G22) ----------------------------------------------

def test_strip_under_lower_opening_is_at_least_min_web():
    """G22: the strip was T tall (2.8-2.9 mm at thin stock, below MIN_WEB)."""
    assert c.BOTTOM_OPENING_Z0 >= c.MIN_WEB - 1e-9, (c.T, c.BOTTOM_OPENING_Z0)
    # the drawer rests on the opening floor, so it is never below it
    assert c.BOTTOM_DRAWER_Z0 == pytest.approx(c.BOTTOM_OPENING_Z0)
    # and the slot above still holds the drawer: top of the drawer under the shelf
    assert c.BOTTOM_DRAWER_Z0 + c.DRAWER_BODY["height"] <= c.SHELF_Z0 - 1.0


def test_faceplate_is_centred_in_its_opening():
    """G20: reveal was 0 at the bottom and 1.5 mm at the top."""
    for z0, z1 in ((c.BOTTOM_OPENING_Z0, c.BOTTOM_OPENING_Z1), (c.TOP_OPENING_Z0, c.TOP_OPENING_Z1)):
        zf = z0 + c.FACEPLATE_Z_OFFSET
        assert zf - z0 == pytest.approx(c.FACEPLATE_REVEAL)
        assert z1 - (zf + c.FACEPLATE["height"]) == pytest.approx(c.FACEPLATE_REVEAL)


def test_magnet_holes_are_centred(parts):
    """G17: a hole 40 mm off centre made a flipped drawer back (or a mirror
    built box) miss its magnet by 80 mm."""
    assert c.MAGNET_Y_OFFSET == 0.0
    def centres(pid):
        out = []
        for h in parts[pid].holes:
            w, ht = h.bounds[2] - h.bounds[0], h.bounds[3] - h.bounds[1]
            if abs(w - ht) < 0.05 and abs(w - c.MAGNET_HOLE_DIA) < 0.5:
                out.append(((h.bounds[0] + h.bounds[2]) / 2, (h.bounds[1] + h.bounds[3]) / 2))
        return out
    back = centres("d_back")
    assert len(back) == 1 and back[0][0] == pytest.approx(parts["d_back"].width / 2, abs=0.01)
    div = centres("divider")
    assert len(div) == 2 and all(x == pytest.approx(parts["divider"].width / 2, abs=0.01) for x, _ in div)
    # and the part really is mirror symmetric in its width now
    from shapely.affinity import scale
    g = parts["d_back"].solid
    mirrored = scale(g, xfact=-1, origin=(parts["d_back"].width / 2, 0))
    assert g.symmetric_difference(mirrored).area < 0.1
