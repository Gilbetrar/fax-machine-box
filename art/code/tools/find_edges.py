"""Dev helper: find the cardboard panel's top/bottom edge lines in a trimmed photo
(darkest long horizontal band per column window), print robust quadratic fits and
write an overlay for checking by eye.

usage: find_edges.py IMG_n OUTDIR [top_band_px] [bot_band_px]
"""
import sys
from pathlib import Path

import cv2
import numpy as np

n, out = sys.argv[1], Path(sys.argv[2])
tb = int(sys.argv[3]) if len(sys.argv) > 3 else 120
bb = int(sys.argv[4]) if len(sys.argv) > 4 else 220
REPO = Path(__file__).resolve().parents[3]
img = cv2.imread(str(REPO / "art" / "trimmed" / f"{n}.jpeg"))
g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
H, W = g.shape
dark = 255 - g
# long horizontal structures: average over a wide horizontal window
hz = cv2.blur(dark, (61, 3))


def fit(rows_fn, label):
    xs, ys = [], []
    for x in range(30, W - 30, 25):
        y = rows_fn(x)
        if y is not None:
            xs.append(x)
            ys.append(y)
    xs, ys = np.array(xs), np.array(ys, float)
    keep = np.ones(len(xs), bool)
    for _ in range(4):
        c = np.polyfit(xs[keep], ys[keep], 2)
        r = ys - np.polyval(c, xs)
        s = np.std(r[keep])
        keep = np.abs(r) < max(2.5 * s, 3)
    print(label, "coef", np.round(c, 8).tolist(), "kept", keep.sum(), "/", len(xs),
          "y@0,mid,W", [round(float(np.polyval(c, v)), 1) for v in (0, W / 2, W)])
    return c, xs[keep], ys[keep]


ct, xt, yt = fit(lambda x: int(np.argmax(hz[:tb, x])), "top")
cb, xb, yb = fit(lambda x: H - bb + int(np.argmax(hz[H - bb:, x])), "bot")
vis = img.copy()
for c, col in [(ct, (0, 0, 255)), (cb, (255, 0, 0))]:
    pts = np.array([[x, np.polyval(c, x)] for x in range(0, W, 10)], np.int32)
    cv2.polylines(vis, [pts], False, col, 3)
for x, y in zip(xt, yt):
    cv2.circle(vis, (int(x), int(y)), 4, (0, 255, 0), -1)
for x, y in zip(xb, yb):
    cv2.circle(vis, (int(x), int(y)), 4, (0, 255, 0), -1)
small = cv2.resize(vis, (1800, int(H * 1800 / W)))
cv2.imwrite(str(out / f"fit_{n}.png"), small)
