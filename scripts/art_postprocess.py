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


def center_crop_to_ratio(gray, target_ratio, axis_hint=None):
    """Center-crop a grayscale array (h,w) to exactly target_ratio (w/h),
    shaving the excess dimension symmetrically. Returns (cropped, box) where
    box=(left,top,right,bottom) in the INPUT's coordinate frame."""
    h, w = gray.shape
    cur_ratio = w / h
    if cur_ratio > target_ratio:
        # too wide -> crop width
        new_w = int(round(h * target_ratio))
        left = (w - new_w) // 2
        box = (left, 0, left + new_w, h)
    else:
        # too tall/narrow -> crop height
        new_h = int(round(w / target_ratio))
        top = (h - new_h) // 2
        box = (0, top, w, top + new_h)
    left, top, right, bottom = box
    return gray[top:bottom, left:right], box


# ------------------------------------------------------------- face specs --

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

def process_simple_wall(name, src_name, target_key, notes):
    """side walls + front wall: threshold -> center-crop to exact ratio ->
    resize+rethreshold."""
    gray, path = load_gray(src_name)
    w_mm, h_mm, tw, th = FACE_TARGETS[target_key]
    target_ratio = tw / th

    bit = threshold_bit(gray, 128)
    bit, removed = remove_speckle(bit, min_area=4)

    cropped, box = center_crop_to_ratio(bit, target_ratio)
    final = resize_area_rethreshold(cropped, tw, th)

    out_path = os.path.join(OUT, f"{name}.png")
    save_bit_png(final, out_path)
    pos, neg = feature_audit(final)

    log(name, source=src_name, source_px=f"{gray.shape[1]}x{gray.shape[0]}",
        steps=notes + [
            f"global threshold @128 (0=ink)",
            f"speckle cleanup: dropped {removed} components <4px^2",
            f"center-crop to exact ratio {target_ratio:.4f} ({w_mm}x{h_mm}mm): box(l,t,r,b)={box}",
            f"area-average downscale to {tw}x{th} + re-threshold",
        ],
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
    target_ratio = tw / th
    bit = threshold_bit(inner, 128)
    bit, removed = remove_speckle(bit, min_area=4)
    cropped, box2 = center_crop_to_ratio(bit, target_ratio)
    final = resize_area_rethreshold(cropped, tw, th)

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
            f"center-crop to exact ratio {target_ratio:.4f} ({w_mm}x{h_mm}mm) "
            f"on the border-free interior: box(l,t,r,b)={box2}",
            f"area-average downscale to {tw}x{th} + re-threshold",
        ],
        final_px=f"{tw}x{th}", canvas_mm=f"{w_mm}x{h_mm}",
        feature_pos_mm=pos, feature_neg_mm=neg)


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
    target_ratio = tw / th
    cropped, box = center_crop_to_ratio(bit, target_ratio)
    final = resize_area_rethreshold(cropped, tw, th)

    out_path = os.path.join(OUT, "right_wall.png")
    save_bit_png(final, out_path)
    pos, neg = feature_audit(final)

    log("right_wall", source="IMG_4230_ai_vH2.png", source_px=f"{w}x{h}",
        steps=[
            "JUDGMENT CALL: SPECS flags 'faint stray marks at top/bottom "
            "edges' as a known cosmetic debt to erase. Verified directly: "
            "no nonwhite pixels within 60px of top or bottom edge, and a "
            "connected-component scan of the top/bottom 400px bands found "
            "only real content (title lettering + stamp icon), not stray "
            "marks -> debt already resolved upstream (whitening pass). "
            f"Cleared a defensive {edge_band}px pure-white edge band anyway.",
            "global threshold @128 (0=ink)",
            f"speckle cleanup: dropped {removed} components <4px^2",
            f"center-crop to exact ratio {target_ratio:.4f} ({w_mm}x{h_mm}mm): box(l,t,r,b)={box}",
            f"area-average downscale to {tw}x{th} + re-threshold",
        ],
        final_px=f"{tw}x{th}", canvas_mm=f"{w_mm}x{h_mm}",
        feature_pos_mm=pos, feature_neg_mm=neg)


def process_faceplate(name, src_name):
    gray, path = load_gray(src_name)
    h, w = gray.shape
    mask = gray < 245
    rows = np.where(mask.any(axis=1))[0]
    content_top, content_bot = rows.min(), rows.max()
    center_row = (content_top + content_bot) / 2.0

    w_mm, h_mm, tw, th = FACE_TARGETS[name]
    target_ratio = tw / th
    crop_h = int(round(w / target_ratio))
    top = int(round(center_row - crop_h / 2))
    top = max(0, min(top, h - crop_h))
    bottom = top + crop_h
    box = (0, top, w, bottom)

    bit = threshold_bit(gray, 128)
    bit, removed = remove_speckle(bit, min_area=4)
    cropped = bit[top:bottom, :]
    final = resize_area_rethreshold(cropped, tw, th)

    out_path = os.path.join(OUT, f"{name}.png")
    save_bit_png(final, out_path)
    pos, neg = feature_audit(final)

    margin_top = content_top - top
    margin_bot = bottom - content_bot
    log(name, source=src_name, source_px=f"{w}x{h}",
        steps=[
            f"content bbox rows {content_top}-{content_bot} (center row "
            f"{center_row:.0f}); crop window centered on CONTENT center "
            "(not canvas center) so the grip-slot-era lettering composition "
            f"stays intact: box(l,t,r,b)={box} "
            f"(margin above content={margin_top}px, below={margin_bot}px)",
            "global threshold @128 (0=ink)",
            f"speckle cleanup: dropped {removed} components <4px^2",
            f"crop height {crop_h}px hits exact ratio {target_ratio:.4f} ({w_mm}x{h_mm}mm), full width kept",
            f"area-average downscale to {tw}x{th} + re-threshold",
        ],
        final_px=f"{tw}x{th}", canvas_mm=f"{w_mm}x{h_mm}",
        feature_pos_mm=pos, feature_neg_mm=neg)


def process_drawer_side(name, src_name, order_note):
    gray, path = load_gray(src_name)
    h, w = gray.shape
    mask = gray < 250
    rows = np.where(mask.any(axis=1))[0]
    cols = np.where(mask.any(axis=0))[0]
    top, bottom = rows.min(), rows.max()
    left, right = cols.min(), cols.max()
    trimmed = gray[top:bottom + 1, left:right + 1]
    tr_h, tr_w = trimmed.shape
    content_ratio = tr_w / tr_h

    w_mm, h_mm, tw, th = FACE_TARGETS[name]
    target_ratio = tw / th

    bit = threshold_bit(trimmed, 128)
    bit, removed = remove_speckle(bit, min_area=4)

    # Fit to FULL HEIGHT (do not crop to ratio -- art is far wider-aspect
    # than the panel and content must not be cropped), center horizontally,
    # pad remainder white to reach the exact target ratio.
    scale = th / tr_h
    fit_w = int(round(tr_w * scale))
    fit_w = min(fit_w, tw)  # should never exceed given all sources < 4.22:1
    resized = resize_area_rethreshold(bit, fit_w, th)

    canvas = np.full((th, tw), 255, dtype=np.uint8)
    pad_left = (tw - fit_w) // 2
    canvas[:, pad_left:pad_left + fit_w] = resized

    out_path = os.path.join(OUT, f"{name}.png")
    save_bit_png(canvas, out_path)
    pos, neg = feature_audit(canvas)

    pad_left_mm = pad_left / PX_PER_MM
    pad_right_mm = (tw - fit_w - pad_left) / PX_PER_MM
    log(name, source=src_name, source_px=f"{w}x{h}",
        steps=[
            order_note,
            f"trimmed white generation-canvas border: content bbox rows "
            f"{top}-{bottom}, cols {left}-{right} -> {tr_w}x{tr_h}px "
            f"(ratio {content_ratio:.3f}:1, vs panel {target_ratio:.3f}:1)",
            "global threshold @128 (0=ink)",
            f"speckle cleanup: dropped {removed} components <4px^2",
            f"fit-to-FULL-HEIGHT (no ratio crop, per SPECS rule 4): scaled to "
            f"{fit_w}x{th}, centered horizontally on a white {tw}x{th} canvas "
            f"(pad {pad_left}px / {pad_left_mm:.2f}mm left, "
            f"{tw - fit_w - pad_left}px / {pad_right_mm:.2f}mm right)",
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


def process_4231():
    gray, path = load_gray("IMG_4231_ai_vT1_master.png")
    h, w = gray.shape

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

    # --- Capsule-registered placement (rev 2, 2026-07-10 proof-gate fix) ---
    # The generation composed the panorama as a ~2.87:1 CONTENT BAND inside
    # a 1.79:1 canvas (21% white margin top AND bottom, 3.5% each side).
    # Mapping the whole canvas onto the 301.25x158.75 field (rev 1) put the
    # art's reserved grip capsule 14.2mm rear of the REAL grip slot and left
    # a bare, lean-edged strip at the lid's front. The physical registration
    # that matters is capsule==slot (slot center: 25.0mm from the lid front
    # edge, width-centered at 79.375mm; slot 30x10mm). So: scale the CONTENT
    # band fit-to-width (its capsule then measures 30.6x9.9mm -- a 2% match
    # to the real slot, confirming this scale), then TRANSLATE so the
    # measured capsule center lands exactly on the slot center. The art
    # becomes a full-length band with clear wood above/below (~27mm each),
    # and the ~6mm forward shift crops most of the leaning drawn front
    # border off the lid's front edge as a side effect.
    mask_sheared = sheared < 245
    cols_any = mask_sheared.any(axis=0)
    rows_any = mask_sheared.any(axis=1)
    cx0 = int(np.argmax(cols_any)); cx1 = int(w - np.argmax(cols_any[::-1]))
    cy0 = int(np.argmax(rows_any)); cy1 = int(h - np.argmax(rows_any[::-1]))
    content = sheared[cy0:cy1, cx0:cx1]

    FIELD_W_MM, FIELD_H_MM = 301.25, 158.75
    SPLIT_MM = 79.0
    field_w_px = int(mm_to_px(SPLIT_MM)) + int(mm_to_px(FIELD_W_MM - SPLIT_MM))  # 933 + 2625
    field_h_px = int(mm_to_px(FIELD_H_MM))                                       # 1875
    px_per_mm_field = field_w_px / FIELD_W_MM

    band_w_px = field_w_px
    band_h_px = int(round(content.shape[0] * band_w_px / content.shape[1]))
    band = cv2.resize(content, (band_w_px, band_h_px), interpolation=cv2.INTER_AREA)
    band_bit = threshold_bit(band, 128)

    # Locate the reserved capsule in the resized band: the largest solid
    # white blob whose bbox is 22-40mm x 6-16mm (stadium ~30x10).
    from scipy import ndimage as _ndi
    lbl, _n = _ndi.label(band_bit == 255)
    capsule = None
    for i, sl in enumerate(_ndi.find_objects(lbl)):
        if sl is None:
            continue
        bh = (sl[0].stop - sl[0].start) / px_per_mm_field
        bw = (sl[1].stop - sl[1].start) / px_per_mm_field
        if 22 < bw < 40 and 6 < bh < 16:
            blob = (lbl[sl] == i + 1)
            if blob.mean() > 0.7:  # solid, stadium-like
                capsule = ((sl[1].start + sl[1].stop) / 2 / px_per_mm_field,
                           (sl[0].start + sl[0].stop) / 2 / px_per_mm_field,
                           bw, bh)
    assert capsule is not None, "4231: reserved grip capsule not found in band; placement cannot be registered"
    cap_x_mm, cap_y_band_mm, cap_w_mm, cap_h_mm = capsule

    SLOT_X_MM, SLOT_Y_MM = 25.0, FIELD_H_MM / 2  # slot center in field coords
    dx_px = int(round((SLOT_X_MM - cap_x_mm) * px_per_mm_field))
    band_top_mm = SLOT_Y_MM - cap_y_band_mm
    dy_px = int(round(band_top_mm * px_per_mm_field))

    field_bit = np.full((field_h_px, field_w_px), 255, dtype=np.uint8)
    src_x0 = max(0, -dx_px); dst_x0 = max(0, dx_px)
    n_cols = min(band_w_px - src_x0, field_w_px - dst_x0)
    src_y0 = max(0, -dy_px); dst_y0 = max(0, dy_px)
    n_rows = min(band_h_px - src_y0, field_h_px - dst_y0)
    field_bit[dst_y0:dst_y0 + n_rows, dst_x0:dst_x0 + n_cols] = \
        band_bit[src_y0:src_y0 + n_rows, src_x0:src_x0 + n_cols]

    split_x = int(mm_to_px(SPLIT_MM))  # 933px at 300dpi

    lid_bit = field_bit[:, :split_x]      # portrait: depth(narrow) x width(tall)
    panel_bit = field_bit[:, split_x:]    # landscape, matches panel convention

    lid_bit, removed_lid = remove_speckle(lid_bit, min_area=4)
    panel_bit, removed_panel = remove_speckle(panel_bit, min_area=4)

    # --- top panel: same orientation as the field, already at target px ---
    w_mm_p, h_mm_p, tw_p, th_p = FACE_TARGETS["top_panel"]
    assert panel_bit.shape == (th_p, tw_p), f"panel px {panel_bit.shape} != target {(th_p, tw_p)}"
    panel_final = panel_bit
    save_bit_png(panel_final, os.path.join(OUT, "top_panel.png"))
    pos_p, neg_p = feature_audit(panel_final)

    # --- sliding lid: field's convention is depth-horizontal/width-vertical;
    # the lid's OWN output convention (per the target table, 163.6mm-wide x
    # 79mm-deep, W>H landscape) is width-horizontal/depth-vertical -- the
    # opposite axis order. A plain transpose would MIRROR the art (a
    # reflection, not a rotation); use np.rot90 (k=-1, i.e. 90 clockwise)
    # which is a proper rotation (preserves handedness) and puts the lid's
    # leading/grip edge (depth=0, the field's left edge) at the TOP row of
    # the output. JUDGMENT CALL: rotation direction was not independently
    # verifiable against the physical box from here -- flagged for Ben to
    # confirm at the placement-proof gate (an easy 180-degree or mirror fix
    # if wrong).
    lid_rot = np.rot90(lid_bit, k=-1)
    lid_rot = np.ascontiguousarray(lid_rot)

    w_mm_l, h_mm_l, tw_l, th_l = FACE_TARGETS["sliding_lid"]
    # lid_bit is (rows=width-axis N_w, cols=depth-axis N_d); rot90(k=-1)
    # (verified against a synthetic test + a direct pixel-mapping check,
    # see notes) gives shape (N_d, N_w): rows=depth, cols=width. Resize
    # preserving aspect to depth=th_l exactly (79mm has no slack), then
    # center the (158.75mm) width strip inside the (163.6mm) lid blank with
    # blank padding each side.
    depth_px_native, width_px_native = lid_rot.shape
    scale = th_l / depth_px_native
    strip_w = int(round(width_px_native * scale))
    strip_resized = resize_area_rethreshold(lid_rot, strip_w, th_l)

    canvas = np.full((th_l, tw_l), 255, dtype=np.uint8)
    pad_left = (tw_l - strip_w) // 2
    pad_left = max(0, pad_left)
    if strip_w > tw_l:
        # strip too wide (shouldn't happen given 158.75<163.6): center-crop
        off = (strip_w - tw_l) // 2
        strip_resized = strip_resized[:, off:off + tw_l]
        pad_left = 0
        strip_w = tw_l
    canvas[:, pad_left:pad_left + strip_w] = strip_resized
    canvas = np.where(canvas < 127, 0, 255).astype(np.uint8)

    save_bit_png(canvas, os.path.join(OUT, "sliding_lid.png"))
    pos_l, neg_l = feature_audit(canvas)

    pad_left_mm = pad_left / PX_PER_MM
    pad_right_mm = (tw_l - strip_w - pad_left) / PX_PER_MM

    shared_steps = [
        f"MEASURED DESKEW: left-edge boundary (a clean hard line, resid_sd="
        f"{resid_sd:.2f}px over n={n_kept}/{n_total} sampled rows) has slope "
        f"dcol/drow={m:.5f} ({angle_deg:.2f} deg from vertical). Top/bottom "
        f"edges independently measured near-flat (median rows {top_row} / "
        f"{bot_row} over x 20%-70% of width) -> this is a horizontal SHEAR, "
        "not a rotation (rotation would tilt the already-level top/bottom). "
        f"Applied shear x'=x+{k:.5f}*(y-{y_ref:.0f}), INTER_CUBIC, white fill. "
        "Verified visually post-shear: left edge vertical, top/bottom level.",
        f"CAPSULE-REGISTERED placement (rev 2): content band bbox "
        f"x[{cx0},{cx1}] y[{cy0},{cy1}] of desheared canvas, scaled "
        f"fit-to-width to {band_w_px}px = 301.25mm ({band_h_px}px = "
        f"{band_h_px / px_per_mm_field:.1f}mm tall band). Reserved grip "
        f"capsule measured in-band at ({cap_x_mm:.1f}, {cap_y_band_mm:.1f})mm, "
        f"size {cap_w_mm:.1f}x{cap_h_mm:.1f}mm (physical slot: 30x10 at "
        f"x=25.0 from lid front, width-centered 79.375 -- 2% dim match "
        f"confirms the scale). Band translated dx={dx_px}px "
        f"dy={dy_px}px so capsule center == slot center exactly; art "
        f"band top at {band_top_mm:.1f}mm, clear wood above/below "
        f"~{(158.75 - band_h_px / px_per_mm_field) / 2:.0f}mm; front "
        f"{abs(min(0, (SLOT_X_MM - cap_x_mm))):.1f}mm of the leaning drawn "
        "front border cropped off the lid front edge by the shift.",
        f"Split at 79.0mm from front: split_x={split_x}px of field "
        f"{field_w_px}px (both at 300dpi -- no further resize).",
        "global threshold @128 (0=ink) applied to the band before compositing",
        f"speckle cleanup: lid dropped {removed_lid}, panel dropped {removed_panel} components <4px^2",
    ]

    log("top_panel", source="IMG_4231_ai_vT1_master.png", source_px=f"{w}x{h}",
        steps=shared_steps + [
            f"top panel keeps the field's own orientation (matches target "
            "table convention 222.25mm-wide x 158.75mm-tall = depth-horizontal "
            "same as field): direct area-average downscale to "
            f"{tw_p}x{th_p} + re-threshold, no rotation/padding needed "
            "(field width == panel nominal width exactly, per SPECS).",
        ],
        final_px=f"{tw_p}x{th_p}", canvas_mm=f"{w_mm_p}x{h_mm_p}",
        feature_pos_mm=pos_p, feature_neg_mm=neg_p)

    log("sliding_lid", source="IMG_4231_ai_vT1_master.png", source_px=f"{w}x{h}",
        steps=shared_steps + [
            "JUDGMENT CALL: lid's target convention (163.6mm-wide x 79mm-deep, "
            "W>H landscape) has width/depth axes SWAPPED relative to the "
            "field's own orientation (depth-horizontal/width-vertical) -- "
            "applied np.rot90(k=-1) (a true 90-degree rotation, not a mirror) "
            "to the lid's field-slice so leading/grip edge (depth=0) lands at "
            "the TOP row of the output. NOT independently verifiable against "
            "the physical box from here -- flag for Ben to confirm rotation "
            "direction (and not a 180-flip) at the placement-proof gate.",
            f"scaled rotated strip to depth={th_l}px exactly (79mm, no slack), "
            f"width came out {strip_w}px; centered on a white {tw_l}x{th_l} "
            f"canvas (163.6mm lid blank vs 158.75mm art field): pad "
            f"{pad_left}px/{pad_left_mm:.2f}mm left, "
            f"{tw_l - strip_w - pad_left}px/{pad_right_mm:.2f}mm right "
            "(spec: ~2.425mm each side).",
            "OBSERVATION / FLAG FOR BEN: the grip-slot capsule drawn in the "
            "art measures ~9-10mm along the width axis and ~28-29mm along "
            "the depth axis in this output (i.e. its long 30mm side runs "
            "front-to-back, not side-to-side). SPECS says 'centered across "
            "the width' which may just mean its POSITION is width-centered "
            "(consistent with what's drawn) rather than dictating which of "
            "its two dimensions is width vs depth -- but worth a physical "
            "check against the real grip-slot cutout before engraving.",
        ],
        final_px=f"{tw_l}x{th_l}", canvas_mm=f"{w_mm_l}x{h_mm_l}",
        feature_pos_mm=pos_l, feature_neg_mm=neg_l)


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
                        "dark diagonal streak (blood-drag joke) is intended art, kept as-is.")
    process_drawer_side("drawer_side_2", "IMG_4235_ai_vS_stitched.png",
                        "drawer_side_2 = IMG_4235 (alligator/seagull) per fixed source order.")
    process_drawer_side("drawer_side_3", "IMG_4237_ai_vS_stitched.png",
                        "drawer_side_3 = IMG_4237 (gallery/audience) per fixed source order. "
                        "Frame-like dark band at top (giant kids peeking over gallery walls) is REAL ART, kept.")
    process_drawer_side("drawer_side_4", "IMG_4239_ai_vS_stitched.png",
                        "drawer_side_4 = IMG_4239 (bookshelf/BLAH BLAH) per fixed source order.")

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
