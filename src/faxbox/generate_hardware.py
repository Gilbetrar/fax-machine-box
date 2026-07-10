"""Generate the lid-retention turn-button (DESIGN.md "Retention (iteration
2)" section B, issue #20 + adversarial-review REV.B): ONE rounded
paddle/stadium piece, pivoting on an M3 bolt through the FRONT WALL's
TURN_BUTTON_PIVOT_BOX_Y/Z hole (see shell_generator.py's front-wall callback
and config.py's TURN_BUTTON* constants). REV.A (2 buttons, one per side
wall) was proven geometrically incapable of retention -- see config.py's
"Lid retention (iteration 2 REV.B...)" comment for the disjoint-volume proof
-- and was replaced with this single front-wall button before any part was
cut.

Output: 1 piece in output/hardware.svg -- Turn Button. Standalone, like
calibration.py's coupons: NOT part of any sheet_*.svg / final_layout.svg
(see layout.py's module docstring: it only nests outer_shell.svg +
drawer.svg + lids.svg).

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

from faxbox import config
from faxbox.calibration import LABEL_GRAY
from faxbox.config import (
    FINGER_PLAY_RELATIVE,
    MATERIAL_THICKNESS,
    TURN_BUTTON,
)
from faxbox.svglabels import enforce_reference_labels

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

    def __init__(self, provider: str | None = None) -> None:
        Boxes.__init__(self)
        self.addSettingsArgs(edges.FingerJointSettings)
        # Provider abstraction (config.PROVIDERS) -- see shell_generator.py's
        # OuterShell.__init__ for the full rationale. Defaults to "nycr".
        provider_cfg = config.PROVIDERS[config.resolve_provider(provider)]
        self.cut_color = provider_cfg["cut_color"]

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
            # Reference-only label in gray, like the sheet labels layout.py
            # produces. move(label=...) would emit it engrave-red -- this is
            # a real visible part, and red text fill is a live laser
            # instruction (see LEARNINGS.md; layout.py recolors sheet labels
            # for the same reason, but hardware.svg bypasses layout.py).
            self.text(
                label, BUTTON_LENGTH / 2, BUTTON_WIDTH / 2,
                align="middle center", fontsize=3.0, color=LABEL_GRAY,
            )
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
        self.move(BUTTON_LENGTH, BUTTON_WIDTH, "right")

    def render(self) -> None:
        """Render the single button (REV.B: one front-wall button, not two
        side-wall ones -- see module docstring)."""
        self.set_source_color(self.cut_color)
        self._build_button("Turn Button")


def generate_hardware(provider: str | None = None) -> Path:
    """Generate the turn-button hardware SVG file.

    `provider` selects a faxbox.config.PROVIDERS entry (see
    shell_generator.generate_shell's docstring). Passing nothing reproduces
    the original output/hardware.svg exactly.

    Returns:
        Path to the generated SVG file.
    """
    name = config.resolve_provider(provider)
    provider_cfg = config.PROVIDERS[name]
    output_path = Path(provider_cfg["output_dir"])
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / "hardware.svg"

    hardware = TurnButton(provider=name)
    hardware.parseArgs([
        "--output", str(output_file),
        "--thickness", str(MATERIAL_THICKNESS),
        "--burn", str(provider_cfg["burn"]),
        "--reference", "0",
        "--FingerJoint_play", str(FINGER_PLAY_RELATIVE),
    ])

    hardware.open()
    hardware.render()
    data = hardware.close()

    with open(output_file, "wb") as f:
        f.write(data.getvalue())

    # This piece already draws its label in LABEL_GRAY directly (see
    # _build_button above), so this is a harmless no-op today -- run it
    # anyway for the same systemic guarantee every other standalone
    # generator gets (see faxbox.svglabels module docstring).
    enforce_reference_labels(output_file)

    print(f"Generated turn-button hardware SVG: {output_file.absolute()}")
    print(f"  1x Turn Button: {BUTTON_LENGTH}mm x {BUTTON_WIDTH}mm, pivot hole "
          f"Ø{PIVOT_HOLE_DIA}mm at {PIVOT_FROM_BLUNT_END}mm from the blunt end")
    print("  Hardware (not cut, buy separately): 1x M3x12 button-head bolt, "
          "1x M3 nyloc nut, 2x M3 washer.")
    return output_file


if __name__ == "__main__":
    generate_hardware()
