"""Per-feature laser-rule measurement (shared by the build's repair loop and
tests/test_code_art.py).

Measured on the rendered SVG at 40 px/mm with exact Euclidean morphology
(distance transforms, not pixel kernels):

  thin  = ink not covered by any 0.275 mm disc that fits inside the ink
  gap   = paper not covered by any 0.325 mm disc that fits inside the paper
          (a 3 px margin at the canvas edge is ignored: the edge is a cut)

Every connected thin or gap feature of at least 0.02 mm2 is a violation.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage as ndi

RULE_PPM = 40.0
# The rules are line >= 0.25 mm and gap >= 0.30 mm. They are MEASURED with
# discs of 0.275 / 0.325 mm: red-team pass 2 used cv2 11 px / 13 px ellipse
# kernels at 40 px/mm and found 0.21-0.30 mm gaps that an exact 0.30 mm disc
# (with a strict '>' on the distance) let through. Measuring with the
# larger discs closes that hole; it is stricter than the rule, never looser.
MIN_LINE_MM = 0.275
MIN_GAP_MM = 0.325
FEATURE_MM2 = 0.02


def opening(m: np.ndarray, r: float) -> np.ndarray:
    c = ndi.distance_transform_edt(m) >= r
    return ndi.distance_transform_edt(~c) <= r


def features(diff: np.ndarray, ppm: float, min_mm2: float = FEATURE_MM2):
    lab, n = ndi.label(diff, structure=np.ones((3, 3)))
    if n == 0:
        return lab, []
    area = np.bincount(lab.ravel())[1:]
    keep = [i + 1 for i, a in enumerate(area) if a >= min_mm2 * ppm * ppm]
    return lab, keep


# The rules themselves, for checking art after the cut-set has placed and
# trimmed it (its geometry is simplified to ~0.02 mm, so it is checked
# against the rule, not against the build's stricter measuring discs).
RULE_LINE_MM = 0.25
RULE_GAP_MM = 0.30


def violations(ink: np.ndarray, ppm: float = RULE_PPM, min_mm2: float = FEATURE_MM2,
               line_mm: float = MIN_LINE_MM, gap_mm: float = MIN_GAP_MM):
    """-> (thin_mask, gap_mask, n_thin, n_gap) of features >= min_mm2."""
    thin = ink & ~opening(ink, line_mm / 2 * ppm)
    paper = ~ink
    gap = paper & ~opening(paper, gap_mm / 2 * ppm)
    gap[:3, :] = gap[-3:, :] = False
    gap[:, :3] = gap[:, -3:] = False
    lt, kt = features(thin, ppm, min_mm2)
    lg, kg = features(gap, ppm, min_mm2)
    return np.isin(lt, kt), np.isin(lg, kg), len(kt), len(kg)
