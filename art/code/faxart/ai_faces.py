"""Recipes for faces traced from Ben's approved AI-restyled hatch art
(art/ai-versions/final/, frozen). The sources are read at full resolution
(no 300 dpi 1-bit middle step) and re-thresholded at 20 px/mm, so the traced
curves come out smooth instead of stair-stepped."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from . import edits as E
from . import raster as R
from .finish import Variant
from .finish import finish as _finish


def finish(face_id, ink, **kw):
    # the approved hatch is fine pen work: thicken sub-minimum strokes only to
    # 0.30 mm (rule 0.25) so the shading doesn't darken more than it must
    kw.setdefault("thicken_mm", 0.30)
    return _finish(face_id, ink, **kw)
from .geometry import size_mm

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
    size = size_mm(face_id)
    dst = dst_box_mm or (0, 0, size[0], size[1])
    g = R.warp_affine(load_gray(name), box_to_rect(src_box, dst), size)
    ink = R.threshold_gray(g, t)
    # nothing from outside the chosen source box (e.g. a drawn frame line)
    X0, Y0, X1, Y1 = [int(round(v * R.PPM)) for v in dst]
    keep = np.zeros(ink.shape, bool)
    keep[max(0, Y0):Y1, max(0, X0):X1] = True
    return ink & keep


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
    """Nothing above the bottom of the lid slot (v 7.5-11.9 mm, open to the
    front edge in geometry v2): fragments left there read as strays."""
    out = ink.copy()
    out[: int(12.5 * R.PPM), int(x0_mm * R.PPM): int(x1_mm * R.PPM)] = False
    return out


def relayout_fax_machine(ink: np.ndarray) -> np.ndarray:
    """Move the drawn letters so the through-cuts miss them:
    - the divider hole column (u 219.0-222.3, keep-out to 218.5-222.8) falls
      between X and the wall edge, and between H and I;
    - the shelf hole row (v 61.9-65.1) clears the tops of MACHINE.
    FAX: F -4.5 mm, A -5.5 mm, X -12.5 mm (gaps 2.6 / 2.2 mm instead of
    3.6 / 9.2). MACHINE: squashed to 92 % height about v 124 (tops drop from
    v 61 to 66); M-A-C-H (and the spray cloud) narrowed to 94.2 % about the
    M's left edge so H ends at u 217.8; I, N, E stay put."""
    lab, comps = E.components(ink)
    F = E.find(comps, 141.7, 25.6)
    A = E.find(comps, 173.6, 31.8)
    X = E.find(comps, 215.0, 28.7)
    M_ = E.find(comps, 144.8, 89.1)
    A2 = E.find(comps, 172.2, 95.2)
    C = E.find(comps, 192.1, 92.5)
    H = E.find(comps, 213.7, 90.2)
    I = E.find(comps, 234.0, 91.1)
    N = E.find(comps, 256.8, 90.8)
    E_ = E.find(comps, 282.6, 92.9)
    mist = E.find(comps, 129.7, 68.3)
    moves = [(F, E.translate(-4.5)), (A, E.translate(-5.5)), (X, E.translate(-12.5))]
    left_group = E.scale_about(0.942, 0.92, 126.2, 124.0)
    for c in (M_, A2, C, H, mist):
        moves.append((c, left_group))
    for c in (I, N, E_):
        moves.append((c, E.scale_about(1.0, 0.92, 0.0, 124.0)))
    sel_all = np.isin(lab, [c["i"] for c, _ in moves])
    out = ink & ~sel_all
    for c, M in moves:
        out = E.affine_paste(out, lab == c["i"], M)
    return out


def relayout_writer(ink: np.ndarray) -> np.ndarray:
    """Right wall: move the seated writer (with the CAP sign behind him)
    5 mm left so the divider hole column (u 76.2-79.4) runs down his wig
    curl instead of his face. The destination is clipped at u 45.5 so it
    never touches the NEW PLAY poster."""
    sel = ink & E.rect(ink.shape, 48.5, 36.0, 88.0, 96.0)
    out = E.affine_paste(ink & ~sel, sel, E.translate(-5.0))
    poster_side = E.rect(ink.shape, 0, 36.0, 45.5, 96.0)
    return np.where(poster_side, ink, out)


def relocate_fun_for(ink: np.ndarray, funfor: np.ndarray) -> np.ndarray:
    """'Fun For' sits where the lid slot now is. Move the drawn words down
    into the clear band over 'err' of 'Terrible' (u 38-73, v 13-19.8), scaled
    to fit, so the funfor variant reads 'Fun For / Terrible Writers...'."""
    glyphs = ink & funfor
    ys, xs = np.nonzero(glyphs)
    u0, u1, v0, v1 = xs.min() / R.PPM, xs.max() / R.PPM, ys.min() / R.PPM, ys.max() / R.PPM
    A0, B0, A1, B1 = 38.0, 13.0, 73.0, 19.8
    s = min((A1 - A0) / (u1 - u0), (B1 - B0) / (v1 - v0))
    M = np.array([[s, 0, A0 - s * u0], [0, s, B0 - s * v0]], float)
    return E.affine_paste(ink & ~funfor, glyphs, M)


def front_dots(ink: np.ndarray) -> np.ndarray:
    """Ben's photo (IMG_4229) has '1 ●  2 ●  3 ●  4 ●': digit + filled dot.
    The AI redraw turned the dots into 0s and a second 4 ('10 20 30 44').
    Keep each row's first digit, replace the rest of the row with a solid
    dot, and clear a 0.8 mm halo of hatching around the column of labels."""
    box = E.rect(ink.shape, 47.0, 95.5, 53.5, 108.8)
    lab, comps = E.components(ink & box, min_mm2=0.2)
    rows = {}
    for c in comps:
        rows.setdefault(round(c["cv"] / 3.0), []).append(c)
    out = ink & ~box
    labels = np.zeros(ink.shape, bool)
    for key in sorted(rows):
        row = sorted(rows[key], key=lambda c: c["u0"])
        first = row[0]
        digit = lab == first["i"]
        labels |= digit
        rest = row[1:]
        h = first["v1"] - first["v0"]
        cu = (min(c["u0"] for c in rest) + max(c["u1"] for c in rest)) / 2 if rest else first["u1"] + h * 0.8
        cv_ = (first["v0"] + first["v1"]) / 2
        dot = np.zeros(ink.shape, np.uint8)
        cv2.circle(dot, (E.P(cu) * 16, E.P(cv_) * 16), int(0.42 * h * R.PPM * 16), 1, -1, cv2.LINE_AA, 4)
        labels |= dot.astype(bool)
    halo = cv2.dilate(R.u8(labels), R.disk(2 * E.P(0.8) + 1)).astype(bool)
    return (out & ~halo) | labels


def left_wall(face_id):
    # source crop = the approved composition (PLACEMENTS.md: drawn frame
    # dropped, robust content bbox), cover-fit to the full wall
    # contain-fit with 4 mm clear of the finger-jointed front/rear edges (the
    # July cover-fit clipped the E of MACHINE into the finger notches)
    box = (247, 116, 6151, 2628)
    ink = ai_ink(face_id, "IMG_4228_ai_vH1.png", box, fit_contain(box, WALL_AREA))
    ink = relayout_fax_machine(ink)                  # before the slot clear: X's arm moves left
    ink = clear_above_lid_slot(ink, 222.0, 298.45)   # left wall: front (slot) is at the right
    W = ink.shape[1]
    lettering = solid_regions(ink)
    lettering[:, : int(0.42 * W)] = False  # parrot side: the spray can is not lettering
    lettering = grow(lettering, 1.0) & ink
    src = "art/ai-versions/final/IMG_4228_ai_vH1.png "
    return [
        Variant("solid", "Solid letters", finish(face_id, ink, protect=lettering),
                default=True, source=src,
                notes="Solid black drip lettering, as on the original cardboard box."),
        Variant("outline", "Outlined letters",
                finish(face_id, outline_fill(ink, lettering)), source=src,
                notes="The same letters as an outline with light hatching inside. Faster to "
                      "engrave and less likely to scorch."),
    ]


def right_wall(face_id):
    box = (357, 182, 5969, 2570)
    ink = ai_ink(face_id, "IMG_4230_ai_vH2.png", box, fit_contain(box, WALL_AREA))
    H, W = ink.shape
    src = "art/ai-versions/final/IMG_4230_ai_vH2.png "
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
    ink = relayout_writer(ink)
    ink_ff = clear_above_lid_slot(relocate_fun_for(ink, funfor), 0.0, 76.7)
    ink = clear_above_lid_slot(ink & ~funfor, 0.0, 76.7)
    # book-pile titles: keep the knock-out channels off the lettering
    books = E.rect(ink.shape, 5.0, 100.0, 150.0, 127.0)
    lettering = lettering | (books & ink)
    return [
        Variant("funfor", "With 'Fun For'", finish(face_id, ink_ff, protect=lettering), source=src,
                notes="The full title, with 'Fun For' moved down beside 'Terrible' so the lid "
                      "slot doesn't cut it."),
        Variant("nofunfor", "Without 'Fun For'", finish(face_id, ink, protect=lettering),
                default=True, source=src,
                notes="The title reads 'Terrible Writers & Artists of All Ages'."),
    ]


def front_wall(face_id):
    # contain-fit ABOVE the bottom finger-hole row (y >= 114.9 mm) so the
    # buttons and the 10/20/30/44 digits are no longer bitten by the teeth
    box = (350, 422, 4384, 3421)
    dst = fit_contain(box, (2.5, 1.0, 156.25, 110.5))
    ink = ai_ink(face_id, "IMG_4229_ai_vH1.png", box, dst)
    ink = front_dots(ink)
    lettering = grow(solid_regions(ink), 1.0) & ink
    return [Variant("traced", "Fax machine", finish(face_id, ink, protect=lettering), default=True,
                    source="art/ai-versions/final/IMG_4229_ai_vH1.png ",
                    notes="The fax machine from the front of the original box, with its WRITE "
                          "and DRAW buttons.")]


RECIPES = {"left": left_wall, "right": right_wall, "front": front_wall}
