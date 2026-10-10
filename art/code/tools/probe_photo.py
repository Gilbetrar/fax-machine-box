"""Dev probe: warp a photo source to a drawer-side canvas, dump ink + tone views.

usage: probe_photo.py IMG_n "x,y;x,y;x,y;x,y" ink_t OUTDIR
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from faxart import raster as R  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
n, quad, ink_t, out = sys.argv[1], sys.argv[2], float(sys.argv[3]), Path(sys.argv[4])
out.mkdir(parents=True, exist_ok=True)
q = [tuple(float(v) for v in p.split(",")) for p in quad.split(";")]
img = cv2.imread(str(REPO / "art" / "trimmed" / f"{n}.jpeg"))
can = R.warp_to_canvas(img, q, (212.25, 50.325))
ink, tone = R.photo_layers(can, ink_t=ink_t)
cv2.imwrite(str(out / f"{n}_warp.jpg"), can)
cv2.imwrite(str(out / f"{n}_ink.png"), np.where(ink, 0, 255).astype(np.uint8))
cv2.imwrite(str(out / f"{n}_tone.png"), (255 - np.clip(tone * 2.5, 0, 1) * 255).astype(np.uint8))
print(can.shape, ink.mean(), np.percentile(tone, [50, 75, 90, 97]))
