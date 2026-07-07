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

from faxbox.config import (
    BAY_LENGTH,
    BAY_X0,
    BAY_X1,
    BOTTOM_OPENING_Z0,
    BOTTOM_OPENING_Z1,
    BURN,
    CUT_COLOR,
    DIVIDER_HEIGHT,
    DIVIDER_X0,
    DIVIDER_X1,
    ENGRAVE_CENTER,
    ENGRAVE_COLOR,
    ENGRAVE_FONT_SPACING,
    ENGRAVE_PIXEL_SIZE,
    ENGRAVE_TEXT,
    FLOOR_TOP,
    FRONT_WALL_HEIGHT,
    FRONT_WALL_TOP,
    INTERIOR_LENGTH,
    INTERIOR_WIDTH,
    LID_SLOT_BOTTOM,
    LID_SLOT_HEIGHT,
    LID_SLOT_X_END,
    MATERIAL_THICKNESS,
    OPENING_HEIGHT,
    OPENING_WIDTH,
    OUTPUT_DIR,
    SHELF_Z0,
    TOP_OPENING_Z0,
    TOP_OPENING_Z1,
    TOP_PANEL_HOLE_Z,
    WALL_HEIGHT,
)

T = MATERIAL_THICKNESS

# Pixel font definitions: 5 columns x 7 rows
PIXEL_FONT = {
    'F': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6),
          (1, 0), (2, 0), (3, 0), (4, 0),
          (1, 3), (2, 3), (3, 3)],
    'A': [(0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6),
          (1, 0), (2, 0), (3, 0),
          (4, 1), (4, 2), (4, 3), (4, 4), (4, 5), (4, 6),
          (1, 3), (2, 3), (3, 3)],
    'X': [(0, 0), (0, 1), (4, 0), (4, 1),
          (1, 2), (3, 2),
          (2, 3),
          (1, 4), (3, 4),
          (0, 5), (0, 6), (4, 5), (4, 6)],
    'M': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6),
          (1, 1), (2, 2), (3, 1),
          (4, 0), (4, 1), (4, 2), (4, 3), (4, 4), (4, 5), (4, 6)],
    'C': [(1, 0), (2, 0), (3, 0), (4, 0),
          (0, 1), (0, 2), (0, 3), (0, 4), (0, 5),
          (1, 6), (2, 6), (3, 6), (4, 6)],
    'H': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6),
          (1, 3), (2, 3), (3, 3),
          (4, 0), (4, 1), (4, 2), (4, 3), (4, 4), (4, 5), (4, 6)],
    'I': [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0),
          (2, 1), (2, 2), (2, 3), (2, 4), (2, 5),
          (0, 6), (1, 6), (2, 6), (3, 6), (4, 6)],
    'N': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6),
          (1, 1), (2, 2), (3, 3),
          (4, 0), (4, 1), (4, 2), (4, 3), (4, 4), (4, 5), (4, 6)],
    'E': [(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), (0, 5), (0, 6),
          (1, 0), (2, 0), (3, 0), (4, 0),
          (1, 3), (2, 3), (3, 3),
          (1, 6), (2, 6), (3, 6), (4, 6)],
    ' ': [],
}

# Divider's thickness zone midplane, expressed as a local-X coordinate on
# both the Bottom panel and the side walls (both use the same box_X - T
# mapping for their local X axis -- see build_side_wall / bottom callback).
DIVIDER_MID_LOCAL_X = (DIVIDER_X0 + DIVIDER_X1) / 2 - T

# Shelf's thickness zone midplane, in Z (used on side walls and divider).
SHELF_MID_Z = SHELF_Z0 + T / 2


class OuterShell(Boxes):
    """Outer shell: bottom, 4 walls, divider, shelf, fixed top panel."""

    def __init__(self) -> None:
        Boxes.__init__(self)
        self.addSettingsArgs(edges.FingerJointSettings)

    # -- pixel-font engraving (ctx.fill() is not implemented by Boxes.py;
    # engrave by stroking closed pixel-square paths in ENGRAVE_COLOR) -------

    def draw_pixel_char(self, char: str, x: float, y: float, pixel_size: float) -> float:
        """Draw a single character using the pixel font. Returns advance width."""
        if char not in PIXEL_FONT:
            return pixel_size * 5 + ENGRAVE_FONT_SPACING
        pixels = PIXEL_FONT[char]
        if not pixels:
            return pixel_size * 5 + ENGRAVE_FONT_SPACING
        pixel_cell = pixel_size * 0.85
        for col, row in pixels:
            px = x + col * pixel_size + (pixel_size - pixel_cell) / 2
            py = y + (6 - row) * pixel_size + (pixel_size - pixel_cell) / 2
            self.ctx.move_to(px, py)
            self.ctx.line_to(px + pixel_cell, py)
            self.ctx.line_to(px + pixel_cell, py + pixel_cell)
            self.ctx.line_to(px, py + pixel_cell)
            self.ctx.line_to(px, py)
            self.ctx.stroke()
        return pixel_size * 5 + ENGRAVE_FONT_SPACING

    def draw_pixel_text(self, text: str, x: float, y: float, pixel_size: float = ENGRAVE_PIXEL_SIZE) -> None:
        """Draw text using the pixel font in the engraving (red) color."""
        self.set_source_color(ENGRAVE_COLOR)
        current_x = x
        for char in text.upper():
            width = self.draw_pixel_char(char, current_x, y, pixel_size)
            current_x += width
        self.set_source_color(CUT_COLOR)

    def _engrave_fax_machine(self) -> None:
        """"FAX MACHINE" pixel text, centered per DESIGN.md's ENGRAVE_CENTER
        (right side wall exterior only)."""
        pixel_size = ENGRAVE_PIXEL_SIZE
        char_width = 5 * pixel_size + ENGRAVE_FONT_SPACING
        text_width = len(ENGRAVE_TEXT) * char_width - ENGRAVE_FONT_SPACING
        text_height = 7 * pixel_size
        center_x = ENGRAVE_CENTER["x"] - T  # box X -> side wall local X
        center_z = ENGRAVE_CENTER["z"]
        text_x = center_x - text_width / 2
        text_y = center_z - text_height / 2
        self.draw_pixel_text(ENGRAVE_TEXT, text_x, text_y, pixel_size)

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

    def _build_side_wall(self, mirror: bool, label: str, engrave: bool) -> None:
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

            if engrave:
                self._engrave_fax_machine()

        self.rectangularWall(
            INTERIOR_LENGTH, WALL_HEIGHT,
            [self.edges["e"], right_edge, self.edges["e"], left_edge],
            callback=[callback, None, None, None],
            move="right", label=label,
        )

    def _build_front_wall(self) -> None:
        """Front wall: INTERIOR_WIDTH (local X = box Y - T) x
        FRONT_WALL_HEIGHT (local Y = box Z), Z = 0 -> FRONT_WALL_TOP
        (DESIGN.md #3)."""

        def callback() -> None:
            self.fingerHolesAt(0, T / 2, INTERIOR_WIDTH, angle=0)

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
        finger-hole line (DESIGN.md #6)."""

        def callback() -> None:
            shelf_mid_local_y = SHELF_MID_Z - FLOOR_TOP
            self.fingerHolesAt(0, shelf_mid_local_y, INTERIOR_WIDTH, angle=0)

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
        top-edge fingers (DESIGN.md #7)."""
        nominal_x = BAY_X1 - DIVIDER_X0

        def callback() -> None:
            self.fingerHolesAt(T / 2, 0, INTERIOR_WIDTH, angle=90)

        self.rectangularWall(
            nominal_x, INTERIOR_WIDTH, ["f", "f", "f", "e"],
            callback=[callback, None, None, None],
            move="right", label="Top Panel",
        )

    def render(self) -> None:
        """Render all 8 shell pieces, laid out in a single row (move=
        'right' throughout) so bounding boxes never overlap."""
        self.set_source_color(CUT_COLOR)

        self._build_bottom()
        self._build_side_wall(mirror=False, label="Right Wall", engrave=True)
        self._build_side_wall(mirror=True, label="Left Wall", engrave=False)
        self._build_front_wall()
        self._build_rear_wall()
        self._build_divider()
        self._build_shelf()
        self._build_top_panel()


def generate_shell() -> Path:
    """Generate outer shell SVG file."""
    output_path = Path(OUTPUT_DIR)
    output_path.mkdir(parents=True, exist_ok=True)
    output_file = output_path / "outer_shell.svg"

    shell = OuterShell()
    shell.parseArgs([
        "--output", str(output_file),
        "--thickness", str(MATERIAL_THICKNESS),
        "--burn", str(BURN),
        "--reference", "0",
    ])

    shell.open()
    shell.render()
    data = shell.close()

    with open(output_file, "wb") as f:
        f.write(data.getvalue())

    print(f"Generated outer shell SVG: {output_file.absolute()}")
    print(f"  Interior dimensions: {INTERIOR_LENGTH}mm x {INTERIOR_WIDTH}mm")
    print(f"  Material thickness: {MATERIAL_THICKNESS}mm")
    return output_file


if __name__ == "__main__":
    generate_shell()
