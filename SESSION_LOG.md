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
