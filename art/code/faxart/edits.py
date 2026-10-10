"""Deterministic layout edits on traced ink masks: move whole drawn elements
(letters, figures) so the box's through-cuts fall in the gaps between them.
Nothing here draws new linework; it only cuts, moves and re-pastes what Ben's
approved art already contains (plus the front-wall dots, re-drawn from his
photo, and the relocated 'Fun For')."""

from __future__ import annotations

import cv2
import numpy as np

from . import raster as R


def P(mm: float) -> int:
    return int(round(mm * R.PPM))


def components(ink: np.ndarray, min_mm2: float = 30.0):
    n, lab, st, cen = cv2.connectedComponentsWithStats(R.u8(ink), connectivity=8)
    out = []
    for i in range(1, n):
        if st[i, cv2.CC_STAT_AREA] >= min_mm2 * R.PPM ** 2:
            x, y, w, h = st[i, :4] / R.PPM
            out.append(dict(i=i, u0=x, u1=x + w, v0=y, v1=y + h,
                            cu=cen[i][0] / R.PPM, cv=cen[i][1] / R.PPM))
    return lab, out


def find(comps, cu, cv, tol=4.0):
    best = min(comps, key=lambda c: (c["cu"] - cu) ** 2 + (c["cv"] - cv) ** 2)
    assert abs(best["cu"] - cu) < tol and abs(best["cv"] - cv) < tol, (cu, cv, best)
    return best


def affine_paste(base: np.ndarray, piece: np.ndarray, M: np.ndarray) -> np.ndarray:
    """OR `piece` (bool mask, same canvas) into base after a 2x3 affine in mm."""
    Mp = M.copy().astype(np.float64)
    Mp[:, 2] *= R.PPM
    g = cv2.warpAffine(R.u8(piece) * 255, Mp, (base.shape[1], base.shape[0]),
                       flags=cv2.INTER_LINEAR, borderValue=0)
    return base | (g > 127)


def move(ink: np.ndarray, sel: np.ndarray, M) -> np.ndarray:
    return affine_paste(ink & ~sel, sel, np.asarray(M, float))


def translate(dx, dy=0.0):
    return np.array([[1, 0, dx], [0, 1, dy]], float)


def scale_about(sx, sy, u0, v0, dx=0.0, dy=0.0):
    return np.array([[sx, 0, u0 - sx * u0 + dx], [0, sy, v0 - sy * v0 + dy]], float)


def rect(shape, u0, v0, u1, v1):
    m = np.zeros(shape, bool)
    m[max(0, P(v0)):P(v1), max(0, P(u0)):P(u1)] = True
    return m
