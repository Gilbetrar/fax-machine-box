"""Pytest configuration for fax machine box tests.

Tests import faxbox.config directly; DESIGN.md is the geometry authority.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = str(REPO_ROOT / "src")

# Force THIS repo's src/ onto every subprocess's import path (ported from
# issue #20 iteration-3, red-team FIX4): faxbox is normally installed
# editable (`pip install -e .`), which points at wherever the venv was
# created, not necessarily this checkout. In a git WORKTREE (a second
# checkout of the same repo on a different branch/path), that editable
# install still resolves to the ORIGINAL checkout's src/ -- meaning `python
# -m faxbox.<generator>` subprocess calls (here AND in test_layout.py's own
# regeneration fixtures) would silently regenerate SVGs from the WRONG
# tree's code, and every test in the suite would then measure geometry the
# diff under review never touched.
#
# Mutating os.environ directly (rather than building a local env dict some
# call sites would have to remember to pass) makes this a session-wide fix:
# every `subprocess.run(...)` anywhere in this test session that does NOT
# pass its own `env=` (which is all of them, in this suite) inherits
# os.environ by default, so THIS checkout's src/ takes precedence
# everywhere, not just in the fixture below.
os.environ["PYTHONPATH"] = SRC_DIR + os.pathsep + os.environ.get("PYTHONPATH", "")

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
