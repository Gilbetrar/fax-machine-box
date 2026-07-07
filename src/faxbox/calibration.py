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

RETENTION COUPON (iteration 3, issue #20 red-team): a SEPARATE sibling
output, output/retention_coupon.svg (kept out of kerf_coupon.svg so its
existing "exactly 1 piece" tests -- see tests/test_layout.py -- stay
meaningful), with pieces for tuning the two retention interference values
(LID_DETENT_ENGAGE, DRAWER_DETENT_ENGAGE) before cutting real
iteration-3 parts:

  3. Wall Flexure Sample + Lid Notch Strip: press the strip's notch over the
     sample's nub and feel it snap in/out. If it's too loose (pops out with
     a light nudge) or too stiff (won't seat without force), adjust
     LID_DETENT_ENGAGE in config.py, regenerate, and re-cut both pieces.
  4. Drawer-Side Flexure Sample + Mock Sill Edge + Mock Floor Strip: this
     one exercises the REAL travel axis, not just a press-fit -- lay the
     sample flat, hold the Mock Sill Edge across it near the nub end and
     slide the sample UNDER it (the nub cams up and over, same as the real
     nub crossing the rear-wall opening's own web on insertion), then keep
     sliding the sample across the Mock Floor Strip (the nub rides
     deflected, same as riding the real floor/shelf) until it reaches the
     strip's catch hole and snaps down into it. Adjust DRAWER_DETENT_ENGAGE
     if it's too loose/stiff, regenerate, and re-cut all three.

     This is also issue #20's force-criteria validation: too loose (nub
     pops back out of the catch hole when the sample is shaken/inverted) ->
     raise the relevant ENGAGE value by 0.25 and re-cut; can't slide the
     sample under the sill/across the floor with one-finger force -> lower
     it by 0.25. Iterate on scrap until both mechanisms pass, then
     regenerate all real sheets -- see calibration.py's docstring below and
     README step 3b for the same rule in the kerf coupon's own spirit.

All cut lines are CUT_COLOR (blue) -- nothing on this coupon is engraved.
"""

from pathlib import Path

from boxes import Boxes
from boxes import edges

from faxbox.config import (
    FINGER_PLAY_RELATIVE,
    BURN,
    CATCH_HOLE_X_LENGTH,
    CATCH_HOLE_Y_WIDTH,
    CUT_COLOR,
    DETENT_BEAM_WIDTH,
    DETENT_CLEARANCE,
    DETENT_ROOT_FILLET,
    DETENT_SEVER_WIDTH,
    DRAWER_DETENT_ENGAGE,
    DRAWER_DETENT_NUB_TO_ROOT_SPAN,
    DRAWER_DETENT_NUB_X,
    DRAWER_DETENT_ROOT_X,
    DRAWER_DETENT_TIP_X,
    LID_DETENT_ENGAGE,
    LID_DETENT_NUB_TO_ROOT_SPAN,
    LID_DETENT_ROOT_X,
    LID_DETENT_TIP_X,
    LID_DETENT_X,
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


T = MATERIAL_THICKNESS

# --- Retention coupon geometry (iteration 3, issue #20 red-team) -------------
# Standalone pieces exercising the two mechanisms at small scale, so Ben can
# feel the snap force and tune LID_DETENT_ENGAGE / DRAWER_DETENT_ENGAGE
# before cutting real parts. All plain-edged blanks, same conventions as the
# kerf/fit pieces above.

_SAMPLE_MARGIN = 5.0

# Wall Flexure Sample: a compact stand-in for a side wall's lid-detent area
# -- a slot-with-nub hole across the top (the lid slot floor, with the nub
# poking up into it) and the cantilever release cut below, both drawn with
# the SAME faxbox.detent helpers shell_generator.py uses for the real wall,
# at the SAME relative tip/nub/root layout as the real mechanism (FIX2: nub
# at the beam's free end, not mid-beam) -- shifted so the tip starts
# _SAMPLE_MARGIN in from the sample's own edge.
_WALL_SHIFT = _SAMPLE_MARGIN - LID_DETENT_TIP_X
WALL_SAMPLE_TIP_X = LID_DETENT_TIP_X + _WALL_SHIFT          # = _SAMPLE_MARGIN
WALL_SAMPLE_NUB_X = LID_DETENT_X + _WALL_SHIFT
WALL_SAMPLE_ROOT_X = LID_DETENT_ROOT_X + _WALL_SHIFT
WALL_SAMPLE_WIDTH = WALL_SAMPLE_ROOT_X + _SAMPLE_MARGIN
WALL_SAMPLE_FLOOR_Z = DETENT_BEAM_WIDTH + DETENT_CLEARANCE + 3.0
WALL_SAMPLE_HEIGHT = WALL_SAMPLE_FLOOR_Z + LID_DETENT_ENGAGE + 5.0

# Lid Notch Strip: a short stand-in for the lid's mating edge, carrying the
# same notch generate_lids.py cuts into the real lid.
NOTCH_STRIP_WIDTH = LID_NOTCH_WIDTH + 2 * _SAMPLE_MARGIN
NOTCH_STRIP_HEIGHT = LID_NOTCH_DEPTH + _SAMPLE_MARGIN

# Drawer-Side Flexure Sample: a compact stand-in for one drawer side wall's
# flexure zone (mechanism B, iteration 3) -- the SAME beam+nub geometry
# generate_drawers.py cuts (nub protruding DOWN past the sample's own
# bottom edge by T + DRAWER_DETENT_ENGAGE, same as the real side wall's
# nub reaching past its finger tabs -- see generate_drawers.py's
# _build_side comment), long enough to slide across the Mock Sill Edge and
# Mock Floor Strip below, exercising the real travel axis rather than a
# simple press-fit.
DRAWER_SAMPLE_LEAD_IN = 10.0   # run before the tip, for a hand-hold and to
                               # clear the Mock Sill Edge before camming
_DRAWER_SHIFT = DRAWER_SAMPLE_LEAD_IN - DRAWER_DETENT_TIP_X
DRAWER_SAMPLE_TIP_X = DRAWER_DETENT_TIP_X + _DRAWER_SHIFT     # = DRAWER_SAMPLE_LEAD_IN
DRAWER_SAMPLE_NUB_X = DRAWER_DETENT_NUB_X + _DRAWER_SHIFT
DRAWER_SAMPLE_ROOT_X = DRAWER_DETENT_ROOT_X + _DRAWER_SHIFT
DRAWER_SAMPLE_LENGTH = DRAWER_SAMPLE_ROOT_X + _SAMPLE_MARGIN
DRAWER_SAMPLE_NUB_DEPTH = T + DRAWER_DETENT_ENGAGE
DRAWER_SAMPLE_HEIGHT = DRAWER_SAMPLE_NUB_DEPTH + DETENT_BEAM_WIDTH + DETENT_CLEARANCE + 5.0

# Mock Sill Edge: a thin plain strip, T thick, representing the rear wall's
# own cross-section at the drawer opening (DESIGN.md: "bottom opening sill
# = floor top ... with 3.175-thick web") -- slide the sample under this
# first; its nub cams up and over the edge, same as on a real insertion.
MOCK_SILL_WIDTH = 30.0
MOCK_SILL_HEIGHT = T

# Mock Floor Strip: a plain strip standing in for the bay floor/shelf, with
# ONE catch hole (same size as the real bottom-panel/shelf holes) near its
# far end, so the sample has real "ride" distance before the nub reaches
# it and snaps down.
MOCK_FLOOR_WIDTH = DRAWER_SAMPLE_LENGTH
MOCK_FLOOR_HEIGHT = 20.0
MOCK_FLOOR_HOLE_X = DRAWER_SAMPLE_ROOT_X - 5.0


class _SampleFlexureNubEdge(edges.Edge):
    """Coupon-only twin of generate_drawers.py's _DrawerFlexureNubEdge (see
    that class for the full rationale) -- duplicated rather than imported
    since Boxes.py generators are independent Boxes subclasses with no
    shared base to hang this on, matching this project's existing per-
    generator duplication convention (e.g. _draw_closed_polygon)."""

    def __init__(self, boxes, nub_center_local: float, peak_depth: float) -> None:
        super().__init__(boxes, None)
        self.nub_center_local = nub_center_local
        self.peak_depth = peak_depth

    def __call__(self, length, **kw):
        detour = edge_nub_detour(
            self.nub_center_local - 1.0, self.nub_center_local + 1.0,
            0.0, -self.peak_depth, burn=self.burn,
        )
        self.ctx.move_to(0, 0)
        for x, y in detour:
            self.ctx.line_to(x, y)
        self.ctx.line_to(length, 0)
        self.ctx.translate(*self.ctx.get_current_point())


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
    """A separate standalone sheet (issue #20 red-team, iteration 3): small
    pieces exercising the two retention mechanisms so LID_DETENT_ENGAGE /
    DRAWER_DETENT_ENGAGE can be tuned by feel before cutting real iteration-3
    parts. Kept in its own output file rather than appended to
    CalibrationCoupon's sheet, per the module docstring."""

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
                nub_center=WALL_SAMPLE_NUB_X, nub_top_z=nub_top_z, burn=self.burn,
            )
            self._draw_closed_polygon(points)

            beam_bottom = WALL_SAMPLE_FLOOR_Z - DETENT_BEAM_WIDTH
            cavity_bottom = beam_bottom - DETENT_CLEARANCE
            cavity, sever = release_cut_rects(
                tip=WALL_SAMPLE_TIP_X, root=WALL_SAMPLE_ROOT_X,
                beam_bottom=beam_bottom, cavity_bottom=cavity_bottom,
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
                burn=self.burn,
            )
            self._draw_closed_polygon(points)

        self.rectangularWall(
            NOTCH_STRIP_WIDTH, NOTCH_STRIP_HEIGHT, "eeee",
            callback=[callback, None, None, None],
            move="right", label="Retention: Lid Notch Strip",
        )

    def _build_drawer_sample(self) -> None:
        """Drawer-Side Flexure Sample (mechanism B, iteration 3, FIX5): the
        SAME CompoundEdge + purpose-built nub-edge technique
        generate_drawers.py uses for the real side wall's bottom edge, at a
        small standalone scale. Flanking segments are plain 'e' (no need to
        replicate the real finger joints on a demo strip)."""
        seg1 = DRAWER_SAMPLE_TIP_X
        seg3 = _SAMPLE_MARGIN
        seg2 = DRAWER_SAMPLE_LENGTH - seg1 - seg3
        nub_center_local = DRAWER_SAMPLE_NUB_X - seg1
        nub_edge = _SampleFlexureNubEdge(self, nub_center_local, DRAWER_SAMPLE_NUB_DEPTH)
        bottom_edge = edges.CompoundEdge(self, ["e", nub_edge, "e"], [seg1, seg2, seg3])

        def callback() -> None:
            beam_top = DETENT_BEAM_WIDTH
            cavity_top = DETENT_BEAM_WIDTH + DETENT_CLEARANCE
            cavity, sever = release_cut_rects(
                tip=DRAWER_SAMPLE_TIP_X, root=DRAWER_SAMPLE_ROOT_X,
                beam_bottom=beam_top, cavity_bottom=cavity_top,
                sever_width=DETENT_SEVER_WIDTH, floor=0.0,
            )
            self.rectangularHole(*cavity, r=DETENT_ROOT_FILLET)
            self.rectangularHole(*sever, r=DETENT_ROOT_FILLET)

        self.rectangularWall(
            DRAWER_SAMPLE_LENGTH, DRAWER_SAMPLE_HEIGHT,
            [bottom_edge, self.edges["e"], self.edges["e"], self.edges["e"]],
            callback=[callback, None, None, None],
            move="right", label="Retention: Drawer-Side Flexure Sample",
        )

    def _build_mock_sill_edge(self) -> None:
        self.rectangularWall(
            MOCK_SILL_WIDTH, MOCK_SILL_HEIGHT, "eeee",
            move="right", label="Retention: Mock Sill Edge",
        )

    def _build_mock_floor_strip(self) -> None:
        def callback() -> None:
            self.rectangularHole(
                MOCK_FLOOR_HOLE_X, MOCK_FLOOR_HEIGHT / 2,
                CATCH_HOLE_X_LENGTH, CATCH_HOLE_Y_WIDTH, r=0,
            )

        self.rectangularWall(
            MOCK_FLOOR_WIDTH, MOCK_FLOOR_HEIGHT, "eeee",
            callback=[callback, None, None, None],
            move="right", label="Retention: Mock Floor Strip",
        )

    def render(self) -> None:
        """Render all retention-coupon pieces in a single row."""
        self.set_source_color(CUT_COLOR)
        self._build_wall_sample()
        self._build_notch_strip()
        self._build_drawer_sample()
        self._build_mock_sill_edge()
        self._build_mock_floor_strip()


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
    """Generate the retention coupon SVG file (issue #20 red-team,
    iteration 3): 5 small pieces for tuning LID_DETENT_ENGAGE /
    DRAWER_DETENT_ENGAGE by feel before cutting real iteration-3 parts.
    See this module's docstring.

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
    print("  Cut this on scrap BEFORE the real iteration-3 parts. Pieces:")
    print("    - Wall Flexure Sample + Lid Notch Strip: press the notch over the")
    print("      sample's nub and feel it snap. Tune LID_DETENT_ENGAGE if it's")
    print("      too loose/stiff, regenerate, and re-cut both.")
    print("    - Drawer-Side Flexure Sample + Mock Sill Edge + Mock Floor Strip:")
    print("      slide the sample under the sill edge (nub cams up and over, same")
    print("      as a real insertion), then across the floor strip until it drops")
    print("      into the catch hole and snaps. Tune DRAWER_DETENT_ENGAGE if it's")
    print("      too loose/stiff, regenerate, and re-cut all three.")
    return output_file


if __name__ == "__main__":
    generate_calibration()
    generate_retention_coupon()
