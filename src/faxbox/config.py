"""Single source of truth for fax machine box dimensions (mm).

Implements DESIGN.md — if a number here disagrees with DESIGN.md, DESIGN.md
wins. Everything below is either a SPEC.md external target, a fit policy
constant, or derived. Do not add independent magic numbers.

Coordinate convention (DESIGN.md): origin at the exterior front-left-bottom
corner. X+ rearward (length, 12"), Y+ rightward (width, 6.5"), Z+ up (5").
"""

import os

# --- Material & laser -------------------------------------------------------

# Nominal 1/8" plywood.  FAXBOX_THICKNESS overrides it (mm) so the cut-file
# generator can produce a full set per stock thickness (2.8-3.5 mm: real
# "3.2 mm" birch ply runs anywhere in that band).  Every derived dimension
# below follows T; the external envelope (SHELL_EXT) stays fixed, so a
# thicker stock makes the interior smaller.  Tests and the default build use
# 3.175.
NOMINAL_THICKNESS = 3.175
MATERIAL_THICKNESS = float(os.environ.get("FAXBOX_THICKNESS", NOMINAL_THICKNESS))
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
LID_SLOT_VERTICAL_CLEARANCE = 1.2  # was 0.8; Ponoko panels warp, see DESIGN.md
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
LID_RAIL_HEIGHT = 7.5                            # material left above the slot (was 5.0)
LID_SLOT_TOP = SHELL_EXT["height"] - LID_RAIL_HEIGHT      # 122.0
LID_SLOT_HEIGHT = T + LID_SLOT_VERTICAL_CLEARANCE         # 3.975
LID_SLOT_BOTTOM = LID_SLOT_TOP - LID_SLOT_HEIGHT          # 118.025
LID_SLOT_X_END = DIVIDER_X0    # slot runs X 3.175 -> 79.375, open at front edge

FRONT_WALL_TOP = LID_SLOT_BOTTOM                 # lid slides over the front wall
FRONT_WALL_HEIGHT = FRONT_WALL_TOP - WALL_Z0     # 118.025

# Divider keying (DESIGN.md "Divider keying"): the walls' divider finger-hole
# rows stop at the lid-slot floor, and the RIGHT wall's row is DIVIDER_KEY_DROP
# shorter than the left wall's (one finger pitch = 4T).
DIVIDER_ROW_TOP_Z = LID_SLOT_BOTTOM
DIVIDER_KEY_DROP = 4 * T

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

# The posts either side of an opening are at least MIN_WEB wide (they were T,
# 2.8-2.9 mm at thin stock): 152.4 at T = 3.175, 153.5 at 2.8.
OPENING_WIDTH = INTERIOR_WIDTH - 2 * max(T, MIN_WEB)
OPENING_HEIGHT = 55.0
# Sill-free: each opening's bottom edge is exactly its slot's floor.  The
# lower slot's floor is the bay floor, except at thin stock: the strip of
# rear wall under the opening is BOTTOM_OPENING_Z0 tall and must be at least
# MIN_WEB, so at T < MIN_WEB the lower drawer (and its opening) sit
# MIN_WEB - T above the bay floor (0.2 mm at 2.8 mm stock; the drawer then
# rests on that strip at the faceplate end and on the bay floor at the far
# end, a tilt of 0.05 degrees).
BOTTOM_DRAWER_Z0 = max(FLOOR_TOP, MIN_WEB)       # 3.175 (3.0 at T = 2.8, 2.9)
BOTTOM_OPENING_Z0 = BOTTOM_DRAWER_Z0
BOTTOM_OPENING_Z1 = BOTTOM_OPENING_Z0 + OPENING_HEIGHT    # 58.175
TOP_OPENING_Z0 = SHELF_Z1                        # 65.0875
TOP_OPENING_Z1 = TOP_OPENING_Z0 + OPENING_HEIGHT          # 120.0875

# --- Drawers (2x identical, 6 pieces each) ----------------------------------

DRAWER_BAY_GAP = 0.475          # bay length minus drawer length (closed)
DRAWER_WIDTH_CLEARANCE = 3.4    # opening width minus drawer width (total)

DRAWER_BODY = {   # external
    "width": OPENING_WIDTH - DRAWER_WIDTH_CLEARANCE,    # Y (149.0 at T=3.175)
    "length": BAY_LENGTH - DRAWER_BAY_GAP,  # X (218.6 at T=3.175, pull direction); bay gap 0.475 -- the divider is
                       # the drawer's in-stop (the inset faceplate can't stop
                       # against the rear wall). Closed, the faceplate sits
                       # recessed by the 0.475 slide gap -- near-flush; true
                       # flush and slide clearance are mutually exclusive.
    "height": 53.5,    # Z
}

# Drawer guides (red-team H1, V5): four plywood ribs, two per drawer slot, lying
# flat on the bottom panel (lower) or the shelf (upper) against the side walls at
# the divider end, flush with the panel's side edge.  They narrow the channel to
# INTERIOR_WIDTH - 2T, which is the rear-wall opening width at T >= 3.0, so the
# far end of a drawer can float no further than its front end can (about 1.7 mm
# each way) instead of 4.9 mm.  Each rib is T wide and T high; its leading end (the
# end facing the rear opening) is tapered 30 degrees in plan, which a flat laser
# part can do and an upright strip could not, so a yawed drawer corner is funnelled
# in instead of butting the end face.
DRAWER_GUIDE = {"length": 40.0, "taper_deg": 30.0, "tip_width": 0.8}      # width and height = T

FACEPLATE = {
    "width": OPENING_WIDTH - 2 * FACEPLATE_REVEAL,    # 150.9
    "height": OPENING_HEIGHT - 2 * FACEPLATE_REVEAL,  # 53.5
}
# The drawer body (53.5 high) rests on the opening's floor; the faceplate is
# the same height, so to leave FACEPLATE_REVEAL all round it is glued this far
# ABOVE the body's bottom edge (body bottom edge sticks out 0.75 below it).
FACEPLATE_Z_OFFSET = FACEPLATE_REVEAL

# Closed grip slot cut through BOTH faceplate and body front, aligned
# (DESIGN.md: 30 x 15 r7.5, slot top 8.0 below the part top edge).
DRAWER_GRIP_SLOT = {"width": 30.0, "height": 15.0, "radius": 7.5,
                    "top_below_edge": 8.0}
# On the faceplate the same slot sits FACEPLATE_Z_OFFSET further below the
# plate's top edge, because the plate is glued that far above the body.
FACEPLATE_SLOT_TOP_BELOW_EDGE = DRAWER_GRIP_SLOT["top_below_edge"] + FACEPLATE_Z_OFFSET

# --- Drawer retention (iteration 2, issue #20): magnet pair per drawer ------
# DESIGN.md "Retention (iteration 2)": one 6mm-nominal disc magnet press-fit
# into a hole in the drawer's LEADING body wall (the "Back" piece in
# generate_drawers.py -- the deep end opposite the faceplate) and a matching
# coaxial hole in the divider, at the drawer's fully-closed position (the
# divider is the drawer's in-stop, contact gap 0 -- see DRAWER_BODY comment
# above). An attracting pair pulls the drawer closed against the divider.
#
# Hole diameter: undersize the magnet's own diameter for a press fit, THEN
# let Boxes.py's `self.hole()` burn-compensate the drawn tool path the same
# way every other hole in this project is compensated (kerf widens the cut
# back out towards nominal) -- this is also upstream precedent: Boxes.py's
# own gridfinitybase.py generator drills its magnet holes via plain
# `self.hole(x, y, d=dia)` with `dia = requested_diameter - 0.5` for a press
# -fit variant (its default magnet-hole argument is 6.5 for 6mm magnets, a
# generic snug fit; the "-0.5" branch is its OWN press-fit case). We follow
# the same `self.hole()` + fixed-undersize pattern, but pick our own
# press-fit constant (0.35, not gridfinity's 0.5) since ply and magnet
# tolerances here were never validated against that project's stock --
# MAGNET_PRESS_FIT is exactly the number the magnet-fit coupon (see
# calibration.py's magnet coupon) exists to recalibrate before cutting real
# parts. BURN and MAGNET_PRESS_FIT do two different jobs and must not be
# conflated: MAGNET_PRESS_FIT sets the *physical* (post-kerf) hole size
# relative to the magnet; BURN is what makes the *drawn* tool path smaller
# than that physical target so the laser's kerf widens it back out to
# MAGNET_HOLE_DIA. As long as BURN stays calibrated (via the kerf coupon),
# the magnet holes need no separate kerf correction of their own.
MAGNET_DIA = 6.0            # nominal disc magnet diameter
MAGNET_PRESS_FIT = 0.35     # undersize for a press fit; recalibrate via the
                             # magnet coupon (calibration.py) before cutting
MAGNET_HOLE_DIA = MAGNET_DIA - MAGNET_PRESS_FIT   # 5.65, physical target size

# Position (DESIGN.md): offset from the drawer's own Y-center (the grip slot
# -- on the OTHER end panel, the Front -- is 30mm wide and Y-centered; the
# magnet hole sits well clear of that zone at center + 40mm). Both drawers
# use the same local offset, and since each drawer is Y-centered in its
# rear-wall opening at closed position (opening_cx = INTERIOR_WIDTH/2 in the
# rear wall's own frame -> box Y = T + INTERIOR_WIDTH/2, see shell_generator's
# rear wall), the two drawers' magnet holes and both divider holes all land
# at the SAME box Y. Checked (2026-07-07; distances corrected 2026-07-09):
# +40mm puts the hole ~39.4mm from the divider's nearer Y-edge (158.75/2 -
# 40) and 34.5mm from the drawer Back panel's nearer finger edge (149.0/2 -
# 40 -- the two parts have different widths, so the two distances differ)
# (both >> the required 3mm/8mm clearances); -40mm is symmetric and equally
# safe -- the choice of side is arbitrary given that clearance margin, so +40
# (toward increasing Y, the right/engraved-wall side) was picked for no
# reason beyond matching the literal offset direction in the design brief.
MAGNET_Y_OFFSET = 0.0     # was 40.0: centred, so a drawer back turned round or a
                          # mirror-built box still lines the magnets up
MAGNET_BOX_Y = T + INTERIOR_WIDTH / 2 + MAGNET_Y_OFFSET   # 82.55, the box centre line

# Z: "drawer mid-height" is a property of the drawer body alone (half its own
# height), independent of which slot it sits in; for the DIVIDER hole (a
# fixed box part) that local mid-height has to be projected into absolute
# box Z using each slot's own floor -- the bottom drawer rests on the bay
# floor (sill-free bottom opening, see DESIGN.md #4), the top drawer rests on
# the shelf's top face (sill-free top opening) -- so the two divider holes
# sit at different Z, one per drawer.
MAGNET_BOTTOM_DRAWER_Z = BOTTOM_DRAWER_Z0 + DRAWER_BODY["height"] / 2   # 29.925
MAGNET_TOP_DRAWER_Z = SHELF_Z1 + DRAWER_BODY["height"] / 2       # 91.8375

# --- Lid retention ----------------------------------------------------------
# None.  The turn-button lock (a bolted paddle on the front wall) was removed
# on 2026-10-10 (Ben's decision): the sliding lid is held by friction in its
# slots only.  There is no button part, no front-wall pivot hole and no bolt,
# washer or nut.

# Hardware to buy: magnets only.
HARDWARE = {
    "magnet": "6 x 2 mm N52 neodymium disc",
    "magnet_thickness": 2.0,
    "magnets_needed": 4,
    "magnets_to_buy": 6,
}

# Paper: quarter letter (4.25 x 5.5 in), standing on edge in the compartment
# with the 5.5 in side along Y and the 4.25 in side vertical.
PAPER = {"height": 107.95, "width": 139.7}
PAPER_BAY_HEIGHT = LID_SLOT_BOTTOM - FLOOR_TOP    # floor top -> underside of the lid
PAPER_HEADROOM = PAPER_BAY_HEIGHT - PAPER["height"]
PAPER_SIDE_ROOM = INTERIOR_WIDTH - PAPER["width"]

# --- Sliding lid -------------------------------------------------------------

# The re-entrant corners at the rear end of the slot (the root of the rail's
# cantilever) are rounded with this radius; the lid stops short of the arcs so
# it never touches them even when it is lifted against the rail.
LID_SLOT_CORNER_R = 1.0
LID_REAR_X = DIVIDER_X0 - LID_SLOT_CORNER_R       # X of the lid's rear end when pushed home (78.375)
LID_FRONT_RECESS = 0.375                          # lid front edge behind the front wall plane when home

SLIDING_LID = {
    "length": LID_REAR_X - LID_FRONT_RECESS,          # X (78.0 at T=3.175; was 79.0)
    "width": SHELL_EXT["width"] - SLIDE_CLEARANCE,    # 163.6 (rides in through-slots)
}
LID_GRIP_SLOT = {"width": 30.0, "height": 10.0, "radius": 5.0,
                 # 25.0 keeps a 10mm ligament between slot and front edge
                 # (15.0 left ~0.2mm -- it would have broken into a notch)
                 "center_from_front": 25.0}

# --- Engraving ---------------------------------------------------------------

ENGRAVE_COLOR = [1.0, 0.0, 0.0]   # red = engrave
CUT_COLOR = [0.0, 0.0, 1.0]       # blue = cut
# The "FAX MACHINE" pixel-font engraving constants (ENGRAVE_TEXT/
# ENGRAVE_PIXEL_SIZE/ENGRAVE_FONT_SPACING/ENGRAVE_CENTER) were REMOVED
# 2026-07-10 with the engraving itself (Ben's decision, issue #25 open-item
# 1: wall art from art/FACES.md supersedes the placeholder text, whose
# Z=63.5 centerline sat exactly on the shelf finger-hole row).

# --- Output ------------------------------------------------------------------

OUTPUT_DIR = "output"

# --- Provider abstraction (laser cutting service target, issue #ponoko) -----
# A "provider" bundles everything that changes when the SAME geometry is
# ordered from a different laser-cutting service: kerf compensation (BURN),
# the cut/engrave SVG stroke colors, the sheet size limit to nest within, and
# whether reference-only part-name labels are kept. Selected either via the
# FAXBOX_PROVIDER env var or an explicit `provider=` kwarg passed to any
# faxbox.generate_*()/faxbox.layout function (see resolve_provider() below).
#
# DEFAULT_PROVIDER = "nycr" and every PROVIDERS["nycr"] value below is
# IDENTICAL to this project's pre-existing (pre-provider-abstraction)
# constants -- BURN, CUT_COLOR, ENGRAVE_COLOR, OUTPUT_DIR -- so the default
# code path (no env var, no provider arg) is byte-for-byte unchanged. Never
# add a new PROVIDERS["nycr"] value that isn't already one of this file's
# pre-existing constants.
#
# Ponoko values verified live against Ponoko's own current help/materials
# pages, 2026-07-07 (see PONOKO_* constants below for each fact + its
# source URL). Independently re-verified via a second live fetch the same
# day after an initial research pass returned a color scheme that turned
# out to be backwards -- see the color-convention comment below.

# --- Ponoko-specific verified constants (birch plywood, 2026-07-07) --------

# Kerf (total width removed by the laser's beam): published directly on
# Ponoko's birch plywood material page.
# Source: https://www.ponoko.com/materials/birch-plywood (fetched
# 2026-07-07: "Kerf Width: 0.20mm").
PONOKO_KERF = 0.20

# BURN is Boxes.py's PER-SIDE kerf compensation (half the total kerf, since
# the beam removes material symmetrically from both sides of the drawn
# line) -- same relationship this project's own kerf coupon uses to derive
# BURN from a measured cut (calibration.py: "BURN = (measured - 10.0) / 2").
# Starting value for a first Ponoko order; recalibrate from the kerf-square
# coupon nested onto the Ponoko sheet (see ponoko.py / README "Ordering
# from Ponoko") the same way BURN itself is calibrated for NYC Resistor.
PONOKO_BURN = PONOKO_KERF / 2   # 0.10

# Color convention. IMPORTANT: an initial research pass returned "red=cut,
# blue=vector-engrave, green=area-engrave" -- this was WRONG (an artifact of
# stale/confused secondary sources) and was caught by a second, independent
# live fetch of Ponoko's own current help article before being encoded here.
# The CURRENT, verified convention is the OPPOSITE for cut/engrave, and uses
# gray fill (not green) for area engrave, which this project doesn't use
# (no filled/area-engrave content anywhere in this design):
#   Blue stroke = cut, Red stroke = line/vector engrave, Gray fill = area engrave.
# Source: https://help.ponoko.com/en/articles/2688732-how-should-i-specify-laser-actions
# (fetched live 2026-07-07: "Blue stroke = cutting / Red stroke = line
# engraving / Gray fill = area engraving"). Corroborated by
# https://help.ponoko.com/en/articles/2688477-what-design-software-file-type-should-i-use
# (same fetch date).
#
# This happens to be IDENTICAL to this project's own NYC Resistor
# convention (DESIGN.md: "blue #0000FF = cut, red #FF0000 = engrave") -- a
# coincidence, not an assumption: both providers' cut/engrave RGB values
# below are deliberately written as their own named constants (not reused
# via a shared alias) so a future provider with a genuinely different
# convention doesn't require restructuring this dict.
PONOKO_CUT_COLOR = [0.0, 0.0, 1.0]       # blue = cut
PONOKO_ENGRAVE_COLOR = [1.0, 0.0, 0.0]   # red = line/vector engrave

# Text handling: Ponoko's file-prep docs require text be converted to
# outlines/paths before upload or "it will not be read" as a laser
# instruction at all (source: same "what design software / file type"
# article above). Rather than outline part-name labels into engrave-red
# vector paths (which would engrave every part name onto the real, visible
# faceplates/walls -- nobody wants that), this project strips reference
# labels entirely for the Ponoko path. Also: Ponoko does not hard-reject
# stray colors (they're user-assignable per-color after upload -- same
# source), but this project still emits ONLY the two colors above, with NO
# other stroke/fill color and NO <text> elements, to keep the uploaded file
# unambiguous.
PONOKO_STRIP_LABELS = True

# Sheet size to nest within. Ponoko publishes two different numbers for
# birch plywood: a raw maximum SHEET size, and a smaller maximum DESIGN
# (workable) area within that sheet -- the gap between them is Ponoko's own
# sheet-edge margin, so designs must nest within the smaller (workable)
# figure, not the raw sheet size.
#   Raw max sheet size: 795.00mm x 395.00mm.
#   Source: https://www.ponoko.com/materials/birch-plywood (fetched
#   2026-07-07: "Maximum Sheet Size: 795.00 x 395.00mm").
#   Max DESIGN/part size (this project's "P3"-equivalent workable area,
#   applies to birch plywood as one of the "100+ materials" at this size):
#   790mm x 384mm.
#   Source: https://help.ponoko.com/en/articles/2688726-what-size-can-i-make-my-part-what-material-sizes-are-available
#   (fetched 2026-07-07: "For 100+ materials the maximum material sheet
#   size is 31.1\" x 15.1\" / 790mm x 384mm").
# This project nests within the smaller (790 x 384) figure.
PONOKO_SHEET_WIDTH = 790.0
PONOKO_SHEET_HEIGHT = 384.0

# Minimum gap Ponoko wants between design elements: "at least 0.040\" (1mm)
# between elements," parts under 6mm can fall through the bed.
# Source: https://help.ponoko.com/en/articles/2688741-how-do-i-design-for-highest-quality
# (fetched 2026-07-07). This project's existing MARGIN_MM=10 /
# SPACING_MM=5 (layout.py) are already well over this minimum, so the
# Ponoko nesting pass reuses those same two constants rather than adding a
# separate, looser pair.

PONOKO_OUTPUT_DIR = f"{OUTPUT_DIR}/ponoko"

# --- NYC Resistor-specific verified constants -------------------------------
# Same conservative-fallback bed size src/faxbox/layout.py has always used
# (see that module's docstring for the full ambiguous-bed-size story, issue
# #19) -- moved here, unchanged, so PROVIDERS["nycr"] can reference them the
# same way PROVIDERS["ponoko"] references PONOKO_SHEET_WIDTH/HEIGHT above.
# layout.py's own SHEET_WIDTH_MM/SHEET_HEIGHT_MM now point at these same two
# constants (not independent copies), so there is exactly one source of
# truth and the default (no env/provider-override) output stays unchanged.
NYCR_SHEET_WIDTH = 609.6   # 24in, conservative fallback
NYCR_SHEET_HEIGHT = 457.2  # 18in, conservative fallback

PROVIDERS = {
    "nycr": {
        "burn": BURN,                    # 0.08, this file's pre-existing default
        "cut_color": CUT_COLOR,          # blue, pre-existing
        "engrave_color": ENGRAVE_COLOR,  # red, pre-existing
        "strip_labels": False,           # keep gray reference-only part labels
        "output_dir": OUTPUT_DIR,        # "output", pre-existing
        "sheet_width": NYCR_SHEET_WIDTH,
        "sheet_height": NYCR_SHEET_HEIGHT,
    },
    "ponoko": {
        "burn": PONOKO_BURN,
        "cut_color": PONOKO_CUT_COLOR,
        "engrave_color": PONOKO_ENGRAVE_COLOR,
        "strip_labels": PONOKO_STRIP_LABELS,
        "output_dir": PONOKO_OUTPUT_DIR,
        "sheet_width": PONOKO_SHEET_WIDTH,
        "sheet_height": PONOKO_SHEET_HEIGHT,
    },
}

DEFAULT_PROVIDER = "nycr"


def resolve_provider(explicit: str | None = None) -> str:
    """Resolve which PROVIDERS entry to use: an explicit `provider=` kwarg
    wins, then the FAXBOX_PROVIDER env var, then DEFAULT_PROVIDER ("nycr").

    Every faxbox.generate_*() function and faxbox.layout.generate_layout()-
    family function takes an optional `provider` kwarg that funnels through
    this, so calling any of them with no arguments and no FAXBOX_PROVIDER
    set reproduces this project's original (pre-provider-abstraction)
    behavior exactly.
    """
    if explicit:
        return explicit
    return os.environ.get("FAXBOX_PROVIDER", DEFAULT_PROVIDER)
