"""Generate outer shell for fax machine box with internal dividers."""

from pathlib import Path

from boxes import Boxes
from boxes import edges

from faxbox.config import (
    BURN,
    DRAWER,
    DRAWER_MATERIAL_THICKNESS,
    ENGRAVE_COLOR,
    ENGRAVE_FONT_SPACING,
    LID_GROOVE_DEPTH,
    LID_GROOVE_WIDTH,
    OUTPUT_DIR,
    PAPER_COMPARTMENT_DEPTH,
    SHELL,
)


# Pixel font definitions: 5 columns x 7 rows
# Each letter is defined as (col, row) coordinates where pixels are filled
# Row 0 is top of character, row 6 is bottom
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
    ' ': [],  # Space - no pixels
}


class OuterShell(Boxes):
    """Outer shell with internal vertical divider and horizontal shelf.

    Layout (top view):
    +---+---------------------------+
    | P |                           |
    | A |      Drawer Bay           |
    | P |      (2 slots)            |
    | E |                           |
    | R |                           |
    +---+---------------------------+
      3"          ~9"

    Paper compartment has sliding lid (grooves on side walls).
    Drawer bay is divided by horizontal shelf into two drawer slots.
    """

    def __init__(self) -> None:
        Boxes.__init__(self)
        self.buildArgParser("x", "y", "h", "outside")
        self.addSettingsArgs(edges.FingerJointSettings)

    def draw_pixel_char(self, char: str, x: float, y: float,
                        pixel_size: float) -> float:
        """Draw a single character using pixel font.

        Args:
            char: Character to draw
            x: X position (left edge)
            y: Y position (bottom edge)
            pixel_size: Size of each pixel cell in mm

        Returns:
            Width of the character drawn (for spacing next character)
        """
        if char not in PIXEL_FONT:
            return pixel_size * 3  # Default space for unknown chars

        pixels = PIXEL_FONT[char]
        if not pixels:
            return pixel_size * 3  # Space character width

        # Draw each pixel as a stroked rectangle outline
        pixel_cell = pixel_size * 0.85  # Pixel size with small gap
        for col, row in pixels:
            # Flip y so row 0 is at top (y increases downward in pixel coords)
            px = x + col * pixel_size + (pixel_size - pixel_cell) / 2
            py = y + (6 - row) * pixel_size + (pixel_size - pixel_cell) / 2

            # Draw pixel as a rectangle outline using Cairo context
            self.ctx.move_to(px, py)
            self.ctx.line_to(px + pixel_cell, py)
            self.ctx.line_to(px + pixel_cell, py + pixel_cell)
            self.ctx.line_to(px, py + pixel_cell)
            self.ctx.line_to(px, py)
            self.ctx.stroke()

        return pixel_size * 5 + ENGRAVE_FONT_SPACING  # 5 columns + spacing

    def draw_pixel_text(self, text: str, x: float, y: float,
                        pixel_size: float) -> None:
        """Draw text using pixel font with engraving color.

        Args:
            text: Text to draw
            x: X position (left edge)
            y: Y position (bottom edge)
            pixel_size: Size of each pixel cell in mm
        """
        # Set engrave color (red for Ponoko)
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

        # Store adjusted dimensions
        self.x = x
        self.y = y
        self.h = h

        # Calculate internal dimensions
        paper_depth = PAPER_COMPARTMENT_DEPTH
        drawer_bay_depth = y - paper_depth - t  # Account for divider

        # Shelf position: center of drawer bay height
        # Leave room for material thickness at bottom
        shelf_height = (h - t) / 2  # Center point

        # Drawer opening dimensions (match drawer dimensions with clearance)
        drawer_width = DRAWER["width"]
        drawer_height = DRAWER["height"]

        # === OUTER WALLS ===

        # Left wall (paper compartment side with lid groove)
        # Needs groove at top for sliding lid
        def add_left_lid_groove():
            """Add groove for sliding lid on paper compartment."""
            groove_y = h - LID_GROOVE_DEPTH / 2
            # Groove spans paper compartment depth
            self.rectangularHole(
                paper_depth / 2, groove_y,
                paper_depth - 2 * t, LID_GROOVE_WIDTH,
                r=0
            )

        self.rectangularWall(
            y, h,
            "FfFf",  # finger joints all around
            callback=[add_left_lid_groove, None, None, None],
            move="right",
            label="Left Wall"
        )

        # Right wall (drawer bay side, no lid groove)
        self.rectangularWall(
            y, h,
            "FfFf",
            move="up",
            label="Right Wall"
        )

        # Front wall - with drawer openings and "FAX MACHINE" engraving
        def add_drawer_openings_and_engraving():
            """Cut drawer openings and add FAX MACHINE engraving."""
            # Opening horizontal center: in the drawer bay
            opening_x = paper_depth + t + drawer_width / 2

            # Bottom drawer opening
            bottom_opening_y = t + drawer_height / 2
            self.rectangularHole(
                opening_x, bottom_opening_y,
                drawer_width, drawer_height,
                r=2
            )

            # Top drawer opening
            top_opening_y = t + shelf_height + t + drawer_height / 2
            self.rectangularHole(
                opening_x, top_opening_y,
                drawer_width, drawer_height,
                r=2
            )

            # Add "FAX MACHINE" engraving across the top of front wall
            # Uses pixel font for retro aesthetic, rendered as paths (not text)
            pixel_size = 3.0  # 3mm per pixel cell
            text = "FAX MACHINE"
            # Calculate text dimensions: 11 chars, each 5 pixels wide + spacing
            char_width = 5 * pixel_size + ENGRAVE_FONT_SPACING
            text_width = len(text) * char_width - ENGRAVE_FONT_SPACING
            text_height = 7 * pixel_size  # 7 pixel rows

            # Center text horizontally on front wall
            text_x = (x - text_width) / 2
            # Position near top, leaving margin below top edge
            text_y = h - text_height - 12

            self.draw_pixel_text(text, text_x, text_y, pixel_size)

        self.rectangularWall(
            x, h,
            "FFFe",  # finger joints except top (for potential lid overlap)
            callback=[add_drawer_openings_and_engraving, None, None, None],
            label="Front Wall"
        )

        self.rectangularWall(
            x, h,
            "FFFf",  # back wall, all finger joints
            move="left",
            label="Back Wall"
        )

        # === BOTTOM ===
        self.rectangularWall(
            x, y,
            "ffff",  # all finger holes
            move="up",
            label="Bottom"
        )

        # === INTERNAL DIVIDER ===
        # Vertical divider separating paper compartment from drawer bay
        # Height = full height, depth = full depth (y)
        # Needs slots for horizontal shelf and lid groove for paper compartment

        def add_divider_features():
            """Add shelf slot and lid groove to vertical divider."""
            # Shelf slot at shelf height, spanning drawer bay side
            slot_x = paper_depth + t + (drawer_bay_depth - t) / 2
            self.rectangularHole(
                slot_x, shelf_height,
                drawer_bay_depth - 2 * t, t,
                r=0
            )
            # Lid groove matching left wall (for sliding lid)
            groove_y = h - LID_GROOVE_DEPTH / 2
            self.rectangularHole(
                paper_depth / 2, groove_y,
                paper_depth - 2 * t, LID_GROOVE_WIDTH,
                r=0
            )

        self.rectangularWall(
            y, h,
            "ffef",  # bottom and sides finger holes, top plain
            callback=[add_divider_features, None, None, None],
            move="right",
            label="Vertical Divider"
        )

        # === HORIZONTAL SHELF ===
        # Divides drawer bay into two compartments
        # Width = drawer bay width (x - paper_depth - t for divider)
        # Depth = drawer bay depth (y - paper_depth - t)

        shelf_width = x - paper_depth - t
        self.rectangularWall(
            shelf_width, drawer_bay_depth,
            "efef",  # plain edges (just rests in slots)
            move="up",
            label="Horizontal Shelf"
        )


def generate_shell() -> Path:
    """Generate outer shell SVG file.

    Returns:
        Path to the generated SVG file.
    """
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
        "--outside", "1",  # Use outside dimensions
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
