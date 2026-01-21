"""Pytest configuration and fixtures for fax machine box tests."""

import pytest

from faxbox.config import (
    DRAWER,
    DRAWER_CLEARANCE,
    DRAWER_MATERIAL_THICKNESS,
    LID_GROOVE_DEPTH,
    LID_GROOVE_WIDTH,
    LID_TAB_CLEARANCE,
    MATERIAL_THICKNESS,
    PAPER_COMPARTMENT_DEPTH,
    SHELL,
    SLIDING_LID_TAB_DEPTH,
)


@pytest.fixture
def shell_dims():
    """External shell dimensions."""
    return SHELL.copy()


@pytest.fixture
def drawer_dims():
    """Internal drawer dimensions."""
    return DRAWER.copy()


@pytest.fixture
def material_thickness():
    """Standard material thickness."""
    return DRAWER_MATERIAL_THICKNESS


@pytest.fixture
def drawer_clearance():
    """Clearance per side for drawer sliding."""
    return DRAWER_CLEARANCE


@pytest.fixture
def paper_compartment_depth():
    """Depth of paper compartment from front."""
    return PAPER_COMPARTMENT_DEPTH


@pytest.fixture
def lid_groove_width():
    """Width of lid groove in wall."""
    return LID_GROOVE_WIDTH


@pytest.fixture
def lid_groove_depth():
    """Depth of lid groove in wall."""
    return LID_GROOVE_DEPTH


@pytest.fixture
def lid_tab_clearance():
    """Clearance for lid tabs."""
    return LID_TAB_CLEARANCE


@pytest.fixture
def sliding_lid_tab_depth():
    """Depth of sliding lid tab."""
    return SLIDING_LID_TAB_DEPTH
