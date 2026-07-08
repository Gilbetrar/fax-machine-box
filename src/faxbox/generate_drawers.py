"""Generate one drawer's 6 pieces (DESIGN.md #9) -- cut twice for the two
identical drawers the box needs.

Body = open-top finger-jointed box, captive bottom: Front, Back, Left Side,
Right Side (all finger-jointed to each other at the vertical corners and to
the Bottom at their lower edge), plus a Bottom panel that sits flush with the
walls' true external footprint and does NOT itself extend (its edges are
plain, with interior finger-hole rows that receive the walls' downward
tabs -- DESIGN.md: "walls' bottom edges may extend downward" while the
bottom stays captive).

Faceplate (6th piece) is a separate, plain-edged panel glued to the body's
front face: it carries the SAME grip slot (aligned with the body Front's, so
a finger can reach through both once glued) plus a red-engraved registration
outline of the body's front cross-section for glue-up alignment.

Only faxbox.config's NEW constants are used here (never the DEPRECATED
legacy block) -- see LEARNINGS.md: Boxes.py 'f' AND 'F' edges both protrude
by up to one thickness (they're phase complements for a corner joint, not a
"male extends / female flush" pair), so a jointed edge always gets counted as
potentially extending a part's blank -- consistent with the tolerance bands
in tests/test_svg_geometry.py.
"""

from pathlib import Path

from boxes import Boxes
from boxes import edges

from faxbox.config import (
    FINGER_PLAY_RELATIVE,
    BURN,
    CUT_COLOR,
    DRAWER_BODY,
    DRAWER_GRIP_SLOT,
    ENGRAVE_COLOR,
    FACEPLATE,
    MAGNET_HOLE_DIA,
    MAGNET_Y_OFFSET,
    MATERIAL_THICKNESS,
    OUTPUT_DIR,
)

T = MATERIAL_THICKNESS

# Body interior (DESIGN.md #9: "Body interior: 142.65 x 211.65 x 50.325").
# Width/length lose a thickness on each of their two jointed (vertical
# corner) edges; height only loses the bottom -- the top is open.
BODY_INTERIOR_LENGTH = DRAWER_BODY["length"] - 2 * T   # 211.65, X
BODY_INTERIOR_WIDTH = DRAWER_BODY["width"] - 2 * T     # 142.65, Y
BODY_INTERIOR_HEIGHT = DRAWER_BODY["height"] - T       # 50.325, Z (floor -> open top)

GRIP_SLOT_W = DRAWER_GRIP_SLOT["width"]
GRIP_SLOT_H = DRAWER_GRIP_SLOT["height"]
GRIP_SLOT_R = DRAWER_GRIP_SLOT["radius"]
GRIP_SLOT_TOP_BELOW_EDGE = DRAWER_GRIP_SLOT["top_below_edge"]  # 8.0

# Magnet retention hole on the Back panel -- the drawer's LEADING wall (the
# deep end, opposite the Front/faceplate -- DESIGN.md "Retention (iteration
# 2)"). Local X is the Back panel's own width axis (= box Y once installed),
# offset from the panel's own center by MAGNET_Y_OFFSET (see config.py: the
# same offset used for the divider's coaxial hole, since the drawer is
# Y-centered in its opening at closed position). Local Y is the panel's own
# height axis; "drawer mid-height" (DRAWER_BODY['height'] / 2) is measured
# from the panel's true physical bottom, which sits T below local y=0 (the
# bottom edge is finger-jointed and protrudes T further down than the
# nominal/unextended blank -- same relationship DESIGN.md's grip-slot formula
# on Front relies on, cross-checked there against the physical 30.5->45.5
# span), hence the "- T" correction here.
MAGNET_BACK_LOCAL_X = BODY_INTERIOR_WIDTH / 2 + MAGNET_Y_OFFSET
MAGNET_BACK_LOCAL_Y = DRAWER_BODY["height"] / 2 - T


class DrawerBox(Boxes):
    """One drawer's 6 pieces: Front, Back, Left Side, Right Side, Bottom,
    Faceplate (DESIGN.md #9)."""

    def __init__(self) -> None:
        Boxes.__init__(self)
        self.addSettingsArgs(edges.FingerJointSettings)

    # -- grip slot: same formula for Front and Faceplate, so they align ---
    # (DESIGN.md: "slot top edge 8.0 below the part's top edge"). Each
    # panel's own local-Y=<its nominal height> IS its true, unextended top
    # edge (both Front and Faceplate use a plain 'e' top edge), so applying
    # this formula against each panel's own nominal height lines the two
    # slots up on the same physical Z once the faceplate is glued flush over
    # the body front.

    def _grip_slot_center_y(self, panel_height: float) -> float:
        slot_top = panel_height - GRIP_SLOT_TOP_BELOW_EDGE
        return slot_top - GRIP_SLOT_H / 2

    def _draw_engraved_rect_outline(self, cx: float, cy: float, width: float, height: float) -> None:
        """Red-engraved rectangle outline, drawn as 4 disjoint line segments
        (small gaps left at the corners) rather than one closed path.

        A single closed rectangle path here would have a bbox ~99% of the
        Faceplate's own bbox area (the registration outline "covers the body
        cross-section exactly in height" per DESIGN.md #9) -- well above
        svg_utils.HOLE_AREA_RATIO (0.5), so the piece-clustering harness
        would treat it as a second same-scale *piece* nested in the
        Faceplate's bbox (exactly the overlap defect that harness exists to
        catch) instead of decoration on it. Cairo's SVG backend also merges
        consecutive same-style strokes into one `<path>` when one segment's
        endpoint exactly matches the next segment's start point (verified
        empirically), so a *connected* 4-segment loop collapses right back
        into one big closed path -- a small corner gap (well under the
        engraving's own visual tolerance) keeps every segment a distinct
        near-zero-area path, each safely clustered as Faceplate decoration.
        """
        gap = 1.0
        x0, x1 = cx - width / 2, cx + width / 2
        y0, y1 = cy - height / 2, cy + height / 2
        self.set_source_color(ENGRAVE_COLOR)
        for (ax, ay), (bx, by) in (
            ((x0 + gap, y0), (x1 - gap, y0)),
            ((x1, y0 + gap), (x1, y1 - gap)),
            ((x1 - gap, y1), (x0 + gap, y1)),
            ((x0, y1 - gap), (x0, y0 + gap)),
        ):
            self.ctx.move_to(ax, ay)
            self.ctx.line_to(bx, by)
            self.ctx.stroke()
        self.set_source_color(CUT_COLOR)

    # -- pieces ---------------------------------------------------------

    def _build_front(self) -> None:
        """Front: BODY_INTERIOR_WIDTH (local X = box Y) x
        BODY_INTERIOR_HEIGHT (local Y = box Z). Left/right finger-joint the
        side walls, bottom finger-joints the Bottom panel, top is open
        (plain). Grip slot cut through per DESIGN.md #9 (amended)."""

        def callback() -> None:
            cy = self._grip_slot_center_y(BODY_INTERIOR_HEIGHT)
            self.rectangularHole(BODY_INTERIOR_WIDTH / 2, cy, GRIP_SLOT_W, GRIP_SLOT_H, r=GRIP_SLOT_R)

        self.rectangularWall(
            BODY_INTERIOR_WIDTH, BODY_INTERIOR_HEIGHT, "fFeF",
            callback=[callback, None, None, None],
            move="right", label="Front",
        )

    def _build_back(self) -> None:
        """Back: same shape as Front, no grip slot -- this IS the drawer's
        LEADING wall (deep end, opposite the faceplate). Carries the
        retention magnet's press-fit through-hole (DESIGN.md "Retention
        (iteration 2)"), coaxial with the divider's matching hole at the
        drawer's fully-closed position."""

        def callback() -> None:
            self.hole(MAGNET_BACK_LOCAL_X, MAGNET_BACK_LOCAL_Y, d=MAGNET_HOLE_DIA)

        self.rectangularWall(
            BODY_INTERIOR_WIDTH, BODY_INTERIOR_HEIGHT, "fFeF",
            callback=[callback, None, None, None],
            move="right", label="Back",
        )

    def _build_side(self, label: str) -> None:
        """Side wall: BODY_INTERIOR_LENGTH (local X = box X) x
        BODY_INTERIOR_HEIGHT (local Y = box Z). Front/back-mating edges
        finger-joint (both ends), bottom finger-joints the Bottom panel, top
        open."""
        self.rectangularWall(
            BODY_INTERIOR_LENGTH, BODY_INTERIOR_HEIGHT, "ffef",
            move="right", label=label,
        )

    def _build_bottom(self) -> None:
        """Bottom: full external footprint (DRAWER_BODY length x width) --
        it sits flush with the walls' true outside faces, not inset between
        them, and its own edges stay plain (captive: DESIGN.md "walls'
        bottom edges may extend downward" while the bottom does not). The
        4 finger-hole rows below receive the walls' downward-protruding
        bottom-edge tabs, one per wall, each row's length matching that
        wall's own interior nominal so the finger pitch lines up."""

        def callback() -> None:
            length, width = DRAWER_BODY["length"], DRAWER_BODY["width"]
            # Front/back rows: vertical, near the X=0 / X=length edges.
            self.fingerHolesAt(T / 2, T, BODY_INTERIOR_WIDTH, angle=90)
            self.fingerHolesAt(length - T / 2, T, BODY_INTERIOR_WIDTH, angle=90)
            # Left/right rows: horizontal, near the Y=0 / Y=width edges.
            self.fingerHolesAt(T, T / 2, BODY_INTERIOR_LENGTH, angle=0)
            self.fingerHolesAt(T, width - T / 2, BODY_INTERIOR_LENGTH, angle=0)

        self.rectangularWall(
            DRAWER_BODY["length"], DRAWER_BODY["width"], "eeee",
            callback=[callback, None, None, None],
            move="right", label="Bottom",
        )

    def _build_faceplate(self) -> None:
        """Faceplate: FACEPLATE width x height (DESIGN.md #9), plain edges
        (glued, not finger-jointed). Grip slot aligned with the body
        Front's, plus a red-engraved registration outline of the body's
        front cross-section (DRAWER_BODY width x height, centered)."""

        def callback() -> None:
            cy = self._grip_slot_center_y(FACEPLATE["height"])
            self.rectangularHole(FACEPLATE["width"] / 2, cy, GRIP_SLOT_W, GRIP_SLOT_H, r=GRIP_SLOT_R)
            self._draw_engraved_rect_outline(
                FACEPLATE["width"] / 2, FACEPLATE["height"] / 2,
                DRAWER_BODY["width"], DRAWER_BODY["height"],
            )

        self.rectangularWall(
            FACEPLATE["width"], FACEPLATE["height"], "eeee",
            callback=[callback, None, None, None],
            move="right", label="Faceplate",
        )

    def render(self) -> None:
        """Render all 6 pieces, laid out in a single row (move='right'
        throughout) so bounding boxes never overlap."""
        self.set_source_color(CUT_COLOR)

        self._build_front()
        self._build_back()
        self._build_side("Left Side")
        self._build_side("Right Side")
        self._build_bottom()
        self._build_faceplate()


def generate_drawer() -> Path:
    """Generate a drawer SVG file (one drawer's 6 pieces; cut twice).

    Returns:
        Path to the generated SVG file.
    """
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / "drawer.svg"

    drawer = DrawerBox()
    drawer.parseArgs([
        "--output", str(output_file),
        "--thickness", str(MATERIAL_THICKNESS),
        "--burn", str(BURN),
        "--reference", "0",
        "--FingerJoint_play", str(FINGER_PLAY_RELATIVE),
    ])

    drawer.open()
    drawer.render()
    data = drawer.close()

    with open(output_file, "wb") as f:
        f.write(data.getvalue())

    print(f"Generated drawer SVG: {output_file.absolute()}")
    print(f"  Body external: {DRAWER_BODY['width']}mm x {DRAWER_BODY['length']}mm x {DRAWER_BODY['height']}mm")
    print(f"  Material thickness: {MATERIAL_THICKNESS}mm")
    return output_file


if __name__ == "__main__":
    generate_drawer()
