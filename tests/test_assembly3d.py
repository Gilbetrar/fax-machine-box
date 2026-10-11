"""3D virtual assembly checks (faxbox.assembly3d).

Every part is placed in box coordinates from its zero-kerf outline.  These
tests re-derive from volumes that the box assembles: no interference, every
finger lands in a hole, the divider only fits one way, the assembly order is
possible step by step, the drawers and the lid slide, the magnet holes line up.
"""

import itertools

import numpy as np
import pytest

from faxbox import assembly3d as a3
from faxbox import config as c

T = c.T


@pytest.fixture(scope="module")
def plates():
    return a3.all_plates()


def test_no_interference(plates):
    # < 1 mm^3 is numerical noise from faces that touch exactly
    assert a3.interferences(plates, thr=1.0) == []


def test_every_finger_lands_and_every_finger_hole_is_filled(plates):
    total, bad = a3.tab_report(plates)
    assert total >= 270, total
    assert not bad, bad[:5]
    assert a3.unfilled_finger_holes(plates) == []


@pytest.mark.parametrize("flip", [(0, 1), (1, 0), (1, 1)])
def test_divider_fits_only_one_way(plates, flip):
    """Turned around, upside down, or both: the divider's fingers land on
    wall material.  (v1 fitted all four ways; upside down its magnet holes
    were 5.24 mm off.)"""
    Q = dict(plates)
    Q["divider"] = a3.Plate("divider", flip)
    clash = [i for i in a3.interferences(Q, thr=1.0) if "divider" in i[1:]]
    unfilled = [u for u in a3.unfilled_finger_holes(Q)]
    assert sum(i[0] for i in clash) > 10.0 or unfilled, (clash, unfilled)


def test_divider_correct_way_is_clean(plates):
    assert not [i for i in a3.interferences(plates, thr=1.0) if "divider" in i[1:]]


@pytest.mark.parametrize("pid", ["right", "left", "top", "shelf", "bottom", "rear", "front"])
def test_wrong_flip_of_walls_and_panels_is_blocked_or_symmetric(plates, pid):
    """Each of these either fits only one way or is mirror-symmetric (the
    shelf, top and bottom are symmetric about the box centre line)."""
    base_unfilled = len(a3.unfilled_finger_holes(plates))
    ok_flips = []
    for flip in itertools.product((0, 1), (0, 1)):
        Q = dict(plates)
        Q[pid] = a3.Plate(pid, flip)
        i = [x for x in a3.interferences(Q, thr=1.0) if pid in x[1:]]
        u = len(a3.unfilled_finger_holes(Q))
        if not i and u == base_unfilled:
            ok_flips.append(flip)
    assert plates[pid].flip in ok_flips
    if pid in ("rear", "front"):
        # upside down is blocked; turned left for right it is symmetric
        assert (0, 1) not in ok_flips and (1, 1) not in ok_flips, ok_flips
    if pid in ("right", "left"):
        assert ok_flips == [plates[pid].flip]


def test_assembly_order_is_possible_step_by_step(plates):
    res = a3.verify_steps(plates)
    assert all(ok for _, ok, _ in res), res


def test_divider_enters_frame_from_the_front_only(plates):
    """With the top panel and shelf in place the divider can only move
    toward +X to engage them."""
    present = ["top", "shelf", "divider", "T_guideL", "T_guideR"]
    free = [a3.DIRNAME[(ax, -s)] for (ax, s) in a3.DIRNAME
            if a3.leaves_freely(plates, ["divider"], present, ax, s)]
    assert free == ["+X"]


def test_bottom_before_divider_is_not_possible(plates):
    """The old README order (bottom first) cannot be done: with the bottom
    panel in, the divider's bottom fingers have no way in."""
    steps = [dict(id=p, parts=[p], direction="?") for p in ("right", "bottom", "divider", "shelf", "top")]
    res = a3.verify_steps(plates, steps)
    assert not all(free for _, _, free in res) or any(not f for _, _, f in res), res


def test_drawer_assembly_order(plates):
    for tag in "BT":
        steps = [dict(id=s["id"], parts=[f"{tag}_{p}" for p in s["parts"]], direction=s["direction"])
                 for s in a3.DRAWER_STEPS if s["id"] != "walls"]
        steps.insert(0, dict(id="walls", parts=[f"{tag}_back", f"{tag}_front"], direction="+X"))
        res = a3.verify_steps(plates, steps)
        assert all(ok for _, ok, _ in res if _ != "face"), res


@pytest.mark.parametrize("tag", ["B", "T"])
def test_drawer_slides_out_clear_of_the_box(plates, tag):
    names = [f"{tag}_{s}" for s in ("back", "front", "left", "right", "bottom", "face")]
    shell = ["bottom", "right", "left", "front", "rear", "divider", "shelf", "top"]
    shell += [n for n in plates if "guide" in n]
    worst, first = a3.sweep_collision(plates, names, a3.X, 1, 300, shell, thr=1.0)
    assert worst == 0.0, first


def test_drawers_do_not_touch_each_other(plates):
    b = [n for n in plates if n.startswith("B_")]
    t = [n for n in plates if n.startswith("T_")]
    G = {n: plates[n].geom for n in b + t}
    for x in b:
        for y in t:
            assert a3.pair_volume(plates[x], G[x], plates[y], G[y]) < 0.01


def test_drawer_fits_slot_with_headroom(plates):
    for tag, floor in (("B", c.FLOOR_TOP), ("T", c.SHELF_Z1)):
        top = plates[f"{tag}_left"].rc if False else None
        rng = plates[f"{tag}_back"].box_bounds()[a3.Z]
        ceiling = c.SHELF_Z0 if tag == "B" else c.TOP_PANEL_Z0
        assert ceiling - rng[1] >= 1.5


@pytest.mark.parametrize("dz", [0.0, 0.6, 1.1])
def test_lid_slides_in_slot_with_vertical_play(plates, dz):
    shell = ["right", "left", "front", "divider", "top", "shelf", "rear", "bottom"]
    worst, first = a3.sweep_collision(plates, ["lid"], a3.X, -1, 120, shell, dz=dz, thr=1.0)
    assert worst == 0.0, first


def test_lid_would_jam_beyond_the_clearance(plates):
    shell = ["right", "left"]
    worst, _ = a3.sweep_collision(plates, ["lid"], a3.X, -1, 60, shell,
                                  dz=c.LID_SLOT_VERTICAL_CLEARANCE + 0.3, thr=1.0)
    assert worst > 1.0


def _hole_centres(plate, dia, axes):
    """Centres of the round holes of diameter `dia` (bbox square, +-0.15)."""
    out = []
    for h in plate.hole_polys:
        b = h.bounds
        if abs(b[2] - b[0] - dia) < 0.15 and abs(b[3] - b[1] - dia) < 0.15:
            ct = h.centroid
            r = {plate.ia: ct.x, plate.ib: ct.y}
            out.append(tuple(round(r[a], 2) for a in axes))
    return sorted(out)


def test_magnet_holes_are_coaxial_at_closed_position(plates):
    div = _hole_centres(plates["divider"], c.MAGNET_HOLE_DIA, (a3.Y, a3.Z))
    assert len(div) == 2
    for tag in "BT":
        back = _hole_centres(plates[f"{tag}_back"], c.MAGNET_HOLE_DIA, (a3.Y, a3.Z))
        assert len(back) == 1
        assert min(np.hypot(back[0][0] - d[0], back[0][1] - d[1]) for d in div) < 0.1, (back, div)
    # and the drawer back panel sits against the divider face
    assert plates["B_back"].rc[0] == pytest.approx(plates["divider"].rc[1], abs=c.DRAWER_BAY_GAP + 1e-6)


def test_no_button_plate_and_front_wall_has_no_pivot_hole(plates):
    assert "button" not in plates
    assert not _hole_centres(plates["front"], 3.2, (a3.Y, a3.Z))
    assert all(p[1] != "button" for p in a3.INVENTORY)
    assert all("button" not in s["parts"] for s in a3.ASSEMBLY_STEPS)


def test_matrices_map_outline_corners_into_box_bounds(plates):
    for pid, p in plates.items():
        m = p.matrix()
        b = p.part.outer.bounds
        corners = np.array([[x, y, z, 1.0] for x in (b[0], b[2]) for y in (b[1], b[3]) for z in (0, T)])
        world = corners @ m.T
        bb = p.box_bounds()
        for ax in range(3):
            assert world[:, ax].min() == pytest.approx(bb[ax][0], abs=1e-6), (pid, ax)
            assert world[:, ax].max() == pytest.approx(bb[ax][1], abs=1e-6), (pid, ax)


def test_all_placements_have_the_same_handedness(plates):
    dets = {round(np.linalg.det(p.matrix()[:3, :3])) for p in plates.values()}
    assert len(dets) == 1, dets


def test_overall_envelope(plates):
    lo = [min(p.box_bounds()[a][0] for p in plates.values()) for a in range(3)]
    hi = [max(p.box_bounds()[a][1] for p in plates.values()) for a in range(3)]
    assert lo[a3.X] == pytest.approx(0, abs=1e-6)
    assert hi[a3.X] == pytest.approx(c.SHELL_EXT["length"], abs=1e-6)
    assert lo[a3.Y] == pytest.approx(0, abs=1e-6) and hi[a3.Y] == pytest.approx(c.SHELL_EXT["width"], abs=1e-6)
    assert lo[a3.Z] == pytest.approx(0, abs=1e-6) and hi[a3.Z] == pytest.approx(c.SHELL_EXT["height"], abs=1e-6)


# --- drawer guides (red-team H1) and the rounded lid slot (H2) ------------------------------------

def test_four_guides_lie_on_the_bottom_panel_and_the_shelf_against_the_walls(plates):
    g = {n: p for n, p in plates.items() if "guide" in n}
    assert sorted(g) == ["B_guideL", "B_guideR", "T_guideL", "T_guideR"]
    for n, p in g.items():
        b = p.box_bounds()
        assert b[a3.X][0] == pytest.approx(c.BAY_X0) and b[a3.X][1] - b[a3.X][0] == pytest.approx(c.DRAWER_GUIDE["length"])
        floor = c.FLOOR_TOP if n[0] == "B" else c.SHELF_Z1
        assert b[a3.Z] == pytest.approx((floor, floor + T), abs=2e-3)    # T high, resting on the panel
        assert b[a3.Y][1] - b[a3.Y][0] == pytest.approx(T, abs=2e-3)    # T wide
        wall_inner = T if n.endswith("L") else c.SHELL_EXT["width"] - T
        face = b[a3.Y][0] if n.endswith("L") else b[a3.Y][1]
        assert face == pytest.approx(wall_inner, abs=2e-3)               # flush against the wall


def test_guide_leading_end_is_tapered_in_plan(plates):
    """V5: a yawed drawer corner must be funnelled in, not meet a square end face.  The end that faces
    the rear opening is cut at 30 degrees in plan, down to a 0.8 mm tip."""
    from shapely.geometry import box as sbox
    for n in ("B_guideL", "B_guideR", "T_guideL", "T_guideR"):
        geom = plates[n].geom                                  # (X, Y) plan of the rib
        x0, y0, x1, y1 = geom.bounds
        assert x1 - x0 == pytest.approx(c.DRAWER_GUIDE["length"])
        inner_y = y1 if n.endswith("L") else y0                 # the face the drawer meets
        # at the rear end the rib is only the tip wide; at the other end it is T wide
        tip = geom.intersection(sbox(x1 - 0.02, y0 - 1, x1, y1 + 1))
        base = geom.intersection(sbox(x0, y0 - 1, x0 + 0.01, y1 + 1))
        assert tip.area / 0.02 == pytest.approx(c.DRAWER_GUIDE["tip_width"], abs=0.02)
        assert base.area / 0.01 == pytest.approx(T, abs=0.02)
        # the taper reaches the full width after (T - tip) / tan 30 = 4.1 mm
        run = (T - c.DRAWER_GUIDE["tip_width"]) / np.tan(np.radians(c.DRAWER_GUIDE["taper_deg"]))
        mid = geom.intersection(sbox(x1 - run - 0.01, y0 - 1, x1 - run + 0.01, y1 + 1))
        assert mid.area / 0.02 == pytest.approx(T, abs=0.05)


def test_guide_taper_angle_is_30_degrees_and_the_yaw_margin_is_small(plates):
    """The wedge face makes 30 degrees with the travel direction (a square end met the drawer corner
    head-on).  The whole guide clearance is under a degree of drawer yaw."""
    run = (T - c.DRAWER_GUIDE["tip_width"]) / np.tan(np.radians(c.DRAWER_GUIDE["taper_deg"]))
    assert np.degrees(np.arctan((T - c.DRAWER_GUIDE["tip_width"]) / run)) == pytest.approx(30.0)
    channel = c.INTERIOR_WIDTH - 2 * T
    yaw = np.degrees(np.arctan((channel - c.DRAWER_BODY["width"]) / c.DRAWER_BODY["length"]))
    assert 0 < yaw < 1.0


def test_guides_limit_the_drawer_float_to_the_front_clearance(plates):
    """The channel between the guides is INTERIOR_WIDTH - 2T, which equals the rear-wall
    opening width at T >= 3.0, so the far end can float no further than the front end.
    N52 6 x 2 mm discs pull 3.7 N at 2.0 mm lateral offset (red-team magnet model), so a
    float of at most 2.0 mm keeps the closed-drawer pull above 3 N.  Without the guides
    the float was (bay - drawer) / 2 = 4.9 mm, where the pull is negative."""
    channel = c.INTERIOR_WIDTH - 2 * T
    drawer = c.DRAWER_BODY["width"]
    float_far = (channel - drawer) / 2
    assert 0 < float_far <= 2.0, float_far
    bay_float = (c.INTERIOR_WIDTH - drawer) / 2
    assert bay_float > 4.0 and float_far < bay_float / 2
    for tag in "BT":
        bottom = plates[f"{tag}_bottom"].box_bounds()[a3.Y]
        guide = plates[f"{tag}_guideL"].box_bounds()[a3.Y]
        assert bottom[0] - guide[1] == pytest.approx(float_far, abs=2e-3)


def test_lid_slot_rear_corners_are_rounded_and_the_lid_clears_them(plates):
    from shapely.geometry import box as sbox
    wall = plates["right"].geom
    h = c.LID_SLOT_HEIGHT
    r = c.LID_SLOT_CORNER_R
    zone = sbox(c.DIVIDER_X0 - 3, c.LID_SLOT_BOTTOM, c.DIVIDER_X0, c.LID_SLOT_BOTTOM + h)
    void = zone.area - zone.intersection(wall).area
    sharp = 3 * h
    assert sharp - void == pytest.approx(2 * (1 - np.pi / 4) * r * r, abs=0.06)       # two quarter-round fillets
    shell = ["right", "left"]
    # pushed home and lifted against the rail: still no contact with the fillets
    worst, _ = a3.sweep_collision(plates, ["lid"], a3.X, -1, 1, shell, dz=c.LID_SLOT_VERTICAL_CLEARANCE - 0.01, thr=0.01)
    assert worst == 0.0
    assert plates["lid"].box_bounds()[a3.X][1] == pytest.approx(c.LID_REAR_X) and c.SLIDING_LID["length"] == pytest.approx(c.LID_REAR_X - c.LID_FRONT_RECESS)
