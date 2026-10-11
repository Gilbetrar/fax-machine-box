"""Laser-rule and placement checks for the code-drawn engraving art
(art/code/, built by `art/code/build.py`).

Every variant SVG listed in art/code/manifest.json is re-rendered from the
SVG itself (cairosvg, 20 px/mm = 0.05 mm/px) and measured, so these tests
check what a laser would actually receive, not the build's intermediate
bitmaps.

Rules (see art/code/faxart/raster.py):
  - min engraved line 0.25 mm and min unburned gap 0.30 mm PER FEATURE:
    rendered at 40 px/mm, exact Euclidean opening of the ink (0.25 mm disk)
    and of the paper (0.30 mm disk); every connected sliver >= 0.02 mm2 fails
    (faxart/rules.py; the build's repair loop uses the same function)
  - no specks: islands / pinholes < 0.09 mm^2 (allow a handful from curve
                                 smoothing at the 0.05 mm render grid)
  - ink coverage per face within a sane band, dense (> 80 % in a 3 mm
    window) area capped except where display lettering is solid by design
  - in the art frame, no ink within 0.55 mm of the nominal cut outline
    (keep-out 0.65 mm at build); the shipped rule, >= 0.35 mm from the
    burnt edge, is checked on the exported sheets by test_engrave_cutfiles
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
from faxart import rules  # noqa: E402
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


@lru_cache(maxsize=None)
def violations_of(svg_rel: str):
    return rules.violations(rasterize_svg(ART / svg_rel, rules.RULE_PPM))


@pytest.mark.parametrize("fid,v", VARIANTS, ids=IDS)
def test_no_thin_feature(fid, v):
    """Per feature (red-team pass 1, A8): no connected sliver of ink narrower
    than 0.25 mm and >= 0.02 mm2 anywhere, measured at 40 px/mm with exact
    Euclidean morphology."""
    _, _, n_thin, _ = violations_of(v["svg"])
    assert n_thin == 0, f"{n_thin} ink features thinner than 0.25 mm"


@pytest.mark.parametrize("fid,v", VARIANTS, ids=IDS)
def test_no_narrow_gap(fid, v):
    """Per feature: no connected unburned gap narrower than 0.30 mm and
    >= 0.02 mm2 (these char shut)."""
    _, _, _, n_gap = violations_of(v["svg"])
    assert n_gap == 0, f"{n_gap} gaps narrower than 0.30 mm"


@lru_cache(maxsize=None)
def ink40(svg_rel: str) -> np.ndarray:
    return rasterize_svg(ART / svg_rel, 40.0)


@pytest.mark.parametrize("fid,v", VARIANTS, ids=IDS)
def test_redteam_closing_gap_check(fid, v):
    """Red-team pass 2's own method, reproduced exactly (art-2/scripts/
    analyze.py): close the engraving with a cv2 13 px ellipse at 40 px/mm,
    keep what it adds inside the wood, and fail any piece > 0.03 mm2. This
    is the check the per-feature test missed before pass 2."""
    E = ink40(v["svg"])
    mat = material_mask(fid, 40.0)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))
    closed = cv2.morphologyEx(E.astype(np.uint8), cv2.MORPH_CLOSE, k).astype(bool)
    n, _, st, _ = cv2.connectedComponentsWithStats((closed & mat & ~E).astype(np.uint8), connectivity=8)
    big = int((st[1:, cv2.CC_STAT_AREA] > 0.03 * 1600).sum())
    assert big == 0, f"{big} narrow gaps (cv2 13 px closing) over 0.03 mm2"


@pytest.mark.parametrize("fid,v", VARIANTS, ids=IDS)
def test_redteam_opening_thin_check(fid, v):
    """Same, for thin strands: cv2 11 px opening at 40 px/mm."""
    E = ink40(v["svg"])
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    op = cv2.morphologyEx(E.astype(np.uint8), cv2.MORPH_OPEN, k).astype(bool)
    n, _, st, _ = cv2.connectedComponentsWithStats((E & ~op).astype(np.uint8), connectivity=8)
    big = int((st[1:, cv2.CC_STAT_AREA] > 0.03 * 1600).sum())
    assert big == 0, f"{big} thin strands (cv2 11 px opening) over 0.03 mm2"


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
    mat = material_mask(fid, PPM, 0.55)
    bad = int((ink & ~mat).sum())
    assert bad <= 40, f"{bad} px ({bad / PPM ** 2:.2f} mm2) of ink within 0.55 mm of a cut"


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


# --- the art AS EXPORTED --------------------------------------------------------------------------
# faxbox.cutset places the art on each part and trims it back from the burnt
# edge wherever a thickness moves a slot or hole under it. Trimming can leave
# hairlines (final verification: 0.25 x 6.7 mm beside the POOS ON ROUGE frame),
# so the same per-feature rules are checked on the trimmed art, at the
# thinnest, nominal and thickest stock and the smallest and largest kerf.

import subprocess  # noqa: E402

TRIM_CHECK = ART / "tools" / "trimmed_check.py"


@lru_cache(maxsize=None)
def trimmed_results(T: float):
    env = dict(__import__("os").environ, FAXBOX_THICKNESS=str(T), PYTHONPATH=str(REPO / "src"))
    out = subprocess.run([sys.executable, str(TRIM_CHECK), "0.12", "0.20"], env=env,
                         capture_output=True, text=True, check=True, cwd=str(REPO)).stdout
    return [json.loads(l) for l in out.splitlines() if l.startswith("{")]


@pytest.mark.parametrize("T", [2.8, 3.2, 3.5])
def test_exported_art_has_no_thin_or_narrow_features(T):
    rows = trimmed_results(T)
    assert len(rows) == 2 * sum(len(f["variants"]) for f in MANIFEST["faces"].values())
    bad = [(r["kerf"], r["face"], r["variant"], r["thin"], r["gap"], r["thin_at"][:2], r["gap_at"][:2])
           for r in rows if r["thin"] or r["gap"]]
    assert not bad, bad
