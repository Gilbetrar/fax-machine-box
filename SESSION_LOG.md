# Session Log

Raw session history from agent work. Check LEARNINGS.md for distilled patterns.

---

## Agent Session - Issue #1

**Worked on:** Issue #1 - Project Setup and Boxes.py Proof of Concept

**What I did:**
- Created full project structure (pyproject.toml, README.md, src/faxbox/)
- Set up config.py with material thickness and dimension constants
- Created test_generator.py to verify Boxes.py works
- Fixed dependency to use GitHub Boxes.py instead of wrong PyPI package

**What I learned:**
- PyPI "boxes" package is NOT the laser cutting library - must install from GitHub
- Boxes.py requires specific call sequence: `parseArgs()` → `open()` → `render()` → `close()`
- `close()` returns BytesIO object that must be manually written to file
- The `--outside` flag requires a value like "1", not just presence

**Codebase facts discovered:**
- Boxes.py generators live in `boxes.generators.<name>` modules
- Use `from boxes.generators import getAllBoxGenerators` to list available generators
- ClosedBox produces 6 panels (4 walls + top + bottom) with finger joints

**Mistakes made:**
- Initially tried `from boxes.generators.box import Box` - wrong import path
- Forgot `box.open()` before render - got AttributeError about missing 'edges'
- Forgot `box.close()` and writing data to file - SVG wasn't created
- Used `--outside` as flag without value - argparse error

---

## Agent Session - Issue #2

**Worked on:** Issue #2 - Generate Drawer Boxes

**What I did:**
- Added drawer dimensions to config.py (222mm × 158mm × 53mm internal, 3.175mm material)
- Created DrawerBox generator class extending Boxes.py
- Implemented open-top drawer with finger joints on all corners
- Added finger-notch pull cutout on front face using callback pattern

**What I learned:**
- For an open-top box, use edge type "e" (plain) for the top edge
- Edge types: F=finger joints (male), f=finger holes (female), e=plain edge
- rectangularWall callback array: [bottom, right, top, left] - called at start of each edge
- Callback index 0 is called at bottom-left corner but can draw holes anywhere
- rectangularHole(x, y, dx, dy, r) - r parameter creates rounded corners

**Boxes.py edge type combinations for open-top drawer:**
- Front/Back walls (x, h): "Ffef" (bottom=F, right=f, top=e, left=f)
- Side walls (y, h): "FFeF" (bottom=F, right=F, top=e, left=F)
- Bottom (x, y): "ffff" (all finger holes)

**Codebase facts discovered:**
- Crate generator shows good example of adding handle holes via callbacks
- Blue paths (stroke="rgb(0,0,255)") in SVG are internal cuts/holes
- Black paths (stroke="rgb(0,0,0)") are external cut lines

**Mistakes made:**
- Initially thought callback was called during face rendering - it's called at edge start
- First tried complex callback signature - callbacks take no arguments, use self for dimensions
