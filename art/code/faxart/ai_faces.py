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


# Parrot placement (red-team pass 3, W1): chosen by tools/place_search.py, which
# scores every (dx, dy) by how much traced ink the shelf hole row removes,
# weighting the eyes, beak, vest pins and spray can 5x. Raising it 11.5 mm
# (pass 2) put the row through the vest pins and the can; 4.5 mm right and
# 0.5 mm up puts the holes between the gorget feathers and past the drool.
PARROT_DX, PARROT_UP = 4.5, 0.5


def relayout_fax_machine(ink: np.ndarray) -> np.ndarray:
    """Move the drawn letters (and the parrot) so the through-cuts miss them.

    FAX: F -4.5, A -5.5, X -12.5 mm, so the divider hole column (u 219.0-222.3,
    keep-out 218.5-222.8) passes right of the X.
    MACHINE: every letter at 90 % width and 92 % height (about v 124, so the
    tops clear the shelf hole row at v 61.9-65.1), laid out with SIX EQUAL
    4.6 mm gaps; the H-I gap is the one the divider column runs down.
    Parrot (with its can and spray cloud): PARROT_DX right, PARROT_UP up."""
    lab, comps = E.components(ink)
    F = E.find(comps, 141.7, 25.6)
    A = E.find(comps, 173.6, 31.8)
    X = E.find(comps, 215.0, 28.7)
    word = [E.find(comps, 144.8, 89.1), E.find(comps, 172.2, 95.2), E.find(comps, 192.1, 92.5),
            E.find(comps, 213.7, 90.2), E.find(comps, 234.0, 91.1), E.find(comps, 256.8, 90.8),
            E.find(comps, 282.6, 92.9)]
    mist = E.find(comps, 129.7, 68.3)
    letters = {c["i"] for c in [F, A, X, *word]}
    parrot = (np.arange(ink.shape[1])[None, :] < E.P(126.0)) & ink & ~np.isin(lab, list(letters))
    parrot |= lab == mist["i"]
    moves = [(lab == F["i"], E.translate(-4.5)), (lab == A["i"], E.translate(-5.5)),
             (lab == X["i"], E.translate(-12.5)), (parrot, E.translate(PARROT_DX, -PARROT_UP))]
    SX, SY, GAP, H_RIGHT = 0.90, 0.92, 4.6, 218.2
    widths = [SX * (c["u1"] - c["u0"]) for c in word]
    left = H_RIGHT - sum(widths[:4]) - 3 * GAP
    for c, w in zip(word, widths):
        M = np.array([[SX, 0, left - SX * c["u0"]], [0, SY, 124.0 - SY * 124.0]], float)
        moves.append((lab == c["i"], M))
        left += w + GAP
    sel_all = np.zeros(ink.shape, bool)
    for m, _ in moves:
        sel_all |= m
    out = ink & ~sel_all
    for m, M in moves:
        out = E.affine_paste(out, m, M)
    return out


def relayout_writer(ink: np.ndarray) -> np.ndarray:
    """Right wall: move and shrink the seated writer (with the CAP sign
    behind him) so the divider hole column (u 76.2-79.4) runs through the
    empty space right of him. The destination is clipped at u 45.5 so it
    never touches the NEW PLAY poster."""
    sel = ink & E.rect(ink.shape, 48.5, 36.0, 88.0, 96.0)
    # 5 mm left, then 83 % about his lower-left corner (u 45.5, desk line
    # v 96): his right edge (wig curl and shoulder, u 82) ends at 75.5, left
    # of the divider hole column's keep-out (pass 3, W2)
    M = E.scale_about(0.83, 0.83, 45.5, 96.0) @ np.vstack([E.translate(-5.0), [0, 0, 1]])
    out = E.affine_paste(ink & ~sel, sel, M)
    poster_side = E.rect(ink.shape, 0, 36.0, 45.5, 96.0)
    return np.where(poster_side, ink, out)


def move_block(ink: np.ndarray, src_box, dx: float, dy: float, keep=None) -> np.ndarray:
    """Translate everything inside src_box by (dx, dy); the moved block
    replaces what is under its new footprint, the strip it vacates keeps the
    old content (here that is always background hatching/rain). Pixels in
    `keep` are never overwritten or moved."""
    src = E.rect(ink.shape, *src_box) & ink
    if keep is not None:
        src &= ~keep
    u0, v0, u1, v1 = src_box
    dst = E.rect(ink.shape, u0 + dx, v0 + dy, u1 + dx, v1 + dy)
    if keep is not None:
        dst &= ~keep
    moved = E.affine_paste(np.zeros_like(ink), src, E.translate(dx, dy))
    return np.where(dst, moved, ink)


def relayout_painter(ink: np.ndarray) -> np.ndarray:
    """Right wall: the shelf hole row (v 61.9-65.1) ran through the painter's
    eye. Slide his head and hat down 4.5 mm so the row crosses the hat brim.
    The block starts above the hat's crown (v 46) so the crown moves whole;
    the 'Artists' letters are excluded from the move."""
    return move_block(ink, (252.0, 46.0, 298.45, 82.0), 0.0, 4.5, keep=title_solids(ink, 60.0, RIGHT_NOT_TITLE))


def relayout_gallery(ink: np.ndarray) -> np.ndarray:
    """Right wall, shelf hole row (holes u 90.5 + 12.7 k, v 61.9-65.1):
    - balloon-dog picture down 2.5 mm, so the row passes above its frame;
    - easel canvas 1 mm left, so both side frames fall between holes;
    - the stick figure inside it 3.5 mm right net, so its neck sits in the
      gap at u 211.1-217.5 (its hair tips and raised arm still cross holes)."""
    keep = title_solids(ink, 60.0, RIGHT_NOT_TITLE)
    ink = move_block(ink, (196.0, 50.0, 224.0, 90.0), 4.5, 0.0, keep)       # figure +4.5 ...
    ink = move_block(ink, (186.5, 43.0, 234.0, 121.0), -1.0, 0.0, keep)     # ... then canvas -1
    ink = move_block(ink, (150.0, 61.0, 187.5, 93.5), 0.0, 2.5, keep)
    return ink


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


INVENTED_SPINES = [   # u0, v0, u1, v1 (mm) on the right wall
    (62.5, 114.0, 81.5, 121.5),   # "SYLVUTA"
    (38.5, 119.0, 60.0, 124.5),   # "MERMAL"
    (83.5, 120.0, 102.5, 125.0),  # "HAVILCRC"
    (14.5, 118.5, 27.5, 122.5),   # "WALT"
]


def blank_invented_spines(ink: np.ndarray) -> np.ndarray:
    """Ben's book pile reads Barr Twain, Bol Dahls, Carper Bee, Hacatha
    Christie, B.S. Smelliot, Jorm Austen, Roy Blabberry, Biertrude. The AI
    redraw added made-up strings on other spines; erase every ink piece that
    lies wholly inside one of those strings' boxes (the letters), keeping
    the spine outlines that run out of the box."""
    n, lab, st, _ = cv2.connectedComponentsWithStats(R.u8(ink), connectivity=8)
    out = ink.copy()
    for u0, v0, u1, v1 in INVENTED_SPINES:
        x0, y0, x1, y1 = E.P(u0), E.P(v0), E.P(u1), E.P(v1)
        for i in np.unique(lab[y0:y1, x0:x1]):
            if i == 0:
                continue
            x, y, w, h = st[i, :4]
            if x >= x0 and y >= y0 and x + w <= x1 and y + h <= y1:
                out[lab == i] = False
    # letter fragments joined to a neighbouring stroke: clear their tight boxes
    for u0, v0, u1, v1 in [(57.5, 119.6, 63.2, 122.6), (102.3, 120.6, 105.6, 123.0),
                           (81.0, 115.0, 83.6, 118.0)]:
        out &= ~E.rect(ink.shape, u0, v0, u1, v1)
    return out


DIGITS_BOX = (47.0, 95.5, 53.5, 108.8)   # measured on the build's front canvas
DIGITS_RAISE_MM = 1.5


SPINE_TITLES = [   # u0, v0, u1, v1 (mm): the lettering of Ben's joke titles
    (11.0, 101.0, 39.0, 108.5),    # BARR TWAIN
    (29.0, 108.5, 54.0, 117.5),    # CARPER BEE
    (87.0, 110.0, 108.5, 117.5),   # B.S. SMELLIOT
    (110.0, 108.0, 127.5, 118.0),  # ROW BLABBARY
    (112.0, 116.5, 137.0, 123.0),  # BIERTRUDE
]
SPINE_SCALE = 1.18


def enlarge_spine_titles(ink: np.ndarray) -> np.ndarray:
    """Scale the traced lettering of the clearest joke titles up by
    SPINE_SCALE about its own centre (a pure scale of Ben's traced letters),
    clipped 0.4 mm inside the white spine it sits on so it never runs into
    the spine outline."""
    out = ink.copy()
    n, lab, st, _ = cv2.connectedComponentsWithStats(R.u8(ink), connectivity=8)
    for u0, v0, u1, v1 in SPINE_TITLES:
        x0, y0, x1, y1 = E.P(u0), E.P(v0), E.P(u1), E.P(v1)
        letters = np.zeros_like(ink)
        for i in np.unique(lab[y0:y1, x0:x1]):
            if i == 0:
                continue
            x, y, w, h = st[i, :4]
            if x >= x0 and y >= y0 and x + w <= x1 and y + h <= y1 and h < E.P(5.5):
                letters |= lab == i
        if not letters.any():
            continue
        # the white spine = the biggest paper region inside the box once the
        # letters are filled in
        paper = ~(ink & ~letters)
        pn, plab, pst, _ = cv2.connectedComponentsWithStats(R.u8(paper[y0:y1, x0:x1]), connectivity=4)
        k = 1 + int(np.argmax(pst[1:, cv2.CC_STAT_AREA]))
        spine = np.zeros_like(ink)
        spine[y0:y1, x0:x1] = plab == k
        spine = cv2.erode(R.u8(spine), R.disk(2 * E.P(0.4) + 1)).astype(bool)
        ys, xs = np.nonzero(letters)
        cu, cv_ = xs.mean() / R.PPM, ys.mean() / R.PPM
        big = E.affine_paste(np.zeros_like(ink), letters,
                             E.scale_about(SPINE_SCALE, SPINE_SCALE, cu, cv_))
        out = (out & ~letters) | (big & spine)
    return out


def front_dots(ink: np.ndarray) -> np.ndarray:
    """Ben's photo (IMG_4229) has '1 ●  2 ●  3 ●  4 ●': digit + filled dot.
    The AI redraw turned the dots into 0s and a second 4 ('10 20 30 44').
    Keep each row's first digit, replace the rest of the row with a solid
    dot, and clear a 0.8 mm halo of hatching around the column of labels."""
    box = E.rect(ink.shape, *DIGITS_BOX)
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
    labels = E.affine_paste(np.zeros_like(labels), labels, E.translate(0.0, -DIGITS_RAISE_MM))
    halo = cv2.dilate(R.u8(labels), R.disk(2 * E.P(0.8) + 1)).astype(bool)
    return (out & ~halo) | labels


def title_solids(ink: np.ndarray, top_mm: float = 60.0, exclude=()) -> np.ndarray:
    """Solid display letters in the upper part of a face (the title), minus
    `exclude` boxes (u0, v0, u1, v1 mm) that hold solid non-letter art."""
    m = solid_regions(ink, 1.6)
    m[E.P(top_mm):, :] = False
    for b in exclude:
        m &= ~E.rect(ink.shape, *b)
    return grow(m, 1.0) & ink


# right wall: the stamp portrait's hair and the writer's black CAP poster are
# solid art, not title lettering (pass 3, W4)
RIGHT_NOT_TITLE = [(0.0, 0.0, 30.0, 45.0), (40.0, 30.0, 70.0, 100.0)]
POSTER_BOX = (44.0, 30.0, 72.0, 100.0)   # the writer's black CAP poster, after his move


def poster_solid(ink: np.ndarray) -> np.ndarray:
    """The CAP poster stays solid black in every right-wall variant."""
    return grow(solid_regions(ink, 1.6) & E.rect(ink.shape, *POSTER_BOX), 1.0) & ink


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
    ink = relayout_painter(ink)
    ink = relayout_gallery(ink)
    ink_ff = clear_above_lid_slot(relocate_fun_for(ink, funfor), 0.0, 76.7)
    ink = clear_above_lid_slot(ink & ~funfor, 0.0, 76.7)
    # enlarge_spine_titles() is NOT applied: Ben's traced titles already fill
    # their spines edge to edge, so any enlargement clips the end letters
    # (tried at 1.18x, pass 3 W6: "BARR TWAIN" -> "RR TWAN")
    ink = blank_invented_spines(ink)
    ink_ff = blank_invented_spines(ink_ff)
    # book-pile titles: keep the knock-out channels off the lettering
    books = E.rect(ink.shape, 5.0, 100.0, 150.0, 127.0)
    lettering = lettering | (books & ink) | poster_solid(ink)
    return [
        Variant("funfor", "With 'Fun For'", finish(face_id, ink_ff, protect=lettering), source=src,
                notes="The full title, with 'Fun For' moved down beside 'Terrible' so the lid "
                      "slot doesn't cut it."),
        Variant("outline", "Outlined title", finish(face_id, outline_fill(ink, title_solids(ink, 60.0, RIGHT_NOT_TITLE)),
                       protect=poster_solid(ink)),
                source=src,
                notes="The title as outlined letters with light hatching inside. Faster to "
                      "engrave and less likely to scorch."),
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
    # the AI drawing's second row of buttons runs off its bottom edge and
    # reads as stubs sitting on the base line: erase them, keep the line
    ink &= ~E.rect(ink.shape, 66.5, 107.2, 114.5, 109.3)
    # tick remnants of those stubs left on the base line (pass 3, W5, and
    # the bumps still attached to the line at u ~100 / 112): inside this
    # strip keep only long horizontal runs, i.e. the base line itself
    strip = E.rect(ink.shape, 66.0, 106.0, 117.0, 111.0)
    lab, comps = E.components(ink & strip, min_mm2=0.0)
    for c in comps:
        if (c["u1"] - c["u0"]) < 2.5 and (c["v1"] - c["v0"]) < 2.5:
            ink &= ~(lab == c["i"])
    line = cv2.morphologyEx(R.u8(ink & strip), cv2.MORPH_OPEN,
                            cv2.getStructuringElement(cv2.MORPH_RECT, (E.P(4.0), 1))).astype(bool)
    ink = (ink & ~strip) | line
    lettering = grow(solid_regions(ink), 1.0) & ink
    outlined = Variant("outline", "Outlined letters",
                       finish(face_id, outline_fill(ink, title_solids(ink, 80.0))),
                       source="art/ai-versions/final/IMG_4229_ai_vH1.png",
                       notes="FAX MACHINE as outlined letters with light hatching inside. Faster "
                             "to engrave and less likely to scorch.")
    return [outlined, Variant("traced", "Fax machine", finish(face_id, ink, protect=lettering), default=True,
                    source="art/ai-versions/final/IMG_4229_ai_vH1.png",
                    notes="The fax machine from the front of the original box, with its WRITE "
                          "and DRAW buttons.")]


RECIPES = {"left": left_wall, "right": right_wall, "front": front_wall}
