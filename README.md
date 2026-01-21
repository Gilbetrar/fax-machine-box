# Fax Machine Box

A laser-cut box generator for a fax machine themed desktop organizer using [Boxes.py](https://github.com/florianfesti/boxes).

## Setup

```bash
pip install -e .
```

## Usage

Generate a test box to verify installation:

```bash
python -m faxbox.test_generator
```

This creates `output/test_box.svg` which can be opened in any browser or SVG viewer.

## Project Structure

```
fax-machine-box/
├── src/faxbox/
│   ├── config.py         # Dimensions, material thickness
│   └── test_generator.py # Test box generator
└── output/               # Generated SVG files
```

## Components

- **Outer shell** - Main enclosure with internal dividers
- **Drawers** - Sliding drawer boxes
- **Lids** - Sliding and tabbed flat lids
- **Engraving** - "FAX MACHINE" text decoration

## Generating Parts

Generate all components:

```bash
python -m faxbox.shell_generator    # Outer shell pieces
python -m faxbox.generate_drawers   # Drawer pieces
python -m faxbox.generate_lids      # Lid pieces
python -m faxbox.layout             # Combined layout for ordering
```

## Ordering for Laser Cutting

The `output/final_layout.svg` file contains all parts ready for laser cutting services like Ponoko.

**Color coding:**
- Blue (`#0000FF`) = Cut lines
- Red (`#FF0000`) = Engrave lines

**Material:** 3.175mm (1/8") plywood

**File dimensions:** ~1290mm x 800mm (~51" x 31")

## Assembly Instructions

### Parts Checklist

After laser cutting, you should have:
- 1x Left Wall
- 1x Right Wall
- 1x Front Wall (with drawer openings and "FAX MACHINE" engraving)
- 1x Back Wall
- 1x Bottom
- 1x Vertical Divider (separates paper compartment from drawer bay)
- 1x Horizontal Shelf (creates upper/lower drawer slots)
- 2x Drawer sets (each with: front, back, 2 sides, bottom)
- 1x Sliding Lid (for paper compartment)
- 1x Flat Lid (optional top cover)

### Assembly Steps

**1. Outer Shell - Bottom Assembly**
   - Start with the Bottom piece
   - Attach Left Wall and Right Wall to the bottom using finger joints
   - Attach Back Wall, connecting to bottom and both side walls

**2. Internal Dividers**
   - Insert the Vertical Divider about 3" from the front
   - Slide it down into the finger joint slots
   - This creates the paper compartment (front) and drawer bay (back)

**3. Horizontal Shelf**
   - Slide the Horizontal Shelf into the drawer bay
   - It should rest on the shelf slots cut into the side walls
   - This divides the drawer bay into upper and lower sections

**4. Front Wall**
   - Attach the Front Wall last
   - Align with all finger joints on sides and bottom
   - The drawer openings should align with the internal shelf

**5. Drawer Assembly (x2)**
   - For each drawer, assemble:
     - Attach sides to front and back using finger joints
     - Slide bottom piece into the finger joint slots
   - Test fit each drawer in its bay

**6. Lids**
   - Sliding Lid: Slide into the grooves on the paper compartment walls
   - Flat Lid: Optional, rests on top of the drawer bay

### Tips

- Dry-fit all pieces before gluing
- Use wood glue sparingly on finger joints
- Sand any tight-fitting joints lightly
- The drawers should slide smoothly; sand if needed
