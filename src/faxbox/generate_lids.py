"""Generate the sliding lid for the fax machine box.

DESIGN.md #8: a single flat panel that rides in the through-slots cut into
both side walls (see shell_generator.py), inserted from the front over the
front wall's top edge. The old flat/tabbed drawer-bay lid is gone -- that bay
is now covered by the fixed Top Panel built in shell_generator.py
(DESIGN.md's "Decisions" section: "Fixed top panel over the drawer bay (not
a removable lid)").

Output: 1 piece in output/lids.svg -- Sliding Lid.
"""

from pathlib import Path

from boxes import Boxes
from boxes import edges

from faxbox.config import (
    FINGER_PLAY_RELATIVE,
    BURN,
    CUT_COLOR,
    LID_GRIP_SLOT,
    LID_NOTCH_CHAMFER,
    LID_NOTCH_DEPTH,
    LID_NOTCH_WIDTH,
    LID_NOTCH_X,
    MATERIAL_THICKNESS,
    OUTPUT_DIR,
    SLIDING_LID,
)
from faxbox.detent import notch_points


class LidGenerator(Boxes):
    """Generate the sliding lid panel for the fax machine box."""

    def __init__(self) -> None:
        Boxes.__init__(self)
        self.addSettingsArgs(edges.FingerJointSettings)

    def _draw_closed_polygon(self, points: list[tuple[float, float]]) -> None:
        """Stroke a closed polygon -- see faxbox.detent module docstring for
        why this is burn-neutral raw ctx, matching the wall nub/notch
        convention (shell_generator.py's _draw_closed_polygon, duplicated
        here rather than shared since Boxes.py generators are independent
        Boxes subclasses with no common base to hang a mixin off cleanly)."""
        self.ctx.move_to(*points[0])
        for pt in points[1:]:
            self.ctx.line_to(*pt)
        self.ctx.line_to(*points[0])
        self.ctx.stroke()

    def render(self) -> None:
        """Render the sliding lid piece."""
        self.set_source_color(CUT_COLOR)

        length = SLIDING_LID["length"]
        width = SLIDING_LID["width"]

        def add_grip_slot() -> None:
            slot = LID_GRIP_SLOT
            self.rectangularHole(
                slot["center_from_front"], width / 2,
                slot["width"], slot["height"], r=slot["radius"],
            )
            # Mating notches for the side-wall lid detent nubs (retention
            # iteration 2, issue #20): edge-open recesses on BOTH long
            # edges, at the X position that aligns with each wall's nub
            # when the lid is closed (DESIGN.md "Retention (iteration 2)").
            # Edge-open the same way the wall's lid-slot mouth is: the
            # polygon's own edge-level boundary coincides with the lid's
            # real edge, so both lines get cut and the notch opens through.
            bottom_edge = notch_points(
                center=LID_NOTCH_X, width=LID_NOTCH_WIDTH, depth=LID_NOTCH_DEPTH,
                chamfer=LID_NOTCH_CHAMFER, edge_level=0.0, inward_sign=1.0,
                burn=self.burn,
            )
            self._draw_closed_polygon(bottom_edge)
            top_edge = notch_points(
                center=LID_NOTCH_X, width=LID_NOTCH_WIDTH, depth=LID_NOTCH_DEPTH,
                chamfer=LID_NOTCH_CHAMFER, edge_level=width, inward_sign=-1.0,
                burn=self.burn,
            )
            self._draw_closed_polygon(top_edge)

        self.rectangularWall(
            length, width, "eeee",
            callback=[add_grip_slot, None, None, None],
            move="right", label="Sliding Lid",
        )


def generate_lids() -> Path:
    """Generate the lids SVG file.

    Returns:
        Path to the generated SVG file.
    """
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)

    output_file = output_path / "lids.svg"

    lids = LidGenerator()
    lids.parseArgs([
        "--output", str(output_file),
        "--thickness", str(MATERIAL_THICKNESS),
        "--burn", str(BURN),
        "--reference", "0",
        "--FingerJoint_play", str(FINGER_PLAY_RELATIVE),
    ])

    lids.open()
    lids.render()
    data = lids.close()

    with open(output_file, "wb") as f:
        f.write(data.getvalue())

    print(f"Generated lids SVG: {output_file.absolute()}")
    print(f"  Sliding lid: {SLIDING_LID['length']}mm x {SLIDING_LID['width']}mm")
    print(f"  Material thickness: {MATERIAL_THICKNESS}mm")
    return output_file


if __name__ == "__main__":
    generate_lids()
