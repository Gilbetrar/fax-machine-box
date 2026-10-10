"""Dev helper: render several art SVGs at a fixed width and stack them vertically.

usage: stack.py OUT.png WIDTH SVG [SVG ...]
"""
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from faxart.vector import rasterize_svg  # noqa: E402

out, width, svgs = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
ims = []
for s in svgs:
    txt = Path(s).read_text()
    import re
    W = float(re.search(r'width="([\d.]+)mm"', txt).group(1))
    m = rasterize_svg(Path(s), width / W)
    ims.append(Image.fromarray(np.where(m, 0, 255).astype(np.uint8)))
h = sum(i.height for i in ims) + 12 * len(ims)
sheet = Image.new("L", (max(i.width for i in ims), h), 160)
y = 0
for i in ims:
    sheet.paste(i, (0, y))
    y += i.height + 12
sheet.save(out)
