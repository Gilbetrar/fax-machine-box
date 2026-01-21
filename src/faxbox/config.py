"""Configuration constants for fax machine box dimensions."""

# Material thickness in mm (3mm plywood is common for laser cutting)
MATERIAL_THICKNESS = 3.0

# Kerf compensation (laser beam width, adjust based on your laser cutter)
KERF = 0.1

# Burn correction for finger joints (adjust for tight/loose fit)
BURN = 0.05

# Default box dimensions in mm (placeholder - will be refined in later issues)
DEFAULT_BOX = {
    "width": 100.0,
    "height": 60.0,
    "depth": 80.0,
}

# Output directory for generated SVG files
OUTPUT_DIR = "output"

# Drawer dimensions in mm
# Internal dimensions: ~8.75" × 6.25" × 2.1" with clearance for sliding
# The issue specifies 3.175mm material (1/8" plywood)
DRAWER_MATERIAL_THICKNESS = 3.175  # 1/8" plywood

DRAWER = {
    "width": 222.0,   # ~8.75" internal width (slightly under for clearance)
    "depth": 158.0,   # ~6.25" internal depth (slightly under for clearance)
    "height": 53.0,   # ~2.1" internal height
}

# Clearance for drawer sliding (per side)
DRAWER_CLEARANCE = 1.0  # 1mm clearance on each side

# Finger-notch pull dimensions (half-circle cutout on front face)
FINGER_NOTCH_RADIUS = 15.0  # 15mm radius for comfortable grip

# Outer shell dimensions in mm
# External: 12" × 6.5" × 5"
SHELL = {
    "width": 304.8,   # 12" external width (left to right)
    "depth": 165.1,   # 6.5" external depth (front to back)
    "height": 127.0,  # 5" external height
}

# Paper compartment dimensions (front section with sliding lid)
# ~3" from front (76.2mm internal)
PAPER_COMPARTMENT_DEPTH = 76.2  # 3" internal depth

# Lid groove dimensions for sliding lid
LID_GROOVE_WIDTH = 3.5  # Slightly wider than material for sliding fit
LID_GROOVE_DEPTH = 5.0  # How deep the groove cuts into the wall

# Lid dimensions
LID_TAB_CLEARANCE = 0.3  # Clearance for lid tabs to fit in grooves
SLIDING_LID_TAB_DEPTH = LID_GROOVE_DEPTH - 1.0  # How far tab extends into groove

# Flat tabbed lid for drawer bay (sits on top)
FLAT_LID_TAB_WIDTH = 10.0  # Width of alignment tabs on flat lid
FLAT_LID_TAB_DEPTH = 5.0  # How deep alignment tabs extend into wall tops

# Engraving settings for "FAX MACHINE" text
ENGRAVE_COLOR = [1.0, 0.0, 0.0]  # Red RGB for Ponoko engraving (#FF0000)
ENGRAVE_FONT_SIZE = 8.0  # Size of each pixel cell in mm
ENGRAVE_FONT_SPACING = 2.0  # Space between letters in mm
ENGRAVE_LINE_WIDTH = 0.5  # Line width for engraving strokes in mm
