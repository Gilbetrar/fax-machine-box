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
    DRAWER_DETENT_PROTRUDE,
    DRAWER_DETENT_ROOT_Z,
    DRAWER_DETENT_TIP_Z,
    DRAWER_GRIP_SLOT,
    ENGRAVE_COLOR,
    FACEPLATE,
    FACEPLATE_DRAWN_WIDTH,
    MATERIAL_THICKNESS,
    OUTPUT_DIR,
)
from faxbox.detent import edge_nub_detour, release_cut_rects

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

    def _draw_closed_polygon(self, points: list[tuple[float, float]]) -> None:
        """Stroke a closed polygon -- see faxbox.detent module docstring;
        duplicated per-generator like generate_lids.py's copy since Boxes.py
        generators don't share a common mixin base."""
        self.ctx.move_to(*points[0])
        for pt in points[1:]:
            self.ctx.line_to(*pt)
        self.ctx.line_to(*points[0])
        self.ctx.stroke()

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
        (glued, not finger-jointed), plus a cantilever spring detent near
        EACH Y side edge (retention iteration 2, issue #20): a ramped nub
        protrudes DRAWER_DETENT_PROTRUDE beyond the nominal edge on both
        sides, so it can snap past the rear-wall opening's side edge on
        close. Grip slot and the glue-up registration outline are unchanged
        in size, just re-centered for the drawing offset below.

        Boxes.py's rectangularWall can't inject a local protrusion into a
        plain "e" edge's path (an edge class draws one continuous straight
        run for its whole length), so the outer boundary is hand-drawn here
        instead -- see faxbox.detent's module docstring. This deliberately
        makes the Faceplate's drawn/measured footprint
        FACEPLATE_DRAWN_WIDTH (150.9 + 2*DRAWER_DETENT_PROTRUDE) rather than
        the plain FACEPLATE["width"] -- see DESIGN.md "Retention (iteration
        2)" and the flagged test_faceplate_blank_size deviation in
        tests/test_svg_geometry.py for why that's an intentional, minimal,
        and unavoidable consequence of this being a REAL protruding
        interference feature (there's no way to add real retention without
        the physical part becoming physically bigger at the nub).
        """
        offset = DRAWER_DETENT_PROTRUDE  # true drawn x=0 is the LEFT nub's tip
        width, height = FACEPLATE["width"], FACEPLATE["height"]

        def body_x(x: float) -> float:
            return x + offset

        left_rest, right_rest = body_x(0.0), body_x(width)
        left_peak, right_peak = left_rest - DRAWER_DETENT_PROTRUDE, right_rest + DRAWER_DETENT_PROTRUDE

        # edge_nub_detour returns (along=Z, across=drawn-x) pairs in
        # increasing-Z order; swap to (x, y) for the polygon point list.
        right_detour = [(x, y) for y, x in edge_nub_detour(
            DRAWER_DETENT_ROOT_Z, DRAWER_DETENT_TIP_Z, right_rest, right_peak)]
        left_detour = [(x, y) for y, x in edge_nub_detour(
            DRAWER_DETENT_ROOT_Z, DRAWER_DETENT_TIP_Z, left_rest, left_peak)]

        outline = [
            (left_rest, 0.0),
            (right_rest, 0.0),
            (right_rest, DRAWER_DETENT_ROOT_Z),
            *right_detour,
            (right_rest, height),
            (left_rest, height),
            (left_rest, DRAWER_DETENT_TIP_Z),
            *reversed(left_detour),
        ]

        # Bypass rectangularWall's automatic straight-edge drawing: its "e"
        # edge class draws one continuous run for the whole edge length with
        # no way to inject the nub detour above, and calling it anyway (even
        # sized to FACEPLATE_DRAWN_WIDTH) would additionally stroke a plain
        # rectangle overlapping/conflicting with the hand-drawn outline. Use
        # the same before/after self.move() bookkeeping rectangularWall uses
        # internally (its own sanctioned public API for this exact purpose,
        # per its docstring) so this piece still lands correctly in the
        # move="right" row of parts, without also drawing the plain edges.
        if self.move(FACEPLATE_DRAWN_WIDTH, height, "right", before=True):
            return
        self.moveTo(0, 0)

        self.set_source_color(CUT_COLOR)
        self._draw_closed_polygon(outline)

        cy = self._grip_slot_center_y(height)
        self.rectangularHole(body_x(width / 2), cy, GRIP_SLOT_W, GRIP_SLOT_H, r=GRIP_SLOT_R)
        self._draw_engraved_rect_outline(
            body_x(width / 2), height / 2,
            DRAWER_BODY["width"], DRAWER_BODY["height"],
        )

        # Cantilever release cuts (both sides): free the beam on 3 sides
        # while leaving its root end solid, same L-shape logic as the wall's
        # lid detent (faxbox.detent.release_cut_rects), just transposed --
        # "along" here is Z (root/tip), "across" is drawn-x, so the returned
        # (cx, cy, dx, dy) tuples need their x/y swapped before calling
        # rectangularHole(x, y, dx, dy).
        for edge_rest, sign in ((left_rest, 1.0), (right_rest, -1.0)):
            beam_bottom = edge_rest + sign * DETENT_BEAM_WIDTH
            cavity_bottom = edge_rest + sign * (DETENT_BEAM_WIDTH + DETENT_CLEARANCE)
            cavity, sever = release_cut_rects(
                tip=DRAWER_DETENT_TIP_Z, root=DRAWER_DETENT_ROOT_Z,
                beam_bottom=beam_bottom, cavity_bottom=cavity_bottom,
                sever_width=DETENT_SEVER_WIDTH, floor=edge_rest,
            )
            for cx, cy, dx, dy in (cavity, sever):
                self.rectangularHole(cy, cx, dy, dx, r=DETENT_ROOT_FILLET)

        self.move(FACEPLATE_DRAWN_WIDTH, height, "right", label="Faceplate")

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
