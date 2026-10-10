"""Dev helper: render a source image with a labelled pixel grid (for picking crop quads by eye).

usage: grid.py SRC OUT [step] [x0,y0,x1,y1] [width]
"""
import sys
from PIL import Image, ImageDraw, ImageFont

src, out = sys.argv[1], sys.argv[2]
step = int(sys.argv[3]) if len(sys.argv) > 3 else 200
box = [int(v) for v in sys.argv[4].split(",")] if len(sys.argv) > 4 and sys.argv[4] != "-" else None
width = int(sys.argv[5]) if len(sys.argv) > 5 else 1800
im = Image.open(src).convert("RGB")
ox, oy = 0, 0
if box:
    im = im.crop(box)
    ox, oy = box[0], box[1]
s = width / im.width
im = im.resize((width, int(im.height * s)))
d = ImageDraw.Draw(im)
f = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial.ttf", 14)
x = (ox // step) * step
while x < ox + im.width / s:
    if x >= ox:
        X = (x - ox) * s
        d.line([(X, 0), (X, im.height)], fill=(255, 0, 255), width=1)
        d.text((X + 2, 2), str(x), fill=(255, 0, 255), font=f)
    x += step
y = (oy // step) * step
while y < oy + im.height / s:
    if y >= oy:
        Y = (y - oy) * s
        d.line([(0, Y), (im.width, Y)], fill=(0, 160, 255), width=1)
        d.text((2, Y + 2), str(y), fill=(0, 120, 255), font=f)
    y += step
im.save(out)
