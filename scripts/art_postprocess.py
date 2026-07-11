#!/usr/bin/env python3
"""Deterministic, re-runnable art post-processing pipeline.

Takes the canonical accepted art in art/ai-versions/final/*.png and produces
one true 1-bit PNG per physical part, at exact 300-DPI target pixel size, in
art/engrave/. Also writes art/engrave/PLACEMENTS.md documenting every
processing step, crop window, deskew angle, and feature-size audit result.

No args: running this script processes everything. Safe to re-run any time;
it always re-derives output from the frozen sources in art/ai-versions/final/
and never touches that directory.

See art/ai-versions/SPECS.md ("STATUS 2026-07-09", "Split-generate-merge",
per-face table, "Post-processing") and art/pilot/PARAMS.md +
art/pilot/extract_lines.py for the background/technique this implements.
"""
import os
import sys
import numpy as np
import cv2
from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(REPO, "art", "ai-versions", "final")
OUT = os.path.join(REPO, "art", "engrave")
DPI = 300.0
PX_PER_MM = DPI / 25.4  # 11.8110...

os.makedirs(OUT, exist_ok=True)

LOG = []  # list of dict, one per output part, for PLACEMENTS.md


def log(part, **kw):
    d = {"part": part}
    d.update(kw)
    LOG.append(d)


# ---------------------------------------------------------------- helpers --

def load_gray(name):
    path = os.path.join(SRC, name)
    im = Image.open(path).convert("L")
    return np.array(im), path


def mm_to_px(mm):
    return mm * PX_PER_MM


def threshold_bit(arr_gray, thresh=128):
    """Global threshold to 0/255 uint8. Foreground(ink)=0? no: returns
    255=white(background), 0=black(ink) i.e. standard photo convention where
    low grey value = ink. We keep this convention (0=ink) throughout and only
    flip to PIL mode '1' (bilevel, 255=white) at save time."""
    return np.where(arr_gray < thresh, 0, 255).astype(np.uint8)


def remove_speckle(bit_img, min_area=4):
    """Defensive cleanup: drop isolated ink specks smaller than min_area px^2
    (antialiasing/resample noise), at native working resolution. Does not
    touch real strokes/hatching (those are elongated & connected, not
    isolated sub-5px blobs)."""
    ink = (bit_img == 0).astype(np.uint8)
    num, labels, stats, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
    out = np.full_like(bit_img, 255)
    removed = 0
    for i in range(1, num):
        if stats[i, cv2.CC_STAT_AREA] >= min_area:
            out[labels == i] = 0
        else:
            removed += 1
    return out, removed


def resize_area_rethreshold(bit_img, target_w, target_h, thresh=127):
    """Rule 5: downscale a 1-bit image by area-averaging (never leave grays),
    then re-threshold at the target resolution. If a dimension needs
    upscaling, use nearest-neighbor (integer-friendly) + re-threshold
    instead of a blurring interpolant."""
    src_h, src_w = bit_img.shape
    need_up = target_w > src_w or target_h > src_h
    if need_up:
        resized = cv2.resize(bit_img, (target_w, target_h), interpolation=cv2.INTER_NEAREST)
    else:
        resized = cv2.resize(bit_img, (target_w, target_h), interpolation=cv2.INTER_AREA)
    out = np.where(resized < thresh, 0, 255).astype(np.uint8)
    return out


def save_bit_png(bit_img, path):
    """bit_img: uint8 array, 0=ink,255=white. Save as true mode '1' PNG."""
    assert set(np.unique(bit_img).tolist()) <= {0, 255}, "not pure bilevel!"
    pil = Image.fromarray(bit_img, mode="L").convert("1")
    pil.save(path)


def feature_audit(bit_img, px_per_mm=PX_PER_MM):
    """Estimate thinnest positive (ink stroke) and negative (white gap)
    feature widths, in mm, via distance-transform local maxima (medial-axis
    proxy): for each blob, the ridge of the distance transform equals half
    the local stroke/gap width; take a low percentile across all ridge
    points (robust to single noisy pixels) as the "thinnest" estimate.
    """
    def thinnest(mask_uint8):
        if mask_uint8.sum() == 0:
            return None
        dist = cv2.distanceTransform(mask_uint8, cv2.DIST_L2, 5)
        dil = cv2.dilate(dist, np.ones((7, 7), np.uint8))
        ridge = (dist == dil) & (mask_uint8 > 0) & (dist > 0.4)
        vals = dist[ridge]
        if vals.size < 5:
            vals = dist[mask_uint8 > 0]
            if vals.size == 0:
                return None
        widths_px = 2.0 * vals
        p5 = np.percentile(widths_px, 5)
        return p5 / px_per_mm

    ink = (bit_img == 0).astype(np.uint8)
    white = (bit_img == 255).astype(np.uint8)
    pos = thinnest(ink)
    neg = thinnest(white)
    return pos, neg


def robust_content_bbox(bit_img, min_ink=3):
    """Rev-3 UNIVERSAL RULE, part 1: a robust content bounding box. Only rows/
    cols carrying >= min_ink ink pixels count as "content", so a lone
    antialiasing/resample speck can't drag the bbox out toward the generation
    canvas's white margin. Returns (top, bottom, left, right), all inclusive,
    in bit_img's own pixel coordinates. bit_img: 0=ink, 255=white."""
    ink = (bit_img == 0)
    row_counts = ink.sum(axis=1)
    col_counts = ink.sum(axis=0)
    rows = np.where(row_counts >= min_ink)[0]
    cols = np.where(col_counts >= min_ink)[0]
    if rows.size == 0 or cols.size == 0:
        raise ValueError("robust_content_bbox: no content found")
    return int(rows.min()), int(rows.max()), int(cols.min()), int(cols.max())


def cover_fit(bit_img, box, target_w, target_h, bias_v=None, bias_h=None):
    """Rev-3 UNIVERSAL RULE, part 2: CSS-'cover' fit. Crop bit_img to
    box=(top,bottom,left,right) inclusive, then scale by
    scale=max(target_w/content_w, target_h/content_h) so BOTH target
    dimensions are completely filled (no residual white space on any side);
    the axis with slack overflows the target and is cropped.

    bias_v='top'|'bottom'|None: 'top' keeps the top edge flush and trims all
    vertical overflow off the bottom; 'bottom' keeps the bottom edge flush
    and trims all overflow off the top; None (default) centers the crop.
    bias_h analogous with 'left'/'right'. Use bias only where centering would
    obviously cut into real content the wrong way (e.g. drawer-side sky vs.
    feet/ground) -- default is a plain center crop.

    Returns (final_bit_img, info dict) -- info reports the content box, the
    exact scale factor, the resulting overflow, and the crop actually taken,
    all needed for the PLACEMENTS.md per-face report.

    BBOX/CROP INTERACTION (caught by rev-3 QA): a naive single pass can
    still leave a blank edge row/column -- the >=3-ink-px pixels that
    justified one axis's bbox edge may live entirely inside the band the
    OTHER axis's crop removes (observed on drawer_side_4: the ink holding up
    its left bbox edge sat wholly inside the sky band the top-crop deleted,
    leaving output column 0 fully white). Fix: iterate -- after choosing the
    crop window, map the kept region back to source coordinates, recompute
    the robust bbox WITHIN that kept region, and re-fit; stop when the bbox
    is stable (converges in 1-2 extra passes; hard cap 5).
    """
    def _one_pass(b):
        top, bottom, left, right = b
        content = bit_img[top:bottom + 1, left:right + 1]
        ch, cw = content.shape
        scale = max(target_w / cw, target_h / ch)
        scaled_w = max(target_w, int(round(cw * scale)))
        scaled_h = max(target_h, int(round(ch * scale)))
        if scale >= 1.0:
            scaled = cv2.resize(content, (scaled_w, scaled_h), interpolation=cv2.INTER_NEAREST)
            scaled = np.where(scaled < 127, 0, 255).astype(np.uint8)
        else:
            scaled = resize_area_rethreshold(content, scaled_w, scaled_h)

        excess_w = scaled_w - target_w
        excess_h = scaled_h - target_h
        if bias_v == "top":
            crop_top = 0
        elif bias_v == "bottom":
            crop_top = excess_h
        else:
            crop_top = excess_h // 2
        if bias_h == "left":
            crop_left = 0
        elif bias_h == "right":
            crop_left = excess_w
        else:
            crop_left = excess_w // 2

        final = scaled[crop_top:crop_top + target_h, crop_left:crop_left + target_w]
        meta = dict(content_wh=(cw, ch), scale=scale, scaled_wh=(scaled_w, scaled_h),
                    excess_w_px=excess_w, excess_h_px=excess_h,
                    crop_top_px=crop_top, crop_left_px=crop_left)
        return final, meta

    iterations = 0
    final, meta = None, None
    for _ in range(5):
        iterations += 1
        final, meta = _one_pass(box)
        top, bottom, left, right = box
        scale = meta["scale"]
        # Map the kept window back to source coordinates (floor the start,
        # ceil the end, so no real content pixel is dropped by rounding).
        kept_l = left + int(meta["crop_left_px"] / scale)
        kept_r = min(right, left + int(np.ceil((meta["crop_left_px"] + target_w) / scale)) - 1)
        kept_t = top + int(meta["crop_top_px"] / scale)
        kept_b = min(bottom, top + int(np.ceil((meta["crop_top_px"] + target_h) / scale)) - 1)
        sub = bit_img[kept_t:kept_b + 1, kept_l:kept_r + 1]
        try:
            st, sb, sl, sr = robust_content_bbox(sub, min_ink=3)
        except ValueError:
            break  # kept region somehow empty -- keep last fit
        new_box = (kept_t + st, kept_t + sb, kept_l + sl, kept_l + sr)
        if new_box == box:
            break
        box = new_box

    info = dict(content_box=box, bias_v=bias_v, bias_h=bias_h,
                bbox_iterations=iterations, **meta)
    return final, info


def balanced_fit(bit_img, box, target_w, target_h):
    """Content-aware alternative to cover_fit() for content whose aspect
    ratio is grossly mismatched with the target -- where pure cover-fit's
    forced crop would delete whole glyphs/features rather than just trim
    margin (measured case: the faceplate wordmarks). Picks the unique scale
    s between contain-fit (s=min(target_w/cw, target_h/ch): zero crop, full
    padding) and cover-fit (s=max(...): zero padding, full crop) that makes
    the LEFTOVER crop and the LEFTOVER pad numerically equal in mm:

        s * (cw + ch) = target_w + target_h

    (derived by setting cw*s - target_w == target_h - ch*s and solving for
    s). This trims a little off the content's long axis AND pads a little
    on its short axis, instead of taking either all the way to its
    destructive extreme. Only reach for this where cover_fit's crop is
    independently verified (by eye) to be destructive -- it is NOT the
    default rev-3 behavior.
    """
    top, bottom, left, right = box
    content = bit_img[top:bottom + 1, left:right + 1]
    ch, cw = content.shape
    s = (target_w + target_h) / (cw + ch)
    scaled_w = max(1, int(round(cw * s)))
    scaled_h = max(1, int(round(ch * s)))
    if s >= 1.0:
        scaled = cv2.resize(content, (scaled_w, scaled_h), interpolation=cv2.INTER_NEAREST)
        scaled = np.where(scaled < 127, 0, 255).astype(np.uint8)
    else:
        scaled = resize_area_rethreshold(content, scaled_w, scaled_h)

    # width: crop if it overflows, else center-pad
    if scaled_w >= target_w:
        off = (scaled_w - target_w) // 2
        w_slice = scaled[:, off:off + target_w]
        dst_x0, crop_l_px, crop_r_px, pad_l_px, pad_r_px = 0, off, scaled_w - target_w - off, 0, 0
    else:
        pad_l_px = (target_w - scaled_w) // 2
        pad_r_px = target_w - scaled_w - pad_l_px
        w_slice = scaled
        dst_x0, crop_l_px, crop_r_px = pad_l_px, 0, 0

    # height: crop if it overflows, else center-pad
    canvas = np.full((target_h, target_w), 255, dtype=np.uint8)
    if scaled_h >= target_h:
        offh = (scaled_h - target_h) // 2
        h_slice = w_slice[offh:offh + target_h, :]
        crop_t_px, crop_b_px, pad_t_px, pad_b_px = offh, scaled_h - target_h - offh, 0, 0
        canvas[:, dst_x0:dst_x0 + h_slice.shape[1]] = h_slice
    else:
        pad_t_px = (target_h - scaled_h) // 2
        pad_b_px = target_h - scaled_h - pad_t_px
        crop_t_px, crop_b_px = 0, 0
        canvas[pad_t_px:pad_t_px + scaled_h, dst_x0:dst_x0 + w_slice.shape[1]] = w_slice
    canvas = np.where(canvas < 127, 0, 255).astype(np.uint8)

    info = dict(
        content_box=box, content_wh=(cw, ch), scale=s, scaled_wh=(scaled_w, scaled_h),
        crop_l_mm=crop_l_px / PX_PER_MM, crop_r_mm=crop_r_px / PX_PER_MM,
        crop_t_mm=crop_t_px / PX_PER_MM, crop_b_mm=crop_b_px / PX_PER_MM,
        pad_l_mm=pad_l_px / PX_PER_MM, pad_r_mm=pad_r_px / PX_PER_MM,
        pad_t_mm=pad_t_px / PX_PER_MM, pad_b_mm=pad_b_px / PX_PER_MM,
    )
    return canvas, info


# ------------------------------------------------------------- face specs --

# CAUTION (rev-3 QA note): the pixel dims below were fixed by hand from the
# SPECS table. Some entries equal round(mm * PX_PER_MM), others equal
# int(mm * PX_PER_MM) (truncation) -- and process_4231 derives its own px
# via int(mm_to_px(...)). Today every value agrees with the runtime math
# (verified for all 13 outputs), but if you regenerate this table for new
# mm values, pick ONE convention (int/trunc, matching mm_to_px usage) or
# the panel-slice == FACE_TARGETS asserts in process_4231 may fire.
FACE_TARGETS = {
    "left_wall": (298.45, 127.0, 3525, 1500),
    "right_wall": (298.45, 127.0, 3525, 1500),
    "front_wall": (158.75, 118.025, 1875, 1394),
    "sliding_lid": (163.6, 79.0, 1932, 933),
    "top_panel": (222.25, 158.75, 2625, 1875),
    "faceplate_colors": (150.9, 53.5, 1782, 632),
    "faceplate_lines": (150.9, 53.5, 1782, 632),
    "drawer_side_1": (212.25, 50.325, 2507, 594),
    "drawer_side_2": (212.25, 50.325, 2507, 594),
    "drawer_side_3": (212.25, 50.325, 2507, 594),
    "drawer_side_4": (212.25, 50.325, 2507, 594),
}


# ------------------------------------------------------------------ faces --

def _cover_fit_steps(box, info, tw, th):
    """Shared PLACEMENTS.md step-text for a robust-bbox + cover-fit face.
    `box` is the caller's INITIAL robust bbox; info['content_box'] is the
    CONVERGED bbox after cover_fit's bbox/crop iteration (identical when the
    fit converged in one pass)."""
    top, bottom, left, right = info["content_box"]
    cw, ch = info["content_wh"]
    sw, sh = info["scaled_wh"]
    ex_w_mm = info["excess_w_px"] / PX_PER_MM
    ex_h_mm = info["excess_h_px"] / PX_PER_MM
    crop_l_mm = info["crop_left_px"] / PX_PER_MM
    crop_r_mm = (info["excess_w_px"] - info["crop_left_px"]) / PX_PER_MM
    crop_t_mm = info["crop_top_px"] / PX_PER_MM
    crop_b_mm = (info["excess_h_px"] - info["crop_top_px"]) / PX_PER_MM
    bias_note = f"bias_v={info['bias_v'] or 'center'}, bias_h={info['bias_h'] or 'center'}"
    n_iter = info.get("bbox_iterations", 1)
    if n_iter > 1:
        it0, ib0, il0, ir0 = box
        bbox_step = (
            f"ROBUST content bbox (rows/cols with >=3 ink px), CONVERGED over "
            f"{n_iter} bbox/crop iterations (initial bbox rows {it0}-{ib0} "
            f"cols {il0}-{ir0} was held up at one edge only by ink inside a "
            f"band the cross-axis crop removes -- see cover_fit docstring): "
            f"final rows {top}-{bottom}, cols {left}-{right} -> {cw}x{ch}px content"
        )
    else:
        bbox_step = (
            f"ROBUST content bbox (rows/cols with >=3 ink px): rows {top}-{bottom}, "
            f"cols {left}-{right} -> {cw}x{ch}px content"
        )
    return [
        bbox_step,
        f"COVER-fit to {tw}x{th}px target: scale=max({tw}/{cw}, {th}/{ch})="
        f"{info['scale']:.4f} -> scaled content {sw}x{sh}px "
        f"(overflow {ex_w_mm:.2f}mm wide / {ex_h_mm:.2f}mm tall, {bias_note})",
        f"edge crop taken from the overflow: left {crop_l_mm:.2f}mm / right "
        f"{crop_r_mm:.2f}mm / top {crop_t_mm:.2f}mm / bottom {crop_b_mm:.2f}mm "
        "(both target dimensions now fully bled, zero white margin)",
    ]


def process_simple_wall(name, src_name, target_key, notes, bias_v=None, bias_h=None):
    """side walls + front wall: threshold -> robust content bbox -> COVER-fit
    (both target dims fully bled, per Ben's rev-3 'no white space' rule)."""
    gray, path = load_gray(src_name)
    w_mm, h_mm, tw, th = FACE_TARGETS[target_key]

    bit = threshold_bit(gray, 128)
    bit, removed = remove_speckle(bit, min_area=4)

    box = robust_content_bbox(bit, min_ink=3)
    final, info = cover_fit(bit, box, tw, th, bias_v=bias_v, bias_h=bias_h)

    out_path = os.path.join(OUT, f"{name}.png")
    save_bit_png(final, out_path)
    pos, neg = feature_audit(final)

    log(name, source=src_name, source_px=f"{gray.shape[1]}x{gray.shape[0]}",
        steps=notes + [
            f"global threshold @128 (0=ink)",
            f"speckle cleanup: dropped {removed} components <4px^2",
        ] + _cover_fit_steps(box, info, tw, th),
        final_px=f"{tw}x{th}", canvas_mm=f"{w_mm}x{h_mm}",
        feature_pos_mm=pos, feature_neg_mm=neg)


def process_left_wall():
    gray, path = load_gray("IMG_4228_ai_vH1.png")
    h, w = gray.shape
    # measured border stroke: top rows 39-52, bottom rows 2632-2645,
    # left cols 51-65, right cols 6270-6284 (drawn frame border, per SPECS
    # "known cosmetic debt" -> BRIEF decision: drop the frame, panel edges
    # do the framing). Crop just inside it with a small safety buffer.
    box = (70, 57, w - 70, h - 60)  # (left,top,right,bottom) inside the border
    inner = gray[box[1]:box[3], box[0]:box[2]]

    w_mm, h_mm, tw, th = FACE_TARGETS["left_wall"]
    bit = threshold_bit(inner, 128)
    bit, removed = remove_speckle(bit, min_area=4)

    box2 = robust_content_bbox(bit, min_ink=3)
    final, info = cover_fit(bit, box2, tw, th)

    out_path = os.path.join(OUT, "left_wall.png")
    save_bit_png(final, out_path)
    pos, neg = feature_audit(final)

    log("left_wall", source="IMG_4228_ai_vH1.png", source_px=f"{w}x{h}",
        steps=[
            "JUDGMENT CALL: source carries a drawn rectangular border frame "
            "(measured: top rows 39-52, bottom rows 2632-2645, left cols "
            "51-65, right cols 6270-6284, ~14px stroke). Per SPECS 'known "
            "cosmetic debt' + BRIEF decision: dropped the frame (crop "
            f"inside it); panel edges do the framing. Inner crop box "
            f"(l,t,r,b)={box} on the {w}x{h} source.",
            "global threshold @128 (0=ink)",
            f"speckle cleanup: dropped {removed} components <4px^2",
        ] + _cover_fit_steps(box2, info, tw, th),
        final_px=f"{tw}x{th}", canvas_mm=f"{w_mm}x{h_mm}",
        feature_pos_mm=pos, feature_neg_mm=neg)


def _erase_funfor(final_bit):
    """VARIANT builder (Ben's 2026-07-11 feedback #4, decision pending): erase
    the six 'Fun For' lead-in glyphs from the finished right_wall placement,
    leaving every other stroke bit-identical. Motivation (measured, see
    scratch/title-shift/): the lid through-slot (x[0.04,76.16]mm,
    y[5.04,8.93]mm) erases the mid-strokes of all six letters; an exhaustive
    rigid-shift search found NO position that clears the slot without landing
    inside 'Terrible ...' or off the part, and Gemini redraw passes could not
    fit readable lettering in the ~3.5mm strip above the slot. Removing the
    lead-in (title reads 'Terrible Writers & Artists of All Ages') is the
    only deterministic clean option.

    Glyph selection is geometric, in final placement coordinates (stable:
    the fit is deterministic): letters live inside x<640, y<170px (measured
    block bbox (113,0)-(607,139)). Five letters are isolated components; the
    leading 'F' is pixel-merged with the portrait frame's squiggle, so that
    component is split by marker watershed (erode to seeds, classify seeds
    by region, assign every pixel to its nearest seed's class) -- method
    validated by eye in scratch/title-shift/watershed_split_check.png."""
    from scipy import ndimage

    RECT_X1, RECT_Y1 = 640, 170          # glyph search region (px)
    GLYPH_X0 = 100                       # letters start at x=113; frame parts hug x=0
    F_X0, F_X1, F_Y1 = 80, 260, 150      # leading-F seed region (px)

    ink = (final_bit == 0).astype(np.uint8)
    n, labels, stats, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
    erase = np.zeros_like(ink, dtype=bool)
    n_whole = 0
    for i in range(1, n):
        x, y, wc, hc, area = stats[i]
        comp = labels == i
        inside = comp[:RECT_Y1, :RECT_X1].sum()
        if inside == 0:
            continue
        frac = inside / area
        if frac >= 0.99 and x >= GLYPH_X0:
            # an isolated letter (u/n/F/o/r); frame fragments (which also sit
            # fully inside the region) all start at x=0 and are excluded
            erase |= comp
            n_whole += 1
        elif 0.3 <= frac < 0.99 and (x + wc) > GLYPH_X0:
            # the F+frame merged component: watershed split
            eroded = cv2.erode(comp.astype(np.uint8) * 255,
                               np.ones((3, 3), np.uint8), iterations=3)
            n2, labels2, stats2, _ = cv2.connectedComponentsWithStats(eroded, connectivity=8)
            seed_img = np.zeros_like(labels2, dtype=np.int32)
            f_seeds = 0
            for j in range(1, n2):
                sx, sy, sw, sh, sarea = stats2[j]
                if sarea < 20:
                    continue
                if F_X0 < sx and (sx + sw) < F_X1 and sy < F_Y1:
                    seed_img[labels2 == j] = 1
                    f_seeds += 1
                else:
                    seed_img[labels2 == j] = 2
            if f_seeds == 0:
                continue  # merged comp has no F seed -- not the F+frame comp
            _, (iy, ix) = ndimage.distance_transform_edt(seed_img == 0,
                                                         return_indices=True)
            nearest = seed_img[iy, ix]
            erase |= comp & (nearest == 1)

    removed_px = int(erase.sum())
    # Loud guard: the measured block is 32,052 ink px. If a future re-fit
    # moves the title, fail here instead of silently erasing the wrong art.
    assert n_whole == 5, f"expected 5 isolated glyphs in the Fun-For region, got {n_whole}"
    assert 25000 <= removed_px <= 40000, \
        f"Fun-For erase removed {removed_px}px, outside the sanity window"
    variant = final_bit.copy()
    variant[erase] = 255
    return variant, removed_px


def process_right_wall():
    gray, path = load_gray("IMG_4230_ai_vH2.png")
    h, w = gray.shape
    bit0 = threshold_bit(gray, 128)

    # SPECS known cosmetic debt: "faint stray marks at top/bottom edges —
    # erase". Checked: no nonwhite pixels within 60px of top/bottom edge in
    # this (already whitened) final/ source; a connected-component scan of
    # the top/bottom 400px bands found only legitimate content (title
    # lettering, postage-stamp icon). Debt appears already resolved by the
    # earlier deterministic white-point pass. Defensive measure applied
    # anyway: clear a thin (12px) pure band at the very top/bottom edge and
    # run the standard small-speckle filter, in case anything reappears
    # after resampling.
    edge_band = 12
    bit0[:edge_band, :] = 255
    bit0[-edge_band:, :] = 255
    bit, removed = remove_speckle(bit0, min_area=4)

    w_mm, h_mm, tw, th = FACE_TARGETS["right_wall"]
    box = robust_content_bbox(bit, min_ink=3)
    final, info = cover_fit(bit, box, tw, th)

    out_path = os.path.join(OUT, "right_wall.png")
    save_bit_png(final, out_path)
    pos, neg = feature_audit(final)

    # VARIANT NOFUNFOR -- see _erase_funfor docstring (Ben feedback #4)
    variant, removed_px = _erase_funfor(final)
    save_bit_png(variant, os.path.join(OUT, "right_wall_VARIANT_NOFUNFOR.png"))
    pos_v, neg_v = feature_audit(variant)
    variant_step = (
        "VARIANT NOFUNFOR (Ben's 2026-07-11 feedback #4, decision pending): "
        "the lid through-slot (76.2x4mm, y 5.04-8.93mm below the top edge, "
        "front half) erases the mid-strokes of all six 'Fun For' lead-in "
        "letters. MEASURED conclusion (scratch/title-shift/): no rigid shift "
        "of the block clears the slot without colliding with 'Terrible', "
        "the framed portrait, or the part edge (best legal shift lands "
        "mid-sentence at dx=+132mm); the strip above the slot is only "
        "~3.5mm -- unreadably small -- and 4 Gemini redraw passes all "
        "failed placement. This variant instead ERASES the six glyphs "
        f"surgically ({removed_px}px removed; 5 isolated components + the "
        "leading F split from the portrait-frame squiggle by marker "
        "watershed), leaving all other approved art bit-identical. Title "
        "reads 'Terrible Writers & Artists of All Ages'; the slot cuts "
        "through blank wood. Ben picks: accept the cut (canonical) vs drop "
        "the lead-in (this variant)."
    )

    log("right_wall", source="IMG_4230_ai_vH2.png", source_px=f"{w}x{h}",
        steps=[
            "JUDGMENT CALL: SPECS flags 'faint stray marks at top/bottom "
            "edges' as a known cosmetic debt to erase. Verified directly: "
            "no nonwhite pixels within 60px of top or bottom edge, and a "
            "connected-component scan of the top/bottom 400px bands found "
            "only real content (title lettering + stamp icon), not stray "
            "marks -> debt already resolved upstream (whitening pass). "
            f"Cleared a defensive {edge_band}px pure-white edge band anyway "
            "(this defensive edge-clear stays in rev 3, per BRIEF).",
            "global threshold @128 (0=ink)",
            f"speckle cleanup: dropped {removed} components <4px^2",
        ] + _cover_fit_steps(box, info, tw, th) + [variant_step],
        final_px=f"{tw}x{th}", canvas_mm=f"{w_mm}x{h_mm}",
        feature_pos_mm=pos, feature_neg_mm=neg)

    log("right_wall_VARIANT_NOFUNFOR", source="IMG_4230_ai_vH2.png",
        source_px=f"{w}x{h}",
        steps=["identical to right_wall.png (same threshold/bbox/cover-fit) "
               "except the final glyph erase:", variant_step],
        final_px=f"{tw}x{th}", canvas_mm=f"{w_mm}x{h_mm}",
        feature_pos_mm=pos_v, feature_neg_mm=neg_v)


def process_faceplate(name, src_name):
    """Ben's DECISION 2026-07-11 (supersedes the rev-3 balanced-fit): the
    faceplates are labels, not scenes -- do NOT full-bleed them. The whole
    word goes BELOW the grip slot, small enough to fit entirely in the clear
    band, centered. Slot geometry (from config/DESIGN): 30x15mm, horizontally
    centered, slot TOP 8mm below the part top edge -> slot bottom sits 23mm
    from the top of the 53.5mm face. The word band is bounded by: slot bottom
    + 2mm clearance (top), 4mm off the bottom edge (finger-jointed -- SPECS
    safe-margin rule; Ben also flagged rev 3 running too close to the bottom
    teeth), 2mm side margins. Contain-fit (zero crop) into that band."""
    gray, path = load_gray(src_name)
    h, w = gray.shape
    w_mm, h_mm, tw, th = FACE_TARGETS[name]

    bit = threshold_bit(gray, 128)
    bit, removed = remove_speckle(bit, min_area=4)

    box = robust_content_bbox(bit, min_ink=3)

    SLOT_BOTTOM_MM = 8.0 + 15.0     # slot top offset + slot height
    CLEAR_BELOW_SLOT_MM = 2.0
    BOTTOM_MARGIN_MM = 4.0          # finger-jointed bottom edge (SPECS >=4mm)
    SIDE_MARGIN_MM = 2.0
    band_top_px = int(round(mm_to_px(SLOT_BOTTOM_MM + CLEAR_BELOW_SLOT_MM)))
    band_bot_px = th - int(round(mm_to_px(BOTTOM_MARGIN_MM)))
    band_h_px = band_bot_px - band_top_px
    band_w_px = tw - 2 * int(round(mm_to_px(SIDE_MARGIN_MM)))

    top_, bottom_, left_, right_ = box
    content = bit[top_:bottom_ + 1, left_:right_ + 1]
    ch, cw = content.shape
    s = min(band_w_px / cw, band_h_px / ch)  # contain fit: no crop, ever
    scaled_w = max(1, int(round(cw * s)))
    scaled_h = max(1, int(round(ch * s)))
    if s >= 1.0:
        scaled = cv2.resize(content, (scaled_w, scaled_h), interpolation=cv2.INTER_NEAREST)
        scaled = np.where(scaled < 127, 0, 255).astype(np.uint8)
    else:
        scaled = resize_area_rethreshold(content, scaled_w, scaled_h)

    final = np.full((th, tw), 255, dtype=np.uint8)
    x0 = (tw - scaled_w) // 2
    y0 = band_top_px + (band_h_px - scaled_h) // 2
    final[y0:y0 + scaled_h, x0:x0 + scaled_w] = scaled

    out_path = os.path.join(OUT, f"{name}.png")
    save_bit_png(final, out_path)
    pos, neg = feature_audit(final)

    steps = [
        "global threshold @128 (0=ink)",
        f"speckle cleanup: dropped {removed} components <4px^2",
        f"ROBUST content bbox (rows/cols with >=3 ink px): rows "
        f"{box[0]}-{box[1]}, cols {box[2]}-{box[3]} -> {cw}x{ch}px content "
        f"({cw/ch:.3f}:1 vs panel {tw/th:.3f}:1)",
        "BELOW-SLOT LABEL PLACEMENT (Ben's decision 2026-07-11, supersedes "
        "rev-3 balanced fit -- faceplates are labels, not scenes; no bleed): "
        f"grip slot is 30x15mm, slot top 8mm below the part top edge -> slot "
        f"bottom at {SLOT_BOTTOM_MM:.0f}mm from top. Word band = rows "
        f"{band_top_px}-{band_bot_px}px ({(SLOT_BOTTOM_MM + CLEAR_BELOW_SLOT_MM):.0f}"
        f"-{h_mm - BOTTOM_MARGIN_MM:.1f}mm from top: {CLEAR_BELOW_SLOT_MM:.0f}mm "
        f"clearance under the slot, {BOTTOM_MARGIN_MM:.0f}mm off the finger-"
        f"jointed bottom edge), {SIDE_MARGIN_MM:.0f}mm side margins. "
        f"CONTAIN-fit (zero crop) scale={s:.4f} -> word {scaled_w}x{scaled_h}px "
        f"({scaled_w / PX_PER_MM:.1f}x{scaled_h / PX_PER_MM:.1f}mm), centered "
        f"horizontally (x0={x0}px) and vertically within the band (y0={y0}px). "
        "The word no longer touches any edge and the slot no longer cuts "
        "through any glyph.",
    ]
    log(name, source=src_name, source_px=f"{w}x{h}", steps=steps,
        final_px=f"{tw}x{th}", canvas_mm=f"{w_mm}x{h_mm}",
        feature_pos_mm=pos, feature_neg_mm=neg)


def process_drawer_side(name, src_name, order_note, bias_v=None):
    """Rev-3: universal robust-bbox + COVER-fit (replaces rev-2's
    fit-to-height + pad-to-ratio, which left ~10-16mm of white padding on
    the panel's short ends -- exactly the "white space on the sides" defect
    Ben flagged). bias_v lets drawer sides with an empty-sky top trim there
    first instead of splitting the (now small) height overflow evenly."""
    gray, path = load_gray(src_name)
    h, w = gray.shape
    w_mm, h_mm, tw, th = FACE_TARGETS[name]

    bit = threshold_bit(gray, 128)
    bit, removed = remove_speckle(bit, min_area=4)

    box = robust_content_bbox(bit, min_ink=3)
    final, info = cover_fit(bit, box, tw, th, bias_v=bias_v)

    out_path = os.path.join(OUT, f"{name}.png")
    save_bit_png(final, out_path)
    pos, neg = feature_audit(final)

    top, bottom, left, right = box
    cw, ch = info["content_wh"]
    log(name, source=src_name, source_px=f"{w}x{h}",
        steps=[
            order_note,
            "global threshold @128 (0=ink)",
            f"speckle cleanup: dropped {removed} components <4px^2",
        ] + _cover_fit_steps(box, info, tw, th) + [
            f"content aspect {cw/ch:.3f}:1 vs panel {tw/th:.3f}:1 -- "
            + (f"bias_v={bias_v}: all vertical overflow trimmed from the "
               f"{'bottom' if bias_v=='top' else 'top'} (sky/empty background "
               "preferred over feet/ground per BRIEF)" if bias_v
               else "overflow small enough (or content dense enough top-to-"
               "bottom, e.g. 4237's real bordered frame) to center-crop"),
        ],
        final_px=f"{tw}x{th}", canvas_mm=f"{w_mm}x{h_mm}",
        feature_pos_mm=pos, feature_neg_mm=neg)


# ------------------------------------------------------ IMG_4231 (lid+top) --

def measure_left_edge_shear(gray):
    """Robust measurement of the left-edge tilt (a clean hard boundary line,
    verified visually distinct from the organic art content): linear
    regression of (row -> first non-white column) over the middle 50% of
    rows, with iterative sigma-clipping. Returns slope m (dcol/drow)."""
    h, w = gray.shape
    mask = gray < 245
    rows = np.arange(int(h * 0.25), int(h * 0.75), 2)
    pts = []
    for y in rows:
        cols = np.where(mask[y, :1600])[0]
        if len(cols):
            pts.append((y, cols[0]))
    pts = np.array(pts, dtype=float)
    cur = pts.copy()
    m, b = 0.0, 0.0
    for _ in range(8):
        A = np.vstack([cur[:, 0], np.ones(len(cur))]).T
        m, b = np.linalg.lstsq(A, cur[:, 1], rcond=None)[0]
        resid = cur[:, 1] - (m * cur[:, 0] + b)
        sd = resid.std()
        keep = np.abs(resid) < 2.5 * sd
        if keep.sum() == len(cur) or sd < 0.5:
            cur = cur[keep]
            break
        cur = cur[keep]
    resid_final = cur[:, 1] - (m * cur[:, 0] + b)
    return m, b, resid_final.std(), len(cur), len(pts)


def _finish_lid_panel(field_bit, variant_label, split_x_px):
    """Shared A/B-variant finish: split a (field_h_px x field_w_px) windowed
    field into lid (front split_x_px cols) + panel (remaining cols), clean
    speckle, orient each into its own FACE_TARGETS convention, save.
    variant_label=None -> canonical files (sliding_lid.png/top_panel.png);
    variant_label="B" -> sliding_lid_VARIANT_B.png/top_panel_VARIANT_B.png.
    Returns a dict with every number PLACEMENTS.md needs."""
    lid_bit = field_bit[:, :split_x_px]      # portrait: width(tall) x depth(narrow)
    panel_bit = field_bit[:, split_x_px:]    # landscape, matches panel convention

    lid_bit, removed_lid = remove_speckle(lid_bit, min_area=4)
    panel_bit, removed_panel = remove_speckle(panel_bit, min_area=4)

    # --- top panel: same orientation as the field, already at target px ---
    w_mm_p, h_mm_p, tw_p, th_p = FACE_TARGETS["top_panel"]
    assert panel_bit.shape == (th_p, tw_p), f"panel px {panel_bit.shape} != target {(th_p, tw_p)}"
    suffix = "" if variant_label is None else f"_VARIANT_{variant_label}"
    panel_name = f"top_panel{suffix}"
    save_bit_png(panel_bit, os.path.join(OUT, f"{panel_name}.png"))
    pos_p, neg_p = feature_audit(panel_bit)

    # --- sliding lid: field's convention is depth-horizontal/width-vertical;
    # the lid's OWN output convention (163.6mm-wide x 79mm-deep, W>H
    # landscape) is width-horizontal/depth-vertical -- the opposite axis
    # order. Per BRIEF: rotate "into the lid's own output convention as rev
    # 2 did" -- reuse rev 2's np.rot90(k=-1) (a true 90-degree rotation, not
    # a mirror), unchanged, putting the lid's leading/grip edge (depth=0,
    # the field's FRONT column -- now the snake-head end) at the TOP row of
    # the output. Still not independently verifiable against the physical
    # box from here -- flagged for Ben at the placement-proof gate.
    lid_rot = np.ascontiguousarray(np.rot90(lid_bit, k=-1))

    w_mm_l, h_mm_l, tw_l, th_l = FACE_TARGETS["sliding_lid"]
    depth_px_native, width_px_native = lid_rot.shape
    scale = th_l / depth_px_native
    strip_w = int(round(width_px_native * scale))
    strip_resized = resize_area_rethreshold(lid_rot, strip_w, th_l)

    canvas = np.full((th_l, tw_l), 255, dtype=np.uint8)
    pad_left = max(0, (tw_l - strip_w) // 2)
    if strip_w > tw_l:
        off = (strip_w - tw_l) // 2
        strip_resized = strip_resized[:, off:off + tw_l]
        pad_left = 0
        strip_w = tw_l
    canvas[:, pad_left:pad_left + strip_w] = strip_resized
    canvas = np.where(canvas < 127, 0, 255).astype(np.uint8)
    lid_name = f"sliding_lid{suffix}"
    save_bit_png(canvas, os.path.join(OUT, f"{lid_name}.png"))
    pos_l, neg_l = feature_audit(canvas)

    return dict(
        removed_lid=removed_lid, removed_panel=removed_panel,
        panel_name=panel_name, lid_name=lid_name,
        pos_p=pos_p, neg_p=neg_p, pos_l=pos_l, neg_l=neg_l,
        pad_left_px=pad_left, pad_left_mm=pad_left / PX_PER_MM,
        pad_right_mm=(tw_l - strip_w - pad_left) / PX_PER_MM,
        strip_w=strip_w, tw_l=tw_l, th_l=th_l, tw_p=tw_p, th_p=th_p,
        w_mm_p=w_mm_p, h_mm_p=h_mm_p, w_mm_l=w_mm_l, h_mm_l=h_mm_l,
        lid_bit_shape=lid_bit.shape,
    )


def process_4231():
    gray, path = load_gray("IMG_4231_ai_vT1_master.png")
    h, w = gray.shape

    # === step 1: deshear -- UNCHANGED from rev 2 ===
    m, b, resid_sd, n_kept, n_total = measure_left_edge_shear(gray)
    assert resid_sd < 5.0, f"4231 left-edge fit not clean (resid_sd={resid_sd}); manual review needed"
    angle_deg = np.degrees(np.arctan(m))

    # Left edge tilts (clean, resid_sd ~1.7px) but top/bottom edges are
    # independently confirmed FLAT (measured near-constant row 643 / 2429
    # across most of the width) -> this is a horizontal SHEAR artifact
    # (photo-inherited, baked in by the padded-canvas compositing step),
    # not a whole-canvas rotation. A rotation would incorrectly tilt the
    # already-level top/bottom edges; a shear isolates the correction to
    # columns only and leaves horizontal lines horizontal (verified
    # visually: after the shear below, both the left edge AND the top/
    # bottom edges read level).
    k = -m  # shear coefficient that nulls the measured slope
    y_ref = h / 2.0
    M = np.array([[1, k, -k * y_ref], [0, 1, 0]], dtype=np.float64)
    sheared = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderValue=255)

    # Re-measure top/bottom edge levelness on the sheared image (flat
    # region, x 20%-70% of width, away from the mosaic panel's own jagged
    # organic edge on the right which is real art, not a field boundary).
    mask_s = sheared < 245
    x0, x1 = int(w * 0.2), int(w * 0.7)
    top_rows = [np.where(mask_s[:, x])[0][0] for x in range(x0, x1, 50) if mask_s[:, x].any()]
    bot_rows = [np.where(mask_s[:, x])[0][-1] for x in range(x0, x1, 50) if mask_s[:, x].any()]
    top_row = int(np.median(top_rows))
    bot_row = int(np.median(bot_rows))

    # === step 2: ROBUST content bbox on the desheared band (rev-3
    # universal rule -- rows/cols need >=3 ink px to count, so a single
    # stray mark can't fake the bbox out to the canvas edge) ===
    bit_full = threshold_bit(sheared, 128)
    cy0, cy1, cx0, cx1 = robust_content_bbox(bit_full, min_ink=3)
    content0 = bit_full[cy0:cy1 + 1, cx0:cx1 + 1]
    c0_h, c0_w = content0.shape
    content_ratio0 = c0_w / c0_h

    # === step 3: ROTATE 180 degrees (np.rot90 k=2 -- a true rotation,
    # preserves handedness, NOT a mirror) so the mosaic snake HEAD end
    # (measured at the RIGHT of the desheared band; cat+floral border at
    # the LEFT) becomes the FRONT. Ben, rev-3 brief: "if we're going to
    # have part that's on the [sliding piece], I'd rather have it be the
    # snake part than the cat part." ===
    content = np.ascontiguousarray(np.rot90(content0, k=2))

    # === step 4: scale content HEIGHT to FIELD_H_MM exactly -- full bleed,
    # top AND bottom edges inked (Ben: "the full sides of the top
    # illustration should touch the top edges"). Width follows the same
    # uniform scale (aspect preserved), landing far past the 301.25mm
    # field -- that's expected, step 5 windows it down. ===
    FIELD_W_MM, FIELD_H_MM, SPLIT_MM = 301.25, 158.75, 79.0
    field_h_px = int(mm_to_px(FIELD_H_MM))                          # 1875 = 158.75mm
    split_x_px = int(mm_to_px(SPLIT_MM))                            # 933  = 79.0mm
    rear_px = int(mm_to_px(FIELD_W_MM - SPLIT_MM))                  # 2625 = 222.25mm
    field_w_px = split_x_px + rear_px                               # 3558 = 301.25mm

    scale4 = field_h_px / content.shape[0]
    total_w_px = int(round(content.shape[1] * scale4))
    if scale4 >= 1.0:
        scaled = cv2.resize(content, (total_w_px, field_h_px), interpolation=cv2.INTER_NEAREST)
        scaled = np.where(scaled < 127, 0, 255).astype(np.uint8)
    else:
        scaled = resize_area_rethreshold(content, total_w_px, field_h_px)
    total_len_mm = total_w_px / PX_PER_MM

    # === step 5: window anchored at the front (head) end, with the
    # smallest forward overshoot in [0,8]mm such that the column landing on
    # the lid's front edge has no contiguous white run over 20% of the
    # 158.75mm field height (i.e. ink genuinely reaches the front edge). ===
    def max_white_run_px(col):
        isw = (col == 255).astype(np.uint8)
        d = np.diff(np.concatenate(([0], isw, [0])))
        starts = np.where(d == 1)[0]
        ends = np.where(d == -1)[0]
        return int((ends - starts).max()) if len(starts) else 0

    RUN_LIMIT_PX = 0.20 * field_h_px  # 31.75mm
    max_overshoot_px = min(int(mm_to_px(8.0)), total_w_px - field_w_px)
    runs_by_px = [max_white_run_px(scaled[:, c]) for c in range(0, max_overshoot_px + 1)]
    met = [c for c, r in enumerate(runs_by_px) if r <= RUN_LIMIT_PX]
    criterion_met = bool(met)
    overshoot_px = met[0] if criterion_met else int(np.argmin(runs_by_px))
    overshoot_mm = overshoot_px / PX_PER_MM
    residual_run_mm = runs_by_px[overshoot_px] / PX_PER_MM

    true_cross_mm = None
    if not criterion_met:
        for c in range(0, total_w_px - field_w_px + 1):
            if max_white_run_px(scaled[:, c]) <= RUN_LIMIT_PX:
                true_cross_mm = c / PX_PER_MM
                break

    window_start_px = overshoot_px
    window_end_px = window_start_px + field_w_px
    field_bit_A = scaled[:, window_start_px:window_end_px]
    rear_trimmed_A_mm = (total_w_px - window_end_px) / PX_PER_MM

    # === step 8: VARIANT B -- CENTERED 301.25mm window, for comparison ===
    window_start_B_px = (total_w_px - field_w_px) // 2
    field_bit_B = scaled[:, window_start_B_px:window_start_B_px + field_w_px]
    front_trimmed_B_mm = window_start_B_px / PX_PER_MM
    rear_trimmed_B_mm = (total_w_px - (window_start_B_px + field_w_px)) / PX_PER_MM

    # === step 8b: VARIANT C (Ben 2026-07-11) -- CAT-END-ANCHORED window:
    # keep the FULL cat + floral border (the rear end of the rotated strip)
    # and trim the snake-head end instead -- the exact opposite anchoring
    # from canonical A. The art stays in the same rot180 orientation (snake
    # toward the front, per Ben: sliding part shows snake, not cat), so the
    # sliding lid receives the window's front 79mm = the snake's mid-body
    # scale region (the head is what gets trimmed). Same full-bleed
    # white-run rule as A's front anchor, applied at the REAR edge: smallest
    # rear overshoot in [0,8]mm whose edge column has no contiguous white
    # run over 20% of field height. ===
    runs_rear = [max_white_run_px(scaled[:, total_w_px - 1 - c])
                 for c in range(0, max_overshoot_px + 1)]
    met_rear = [c for c, r in enumerate(runs_rear) if r <= RUN_LIMIT_PX]
    rear_criterion_met_C = bool(met_rear)
    rear_overshoot_C_px = met_rear[0] if rear_criterion_met_C else int(np.argmin(runs_rear))
    rear_overshoot_C_mm = rear_overshoot_C_px / PX_PER_MM
    residual_run_C_mm = runs_rear[rear_overshoot_C_px] / PX_PER_MM
    window_end_C_px = total_w_px - rear_overshoot_C_px
    window_start_C_px = window_end_C_px - field_w_px
    field_bit_C = scaled[:, window_start_C_px:window_end_C_px]
    front_trimmed_C_mm = window_start_C_px / PX_PER_MM

    # === steps 6/7: split at 79mm + orient into lid/panel conventions ===
    res_A = _finish_lid_panel(field_bit_A, None, split_x_px)
    res_B = _finish_lid_panel(field_bit_B, "B", split_x_px)
    res_C = _finish_lid_panel(field_bit_C, "C", split_x_px)

    # === step 9: locate the real grip slot inside the head art (no
    # reserved capsule in this placement -- Ben has accepted cuts through
    # the art). Slot: 30(depth) x 10(width)mm, depth 10-40mm from lid
    # front, width-centered at 79.375mm of the 158.75mm art strip. In the
    # rot90(k=-1) lid convention, row 0 = depth 0 = front, so the slot
    # lands at rows [10mm,40mm] of the 79mm-deep output, centered
    # width-wise (columns ~74.4-84.4mm of the 158.75mm art strip, i.e.
    # ~76.8-86.8mm of the padded 163.6mm canvas). ===
    SLOT_DEPTH0_MM, SLOT_DEPTH1_MM = 10.0, 40.0
    SLOT_WIDTH_CENTER_MM, SLOT_WIDTH_MM = 79.375, 10.0

    shared_deskew_step = (
        f"MEASURED DESKEW (unchanged from rev 2): left-edge boundary (a clean "
        f"hard line, resid_sd={resid_sd:.2f}px over n={n_kept}/{n_total} "
        f"sampled rows) has slope dcol/drow={m:.5f} ({angle_deg:.2f} deg from "
        f"vertical). Top/bottom edges independently measured near-flat "
        f"(median rows {top_row} / {bot_row} over x 20%-70% of width) -> "
        "this is a horizontal SHEAR, not a rotation. Applied shear "
        f"x'=x+{k:.5f}*(y-{y_ref:.0f}), INTER_CUBIC, white fill. Verified "
        "visually post-shear: left edge vertical, top/bottom level."
    )
    content_step = (
        f"ROBUST content bbox on the desheared band: rows {cy0}-{cy1}, cols "
        f"{cx0}-{cx1} -> {c0_w}x{c0_h}px ({content_ratio0:.3f}:1, matches the "
        "~2.87:1 panorama band)."
    )
    rotate_step = (
        "ROTATED 180 degrees (np.rot90 k=2, a true rotation -- preserves "
        "handedness, does not mirror): the mosaic snake HEAD (measured at "
        "the content band's RIGHT edge pre-rotation) becomes the FRONT "
        "(left) end; the floral border + cat (LEFT edge pre-rotation) "
        "becomes the REAR (right) end. Per Ben: snake on the sliding lid, "
        "not the cat."
    )
    scale_step = (
        f"Scaled content HEIGHT to {field_h_px}px = {FIELD_H_MM}mm exactly "
        f"(full bleed, both long edges inked) -- uniform scale={scale4:.4f}, "
        f"width follows to {total_w_px}px = {total_len_mm:.2f}mm "
        f"(vs the {FIELD_W_MM}mm field -- {total_len_mm - FIELD_W_MM:.1f}mm "
        "of surplus length to window down)."
    )
    if criterion_met:
        overshoot_verdict = (
            f"Front-edge white-run search over [0,8]mm SATISFIED at "
            f"overshoot={overshoot_mm:.2f}mm (residual max white run "
            f"{residual_run_mm:.2f}mm, under the "
            f"{RUN_LIMIT_PX / PX_PER_MM:.2f}mm/20% limit)."
        )
    else:
        overshoot_verdict = (
            f"Front-edge white-run search over [0,8]mm did NOT find a "
            f"column meeting the <20%-of-height (<{RUN_LIMIT_PX / PX_PER_MM:.2f}mm) "
            f"criterion -- the head's drawn boundary is a much longer diagonal "
            "than an 8mm nudge can clear (the head is a rounded/tapered shape, "
            "not a hard vertical edge). Picked the BEST available point within "
            f"the mandated cap: overshoot={overshoot_mm:.2f}mm (max overshoot "
            f"allowed), residual max white run {residual_run_mm:.2f}mm "
            f"({100 * residual_run_mm / (field_h_px / PX_PER_MM):.0f}% of the "
            "158.75mm height -- i.e. roughly the bottom/most of that front "
            "column is still blank). FLAG FOR BEN: the true crossing point "
            f"(where a contiguous white run finally drops under 20%) is "
            f"~{true_cross_mm:.1f}mm of overshoot, well past the 8mm cap -- "
            "getting fully solid ink at the very front edge would cost "
            f"~{true_cross_mm - 8:.0f}mm more of the head's tip than budgeted. "
            "Shipping at the 8mm cap as instructed; revisit at the proof gate "
            "if a fully-inked front edge matters more than preserving the "
            "head's tip."
        )
    window_step = (
        f"WINDOW (canonical, head-anchored): [{window_start_px}px, "
        f"{window_end_px}px) = [{overshoot_mm:.2f}mm, "
        f"{overshoot_mm + FIELD_W_MM:.2f}mm) of the {total_len_mm:.2f}mm "
        f"scaled content. {overshoot_verdict} REAR TRIM: "
        f"{rear_trimmed_A_mm:.2f}mm dropped off the tail end of the window "
        "-- VERIFIED BY EYE (top_panel.png's trailing edge): the scale "
        "pattern and the full coiled tail curl both fall inside the kept "
        "window, and the floral/vine wallpaper background just barely "
        "starts to reappear right at the panel's trailing edge (a few "
        "flowers/leaves), but the CAT FIGURE ITSELF (body, face, hose, "
        "leash) is entirely outside the window -- none of it survives in "
        "either the lid or the top panel. See lid_top_panel_seam.png / the "
        "top_panel.png proof for the exact cut line."
    )
    split_step = (
        f"Split at {SPLIT_MM}mm from front: split_x={split_x_px}px of the "
        f"{field_w_px}px ({FIELD_W_MM}mm) window (no further resize -- both "
        "halves already land on their exact target px)."
    )
    speckle_step_A = (
        "global threshold @128 (0=ink) applied before compositing; speckle "
        f"cleanup: lid dropped {res_A['removed_lid']}, panel dropped "
        f"{res_A['removed_panel']} components <4px^2"
    )
    speckle_step_B = (
        "global threshold @128 (0=ink) applied before compositing; speckle "
        f"cleanup: lid dropped {res_B['removed_lid']}, panel dropped "
        f"{res_B['removed_panel']} components <4px^2"
    )
    speckle_step_C = (
        "global threshold @128 (0=ink) applied before compositing; speckle "
        f"cleanup: lid dropped {res_C['removed_lid']}, panel dropped "
        f"{res_C['removed_panel']} components <4px^2"
    )
    if rear_criterion_met_C:
        rear_verdict_C = (
            f"Rear-edge white-run search over [0,8]mm SATISFIED at rear "
            f"overshoot={rear_overshoot_C_mm:.2f}mm (residual max white run "
            f"{residual_run_C_mm:.2f}mm, under the "
            f"{RUN_LIMIT_PX / PX_PER_MM:.2f}mm/20% limit)."
        )
    else:
        rear_verdict_C = (
            f"Rear-edge white-run search over [0,8]mm did NOT meet the "
            f"<{RUN_LIMIT_PX / PX_PER_MM:.2f}mm criterion; picked the best "
            f"available point: rear overshoot={rear_overshoot_C_mm:.2f}mm, "
            f"residual max white run {residual_run_C_mm:.2f}mm. FLAG for the "
            "proof gate."
        )
    variant_c_step = (
        f"VARIANT C (Ben 2026-07-11, CAT-END-ANCHORED window): "
        f"[{window_start_C_px}px, {window_end_C_px}px) = "
        f"[{front_trimmed_C_mm:.2f}mm, {front_trimmed_C_mm + FIELD_W_MM:.2f}mm) "
        f"of the {total_len_mm:.2f}mm scaled content -- the exact opposite "
        f"anchoring from canonical A: the window is flush against the "
        f"floral/cat (rear) end, so the FULL cat figure (body, face, hose, "
        f"leash) plus the floral border survive on the top panel, and "
        f"{front_trimmed_C_mm:.1f}mm is trimmed off the snake-HEAD end "
        f"instead. {rear_verdict_C} The art keeps the same rot180 "
        "orientation as A (snake toward the front), so the sliding lid "
        "carries whatever the window's front 79mm holds (the region just "
        "past the trimmed head -- see the proof strip for exactly what "
        "survives and where the grip slot lands). "
        "Saved as sliding_lid_VARIANT_C.png / top_panel_VARIANT_C.png; "
        "proof strip lid_top_panel_seam_VARIANT_C.png. Ben picks A (head "
        "on lid, cat lost) vs C (full cat at the panel rear, head lost) at "
        "the proof gate."
    )
    variant_b_step = (
        f"VARIANT B (comparison, CENTERED window): [{window_start_B_px}px, "
        f"{window_start_B_px + field_w_px}px) = [{front_trimmed_B_mm:.2f}mm, "
        f"{front_trimmed_B_mm + FIELD_W_MM:.2f}mm) of the same "
        f"{total_len_mm:.2f}mm scaled content -- trims {front_trimmed_B_mm:.2f}mm "
        "off the head end (into the head's own body/neck area, past its "
        f"pointed tip) AND {rear_trimmed_B_mm:.2f}mm off the tail end "
        "(floral border + cat, same region variant A trims, just less of "
        "it). Saved as sliding_lid_VARIANT_B.png / top_panel_VARIANT_B.png "
        "for a trim-judgment comparison at the proof gate; NOT used by "
        "art_proofs.py's main per-part renders (canonical A only) -- see "
        "scratch/art-proofs/lid_top_panel_seam_VARIANT_B.png."
    )
    lid_pad_step = (
        f"lid: rotated the front {SPLIT_MM}mm slice with np.rot90(k=-1) (rev "
        "2's rotation, reused per BRIEF -- direction still not independently "
        "verifiable against the physical box from here; flag for Ben at the "
        f"proof gate), scaled to depth={res_A['th_l']}px exactly (79mm, no "
        f"slack), width came out {res_A['strip_w']}px; centered on a white "
        f"{res_A['tw_l']}x{res_A['th_l']} canvas (163.6mm lid blank vs "
        f"158.75mm art field): pad {res_A['pad_left_px']}px/"
        f"{res_A['pad_left_mm']:.2f}mm left, "
        f"{res_A['tw_l'] - res_A['strip_w'] - res_A['pad_left_px']}px/"
        f"{res_A['pad_right_mm']:.2f}mm right. This pad is BLANK BY DESIGN, "
        "not a processing defect -- both edges ride hidden inside the "
        "wall slots once assembled, so they will never read as visible "
        "white space on the finished box."
    )
    grip_slot_step = (
        f"GRIP SLOT LOCATION (no reserved capsule in this placement -- Ben "
        "has accepted the slot cutting into drawn art): the real slot is "
        f"{SLOT_WIDTH_MM:.0f}x30mm, depth {SLOT_DEPTH0_MM:.0f}-"
        f"{SLOT_DEPTH1_MM:.0f}mm from the lid front edge (rows "
        f"{int(mm_to_px(SLOT_DEPTH0_MM))}-{int(mm_to_px(SLOT_DEPTH1_MM))}px "
        f"of the {res_A['th_l']}px-deep lid), width-centered at "
        f"{SLOT_WIDTH_CENTER_MM}mm of the 158.75mm art strip (columns "
        f"~{int(mm_to_px(SLOT_WIDTH_CENTER_MM - SLOT_WIDTH_MM / 2)) + res_A['pad_left_px']}-"
        f"{int(mm_to_px(SLOT_WIDTH_CENTER_MM + SLOT_WIDTH_MM / 2)) + res_A['pad_left_px']}px "
        f"of the padded {res_A['tw_l']}px canvas). This falls in the FRONT "
        "third of the snake-head mosaic -- directly through the head's jaw/"
        "cheek scale-mosaic linework (see sliding_lid.png; the slot does "
        "NOT land on either drawn eye, but does cross several mosaic-tile "
        "boundary lines and hatching). Ben: 'eat the cost of those holes' -- "
        "no further mitigation applied."
    )

    log("top_panel", source="IMG_4231_ai_vT1_master.png", source_px=f"{w}x{h}",
        steps=[
            shared_deskew_step, content_step, rotate_step, scale_step,
            window_step, split_step, speckle_step_A,
            "top panel keeps the field's own orientation (matches target "
            "table convention 222.25mm-wide x 158.75mm-tall = depth-horizontal "
            "same as field): direct slice, already at target px, no rotation/"
            "padding needed.",
            variant_b_step, variant_c_step,
        ],
        final_px=f"{res_A['tw_p']}x{res_A['th_p']}",
        canvas_mm=f"{res_A['w_mm_p']}x{res_A['h_mm_p']}",
        feature_pos_mm=res_A["pos_p"], feature_neg_mm=res_A["neg_p"])

    log("sliding_lid", source="IMG_4231_ai_vT1_master.png", source_px=f"{w}x{h}",
        steps=[
            shared_deskew_step, content_step, rotate_step, scale_step,
            window_step, split_step, speckle_step_A, lid_pad_step,
            grip_slot_step, variant_b_step, variant_c_step,
        ],
        final_px=f"{res_A['tw_l']}x{res_A['th_l']}",
        canvas_mm=f"{res_A['w_mm_l']}x{res_A['h_mm_l']}",
        feature_pos_mm=res_A["pos_l"], feature_neg_mm=res_A["neg_l"])

    log("top_panel_VARIANT_B", source="IMG_4231_ai_vT1_master.png", source_px=f"{w}x{h}",
        steps=[shared_deskew_step, content_step, rotate_step, scale_step,
               variant_b_step, split_step, speckle_step_B,
               "same field orientation as the canonical top panel, no rotation."],
        final_px=f"{res_B['tw_p']}x{res_B['th_p']}",
        canvas_mm=f"{res_B['w_mm_p']}x{res_B['h_mm_p']}",
        feature_pos_mm=res_B["pos_p"], feature_neg_mm=res_B["neg_p"])

    log("sliding_lid_VARIANT_B", source="IMG_4231_ai_vT1_master.png", source_px=f"{w}x{h}",
        steps=[shared_deskew_step, content_step, rotate_step, scale_step,
               variant_b_step, split_step, speckle_step_B,
               "same rot90(k=-1) + pad-center treatment as the canonical lid "
               f"(pad {res_B['pad_left_mm']:.2f}mm left / "
               f"{res_B['pad_right_mm']:.2f}mm right, blank-by-design, hidden "
               "in the wall slots)."],
        final_px=f"{res_B['tw_l']}x{res_B['th_l']}",
        canvas_mm=f"{res_B['w_mm_l']}x{res_B['h_mm_l']}",
        feature_pos_mm=res_B["pos_l"], feature_neg_mm=res_B["neg_l"])

    log("top_panel_VARIANT_C", source="IMG_4231_ai_vT1_master.png", source_px=f"{w}x{h}",
        steps=[shared_deskew_step, content_step, rotate_step, scale_step,
               variant_c_step, split_step, speckle_step_C,
               "same field orientation as the canonical top panel, no rotation."],
        final_px=f"{res_C['tw_p']}x{res_C['th_p']}",
        canvas_mm=f"{res_C['w_mm_p']}x{res_C['h_mm_p']}",
        feature_pos_mm=res_C["pos_p"], feature_neg_mm=res_C["neg_p"])

    log("sliding_lid_VARIANT_C", source="IMG_4231_ai_vT1_master.png", source_px=f"{w}x{h}",
        steps=[shared_deskew_step, content_step, rotate_step, scale_step,
               variant_c_step, split_step, speckle_step_C,
               "same rot90(k=-1) + pad-center treatment as the canonical lid "
               f"(pad {res_C['pad_left_mm']:.2f}mm left / "
               f"{res_C['pad_right_mm']:.2f}mm right, blank-by-design, hidden "
               "in the wall slots)."],
        final_px=f"{res_C['tw_l']}x{res_C['th_l']}",
        canvas_mm=f"{res_C['w_mm_l']}x{res_C['h_mm_l']}",
        feature_pos_mm=res_C["pos_l"], feature_neg_mm=res_C["neg_l"])


# --------------------------------------------------------------- runner ----

def main():
    process_left_wall()
    process_right_wall()
    process_simple_wall("front_wall", "IMG_4229_ai_vH1.png", "front_wall", [
        "no border frame / no stray-mark debt on this source (checked)",
    ])
    process_4231()
    process_faceplate("faceplate_colors", "IMG_4236_ai_vH3.png")
    process_faceplate("faceplate_lines", "IMG_4238_ai_vH2.png")
    process_drawer_side("drawer_side_1", "IMG_4233_ai_vS_stitched.png",
                        "drawer_side_1 = IMG_4233 (turkeys/desert) per fixed source order 4233,4235,4237,4239; "
                        "dark diagonal streak (blood-drag joke) is intended art, kept as-is. "
                        "CONTENT-AWARE BIAS: top of frame is empty sky, bottom holds the turkeys' feet/tracks -- "
                        "bias_v='bottom' trims the (small, ~5.5mm) vertical overflow entirely off the sky.",
                        bias_v="bottom")
    process_drawer_side("drawer_side_2", "IMG_4235_ai_vS_stitched.png",
                        "drawer_side_2 = IMG_4235 (alligator/seagull) per fixed source order. "
                        "CONTENT-AWARE BIAS: top of frame is clouds/sun (empty sky), bottom holds the seagull "
                        "standing on sand -- bias_v='bottom' trims the (small, ~2.8mm) vertical overflow off the sky.",
                        bias_v="bottom")
    process_drawer_side("drawer_side_3", "IMG_4237_ai_vS_stitched.png",
                        "drawer_side_3 = IMG_4237 (gallery/audience) per fixed source order. "
                        "Frame-like dark band at top (giant kids peeking over gallery walls) is REAL ART, kept. "
                        "Content already runs nearly edge-to-edge top-to-bottom (starry night top, gallery floor "
                        "bottom, ratio 4.190:1 vs panel 4.221:1) -- overflow is tiny (0.36mm), centered.")
    process_drawer_side("drawer_side_4", "IMG_4239_ai_vS_stitched.png",
                        "drawer_side_4 = IMG_4239 (bookshelf/BLAH BLAH) per fixed source order. "
                        "Diagonal-hatch background pattern + book spine titles run to both the top and bottom of "
                        "the frame already (checked directly, no empty sky/ground band) -- centered crop is safe.")

    write_manifest()
    print(f"\nWrote {len(LOG)} parts to {OUT}/")


def write_manifest():
    lines = []
    lines.append("# art/engrave/PLACEMENTS.md")
    lines.append("")
    lines.append("Generated by `scripts/art_postprocess.py` (deterministic, re-runnable, no args). "
                 "Do not hand-edit -- re-run the script instead.")
    lines.append("")
    lines.append(f"300 DPI throughout ({PX_PER_MM:.4f} px/mm).")
    lines.append("")

    flag_rows = []

    for d in LOG:
        lines.append(f"## {d['part']}.png")
        lines.append("")
        lines.append(f"- **Source:** `{d['source']}` ({d['source_px']} px)")
        lines.append(f"- **Final size:** {d['final_px']} px  |  **Canvas:** {d['canvas_mm']} mm")
        lines.append("- **Processing:**")
        for s in d["steps"]:
            lines.append(f"  - {s}")
        pos = d["feature_pos_mm"]
        neg = d["feature_neg_mm"]
        pos_s = f"{pos:.3f} mm" if pos is not None else "n/a"
        neg_s = f"{neg:.3f} mm" if neg is not None else "n/a"
        flag = ""
        for label, val in (("stroke", pos), ("gap", neg)):
            if val is not None and val < 0.3:
                flag = " -- **FLAG: under 0.3mm (CO2 spot ~0.2mm; birch chars)**"
        lines.append(f"- **Feature-size audit:** thinnest positive stroke ~{pos_s}; "
                     f"thinnest negative gap ~{neg_s}.{flag}")
        if flag:
            flag_rows.append((d["part"], pos_s, neg_s))
        lines.append("")

    if flag_rows:
        lines.append("## Feature-size flags summary")
        lines.append("")
        for part, pos_s, neg_s in flag_rows:
            lines.append(f"- **{part}**: stroke {pos_s}, gap {neg_s} -- flagged, not auto-fixed.")
        lines.append("")

    with open(os.path.join(OUT, "PLACEMENTS.md"), "w") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
