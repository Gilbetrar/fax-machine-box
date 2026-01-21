"""Generate drawer boxes for the fax machine organizer."""

from pathlib import Path

from boxes import Boxes
from boxes import edges

from faxbox.config import (
    BURN,
    DRAWER,
    DRAWER_MATERIAL_THICKNESS,
    FINGER_NOTCH_RADIUS,
    OUTPUT_DIR,
)


class DrawerBox(Boxes):
    """Open-top drawer box with finger joints and front finger-notch pull."""

    def __init__(self) -> None:
        Boxes.__init__(self)
        self.buildArgParser("x", "y", "h", "outside")
        self.addSettingsArgs(edges.FingerJointSettings)

    def render(self) -> None:
        """Render all drawer pieces."""
        # Set default cut color to blue for Ponoko compatibility (#0000FF)
        self.set_source_color([0.0, 0.0, 1.0])

        x, y, h = self.x, self.y, self.h
        t = self.thickness

        if self.outside:
            x = self.adjustSize(x)
            y = self.adjustSize(y)
            h = self.adjustSize(h, False)

        # Store dimensions
        self.x = x
        self.y = y
        self.h = h

        # For an open-top drawer with finger joints:
        # - Front/Back walls (x, h): bottom=F, right=f, top=e, left=f
        # - Side walls (y, h): bottom=F, right=F, top=e, left=F
        # - Bottom (x, y): all finger holes (ffff)

        # Front wall with finger-notch cutout
        # Using callback to add the finger notch hole
        def add_finger_notch():
            """Add a finger-notch hole at the top center for easy grip."""
            notch_width = FINGER_NOTCH_RADIUS * 2
            notch_height = FINGER_NOTCH_RADIUS
            # Position so the top of the hole is near the top edge
            notch_y = h - notch_height / 2 - t  # Account for edge thickness
            self.rectangularHole(x / 2, notch_y, notch_width, notch_height, r=notch_height / 2)

        self.rectangularWall(
            x, h,
            "Ffef",  # bottom=F (to bottom), right=f, top=e (open), left=f
            callback=[add_finger_notch, None, None, None],
            move="right",
            label="Front"
        )

        # Back wall (same as front but no notch)
        self.rectangularWall(
            x, h,
            "Ffef",
            move="up",
            label="Back"
        )

        # Side walls
        self.rectangularWall(
            y, h,
            "FFeF",  # bottom=F, right=F, top=e (open), left=F
            label="Left Side"
        )

        self.rectangularWall(
            y, h,
            "FFeF",
            move="left",
            label="Right Side"
        )

        # Bottom
        self.rectangularWall(
            x, y,
            "ffff",  # all finger holes
            move="up",
            label="Bottom"
        )


def generate_drawer() -> Path:
    """Generate a drawer box SVG file.

    Returns:
        Path to the generated SVG file.
    """
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)

    output_file = output_path / "drawer.svg"

    drawer = DrawerBox()
    drawer.parseArgs([
        "--output", str(output_file),
        "--thickness", str(DRAWER_MATERIAL_THICKNESS),
        "--burn", str(BURN),
        "--x", str(DRAWER["width"]),
        "--y", str(DRAWER["depth"]),
        "--h", str(DRAWER["height"]),
        "--outside", "0",  # Use inside dimensions
    ])

    drawer.open()
    drawer.render()

    # Add finger notch hole to front wall
    # Position it centered on the top edge of the front panel
    # We need to use the hole feature of boxes.py
    # The front wall should have a semicircular cutout at the top center

    data = drawer.close()

    with open(output_file, "wb") as f:
        f.write(data.getvalue())

    print(f"Generated drawer SVG: {output_file.absolute()}")
    print(f"  Internal dimensions: {DRAWER['width']}mm × {DRAWER['depth']}mm × {DRAWER['height']}mm")
    print(f"  Material thickness: {DRAWER_MATERIAL_THICKNESS}mm")
    return output_file


if __name__ == "__main__":
    generate_drawer()
