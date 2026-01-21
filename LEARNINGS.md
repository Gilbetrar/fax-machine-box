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
├── preview/              # 3D preview (Three.js)
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

## 3D Preview (preview/)

- Three.js via ES module importmaps (no bundler needed)
- OrbitControls for camera rotation/zoom
- Raycasting for part selection
- Open `preview/index.html` in browser

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
- Sliding lids need grooves on BOTH sides
- `--outside 0` means dimensions are internal; external = internal + 2×thickness
- Config coordinate naming differs from spec: config "width"=12" is spec "length", config "depth"=6.5" is spec "width"
