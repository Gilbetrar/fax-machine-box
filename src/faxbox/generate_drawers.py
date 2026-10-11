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

import math
from pathlib import Path

from boxes import Boxes
from boxes import edges

from faxbox import config
from faxbox.config import (
    FINGER_PLAY_RELATIVE,
    DRAWER_BODY,
    DRAWER_GUIDE,
    DRAWER_GRIP_SLOT,
    FACEPLATE,
    FACEPLATE_SLOT_TOP_BELOW_EDGE,
    FACEPLATE_Z_OFFSET,
    MAGNET_HOLE_DIA,
    MAGNET_Y_OFFSET,
    MATERIAL_THICKNESS,
)
from faxbox.svglabels import enforce_reference_labels

T = MATERIAL_THICKNESS

# Body interior (DESIGN.md #9: "Body interior: 142.65 x 212.25 x 50.325").
# Width/length lose a thickness on each of their two jointed (vertical
# corner) edges; height only loses the bottom -- the top is open.
BODY_INTERIOR_LENGTH = DRAWER_BODY["length"] - 2 * T   # 212.25, X
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
MAGNET_BACK_LOCAL_X = BODY_INTERIOR_WIDTH / 2 + MAGNET_Y_OFFSET     # centred (MAGNET_Y_OFFSET = 0)
MAGNET_BACK_LOCAL_Y = DRAWER_BODY["height"] / 2 - T


class DrawerBox(Boxes):
    """One drawer's 6 pieces: Front, Back, Left Side, Right Side, Bottom,
    Faceplate (DESIGN.md #9)."""

    def __init__(self, provider: str | None = None) -> None:
        Boxes.__init__(self)
        self.addSettingsArgs(edges.FingerJointSettings)
        # Provider abstraction (config.PROVIDERS) -- see shell_generator.py's
        # OuterShell.__init__ for the full rationale. Defaults to "nycr".
        provider_cfg = config.PROVIDERS[config.resolve_provider(provider)]
        self.cut_color = provider_cfg["cut_color"]
        self.engrave_color = provider_cfg["engrave_color"]

    # -- grip slot: same formula for Front and Faceplate, so they align ---
    # (DESIGN.md: "slot top edge 8.0 below the part's top edge"). Each
    # panel's own local-Y=<its nominal height> IS its true, unextended top
    # edge (both Front and Faceplate use a plain 'e' top edge), so applying
    # this formula against each panel's own nominal height lines the two
    # slots up on the same physical Z once the faceplate is glued flush over
    # the body front.

    def _grip_slot_center_y(self, panel_height: float, below_edge: float = GRIP_SLOT_TOP_BELOW_EDGE) -> float:
        slot_top = panel_height - below_edge
        return slot_top - GRIP_SLOT_H / 2

    def _draw_engraved_rect_outline(self, cx: float, cy_unused: float, width: float, height: float) -> None:
        """Red-engraved glue-up registration lines for the drawer body's
        front face: its left and right edges and its top edge, as 3
        disjoint segments with small gaps at the corners (see below).

        The faceplate is glued FACEPLATE_Z_OFFSET (0.75 mm) above the body's
        bottom edge so the plate is centred in the rear-wall opening, which
        puts the body's bottom edge 0.75 mm BELOW the plate: there is no
        bottom line.  Every line stays at least 0.5 mm from the plate's cut
        edge (sides 0.95 in, top 0.75 in, side lines stop 0.6 above the
        bottom edge), so a cut-only service that cuts every line still
        leaves the plate whole, and the lines do not read as part of the
        outline.

        Disjoint segments: Cairo's SVG backend merges consecutive same-style
        strokes into one `<path>` when one segment's endpoint exactly
        matches the next segment's start point, and a merged loop would be
        clustered by svg_utils as a second piece nested in the faceplate.
        A 0.3 mm corner gap keeps each segment its own near-zero-area path
        and is invisible at normal zoom.
        """
        gap = 0.3
        inset_bottom = 0.6
        x0, x1 = cx - width / 2, cx + width / 2
        y_top = FACEPLATE["height"] - FACEPLATE_Z_OFFSET
        self.set_source_color(self.engrave_color)
        for (ax, ay), (bx, by) in (
            ((x0 + gap, y_top), (x1 - gap, y_top)),
            ((x1, y_top - gap), (x1, inset_bottom)),
            ((x0, inset_bottom), (x0, y_top - gap)),
        ):
            self.ctx.move_to(ax, ay)
            self.ctx.line_to(bx, by)
            self.ctx.stroke()
        self.set_source_color(self.cut_color)

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
            cy = self._grip_slot_center_y(FACEPLATE["height"], FACEPLATE_SLOT_TOP_BELOW_EDGE)
            self.rectangularHole(FACEPLATE["width"] / 2, cy, GRIP_SLOT_W, GRIP_SLOT_H, r=GRIP_SLOT_R)
            self._draw_engraved_rect_outline(
                FACEPLATE["width"] / 2, 0.0, DRAWER_BODY["width"], DRAWER_BODY["height"],
            )

        self.rectangularWall(
            FACEPLATE["width"], FACEPLATE["height"], "eeee",
            callback=[callback, None, None, None],
            move="right", label="Faceplate",
        )

    def _build_guide(self, label: str = "Drawer Guide") -> None:
        """Drawer guide rib: DRAWER_GUIDE length x T wide in plan, the leading end
        tapered (red-team H1, V5).  Local x runs along the box X (the tapered end
        at x = length), local y away from the wall (y = 0 is the wall side)."""
        L = DRAWER_GUIDE["length"]
        wt = DRAWER_GUIDE["tip_width"]
        run = (T - wt) / math.tan(math.radians(DRAWER_GUIDE["taper_deg"]))
        hyp = math.hypot(run, T - wt)
        a2 = math.degrees(math.atan2(T - wt, -run))            # heading of the chamfer
        if self.move(L, T, "right", before=True):
            return
        self.moveTo(0, 0, 0)
        self.polyline(L, 90, wt, a2 - 90, hyp, 180 - a2, L - run, 90, T, 90)
        self.ctx.stroke()
        self.move(L, T, "right", label=label)

    def render(self) -> None:
        """Render all 6 pieces, laid out in a single row (move='right'
        throughout) so bounding boxes never overlap."""
        self.set_source_color(self.cut_color)

        self._build_front()
        self._build_back()
        self._build_side("Left Side")
        self._build_side("Right Side")
        self._build_bottom()
        self._build_faceplate()


def generate_guides(provider: str | None = None, burn: float | None = None) -> Path:
    """The four drawer guide strips (two per drawer) in output/guides.svg."""
    name = config.resolve_provider(provider)
    provider_cfg = config.PROVIDERS[name]
    output_path = Path(provider_cfg["output_dir"])
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / "guides.svg"
    g = DrawerBox(provider=name)
    g.parseArgs([
        "--output", str(output_file),
        "--thickness", str(MATERIAL_THICKNESS),
        "--burn", str(provider_cfg["burn"] if burn is None else burn),
        "--reference", "0",
        "--FingerJoint_play", str(FINGER_PLAY_RELATIVE),
    ])
    g.open()
    g.set_source_color(g.cut_color)
    for i in range(4):
        g._build_guide(f"Drawer Guide {i + 1}")
    data = g.close()
    with open(output_file, "wb") as f:
        f.write(data.getvalue())
    enforce_reference_labels(output_file)
    print(f"Generated drawer guides SVG: {output_file.absolute()}")
    return output_file


def generate_drawer(provider: str | None = None, burn: float | None = None) -> Path:
    """Generate a drawer SVG file (one drawer's 6 pieces; cut twice).

    `burn` overrides the provider's per-side kerf compensation (mm); the cut
    sets use it to generate one file set per laser kerf.

    `provider` selects a faxbox.config.PROVIDERS entry (see
    shell_generator.generate_shell's docstring). Passing nothing reproduces
    the original output/drawer.svg exactly.

    Returns:
        Path to the generated SVG file.
    """
    name = config.resolve_provider(provider)
    provider_cfg = config.PROVIDERS[name]
    output_path = Path(provider_cfg["output_dir"])
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / "drawer.svg"

    drawer = DrawerBox(provider=name)
    drawer.parseArgs([
        "--output", str(output_file),
        "--thickness", str(MATERIAL_THICKNESS),
        "--burn", str(provider_cfg["burn"] if burn is None else burn),
        "--reference", "0",
        "--FingerJoint_play", str(FINGER_PLAY_RELATIVE),
    ])

    drawer.open()
    drawer.render()
    data = drawer.close()

    with open(output_file, "wb") as f:
        f.write(data.getvalue())

    # Boxes.py's own move(label=...) draws "Front"/"Back"/etc. in the same
    # red used for real engraves (see faxbox.svglabels module docstring) --
    # neutralize before this file is ever considered laser-ready.
    enforce_reference_labels(output_file)

    print(f"Generated drawer SVG: {output_file.absolute()}")
    print(f"  Body external: {DRAWER_BODY['width']}mm x {DRAWER_BODY['length']}mm x {DRAWER_BODY['height']}mm")
    print(f"  Material thickness: {MATERIAL_THICKNESS}mm")
    return output_file


if __name__ == "__main__":
    generate_drawer()
