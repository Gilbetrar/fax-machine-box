"""Cut-file sets (faxbox.cutset, scripts/export_cutfiles.py)."""

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from shapely.geometry import Polygon
from svgpathtools import parse_path

from faxbox import cutset as cs

ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("set")
    info = cs.build_set(out)
    return out, info


def test_every_part_once_per_bed(built):
    out, info = built
    for bed, b in info["beds"].items():
        names = [n for sheet in b["parts"] for n in sheet]
        assert len(names) == 21 == len(set(names)), bed


def test_sheet_counts_are_sensible(built):
    _, info = built
    n = {b: v["sheets"] for b, v in info["beds"].items()}
    assert n["ponoko"] == 2
    assert 3 <= n["generic_600x400"] <= 4
    assert n["xtool_s1"] <= 5 and n["xtool_p2"] <= 5 and n["glowforge_pro"] <= 6


def _outer_polys(svg_path):
    """Largest closed contour of every part group."""
    txt = svg_path.read_text()
    out = []
    for g in re.findall(r"<g id=.*?</g>", txt, flags=re.S):
        best = None
        for d in re.findall(r' d="([^"]+)" fill="none" stroke="rgb\(0,0,255\)"', g):
            pts = [(s.start.real, s.start.imag) for s in parse_path(d)]
            poly = Polygon(pts).buffer(0)
            if best is None or poly.area > best.area:
                best = poly
        out.append(best)
    return out


@pytest.mark.parametrize("bed", ["ponoko", "xtool_s1", "glowforge_pro"])
def test_parts_stay_on_the_bed_and_apart(built, bed):
    out, info = built
    bw, bh, margin, spacing = cs.BEDS[bed]
    for i in range(1, info["beds"][bed]["sheets"] + 1):
        polys = _outer_polys(out / f"{bed}_sheet_{i}.svg")
        for p in polys:
            x0, y0, x1, y1 = p.bounds
            assert x0 >= margin - 0.01 and y0 >= margin - 0.01
            assert x1 <= bw - margin + 0.01 and y1 <= bh - margin + 0.01
        for a in range(len(polys)):
            for b in range(a + 1, len(polys)):
                assert polys[a].distance(polys[b]) >= 3.0, (bed, i, a, b)


def test_dxf_matches_svg_contours(built):
    out, info = built
    for name in ("xtool_s1_sheet_1", "coupon"):
        svg = (out / f"{name}.svg").read_text()
        dxf = (out / f"{name}.dxf").read_text()
        n_svg = len(re.findall(r"<path ", svg))
        # R2000 DXF (units in the header): one LWPOLYLINE per contour
        n_dxf = len(re.findall(r"\nLWPOLYLINE\n", dxf))
        assert "$INSUNITS\n 70\n4" in dxf.replace("\n70\n", "\n 70\n") or "$INSUNITS\n70\n4" in dxf
        assert n_svg == n_dxf
        assert dxf.rstrip().endswith("EOF")


def test_svg_has_only_cut_and_engrave_colours_and_no_text(built):
    out, _ = built
    for f in out.glob("*.svg"):
        txt = f.read_text()
        assert "<text" not in txt
        colours = set(re.findall(r'stroke="([^"]+)"', txt))
        assert colours <= {"rgb(0,0,255)", "rgb(255,0,0)", "#808080"}
        if not f.stem.endswith(("_engrave", "_marked")):
            # red-team G4: the cut-only files are blue lines and nothing else
            assert colours == {"rgb(0,0,255)"}, f.name


def test_coupon_has_all_five_tests(built):
    _, info = built
    names = " ".join(info["coupon_parts"])
    for key in ("kerf square", "thickness slots", "magnet holes", "three-finger corner", "lid slot", "lid strip"):
        assert key in names


@pytest.mark.parametrize("t", [2.8, 3.0, 3.2, 3.5])
def test_geometry_guards_hold_at_each_thickness(t):
    """Chips, ligaments, breakouts at other stock thicknesses (own process:
    the geometry reads FAXBOX_THICKNESS at import)."""
    env = dict(os.environ, FAXBOX_THICKNESS=str(t), PYTHONPATH=str(ROOT / "src"))
    r = subprocess.run([sys.executable, "-m", "pytest", str(ROOT / "tests" / "test_geometry_v2.py"), "-q", "-x"],
                       env=env, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout[-2000:]
