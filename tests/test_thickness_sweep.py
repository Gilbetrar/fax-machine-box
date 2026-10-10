"""The 3D checks at the ends of the stock range (red-team: re-run the full 3D
verification at T = 2.8, 3.175 and 3.5).  The geometry reads FAXBOX_THICKNESS
at import, so each thickness runs in its own process.  3.175 is what the rest of
the suite already runs at."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FILES = ["tests/test_assembly3d.py", "tests/test_orientation.py", "tests/test_geometry_v2.py"]


@pytest.mark.parametrize("t", [2.8, 3.5])
def test_3d_assembly_orientation_and_geometry_at_thickness(t):
    env = dict(os.environ, FAXBOX_THICKNESS=str(t), PYTHONPATH=str(ROOT / "src"))
    r = subprocess.run([sys.executable, "-m", "pytest", *FILES, "-q", "-x", "-p", "no:cacheprovider"],
                       env=env, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, (r.stdout + r.stderr)[-3000:]
