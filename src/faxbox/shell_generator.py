"""Generate outer shell for fax machine box with internal dividers."""

from pathlib import Path

from boxes import Boxes
from boxes import edges

from faxbox.config import (
    BURN,
    DRAWER,
    DRAWER_MATERIAL_THICKNESS,
    LID_GROOVE_DEPTH,
    LID_GROOVE_WIDTH,
    OUTPUT_DIR,
    PAPER_COMPARTMENT_DEPTH,
    SHELL,
)


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

        # Front wall - with two drawer openings
        def add_drawer_openings():
            """Cut openings for two drawers."""
            # Position from right edge where drawers go
            # Drawers are in the drawer bay (past paper compartment)
            # Front wall is x wide, drawer bay starts at paper_depth + t from left

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

        self.rectangularWall(
            x, h,
            "FFFe",  # finger joints except top (for potential lid overlap)
            callback=[add_drawer_openings, None, None, None],
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
        # Needs slots for horizontal shelf

        def add_shelf_slot():
            """Add slot for horizontal shelf."""
            # Slot at shelf height, spanning drawer bay side
            slot_x = paper_depth + t + (drawer_bay_depth - t) / 2
            self.rectangularHole(
                slot_x, shelf_height,
                drawer_bay_depth - 2 * t, t,
                r=0
            )

        self.rectangularWall(
            y, h,
            "ffef",  # bottom and sides finger holes, top plain
            callback=[add_shelf_slot, None, None, None],
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
    print(f"  External dimensions: {SHELL['width']}mm × {SHELL['depth']}mm × {SHELL['height']}mm")
    print(f"  Paper compartment depth: {PAPER_COMPARTMENT_DEPTH}mm")
    print(f"  Material thickness: {DRAWER_MATERIAL_THICKNESS}mm")
    return output_file


if __name__ == "__main__":
    generate_shell()
