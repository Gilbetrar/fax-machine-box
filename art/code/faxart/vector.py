"""Vector stage: potrace the cleaned ink mask into smooth filled Beziers, write
an engrave-only SVG in physical mm, and render previews."""

from __future__ import annotations

import io
import re
import subprocess
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

import cairosvg
import numpy as np
from PIL import Image

from .raster import PPM

POTRACE = "potrace"
# -a 1.0: smooth corners (kills stair-steps); -O 0.4: curve optimisation
# tolerance in px (0.02 mm); -t 8: ignore <8 px islands (already despeckled).
POTRACE_ARGS = ["-s", "-a", "1.0", "-O", "0.4", "-t", "8"]


def trace(mask: np.ndarray) -> list[str]:
    """Return potrace path 'd' strings, in potrace's native units
    (0.1 px, y up from the bottom edge)."""
    with tempfile.TemporaryDirectory() as td:
        pbm = Path(td) / "m.pbm"
        Image.fromarray(~mask).convert("1").save(pbm)
        out = subprocess.run([POTRACE, *POTRACE_ARGS, str(pbm), "-o", "-"],
                             check=True, capture_output=True, text=True).stdout
    return re.findall(r'<path d="([^"]+)"', out, flags=re.S)


def write_svg(path: Path, ds: list[str], size_mm: tuple[float, float], title: str,
              desc: str) -> None:
    W, H = size_mm
    s = 1.0 / (10.0 * PPM)  # potrace unit (0.1 px) -> mm
    body = "\n".join(f'<path d="{" ".join(d.split())}"/>' for d in ds)
    svg = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.3f}mm" height="{H:.3f}mm" '
        f'viewBox="0 0 {W:.3f} {H:.3f}">\n'
        f"<title>{escape(title)}</title>\n<desc>{escape(desc)}</desc>\n"
        f'<g id="engrave" fill="#000000" stroke="none" fill-rule="nonzero" '
        f'transform="matrix({s:.6f},0,0,{-s:.6f},0,{H:.3f})">\n{body}\n</g>\n</svg>\n'
    )
    path.write_text(svg)


def rasterize_svg(svg_path: Path, ppm: float = PPM) -> np.ndarray:
    """bool ink mask of an art SVG rendered at ppm (white background)."""
    txt = Path(svg_path).read_text()
    m = re.search(r'width="([\d.]+)mm" height="([\d.]+)mm"', txt)
    W, H = float(m.group(1)), float(m.group(2))
    png = cairosvg.svg2png(bytestring=txt.encode(), output_width=int(round(W * ppm)),
                           output_height=int(round(H * ppm)), background_color="white")
    g = np.array(Image.open(io.BytesIO(png)).convert("L"))
    return g < 128


def preview_png(svg_path: Path, png_path: Path, width: int = 1200) -> None:
    cairosvg.svg2png(url=str(svg_path), write_to=str(png_path), output_width=width,
                     background_color="white")
