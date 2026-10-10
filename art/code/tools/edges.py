"""Dev helper: stack top and bottom strips of a trimmed photo (with grids) to read edge polylines."""
import subprocess
import sys
from pathlib import Path

from PIL import Image

n, outdir = sys.argv[1], Path(sys.argv[2])
REPO = Path(__file__).resolve().parents[3]
src = REPO / "art" / "trimmed" / f"{n}.jpeg"
W, H = Image.open(src).size
py = sys.executable
tool = Path(__file__).with_name("grid.py")
parts = []
for name, box in [("top", (0, 0, W, 160)), ("bot", (0, H - 220, W, H))]:
    half = W // 2
    for k, (a, b) in enumerate([(0, half + 50), (half - 50, W)]):
        out = outdir / f"_{n}_{name}{k}.png"
        subprocess.run([py, str(tool), str(src), str(out), "20", f"{a},{box[1]},{b},{box[3]}", "1800"], check=True)
        parts.append(Image.open(out))
h = sum(p.height for p in parts) + 10 * len(parts)
sheet = Image.new("RGB", (1800, h), "white")
y = 0
for p in parts:
    sheet.paste(p, (0, y))
    y += p.height + 10
sheet.save(outdir / f"edges_{n}.png")
