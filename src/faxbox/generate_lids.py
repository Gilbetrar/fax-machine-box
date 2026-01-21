"""Generate lids for the fax machine box.

Two lids:
1. Sliding lid for paper compartment - slides front-to-back in grooves
2. Flat tabbed lid for drawer bay - sits on top with alignment tabs
"""

from pathlib import Path

from boxes import Boxes
from boxes import edges

from faxbox.config import (
    BURN,
    DRAWER_MATERIAL_THICKNESS,
    LID_GROOVE_DEPTH,
    LID_GROOVE_WIDTH,
    OUTPUT_DIR,
    PAPER_COMPARTMENT_DEPTH,
    SHELL,
)


class LidGenerator(Boxes):
    """Generate sliding and flat lids for the fax machine box."""

    def __init__(self) -> None:
        Boxes.__init__(self)
        self.buildArgParser("outside")
        self.addSettingsArgs(edges.FingerJointSettings)

    def render(self) -> None:
        """Render both lid pieces."""
        # Set default cut color to blue for Ponoko compatibility (#0000FF)
        self.set_source_color([0.0, 0.0, 1.0])

        t = self.thickness

        # Calculate internal dimensions from external shell
        internal_width = SHELL["width"] - 2 * t
        internal_depth = SHELL["depth"] - 2 * t

        # Paper compartment dimensions
        paper_width = PAPER_COMPARTMENT_DEPTH - t  # Account for divider

        # Drawer bay dimensions
        drawer_bay_width = internal_width - paper_width - t

        # === SLIDING LID (Paper Compartment) ===
        # Slides front-to-back in grooves on side walls
        # Width: paper compartment width minus clearance for groove fit
        # Depth: full internal depth to slide through

        # Lid tabs fit in grooves: width = LID_GROOVE_WIDTH with clearance
        lid_clearance = 0.5  # mm clearance for smooth sliding
        sliding_lid_width = paper_width - lid_clearance
        sliding_lid_depth = internal_depth - lid_clearance

        # Tab dimensions (extend into grooves)
        tab_depth = LID_GROOVE_DEPTH - 1  # Slightly less than groove depth

        def add_sliding_lid_tabs():
            """Add tabs on left and right edges for groove engagement."""
            # Left tab (rectangular extension)
            self.rectangularHole(
                -tab_depth / 2,  # Extends past left edge
                sliding_lid_depth / 2,  # Center along depth
                tab_depth,
                sliding_lid_depth - 2 * t,  # Leave clearance at ends
                r=0
            )
            # Right tab
            self.rectangularHole(
                sliding_lid_width + tab_depth / 2,  # Extends past right edge
                sliding_lid_depth / 2,
                tab_depth,
                sliding_lid_depth - 2 * t,
                r=0
            )

        # Main sliding lid panel
        self.rectangularWall(
            sliding_lid_width,
            sliding_lid_depth,
            "eeee",  # Plain edges - tabs added separately
            move="right",
            label="Sliding Lid (Paper)"
        )

        # Add separate tab pieces that attach to sliding lid edges
        # Left tab strip
        self.rectangularWall(
            tab_depth,
            sliding_lid_depth - 4 * t,  # Slightly shorter to clear ends
            "eeee",
            move="right",
            label="Sliding Lid - Left Tab"
        )

        # Right tab strip
        self.rectangularWall(
            tab_depth,
            sliding_lid_depth - 4 * t,
            "eeee",
            move="up",
            label="Sliding Lid - Right Tab"
        )

        # === FLAT TABBED LID (Drawer Bay) ===
        # Sits on top of drawer bay, tabs slot into wall tops
        flat_lid_width = drawer_bay_width - lid_clearance
        flat_lid_depth = internal_depth - lid_clearance

        # Alignment tabs on underside (small rectangles at edges)
        tab_size = t  # Tabs are material-thickness sized
        tab_inset = 10  # mm from corners

        def add_alignment_tab_holes():
            """Add holes to show where alignment tabs should be glued."""
            # Corner alignment tabs (4 total)
            corners = [
                (tab_inset, tab_inset),  # Front-left
                (flat_lid_width - tab_inset, tab_inset),  # Front-right
                (tab_inset, flat_lid_depth - tab_inset),  # Back-left
                (flat_lid_width - tab_inset, flat_lid_depth - tab_inset),  # Back-right
            ]
            for cx, cy in corners:
                # Small square marks for tab placement
                self.rectangularHole(cx, cy, tab_size * 2, tab_size * 2, r=0)

        self.rectangularWall(
            flat_lid_width,
            flat_lid_depth,
            "eeee",
            callback=[add_alignment_tab_holes, None, None, None],
            move="right",
            label="Flat Lid (Drawer Bay)"
        )

        # Alignment tabs (small squares to glue under lid)
        for i in range(4):
            self.rectangularWall(
                tab_size * 2,
                tab_size * 2,
                "eeee",
                move="right" if i < 3 else "up",
                label=f"Alignment Tab {i + 1}"
            )


def generate_lids() -> Path:
    """Generate lids SVG file.

    Returns:
        Path to the generated SVG file.
    """
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)

    output_file = output_path / "lids.svg"

    lids = LidGenerator()
    lids.parseArgs([
        "--output", str(output_file),
        "--thickness", str(DRAWER_MATERIAL_THICKNESS),
        "--burn", str(BURN),
    ])

    lids.open()
    lids.render()
    data = lids.close()

    with open(output_file, "wb") as f:
        f.write(data.getvalue())

    # Calculate dimensions for output
    t = DRAWER_MATERIAL_THICKNESS
    internal_width = SHELL["width"] - 2 * t
    internal_depth = SHELL["depth"] - 2 * t
    paper_width = PAPER_COMPARTMENT_DEPTH - t
    drawer_bay_width = internal_width - paper_width - t

    print(f"Generated lids SVG: {output_file.absolute()}")
    print(f"  Sliding lid (paper): ~{paper_width:.1f}mm x {internal_depth:.1f}mm")
    print(f"  Flat lid (drawer bay): ~{drawer_bay_width:.1f}mm x {internal_depth:.1f}mm")
    print(f"  Groove width: {LID_GROOVE_WIDTH}mm, depth: {LID_GROOVE_DEPTH}mm")
    print(f"  Material thickness: {DRAWER_MATERIAL_THICKNESS}mm")
    return output_file


if __name__ == "__main__":
    generate_lids()
