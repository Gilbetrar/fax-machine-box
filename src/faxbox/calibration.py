"""Generate calibration coupons (red-team finding: DESIGN.md and config.py
specify BURN=0.08 and FINGER_PLAY=0.1 as *starting* values that must be
"calibrate[d] with a test cut before the real run" -- but no such test cut
existed anywhere in this project, so the first real sheet would have been the
first data point).

Output: output/kerf_coupon.svg (kerf/ply-thickness coupon, below) and
output/magnet_coupon.svg (iteration-2 magnet press-fit coupon, see
generate_magnet_coupon()) -- both single small standalone panels, NOT part of
any sheet_*.svg / final_layout.svg (see layout.py's module docstring: it only
nests outer_shell.svg + drawer.svg + lids.svg). Cut kerf_coupon.svg on scrap
BEFORE the real sheets, then:

  1. Try to press a scrap of the actual plywood stock into each of the three
     slots. Whichever slot it seats into snugly (not loose, not forced) says
     how thick your stock is actually measuring -- use that to sanity-check
     MATERIAL_THICKNESS / FINGER_PLAY in config.py before cutting joints.
  2. Measure the square hole with calipers. Its tool path is drawn at exactly
     10.0mm x 10.0mm (burn compensation cancelled for this one feature), so
     the physical hole measures 10.0 + 2x(real per-side kerf). Set
     BURN = (measured - 10.0) / 2, then regenerate and re-cut the coupon:
     the thickness slots only read true once BURN matches the real kerf.

All cut lines are CUT_COLOR (blue) -- nothing on either coupon is engraved.
"""

from pathlib import Path
import math

from boxes import Boxes
from boxes import edges

from faxbox.config import (
    FINGER_PLAY_RELATIVE,
    BURN,
    CUT_COLOR,
    MAGNET_DIA,
    MAGNET_PRESS_FIT,
    MATERIAL_THICKNESS,
    OUTPUT_DIR,
)

# Reference-only label color (see LEARNINGS.md: "<text> fill color is a real
# laser instruction -- reference-only labels must use a color the cut/engrave
# driver is told to ignore, never the engrave color"). Same gray layout.py
# recolors part-name labels to (rgb(128,128,128)).
LABEL_GRAY = [128 / 255, 128 / 255, 128 / 255]

# --- Coupon geometry ---------------------------------------------------------

COUPON_WIDTH = 90.0   # X
COUPON_HEIGHT = 25.0  # Y

# Three "which slot does my ply fit snugly" through-slots, narrowest to
# widest, straddling the nominal material thickness (config.MATERIAL_THICKNESS
# = 3.175mm) since nominal 1/8" ply commonly measures 3.0-3.4mm in practice
# (see DESIGN.md's kerf/play note).
SLOT_WIDTHS = (3.05, MATERIAL_THICKNESS, 3.30)
SLOT_HEIGHT = 15.0
SLOT_LABELS = ("undersize (3.05mm)", "nominal (3.175mm = T)", "oversize (3.30mm)")

# Kerf-calibration through-hole: the TOOL PATH must be exactly 10.0mm square
# for the measurement to mean anything, so it is drawn with raw ctx line
# segments (which Boxes.py never burn-compensates -- same mechanism as the
# pixel-font engraving) instead of rectangularHole (whose drawn size shifts
# with the current BURN). Drawn at 10.0 exactly, the physical hole measures
# 10.0 + 2*(real per-side kerf): set BURN to (measured - 10.0) / 2. A
# burn-compensated square would instead measure the kerf *error* relative to
# the current BURN, and a perfectly calibrated laser would read "kerf = 0" --
# a trap that zeroes out BURN (red-team pass-2 catch).
KERF_HOLE_SIZE = 10.0

# Even spacing across COUPON_WIDTH for the 3 slots + 1 hole (4 items -> 5
# gaps: left margin, 3 inter-item gaps, right margin), comfortably over the
# >=6mm-apart requirement.
_ITEM_WIDTHS = list(SLOT_WIDTHS) + [KERF_HOLE_SIZE]
_GAP = (COUPON_WIDTH - sum(_ITEM_WIDTHS)) / (len(_ITEM_WIDTHS) + 1)

CENTER_Y = COUPON_HEIGHT / 2


def _item_centers() -> list[float]:
    """X centers, left to right, for the 3 slots then the kerf hole."""
    centers = []
    cursor = _GAP
    for w in _ITEM_WIDTHS:
        centers.append(cursor + w / 2)
        cursor += w + _GAP
    return centers


class CalibrationCoupon(Boxes):
    """A single small standalone panel: 3 fit-test slots + 1 kerf-test hole."""

    def __init__(self) -> None:
        Boxes.__init__(self)
        self.addSettingsArgs(edges.FingerJointSettings)

    def render(self) -> None:
        """Render the coupon: a plain-edged blank with the 3 slots and 1
        square hole cut through it (all CUT_COLOR)."""
        self.set_source_color(CUT_COLOR)

        centers = _item_centers()
        slot_centers, hole_center = centers[:3], centers[3]

        def callback() -> None:
            for cx, width in zip(slot_centers, SLOT_WIDTHS):
                self.rectangularHole(cx, CENTER_Y, width, SLOT_HEIGHT, r=0)
            # Raw ctx path: exact 10.0mm tool path, immune to burn compensation.
            half = KERF_HOLE_SIZE / 2
            x0, y0 = hole_center - half, CENTER_Y - half
            x1, y1 = hole_center + half, CENTER_Y + half
            self.ctx.move_to(x0, y0)
            self.ctx.line_to(x1, y0)
            self.ctx.line_to(x1, y1)
            self.ctx.line_to(x0, y1)
            self.ctx.line_to(x0, y0)
            self.ctx.stroke()

        self.rectangularWall(
            COUPON_WIDTH, COUPON_HEIGHT, "eeee",
            callback=[callback, None, None, None],
            move="right", label="Kerf Coupon",
        )


def generate_calibration() -> Path:
    """Generate the kerf/fit calibration coupon SVG file.

    Returns:
        Path to the generated SVG file.
    """
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / "kerf_coupon.svg"

    coupon = CalibrationCoupon()
    coupon.parseArgs([
        "--output", str(output_file),
        "--thickness", str(MATERIAL_THICKNESS),
        "--burn", str(BURN),
        "--reference", "0",
        "--FingerJoint_play", str(FINGER_PLAY_RELATIVE),
    ])

    coupon.open()
    coupon.render()
    data = coupon.close()

    with open(output_file, "wb") as f:
        f.write(data.getvalue())

    print(f"Generated kerf/fit calibration coupon SVG: {output_file.absolute()}")
    print(f"  Coupon blank: {COUPON_WIDTH}mm x {COUPON_HEIGHT}mm")
    print("  Cut this alone on scrap BEFORE the real sheets. Slots (left to right):")
    for label, width in zip(SLOT_LABELS, SLOT_WIDTHS):
        print(f"    - {width:.3f}mm slot: {label} -- press a scrap of the actual ply into all")
        print("      three; whichever it seats into snugly tells you the real stock thickness.")
    print(
        f"  Square hole: tool path exactly {KERF_HOLE_SIZE:.1f}mm x {KERF_HOLE_SIZE:.1f}mm "
        "(burn-neutral). Measure the physical hole with calipers: "
        "set BURN = (measured - 10.0) / 2 in config.py."
    )
    print(
        "  If you change BURN (or FINGER_PLAY), regenerate and RE-CUT this coupon "
        "before trusting the thickness slots -- their physical widths are only "
        "accurate once BURN matches the real kerf."
    )
    return output_file


# =============================================================================
# Magnet press-fit coupon (iteration 2, issue #20)
# =============================================================================
# DESIGN.md "Retention (iteration 2)": MAGNET_PRESS_FIT (config.py) is a
# starting guess, same status as BURN/FINGER_PLAY -- it needs a real-magnet
# test cut before it's trusted for the drawer/divider retention holes.
#
# Unlike the drawer/divider holes (self.hole(), burn-compensated like every
# other DESIGN.md hole -- see config.py's "Drawer retention" section for why
# that's the right call there), these 4 gauge holes are drawn RAW (immune to
# burn compensation, same technique as the kerf square above: plain ctx
# move_to/line_to segments, approximating a circle with a many-sided polygon
# since Boxes.py's own arc() primitive divides by zero for closed sweeps).
# That is deliberate: the point of this coupon is to let Ben find the
# snuggest-fitting DRAWN diameter directly against a real magnet on real
# scrap, in one physical test that already bakes in the real kerf --
# whatever the actual kerf turns out to be. A burn-compensated hole here
# would only tell him how close the *current, unvalidated* BURN guess is to
# reality, which is exactly the self-defeating trap the kerf square's own
# burn-neutral design already avoids (see its comment above).
MAGNET_COUPON_WIDTH = 70.0   # X
MAGNET_COUPON_HEIGHT = 28.0  # Y

# 4 drawn (burn-neutral) diameters spanning the current MAGNET_HOLE_DIA
# guess (config.py: MAGNET_DIA - MAGNET_PRESS_FIT = 6.0 - 0.35 = 5.65) so the
# snuggest-fitting slot can land on either side of today's guess.
MAGNET_COUPON_DIAMETERS = (5.5, 5.65, 5.8, 5.95)

_MAGNET_GAP = (
    MAGNET_COUPON_WIDTH - sum(MAGNET_COUPON_DIAMETERS)
) / (len(MAGNET_COUPON_DIAMETERS) + 1)

MAGNET_HOLE_ROW_Y = MAGNET_COUPON_HEIGHT - 14.0   # leaves room for labels below
MAGNET_LABEL_Y = 4.0                               # from the panel's bottom edge


def _magnet_hole_centers() -> list[float]:
    """X centers, left to right, for the 4 magnet-fit gauge holes."""
    centers = []
    cursor = _MAGNET_GAP
    for d in MAGNET_COUPON_DIAMETERS:
        centers.append(cursor + d / 2)
        cursor += d + _MAGNET_GAP
    return centers


def _draw_raw_circle(boxes_obj: Boxes, cx: float, cy: float, d: float, n: int = 64) -> None:
    """A closed circular path built from raw ctx line segments (immune to
    burn compensation -- see module comment above). `n` segments is smooth
    enough that the polygon's own faceting error is negligible next to the
    0.1mm measurement tolerance these coupons are read to."""
    r = d / 2
    ctx = boxes_obj.ctx
    ctx.move_to(cx + r, cy)
    for i in range(1, n + 1):
        angle = 2 * math.pi * i / n
        ctx.line_to(cx + r * math.cos(angle), cy + r * math.sin(angle))
    ctx.stroke()


class MagnetFitCoupon(Boxes):
    """A single small standalone panel: 4 raw-diameter magnet press-fit
    gauge holes, each labeled in gray reference-only text."""

    def __init__(self) -> None:
        Boxes.__init__(self)
        self.addSettingsArgs(edges.FingerJointSettings)

    def render(self) -> None:
        """Render the coupon: a plain-edged blank with 4 burn-neutral
        circular holes (blue) and 4 gray diameter labels underneath."""
        self.set_source_color(CUT_COLOR)

        centers = _magnet_hole_centers()

        def callback() -> None:
            for cx, d in zip(centers, MAGNET_COUPON_DIAMETERS):
                _draw_raw_circle(self, cx, MAGNET_HOLE_ROW_Y, d)
            for cx, d in zip(centers, MAGNET_COUPON_DIAMETERS):
                self.text(
                    f"{d:.2f}", cx, MAGNET_LABEL_Y,
                    align="middle center", fontsize=3.0, color=LABEL_GRAY,
                )

        self.rectangularWall(
            MAGNET_COUPON_WIDTH, MAGNET_COUPON_HEIGHT, "eeee",
            callback=[callback, None, None, None],
            move="right", label="Magnet Fit Coupon",
        )


def generate_magnet_coupon() -> Path:
    """Generate the magnet press-fit calibration coupon SVG file.

    Returns:
        Path to the generated SVG file.
    """
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / "magnet_coupon.svg"

    coupon = MagnetFitCoupon()
    coupon.parseArgs([
        "--output", str(output_file),
        "--thickness", str(MATERIAL_THICKNESS),
        "--burn", str(BURN),
        "--reference", "0",
        "--FingerJoint_play", str(FINGER_PLAY_RELATIVE),
    ])

    coupon.open()
    coupon.render()
    data = coupon.close()

    with open(output_file, "wb") as f:
        f.write(data.getvalue())

    print(f"Generated magnet press-fit coupon SVG: {output_file.absolute()}")
    print(f"  Coupon blank: {MAGNET_COUPON_WIDTH}mm x {MAGNET_COUPON_HEIGHT}mm")
    print(f"  Current config guess: MAGNET_DIA={MAGNET_DIA}, MAGNET_PRESS_FIT={MAGNET_PRESS_FIT} "
          f"(hole dia {MAGNET_DIA - MAGNET_PRESS_FIT:.2f}mm)")
    print("  4 drawn (burn-neutral) gauge holes -- press a real 6mm disc magnet into each on")
    print("  scrap; whichever seats snugly (not loose, not forced) sets the real press-fit hole")
    print(f"  diameter. Gauge diameters: {', '.join(f'{d:.2f}mm' for d in MAGNET_COUPON_DIAMETERS)}.")
    print("  Then set MAGNET_PRESS_FIT = MAGNET_DIA - <snuggest diameter> in config.py and")
    print("  regenerate the shell/drawer SVGs (the magnet holes there ARE burn-compensated, so")
    print("  they need no further correction once MAGNET_PRESS_FIT itself is right).")
    return output_file


if __name__ == "__main__":
    generate_calibration()
    generate_magnet_coupon()
