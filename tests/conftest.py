"""Pytest configuration for fax machine box tests.

Tests import faxbox.config directly; DESIGN.md is the geometry authority.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# The three generator entry points (issue #16 verification procedure). Run in
# this order via `sys.executable -m <module>` -- same as a human would from
# the README -- so the fixture exercises exactly what ships, not an in-process
# shortcut that could mask import/CLI-arg bugs.
GENERATOR_MODULES = [
    "faxbox.shell_generator",
    "faxbox.generate_drawers",
    "faxbox.generate_lids",
]


@pytest.fixture(scope="session")
def regenerate_svgs():
    """Regenerate output/*.svg from current source before geometry/laser
    tests run, so those tests always measure current code rather than stale
    files left over from a previous run or a hand edit.

    Session-scoped: runs once per test session, not once per test function.
    Tests that need it opt in with `pytestmark =
    [pytest.mark.usefixtures("regenerate_svgs")]` rather than this being
    autouse, so unrelated tests (e.g. test_assembly_fit.py, which only checks
    faxbox.config numbers) aren't slowed down by three subprocess calls.
    """
    for module in GENERATOR_MODULES:
        subprocess.run(
            [sys.executable, "-m", module],
            check=True,
            cwd=REPO_ROOT,
            capture_output=True,
        )
