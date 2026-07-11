"""Generate the outer shell (8 pieces) for the fax machine box.

Implements DESIGN.md's shell geometry exactly: full-height side/front/rear
walls with an inset bottom panel (standard finger-box construction), a
vertical divider, a horizontal shelf, and a fixed top panel over the drawer
bay. See DESIGN.md for the canonical numbers; only faxbox.config's NEW
constants are used here (never the DEPRECATED legacy block).

Coordinate convention used throughout the callbacks below (per DESIGN.md):
origin at the exterior front-left-bottom corner, X = length (front->rear),
Y = width (left->right), Z = height (bottom->top). Each rectangularWall's own
"local" x/y axes are documented at the top of the function that builds it.

Output: 8 pieces in output/outer_shell.svg -- Bottom, Left Wall, Right Wall,
Front Wall, Rear Wall, Vertical Divider, Horizontal Shelf, Top Panel.
"""

from pathlib import Path

from boxes import Boxes
from boxes import edges

from faxbox import config
from faxbox.config import (
    FINGER_PLAY_RELATIVE,
    BAY_LENGTH,
    BAY_X0,
    BAY_X1,
    BOTTOM_OPENING_Z0,
    BOTTOM_OPENING_Z1,
    DIVIDER_HEIGHT,
    DIVIDER_X0,
    DIVIDER_X1,
    FLOOR_TOP,
    FRONT_WALL_HEIGHT,
    FRONT_WALL_TOP,
    INTERIOR_LENGTH,
    INTERIOR_WIDTH,
    LID_SLOT_BOTTOM,
    LID_SLOT_HEIGHT,
    LID_SLOT_X_END,
    MAGNET_BOTTOM_DRAWER_Z,
    MAGNET_BOX_Y,
    MAGNET_HOLE_DIA,
    MAGNET_TOP_DRAWER_Z,
    MATERIAL_THICKNESS,
    OPENING_HEIGHT,
    OPENING_WIDTH,
    SHELF_Z0,
    TOP_OPENING_Z0,
    TOP_OPENING_Z1,
    TOP_PANEL_HOLE_Z,
    TURN_BUTTON,
    TURN_BUTTON_PIVOT_BOX_Y,
    TURN_BUTTON_PIVOT_BOX_Z,
    WALL_HEIGHT,
)
from faxbox.svglabels import enforce_reference_labels

T = MATERIAL_THICKNESS

# The "FAX MACHINE" pixel-font engraving (a 5x7 hatch-filled font drawn on
# the right wall) was REMOVED entirely on 2026-07-10 (Ben's decision, issue
# #25 open-item 1): the wall artwork from art/FACES.md supersedes it, and the
# lettering already lives inside IMG_4228's drip-graffiti art on the left
# wall. Engrave art lands via the art-integration pipeline, not drawn here.

# Divider's thickness zone midplane, expressed as a local-X coordinate on
# both the Bottom panel and the side walls (both use the same box_X - T
# mapping for their local X axis -- see build_side_wall / bottom callback).
DIVIDER_MID_LOCAL_X = (DIVIDER_X0 + DIVIDER_X1) / 2 - T

# Shelf's thickness zone midplane, in Z (used on side walls and divider).
SHELF_MID_Z = SHELF_Z0 + T / 2


class OuterShell(Boxes):
    """Outer shell: bottom, 4 walls, divider, shelf, fixed top panel."""

    def __init__(self, provider: str | None = None) -> None:
        Boxes.__init__(self)
        self.addSettingsArgs(edges.FingerJointSettings)
        # Provider abstraction (config.PROVIDERS): which cut/engrave colors
        # this instance draws with. Defaults to "nycr" (this project's
        # original hardcoded CUT_COLOR/ENGRAVE_COLOR), so an un-parameterized
        # OuterShell() is byte-for-byte identical to pre-provider-abstraction
        # behavior. BURN itself is NOT threaded through here -- it flows via
        # the --burn CLI arg in generate_shell() below, same as always.
        provider_cfg = config.PROVIDERS[config.resolve_provider(provider)]
        self.cut_color = provider_cfg["cut_color"]
        self.engrave_color = provider_cfg["engrave_color"]

    # -- pieces ---------------------------------------------------------

    def _build_bottom(self) -> None:
        """Bottom panel: INTERIOR_LENGTH x INTERIOR_WIDTH, 'f' all around,
        plus a fingerHolesAt line receiving the divider's bottom-edge
        fingers (DESIGN.md #1)."""

        def callback() -> None:
            self.fingerHolesAt(DIVIDER_MID_LOCAL_X, 0, INTERIOR_WIDTH, angle=90)

        self.rectangularWall(
            INTERIOR_LENGTH, INTERIOR_WIDTH, "ffff",
            callback=[callback, None, None, None],
            move="right", label="Bottom",
        )

    def _build_side_wall(self, mirror: bool, label: str) -> None:
        """Side wall: INTERIOR_LENGTH (local X = box X - T) x WALL_HEIGHT
        (local Y = box Z), full height (DESIGN.md #2).

        RIGHT wall (mirror=False) is the base pattern: front edge (local
        X=0) is the wall's own front; LEFT wall (mirror=True) draws the
        exact mirror image in local X (both walls are drawn exterior-face
        up, per DESIGN.md's amendment note on part #2).
        """

        def mirror_point(x: float) -> float:
            return INTERIOR_LENGTH - x

        def mirror_start(x: float, length: float) -> float:
            return INTERIOR_LENGTH - x - length

        # Front-edge compound: finger joint (mates front wall) below
        # FRONT_WALL_TOP, plain (lid-slot mouth + rail end) above it. The
        # plain portion spans the whole rail zone above the front wall,
        # WALL_HEIGHT - FRONT_WALL_TOP (this includes both the lid slot's
        # own height and the LID_RAIL_HEIGHT of solid material above it).
        front_plain_z = WALL_HEIGHT - FRONT_WALL_TOP
        front_edge_top_to_bottom = edges.CompoundEdge(
            self, ["e", "f"], [front_plain_z, FRONT_WALL_TOP])
        front_edge_bottom_to_top = edges.CompoundEdge(
            self, ["f", "e"], [FRONT_WALL_TOP, front_plain_z])
        rear_edge = self.edges["f"]  # full height, mates rear wall

        # Top edge: plain at full height for its whole length. The fixed top
        # panel joins through a fingerHolesAt line just below the top edge
        # (see callback) -- an edge-to-edge finger joint here would either
        # stand proud of the 127mm top plane or need per-segment baseline
        # offsets that CompoundEdge can't express.
        if not mirror:
            left_edge = front_edge_top_to_bottom   # index3: travels top->bottom
            right_edge = rear_edge                  # index1: travels bottom->top
        else:
            left_edge = rear_edge
            right_edge = front_edge_bottom_to_top

        def callback() -> None:
            # Bottom-panel finger-hole line (straight edge, hole line only).
            self.fingerHolesAt(0, T / 2, INTERIOR_LENGTH, angle=0)

            # Lid through-slot: closed hole whose front boundary coincides
            # with the blank's front edge -- both lines get cut, opening the
            # mouth (DESIGN.md #2).
            slot_length = LID_SLOT_X_END - T
            slot_cx = slot_length / 2
            slot_cz = LID_SLOT_BOTTOM + LID_SLOT_HEIGHT / 2
            if mirror:
                slot_cx = mirror_point(slot_cx)
            self.rectangularHole(slot_cx, slot_cz, slot_length, LID_SLOT_HEIGHT, r=0)

            # Divider finger-hole line (vertical).
            divider_x = DIVIDER_MID_LOCAL_X
            if mirror:
                divider_x = mirror_point(divider_x)
            self.fingerHolesAt(divider_x, FLOOR_TOP, DIVIDER_HEIGHT, angle=90)

            # Shelf finger-hole line (horizontal).
            shelf_x0 = BAY_X0 - T
            if mirror:
                shelf_x0 = mirror_start(shelf_x0, BAY_LENGTH)
            self.fingerHolesAt(shelf_x0, SHELF_MID_Z, BAY_LENGTH, angle=0)

            # Top-panel finger-hole line (horizontal, just below the top
            # edge; panel finger tips end flush with the exterior face).
            top_x0 = BAY_X0 - T
            if mirror:
                top_x0 = mirror_start(top_x0, BAY_LENGTH)
            self.fingerHolesAt(top_x0, TOP_PANEL_HOLE_Z, BAY_LENGTH, angle=0)

        self.rectangularWall(
            INTERIOR_LENGTH, WALL_HEIGHT,
            [self.edges["e"], right_edge, self.edges["e"], left_edge],
            callback=[callback, None, None, None],
            move="right", label=label,
        )

    def _build_front_wall(self) -> None:
        """Front wall: INTERIOR_WIDTH (local X = box Y - T) x
        FRONT_WALL_HEIGHT (local Y = box Z), Z = 0 -> FRONT_WALL_TOP
        (DESIGN.md #3).

        Also carries the sole lid-retention turn-button pivot hole
        (DESIGN.md "Retention (iteration 2)" section B, adversarial-review
        REV.B): a single M3-clearance hole on this wall's exterior face, at
        box (Y, Z) = (TURN_BUTTON_PIVOT_BOX_Y, TURN_BUTTON_PIVOT_BOX_Z). No
        mirroring needed -- there is only one front wall and only one
        button. Local X = box Y - T, same mapping the bottom-panel hole
        line above already uses; local Y = box Z directly (this wall's Z
        axis is unextended -- see test_front_wall_blank_size)."""

        def callback() -> None:
            self.fingerHolesAt(0, T / 2, INTERIOR_WIDTH, angle=0)
            pivot_local_x = TURN_BUTTON_PIVOT_BOX_Y - T
            self.hole(pivot_local_x, TURN_BUTTON_PIVOT_BOX_Z, d=TURN_BUTTON["pivot_hole_dia"])

        self.rectangularWall(
            INTERIOR_WIDTH, FRONT_WALL_HEIGHT, "eFeF",
            callback=[callback, None, None, None],
            move="right", label="Front Wall",
        )

    def _build_rear_wall(self) -> None:
        """Rear wall: INTERIOR_WIDTH (local X = box Y - T) x WALL_HEIGHT
        (local Y = box Z), full height, two drawer openings (DESIGN.md #4)."""

        def callback() -> None:
            self.fingerHolesAt(0, T / 2, INTERIOR_WIDTH, angle=0)
            # Top-panel finger-hole line (rear edge of the panel).
            self.fingerHolesAt(0, TOP_PANEL_HOLE_Z, INTERIOR_WIDTH, angle=0)

            opening_cx = INTERIOR_WIDTH / 2
            bottom_cz = (BOTTOM_OPENING_Z0 + BOTTOM_OPENING_Z1) / 2
            top_cz = (TOP_OPENING_Z0 + TOP_OPENING_Z1) / 2
            self.rectangularHole(opening_cx, bottom_cz, OPENING_WIDTH, OPENING_HEIGHT, r=0)
            self.rectangularHole(opening_cx, top_cz, OPENING_WIDTH, OPENING_HEIGHT, r=0)

        self.rectangularWall(
            INTERIOR_WIDTH, WALL_HEIGHT, "eFeF",
            callback=[callback, None, None, None],
            move="right", label="Rear Wall",
        )

    def _build_divider(self) -> None:
        """Vertical divider: INTERIOR_WIDTH (local X = box Y) x
        DIVIDER_HEIGHT (local Y = box Z - FLOOR_TOP), fully captive on all
        four edges (DESIGN.md #5). Callback adds the shelf's front-edge
        finger-hole line (DESIGN.md #6) plus the two drawer-magnet holes
        (DESIGN.md "Retention (iteration 2)"): one per drawer, coaxial with
        that drawer's Back-wall magnet hole at the drawer's fully-closed
        position. Both share the same local X (MAGNET_BOX_Y - T, box Y is
        the same for both drawers by design); Z differs per drawer since
        the bottom drawer rests on the bay floor and the top drawer rests
        on the shelf."""

        def callback() -> None:
            shelf_mid_local_y = SHELF_MID_Z - FLOOR_TOP
            self.fingerHolesAt(0, shelf_mid_local_y, INTERIOR_WIDTH, angle=0)

            magnet_local_x = MAGNET_BOX_Y - T
            self.hole(magnet_local_x, MAGNET_BOTTOM_DRAWER_Z - FLOOR_TOP, d=MAGNET_HOLE_DIA)
            self.hole(magnet_local_x, MAGNET_TOP_DRAWER_Z - FLOOR_TOP, d=MAGNET_HOLE_DIA)

        self.rectangularWall(
            INTERIOR_WIDTH, DIVIDER_HEIGHT, "ffff",
            callback=[callback, None, None, None],
            move="right", label="Vertical Divider",
        )

    def _build_shelf(self) -> None:
        """Horizontal shelf: BAY_LENGTH (local X = box X - BAY_X0) x
        INTERIOR_WIDTH (local Y = box Y), side edges into the side walls,
        front edge into the divider, rear edge plain (DESIGN.md #6)."""
        self.rectangularWall(
            BAY_LENGTH, INTERIOR_WIDTH, ["f", "e", "f", "f"],
            move="right", label="Horizontal Shelf",
        )

    def _build_top_panel(self) -> None:
        """Fixed top panel over the drawer bay: nominal X = BAY_X1 -
        DIVIDER_X0 (local X = box X - DIVIDER_X0) x INTERIOR_WIDTH (local
        Y = box Y). Side/rear edges finger-joint the walls; front edge is
        plain, with an interior finger-hole line receiving the divider's
        top-edge fingers (DESIGN.md #7).

        The side edges are COMPOUND: plain over the divider cover strip
        (local X 0..T), fingers only over the bay span (T..T+BAY_LENGTH).
        The walls' top-panel hole rows are generated for BAY_LENGTH starting
        at BAY_X0, and Boxes.py lays fingers out per-segment -- fingering
        the full 222.25mm edge would produce 17 fingers misaligned with the
        16 wall holes by up to ~8mm (assembly-impossible; caught in red-team
        review)."""
        nominal_x = BAY_X1 - DIVIDER_X0

        # Edge index travel: bottom (index0) runs local x 0->max, top
        # (index2) runs back max->0, so the compound segment order flips.
        side_edge_fwd = edges.CompoundEdge(self, ["e", "f"], [T, BAY_LENGTH])
        side_edge_rev = edges.CompoundEdge(self, ["f", "e"], [BAY_LENGTH, T])

        def callback() -> None:
            self.fingerHolesAt(T / 2, 0, INTERIOR_WIDTH, angle=90)

        self.rectangularWall(
            nominal_x, INTERIOR_WIDTH,
            [side_edge_fwd, self.edges["f"], side_edge_rev, self.edges["e"]],
            callback=[callback, None, None, None],
            move="right", label="Top Panel",
        )

    def render(self) -> None:
        """Render all 8 shell pieces, laid out in a single row (move=
        'right' throughout) so bounding boxes never overlap."""
        self.set_source_color(self.cut_color)

        self._build_bottom()
        self._build_side_wall(mirror=False, label="Right Wall")
        self._build_side_wall(mirror=True, label="Left Wall")
        self._build_front_wall()
        self._build_rear_wall()
        self._build_divider()
        self._build_shelf()
        self._build_top_panel()


def generate_shell(provider: str | None = None) -> Path:
    """Generate outer shell SVG file.

    `provider` selects a faxbox.config.PROVIDERS entry (falls back to the
    FAXBOX_PROVIDER env var, then "nycr" -- see config.resolve_provider).
    Passing nothing reproduces this project's original behavior exactly:
    output/outer_shell.svg, BURN=0.08, blue cut / red engrave.
    """
    name = config.resolve_provider(provider)
    provider_cfg = config.PROVIDERS[name]
    output_path = Path(provider_cfg["output_dir"])
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / "outer_shell.svg"

    shell = OuterShell(provider=name)
    shell.parseArgs([
        "--output", str(output_file),
        "--thickness", str(MATERIAL_THICKNESS),
        "--burn", str(provider_cfg["burn"]),
        "--reference", "0",
        "--FingerJoint_play", str(FINGER_PLAY_RELATIVE),
    ])

    shell.open()
    shell.render()
    data = shell.close()

    with open(output_file, "wb") as f:
        f.write(data.getvalue())

    # Boxes.py's own move(label=...) draws each wall's part name in the
    # same red used for real engraves (see faxbox.svglabels module
    # docstring) -- neutralize before this file is ever considered
    # laser-ready.
    enforce_reference_labels(output_file)

    print(f"Generated outer shell SVG: {output_file.absolute()}")
    print(f"  Interior dimensions: {INTERIOR_LENGTH}mm x {INTERIOR_WIDTH}mm")
    print(f"  Material thickness: {MATERIAL_THICKNESS}mm")
    return output_file


if __name__ == "__main__":
    generate_shell()
