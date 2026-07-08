#!/usr/bin/env python3
"""Extract dark linework (black marker + parrot outlines) from corrected photo.

Produces a clean B/W mask: ink = black, everything else = white.

Approach: thick black-marker letters can be ~100-150px wide at this
resolution, so a naive local-mean adaptive threshold fails (the local
neighborhood inside a big solid letter is *also* dark, so the letter
interior reads as "background" and only the edges pop out as rings).

Instead we estimate the smooth background illumination (the yellow ground's
lighting gradient) via a large grayscale morphological CLOSE, which fills in
dark valleys (ink, of any width up to ~kernel size) while tracking the slow
lighting gradient. Then ink = wherever the real image is significantly
darker than that estimated background.
"""
import sys
import cv2
import numpy as np

src = sys.argv[1] if len(sys.argv) > 1 else "art/pilot/corrected_original.png"
dst = sys.argv[2] if len(sys.argv) > 2 else "art/pilot/linework_mask.png"
close_ksize = int(sys.argv[3]) if len(sys.argv) > 3 else 251
diff_thresh = int(sys.argv[4]) if len(sys.argv) > 4 else 35
min_area = int(sys.argv[5]) if len(sys.argv) > 5 else 25

img = cv2.imread(src, cv2.IMREAD_COLOR)
if img is None:
    raise SystemExit(f"failed to load {src}")

b, g, r = cv2.split(img)
# Max channel: yellow ground + colored pencil fill all have a bright channel;
# true black marker ink is dark in all three, so max() stays low only there.
value = cv2.max(cv2.max(b, g), r)
value = cv2.medianBlur(value, 9)

kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_ksize, close_ksize))
background = cv2.morphologyEx(value, cv2.MORPH_CLOSE, kernel)

diff = cv2.subtract(background, value)  # positive where ink is darker than local bg
_, ink = cv2.threshold(diff, diff_thresh, 255, cv2.THRESH_BINARY)

# Denoise: open to drop hairline speckle, then drop small components outright.
kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
ink = cv2.morphologyEx(ink, cv2.MORPH_OPEN, kernel_open, iterations=1)

num, labels, stats, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
clean = np.zeros_like(ink)
for i in range(1, num):
    if stats[i, cv2.CC_STAT_AREA] >= min_area:
        clean[labels == i] = 255

kernel_close_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
clean = cv2.morphologyEx(clean, cv2.MORPH_CLOSE, kernel_close_small, iterations=1)

out = cv2.bitwise_not(clean)  # white bg, black ink
cv2.imwrite(dst, out)
print("wrote", dst, out.shape, "close_ksize=", close_ksize, "diff_thresh=", diff_thresh, "min_area=", min_area)
