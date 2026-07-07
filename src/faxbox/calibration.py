"""Generate a kerf/fit calibration coupon (red-team finding: DESIGN.md and
config.py specify BURN=0.08 and FINGER_PLAY=0.1 as *starting* values that
must be "calibrate[d] with a test cut before the real run" -- but no such
test cut existed anywhere in this project, so the first real sheet would
have been the first data point).

Output: 1 piece in output/kerf_coupon.svg -- a single small standalone panel,
NOT part of any sheet_*.svg / final_layout.svg (see layout.py's module
docstring: it only nests outer_shell.svg + drawer.svg + lids.svg). Cut this
on scrap BEFORE the real sheets, then:

  1. Try to press a scrap of the actual plywood stock into each of the three
     slots. Whichever slot it seats into snugly (not loose, not forced) says
     how thick your stock is actually measuring -- use that to sanity-check
     MATERIAL_THICKNESS / FINGER_PLAY in config.py before cutting joints.
  2. Measure the square hole with calipers. Its tool path is drawn at exactly
     10.0mm x 10.0mm (burn compensation cancelled for this one feature), so
     the physical hole measures 10.0 + 2x(real per-side kerf). Set
     BURN = (measured - 10.0) / 2, then regenerate and re-cut the coupon:
     the thickness slots only read true once BURN matches the real kerf.

RETENTION COUPON (iteration 2, issue #20): a SEPARATE sibling output,
output/retention_coupon.svg (kept out of kerf_coupon.svg so its existing
"exactly 1 piece" tests -- see tests/test_layout.py -- stay meaningful), with
4 small pieces for tuning the two retention interference values
(LID_DETENT_ENGAGE, DRAWER_DETENT_PROTRUDE) before cutting real
iteration-2 parts:

  3. Wall Flexure Sample + Lid Notch Strip: press the strip's notch over the
     sample's nub and feel it snap in/out. If it's too loose (pops out with
     a light nudge) or too stiff (won't seat without force), adjust
     LID_DETENT_ENGAGE in config.py, regenerate, and re-cut both pieces.
  4. Faceplate Flexure Sample + Mock Opening Edge: slide the mock edge
     across the sample's nub the way the rear-wall opening's corner would
     slide across it on a real close, and feel the same snap. Adjust
     DRAWER_DETENT_PROTRUDE if it's too loose/stiff, regenerate, and re-cut.

All cut lines are CUT_COLOR (blue) -- nothing on this coupon is engraved.
"""

from pathlib import Path

from boxes import Boxes
from boxes import edges

from faxbox.config import (
    FINGER_PLAY_RELATIVE,
    BURN,
    CUT_COLOR,
    DETENT_BEAM_LENGTH,
    DETENT_BEAM_WIDTH,
    DETENT_CLEARANCE,
    DETENT_ROOT_FILLET,
    DETENT_SEVER_WIDTH,
    DRAWER_DETENT_PROTRUDE,
    FACEPLATE_REVEAL,
    LID_DETENT_ENGAGE,
    LID_NOTCH_CHAMFER,
    LID_NOTCH_DEPTH,
    LID_NOTCH_WIDTH,
    MATERIAL_THICKNESS,
    OUTPUT_DIR,
)
from faxbox.detent import edge_nub_detour, lid_slot_with_nub_points, notch_points, release_cut_rects

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


# --- Retention coupon geometry (iteration 2, issue #20) ----------------------
# Four standalone pieces exercising the two mechanisms at small scale, so Ben
# can feel the snap force and tune LID_DETENT_ENGAGE / DRAWER_DETENT_PROTRUDE
# before cutting real parts. All plain-edged blanks, same conventions as the
# kerf/fit pieces above.

_SAMPLE_MARGIN = 5.0

# Wall Flexure Sample: a compact stand-in for a side wall's lid-detent area
# -- a slot-with-nub hole across the top (the lid slot floor, with the nub
# poking up into it) and the cantilever release cut below, both drawn with
# the SAME faxbox.detent helpers shell_generator.py uses for the real wall.
WALL_SAMPLE_WIDTH = DETENT_BEAM_LENGTH + 2 * _SAMPLE_MARGIN
WALL_SAMPLE_FLOOR_Z = DETENT_BEAM_WIDTH + DETENT_CLEARANCE + 3.0
WALL_SAMPLE_HEIGHT = WALL_SAMPLE_FLOOR_Z + LID_DETENT_ENGAGE + 5.0

# Lid Notch Strip: a short stand-in for the lid's mating edge, carrying the
# same notch generate_lids.py cuts into the real lid.
NOTCH_STRIP_WIDTH = LID_NOTCH_WIDTH + 2 * _SAMPLE_MARGIN
NOTCH_STRIP_HEIGHT = LID_NOTCH_DEPTH + _SAMPLE_MARGIN

# Faceplate Flexure Sample: a compact stand-in for one faceplate Y edge --
# the SAME nub-detour + release-cut shape generate_drawers.py cuts into the
# real faceplate, on just one edge (a sample only needs one to demonstrate
# the snap).
FACE_SAMPLE_HEIGHT = DETENT_BEAM_LENGTH + 2 * _SAMPLE_MARGIN
FACE_SAMPLE_BODY_WIDTH = DETENT_BEAM_WIDTH + DETENT_CLEARANCE + 3.0
FACE_SAMPLE_WIDTH = FACE_SAMPLE_BODY_WIDTH + DRAWER_DETENT_PROTRUDE

# Mock Opening Edge: a plain strip representing the rear-wall opening's side
# edge the faceplate nub snaps behind -- hold it FACEPLATE_REVEAL off the
# faceplate sample's rest edge and slide the two together.
MOCK_EDGE_WIDTH = 40.0
MOCK_EDGE_HEIGHT = 15.0


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


class RetentionCoupon(Boxes):
    """A separate standalone sheet (issue #20): 4 small pieces exercising
    the two retention mechanisms so LID_DETENT_ENGAGE / DRAWER_DETENT_PROTRUDE
    can be tuned by feel before cutting real iteration-2 parts. Kept in its
    own output file rather than appended to CalibrationCoupon's sheet, per
    the module docstring."""

    def __init__(self) -> None:
        Boxes.__init__(self)
        self.addSettingsArgs(edges.FingerJointSettings)

    def _draw_closed_polygon(self, points: list[tuple[float, float]]) -> None:
        """Stroke a closed polygon -- see faxbox.detent module docstring."""
        self.ctx.move_to(*points[0])
        for pt in points[1:]:
            self.ctx.line_to(*pt)
        self.ctx.line_to(*points[0])
        self.ctx.stroke()

    def _build_wall_sample(self) -> None:
        def callback() -> None:
            nub_top_z = WALL_SAMPLE_FLOOR_Z + LID_DETENT_ENGAGE
            points = lid_slot_with_nub_points(
                u0=0, u1=WALL_SAMPLE_WIDTH, z0=WALL_SAMPLE_FLOOR_Z, z1=WALL_SAMPLE_HEIGHT,
                nub_center=WALL_SAMPLE_WIDTH / 2, nub_top_z=nub_top_z,
            )
            self._draw_closed_polygon(points)

            tip = WALL_SAMPLE_WIDTH / 2 - DETENT_BEAM_LENGTH / 2
            root = WALL_SAMPLE_WIDTH / 2 + DETENT_BEAM_LENGTH / 2
            beam_bottom = WALL_SAMPLE_FLOOR_Z - DETENT_BEAM_WIDTH
            cavity_bottom = beam_bottom - DETENT_CLEARANCE
            cavity, sever = release_cut_rects(
                tip=tip, root=root, beam_bottom=beam_bottom, cavity_bottom=cavity_bottom,
                sever_width=DETENT_SEVER_WIDTH, floor=WALL_SAMPLE_FLOOR_Z,
            )
            self.rectangularHole(*cavity, r=DETENT_ROOT_FILLET)
            self.rectangularHole(*sever, r=DETENT_ROOT_FILLET)

        self.rectangularWall(
            WALL_SAMPLE_WIDTH, WALL_SAMPLE_HEIGHT, "eeee",
            callback=[callback, None, None, None],
            move="right", label="Retention: Wall Flexure Sample",
        )

    def _build_notch_strip(self) -> None:
        def callback() -> None:
            points = notch_points(
                center=NOTCH_STRIP_WIDTH / 2, width=LID_NOTCH_WIDTH, depth=LID_NOTCH_DEPTH,
                chamfer=LID_NOTCH_CHAMFER, edge_level=0.0, inward_sign=1.0,
            )
            self._draw_closed_polygon(points)

        self.rectangularWall(
            NOTCH_STRIP_WIDTH, NOTCH_STRIP_HEIGHT, "eeee",
            callback=[callback, None, None, None],
            move="right", label="Retention: Lid Notch Strip",
        )

    def _build_faceplate_sample(self) -> None:
        """Bypasses rectangularWall's automatic straight edges for the same
        reason generate_drawers.py's _build_faceplate does: the nub-bearing
        edge needs a local protrusion no Boxes.py edge class can express, so
        the whole outline is hand-drawn (see faxbox.detent's docstring)."""
        edge_rest = DRAWER_DETENT_PROTRUDE
        peak = 0.0
        tip_z = FACE_SAMPLE_HEIGHT / 2 + DETENT_BEAM_LENGTH / 2
        root_z = FACE_SAMPLE_HEIGHT / 2 - DETENT_BEAM_LENGTH / 2
        detour = [(x, y) for y, x in edge_nub_detour(root_z, tip_z, edge_rest, peak)]
        outline = [
            (edge_rest, 0.0),
            (FACE_SAMPLE_WIDTH, 0.0),
            (FACE_SAMPLE_WIDTH, FACE_SAMPLE_HEIGHT),
            (edge_rest, FACE_SAMPLE_HEIGHT),
            (edge_rest, tip_z),
            *reversed(detour),
        ]

        if self.move(FACE_SAMPLE_WIDTH, FACE_SAMPLE_HEIGHT, "right", before=True):
            return
        self.moveTo(0, 0)
        self.set_source_color(CUT_COLOR)
        self._draw_closed_polygon(outline)

        beam_bottom = edge_rest + DETENT_BEAM_WIDTH
        cavity_bottom = beam_bottom + DETENT_CLEARANCE
        cavity, sever = release_cut_rects(
            tip=tip_z, root=root_z, beam_bottom=beam_bottom, cavity_bottom=cavity_bottom,
            sever_width=DETENT_SEVER_WIDTH, floor=edge_rest,
        )
        for cx, cy, dx, dy in (cavity, sever):
            self.rectangularHole(cy, cx, dy, dx, r=DETENT_ROOT_FILLET)

        self.move(FACE_SAMPLE_WIDTH, FACE_SAMPLE_HEIGHT, "right", label="Retention: Faceplate Flexure Sample")

    def _build_mock_opening_edge(self) -> None:
        self.rectangularWall(
            MOCK_EDGE_WIDTH, MOCK_EDGE_HEIGHT, "eeee",
            move="right", label="Retention: Mock Opening Edge",
        )

    def render(self) -> None:
        """Render all 4 retention-coupon pieces in a single row."""
        self.set_source_color(CUT_COLOR)
        self._build_wall_sample()
        self._build_notch_strip()
        self._build_faceplate_sample()
        self._build_mock_opening_edge()


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


def generate_retention_coupon() -> Path:
    """Generate the retention coupon SVG file (issue #20): 4 small pieces
    for tuning LID_DETENT_ENGAGE / DRAWER_DETENT_PROTRUDE by feel before
    cutting real iteration-2 parts. See this module's docstring.

    Returns:
        Path to the generated SVG file.
    """
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / "retention_coupon.svg"

    coupon = RetentionCoupon()
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

    print(f"Generated retention coupon SVG: {output_file.absolute()}")
    print("  Cut this on scrap BEFORE the real iteration-2 parts. Pieces:")
    print("    - Wall Flexure Sample + Lid Notch Strip: press the notch over the")
    print("      sample's nub and feel it snap. Tune LID_DETENT_ENGAGE if it's")
    print("      too loose/stiff, regenerate, and re-cut both.")
    print("    - Faceplate Flexure Sample + Mock Opening Edge: slide the mock edge")
    print("      across the sample's nub the way a real close would, and feel the")
    print("      same snap. Tune DRAWER_DETENT_PROTRUDE, regenerate, and re-cut.")
    return output_file


if __name__ == "__main__":
    generate_calibration()
    generate_retention_coupon()
