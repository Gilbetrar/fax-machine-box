# Fax Machine Box - Learnings

Distilled patterns and gotchas for future agents. Keep under 100 lines.

## Project Overview

Laser-cut fax machine themed desktop organizer using Boxes.py.

## Project Structure

```
fax-machine-box/
├── src/faxbox/         # Python source
│   ├── config.py       # Dimensions, material thickness
│   └── test_generator.py
├── output/             # Generated SVG files (gitignored)
├── LEARNINGS.md        # Distilled patterns (read this first)
└── SESSION_LOG.md      # Raw session history (don't read)
```

## Commands That Work

```bash
# Install project
python3 -m pip install -e .

# Generate test box
python3 -m faxbox.test_generator
```

## Boxes.py Usage Pattern

**Critical**: Must call `open()` before `render()` and `close()` after to get output.

```python
from boxes.generators.closedbox import ClosedBox

box = ClosedBox()
box.parseArgs(["--x", "100", "--y", "80", "--h", "60", "--output", "out.svg"])
box.open()      # Initialize canvas - REQUIRED before render
box.render()    # Generate geometry
data = box.close()  # Finalize - returns BytesIO

# Write to file
with open("out.svg", "wb") as f:
    f.write(data.getvalue())
```

## Available Generators

Key generators for this project:
- `ClosedBox` - Basic fully closed box
- `OpenBox` - Open top box
- `SlidingLidBox` - Box with sliding lid (for drawers?)

List all: `from boxes.generators import getAllBoxGenerators`

## Dependencies

- Boxes.py must be installed from GitHub (PyPI "boxes" is wrong package)
- Dependency: `boxes @ git+https://github.com/florianfesti/boxes.git`

## Config Constants (config.py)

- `MATERIAL_THICKNESS = 3.0` mm (standard laser-cut plywood)
- `BURN = 0.05` mm (adjust for joint tightness)
- `OUTPUT_DIR = "output"`
