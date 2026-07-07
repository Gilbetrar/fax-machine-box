"""Single source of truth for fax machine box dimensions (mm).

Implements DESIGN.md — if a number here disagrees with DESIGN.md, DESIGN.md
wins. Everything below is either a SPEC.md external target, a fit policy
constant, or derived. Do not add independent magic numbers.

Coordinate convention (DESIGN.md): origin at the exterior front-left-bottom
corner. X+ rearward (length, 12"), Y+ rightward (width, 6.5"), Z+ up (5").
"""

import math

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

# --- Retention (iteration 2, issue #20) --------------------------------------
# Two in-plane laser-cut cantilever spring detents, adapted from Boxes.py's
# own precedents (boxes/edges.py SlideOnLidSettings/LidRight: spring finger
# length min(6t, ...), 30 degree tip ramp, catch-hole depth 0.4t; boxes/
# generators/dinrailbox.py: a cantilever tongue with a nub cut directly into
# a panel). We adapt the *proportions* of those precedents, not their play
# values (they assume ~0.3mm clearance; this project's slide clearances are
# deliberately looser, see SLIDE_CLEARANCE / LID_SLOT_VERTICAL_CLEARANCE
# above) -- see DESIGN.md's "Retention (iteration 2)" section for the full
# derivation and coordinates.
#
# Mechanism A (side walls): a cantilever cut into the wall material just
# below the lid slot floor, with a ramped nub poking up through the floor
# into the slot cavity -- the lid's closed position carries a matching
# edge-open notch that the nub pops into.
# Mechanism B (drawer faceplates): a cantilever cut near each Y side edge of
# the faceplate, with a ramped nub poking out sideways past the faceplate's
# own edge -- it snaps past the rear-wall opening's side edge on close.

# Nub engagement / interference depths (the two values Ben tunes against the
# retention coupon before cutting real parts -- see calibration.py).
LID_DETENT_ENGAGE = 1.5        # nub rise above the lid slot floor (mm); must
                                # exceed LID_SLOT_VERTICAL_CLEARANCE (0.8) so
                                # the nub stays engaged when the lid shifts
                                # within its own vertical play.
DRAWER_DETENT_PROTRUDE = 1.2   # nub protrusion beyond the faceplate edge
                                # (mm); 0.45mm interference past the 0.75mm
                                # FACEPLATE_REVEAL when the faceplate is
                                # centered in its opening.

# Shared cantilever proportions (both mechanisms use the same beam stock;
# only the nub height/protrusion differs per mechanism above).
DETENT_BEAM_LENGTH = 18.0       # cantilever length (mm)
DETENT_BEAM_WIDTH = 2.5         # beam cross-section width in the flex
                                # direction (mm) -- the dimension that bends
DETENT_ROOT_FILLET = 1.0        # minimum root fillet radius (mm)
DETENT_CLEARANCE = 2.5          # clearance behind/below the beam so it can
                                # deflect its own engagement depth without
                                # bottoming out (mm)
DETENT_RAMP_DEG = 30.0          # nub ramp angle from the beam's rest plane,
                                # matching Boxes.py LidRight's barb angle `a`
DETENT_SEVER_WIDTH = 1.0        # width of the release cut that frees the
                                # beam's tip from the surrounding material
                                # (mm) -- well above kerf so it fully parts
DETENT_NUB_TOP_WIDTH = 2.5      # flat land at the nub's tip (mm); a flat
                                # top (rather than a knife edge) avoids the
                                # stress-concentrating point a bare 30 degree
                                # wedge would leave in cross-grain plywood

# --- Mechanism A: side-wall lid detent ---------------------------------------
# Nub centered on the beam (LID_DETENT_X +/- half the beam length); the free
# (severed) end sits toward the wall's front (mouth) edge, the root end is
# solid, deeper into the wall -- clear of both the front-edge finger joints
# (below LID_SLOT_BOTTOM only) and the divider hole line (79.375-82.55).
LID_DETENT_X = 20.0             # box X, nub center (both walls; the mirror
                                 # convention in shell_generator.py lands
                                 # both walls' nubs at this same real box X)
LID_DETENT_TIP_X = LID_DETENT_X - DETENT_BEAM_LENGTH / 2   # 11.0, free/severed end
LID_DETENT_ROOT_X = LID_DETENT_X + DETENT_BEAM_LENGTH / 2  # 29.0, solid anchor end

LID_DETENT_RAMP_RUN = LID_DETENT_ENGAGE / math.tan(math.radians(DETENT_RAMP_DEG))
LID_DETENT_NUB_BASE_WIDTH = DETENT_NUB_TOP_WIDTH + 2 * LID_DETENT_RAMP_RUN  # ~7.7

LID_DETENT_NUB_TOP_Z = LID_SLOT_BOTTOM + LID_DETENT_ENGAGE          # 119.525
LID_DETENT_BEAM_BOTTOM_Z = LID_SLOT_BOTTOM - DETENT_BEAM_WIDTH      # 115.525
LID_DETENT_CAVITY_BOTTOM_Z = LID_DETENT_BEAM_BOTTOM_Z - DETENT_CLEARANCE  # 113.025

# Mating notch in the lid's side edges (DESIGN.md #8: closed lid front edge
# sits at box X = LID_SLOT_X_END - SLIDING_LID["length"], "~0.4mm shy" of the
# front face -- lid-local X = box X - that offset).
LID_CLOSED_FRONT_X = LID_SLOT_X_END - SLIDING_LID["length"]        # 0.375
LID_NOTCH_X = LID_DETENT_X - LID_CLOSED_FRONT_X                    # 19.625, lid-local
LID_NOTCH_WIDTH = LID_DETENT_NUB_BASE_WIDTH + 1.0                  # ~8.7
LID_NOTCH_DEPTH = 3.0                # >= LID lid-slot engagement (2.425) + margin
LID_NOTCH_CHAMFER = 1.0              # corner ease at the notch mouth (mm)

# --- Mechanism B: drawer faceplate detent ------------------------------------
# Nub Z-center at the faceplate's mid-height -- beside (never intersecting)
# the Y-centered grip slot, which sits ~60mm away in Y. Root end toward the
# bottom edge, free/severed (tip) end toward the top -- an arbitrary but
# consistent choice; the grip slot's Y-separation is what actually keeps the
# two features apart, not the Z split.
DRAWER_DETENT_Z = FACEPLATE["height"] / 2                          # 26.75
DRAWER_DETENT_ROOT_Z = DRAWER_DETENT_Z - DETENT_BEAM_LENGTH / 2    # 17.75
DRAWER_DETENT_TIP_Z = DRAWER_DETENT_Z + DETENT_BEAM_LENGTH / 2     # 35.75

DRAWER_DETENT_RAMP_RUN = DRAWER_DETENT_PROTRUDE / math.tan(math.radians(DETENT_RAMP_DEG))
DRAWER_DETENT_NUB_BASE_WIDTH = DETENT_NUB_TOP_WIDTH + 2 * DRAWER_DETENT_RAMP_RUN  # ~6.66

# Faceplate's true drawn footprint, including both nubs (DESIGN.md #9,
# amended): the outer boundary is drawn offset by DRAWER_DETENT_PROTRUDE so
# the leftmost nub tip sits at local x=0 (see generate_drawers.py).
FACEPLATE_DRAWN_WIDTH = FACEPLATE["width"] + 2 * DRAWER_DETENT_PROTRUDE  # 153.3

# --- Output ------------------------------------------------------------------

OUTPUT_DIR = "output"
