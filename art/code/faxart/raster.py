"""Raster stages of the code-drawn art pipeline (all deterministic).

Working resolution: PPM px per mm (20 px/mm = 0.05 mm/px). Ink masks are
bool arrays, True = engrave.

Laser rules (enforced here, verified on the traced SVG by
tests/test_code_art.py):
    MIN_LINE_MM  0.25  thinnest engraved line
    MIN_GAP_MM   0.30  thinnest unburned gap between engraved areas
    SPECK_MM2    0.09  smallest engraved island / unburned pinhole kept
"""

from __future__ import annotations

import math

import cv2
import numpy as np
from skimage.morphology import skeletonize

PPM = 20.0
MIN_LINE_MM = 0.25
MIN_GAP_MM = 0.30
SPECK_MM2 = 0.09
KEEPOUT_MM = 0.55   # art stays >= 0.45 mm from every cut after curve fitting


def px(mm: float) -> int:
    return max(1, int(round(mm * PPM)))


def disk(d_px: int) -> np.ndarray:
    # always odd: an even cv2 kernel is off-centre and shifts edges by a pixel
    d = max(1, int(d_px)) | 1
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (d, d))


def u8(m: np.ndarray) -> np.ndarray:
    return m.astype(np.uint8)


# ---------------------------------------------------------------- sources

def warp_to_canvas(img: np.ndarray, src_quad, size_mm, border=255) -> np.ndarray:
    """Perspective-map the source quad (TL, TR, BR, BL in source px) onto the
    full canvas of size_mm at PPM. Pre-shrinks with INTER_AREA when the
    source is much denser than the canvas so thin lines don't alias."""
    W, H = int(round(size_mm[0] * PPM)), int(round(size_mm[1] * PPM))
    q = np.array(src_quad, dtype=np.float64)
    src_w = max(np.linalg.norm(q[1] - q[0]), np.linalg.norm(q[2] - q[3]))
    shrink = W / src_w
    if shrink < 0.7:
        f = shrink / 0.85
        img = cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        q = q * f
    dst = np.array([[0, 0], [W, 0], [W, H], [0, H]], dtype=np.float64)
    M = cv2.getPerspectiveTransform(q.astype(np.float32), dst.astype(np.float32))
    bv = (border,) * (img.shape[2] if img.ndim == 3 else 1)
    return cv2.warpPerspective(img, M, (W, H), flags=cv2.INTER_CUBIC,
                               borderMode=cv2.BORDER_CONSTANT, borderValue=bv)


def warp_strip(img: np.ndarray, x_range, top_poly, bot_poly, size_mm, inset_px=(8, 8),
               border=255) -> np.ndarray:
    """Unroll a photographed side panel whose top/bottom cardboard edges are
    gently curved (lens + perspective): output column u maps linearly onto
    source x in x_range; each column's rows span from the fitted top edge
    (+inset) to the fitted bottom edge (-inset). Polys are numpy.polyval
    coefficients of y(x) in source px."""
    W, H = int(round(size_mm[0] * PPM)), int(round(size_mm[1] * PPM))
    x0, x1 = x_range
    sx = x0 + (np.arange(W, dtype=np.float64) + 0.5) / W * (x1 - x0)
    yt = np.polyval(top_poly, sx) + inset_px[0]
    yb = np.polyval(bot_poly, sx) - inset_px[1]
    v = (np.arange(H, dtype=np.float64) + 0.5) / H
    map_x = np.broadcast_to(sx[None, :], (H, W)).astype(np.float32)
    map_y = (yt[None, :] + v[:, None] * (yb - yt)[None, :]).astype(np.float32)
    bv = (border,) * (img.shape[2] if img.ndim == 3 else 1)
    return cv2.remap(img, map_x, map_y, interpolation=cv2.INTER_CUBIC,
                     borderMode=cv2.BORDER_CONSTANT, borderValue=bv)


def warp_affine(img: np.ndarray, M: np.ndarray, size_mm, border=255) -> np.ndarray:
    """M maps source px -> canvas px (2x3)."""
    W, H = int(round(size_mm[0] * PPM)), int(round(size_mm[1] * PPM))
    scale = math.sqrt(abs(np.linalg.det(M[:, :2])))
    if scale < 0.7:
        f = scale / 0.85
        img = cv2.resize(img, None, fx=f, fy=f, interpolation=cv2.INTER_AREA)
        M = M.copy()
        M[:, :2] = M[:, :2] / f
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=border)


def threshold_gray(gray: np.ndarray, t: int = 128, blur_px: float = 0.7) -> np.ndarray:
    g = cv2.GaussianBlur(gray, (0, 0), blur_px) if blur_px > 0 else gray
    return g < t


def photo_layers(bgr: np.ndarray, ink_t: float = 0.5, bg_mm: float = 6.0, sat_max: float = 1.0):
    """Split a colour photo of marker + coloured pencil into
    (ink mask, pencil darkness 0..1).

    ink   = black marker: dark in ALL channels (max channel) relative to the
            local background (large grey closing, survives lighting gradients
            and stays outside marker strokes up to ~bg_mm wide).
    tone  = coloured-pencil darkness: luminance below the paper estimate
            (a very large closing), ink excluded.
    """
    value = bgr.max(axis=2)
    value = cv2.medianBlur(value, 5)
    small = cv2.resize(value, None, fx=0.25, fy=0.25, interpolation=cv2.INTER_AREA)
    k = disk(int(bg_mm * PPM * 0.25) | 1)
    bg = cv2.morphologyEx(small, cv2.MORPH_CLOSE, k)
    bg = cv2.GaussianBlur(bg, (0, 0), 3)
    bg = cv2.resize(bg, (value.shape[1], value.shape[0]), interpolation=cv2.INTER_CUBIC)
    norm = value.astype(np.float32) / np.maximum(bg.astype(np.float32), 1)
    ink = norm < ink_t
    if sat_max < 1.0:
        # black marker is neutral; dark coloured pencil (night sky) is not
        sat = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[:, :, 1].astype(np.float32) / 255.0
        ink &= cv2.GaussianBlur(sat, (0, 0), 2.0) < sat_max

    lum = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)[:, :, 0].astype(np.float32)
    s2 = cv2.resize(lum, None, fx=0.1, fy=0.1, interpolation=cv2.INTER_AREA)
    paper = cv2.morphologyEx(s2, cv2.MORPH_CLOSE, disk(int(40 * PPM * 0.1) | 1))
    paper = cv2.GaussianBlur(paper, (0, 0), 8)
    paper = cv2.resize(paper, (lum.shape[1], lum.shape[0]), interpolation=cv2.INTER_CUBIC)
    tone = np.clip(1.0 - lum / np.maximum(paper, 1), 0, 1)
    return ink, tone


# ---------------------------------------------------------------- cleanup

def remove_small(mask: np.ndarray, min_mm2: float = SPECK_MM2) -> np.ndarray:
    min_px = min_mm2 * PPM * PPM
    n, lab, st, _ = cv2.connectedComponentsWithStats(u8(mask), connectivity=8)
    keep = st[:, cv2.CC_STAT_AREA] >= min_px
    keep[0] = False
    return keep[lab]


def fill_pinholes(mask: np.ndarray, min_mm2: float = SPECK_MM2) -> np.ndarray:
    return ~remove_small(~mask, min_mm2)


def thicken_to_min(mask: np.ndarray, min_mm: float = 0.35) -> np.ndarray:
    """Every stroke at least min_mm wide: dilate the skeleton by min/2 and
    union. Strokes already wider are untouched (the disk fits inside)."""
    sk = skeletonize(mask)
    r = int(round(min_mm * PPM / 2))
    return mask | cv2.dilate(u8(sk), disk(2 * r + 1)).astype(bool)


def stripes(shape, pitch_mm: float, width_mm: float, angle_deg: float, phase: float = 0.0) -> np.ndarray:
    H, W = shape
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    a = math.radians(angle_deg)
    d = (xx * math.sin(a) - yy * math.cos(a)) / PPM + phase
    return np.mod(d, pitch_mm) < width_mm


def line_angles(ink: np.ndarray, sigma_mm: float = 1.5) -> np.ndarray:
    """Per-pixel dominant stroke direction (degrees, image coords) from the
    structure tensor of the ink."""
    f = cv2.GaussianBlur(ink.astype(np.float32), (0, 0), 1.2)
    gx = cv2.Sobel(f, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(f, cv2.CV_32F, 0, 1, ksize=3)
    s = sigma_mm * PPM
    jxx = cv2.GaussianBlur(gx * gx, (0, 0), s)
    jyy = cv2.GaussianBlur(gy * gy, (0, 0), s)
    jxy = cv2.GaussianBlur(gx * gy, (0, 0), s)
    return jxx, jyy, jxy


def knock_out_solids(mask: np.ndarray, protect: np.ndarray | None = None, solid_mm: float = 2.4,
                     border_mm: float = 0.6, pitch_mm: float = 1.05, gap_mm: float = 0.48,
                     orient_from: np.ndarray | None = None, seed: int = 3,
                     min_area_mm2: float = 45.0
                     ) -> tuple[np.ndarray, np.ndarray]:
    """Large solid blacks char and take forever, and merged dense hatching is
    the same problem. Keep a border_mm rim and cut gap_mm unburned channels
    through the interior so it reads as heavy hatching. The channels are drawn
    with the same hand-stroke generator as the hatching, and each solid area's
    channels run along the dominant stroke direction of the ORIGINAL drawing
    there (structure tensor of `orient_from`), so merged hatch reopens in
    roughly its own direction. Regions in `protect` (display lettering) stay
    solid. Returns (new mask, the solid-core mask that was opened up)."""
    big = cv2.morphologyEx(u8(mask), cv2.MORPH_OPEN, disk(px(solid_mm))).astype(bool)
    core = cv2.erode(u8(big), disk(2 * px(border_mm) + 1)).astype(bool)
    if protect is not None:
        core &= ~protect
    # small solids (pupils, buttons, a beak tip) burn fine and carry the
    # drawing's punch: only open up solid areas bigger than min_area_mm2
    big = remove_small(big, min_area_mm2)
    core &= big
    if not core.any():
        return mask, core
    J = line_angles(orient_from if orient_from is not None else mask)
    n, lab, st, _ = cv2.connectedComponentsWithStats(u8(core), connectivity=8)
    cut = np.zeros(mask.shape, bool)
    for i in range(1, n):
        x, y, w, h = st[i, 0], st[i, 1], st[i, 2], st[i, 3]
        sl = (slice(y, y + h), slice(x, x + w))
        reg = lab[sl] == i
        jxx, jyy, jxy = (j[sl][reg].mean() for j in J)
        coh = math.hypot(jxx - jyy, 2 * jxy) / max(jxx + jyy, 1e-6)
        if coh > 0.15:
            grad = 0.5 * math.degrees(math.atan2(2 * jxy, jxx - jyy))
            ang = grad + 90.0
        else:
            ang = 45.0
        cut[sl] |= hatch(reg, pitch_mm=pitch_mm, angle_deg=ang, width_mm=gap_mm, seed=seed + i,
                         trim_mm=(0.0, 0.2), stroke_mm=(6, 16), lift_mm=(0.5, 1.0),
                         jitter_deg=0.8, wobble_mm=0.05, offset_jitter=0.03)
    return mask & ~cut, core


def _eopen(m: np.ndarray, r_px: float) -> np.ndarray:
    """Exact Euclidean opening by a disk of radius r_px."""
    from scipy import ndimage as ndi
    c = ndi.distance_transform_edt(m) > r_px
    return ndi.distance_transform_edt(~c) <= r_px


def enforce_laser_rules(mask: np.ndarray, material: np.ndarray | None = None,
                        rounds: int = 3) -> np.ndarray:
    """Guarantee min line / min gap / speck rules with exact Euclidean
    morphology and a margin over the rules (line 0.30 mm, gap 0.40 mm), so
    the traced curves still pass at 40 px/mm. Ends on the gap pass: an
    opening last would cut thin necks and leave new narrow gaps."""
    r_line = 0.15 * PPM
    r_gap = 0.20 * PPM
    m = mask
    for _ in range(rounds):
        if material is not None:
            m = m & material
        m = _eopen(m, r_line)
        m = remove_small(m)
        m = ~_eopen(~m, r_gap)          # closing = opening of the paper
        if material is not None:
            m = m & material
        m = fill_pinholes(m)
    return fill_pinholes(remove_small(m, 1.4 * SPECK_MM2), 1.4 * SPECK_MM2)


# ---------------------------------------------------------------- coded hatching

def hatch(region: np.ndarray, pitch_mm: float, angle_deg: float, width_mm: float = 0.35,
          seed: int = 0, phase_mm: float | None = None, stroke_mm: tuple[float, float] = (3.0, 9.0),
          lift_mm: tuple[float, float] = (0.3, 0.9), trim_mm: tuple[float, float] = (0.1, 0.5),
          min_len_mm: float = 0.9, jitter_deg: float = 2.2, wobble_mm: float = 0.09,
          offset_jitter: float = 0.07) -> np.ndarray:
    """Hand hatching in code. Parallel rows at `pitch_mm`; along each row the
    region is filled with SHORT strokes (stroke_mm long, small pen-lift gaps
    between them), each stroke with its own tiny angle tilt, sideways offset
    and a gentle bow, and ragged ends that stop short of the region edge.
    Short strokes keep the jitter from ever drifting rows into each other, so
    the gap between rows stays ~pitch - width everywhere.
    Returns a bool ink mask clipped to `region`."""
    rng = np.random.default_rng(seed)
    H, W = region.shape
    canvas = np.zeros((H, W), np.uint8)
    diag = math.hypot(W, H) / PPM
    cx, cy = W / PPM / 2, H / PPM / 2
    a = math.radians(angle_deg)
    dx, dy = math.cos(a), math.sin(a)
    nx, ny = -dy, dx
    step = 0.1
    tt = np.arange(-diag / 2, diag / 2, step)
    off = -diag / 2 + (rng.uniform(0, pitch_mm) if phase_mm is None else phase_mm)
    wpx = max(1, int(round(width_mm * PPM)))
    while off < diag / 2:
        xs = cx + nx * off + dx * tt
        ys = cy + ny * off + dy * tt
        ix = np.round(xs * PPM).astype(int)
        iy = np.round(ys * PPM).astype(int)
        ok = (ix >= 0) & (ix < W) & (iy >= 0) & (iy < H)
        if ok.any():
            inside = np.zeros(len(tt), bool)
            inside[ok] = region[iy[ok], ix[ok]]
            if inside.any():
                dd = np.diff(np.concatenate(([0], inside.astype(np.int8), [0])))
                for s, e in zip(np.where(dd == 1)[0], np.where(dd == -1)[0]):
                    t0 = tt[s] + rng.uniform(*trim_mm)
                    t1 = tt[e - 1] - rng.uniform(*trim_mm)
                    t = t0
                    while t1 - t >= min_len_mm:
                        L = rng.uniform(*stroke_mm)
                        te = min(t + L, t1)
                        if t1 - te < min_len_mm + 0.3:
                            te = t1
                        n = max(2, int((te - t) / 0.4) + 1)
                        u = np.linspace(0, 1, n)
                        tilt = math.radians(rng.uniform(-jitter_deg, jitter_deg))
                        o = off + rng.uniform(-offset_jitter, offset_jitter) * pitch_mm
                        bow = rng.uniform(-wobble_mm, wobble_mm) * np.sin(np.pi * u)
                        tc = (t + te) / 2
                        along = t + u * (te - t)
                        side = o + bow + (along - tc) * math.tan(tilt)
                        px_ = (cx + nx * side + dx * along) * PPM
                        py_ = (cy + ny * side + dy * along) * PPM
                        pts = np.stack([px_, py_], 1)
                        cv2.polylines(canvas, [np.round(pts * 16).astype(np.int32)], False, 255,
                                      thickness=wpx, lineType=cv2.LINE_AA, shift=4)
                        t = te + rng.uniform(*lift_mm)
        off += pitch_mm
    return (canvas > 110) & region


def tone_hatch(levels: np.ndarray, region_ok: np.ndarray, spec: list[dict], seed: int = 0) -> np.ndarray:
    """levels: int array (0 = no tone). spec[i] = hatch kwargs for level i+1;
    a level may list several passes (crosshatch) under key 'passes'."""
    out = np.zeros(levels.shape, bool)
    for i, s in enumerate(spec, start=1):
        reg = (levels >= i) & region_ok
        if not reg.any():
            continue
        for j, p in enumerate(s.get("passes", [s])):
            out |= hatch(reg, seed=seed * 101 + i * 7 + j, **p)
    return out


def quantize_tone(tone: np.ndarray, thresholds: list[float], smooth_mm: float = 0.8,
                  min_area_mm2: float = 20.0, exclude: np.ndarray | None = None) -> np.ndarray:
    t = cv2.GaussianBlur(tone.astype(np.float32), (0, 0), smooth_mm * PPM)
    lev = np.zeros(t.shape, np.int32)
    for i, th in enumerate(thresholds, start=1):
        m = t > th
        if exclude is not None:
            m &= ~exclude
        m = cv2.morphologyEx(u8(m), cv2.MORPH_OPEN, disk(px(0.8))).astype(bool)
        m = remove_small(m, min_area_mm2)
        lev[m] = i
    return lev
