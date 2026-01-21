"""Generate outer shell for fax machine box with internal dividers."""

from pathlib import Path

from boxes import Boxes
from boxes import edges

from faxbox.config import (
    BURN,
    DRAWER,
    DRAWER_MATERIAL_THICKNESS,
    ENGRAVE_COLOR,
    ENGRAVE_FONT_SIZE,
    ENGRAVE_FONT_SPACING,
    ENGRAVE_LINE_WIDTH,
    LID_GROOVE_DEPTH,
    LID_GROOVE_WIDTH,
    OUTPUT_DIR,
    PAPER_COMPARTMENT_DEPTH,
    SHELL,
)


# Pixel font definitions: 5 columns x 7 rows
PIXEL_FONT = {
    'F': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6),
          (1, 0), (2, 0), (3, 0), (4, 0),
          (1, 3), (2, 3), (3, 3)],
    'A': [(0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6),
          (1, 0), (2, 0), (3, 0),
          (4, 1), (4, 2), (4, 3), (4, 4), (4, 5), (4, 6),
          (1, 3), (2, 3), (3, 3)],
    'X': [(0, 0), (0, 1), (4, 0), (4, 1),
          (1, 2), (3, 2),
          (2, 3),
          (1, 4), (3, 4),
          (0, 5), (0, 6), (4, 5), (4, 6)],
    'M': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6),
          (1, 1), (2, 2), (3, 1),
          (4, 0), (4, 1), (4, 2), (4, 3), (4, 4), (4, 5), (4, 6)],
    'C': [(1, 0), (2, 0), (3, 0), (4, 0),
          (0, 1), (0, 2), (0, 3), (0, 4), (0, 5),
          (1, 6), (2, 6), (3, 6), (4, 6)],
    'H': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6),
          (1, 3), (2, 3), (3, 3),
          (4, 0), (4, 1), (4, 2), (4, 3), (4, 4), (4, 5), (4, 6)],
    'I': [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0),
          (2, 1), (2, 2), (2, 3), (2, 4), (2, 5),
          (0, 6), (1, 6), (2, 6), (3, 6), (4, 6)],
    'N': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6),
          (1, 1), (2, 2), (3, 3),
          (4, 0), (4, 1), (4, 2), (4, 3), (4, 4), (4, 5), (4, 6)],
    'E': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6),
          (1, 0), (2, 0), (3, 0), (4, 0),
          (1, 3), (2, 3), (3, 3),
          (1, 6), (2, 6), (3, 6), (4, 6)],
    ' ': [],
}


class OuterShell(Boxes):
    """Outer shell with internal vertical divider and horizontal shelf."""

    def __init__(self) -> None:
        Boxes.__init__(self)
        self.buildArgParser("x", "y", "h", "outside")
        self.addSettingsArgs(edges.FingerJointSettings)

    def draw_pixel_char(self, char: str, x: float, y: float, pixel_size: float) -> float:
        """Draw a single character using pixel font."""
        if char not in PIXEL_FONT:
            return pixel_size * 3
        pixels = PIXEL_FONT[char]
        if not pixels:
            return pixel_size * 3
        pixel_cell = pixel_size * 0.85
        for col, row in pixels:
            px = x + col * pixel_size + (pixel_size - pixel_cell) / 2
            py = y + (6 - row) * pixel_size + (pixel_size - pixel_cell) / 2
            self.ctx.move_to(px, py)
            self.ctx.line_to(px + pixel_cell, py)
            self.ctx.line_to(px + pixel_cell, py + pixel_cell)
            self.ctx.line_to(px, py + pixel_cell)
            self.ctx.line_to(px, py)
            self.ctx.stroke()
        return pixel_size * 5 + ENGRAVE_FONT_SPACING

    def draw_pixel_text(self, text: str, x: float, y: float, pixel_size: float = ENGRAVE_FONT_SIZE) -> None:
        """Draw text using pixel font with engraving color (red)."""
        self.set_source_color(ENGRAVE_COLOR)
        current_x = x
        for char in text.upper():
            width = self.draw_pixel_char(char, current_x, y, pixel_size)
            current_x += width

    def render(self) -> None:
        """Render all shell pieces."""
        x, y, h = self.x, self.y, self.h
        t = self.thickness

        if self.outside:
            x = self.adjustSize(x)
            y = self.adjustSize(y)
            h = self.adjustSize(h, False)

        self.x = x
        self.y = y
        self.h = h

        paper_depth = PAPER_COMPARTMENT_DEPTH
        drawer_bay_depth = y - paper_depth - t
        shelf_height = (h - t) / 2
        drawer_width = DRAWER["width"]
        drawer_height = DRAWER["height"]

        def add_left_lid_groove():
            groove_y = h - LID_GROOVE_DEPTH / 2
            self.rectangularHole(paper_depth / 2, groove_y, paper_depth - 2 * t, LID_GROOVE_WIDTH, r=0)

        self.rectangularWall(y, h, "FfFf", callback=[add_left_lid_groove, None, None, None], move="right", label="Left Wall")
        self.rectangularWall(y, h, "FfFf", move="up", label="Right Wall")

        def add_drawer_openings_and_engraving():
            opening_x = paper_depth + t + drawer_width / 2
            bottom_opening_y = t + drawer_height / 2
            self.rectangularHole(opening_x, bottom_opening_y, drawer_width, drawer_height, r=2)
            top_opening_y = t + shelf_height + t + drawer_height / 2
            self.rectangularHole(opening_x, top_opening_y, drawer_width, drawer_height, r=2)
            
            pixel_size = 3.0
            text = "FAX MACHINE"
            char_width = 5 * pixel_size + ENGRAVE_FONT_SPACING
            text_width = len(text) * char_width - ENGRAVE_FONT_SPACING
            text_height = 7 * pixel_size
            text_x = (x - text_width) / 2
            text_y = h - text_height - 12
            self.draw_pixel_text(text, text_x, text_y, pixel_size)

        self.rectangularWall(x, h, "FFFe", callback=[add_drawer_openings_and_engraving, None, None, None], label="Front Wall")
        self.rectangularWall(x, h, "FFFf", move="left", label="Back Wall")
        self.rectangularWall(x, y, "ffff", move="up", label="Bottom")

        def add_divider_features():
            slot_x = paper_depth + t + (drawer_bay_depth - t) / 2
            self.rectangularHole(slot_x, shelf_height, drawer_bay_depth - 2 * t, t, r=0)
            groove_y = h - LID_GROOVE_DEPTH / 2
            self.rectangularHole(paper_depth / 2, groove_y, paper_depth - 2 * t, LID_GROOVE_WIDTH, r=0)

        self.rectangularWall(y, h, "ffef", callback=[add_divider_features, None, None, None], move="right", label="Vertical Divider")
        shelf_width = x - paper_depth - t
        self.rectangularWall(shelf_width, drawer_bay_depth, "efef", move="up", label="Horizontal Shelf")


def generate_shell() -> Path:
    """Generate outer shell SVG file."""
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / "outer_shell.svg"

    shell = OuterShell()
    shell.parseArgs([
        "--output", str(output_file),
        "--thickness", str(DRAWER_MATERIAL_THICKNESS),
        "--burn", str(BURN),
        "--x", str(SHELL["width"]),
        "--y", str(SHELL["depth"]),
        "--h", str(SHELL["height"]),
        "--outside", "1",
    ])

    shell.open()
    shell.render()
    data = shell.close()

    with open(output_file, "wb") as f:
        f.write(data.getvalue())

    print(f"Generated outer shell SVG: {output_file.absolute()}")
    print(f"  External dimensions: {SHELL['width']}mm x {SHELL['depth']}mm x {SHELL['height']}mm")
    print(f"  Paper compartment depth: {PAPER_COMPARTMENT_DEPTH}mm")
    print(f"  Material thickness: {DRAWER_MATERIAL_THICKNESS}mm")
    return output_file


if __name__ == "__main__":
    generate_shell()
