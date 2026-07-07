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
    DETENT_BEAM_WIDTH,
    DETENT_CLEARANCE,
    DETENT_ROOT_FILLET,
    DETENT_SEVER_WIDTH,
    DRAWER_BODY,
    DRAWER_DETENT_ENGAGE,
    DRAWER_DETENT_NUB_X,
    DRAWER_DETENT_PLAIN_HI,
    DRAWER_DETENT_PLAIN_LO,
    DRAWER_DETENT_ROOT_X,
    DRAWER_DETENT_TIP_X,
    DRAWER_GRIP_SLOT,
    ENGRAVE_COLOR,
    FACEPLATE,
    MATERIAL_THICKNESS,
    OUTPUT_DIR,
)
from faxbox.detent import edge_nub_detour, release_cut_rects

T = MATERIAL_THICKNESS

# Body interior (DESIGN.md #9: "Body interior: 142.65 x 212.25 x 50.325").
# Width/length lose a thickness on each of their two jointed (vertical
# corner) edges; height only loses the bottom -- the top is open.
BODY_INTERIOR_LENGTH = DRAWER_BODY["length"] - 2 * T   # 212.25, X
BODY_INTERIOR_WIDTH = DRAWER_BODY["width"] - 2 * T     # 142.65, Y
BODY_INTERIOR_HEIGHT = DRAWER_BODY["height"] - T       # 50.325, Z (floor -> open top)


class _DrawerFlexureNubEdge(edges.Edge):
    """A straight edge (drop-in for Boxes.py's plain "e") that additionally
    draws a single ramped, DOWNWARD-protruding flexure nub at a fixed
    position along its own length.

    Used as the middle segment of a CompoundEdge standing in for the drawer
    side wall's normally fully finger-jointed bottom edge, over the
    flexure's plain zone (mechanism B, iteration 3, issue #20 red-team):
    Boxes.py's edge classes draw one continuous run with no way to inject a
    local protrusion (the same limitation the removed iteration-2 faceplate
    detent hit), so this is a purpose-built Edge subclass instead of a
    callback -- it participates in the same finger-joint-length-matching
    CompoundEdge convention already used elsewhere in this project
    (shell_generator.py's front-edge and top-panel CompoundEdges).
    """

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

GRIP_SLOT_W = DRAWER_GRIP_SLOT["width"]
GRIP_SLOT_H = DRAWER_GRIP_SLOT["height"]
GRIP_SLOT_R = DRAWER_GRIP_SLOT["radius"]
GRIP_SLOT_TOP_BELOW_EDGE = DRAWER_GRIP_SLOT["top_below_edge"]  # 8.0


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
        """Back: same shape as Front, no grip slot."""
        self.rectangularWall(
            BODY_INTERIOR_WIDTH, BODY_INTERIOR_HEIGHT, "fFeF",
            move="right", label="Back",
        )

    def _build_side(self, label: str) -> None:
        """Side wall: BODY_INTERIOR_LENGTH (local X = box X) x
        BODY_INTERIOR_HEIGHT (local Y = box Z). Front/back-mating edges
        finger-joint (both ends), top open.

        Bottom edge: finger-jointed to the Bottom panel EXCEPT a short
        PLAIN zone (DRAWER_DETENT_PLAIN_LO -> DRAWER_DETENT_PLAIN_HI) near
        the FRONT (x=0, faceplate) end, carrying a cantilever spring-detent
        flexure (mechanism B, iteration 3, issue #20 red-team replacement
        for the geometrically-impossible faceplate detent -- see DESIGN.md
        "Retention"). Convention (this project's own choice; both ends
        finger-joint identically otherwise, so nothing else distinguishes
        them): local x=0 mates the Front panel (the faceplate end); this is
        a NEW assembly constraint -- both side panels must go in with their
        flexure end toward Front, not Back. A finger-jointed edge can't
        locally express the nub's protrusion (same reason the old faceplate
        needed a hand-drawn boundary), so the plain zone uses a purpose-
        built Edge (_DrawerFlexureNubEdge) via CompoundEdge instead of a
        plain 'e' -- the Bottom panel's matching finger-hole row is split to
        skip this same X-range (see _build_bottom)."""
        seg1_len = DRAWER_DETENT_PLAIN_LO
        seg2_len = DRAWER_DETENT_PLAIN_HI - DRAWER_DETENT_PLAIN_LO
        seg3_len = BODY_INTERIOR_LENGTH - DRAWER_DETENT_PLAIN_HI
        nub_center_local = DRAWER_DETENT_NUB_X - DRAWER_DETENT_PLAIN_LO
        # The plain zone's local y=0 is the wall's NOMINAL (pre-tab) bottom
        # reference; the "f" edges either side of it already protrude T
        # beyond that (their finger tabs reach the drawer's TRUE exterior
        # bottom). DRAWER_DETENT_ENGAGE is defined relative to that true
        # exterior bottom (DESIGN.md), so the nub's drawn depth from y=0 is
        # T + DRAWER_DETENT_ENGAGE, not DRAWER_DETENT_ENGAGE alone -- else
        # the nub falls short of even the neighboring tabs' own reach.
        nub_edge = _DrawerFlexureNubEdge(self, nub_center_local, T + DRAWER_DETENT_ENGAGE)
        bottom_edge = edges.CompoundEdge(
            self, ["f", nub_edge, "f"], [seg1_len, seg2_len, seg3_len])

        def callback() -> None:
            # Cantilever release cut: frees the beam on 3 sides (a clearance
            # cavity above it, into the panel's own solid material, and a
            # severing slot at its free/tip end) while leaving the root end
            # (deeper into the wall, toward the Back panel) solid -- same
            # L-shape logic as the wall's lid detent (faxbox.detent.
            # release_cut_rects), just transposed: "along" is X, "across"
            # is local Y, "floor" is the plain zone's own baseline (local
            # y=0), and the beam sits ABOVE it (local y increasing, into
            # the panel) rather than below, since the nub protrudes DOWN
            # past y=0 while the panel's own bulk is above it.
            beam_top = DETENT_BEAM_WIDTH
            cavity_top = DETENT_BEAM_WIDTH + DETENT_CLEARANCE
            cavity, sever = release_cut_rects(
                tip=DRAWER_DETENT_TIP_X, root=DRAWER_DETENT_ROOT_X,
                beam_bottom=beam_top, cavity_bottom=cavity_top,
                sever_width=DETENT_SEVER_WIDTH, floor=0.0,
            )
            self.rectangularHole(*cavity, r=DETENT_ROOT_FILLET)
            self.rectangularHole(*sever, r=DETENT_ROOT_FILLET)

        self.rectangularWall(
            BODY_INTERIOR_LENGTH, BODY_INTERIOR_HEIGHT,
            [bottom_edge, self.edges["f"], self.edges["e"], self.edges["f"]],
            callback=[callback, None, None, None],
            move="right", label=label,
        )

    def _build_bottom(self) -> None:
        """Bottom: full external footprint (DRAWER_BODY length x width) --
        it sits flush with the walls' true outside faces, not inset between
        them, and its own edges stay plain (captive: DESIGN.md "walls'
        bottom edges may extend downward" while the bottom does not). The
        finger-hole rows below receive the walls' downward-protruding
        bottom-edge tabs, one per wall, each row's length matching that
        wall's own interior nominal so the finger pitch lines up.

        The left/right (side-wall) rows are each SPLIT into two segments
        skipping DRAWER_DETENT_PLAIN_LO -> DRAWER_DETENT_PLAIN_HI, matching
        the side walls' own CompoundEdge plain zone there (mechanism B) --
        without this split, that row would carry finger holes with no
        tab to plug them (the side wall has no tab in that zone either)."""

        def callback() -> None:
            length, width = DRAWER_BODY["length"], DRAWER_BODY["width"]
            # Front/back rows: vertical, near the X=0 / X=length edges.
            self.fingerHolesAt(T / 2, T, BODY_INTERIOR_WIDTH, angle=90)
            self.fingerHolesAt(length - T / 2, T, BODY_INTERIOR_WIDTH, angle=90)
            # Left/right rows: horizontal, near the Y=0 / Y=width edges,
            # split around the flexure's plain zone (both side walls carry
            # the SAME zone, so both rows split the same way).
            seg2_start = T + DRAWER_DETENT_PLAIN_HI
            seg2_len = BODY_INTERIOR_LENGTH - DRAWER_DETENT_PLAIN_HI
            for y in (T / 2, width - T / 2):
                self.fingerHolesAt(T, y, DRAWER_DETENT_PLAIN_LO, angle=0)
                self.fingerHolesAt(seg2_start, y, seg2_len, angle=0)

        self.rectangularWall(
            DRAWER_BODY["length"], DRAWER_BODY["width"], "eeee",
            callback=[callback, None, None, None],
            move="right", label="Bottom",
        )

    def _build_faceplate(self) -> None:
        """Faceplate: FACEPLATE width x height (DESIGN.md #9), plain edges
        (glued, not finger-jointed). Grip slot aligned with the body
        Front's, plus a red-engraved registration outline of the body's
        front cross-section (DRAWER_BODY width x height, centered).

        Reverted to the exact v1 (pre-iteration-2) blank (issue #20
        red-team FIX1): the iteration-2 faceplate detent was geometrically
        impossible (the faceplate is a Y-Z plate; the drawer travels along
        X, normal to that plate, so a Z-ramped nub can never be swept by the
        drawer's own motion -- it would only ever meet the rear-wall opening
        as a square 0.45mm interference, not a cam). Retention now lives
        entirely in the drawer SIDE walls instead -- see _build_side and
        DESIGN.md's "Retention" section."""

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
