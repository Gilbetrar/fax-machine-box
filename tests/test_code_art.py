"""Laser-rule and placement checks for the code-drawn engraving art
(art/code/, built by `art/code/build.py`).

Every variant SVG listed in art/code/manifest.json is re-rendered from the
SVG itself (cairosvg, 20 px/mm = 0.05 mm/px) and measured, so these tests
check what a laser would actually receive, not the build's intermediate
bitmaps.

Rules (see art/code/faxart/raster.py):
  - min engraved line 0.25 mm   (morphological opening by a 5 px = 0.25 mm
                                 disk removes < 0.3 % of the ink, counting
                                 slivers >= 0.05 mm2; corner nibbles excluded)
  - min unburned gap 0.30 mm    (closing by a 7 px = 0.35 mm disk, stricter
                                 than the rule, adds < 0.3 % in slivers; kernels are odd
                                 because an even cv2 kernel is off-centre)
  - no specks: islands / pinholes < 0.09 mm^2 (allow a handful from curve
                                 smoothing at the 0.05 mm render grid)
  - ink coverage per face within a sane band, dense (> 80 % in a 3 mm
    window) area capped except where display lettering is solid by design
  - no ink within 0.35 mm of any through-cut (keep-out is 0.5 mm at build)
  - every SVG is exactly its part's nominal blank in mm, and the blank sits
    inside the generator's drawn piece.
"""

from __future__ import annotations

import json
import re
import sys
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
import pytest

REPO = Path(__file__).resolve().parent.parent
ART = REPO / "art" / "code"
sys.path.insert(0, str(ART))

from faxart.geometry import FACES, material_mask, part, size_mm  # noqa: E402
from faxart.vector import rasterize_svg  # noqa: E402

PPM = 20.0
MANIFEST = json.loads((ART / "manifest.json").read_text())

VARIANTS = [(fid, v) for fid, f in MANIFEST["faces"].items() for v in f["variants"]]
IDS = [f"{fid}__{v['id']}" for fid, v in VARIANTS]

# faces whose display lettering is solid black on purpose (Ben's style);
# their dense-area cap is higher
SOLID_LETTERING = {"left__solid", "right__funfor", "right__nofunfor", "front__traced"}


@lru_cache(maxsize=None)
def ink_of(svg_rel: str) -> np.ndarray:
    return rasterize_svg(ART / svg_rel, PPM)


def disk(d):
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d, d))


def blobs_over(diff: np.ndarray, min_px: int = 20) -> int:
    """Pixels in connected pieces of `diff` of at least min_px (0.05 mm2).
    Morphology always nibbles a few px at sharp corners and hatch crossings;
    a real sub-minimum line or gap is a longer sliver that shows up as a
    larger piece."""
    n, _, st, _ = cv2.connectedComponentsWithStats(diff.astype(np.uint8), connectivity=8)
    a = st[1:, cv2.CC_STAT_AREA]
    return int(a[a >= min_px].sum())


def test_manifest_covers_every_face():
    assert set(MANIFEST["faces"]) == set(FACES)
    for fid, f in MANIFEST["faces"].items():
        assert f["part_id"] == fid
        assert sum(v["default"] for v in f["variants"]) == 1, fid
        for v in f["variants"]:
            assert (ART / v["svg"]).exists() and (ART / v["png"]).exists()


def test_required_variants_present():
    ids = {fid: {v["id"] for v in f["variants"]} for fid, f in MANIFEST["faces"].items()}
    assert {"solid", "outline"} <= ids["left"]
    assert {"funfor", "nofunfor"} <= ids["right"]
    assert {"a", "c"} <= ids["lid"]
    assert {"a", "c"} <= ids["top"]


@pytest.mark.parametrize("fid,v", VARIANTS, ids=IDS)
def test_svg_size_matches_part(fid, v):
    txt = (ART / v["svg"]).read_text()
    w, h = (float(x) for x in re.search(r'width="([\d.]+)mm" height="([\d.]+)mm"', txt).groups())
    W, H = size_mm(fid)
    assert abs(w - W) < 1e-3 and abs(h - H) < 1e-3
    assert f'viewBox="0 0 {W:.3f} {H:.3f}"' in txt
    # the canvas is the part's NOMINAL rectangle in faxbox.partgeom
    g = part(fid)
    assert abs(g.width - W) < 1e-3 and abs(g.height - H) < 1e-3
    assert MANIFEST["faces"][fid]["size_mm"] == [W, H]


@pytest.mark.parametrize("fid,v", VARIANTS, ids=IDS)
def test_png_preview(fid, v):
    from PIL import Image
    assert Image.open(ART / v["png"]).width == 1200


@pytest.mark.parametrize("fid,v", VARIANTS, ids=IDS)
def test_min_line_width(fid, v):
    ink = ink_of(v["svg"])
    opened = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_OPEN, disk(5)).astype(bool)
    lost = blobs_over(ink & ~opened) / max(1, ink.sum())
    assert lost < 0.003, f"{lost:.3%} of ink is in features thinner than 0.25 mm"


@pytest.mark.parametrize("fid,v", VARIANTS, ids=IDS)
def test_min_gap(fid, v):
    ink = ink_of(v["svg"])
    closed = cv2.morphologyEx(ink.astype(np.uint8), cv2.MORPH_CLOSE, disk(7)).astype(bool)
    added = blobs_over(closed & ~ink) / max(1, ink.sum())
    assert added < 0.003, f"gaps under 0.35 mm would add {added:.3%} more burn"


@pytest.mark.parametrize("fid,v", VARIANTS, ids=IDS)
def test_no_specks(fid, v):
    ink = ink_of(v["svg"]).astype(np.uint8)
    min_px = 0.09 * PPM * PPM
    specks = 0
    for m in (ink, 1 - ink):
        n, _, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
        specks += int((st[1:, cv2.CC_STAT_AREA] < min_px).sum())
    assert specks <= 5, f"{specks} islands/pinholes under 0.09 mm2"


@pytest.mark.parametrize("fid,v", VARIANTS, ids=IDS)
def test_ink_coverage_and_density(fid, v):
    ink = ink_of(v["svg"])
    cov = ink.mean()
    assert 0.03 < cov < 0.33, f"ink coverage {cov:.1%}"
    k = int(3 * PPM)
    dens = cv2.blur(ink.astype(np.float32), (k, k))
    dense = (dens > 0.8).mean()
    cap = 0.20 if f"{fid}__{v['id']}" in SOLID_LETTERING else 0.03
    assert dense < cap, f"{dense:.1%} of the face is >80% burned in a 3 mm window"


@pytest.mark.parametrize("fid,v", VARIANTS, ids=IDS)
def test_clear_of_cuts(fid, v):
    ink = ink_of(v["svg"])
    mat = material_mask(fid, PPM, 0.35)
    bad = int((ink & ~mat).sum())
    assert bad <= 40, f"{bad} px ({bad / PPM ** 2:.2f} mm2) of ink within 0.35 mm of a cut"


PARTS = {p["id"]: p for p in json.loads((REPO / "site" / "data" / "parts.json").read_text())["parts"]}


def test_face_ids_are_site_part_ids():
    for fid, f in MANIFEST["faces"].items():
        assert fid in PARTS, fid
        assert f["exterior_face"] == PARTS[fid]["exterior_face"], fid
        assert f["engrave_part_flipped"] == PARTS[fid]["outline_mirrored_when_viewed_from_exterior"]


def test_art_frame_vectors():
    """art_up / art_right are unit box vectors at right angles, and for every
    vertical face the art is upright (up = +Z)."""
    for fid, f in MANIFEST["faces"].items():
        up, right = np.array(f["art_up"]), np.array(f["art_right"])
        assert abs(np.linalg.norm(up) - 1) < 1e-6 and abs(np.linalg.norm(right) - 1) < 1e-6
        assert abs(up @ right) < 1e-6
        if fid not in ("lid", "top"):
            assert list(up) == [0, 0, 1], fid
    assert MANIFEST["faces"]["lid"]["art_right"] == [1, 0, 0]     # front -> rear
    assert MANIFEST["faces"]["top"]["art_up"] == MANIFEST["faces"]["lid"]["art_up"]
