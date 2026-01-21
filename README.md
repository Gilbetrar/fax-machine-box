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
