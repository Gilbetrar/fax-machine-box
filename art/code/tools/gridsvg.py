"""Dev helper: render an art SVG with its cuts (red) and a labelled mm grid.

usage: gridsvg.py FACE SVG OUT.png ppm x0,y0,x1,y1 [step_mm]
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from faxart.geometry import material_mask  # noqa: E402
from faxart.vector import rasterize_svg  # noqa: E402

face, svg, out, ppm = sys.argv[1], sys.argv[2], sys.argv[3], float(sys.argv[4])
x0, y0, x1, y1 = [float(v) for v in sys.argv[5].split(",")]
step = float(sys.argv[6]) if len(sys.argv) > 6 else 5
ink = rasterize_svg(Path(svg), ppm)
mat = material_mask(face, ppm)
img = np.full(ink.shape + (3,), 255, np.uint8)
img[~mat] = (170, 170, 255)
img[ink] = 0
img[ink & ~mat] = (0, 0, 200)
crop = img[int(y0 * ppm):int(y1 * ppm), int(x0 * ppm):int(x1 * ppm)].copy()
v = np.ceil(x0 / step) * step
while v < x1:
    X = int((v - x0) * ppm)
    cv2.line(crop, (X, 0), (X, crop.shape[0]), (255, 0, 255) if v % (2 * step) == 0 else (255, 200, 255), 1)
    if v % (2 * step) == 0:
        cv2.putText(crop, f"{v:g}", (X + 2, 12), 0, 0.4, (200, 0, 200), 1)
    v += step
v = np.ceil(y0 / step) * step
while v < y1:
    Y = int((v - y0) * ppm)
    cv2.line(crop, (0, Y), (crop.shape[1], Y), (255, 160, 0) if v % (2 * step) == 0 else (255, 220, 170), 1)
    if v % (2 * step) == 0:
        cv2.putText(crop, f"{v:g}", (2, Y - 2), 0, 0.4, (200, 100, 0), 1)
    v += step
cv2.imwrite(out, crop)
