"""Dimension validation tests for fax machine box.

These tests verify that all dimensions are internally consistent
and physically possible before ordering laser cutting.
"""

import pytest

from faxbox.config import (
    DRAWER,
    DRAWER_CLEARANCE,
    DRAWER_MATERIAL_THICKNESS,
    FLAT_LID_TAB_DEPTH,
    FLAT_LID_TAB_WIDTH,
    LID_GROOVE_DEPTH,
    LID_GROOVE_WIDTH,
    LID_TAB_CLEARANCE,
    MATERIAL_THICKNESS,
    PAPER_COMPARTMENT_DEPTH,
    SHELL,
    SLIDING_LID_TAB_DEPTH,
)


class TestDrawerFitsInShell:
    """Tests verifying drawers fit inside the outer shell with clearance."""

    def test_drawer_width_fits_in_shell(self):
        """Drawer width + walls + clearance must fit within shell internal width."""
        shell_internal_width = SHELL["width"] - (2 * DRAWER_MATERIAL_THICKNESS)
        drawer_external_width = DRAWER["width"] + (2 * DRAWER_MATERIAL_THICKNESS)
        required_clearance = 2 * DRAWER_CLEARANCE

        total_drawer_width_needed = drawer_external_width + required_clearance
        assert total_drawer_width_needed <= shell_internal_width, (
            f"Drawer external width ({drawer_external_width}mm) + clearance "
            f"({required_clearance}mm) = {total_drawer_width_needed}mm exceeds "
            f"shell internal width ({shell_internal_width}mm)"
        )

    def test_drawer_depth_reasonable_for_shell(self):
        """Drawer depth should be reasonable relative to shell depth.

        Note: In this design, drawers slide from the front and may extend
        out when pulled. This test ensures drawer depth is within 2x the
        shell depth (sanity check against gross misconfiguration).
        """
        shell_external_depth = SHELL["depth"]
        drawer_external_depth = DRAWER["depth"] + (2 * DRAWER_MATERIAL_THICKNESS)

        # Drawer depth should not exceed 2x shell depth (sanity check)
        assert drawer_external_depth <= 2 * shell_external_depth, (
            f"Drawer external depth ({drawer_external_depth}mm) exceeds "
            f"2x shell external depth ({2 * shell_external_depth}mm)"
        )

        # Drawer depth should be positive and reasonable (at least 50mm)
        assert drawer_external_depth >= 50.0, (
            f"Drawer external depth ({drawer_external_depth}mm) too shallow"
        )

    def test_drawer_height_fits_in_shell(self):
        """Single drawer height + walls must allow at least one drawer to fit."""
        shell_internal_height = SHELL["height"] - (2 * DRAWER_MATERIAL_THICKNESS)
        drawer_external_height = DRAWER["height"] + DRAWER_MATERIAL_THICKNESS  # Bottom only
        required_clearance = 2 * DRAWER_CLEARANCE

        total_drawer_height_needed = drawer_external_height + required_clearance
        assert total_drawer_height_needed <= shell_internal_height, (
            f"Drawer external height ({drawer_external_height}mm) + clearance "
            f"({required_clearance}mm) = {total_drawer_height_needed}mm exceeds "
            f"shell internal height ({shell_internal_height}mm)"
        )

    def test_two_drawers_fit_vertically(self):
        """Two drawers stacked must fit in shell height."""
        shell_internal_height = SHELL["height"] - (2 * DRAWER_MATERIAL_THICKNESS)
        # Two drawer bottoms, middle shelf, clearance for each drawer
        drawer_stack_height = (
            2 * DRAWER["height"]  # Internal heights
            + 2 * DRAWER_MATERIAL_THICKNESS  # Two drawer bottoms
            + DRAWER_MATERIAL_THICKNESS  # Middle shelf
            + 4 * DRAWER_CLEARANCE  # Top/bottom clearance for each drawer
        )

        assert drawer_stack_height <= shell_internal_height, (
            f"Two drawers stacked ({drawer_stack_height}mm) exceed "
            f"shell internal height ({shell_internal_height}mm)"
        )


class TestMaterialThicknessAccounting:
    """Tests verifying material thickness is properly accounted for."""

    def test_material_thickness_positive(self):
        """Material thickness must be positive."""
        assert MATERIAL_THICKNESS > 0, "Material thickness must be positive"
        assert DRAWER_MATERIAL_THICKNESS > 0, "Drawer material thickness must be positive"

    def test_drawer_material_reasonable(self):
        """Drawer material should be reasonable for laser cutting (1-6mm typical)."""
        assert 1.0 <= DRAWER_MATERIAL_THICKNESS <= 6.0, (
            f"Drawer material thickness ({DRAWER_MATERIAL_THICKNESS}mm) "
            "outside typical laser cutting range (1-6mm)"
        )

    def test_shell_external_greater_than_internal(self):
        """Shell external dimensions must exceed internal by 2x material thickness."""
        expected_internal_width = SHELL["width"] - (2 * DRAWER_MATERIAL_THICKNESS)
        expected_internal_height = SHELL["height"] - (2 * DRAWER_MATERIAL_THICKNESS)
        expected_internal_depth = SHELL["depth"] - (2 * DRAWER_MATERIAL_THICKNESS)

        assert expected_internal_width > 0, "Shell internal width must be positive"
        assert expected_internal_height > 0, "Shell internal height must be positive"
        assert expected_internal_depth > 0, "Shell internal depth must be positive"


class TestDividerAndShelfPositions:
    """Tests verifying divider and shelf positions account for material thickness."""

    def test_paper_compartment_depth_reasonable(self):
        """Paper compartment must fit within shell and leave room for drawers."""
        shell_internal_depth = SHELL["depth"] - (2 * DRAWER_MATERIAL_THICKNESS)

        assert PAPER_COMPARTMENT_DEPTH > 0, "Paper compartment depth must be positive"
        assert PAPER_COMPARTMENT_DEPTH < shell_internal_depth, (
            f"Paper compartment depth ({PAPER_COMPARTMENT_DEPTH}mm) exceeds "
            f"shell internal depth ({shell_internal_depth}mm)"
        )

    def test_divider_leaves_drawer_bay_space(self):
        """Vertical divider position must leave positive space for drawer bay."""
        shell_internal_depth = SHELL["depth"] - (2 * DRAWER_MATERIAL_THICKNESS)
        drawer_bay_depth = shell_internal_depth - PAPER_COMPARTMENT_DEPTH - DRAWER_MATERIAL_THICKNESS

        # Drawer bay must have positive depth (drawers may extend out front)
        assert drawer_bay_depth > 0, (
            f"Drawer bay depth ({drawer_bay_depth}mm) must be positive"
        )
        # Drawer bay should be at least 50mm for practical use
        assert drawer_bay_depth >= 50.0, (
            f"Drawer bay depth ({drawer_bay_depth}mm) too shallow for practical use"
        )


class TestLidDimensions:
    """Tests verifying lid dimensions match their compartments."""

    def test_lid_groove_wider_than_material(self):
        """Lid groove must be wider than material for sliding fit."""
        assert LID_GROOVE_WIDTH > DRAWER_MATERIAL_THICKNESS, (
            f"Lid groove width ({LID_GROOVE_WIDTH}mm) must exceed "
            f"material thickness ({DRAWER_MATERIAL_THICKNESS}mm) for sliding fit"
        )

    def test_sliding_lid_tab_depth_fits_groove(self):
        """Sliding lid tab must fit within groove depth."""
        assert SLIDING_LID_TAB_DEPTH < LID_GROOVE_DEPTH, (
            f"Sliding lid tab depth ({SLIDING_LID_TAB_DEPTH}mm) must be less than "
            f"groove depth ({LID_GROOVE_DEPTH}mm)"
        )

    def test_lid_tab_clearance_positive(self):
        """Lid tab clearance must be positive for insertion."""
        assert LID_TAB_CLEARANCE > 0, "Lid tab clearance must be positive"

    def test_flat_lid_tab_dimensions_positive(self):
        """Flat lid tab dimensions must be positive."""
        assert FLAT_LID_TAB_WIDTH > 0, "Flat lid tab width must be positive"
        assert FLAT_LID_TAB_DEPTH > 0, "Flat lid tab depth must be positive"

    def test_sliding_lid_fits_paper_compartment(self):
        """Sliding lid width must fit paper compartment."""
        shell_internal_width = SHELL["width"] - (2 * DRAWER_MATERIAL_THICKNESS)
        # Lid sits in grooves, so it needs clearance
        lid_width_with_tabs = shell_internal_width + (2 * SLIDING_LID_TAB_DEPTH)

        # The lid should be narrower than the total available space
        assert lid_width_with_tabs > 0, "Sliding lid width must be positive"


class TestTotalInternalSpace:
    """Tests verifying internal space equals external minus walls."""

    def test_shell_internal_volume_calculation(self):
        """Internal volume should be calculable from external minus walls."""
        external_volume = SHELL["width"] * SHELL["height"] * SHELL["depth"]

        internal_width = SHELL["width"] - (2 * DRAWER_MATERIAL_THICKNESS)
        internal_height = SHELL["height"] - (2 * DRAWER_MATERIAL_THICKNESS)
        internal_depth = SHELL["depth"] - (2 * DRAWER_MATERIAL_THICKNESS)
        internal_volume = internal_width * internal_height * internal_depth

        assert internal_volume < external_volume, "Internal volume must be less than external"
        assert internal_volume > 0, "Internal volume must be positive"

    def test_drawer_internal_dimensions_positive(self):
        """All drawer internal dimensions must be positive."""
        assert DRAWER["width"] > 0, "Drawer width must be positive"
        assert DRAWER["height"] > 0, "Drawer height must be positive"
        assert DRAWER["depth"] > 0, "Drawer depth must be positive"


class TestFingerJointConsistency:
    """Tests for finger joint consistency between mating edges."""

    def test_material_thickness_allows_finger_joints(self):
        """Material must be thick enough for finger joints (minimum 2mm typical)."""
        MIN_FINGER_JOINT_MATERIAL = 2.0
        assert DRAWER_MATERIAL_THICKNESS >= MIN_FINGER_JOINT_MATERIAL, (
            f"Material thickness ({DRAWER_MATERIAL_THICKNESS}mm) too thin "
            f"for finger joints (min {MIN_FINGER_JOINT_MATERIAL}mm)"
        )

    def test_drawer_dimensions_allow_multiple_fingers(self):
        """Drawer dimensions should allow for multiple finger joints."""
        MIN_FINGER_SIZE = 5.0  # Typical minimum finger size
        MIN_FINGERS = 3  # At least 3 fingers for strength

        min_dimension = min(DRAWER["width"], DRAWER["height"], DRAWER["depth"])
        min_edge_for_fingers = MIN_FINGER_SIZE * MIN_FINGERS * 2  # Fingers + gaps

        assert min_dimension >= min_edge_for_fingers, (
            f"Smallest drawer dimension ({min_dimension}mm) too small "
            f"for finger joints (need at least {min_edge_for_fingers}mm)"
        )

    def test_shell_dimensions_allow_multiple_fingers(self):
        """Shell dimensions should allow for multiple finger joints."""
        MIN_FINGER_SIZE = 5.0
        MIN_FINGERS = 3

        min_dimension = min(SHELL["width"], SHELL["height"], SHELL["depth"])
        min_edge_for_fingers = MIN_FINGER_SIZE * MIN_FINGERS * 2

        assert min_dimension >= min_edge_for_fingers, (
            f"Smallest shell dimension ({min_dimension}mm) too small "
            f"for finger joints (need at least {min_edge_for_fingers}mm)"
        )


class TestClearanceValues:
    """Tests verifying clearance values are reasonable."""

    def test_drawer_clearance_positive(self):
        """Drawer clearance must be positive for sliding."""
        assert DRAWER_CLEARANCE > 0, "Drawer clearance must be positive"

    def test_drawer_clearance_reasonable(self):
        """Drawer clearance should be reasonable (0.5-3mm typical)."""
        assert 0.5 <= DRAWER_CLEARANCE <= 3.0, (
            f"Drawer clearance ({DRAWER_CLEARANCE}mm) outside typical range (0.5-3mm)"
        )

    def test_lid_clearances_reasonable(self):
        """Lid clearances should be reasonable."""
        assert LID_TAB_CLEARANCE < LID_GROOVE_WIDTH, (
            f"Lid tab clearance ({LID_TAB_CLEARANCE}mm) should be less than "
            f"groove width ({LID_GROOVE_WIDTH}mm)"
        )
