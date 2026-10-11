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
from .geometry import size_mm

K = 0.14157
Y_REF = 1536.0
COL1, ROW1 = 5417.0, 2430.0          # one past the content bbox max col / row
S = 158.75 / 1786.0                  # mm per desheared source px
FIELD = (305.0, 158.75)   # lid + top panel (+ slack); split at the lid length
SPLIT = 79.0
LID_PAD = (163.6 - 158.75) / 2
WINDOWS = {"A": 7.96, "C": 153.67}


def field_affine(w0_mm: float, sx: float = 1.0) -> np.ndarray:
    """2x3: master px (x, y) -> field canvas px (rot180 + deshear + scale),
    with an extra horizontal scale sx about the canvas front edge."""
    P = R.PPM
    sp = S * P
    # X = sx ((COL1 - (x + K (y - Y_REF))) * S - w0) * P ;  Y = (ROW1 - y) * S * P
    return np.array([[-sp * sx, -K * sp * sx, sx * ((COL1 + K * Y_REF) * sp - w0_mm * P)],
                     [0.0, -sp, ROW1 * sp]], np.float64)


# Variant A (snake head): the head is placed so BOTH almond eyes sit on the
# lid, clear of the grip slot (red-team pass 2, B3): the window starts 18 mm
# further toward the head than in July and the lid's share of the strip is
# drawn at 95 % width. The top panel continues the strip at full scale from
# exactly where the lid's share ends, so the picture still runs on across
# the seam (a 5 % width change at a seam that is also a 5.8 mm step).
LID_SQUASH_A = 0.95
A_HEAD_SHIFT = 27.0


TOP_U0 = 79.0   # the top panel's art starts at field u = 79 mm (box geometry)


def split_mm() -> float:
    """Lid length from partgeom (78.0 since the slot-end corners were rounded;
    the lost millimetre is at the lid's rear, under the top panel's edge)."""
    return size_mm("lid")[0]


def field_ink(variant: str) -> np.ndarray:
    master = load_gray("IMG_4231_ai_vT1_master.png")
    if variant == "A":
        w0 = WINDOWS["A"] + A_HEAD_SHIFT
        lid = R.warp_affine(master, field_affine(w0, LID_SQUASH_A), FIELD)
        top = R.warp_affine(master, field_affine(w0 + TOP_U0 / LID_SQUASH_A - TOP_U0), FIELD)
        cut = int(round(TOP_U0 * R.PPM))
        g = np.concatenate([lid[:, :cut], top[:, cut:]], axis=1)
    else:
        g = R.warp_affine(master, field_affine(WINDOWS[variant]), FIELD)
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
    sp = int(round(split_mm() * R.PPM))
    lid_part = ink_field[:, :sp]
    top = ink_field[:, int(round(TOP_U0 * R.PPM)):]
    W_lid, H_lid = size_mm("lid")
    top_w = int(round(size_mm("top")[0] * R.PPM))
    top = top[:, :top_w]
    H = int(round(H_lid * R.PPM))
    lid = np.zeros((H, sp), bool)
    off = int(round((H_lid - FIELD[1]) / 2 * R.PPM))
    lid[off:off + lid_part.shape[0], :] = lid_part
    return lid, top


def drop_edge_orphans(m: np.ndarray, band_mm: float = 8.0, max_mm2: float = 25.0) -> np.ndarray:
    """Small pieces of the lid's drawing that spill over the seam onto the
    top panel's front edge read as orphans there: drop them."""
    n, lab, st, _ = cv2.connectedComponentsWithStats(R.u8(m), connectivity=8)
    out = m.copy()
    band = int(band_mm * R.PPM)
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if x + w <= band and a < max_mm2 * R.PPM ** 2:
            out[lab == i] = False
    return out


SRC = "art/ai-versions/final/IMG_4231_ai_vT1_master.png (approved panorama)"


def _variants(part: str):
    out = []
    for v, label, default, note in [
        ("A", "Snake head", True,
         "The mosaic snake's head sits on the sliding lid and its scaled body runs back across "
         "the top. The cat is left off."),
        ("C", "Whole cat", False,
         "The whole cat and the flowered wallpaper fill the top panel; the lid "
         "shows the snake's scales. The snake's head is left off."),
    ]:
        lid, top = split(field_ink(v))
        face = "lid" if part == "lid" else "top"
        m = lid if part == "lid" else top
        if part == "top":
            m = drop_edge_orphans(m)
        # the snake's pupils (the solid almond slits, ~100 mm2 each) stay solid;
        # the dark crosshatch under each eye still gets gap channels
        pupils = cv2.morphologyEx(R.u8(m), cv2.MORPH_OPEN, R.disk(R.px(3.0))).astype(bool)
        pupils = cv2.dilate(R.u8(pupils), R.disk(R.px(0.8))).astype(bool) & m
        out.append(Variant(v.lower(), label, finish(face, m, protect=pupils),
                           default=default, source=SRC, notes=note))
    return out


def sliding_lid(face_id):
    return _variants("lid")


def top_panel(face_id):
    return _variants("top")


RECIPES = {"lid": sliding_lid, "top": top_panel}
