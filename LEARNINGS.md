# Fax Machine Box - Learnings

Distilled patterns for future agents. For full session history, see SESSION_LOG.md.

## Project Structure

```
fax-machine-box/
├── src/faxbox/           # Python generators
│   ├── config.py         # All dimensions and constants
│   ├── generate_drawers.py
│   ├── generate_lids.py
│   └── shell_generator.py
├── tests/                # pytest dimension tests
│   ├── conftest.py       # Config fixtures
│   └── test_dimensions.py
├── output/               # Generated SVGs (gitignored)
└── assets/fonts/         # Press Start 2P font
```

## Build & Test

```bash
python3 -m pip install -e .              # Install project
python3 -m faxbox.test_generator         # Test box (proof of concept)
python3 -m faxbox.generate_drawers       # Generate drawer SVGs
python3 -m faxbox.shell_generator        # Generate outer shell SVGs
python3 -m faxbox.generate_lids          # Generate lid SVGs
python3 -m faxbox.layout                 # Generate final combined layout
pytest tests/                            # Run dimension validation tests
```

## Boxes.py Patterns

**Critical call sequence:** `parseArgs()` → `open()` → `render()` → `close()`

**Edge types** (counter-clockwise from bottom-left):
- `F` = finger joints (male), `f` = finger holes (female), `e` = plain edge

**Common edge combinations:**
- Open-top drawer: Front "Ffef", Sides "FFeF", Bottom "ffff"
- Simple flat pieces (lids): "eeee"

**Callbacks:** Array of 4 functions [bottom, right, top, left] called at edge start
```python
self.rectangularWall(x, h, "Ffef", callback=[add_hole, None, None, None])
```

**Engraving:** ctx.fill() NOT implemented - use stroke() with closed paths
```python
self.ctx.set_source_color([1.0, 0.0, 0.0])  # RGB [0-1]
```

## Dependencies

- Boxes.py from GitHub: `boxes @ git+https://github.com/florianfesti/boxes.git`
- PyPI "boxes" is WRONG package

## SVG Color Coding (Ponoko Compatible)

- Blue `rgb(0,0,255)` = cut lines
- Red `rgb(255,0,0)` = engrave lines
- `layout.py` converts black strokes to blue via `convert_colors_to_ponoko()`
- Must strip metadata with namespace prefixes (rdf:, cc:, dc:) when combining SVGs

## Gotchas

- File names must match acceptance criteria commands exactly
- No CI workflows configured - can push directly
- Check `git status` for uncommitted work from previous agents
- `--outside 0` means dimensions are internal; external = internal + 2×thickness
- ~~Config coordinate naming differs from spec~~ — fixed in #15: DESIGN.md defines the canonical X/Y/Z convention; config.py follows it. The legacy `SHELL`/`DRAWER` dicts are DEPRECATED aliases only.
- **Boxes.py draws a black 100×10mm calibration rectangle** in every output unless the generator passes `--reference 0`. Rebuilt generators (#17/#18) must pass `--reference 0` so files are laser-clean; the test harness detects it geometrically meanwhile.
- Boxes.py SVG structure: a piece's outer boundary and its finger teeth are one continuous `<path>`, but holes are sometimes separate sibling paths — count pieces by bbox containment clustering (see `tests/svg_utils.py`), never by raw path count or `<g>` grouping.
- The harness treats a contained path as a *hole* only if < 50% of its container's area (`HOLE_AREA_RATIO`) — otherwise a mispositioned full-size piece nested inside another's bbox would be silently swallowed instead of flagged as overlap.
- Test policy (Ben, issues #7/#10): tests are never weakened to pass. Broken-generator expectations are `xfail(strict=False)` with the rebuild issue cited in the reason; rebuilds remove the markers.
- **Boxes.py 'f' AND 'F' edges both protrude** by one thickness (they're phase complements for corner joints). For a panel inset flush with wall tops, edge-to-edge joints are wrong — join via `fingerHolesAt` lines inside the wall instead (panel finger tips end flush with the exterior). Caught in #17 review via landmark measurement; the blank-size band that would have masked it is now tightened (walls' Z axis = 0 jointed edges).
- `edges.CompoundEdge(self, types, lengths)` works for mixed finger/plain edges but all segments share one baseline — it cannot express per-segment height offsets.
- `layout.py` (#19) nests parts onto laser-bed-sized sheets with a deterministic shelf/row packer: sort pieces tallest-first, place each into the shortest existing shelf (row) with both enough height and enough remaining width, opening a new shelf (same sheet if there's vertical room, else a new sheet) when none fits. No rotation, no splitting — each piece is one rigid rectangle read straight from a source SVG's per-part `<g>` (Boxes.py's own grouping), translated into its sheet position by re-serializing each `<path>`'s `d` via `svgpathtools` (`Path.translated()` + `.d()`) rather than relying on nested SVG `transform`s some laser software handles inconsistently.
