"""Dev helper: render an art SVG at a given px/mm (optionally a mm crop) to PNG.

usage: view.py SVG OUT.png [ppm] [x0,y0,x1,y1 mm]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from faxart.vector import rasterize_svg  # noqa: E402

svg, out = sys.argv[1], sys.argv[2]
ppm = float(sys.argv[3]) if len(sys.argv) > 3 else 8
m = rasterize_svg(Path(svg), ppm)
if len(sys.argv) > 4:
    x0, y0, x1, y1 = [float(v) for v in sys.argv[4].split(",")]
    m = m[int(y0 * ppm):int(y1 * ppm), int(x0 * ppm):int(x1 * ppm)]
Image.fromarray(np.where(m, 0, 255).astype(np.uint8)).save(out)
