"""Drawer faceplates: the hand-drawn letter OUTLINES are traced from the
approved AI art; every letter's fill is redrawn in code with the pattern the
drawing uses (diagonal, crosshatch, vertical, horizontal, grid, waves,
little circles) at laser-safe spacing. The fine 0.1-0.2 mm hatching in the
source would burn to mud at 100 mm word width; the coded fills keep >= 0.45 mm
gaps.

Placement (Ben, July): the word sits BELOW the 30x15 mm grip slot (slot
bottom at 22.9 mm), in the band 25-49.5 mm from the top edge, no bleed.
"""

from __future__ import annotations

import math

import cv2
import numpy as np

from . import raster as R
from .ai_faces import ai_ink, fit_contain, grow
from .finish import Variant, finish

BAND = (3.0, 25.0, 147.9, 49.5)

WORDS = {
    "B_face": dict(src="IMG_4236_ai_vH3.png", box=(283, 725, 6053, 2134),
                             patterns=["diag", "cross", "vert", "horiz", "diag_r", "cross_dense"], ring_mm=1.05, rim_mm=0.4),
    "T_face": dict(src="IMG_4238_ai_vH2.png", box=(755, 520, 5749, 2165),
                            patterns=["grid", "cross", "cross", "diag_r", "wave", "circles"], ring_mm=0.75, rim_mm=0.65),
}
# 'Lines' has 6 fill regions: L, the i dot, the i stem, n, e, s.


def waves(region, pitch=1.25, amp=0.35, lam=2.6, width=0.34, seed=0):
    rng = np.random.default_rng(seed)
    H, W = region.shape
    can = np.zeros((H, W), np.uint8)
    xs = np.arange(0, W / R.PPM, 0.1)
    y = rng.uniform(0, pitch)
    while y < H / R.PPM:
        ph = rng.uniform(0, 2 * math.pi)
        ys = y + amp * np.sin(2 * math.pi * xs / lam + ph)
        pts = np.stack([xs, ys], 1) * R.PPM
        cv2.polylines(can, [np.round(pts * 16).astype(np.int32)], False, 255,
                      thickness=int(round(width * R.PPM)), lineType=cv2.LINE_AA, shift=4)
        y += pitch
    return (can > 110) & region


def circles(region, spacing=1.25, d=1.1, width=0.32, seed=0):
    """Little hand-drawn rings scattered with a minimum spacing (dart throwing)."""
    rng = np.random.default_rng(seed)
    H, W = region.shape
    can = np.zeros((H, W), np.uint8)
    inner = cv2.erode(R.u8(region), R.disk(2 * R.px(d / 2) + 1)).astype(bool)
    ys, xs = np.nonzero(inner)
    if len(xs) == 0:
        return can > 0
    order = rng.permutation(len(xs))
    placed = []
    sp2 = (spacing * R.PPM) ** 2
    for k in order[: 40000]:
        x, y = xs[k], ys[k]
        if all((x - a) ** 2 + (y - b) ** 2 >= sp2 for a, b in placed[-400:]) and \
           all((x - a) ** 2 + (y - b) ** 2 >= sp2 for a, b in placed):
            placed.append((x, y))
    for x, y in placed:
        r = d / 2 * rng.uniform(0.85, 1.15) * R.PPM
        cv2.ellipse(can, (int(x * 16), int(y * 16)), (int(r * 16), int(r * 0.9 * 16)),
                    rng.uniform(0, 180), 0, 360, 255, int(round(width * R.PPM)), cv2.LINE_AA, 4)
    return (can > 110) & region


def pattern(name, region, seed):
    h = lambda **k: R.hatch(region, seed=seed, stroke_mm=(3, 8), **k)  # noqa: E731
    if name == "diag":
        return h(pitch_mm=1.0, angle_deg=45, width_mm=0.34)
    if name == "diag_r":
        return h(pitch_mm=1.0, angle_deg=-45, width_mm=0.34)
    if name == "vert":
        return h(pitch_mm=1.05, angle_deg=90, width_mm=0.34)
    if name == "horiz":
        return h(pitch_mm=0.95, angle_deg=0, width_mm=0.34)
    if name == "cross":
        return h(pitch_mm=1.3, angle_deg=45, width_mm=0.32) | \
            R.hatch(region, seed=seed + 1, stroke_mm=(3, 8), pitch_mm=1.3, angle_deg=-45, width_mm=0.32)
    if name == "cross_dense":
        return h(pitch_mm=1.05, angle_deg=40, width_mm=0.32) | \
            R.hatch(region, seed=seed + 1, stroke_mm=(3, 8), pitch_mm=1.15, angle_deg=-50, width_mm=0.32)
    if name == "grid":
        return h(pitch_mm=1.3, angle_deg=0, width_mm=0.32) | \
            R.hatch(region, seed=seed + 1, stroke_mm=(3, 8), pitch_mm=1.3, angle_deg=90, width_mm=0.32)
    if name == "wave":
        return waves(region, seed=seed)
    if name == "circles":
        return circles(region, seed=seed)
    raise KeyError(name)


def faceplate(face_id):
    c = WORDS[face_id]
    dst = fit_contain(c["box"], BAND)
    ink = ai_ink(face_id, c["src"], c["box"], dst)
    # letter silhouettes: everything not connected to the background once
    # the hatching is closed up
    closed = cv2.morphologyEx(R.u8(ink), cv2.MORPH_CLOSE, R.disk(R.px(0.6))).astype(bool)
    n, lab = cv2.connectedComponents(R.u8(~closed), connectivity=4)
    border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    sil = ~np.isin(lab, border[border > 0])
    # counters (O, R, e holes...): areas enclosed by the bold outline that the
    # drawing leaves BLANK (sparse fills such as dots or waves are not blank)
    thick = cv2.morphologyEx(R.u8(ink), cv2.MORPH_OPEN, R.disk(R.px(0.4))).astype(bool)
    # A counter is a hole INSIDE an inner outline loop: in the contour tree of
    # the bold outline that is depth 3 (outer loop -> its hole -> inner loop ->
    # its hole). Blank patches of a letter's own fill are only depth 1, so a
    # lightly hatched L or S is never mistaken for a counter.
    cs, hier = cv2.findContours(R.u8(thick), cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
    counters = np.zeros(ink.shape, np.uint8)
    if hier is not None:
        hier = hier[0]
        for i, cnt in enumerate(cs):
            d, j = 0, hier[i][3]
            while j >= 0:
                d, j = d + 1, hier[j][3]
            if d == 3 and cv2.contourArea(cnt) > 3 * R.PPM ** 2:
                cv2.drawContours(counters, cs, i, 1, -1)
    counters = counters.astype(bool) & ~thick
    body = sil & ~counters
    body = cv2.morphologyEx(R.u8(body), cv2.MORPH_OPEN, R.disk(R.px(0.5))).astype(bool)
    ring_mm = c["ring_mm"]  # measured outline weight of each drawing
    ring = body & ~cv2.erode(R.u8(body), R.disk(2 * R.px(ring_mm) + 1)).astype(bool)
    outline = (thick & ring) | (body & ~cv2.erode(R.u8(body), R.disk(2 * R.px(c["rim_mm"]) + 1)).astype(bool))
    inner = cv2.erode(R.u8(body), R.disk(2 * R.px(ring_mm + 0.4) + 1)).astype(bool)
    # one fill pattern per LETTER (a letter's interior can split into pieces)
    nl, labl, stl, cenl = cv2.connectedComponentsWithStats(R.u8(body), connectivity=8)
    letters = sorted((cenl[i][0], i) for i in range(1, nl) if stl[i, cv2.CC_STAT_AREA] > 4 * R.PPM ** 2)
    pats = c["patterns"]
    assert len(letters) == len(pats), (face_id, len(letters))
    fill = np.zeros(ink.shape, bool)
    for k, (_, i) in enumerate(letters):
        fill |= pattern(pats[k], inner & (labl == i), seed=100 + k)
    art = outline | fill
    return [Variant("traced", "Patterned letters", finish(face_id, art, knock=False),
                    default=True, source=f"art/ai-versions/final/{c['src']}",
                    notes="The hand-drawn letters, each filled with its own pattern, set below the "
                          "finger slot.")]


RECIPES = {"B_face": faceplate, "T_face": faceplate}
