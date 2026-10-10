"""site/data/parts.json export (scripts/export_site_data.py)."""

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from faxbox import assembly3d as a3
from faxbox import config as c

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def data():
    return a3.site_data()


def test_schema(data):
    assert {"box", "parts", "steps", "inventory"} <= set(data)
    assert data["box"]["length"] == pytest.approx(304.8)
    assert len(data["parts"]) == 21
    for p in data["parts"]:
        for k in ("id", "name", "letter", "outline", "holes", "thickness", "transform", "color",
                  "assembly_step", "insert_direction", "exterior_face"):
            assert k in p, (p["id"], k)
        assert len(p["transform"]) == 4 and all(len(r) == 4 for r in p["transform"])
        assert p["exterior_face"] in ("+", "-")
        assert len(p["insert_direction"]) == 3


def test_every_part_is_in_exactly_the_steps_it_names(data):
    ids = {p["id"] for p in data["parts"]}
    for p in data["parts"]:
        st = data["steps"][p["assembly_step"] - 1]
        assert p["id"] in st["parts"]
        assert st["insert_direction"] == p["insert_direction"]
    listed = {pid for s in data["steps"] for pid in s["parts"]}
    assert listed == ids


def test_transform_places_outline_inside_the_box(data):
    for p in data["parts"]:
        m = np.array(p["transform"])
        pts = np.array([[x, y, 0, 1] for x, y in p["outline"]]) @ m.T
        assert pts[:, 0].min() >= -1e-6 and pts[:, 0].max() <= c.SHELL_EXT["length"] + 1e-6
        assert pts[:, 1].min() >= -1e-6 and pts[:, 1].max() <= c.SHELL_EXT["width"] + 1e-6
        assert pts[:, 2].min() >= -1e-6 and pts[:, 2].max() <= c.SHELL_EXT["height"] + 1e-6


def test_outline_and_holes_are_valid_shapes(data):
    from shapely.geometry import Polygon
    for p in data["parts"]:
        poly = Polygon(p["outline"], p["holes"])
        assert poly.is_valid, p["id"]


def test_letters_match_inventory(data):
    inv = {i["letter"]: i["quantity"] for i in data["inventory"]}
    for letter, qty in inv.items():
        assert sum(1 for p in data["parts"] if p["letter"] == letter) == qty


def test_export_script_is_deterministic(tmp_path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    for out in (a, b):
        subprocess.run([sys.executable, str(ROOT / "scripts" / "export_site_data.py"), str(out)],
                       check=True, capture_output=True)
    assert a.read_bytes() == b.read_bytes()
    json.loads(a.read_text())
