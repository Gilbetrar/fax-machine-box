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
