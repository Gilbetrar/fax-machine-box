"""Export cut-ready SVG sheets to PDF (CorelDraw import fallback).

NYC Resistor's workflow is CorelDraw X5-based, and their tips page warns
that Inkscape's raw SVG export can get corrupted on import there --
recommending PDF instead (see README "Cut day at NYC Resistor", step 4).
This script converts each cut-ready sheet (output/sheet_*.svg) plus the kerf
calibration coupon (output/kerf_coupon.svg) to a same-named PDF alongside it.

Physical scale is the entire point: every source SVG declares its
width/height in mm (see tests/svg_utils.py's get_svg_dimensions_mm, which
gates this for the SVGs themselves), and cairosvg preserves those mm
dimensions as the PDF page's MediaBox (1mm = 72/25.4 pt) as long as no
output_width/output_height/scale override is passed -- CorelDraw honors the
PDF page box, so this is what keeps the physical part sizes correct on
import. Do not add scaling options here without re-verifying the MediaBox
math (see tests exercising this, or re-derive by hand: mm * 72 / 25.4 = pt).
"""

from __future__ import annotations

import re
from pathlib import Path

import cairosvg

from faxbox.config import OUTPUT_DIR


def _sheet_sort_key(path: Path) -> tuple[int, str]:
    """Numeric sort for sheet_1.svg, sheet_2.svg, ... sheet_10.svg (not
    lexicographic, which would put sheet_10 before sheet_2)."""
    m = re.search(r"(\d+)", path.stem)
    return (int(m.group(1)) if m else 0, path.name)


def _cut_files(output_path: Path) -> list[Path]:
    """Every cut-ready file this project sends to the laser: sheet_*.svg
    (however many `layout.py` currently nests) plus the standalone kerf
    coupon. Deliberately excludes final_layout.svg and the raw per-part
    files (outer_shell.svg, drawer.svg, lids.svg) -- none of those are sent
    for cutting (see layout.py's module docstring)."""
    sheets = sorted(output_path.glob("sheet_*.svg"), key=_sheet_sort_key)
    coupon = output_path / "kerf_coupon.svg"
    files = list(sheets)
    if coupon.exists():
        files.append(coupon)
    return files


def export_pdfs() -> list[Path]:
    """Convert every cut-ready SVG to a same-named PDF in output/.

    Returns:
        List of generated PDF paths, in the same order as the source SVGs.
    """
    output_path = Path(OUTPUT_DIR)
    svg_files = _cut_files(output_path)
    if not svg_files:
        print(f"Error: no sheet_*.svg / kerf_coupon.svg found in {output_path.absolute()}")
        print("Generate them first: .venv/bin/python -m faxbox.layout")
        raise FileNotFoundError(f"No cut-ready SVGs in {output_path}")

    pdf_paths: list[Path] = []
    for svg_path in svg_files:
        pdf_path = svg_path.with_suffix(".pdf")
        cairosvg.svg2pdf(url=str(svg_path), write_to=str(pdf_path))
        pdf_paths.append(pdf_path)

    print(f"Exported {len(pdf_paths)} PDF(s) to {output_path.absolute()}:")
    for pdf_path in pdf_paths:
        print(f"  {pdf_path.name}")
    print(
        "Physical scale is preserved (PDF page box = SVG's declared mm size); "
        "use these as the CorelDraw import fallback if raw SVG import mangles a sheet."
    )
    return pdf_paths


if __name__ == "__main__":
    export_pdfs()
