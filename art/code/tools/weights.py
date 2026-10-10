"""Dev helper: stroke-weight profile per default variant (skeleton width
percentiles, excluding solids wider than 1.5 mm), to compare faces."""
import json
import sys
from pathlib import Path

import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from faxart.vector import rasterize_svg  # noqa: E402

man = json.loads((HERE / "manifest.json").read_text())
for fid, f in man["faces"].items():
    v = next(x for x in f["variants"] if x["default"])
    ink = rasterize_svg(HERE / v["svg"], 40)
    w = 2 * ndi.distance_transform_edt(ink)[skeletonize(ink)] / 40
    w = w[w < 1.5]
    print(f"{fid:8s} p25 {np.percentile(w, 25):.2f}  p50 {np.percentile(w, 50):.2f}  "
          f"p75 {np.percentile(w, 75):.2f}  p90 {np.percentile(w, 90):.2f}")
