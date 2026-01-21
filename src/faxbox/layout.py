"""Combine all fax machine box parts into a single layout SVG for laser cutting.

Creates final_layout.svg with all parts arranged to minimize material waste.
Color coding for Ponoko:
- Blue (#0000FF): Cut lines
- Red (#FF0000): Engrave lines
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import NamedTuple

from faxbox.config import OUTPUT_DIR


class BoundingBox(NamedTuple):
    """Bounding box with width and height in mm."""
    width: float
    height: float


def parse_svg_dimensions(svg_path: Path) -> BoundingBox:
    """Extract width and height from SVG viewBox or dimensions."""
    tree = ET.parse(svg_path)
    root = tree.getroot()

    # Try viewBox first (format: "minX minY width height")
    viewbox = root.get("viewBox")
    if viewbox:
        parts = viewbox.split()
        if len(parts) == 4:
            return BoundingBox(float(parts[2]), float(parts[3]))

    # Fall back to width/height attributes
    width = root.get("width", "0").replace("mm", "")
    height = root.get("height", "0").replace("mm", "")
    return BoundingBox(float(width), float(height))


def convert_colors_to_ponoko(content: str) -> str:
    """Convert all stroke colors to Ponoko standard (blue=cut, red=engrave).

    Black and other colors are converted to blue (cut).
    Red is preserved for engraving.
    """
    # Convert black to blue
    content = re.sub(r'stroke="rgb\(0,0,0\)"', 'stroke="rgb(0,0,255)"', content)
    content = re.sub(r'stroke="#000000"', 'stroke="#0000FF"', content)
    content = re.sub(r'stroke="black"', 'stroke="#0000FF"', content)

    return content


def extract_svg_content(svg_path: Path) -> str:
    """Extract the inner content of an SVG (everything inside <svg> tags)."""
    with open(svg_path, "r") as f:
        content = f.read()

    # Remove XML declaration
    content = re.sub(r'<\?xml[^?]*\?>\s*', '', content)

    # Extract content between <svg> tags, removing the outer svg element
    match = re.search(r'<svg[^>]*>(.*)</svg>', content, re.DOTALL)
    if match:
        content = match.group(1)

    # Remove metadata blocks (contain namespace prefixes that break combined SVG)
    content = re.sub(r'<metadata>.*?</metadata>', '', content, flags=re.DOTALL)
    content = re.sub(r'<title>.*?</title>', '', content, flags=re.DOTALL)

    # Remove comments (boxes.py metadata)
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)

    # Convert colors to Ponoko standard
    content = convert_colors_to_ponoko(content)

    return content


def create_layout_svg(
    shell_svg: Path,
    drawer_svg: Path,
    lids_svg: Path,
    output_path: Path,
    spacing: float = 5.0
) -> None:
    """Combine all part SVGs into a single layout.

    Layout strategy:
    - Row 1: Outer shell parts
    - Row 2: Two drawer sets side by side, then lids

    Args:
        shell_svg: Path to outer shell SVG
        drawer_svg: Path to drawer SVG (will be duplicated for 2 drawers)
        lids_svg: Path to lids SVG
        output_path: Path for output combined SVG
        spacing: Gap between parts in mm
    """
    # Get dimensions of each component
    shell_box = parse_svg_dimensions(shell_svg)
    drawer_box = parse_svg_dimensions(drawer_svg)
    lids_box = parse_svg_dimensions(lids_svg)

    # Calculate layout dimensions
    # Row 1: Shell parts
    # Row 2: Drawer 1 | Drawer 2 | Lids

    row1_width = shell_box.width
    row1_height = shell_box.height

    row2_width = drawer_box.width * 2 + lids_box.width + spacing * 2
    row2_height = max(drawer_box.height, lids_box.height)

    total_width = max(row1_width, row2_width)
    total_height = row1_height + spacing + row2_height

    # Extract SVG content
    shell_content = extract_svg_content(shell_svg)
    drawer_content = extract_svg_content(drawer_svg)
    lids_content = extract_svg_content(lids_svg)

    # Build the combined SVG
    svg_header = f'''<?xml version='1.0' encoding='utf-8'?>
<svg
    height="{total_height}mm"
    width="{total_width}mm"
    viewBox="0 0 {total_width} {total_height}"
    xmlns="http://www.w3.org/2000/svg"
    xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape">
<!--
Fax Machine Box - Final Assembly Layout
All parts combined for laser cutting service (e.g., Ponoko)

Color coding:
  Blue (#0000FF) = Cut lines
  Red (#FF0000) = Engrave lines

Parts included:
  - Outer shell (all pieces)
  - 2x Drawer sets (5 pieces each)
  - 2x Lid sets

Material: 3.175mm (1/8") plywood
Total dimensions: {total_width:.1f}mm x {total_height:.1f}mm
-->
<title>Fax Machine Box - Final Layout</title>
'''

    # Position each group
    # Row 1: Shell at origin
    shell_group = f'''
<!-- Outer Shell Parts -->
<g id="outer-shell" transform="translate(0, 0)" inkscape:label="Outer Shell">
{shell_content}
</g>
'''

    # Row 2: Drawer 1
    drawer1_y = row1_height + spacing
    drawer1_group = f'''
<!-- Drawer 1 -->
<g id="drawer-1" transform="translate(0, {drawer1_y})" inkscape:label="Drawer 1">
{drawer_content}
</g>
'''

    # Row 2: Drawer 2
    drawer2_x = drawer_box.width + spacing
    drawer2_group = f'''
<!-- Drawer 2 -->
<g id="drawer-2" transform="translate({drawer2_x}, {drawer1_y})" inkscape:label="Drawer 2">
{drawer_content}
</g>
'''

    # Row 2: Lids
    lids_x = drawer_box.width * 2 + spacing * 2
    lids_group = f'''
<!-- Lids (Sliding + Flat) -->
<g id="lids" transform="translate({lids_x}, {drawer1_y})" inkscape:label="Lids">
{lids_content}
</g>
'''

    svg_footer = "\n</svg>"

    # Combine all parts
    combined_svg = svg_header + shell_group + drawer1_group + drawer2_group + lids_group + svg_footer

    # Write output
    with open(output_path, "w") as f:
        f.write(combined_svg)


def generate_layout() -> Path:
    """Generate the final layout SVG combining all parts.

    Returns:
        Path to the generated layout SVG.
    """
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)

    shell_svg = output_path / "outer_shell.svg"
    drawer_svg = output_path / "drawer.svg"
    lids_svg = output_path / "lids.svg"
    final_layout = output_path / "final_layout.svg"

    # Check that all source files exist
    missing = []
    for svg_file in [shell_svg, drawer_svg, lids_svg]:
        if not svg_file.exists():
            missing.append(svg_file.name)

    if missing:
        print("Error: Missing source SVG files. Generate them first:")
        for name in missing:
            print(f"  - {name}")
        print("\nRun these commands:")
        print("  python3 -m faxbox.shell_generator")
        print("  python3 -m faxbox.generate_drawers")
        print("  python3 -m faxbox.generate_lids")
        raise FileNotFoundError(f"Missing: {', '.join(missing)}")

    # Create the combined layout
    create_layout_svg(shell_svg, drawer_svg, lids_svg, final_layout)

    # Get final dimensions
    shell_box = parse_svg_dimensions(shell_svg)
    drawer_box = parse_svg_dimensions(drawer_svg)
    lids_box = parse_svg_dimensions(lids_svg)

    row2_width = drawer_box.width * 2 + lids_box.width + 10  # spacing
    total_width = max(shell_box.width, row2_width)
    total_height = shell_box.height + 5 + max(drawer_box.height, lids_box.height)

    print(f"Generated final layout: {final_layout.absolute()}")
    print(f"\nLayout dimensions: {total_width:.1f}mm x {total_height:.1f}mm")
    print(f"  ({total_width / 25.4:.1f}\" x {total_height / 25.4:.1f}\")")
    print(f"\nParts included:")
    print(f"  - Outer shell: {shell_box.width:.1f}mm x {shell_box.height:.1f}mm")
    print(f"  - 2x Drawers: {drawer_box.width:.1f}mm x {drawer_box.height:.1f}mm each")
    print(f"  - Lids: {lids_box.width:.1f}mm x {lids_box.height:.1f}mm")
    print(f"\nColor coding:")
    print(f"  Blue (#0000FF) = Cut lines")
    print(f"  Red (#FF0000) = Engrave lines")

    return final_layout


if __name__ == "__main__":
    generate_layout()
