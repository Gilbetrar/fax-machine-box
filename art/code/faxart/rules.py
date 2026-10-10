"""Per-feature laser-rule measurement (shared by the build's repair loop and
tests/test_code_art.py).

Measured on the rendered SVG at 40 px/mm with exact Euclidean morphology
(distance transforms, not pixel kernels):

  thin  = ink not covered by any 0.25 mm disk that fits inside the ink
  gap   = paper not covered by any 0.30 mm disk that fits inside the paper
          (a 3 px margin at the canvas edge is ignored: the edge is a cut)

Every connected thin or gap feature of at least 0.02 mm2 is a violation.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

RULE_PPM = 40.0
MIN_LINE_MM = 0.25
MIN_GAP_MM = 0.30
FEATURE_MM2 = 0.02


def opening(m: np.ndarray, r: float) -> np.ndarray:
    c = ndi.distance_transform_edt(m) > r
    return ndi.distance_transform_edt(~c) <= r


def features(diff: np.ndarray, ppm: float, min_mm2: float = FEATURE_MM2):
    lab, n = ndi.label(diff, structure=np.ones((3, 3)))
    if n == 0:
        return lab, []
    area = np.bincount(lab.ravel())[1:]
    keep = [i + 1 for i, a in enumerate(area) if a >= min_mm2 * ppm * ppm]
    return lab, keep


def violations(ink: np.ndarray, ppm: float = RULE_PPM, min_mm2: float = FEATURE_MM2):
    """-> (thin_mask, gap_mask, n_thin, n_gap) of features >= min_mm2."""
    thin = ink & ~opening(ink, MIN_LINE_MM / 2 * ppm)
    paper = ~ink
    gap = paper & ~opening(paper, MIN_GAP_MM / 2 * ppm)
    gap[:3, :] = gap[-3:, :] = False
    gap[:, :3] = gap[:, -3:] = False
    lt, kt = features(thin, ppm, min_mm2)
    lg, kg = features(gap, ppm, min_mm2)
    return np.isin(lt, kt), np.isin(lg, kg), len(kt), len(kg)
