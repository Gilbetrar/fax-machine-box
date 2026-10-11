"""Dev helper: crop of exported (cut-set) ink around a point, with thin (red)
and gap (blue) violations. FAXBOX_THICKNESS=T trimmed_crop.py FACE VARIANT KERF X Y OUT"""
import os
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from trimmed_check import PPM, cs, raster, rules  # noqa: E402

face, var, kerf, X, Y, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5]), sys.argv[6]
items = cs.generate_items(Path(tempfile.mkdtemp()), kerf)
it = next(i for i in items if i.face == face)
r = cs.clearance(it, var)
x0, y0, x1, y1 = r["material"].bounds
m = raster(r["ink"].buffer(0), x0, y0, x1 - x0, y1 - y0)
mat = raster(r["material"], x0, y0, x1 - x0, y1 - y0)
thin, gap, _, _ = rules.violations(m)
cx, cy, h = int((X - x0) * PPM), int((Y - y0) * PPM), int(3 * PPM)
sl = (slice(max(0, cy - h), cy + h), slice(max(0, cx - h), cx + h))
img = np.full(m[sl].shape + (3,), 255, np.uint8)
img[~mat[sl]] = (200, 200, 255)
img[m[sl]] = 0
img[thin[sl]] = (0, 0, 255)
img[gap[sl]] = (255, 0, 0)
cv2.imwrite(out, cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_NEAREST))
