"""Recipes for faces traced from Ben's approved AI-restyled hatch art
(art/ai-versions/final/, frozen). The sources are read at full resolution
(no 300 dpi 1-bit middle step) and re-thresholded at 20 px/mm, so the traced
curves come out smooth instead of stair-stepped."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from . import raster as R
from .finish import Variant, finish
from .geometry import FACES

REPO = Path(__file__).resolve().parents[3]
FINAL = REPO / "art" / "ai-versions" / "final"


def load_gray(name: str) -> np.ndarray:
    g = cv2.imread(str(FINAL / name), cv2.IMREAD_GRAYSCALE)
    assert g is not None, name
    return g


def box_to_rect(src_box, dst_box_mm) -> np.ndarray:
    """2x3 affine taking a source px box (x0,y0,x1,y1) onto a canvas mm box."""
    x0, y0, x1, y1 = src_box
    X0, Y0, X1, Y1 = [v * R.PPM for v in dst_box_mm]
    sx, sy = (X1 - X0) / (x1 - x0), (Y1 - Y0) / (y1 - y0)
    return np.array([[sx, 0, X0 - sx * x0], [0, sy, Y0 - sy * y0]], np.float64)


def fit_contain(src_box, area_mm) -> tuple:
    """Uniform scale of src_box into area (x0,y0,x1,y1 mm), centred."""
    x0, y0, x1, y1 = src_box
    A0, B0, A1, B1 = area_mm
    s = min((A1 - A0) / (x1 - x0), (B1 - B0) / (y1 - y0))
    w, h = (x1 - x0) * s, (y1 - y0) * s
    cx, cy = (A0 + A1) / 2, (B0 + B1) / 2
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


def ai_ink(face_id, name, src_box, dst_box_mm=None, t=128):
    size = FACES[face_id].size_mm
    dst = dst_box_mm or (0, 0, size[0], size[1])
    g = R.warp_affine(load_gray(name), box_to_rect(src_box, dst), size)
    return R.threshold_gray(g, t)


def solid_regions(ink: np.ndarray, solid_mm: float = 2.4) -> np.ndarray:
    return cv2.morphologyEx(R.u8(ink), cv2.MORPH_OPEN, R.disk(R.px(solid_mm))).astype(bool)


def grow(mask: np.ndarray, mm: float) -> np.ndarray:
    return cv2.dilate(R.u8(mask), R.disk(2 * R.px(mm) + 1)).astype(bool)


def outline_fill(ink: np.ndarray, letters: np.ndarray, ring_mm: float = 0.9,
                 pitch_mm: float = 1.7, seed: int = 5) -> np.ndarray:
    """Solid letters -> a hand-weight outline + light coded hatch inside."""
    core = cv2.erode(R.u8(letters), R.disk(2 * R.px(ring_mm) + 1)).astype(bool)
    inner = cv2.erode(R.u8(core), R.disk(2 * R.px(0.45) + 1)).astype(bool)
    fill = R.hatch(inner, pitch_mm=pitch_mm, angle_deg=45, width_mm=0.34, seed=seed,
                   stroke_mm=(6, 16), lift_mm=(0.4, 1.0))
    return (ink & ~core) | fill


WALL_AREA = (4.0, 1.0, 294.45, 126.0)


def clear_above_lid_slot(ink: np.ndarray, x0_mm: float, x1_mm: float) -> np.ndarray:
    """The 3.5 mm strip between the wall's top edge and the lid through-slot
    is too thin to carry art; fragments left there read as strays."""
    out = ink.copy()
    out[: int(5.2 * R.PPM), int(x0_mm * R.PPM): int(x1_mm * R.PPM)] = False
    return out


def left_wall(face_id):
    # source crop = the approved composition (PLACEMENTS.md: drawn frame
    # dropped, robust content bbox), cover-fit to the full wall
    # contain-fit with 4 mm clear of the finger-jointed front/rear edges (the
    # July cover-fit clipped the E of MACHINE into the finger notches)
    box = (247, 116, 6151, 2628)
    ink = ai_ink(face_id, "IMG_4228_ai_vH1.png", box, fit_contain(box, WALL_AREA))
    ink = clear_above_lid_slot(ink, 222.0, 298.45)   # left wall: front (slot) is at the right
    W = ink.shape[1]
    lettering = solid_regions(ink)
    lettering[:, : int(0.42 * W)] = False  # parrot side: the spray can is not lettering
    lettering = grow(lettering, 1.0) & ink
    src = "art/ai-versions/final/IMG_4228_ai_vH1.png (approved)"
    return [
        Variant("solid", "FAX MACHINE solid", finish(face_id, ink, protect=lettering),
                default=True, source=src,
                notes="Display lettering kept solid black (Ben's style); other large solids "
                      "get gap channels."),
        Variant("outline", "FAX MACHINE outline + light fill",
                finish(face_id, outline_fill(ink, lettering)), source=src,
                notes="Lettering redrawn as a 0.9 mm outline with light coded hatching inside: "
                      "much less burn time and charring than solid."),
    ]


def right_wall(face_id):
    box = (357, 182, 5969, 2570)
    ink = ai_ink(face_id, "IMG_4230_ai_vH2.png", box, fit_contain(box, WALL_AREA))
    ink = clear_above_lid_slot(ink, 0.0, 76.5)       # right wall: front (slot) is at the left
    H, W = ink.shape
    src = "art/ai-versions/final/IMG_4230_ai_vH2.png (approved)"
    lettering = solid_regions(ink, 1.6)
    lettering[int(0.45 * H):, :] = False  # title band only
    lettering = grow(lettering, 1.0) & ink
    # 'Fun For' = the pixels the July NOFUNFOR variant erased (same 300 dpi
    # canvas mapping), lifted to 20 px/mm, plus every ink component they touch
    # in the top-left title corner.
    a = cv2.imread(str(REPO / "art/engrave/right_wall.png"), cv2.IMREAD_GRAYSCALE)
    b = cv2.imread(str(REPO / "art/engrave/right_wall_VARIANT_NOFUNFOR.png"), cv2.IMREAD_GRAYSCALE)
    erased = R.u8((a < 128) & (b >= 128)) * 255
    # the July canvas = the source box cover-fit to the full wall; map it into
    # this build's contain-fit box
    X0, Y0, X1, Y1 = [int(round(v * R.PPM)) for v in fit_contain(box, WALL_AREA)]
    small = cv2.resize(erased, (X1 - X0, Y1 - Y0), interpolation=cv2.INTER_LINEAR) > 60
    erased = np.zeros((H, W), bool)
    erased[Y0:Y1, X0:X1] = small[: H - Y0, : W - X0]
    corner = np.zeros((H, W), bool)
    corner[: int(0.2 * H), int(0.08 * W): int(0.3 * W)] = True
    n, lab = cv2.connectedComponents(R.u8(ink & corner))
    hit = np.unique(lab[erased & ink & corner])
    funfor = np.isin(lab, hit[hit > 0]) | grow(erased, 0.4)
    return [
        Variant("funfor", "With 'Fun For'", finish(face_id, ink, protect=lettering), source=src,
                notes="Full title. The lid through-slot (y 5.1-8.9 mm, front 76 mm) cuts "
                      "through 'Fun For'."),
        Variant("nofunfor", "Without 'Fun For'", finish(face_id, ink & ~funfor, protect=lettering),
                default=True, source=src,
                notes="'Fun For' removed so the lid slot crosses blank wood; the title reads "
                      "'Terrible Writers & Artists of All Ages'."),
    ]


def front_wall(face_id):
    # contain-fit ABOVE the bottom finger-hole row (y >= 114.9 mm) so the
    # buttons and the 10/20/30/44 digits are no longer bitten by the teeth
    box = (350, 422, 4384, 3421)
    dst = fit_contain(box, (2.5, 1.0, 156.25, 113.4))
    ink = ai_ink(face_id, "IMG_4229_ai_vH1.png", box, dst)
    lettering = grow(solid_regions(ink), 1.0) & ink
    return [Variant("traced", "Traced", finish(face_id, ink, protect=lettering), default=True,
                    source="art/ai-versions/final/IMG_4229_ai_vH1.png (approved)",
                    notes="Fit above the bottom finger-joint row (art bottom at 113.4 mm). "
                          "'44' kept as drawn in the source.")]


RECIPES = {"left_wall": left_wall, "right_wall": right_wall, "front_wall": front_wall}
