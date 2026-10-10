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

from faxart.geometry import FACES, material_mask, piece_for, regenerate_svgs  # noqa: E402
from faxart.vector import rasterize_svg  # noqa: E402

PPM = 20.0
MANIFEST = json.loads((ART / "manifest.json").read_text())

VARIANTS = [(fid, v) for fid, f in MANIFEST["faces"].items() for v in f["variants"]]
IDS = [f"{fid}__{v['id']}" for fid, v in VARIANTS]

# faces whose display lettering is solid black on purpose (Ben's style);
# their dense-area cap is higher
SOLID_LETTERING = {"left_wall__solid", "right_wall__funfor", "right_wall__nofunfor", "front_wall__traced"}


@pytest.fixture(scope="module", autouse=True)
def _svgs():
    regenerate_svgs()


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
    assert {"solid", "outline"} <= ids["left_wall"]
    assert {"funfor", "nofunfor"} <= ids["right_wall"]
    assert {"a", "c"} <= ids["sliding_lid"]
    assert {"a", "c"} <= ids["top_panel"]


@pytest.mark.parametrize("fid,v", VARIANTS, ids=IDS)
def test_svg_size_matches_part(fid, v):
    txt = (ART / v["svg"]).read_text()
    w, h = (float(x) for x in re.search(r'width="([\d.]+)mm" height="([\d.]+)mm"', txt).groups())
    W, H = FACES[fid].size_mm
    assert abs(w - W) < 1e-3 and abs(h - H) < 1e-3
    assert f'viewBox="0 0 {W:.3f} {H:.3f}"' in txt
    # nominal blank inside the drawn piece (which also carries finger tabs)
    bb = piece_for(fid).bbox
    assert W <= bb.width + 0.01 and H <= bb.height + 0.01
    # proof renderer uses the same nominal sizes
    sys.path.insert(0, str(REPO / "scripts"))
    import art_proofs  # noqa: E402
    spec = {s.key: s for s in art_proofs.PART_SPECS}[fid]
    assert spec.nominal_mm == FACES[fid].size_mm


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
