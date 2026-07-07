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

# --- Retention (iteration 3, issue #20 red-team) -----------------------------
# Two in-plane laser-cut cantilever spring detents. Mechanism A (side-wall
# lid detent) is unchanged in kinematics from iteration 2, only re-tuned for
# strain (FIX2). Mechanism B (drawer retention) is a NEW mechanism replacing
# iteration 2's faceplate detent, which red-team review found geometrically
# impossible (a Y-Z faceplate can't cam against drawer travel along X --
# square interference, not a ramp). See DESIGN.md's "Retention (iteration 3)"
# section for the full derivation, kinematics, and strain numbers.
#
# Mechanism A (side walls): a cantilever cut into the wall material just
# below the lid slot floor, with a ramped nub poking up through the floor
# into the slot cavity -- the lid's closed position carries a matching
# edge-open notch that the nub pops into.
# Mechanism B (drawer sides): a cantilever cut into EACH drawer side wall
# (an X-Z part -- its plane contains both the travel axis X and the
# deflection axis Z, so the ramps genuinely cam), nub on the free end
# protruding DOWN below the side's bottom edge. On insertion the nub cams up
# over the rear-wall opening's own sill web, rides deflected along the floor
# (bottom drawer) / shelf (top drawer), and drops into a catch hole cut
# through that panel at the closed position.

# Nub engagement / interference depths (the two values Ben tunes against the
# retention coupon before cutting real parts -- see calibration.py).
LID_DETENT_ENGAGE = 1.5        # nub rise above the lid slot floor (mm); must
                                # exceed LID_SLOT_VERTICAL_CLEARANCE (0.8) so
                                # the nub stays engaged when the lid shifts
                                # within its own vertical play.
DRAWER_DETENT_ENGAGE = 2.2     # nub protrusion below the drawer side wall's
                                # bottom edge (mm); exceeds the drawer's
                                # 1.5mm opening vertical clearance by 0.7mm
                                # so the nub stays engaged at worst-case
                                # drawer lift within that clearance.

# Shared cantilever proportions (both mechanisms use the same beam stock;
# only the nub height/protrusion and beam span differ per mechanism below).
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
DETENT_SEVER_CLEARANCE = 1.5    # gap kept between a nub's own (ramped) base
                                # edge and its release/sever cut, so the
                                # sever cut cannot undercut the nub's own
                                # base and leave it bridged to the fixed
                                # material on its outward side (verified
                                # empirically against the pre-fix wall
                                # geometry: the ORIGINAL nub-mid-beam design
                                # already relied on exactly this separation,
                                # just via a much larger, accidental gap;
                                # see also DESIGN.md's "Retention" section).


def _ramp_run(rise: float) -> float:
    return rise / math.tan(math.radians(DETENT_RAMP_DEG))


def _nub_base_width(rise: float) -> float:
    return DETENT_NUB_TOP_WIDTH + 2 * _ramp_run(rise)


# --- Mechanism A: side-wall lid detent ---------------------------------------
# The nub sits at the beam's FREE end (FIX2, red-team pass 2: the previous
# revision put the nub mid-beam at X=20 with root at X=29, a 9mm root-to-nub
# span giving eps~6.9% -- above plywood's ~1.5-2% crack threshold). Nub
# position (LID_DETENT_X) is UNCHANGED so the lid notch position is
# unaffected; the beam is lengthened and re-anchored so the root sits
# LID_DETENT_NUB_TO_ROOT_SPAN away from the nub, and the sever cut (the
# beam's free/tip end) sits DETENT_SEVER_CLEARANCE beyond the nub's own base
# -- close to the nub (so root-to-nub, the strain-relevant span, is nearly
# the whole beam) but not so close that the sever cut undercuts the nub's
# own base and leaves it bridged to the fixed material outward of it.
LID_DETENT_X = 20.0             # box X, nub center (both walls; the mirror
                                 # convention in shell_generator.py lands
                                 # both walls' nubs at this same real box X)
LID_DETENT_NUB_TO_ROOT_SPAN = 22.0   # root-to-nub span (mm); eps ~= 1.16%
                                      # at DETENT_BEAM_WIDTH=2.5,
                                      # LID_DETENT_ENGAGE=1.5 (see DESIGN.md)

LID_DETENT_NUB_BASE_WIDTH = _nub_base_width(LID_DETENT_ENGAGE)   # ~7.70

LID_DETENT_TIP_X = LID_DETENT_X - LID_DETENT_NUB_BASE_WIDTH / 2 - DETENT_SEVER_CLEARANCE  # ~14.65, free/severed end
LID_DETENT_ROOT_X = LID_DETENT_X + LID_DETENT_NUB_TO_ROOT_SPAN                            # 42.0, solid anchor end

LID_DETENT_NUB_TOP_Z = LID_SLOT_BOTTOM + LID_DETENT_ENGAGE          # 119.525
LID_DETENT_BEAM_BOTTOM_Z = LID_SLOT_BOTTOM - DETENT_BEAM_WIDTH      # 115.525
LID_DETENT_CAVITY_BOTTOM_Z = LID_DETENT_BEAM_BOTTOM_Z - DETENT_CLEARANCE  # 113.025

# Mating notch in the lid's side edges (DESIGN.md #8: closed lid front edge
# sits at box X = LID_SLOT_X_END - SLIDING_LID["length"], "~0.4mm shy" of the
# front face -- lid-local X = box X - that offset).
LID_CLOSED_FRONT_X = LID_SLOT_X_END - SLIDING_LID["length"]        # 0.375
LID_NOTCH_X = LID_DETENT_X - LID_CLOSED_FRONT_X                    # 19.625, lid-local
LID_NOTCH_WIDTH = LID_DETENT_NUB_BASE_WIDTH + 1.0                  # ~8.7
LID_NOTCH_DEPTH = 3.5                # >= LID lid-slot engagement (2.425) + margin;
                                      # bumped from 3.0 (FIX3, burn consistency):
                                      # once the notch is drawn shrunk-by-BURN
                                      # (so its AS-CUT depth matches nominal
                                      # instead of drifting with BURN), 3.0 left
                                      # only ~0.075mm of real margin over the
                                      # 2.925 requirement -- less than BURN
                                      # itself could erase. 3.5 restores a real
                                      # margin regardless of BURN's exact value.
LID_NOTCH_CHAMFER = 1.0              # corner ease at the notch mouth (mm)

# --- Mechanism B: drawer side-wall flexure (iteration 3, issue #20) ----------
# Cut into EACH drawer side wall (Left Side, Right Side -- both, per drawer),
# near the FRONT (faceplate) end. Convention (this project's own choice,
# since both ends finger-joint identically to Front/Back and are otherwise
# symmetric): drawer-local x=0 is the end assembled against the Front panel
# (the faceplate end); x=BODY_INTERIOR_LENGTH is the Back-panel end. This
# means each side panel is no longer front/back-symmetric once cut, and must
# be assembled with its flexure end toward the Front panel -- flagged
# explicitly here and in DESIGN.md/README since it's a new assembly
# constraint the pre-iteration-3 parts didn't have.
#
# Beam sizing by strain (FIX1): eps = 3*w*delta/(2*L^2), w=DETENT_BEAM_WIDTH,
# delta=DRAWER_DETENT_ENGAGE. Solving eps<=1.5% for L at w=2.5, delta=2.2
# gives L >= ~23.45mm; DRAWER_DETENT_NUB_TO_ROOT_SPAN=26 gives eps~=1.22%,
# a real margin below the ~1.5-2% plywood cracking threshold.
DRAWER_DETENT_NUB_TO_ROOT_SPAN = 26.0

DRAWER_DETENT_NUB_BASE_WIDTH = _nub_base_width(DRAWER_DETENT_ENGAGE)  # ~10.12

# Nub position (drawer-local X, front/faceplate end): far enough from the
# front finger joints (>=15mm clear, per issue instructions) even after
# backing out DETENT_SEVER_CLEARANCE + the nub's own half-base for the sever
# cut position below.
DRAWER_DETENT_NUB_X = 24.0
DRAWER_DETENT_TIP_X = DRAWER_DETENT_NUB_X - DRAWER_DETENT_NUB_BASE_WIDTH / 2 - DETENT_SEVER_CLEARANCE  # ~17.44
DRAWER_DETENT_ROOT_X = DRAWER_DETENT_NUB_X + DRAWER_DETENT_NUB_TO_ROOT_SPAN                            # 50.0

# The side wall's bottom edge is finger-jointed to the drawer's own Bottom
# panel along its ENTIRE length except a short PLAIN zone here, sized to
# contain the flexure's tip-to-root span with margin (a finger-jointed edge
# can't locally express the nub's protrusion -- see generate_drawers.py). The
# Bottom panel's matching finger-hole row is split to skip this same zone.
DRAWER_DETENT_PLAIN_LO = DRAWER_DETENT_TIP_X - 2.0    # ~15.44
DRAWER_DETENT_PLAIN_HI = DRAWER_DETENT_ROOT_X + 2.0   # 52.0

# --- Catch holes (bottom panel for the bottom drawer, shelf for the top
# drawer): X position derived from existing datums (rear wall plane, the
# drawer's own closed-position "bay gap" reveal, body length, faceplate
# thickness) so hole center = nub center at the closed position.
DRAWER_BAY_GAP = BAY_LENGTH - DRAWER_BODY["length"]   # 0.475, closed-position
                                                       # reveal (DESIGN.md #9)
DRAWER_FRONT_INNER_FACE_CLOSED_X = BAY_X1 - DRAWER_BAY_GAP - T   # 297.975,
                                   # box X of the Front panel's INNER face
                                   # (interior-facing surface) when the
                                   # drawer is fully closed
CATCH_HOLE_X = DRAWER_FRONT_INNER_FACE_CLOSED_X - DRAWER_DETENT_NUB_X   # ~273.975

# X-length: nub base + ramp clearance, keeping engaged X-slop <= 0.8mm total.
CATCH_HOLE_X_LENGTH = DRAWER_DETENT_NUB_BASE_WIDTH + 0.8   # ~10.92

# Y-width: side thickness + both drawers' full lateral float + margin, so
# the nub can't miss the hole even at worst-case drawer skew (DESIGN.md
# derives this from the drawer's own ~4.9mm/side bay float).
DRAWER_LATERAL_GAP = (INTERIOR_WIDTH - DRAWER_BODY["width"]) / 2   # 4.875, "~4.9mm/side"
CATCH_HOLE_Y_WIDTH = T + 2 * DRAWER_LATERAL_GAP + 1.0              # ~13.925

# Y centers: box Y of each side wall's mid-thickness when the drawer is
# laterally centered in the bay (the catch hole's own width, above, covers
# the full float either side of this nominal center).
CATCH_HOLE_LEFT_Y = T + DRAWER_LATERAL_GAP + T / 2                              # ~9.6375
CATCH_HOLE_RIGHT_Y = T + DRAWER_LATERAL_GAP + DRAWER_BODY["width"] - T / 2      # ~155.4625

# Catch holes need real 0.5mm margin at the drawer's WORST-CASE lateral
# extreme (side wall flush against the bay wall) -- at that extreme, the
# nub's own footprint already reaches exactly to the bay wall's interior
# face, so the required margin necessarily pushes the hole a hair PAST that
# face, into the zone where the bottom panel's/shelf's own finger tabs to
# that wall would otherwise sit. Rather than let the catch hole silently
# clip 1-2 finger teeth (verified by rendering: it does), both the bottom
# panel's and shelf's edges to the LEFT/RIGHT walls carry a short PLAIN
# zone at the catch hole's own X range (same CompoundEdge technique as the
# drawer side wall's flexure zone) so there's no tooth there to clip.
CATCH_HOLE_PLAIN_MARGIN = 3.0
CATCH_HOLE_X_PLAIN_LO = CATCH_HOLE_X - CATCH_HOLE_X_LENGTH / 2 - CATCH_HOLE_PLAIN_MARGIN
CATCH_HOLE_X_PLAIN_HI = CATCH_HOLE_X + CATCH_HOLE_X_LENGTH / 2 + CATCH_HOLE_PLAIN_MARGIN

# --- Output ------------------------------------------------------------------

OUTPUT_DIR = "output"
