"""Per-face recipes. Each returns a list of finish.Variant."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from . import raster as R
from .finish import Variant, finish
from .geometry import size_mm
from .photo import build_photo_face

REPO = Path(__file__).resolve().parents[3]
TRIM = REPO / "art" / "trimmed"
FINAL = REPO / "art" / "ai-versions" / "final"


def canvas_shape(face_id):
    w, h = size_mm(face_id)
    return int(round(h * R.PPM)), int(round(w * R.PPM))


# ------------------------------------------------------------------ drawer sides
# Source = Ben's original photos (art/trimmed/), one continuous drawing per
# side, so there is no seam to fix. The cardboard's top/bottom edges were
# fitted as quadratics y(x) in trimmed-photo px (tools/find_edges.py, checked
# by eye on the overlays) and the panel is unrolled between them
# (raster.warp_strip). The small aspect difference to the 4.22:1 wooden panel
# (3.9-4.2:1 in the photos) is taken as a mild horizontal stretch.

DRAWER_SIDES = {
    "B_left": dict(src="IMG_4233", x=(0, 3885),
                          top=[1.8e-06, -0.01182261, 40.6], bot=[-3.43e-06, -0.02692512, 1031.17],
                          inset=(20, 12), ink_t=0.42, tone_ths=(0.22, 0.32, 0.45),
                          colour_line_kw=dict(sat_t=0.5), seed=11,
                          # the sun (top right) stays an outline: hatching made it a striped half-disc
                          tone_exclude=[[(188, 0), (212.25, 0), (212.25, 27), (188, 27)]]),
    "B_right": dict(src="IMG_4235", x=(0, 3225),
                          top=[-2.49e-06, 0.01411701, 3.37], bot=[3.62e-06, -0.03796397, 832.75],
                          inset=(14, 10), ink_t=0.5, tone_ths=(0.18, 0.30, 0.42),
                          colour_line_kw=None, seed=12),
    "T_left": dict(src="IMG_4237", x=(0, 3770),
                          top=[1.92e-06, -0.01088373, 23.53], bot=[2.71e-06, -0.03814268, 968.35],
                          inset=(8, 10), ink_t=0.45, tone_ths=(0.24, 0.37, 0.50),
                          colour_line_kw=None, seed=13,
                          # short strokes in every direction read as pencil sky, not rain
                          hatch_kw=dict(stroke_mm=(1.2, 3.0), jitter_deg=28.0, lift_mm=(0.5, 1.2))),
    "T_right": dict(src="IMG_4239", x=(12, 3725),
                          top=[2.1e-06, -0.00685499, 30.25], bot=[5.98e-06, -0.03640593, 939.44],
                          inset=(10, 10), ink_t=0.48, tone_ths=(0.20, 0.32, 0.45),
                          colour_line_kw=None, seed=14,
                          # the bookshelf: leave the spines unhatched so every title reads
                          tone_exclude=[[(112, 0), (212.25, 0), (212.25, 50.4), (146, 50.4)]],
                          line_grow_mm=0.0),    # the crowded shelf: no extra weight or it fills in
}


def drawer_side(face_id: str) -> list[Variant]:
    c = DRAWER_SIDES[face_id]
    img = cv2.imread(str(TRIM / f"{c['src']}.jpeg"))
    can = R.warp_strip(img, c["x"], c["top"], c["bot"], size_mm(face_id), c["inset"])
    W, H = size_mm(face_id)
    excl = None
    if c.get("tone_exclude"):
        excl = np.zeros((int(round(H * R.PPM)), int(round(W * R.PPM))), np.uint8)
        for poly in c["tone_exclude"]:
            cv2.fillPoly(excl, [np.round(np.array(poly) * R.PPM).astype(np.int32)], 1)
        excl = excl.astype(bool)
    layers = build_photo_face(can, ink_t=c["ink_t"], tone_ths=c["tone_ths"],
                              colour_line_kw=c["colour_line_kw"], seed=c["seed"],
                              tone_exclude=excl, hatch_kw=c.get("hatch_kw"),
                              line_grow_mm=c.get("line_grow_mm", 0.1))
    mask = finish(face_id, layers["lines"] | layers["tone"])
    return [Variant("traced", "Hand-drawn scene", mask, default=True,
                    source=f"art/trimmed/{c['src']}.jpeg",
                    notes="Traced from the original cardboard box. The colored-pencil shading "
                          "becomes hatching.")]


RECIPES = {k: drawer_side for k in DRAWER_SIDES}
