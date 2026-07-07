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
    FINGER_PLAY,
    BURN,
    CUT_COLOR,
    LID_GRIP_SLOT,
    MATERIAL_THICKNESS,
    OUTPUT_DIR,
    SLIDING_LID,
)


class LidGenerator(Boxes):
    """Generate the sliding lid panel for the fax machine box."""

    def __init__(self) -> None:
        Boxes.__init__(self)
        self.addSettingsArgs(edges.FingerJointSettings)

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
        "--FingerJoint_play", str(FINGER_PLAY),
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
