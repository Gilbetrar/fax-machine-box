"""Dev probe: show colour-marker lines + quantised pencil tone for a photo face."""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from faxart import raster as R  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
n, quad, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
ths = [float(v) for v in sys.argv[4].split(",")] if len(sys.argv) > 4 else [0.12, 0.25, 0.4]
q = [tuple(float(v) for v in p.split(",")) for p in quad.split(";")]
img = cv2.imread(str(REPO / "art" / "trimmed" / f"{n}.jpeg"))
can = R.warp_to_canvas(img, q, (212.25, 50.325))
ink, tone = R.photo_layers(can)
hsv = cv2.cvtColor(can, cv2.COLOR_BGR2HSV)
sat = hsv[:, :, 1] / 255.0
excl = cv2.dilate(R.u8(ink), R.disk(R.px(0.6))).astype(bool)
lev = R.quantize_tone(tone, ths, exclude=excl)
vis = np.full(can.shape, 255, np.uint8)
cols = [(255, 255, 255), (200, 230, 255), (120, 180, 255), (30, 80, 200)]
for i in range(1, len(ths) + 1):
    vis[lev == i] = cols[i]
vis[ink] = 0
cv2.imwrite(str(out / f"{n}_levels.png"), vis)
ts = cv2.GaussianBlur(tone.astype(np.float32), (0, 0), 16)
print("tone pct (non-ink)", np.percentile(ts[~excl], [10, 25, 50, 75, 90, 97]).round(3))
print("sat pct", np.percentile(sat[~excl], [50, 90, 97]).round(3))
