"""Assembly-fit tests: every mating pair in DESIGN.md, enforced.

These tests encode DESIGN.md's geometry as relationships. They deliberately
recompute derived quantities from the SPEC externals instead of trusting
config's derived constants, so a drifted derivation fails loudly.

Policy (issues #7/#10 precedent): never weaken these tests to make code pass.
"""

import pytest

from faxbox import config as c

APPROX = dict(abs=1e-9)

SPEC_LENGTH = 304.8   # 12"
SPEC_WIDTH = 165.1    # 6.5"
SPEC_HEIGHT = 127.0   # 5"
SPEC_PAPER = 76.2     # 3"
SPEC_MIN_SLIDE_PLAY = 1.5  # 1/16"


# --- Material ----------------------------------------------------------------

def test_uniform_material_thickness():
    """SPEC: uniform thickness for all parts — exactly one thickness constant."""
    assert c.MATERIAL_THICKNESS == pytest.approx(3.175, **APPROX)
    thickness_names = [n for n in dir(c) if "THICKNESS" in n]
    assert thickness_names == ["MATERIAL_THICKNESS"], thickness_names


def test_external_envelope_matches_spec():
    assert c.SHELL_EXT["length"] == pytest.approx(SPEC_LENGTH, **APPROX)
    assert c.SHELL_EXT["width"] == pytest.approx(SPEC_WIDTH, **APPROX)
    assert c.SHELL_EXT["height"] == pytest.approx(SPEC_HEIGHT, **APPROX)


# --- Longitudinal layout (X) --------------------------------------------------

def test_x_axis_partition_is_exact():
    """front wall + paper + divider + bay + rear wall == 12" exactly."""
    total = c.T + SPEC_PAPER + c.T + c.BAY_LENGTH + c.T
    assert total == pytest.approx(SPEC_LENGTH, **APPROX)
    assert c.DIVIDER_X0 == pytest.approx(c.T + SPEC_PAPER, **APPROX)
    assert c.BAY_X0 == pytest.approx(c.DIVIDER_X0 + c.T, **APPROX)
    assert c.BAY_X1 == pytest.approx(SPEC_LENGTH - c.T, **APPROX)


# --- Vertical layout (Z) -------------------------------------------------------

def test_z_axis_partition_is_exact():
    """bottom + two equal slots + shelf + top panel == 5" exactly."""
    total = c.T + 2 * c.DRAWER_SLOT_HEIGHT + c.T + c.T
    assert total == pytest.approx(SPEC_HEIGHT, **APPROX)
    assert c.SHELF_Z0 == pytest.approx(c.T + c.DRAWER_SLOT_HEIGHT, **APPROX)
    assert c.SHELF_Z1 == pytest.approx(c.SHELF_Z0 + c.T, **APPROX)
    assert c.TOP_PANEL_Z0 == pytest.approx(SPEC_HEIGHT - c.T, **APPROX)


def test_shelf_is_at_spec_vertical_midpoint():
    """SPEC: fixed shelf at the vertical midpoint (~2.5")."""
    shelf_mid = (c.SHELF_Z0 + c.SHELF_Z1) / 2
    assert shelf_mid == pytest.approx(SPEC_HEIGHT / 2, abs=1.0)


# --- Drawers vs openings --------------------------------------------------------

def test_drawer_body_clears_opening_width():
    gap = c.OPENING_WIDTH - c.DRAWER_BODY["width"]
    assert gap >= 2 * SPEC_MIN_SLIDE_PLAY - 1e-9, (
        f"drawer body {c.DRAWER_BODY['width']} needs >= {2 * SPEC_MIN_SLIDE_PLAY} "
        f"total width clearance in opening {c.OPENING_WIDTH}, got {gap}"
    )


def test_drawer_body_clears_opening_height():
    gap = c.OPENING_HEIGHT - c.DRAWER_BODY["height"]
    assert gap >= SPEC_MIN_SLIDE_PLAY - 1e-9


def test_drawer_body_fits_slot_height():
    gap = c.DRAWER_SLOT_HEIGHT - c.DRAWER_BODY["height"]
    assert gap >= SPEC_MIN_SLIDE_PLAY - 1e-9


def test_drawer_body_fits_bay_length():
    gap = c.BAY_LENGTH - c.DRAWER_BODY["length"]
    assert 0 < gap < 5.0, "drawer should nearly fill the bay when closed"


def test_drawer_body_fits_bay_width():
    assert c.DRAWER_BODY["width"] <= c.INTERIOR_WIDTH - 2 * SPEC_MIN_SLIDE_PLAY


def test_faceplate_fills_opening_with_reveal():
    reveal_w = (c.OPENING_WIDTH - c.FACEPLATE["width"]) / 2
    reveal_h = (c.OPENING_HEIGHT - c.FACEPLATE["height"]) / 2
    assert 0.5 <= reveal_w <= 1.0
    assert 0.5 <= reveal_h <= 1.0


def test_faceplate_covers_drawer_body():
    assert c.FACEPLATE["width"] >= c.DRAWER_BODY["width"]
    assert c.FACEPLATE["height"] >= c.DRAWER_BODY["height"] - 1e-9


def test_total_drawer_length_within_spec_target():
    """SPEC target 9" external is 'to fit'; body+faceplate must not exceed it."""
    total = c.DRAWER_BODY["length"] + c.T
    assert total <= 228.6
    assert total > 200.0, "drawer should use most of the bay depth"


# --- Rear wall openings: sill-free and structurally sound ----------------------

def test_openings_are_sill_free():
    """Opening floors must be exactly at bay floor / shelf top or drawers catch."""
    assert c.BOTTOM_OPENING_Z0 == pytest.approx(c.FLOOR_TOP, **APPROX)
    assert c.TOP_OPENING_Z0 == pytest.approx(c.SHELF_Z1, **APPROX)


def test_openings_stay_within_their_slots():
    assert c.BOTTOM_OPENING_Z1 <= c.SHELF_Z0
    assert c.TOP_OPENING_Z1 <= c.TOP_PANEL_Z0


def test_rear_wall_webs_are_structural():
    web_below_bottom = c.BOTTOM_OPENING_Z0 - c.WALL_Z0  # backed by the inset panel
    web_below_shelf = c.SHELF_Z0 - c.BOTTOM_OPENING_Z1
    web_above_top = c.TOP_PANEL_Z0 - c.TOP_OPENING_Z1
    side_web = (c.INTERIOR_WIDTH - c.OPENING_WIDTH) / 2 + c.T
    for name, web in [("below bottom opening", web_below_bottom),
                      ("below shelf", web_below_shelf),
                      ("above top opening", web_above_top),
                      ("beside openings", side_web)]:
        assert web >= c.MIN_WEB, f"web {name} = {web} < {c.MIN_WEB}"


# --- Divider and shelf joinery ---------------------------------------------------

def test_divider_is_full_height_to_top_panel():
    """SPEC: divider is structural; it must reach the top panel underside."""
    assert c.DIVIDER_TOP == pytest.approx(c.TOP_PANEL_Z0, **APPROX)
    assert c.DIVIDER_HEIGHT == pytest.approx(c.TOP_PANEL_Z0 - c.FLOOR_TOP, **APPROX)


def test_divider_blocks_lid_slot_band():
    """Divider must span past the lid slot top so it can stop the lid."""
    assert c.DIVIDER_TOP >= c.LID_SLOT_TOP


def test_shelf_spans_bay_exactly():
    # nominal shelf length equals bay interior length (fingers extend beyond)
    assert c.BAY_LENGTH == pytest.approx(c.BAY_X1 - c.BAY_X0, **APPROX)
    assert c.SHELF_Z1 - c.SHELF_Z0 == pytest.approx(c.T, **APPROX)


# --- Sliding lid -------------------------------------------------------------------

def test_lid_slot_geometry():
    assert c.LID_SLOT_HEIGHT == pytest.approx(c.T + 0.8, **APPROX)
    assert c.LID_SLOT_TOP - c.LID_SLOT_BOTTOM == pytest.approx(c.LID_SLOT_HEIGHT, **APPROX)
    assert c.LID_RAIL_HEIGHT >= 3.0, "rail above slot must be sturdy enough"
    assert c.LID_SLOT_X_END == pytest.approx(c.DIVIDER_X0, **APPROX), (
        "slot must end at the divider face so the divider is the lid stop"
    )


def test_front_wall_top_is_slot_bottom():
    assert c.FRONT_WALL_TOP == pytest.approx(c.LID_SLOT_BOTTOM, **APPROX)
    assert c.FRONT_WALL_HEIGHT == pytest.approx(c.FRONT_WALL_TOP, **APPROX), (
        "front wall runs from Z=0 (walls full height, bottom panel inset)"
    )


def test_lid_engages_both_slots_with_play():
    play = c.SHELL_EXT["width"] - c.SLIDING_LID["width"]
    assert play >= SPEC_MIN_SLIDE_PLAY - 1e-9
    engagement = (c.SLIDING_LID["width"] - c.INTERIOR_WIDTH) / 2
    assert engagement >= 2.0, f"lid engages only {engagement}mm per slot"
    assert engagement <= c.T, "lid cannot stick out past the exterior faces"


def test_lid_covers_paper_compartment():
    assert c.SLIDING_LID["length"] <= c.LID_SLOT_X_END
    # closed lid front edge within 1mm of the front face
    assert c.LID_SLOT_X_END - c.SLIDING_LID["length"] <= 1.0


def test_lid_clears_rail_and_top_panel():
    """Lid must ride below the rail strip and below the top panel zone."""
    lid_top_when_riding = c.LID_SLOT_BOTTOM + c.T
    assert lid_top_when_riding < c.LID_SLOT_TOP
    assert c.LID_SLOT_TOP <= c.TOP_PANEL_Z0


# --- Bottom panel ---------------------------------------------------------------

def test_bottom_panel_inset_between_full_height_walls():
    """DESIGN.md amendment: full-height walls, bottom panel inset between them
    (gives the rear wall a solid web under its sill-free openings)."""
    assert c.WALL_Z0 == pytest.approx(0.0, **APPROX)
    assert c.WALL_HEIGHT == pytest.approx(SPEC_HEIGHT, **APPROX)
    assert c.FLOOR_TOP == pytest.approx(c.T, **APPROX)


# --- Sanity: derived interior values ----------------------------------------------

def test_interior_dimensions():
    assert c.INTERIOR_LENGTH == pytest.approx(SPEC_LENGTH - 2 * c.T, **APPROX)
    assert c.INTERIOR_WIDTH == pytest.approx(SPEC_WIDTH - 2 * c.T, **APPROX)
    assert c.BAY_INTERIOR_HEIGHT == pytest.approx(SPEC_HEIGHT - 2 * c.T, **APPROX)
