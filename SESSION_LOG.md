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

---

## Agent Session - Issue #2 Cleanup

**Worked on:** Issue #2 - Generate Drawer Boxes (acceptance criteria fix)

**What I did:**
- Renamed drawer_generator.py → generate_drawers.py to match acceptance criteria
- Updated LEARNINGS.md with correct command
- Verified both generators still work after rename
- Closed issue #2

**What I learned:**
- Always check that file names match the acceptance criteria commands exactly
- Issue acceptance criteria verification steps are the spec - if they say `python -m faxbox.generate_drawers`, that's what should work
- This repo has no CI workflows configured - don't need to wait for CI

**Codebase facts discovered:**
- Project is Python-only, no npm/package.json
- No pytest tests yet - just generator scripts
- test_generator.py is a proof-of-concept generator, not a pytest test file

**Mistakes made:**
- Previous agent named the module differently than the issue specified

---

## Agent Session - Issue #3

**Worked on:** Issue #3 - Generate Outer Shell with Internal Dividers

**What I did:**
- Added shell dimensions to config.py (304.8mm × 165.1mm × 127mm external)
- Added paper compartment depth (76.2mm / 3") and lid groove dimensions
- Created shell_generator.py with OuterShell class extending Boxes
- Generated all outer shell pieces:
  - Left/Right walls with finger joints
  - Front wall with drawer openings
  - Back wall
  - Bottom panel
  - Internal vertical divider (separates paper from drawer bay)
  - Horizontal shelf (divides drawer bay into 2 slots)
- Added lid groove cutouts on left wall for sliding lid

**What I learned:**
- Complex multi-piece generators need careful dimension planning
- rectangularHole works for internal cutouts (drawer openings, lid grooves)
- For internal dividers, edge type "f" (holes) allows other pieces to slot in
- The `move` parameter on rectangularWall controls piece layout on canvas
- callback parameter is array of 4 functions [bottom, right, top, left] called at edge drawing

**Layout understanding:**
- Paper compartment (3" wide) on left side with sliding lid
- Drawer bay (~9" wide) on right side
- Horizontal shelf divides drawer bay vertically into 2 drawer slots
- Vertical divider runs front-to-back separating paper from drawers

**Codebase facts discovered:**
- No CI workflows configured for this repo
- Output files go to output/ directory (gitignored except .gitkeep)
- All generators follow same pattern: Class(Boxes) → parseArgs → open → render → close

**Potential refinements for future:**
- Lid groove implementation uses rectangularHole cutouts - may need adjustment when implementing actual lids in issue #4
- Drawer opening positions should be verified against actual drawer dimensions
- Finger joint alignment between shell and internal dividers needs verification
