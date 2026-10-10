"""Sliding lid + top panel: one continuous panorama field (front->rear
301.25 x 158.75 mm) cut from the approved IMG_4231 master, split at 79 mm.

Field geometry (same numbers as scripts/art_postprocess.py process_4231, so
the composition matches the July proofs): the master is desheared
x' = x + 0.14157 (y - 1536); the content band is rows 644-2429, cols
295-5416 of the desheared image; it is rotated 180 deg (snake head to the
front) and scaled so its height is exactly 158.75 mm (455.25 mm long). A
301.25 mm window of that strip is the field:
    variant A (snake head): window starts 7.96 mm from the head end
    variant C (full cat):   window starts 153.67 mm (flush with the cat end)

Part frames: top panel local x = field u - 79 (x 0 = front), y = field v.
Lid local x = field u (x 0 = front edge), y = field v + 2.425 (the 158.75 mm
field is centred in the 163.6 mm lid blank; the side strips ride in the
wall slots).
"""

from __future__ import annotations

import cv2
import numpy as np

from . import raster as R
from .ai_faces import finish, load_gray
from .finish import Variant

K = 0.14157
Y_REF = 1536.0
COL1, ROW1 = 5417.0, 2430.0          # one past the content bbox max col / row
S = 158.75 / 1786.0                  # mm per desheared source px
FIELD = (301.25, 158.75)
SPLIT = 79.0
LID_PAD = (163.6 - 158.75) / 2
WINDOWS = {"A": 7.96, "C": 153.67}


def field_affine(w0_mm: float) -> np.ndarray:
    """2x3: master px (x, y) -> field canvas px (rot180 + deshear + scale)."""
    P = R.PPM
    sp = S * P
    # X = ((COL1 - (x + K (y - Y_REF))) * S - w0) * P ;  Y = (ROW1 - y) * S * P
    return np.array([[-sp, -K * sp, (COL1 + K * Y_REF) * sp - w0_mm * P],
                     [0.0, -sp, ROW1 * sp]], np.float64)


def field_ink(variant: str) -> np.ndarray:
    g = R.warp_affine(load_gray("IMG_4231_ai_vT1_master.png"), field_affine(WINDOWS[variant]), FIELD)
    ink = R.threshold_gray(g, 128)
    if variant == "C":
        ink = fill_capsule(ink)
    return ink


# The master carries a blank rounded "grip capsule" left over from the
# abandoned rev-2 composition. Variant C's window keeps it (it lands on the
# top panel) and it reads as an empty pill in the floral wallpaper. Fill it
# by copying the wallpaper from just beside it along the stripe direction.
CAPSULE_C = {"box": (239.5, 72.8, 288.5, 86.8), "copy_dx_mm": -50.0}  # field mm, measured on the C field render


def fill_capsule(ink: np.ndarray) -> np.ndarray:
    box = CAPSULE_C
    if box is None:
        return ink
    x0, y0, x1, y1 = [int(round(v * R.PPM)) for v in box["box"]]
    dx = int(round(box["copy_dx_mm"] * R.PPM))
    out = ink.copy()
    patch = ink[y0:y1, x0 + dx:x1 + dx]
    # feathered pill-shaped paste so the copied stripes meet the old ones
    h, w = y1 - y0, x1 - x0
    m = np.zeros((h, w), np.uint8)
    r = h // 2
    cv2.rectangle(m, (r, 0), (w - r, h - 1), 1, -1)
    cv2.circle(m, (r, r), r, 1, -1)
    cv2.circle(m, (w - r, r), r, 1, -1)
    m = m.astype(bool)
    out[y0:y1, x0:x1] = np.where(m, patch, out[y0:y1, x0:x1])
    return out


def split(ink_field: np.ndarray):
    sp = int(round(SPLIT * R.PPM))
    lid_part = ink_field[:, :sp]
    top = ink_field[:, sp:]
    H = int(round(163.6 * R.PPM))
    lid = np.zeros((H, sp), bool)
    off = int(round(LID_PAD * R.PPM))
    lid[off:off + lid_part.shape[0], :] = lid_part
    return lid, top


SRC = "art/ai-versions/final/IMG_4231_ai_vT1_master.png (approved panorama)"


def _variants(part: str):
    out = []
    for v, label, default, note in [
        ("A", "Snake head (A)", True,
         "Head-anchored window: the mosaic snake head sits on the sliding lid; the cat is trimmed off."),
        ("C", "Full cat (C)", False,
         "Cat-anchored window: the full cat and floral border survive at the rear of the top panel; "
         "the snake head is trimmed. The old blank grip-capsule patch is filled with wallpaper."),
    ]:
        lid, top = split(field_ink(v))
        face = "sliding_lid" if part == "lid" else "top_panel"
        m = lid if part == "lid" else top
        out.append(Variant(v.lower(), label, finish(face, m), default=default, source=SRC, notes=note))
    return out


def sliding_lid(face_id):
    return _variants("lid")


def top_panel(face_id):
    return _variants("top")


RECIPES = {"sliding_lid": sliding_lid, "top_panel": top_panel}
