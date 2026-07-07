"""Generate the lid-retention turn-buttons (DESIGN.md "Retention (iteration
2)", issue #20): 2 identical rounded paddle/stadium pieces, one per side
wall, each pivoting on an M3 bolt through the wall's TURN_BUTTON_PIVOT_X/Z
hole (see shell_generator.py's side-wall callback and config.py's
TURN_BUTTON* constants). Both walls use the same physical button -- the
paddle is symmetric about its own long axis, so no left/right mirroring is
needed (unlike the side walls themselves).

Output: 2 pieces in output/hardware.svg -- Turn Button 1, Turn Button 2.
Standalone, like calibration.py's coupons: NOT part of any sheet_*.svg /
final_layout.svg (see layout.py's module docstring: it only nests
outer_shell.svg + drawer.svg + lids.svg).

Shape: a "stadium" (rectangle with full semicircular caps at both ends,
radius = width/2) -- a simple, robust paddle shape built from Boxes.py's own
burn-aware `polyline`/`corner` primitives (the same primitives
`rectangularWall` itself is built from), so the cut piece is properly
kerf-compensated like every other real part in this project -- unlike the
raw/burn-neutral calibration coupons, this IS a functional hardware part.
The pivot hole sits at the blunt end's own cap center (pivot_from_blunt_end
== width / 2, config.py), which is why the blunt-end cap radius doubles as
that offset.
"""

from pathlib import Path

from boxes import Boxes
from boxes import edges

from faxbox.config import (
    FINGER_PLAY_RELATIVE,
    BURN,
    CUT_COLOR,
    MATERIAL_THICKNESS,
    OUTPUT_DIR,
    TURN_BUTTON,
)

BUTTON_LENGTH = TURN_BUTTON["length"]
BUTTON_WIDTH = TURN_BUTTON["width"]
PIVOT_FROM_BLUNT_END = TURN_BUTTON["pivot_from_blunt_end"]
PIVOT_HOLE_DIA = TURN_BUTTON["pivot_hole_dia"]

# The stadium's end-cap radius equals half the paddle's width (a full
# semicircle cap at each end); the pivot hole is positioned at that same
# offset from the blunt end, since it's drawn centered in the blunt cap.
CAP_RADIUS = BUTTON_WIDTH / 2
assert abs(CAP_RADIUS - PIVOT_FROM_BLUNT_END) < 1e-9, (
    "TURN_BUTTON: pivot_from_blunt_end must equal width/2 for the pivot to "
    "sit at the blunt end's own cap center"
)


class TurnButton(Boxes):
    """One rounded paddle/stadium turn-button, pivot hole in the blunt end."""

    def __init__(self) -> None:
        Boxes.__init__(self)
        self.addSettingsArgs(edges.FingerJointSettings)

    def _build_button(self, label: str) -> None:
        """Draw one button: pivot hole first (in the pristine, untranslated
        frame -- see module note below), THEN the stadium outline via
        moveTo + polyline, so the hole lands at true local (CAP_RADIUS,
        CAP_RADIUS) rather than being offset by the outline's own starting
        moveTo (Boxes.py's cursor-based drawing model carries the current
        position/rotation forward across calls; calling hole() before any
        moveTo keeps it anchored to this piece's own origin)."""

        def callback() -> None:
            self.hole(CAP_RADIUS, CAP_RADIUS, d=PIVOT_HOLE_DIA)
            straight = BUTTON_LENGTH - 2 * CAP_RADIUS
            self.moveTo(CAP_RADIUS, 0, 0)
            self.polyline(straight, (180, CAP_RADIUS), straight, (180, CAP_RADIUS))
            self.ctx.stroke()

        # A bare custom shape (not rectangularWall) still needs to
        # participate in the move= layout protocol so pieces don't overlap;
        # self.move() is the same helper rectangularWall calls internally.
        if self.move(BUTTON_LENGTH, BUTTON_WIDTH, "right", before=True):
            return
        callback()
        self.move(BUTTON_LENGTH, BUTTON_WIDTH, "right", label=label)

    def render(self) -> None:
        """Render both identical buttons, laid out left to right."""
        self.set_source_color(CUT_COLOR)
        self._build_button("Turn Button 1")
        self._build_button("Turn Button 2")


def generate_hardware() -> Path:
    """Generate the turn-button hardware SVG file.

    Returns:
        Path to the generated SVG file.
    """
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / "hardware.svg"

    hardware = TurnButton()
    hardware.parseArgs([
        "--output", str(output_file),
        "--thickness", str(MATERIAL_THICKNESS),
        "--burn", str(BURN),
        "--reference", "0",
        "--FingerJoint_play", str(FINGER_PLAY_RELATIVE),
    ])

    hardware.open()
    hardware.render()
    data = hardware.close()

    with open(output_file, "wb") as f:
        f.write(data.getvalue())

    print(f"Generated turn-button hardware SVG: {output_file.absolute()}")
    print(f"  2x Turn Button: {BUTTON_LENGTH}mm x {BUTTON_WIDTH}mm, pivot hole "
          f"Ø{PIVOT_HOLE_DIA}mm at {PIVOT_FROM_BLUNT_END}mm from the blunt end")
    print("  Hardware per button (not cut, buy separately): 1x M3x12 button-head bolt, "
          "1x M3 nyloc nut, 2x M3 washer.")
    return output_file


if __name__ == "__main__":
    generate_hardware()
