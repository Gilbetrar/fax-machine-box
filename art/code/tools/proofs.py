"""Proof sheets for the code-drawn art: every face variant over its real cut
geometry, plus side-by-side comparisons (Ben's original photo | July
AI-placement engrave | new code art) and the assembled lid + top panel.

usage: proofs.py OUTDIR [ppm]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from faxart.geometry import FACES, cut_polylines, material_mask, size_mm  # noqa: E402
from faxart.vector import rasterize_svg  # noqa: E402

REPO = HERE.parents[1]
out = Path(sys.argv[1])
PPM = float(sys.argv[2]) if len(sys.argv) > 2 else 12.0
out.mkdir(parents=True, exist_ok=True)
FONT = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 22)
SMALL = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 16)
PAD = 8.0  # mm around the art canvas (finger tabs stick out)

ORIGINAL = {
    "left": "IMG_4228", "right": "IMG_4230", "front": "IMG_4229",
    "top": "IMG_4231", "lid": "IMG_4231", "B_face": "IMG_4236",
    "T_face": "IMG_4238", "B_left": "IMG_4233", "B_right": "IMG_4235",
    "T_left": "IMG_4237", "T_right": "IMG_4239",
}
JULY = {
    "left": "left_wall.png", "right": "right_wall.png", "front": "front_wall.png",
    "top": "top_panel.png", "lid": "sliding_lid.png",
    "B_face": "faceplate_colors.png", "T_face": "faceplate_lines.png",
    "B_left": "drawer_side_1.png", "B_right": "drawer_side_2.png",
    "T_left": "drawer_side_3.png", "T_right": "drawer_side_4.png",
}


def on_geometry(face_id: str, svg: Path, title: str) -> Image.Image:
    W, H = size_mm(face_id)
    ink = rasterize_svg(svg, PPM)
    pw, ph = int((W + 2 * PAD) * PPM), int((H + 2 * PAD) * PPM)
    o = int(PAD * PPM)
    img = np.full((ph + 60, pw, 3), 255, np.uint8)
    mat = material_mask(face_id, PPM, 0.0)
    canvas = img[o:o + ink.shape[0], o:o + ink.shape[1]]
    canvas[~mat] = (232, 232, 232)            # cut away / outside the part
    canvas[ink] = (0, 0, 0)
    for kind, p in cut_polylines(face_id):
        pts = np.round(((p + PAD) * PPM) * 16).astype(np.int32).reshape(-1, 1, 2)
        cv2.polylines(img, [pts], True, (255, 60, 0) if kind == "outer" else (255, 60, 0), 2,
                      cv2.LINE_AA, shift=4)
    im = Image.fromarray(img[:, :, ::-1].copy())
    d = ImageDraw.Draw(im)
    d.text((10, ph + 8), title, fill=(0, 0, 0), font=FONT)
    d.text((10, ph + 36), f"{W} x {H} mm   blue = cut path, grey = no wood, black = engrave",
           fill=(90, 90, 90), font=SMALL)
    return im


def label(im: Image.Image, text: str) -> Image.Image:
    c = Image.new("RGB", (im.width, im.height + 34), "white")
    c.paste(im.convert("RGB"), (0, 34))
    ImageDraw.Draw(c).text((6, 6), text, fill=(0, 0, 0), font=FONT)
    return c


def fit_w(im: Image.Image, w: int) -> Image.Image:
    return im.resize((w, max(1, int(im.height * w / im.width))), Image.LANCZOS)


def main():
    man = json.loads((HERE / "manifest.json").read_text())
    sheets = []
    for fid, f in man["faces"].items():
        for v in f["variants"]:
            im = on_geometry(fid, HERE / v["svg"], f"{fid} / {v['id']}: {v['label']}"
                             + ("  (default)" if v["default"] else ""))
            p = out / f"proof_{fid}__{v['id']}.png"
            im.save(p)
            sheets.append(p)
        # comparison: original | July engrave | new default
        Wcol = 1400
        orig = Image.open(REPO / "art" / "trimmed" / f"{ORIGINAL[fid]}.jpeg")
        july = Image.open(REPO / "art" / "engrave" / JULY[fid])
        dv = next(v for v in f["variants"] if v["default"])
        new = Image.fromarray(np.where(rasterize_svg(HERE / dv["svg"], 10), 0, 255).astype(np.uint8))
        if fid == "lid":   # July file is landscape; show both in the part frame
            july = july.transpose(Image.ROTATE_90)
        rows = [label(fit_w(orig, Wcol), f"Ben's original photo ({ORIGINAL[fid]})"),
                label(fit_w(july, Wcol), f"July AI placement (art/engrave/{JULY[fid]})"),
                label(fit_w(new, Wcol), f"New code art ({dv['id']})")]
        if fid == "lid":
            rows = [label(fit_w(r, 420), t) for r, t in [
                (orig, "original"), (july, "July"), (new, "new")]]
            sheet = Image.new("RGB", (sum(r.width for r in rows) + 40, max(r.height for r in rows)), "white")
            x = 0
            for r in rows:
                sheet.paste(r, (x, 0))
                x += r.width + 20
        else:
            sheet = Image.new("RGB", (Wcol, sum(r.height for r in rows) + 40), "white")
            y = 0
            for r in rows:
                sheet.paste(r, (0, y))
                y += r.height + 20
        sheet.save(out / f"compare_{fid}.png")

    # assembled top surface: lid (front) + top panel, as seen from above
    for vid in ("a", "c"):
        lid = rasterize_svg(HERE / f"out/lid__{vid}.svg", PPM)
        top = rasterize_svg(HERE / f"out/top__{vid}.svg", PPM)
        pad = int(round((163.6 - 158.75) / 2 * PPM))
        lid = lid[pad:pad + top.shape[0], :]
        gap = int(2 * PPM)
        both = np.full((top.shape[0], lid.shape[1] + gap + top.shape[1]), 255, np.uint8)
        both[:, :lid.shape[1]][lid] = 0
        both[:, lid.shape[1] + gap:][top] = 0
        both[:, lid.shape[1]:lid.shape[1] + gap] = 200
        label(Image.fromarray(both), f"Top surface, variant {vid.upper()}: sliding lid (front, left) | "
              f"top panel (grey bar = seam)").save(out / f"assembled_top_{vid}.png")
    print(f"{len(sheets)} proofs -> {out}")


main()
