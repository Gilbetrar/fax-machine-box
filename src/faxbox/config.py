"""Single source of truth for fax machine box dimensions (mm).

Implements DESIGN.md — if a number here disagrees with DESIGN.md, DESIGN.md
wins. Everything below is either a SPEC.md external target, a fit policy
constant, or derived. Do not add independent magic numbers.

Coordinate convention (DESIGN.md): origin at the exterior front-left-bottom
corner. X+ rearward (length, 12"), Y+ rightward (width, 6.5"), Z+ up (5").
"""

# --- Material & laser -------------------------------------------------------

MATERIAL_THICKNESS = 3.175  # 1/8" plywood, uniform for ALL parts (SPEC)
T = MATERIAL_THICKNESS

# Boxes.py burn = kerf compensation. Starting value for 1/8" ply on a CO2
# laser; calibrate with a test cut at NYC Resistor before the real run.
BURN = 0.08

# Finger-joint play in MM: widens finger holes/slots so joints still
# assemble when the ply runs thick (nominal 3.175 stock commonly measures
# 3.0-3.4). Calibrate together with BURN via the kerf coupon.
# CAUTION: Boxes.py's FingerJointSettings "play" is RELATIVE (multiples of
# thickness), so generators must pass FINGER_PLAY_RELATIVE, never this raw
# mm value (0.1 passed raw silently becomes 0.3175mm — red-team pass-2 catch).
FINGER_PLAY = 0.1
FINGER_PLAY_RELATIVE = FINGER_PLAY / MATERIAL_THICKNESS

# --- Fit policy (DESIGN.md "Clearance summary") -----------------------------

SLIDE_CLEARANCE = 1.5        # SPEC: min 1/16" play on sliding interfaces
LID_SLOT_VERTICAL_CLEARANCE = 0.8  # documented deviation, see DESIGN.md
FACEPLATE_REVEAL = 0.75      # flush faceplate gap per side in its opening
MIN_WEB = 3.0                # thinnest allowed structural web in a wall

# --- SPEC external envelope -------------------------------------------------

SHELL_EXT = {
    "length": 304.8,  # X, 12"
    "width": 165.1,   # Y, 6.5"
    "height": 127.0,  # Z, 5"
}

PAPER_COMPARTMENT_LENGTH = 76.2  # X interior span of the paper compartment (3")

# --- Derived interior geometry ----------------------------------------------

INTERIOR_LENGTH = SHELL_EXT["length"] - 2 * T   # 298.45
INTERIOR_WIDTH = SHELL_EXT["width"] - 2 * T     # 158.75

# Walls run full height; the bottom panel is inset between them (standard
# finger-box construction — see DESIGN.md amendment note).
WALL_Z0 = 0.0
WALL_HEIGHT = SHELL_EXT["height"]                # 127.0
FLOOR_TOP = T                                    # 3.175, top of inset bottom panel

# Longitudinal layout (X)
DIVIDER_X0 = T + PAPER_COMPARTMENT_LENGTH        # 79.375
DIVIDER_X1 = DIVIDER_X0 + T                      # 82.55
BAY_X0 = DIVIDER_X1                              # 82.55
BAY_X1 = SHELL_EXT["length"] - T                 # 301.625
BAY_LENGTH = BAY_X1 - BAY_X0                     # 219.075

# Sliding lid slot (through both side walls, open at the front edge)
LID_RAIL_HEIGHT = 5.0                            # material left above the slot
LID_SLOT_TOP = SHELL_EXT["height"] - LID_RAIL_HEIGHT      # 122.0
LID_SLOT_HEIGHT = T + LID_SLOT_VERTICAL_CLEARANCE         # 3.975
LID_SLOT_BOTTOM = LID_SLOT_TOP - LID_SLOT_HEIGHT          # 118.025
LID_SLOT_X_END = DIVIDER_X0    # slot runs X 3.175 -> 79.375, open at front edge

FRONT_WALL_TOP = LID_SLOT_BOTTOM                 # lid slides over the front wall
FRONT_WALL_HEIGHT = FRONT_WALL_TOP - WALL_Z0     # 118.025

# Fixed top panel over the drawer bay
TOP_PANEL_Z0 = SHELL_EXT["height"] - T           # 123.825
TOP_PANEL_HOLE_Z = TOP_PANEL_Z0 + T / 2          # 125.4125, hole-line midplane in walls
DIVIDER_TOP = TOP_PANEL_Z0                       # divider supports the top panel
DIVIDER_HEIGHT = DIVIDER_TOP - FLOOR_TOP         # 120.65

# Drawer bay vertical split
BAY_INTERIOR_HEIGHT = TOP_PANEL_Z0 - FLOOR_TOP   # 120.65
DRAWER_SLOT_HEIGHT = (BAY_INTERIOR_HEIGHT - T) / 2        # 58.7375
SHELF_Z0 = FLOOR_TOP + DRAWER_SLOT_HEIGHT        # 61.9125
SHELF_Z1 = SHELF_Z0 + T                          # 65.0875

# --- Rear wall drawer openings ----------------------------------------------

OPENING_WIDTH = INTERIOR_WIDTH - 2 * T           # 152.4 (leaves T webs at corners)
OPENING_HEIGHT = 55.0
# Sill-free: each opening's bottom edge is exactly its slot's floor.
BOTTOM_OPENING_Z0 = FLOOR_TOP                    # 3.175
BOTTOM_OPENING_Z1 = BOTTOM_OPENING_Z0 + OPENING_HEIGHT    # 58.175
TOP_OPENING_Z0 = SHELF_Z1                        # 65.0875
TOP_OPENING_Z1 = TOP_OPENING_Z0 + OPENING_HEIGHT          # 120.0875

# --- Drawers (2x identical, 6 pieces each) ----------------------------------

DRAWER_BODY = {   # external
    "width": 149.0,    # Y
    "length": 218.6,   # X (pull direction); bay gap 0.475 -- the divider is
                       # the drawer's in-stop (the inset faceplate can't stop
                       # against the rear wall). Closed, the faceplate sits
                       # recessed by the 0.475 slide gap -- near-flush; true
                       # flush and slide clearance are mutually exclusive.
    "height": 53.5,    # Z
}

FACEPLATE = {
    "width": OPENING_WIDTH - 2 * FACEPLATE_REVEAL,    # 150.9
    "height": OPENING_HEIGHT - 2 * FACEPLATE_REVEAL,  # 53.5
}

# Closed grip slot cut through BOTH faceplate and body front, aligned
# (DESIGN.md: 30 x 15 r7.5, slot top 8.0 below the part top edge).
DRAWER_GRIP_SLOT = {"width": 30.0, "height": 15.0, "radius": 7.5,
                    "top_below_edge": 8.0}

# --- Sliding lid -------------------------------------------------------------

SLIDING_LID = {
    "length": 79.0,                                   # X
    "width": SHELL_EXT["width"] - SLIDE_CLEARANCE,    # 163.6 (rides in through-slots)
}
LID_GRIP_SLOT = {"width": 30.0, "height": 10.0, "radius": 5.0,
                 # 25.0 keeps a 10mm ligament between slot and front edge
                 # (15.0 left ~0.2mm -- it would have broken into a notch)
                 "center_from_front": 25.0}

# --- Engraving ---------------------------------------------------------------

ENGRAVE_COLOR = [1.0, 0.0, 0.0]   # red = engrave
CUT_COLOR = [0.0, 0.0, 1.0]       # blue = cut
ENGRAVE_TEXT = "FAX MACHINE"
ENGRAVE_PIXEL_SIZE = 4.0          # 5x7 pixel font cell size
ENGRAVE_FONT_SPACING = 2.0        # gap between letters
ENGRAVE_CENTER = {"x": SHELL_EXT["length"] / 2, "z": 63.5}  # right wall exterior

# --- Output ------------------------------------------------------------------

OUTPUT_DIR = "output"
