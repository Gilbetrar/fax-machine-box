"""Photo-source recipe (Ben's original prototype photos): traced marker line
+ coded hatching in place of coloured pencil."""

from __future__ import annotations

import cv2
import numpy as np

from . import raster as R

# Default hatch vocabulary, light -> dark. Pitches keep every gap >= 0.45 mm
# at 0.35 mm stroke width; the darkest level crosshatches.
HATCH_LEVELS = [
    # level 1: open hatch, rows every 2.0 mm
    {"pitch_mm": 2.0, "angle_deg": 45, "width_mm": 0.34, "phase_mm": 0.0},
    # level 2: a second set INTERLEAVED half a pitch over -> rows every 1.0 mm
    {"pitch_mm": 2.0, "angle_deg": 45, "width_mm": 0.34, "phase_mm": 1.0},
    # level 3: crosshatch on top
    {"pitch_mm": 1.4, "angle_deg": -45, "width_mm": 0.32, "phase_mm": 0.3},
]


def colour_lines(bgr: np.ndarray, tone: np.ndarray, sat_t: float = 0.42, tone_t: float = 0.10,
                 dark_t: float = 9.0, max_w_mm: float = 1.6) -> np.ndarray:
    """Thin saturated or dark coloured strokes (marker squiggles, the red
    streak, pencil dashes in the sun) become engraved line like the black
    marker. Broad coloured areas don't (they get hatched)."""
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    sat = cv2.GaussianBlur(hsv[:, :, 1].astype(np.float32) / 255.0, (0, 0), 1.0)
    t = cv2.GaussianBlur(tone, (0, 0), 1.0)
    m = ((sat > sat_t) & (t > tone_t)) | (t > dark_t)
    m = cv2.morphologyEx(R.u8(m), cv2.MORPH_OPEN, R.disk(R.px(0.3))).astype(bool)
    broad = cv2.morphologyEx(R.u8(m), cv2.MORPH_OPEN, R.disk(R.px(max_w_mm))).astype(bool)
    broad = cv2.dilate(R.u8(broad), R.disk(R.px(0.8))).astype(bool)
    thin = R.u8(m & ~broad)
    # keep only stroke-like pieces: long, with a small mean width (area/length)
    n, lab, st, _ = cv2.connectedComponentsWithStats(thin, connectivity=8)
    keep = np.zeros(n, bool)
    for i in range(1, n):
        w, h, a = st[i, cv2.CC_STAT_WIDTH], st[i, cv2.CC_STAT_HEIGHT], st[i, cv2.CC_STAT_AREA]
        length = np.hypot(w, h) / R.PPM
        keep[i] = length >= 5.0 and (a / R.PPM ** 2) / length < 1.1
    return keep[lab]


def build_photo_face(bgr: np.ndarray, *, ink_t: float = 0.5, tone_ths=(0.22, 0.32, 0.45),
                     hatch_levels=HATCH_LEVELS, colour_line_kw: dict | None = None,
                     seed: int = 1, angle_by_region: bool = True,
                     tone_exclude: np.ndarray | None = None) -> dict[str, np.ndarray]:
    ink, tone = R.photo_layers(bgr, ink_t=ink_t)
    ink = R.remove_small(ink, 0.12)
    lines = ink.copy()
    if colour_line_kw is not None:
        lines |= colour_lines(bgr, tone, **colour_line_kw)
    excl = cv2.dilate(R.u8(lines), R.disk(R.px(0.7))).astype(bool)
    if tone_exclude is not None:
        excl |= tone_exclude
    lev = R.quantize_tone(tone, list(tone_ths), exclude=excl)
    clear = ~cv2.dilate(R.u8(lines), R.disk(2 * R.px(0.4) + 1)).astype(bool)

    tone_ink = np.zeros(lev.shape, bool)
    if angle_by_region:
        # each pencil-filled area gets its own hatch direction, like a hand
        # that turns the page: angle picked per connected tone region.
        n, lab = cv2.connectedComponents(R.u8(lev > 0), connectivity=8)
        rng = np.random.default_rng(seed)
        angles = rng.choice([45, 30, 60, 135, 120, 50], size=n)
        for i in range(1, n):
            reg = lab == i
            ys, xs = np.where(reg)
            y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            sub_lev = np.where(reg[y0:y1, x0:x1], lev[y0:y1, x0:x1], 0)
            spec = []
            for s in hatch_levels:
                passes = s.get("passes", [s])
                rot = [dict(p, angle_deg=p["angle_deg"] - 45 + angles[i]) for p in passes]
                spec.append({"passes": rot})
            tone_ink[y0:y1, x0:x1] |= R.tone_hatch(sub_lev, clear[y0:y1, x0:x1], spec, seed=seed + i)
    else:
        tone_ink = R.tone_hatch(lev, clear, hatch_levels, seed=seed)
    return {"lines": lines, "tone": tone_ink, "levels": lev}
