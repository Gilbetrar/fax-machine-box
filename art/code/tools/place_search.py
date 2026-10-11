"""Dev helper: search a translation (dx, dy) for a traced group that minimises
how much of it the through-cuts remove, weighting important boxes 5x.

usage:
  place_search.py left
  place_search.py right GROUP_BOX "IMP1;IMP2;..." dx0,dx1 dy0,dy1
     boxes are u0,v0,u1,v1 in mm on the right-wall canvas as built so far
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from faxart import ai_faces as F  # noqa: E402
from faxart import edits as E  # noqa: E402
from faxart.geometry import material_mask  # noqa: E402
from faxart.vector import rasterize_svg  # noqa: E402

HERE = Path(__file__).resolve().parents[1]
which = sys.argv[1]
if which == "left":
    box = (247, 116, 6151, 2628)
    ink = F.ai_ink("left", "IMG_4228_ai_vH1.png", box, F.fit_contain(box, F.WALL_AREA))
    group = ink & E.rect(ink.shape, 0, 0, 126.0, 127.0)
    important = [(112, 66, 122, 89), (58, 67, 71, 76), (72, 36, 86, 44), (77, 44, 106, 73)]
    dxs, dys = np.arange(-8, 4.6, 0.5), np.arange(-3, 14.6, 0.5)
    face = "left"
else:
    face = "right"
    box = (357, 182, 5969, 2570)
    ink = F.ai_ink("right", "IMG_4230_ai_vH2.png", box, F.fit_contain(box, F.WALL_AREA))
    if len(sys.argv) > 6 and sys.argv[6] == "writer-moved":
        ink = F.relayout_writer(ink)
    gb = [float(v) for v in sys.argv[2].split(",")]
    group = ink & E.rect(ink.shape, *gb)
    important = [tuple(float(v) for v in b.split(",")) for b in sys.argv[3].split(";") if b]
    a, b = (float(v) for v in sys.argv[4].split(","))
    c, d = (float(v) for v in sys.argv[5].split(","))
    dxs, dys = np.arange(a, b + 0.01, 0.5), np.arange(c, d + 0.01, 0.5)

mat = material_mask(face, 20, 0.6)
holes = ~mat
holes[:, : 4 * 20] = False
holes[int(120 * 20):] = False
holes[: 13 * 20] = False
imp = np.zeros_like(ink)
for bx in important:
    imp |= E.rect(ink.shape, *bx)
res = []
for dy in dys:
    for dx in dxs:
        M = E.translate(dx, -dy)
        p = E.affine_paste(np.zeros_like(ink), group, M)
        q = E.affine_paste(np.zeros_like(ink), group & imp, M)
        bottom = p[int(124.5 * 20):].sum() / 400
        left = p[:, : int(4 * 20)].sum() / 400
        a_ = (p & holes).sum() / 400
        ai = (q & holes).sum() / 400
        res.append((round(ai * 5 + a_ + 3 * (bottom + left), 2), float(dx), float(dy), round(a_, 2), round(ai, 2)))
res.sort()
for r in res[:10]:
    print(r)
