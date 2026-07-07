# Fax Machine Box

A laser-cut, fax-machine-themed desktop organizer, generated from
[Boxes.py](https://github.com/florianfesti/boxes) finger-joint parametric
box code. `DESIGN.md` is the canonical geometry reference — read it before
touching any dimension. This README covers building, testing, and cutting.

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
```

(A `.venv/` already exists in this repo checkout — use it directly, e.g.
`.venv/bin/python`, rather than re-creating it, unless it's missing or
broken.)

## Build

Generate every part, then nest them onto cut-ready sheets:

```bash
.venv/bin/python -m faxbox.shell_generator    # outer shell: 8 pieces -> output/outer_shell.svg
.venv/bin/python -m faxbox.generate_drawers   # one drawer's 6 pieces -> output/drawer.svg (cut TWICE)
.venv/bin/python -m faxbox.generate_lids      # sliding lid: 1 piece -> output/lids.svg
.venv/bin/python -m faxbox.layout             # nests all of the above onto output/sheet_1.svg, sheet_2.svg, ...
```

`layout.py` also writes `output/final_layout.svg` — a combined, true-scale
view of every sheet side by side, for eyeballing the whole nesting in a
browser in one shot. **`final_layout.svg` is bigger than any real laser bed
and must never be sent for cutting** — send `sheet_1.svg`, `sheet_2.svg`,
... individually. Each `sheet_N.svg` is itself real, complete, laser-ready
input: the right SVG to open and inspect before cutting is one of those, not
`final_layout.svg`.

## Test

```bash
.venv/bin/python -m pytest tests/ -v
```

The test suite regenerates `output/*.svg` from current source before
checking it (see `tests/conftest.py`), so it always measures what the code
*currently* produces, not stale files. All tests must be green with zero
`xfail`s before cutting anything — this is the project's standing policy
(see `LEARNINGS.md`).

## Project Structure

```
fax-machine-box/
├── src/faxbox/
│   ├── config.py            # single source of truth for all dimensions (implements DESIGN.md)
│   ├── shell_generator.py   # outer shell: bottom, 4 walls, divider, shelf, top panel (8 pieces)
│   ├── generate_drawers.py  # one drawer's 6 pieces (body x5 + faceplate); cut this sheet twice
│   ├── generate_lids.py     # sliding lid (1 piece)
│   └── layout.py            # nests all parts onto bed-sized sheets for cutting
├── tests/                   # pytest harness: geometry, laser-compliance, and layout checks
├── docs/service-comparison.md  # laser service comparison + verified NYC Resistor constraints
├── DESIGN.md                # canonical geometry — the source of truth for every number
└── output/                  # generated SVGs (gitignored)
```

## Color coding

- **Blue (`#0000FF`)** = cut line
- **Red (`#FF0000`)** = engrave line (the "FAX MACHINE" text on the right
  wall, and the faceplate glue-up registration outlines)

This is a convention this project chose (see DESIGN.md's "Decisions"
section), not a documented NYC Resistor requirement — no color convention
could be confirmed on their site. See `docs/service-comparison.md` for
details.

## Parts checklist

21 pieces total, all cut from uniform 3.175mm (1/8") plywood. Matches
DESIGN.md's parts list exactly.

**Outer shell — `output/sheet_*.svg`, 8 pieces, cut once (from
`outer_shell.svg`):**

- [ ] 1× Bottom panel (inset between the four walls)
- [ ] 1× Left Wall
- [ ] 1× Right Wall (carries the "FAX MACHINE" engraving)
- [ ] 1× Front Wall
- [ ] 1× Rear Wall (two drawer openings)
- [ ] 1× Vertical Divider (separates paper compartment from drawer bay)
- [ ] 1× Horizontal Shelf (splits the drawer bay into upper/lower slots)
- [ ] 1× Top Panel (fixed, over the drawer bay — **not** a removable lid)

**Drawers — 6 pieces × 2 identical sets = 12 pieces (from `drawer.svg`, cut
the same sheet TWICE):**

- [ ] 2× Front (body)
- [ ] 2× Back (body)
- [ ] 2× Left Side (body)
- [ ] 2× Right Side (body)
- [ ] 2× Bottom (body)
- [ ] 2× Faceplate (glued to the body front, not finger-jointed)

**Lid — 1 piece (from `lids.svg`):**

- [ ] 1× Sliding Lid (rides in through-slots cut into both side walls)

There is **no separate flat/tabbed lid** — that part doesn't exist in this
design. The drawer bay is covered by the fixed Top Panel above, not a
removable cover.

## Assembly steps

This is the *current* (post-rebuild) design: fixed top panel, through-slot
sliding lid, glued faceplate drawers, inset bottom panel. See DESIGN.md for
every number and the reasoning behind each joint.

**1. Inset the Bottom panel between the four walls.**
   Stand the Left Wall, Right Wall, Front Wall, and Rear Wall up and dry-fit
   the Bottom panel's edge fingers into the hole lines near each wall's
   bottom edge (not a corner-to-corner edge joint — the walls run full
   height and the bottom panel sits inset between them, flush with their
   bottom edges). Glue and clamp square.

**2. Add the Vertical Divider.**
   Slide the Divider's fingers down into the Bottom panel's hole line and
   into the Left/Right Wall hole lines (~3" / 79.4mm from the front). It's
   captive on all four edges and carries real structural load — its front
   face is also the sliding lid's end stop, so get it square and glued
   before moving on.

**3. Add the Horizontal Shelf.**
   Slide the Shelf into the side-wall hole lines at the bay's vertical
   midpoint, its front edge into the Divider's hole line, its rear edge
   butting the Rear Wall's interior face (plain, unglued butt joint is
   fine — it's captive on the other three edges). This splits the drawer
   bay into a bottom drawer slot and a top drawer slot.

**4. Glue on the fixed Top Panel.**
   The Top Panel's side and rear edges finger through hole lines in the
   side/rear walls near the top edge; its front edge sits plain, flush over
   the Divider's top edge. This is permanent — there is no way to remove it
   after assembly, by design (DESIGN.md: "Fixed top panel over the drawer
   bay, not a removable lid").

**5. Assemble both drawers (×2, identical).**
   For each drawer: finger-joint Front + Back + Left Side + Right Side at
   the vertical corners, then slide the Bottom panel into the hole lines at
   the base (captive, not edge-jointed). Test-fit each body in its rear-wall
   opening before gluing the faceplate on.

**6. Glue on the faceplates (×2).**
   Each Faceplate glues flush to its drawer body's front face — align it
   using the red-engraved registration outline on the faceplate's back
   (traces the body's front cross-section). The Faceplate's grip slot must
   line up with the body Front's grip slot so a finger can reach through
   both into the drawer once assembled. Faceplates sit flush with the rear
   wall's exterior plane when the drawer is closed.

**7. Slide in the Sliding Lid — last.**
   Insert the Sliding Lid from the front, over the Front Wall's top edge and
   into the through-slots cut into both side walls. It travels until it
   stops against the Vertical Divider's front face. The slots are open at
   the walls' front edge specifically so the lid *can* be inserted this way
   — there's no other assembly order that works for this part.

**Tips:**
- Dry-fit everything before gluing; the finger joints are meant to be snug,
  not force-fit.
- Glue the shell (steps 1–4) fully before starting the drawers — the
  Divider and Shelf are structural and should be square before anything
  else depends on their position.
- Sand lightly if any joint is tight; do not sand the sliding-lid slots or
  the drawer/opening clearances beyond what's needed for a smooth slide —
  they're already sized with SPEC's minimum 1.5mm play built in.

## Cut-day checklist (NYC Resistor)

See `docs/service-comparison.md` → "NYC Resistor cutting constraints
(verified 2026-07-07)" for the full writeup, sources, and what could **not**
be verified (notably: their stated 32"×20" bed is disputed by a comment on
their own page claiming the real cuttable area is smaller, 12"×24" — this
project plans against a conservative 18"×24" fallback instead of trusting
either number; verify the real bed in person).

1. **Material.** Bring your own 1/8" (3.175mm) plywood (Baltic Birch
   preferred) — BYO is explicitly welcome, or buy limited stock on-site
   (email ahead to confirm availability). Buy enough sheet to cover however
   many `sheet_*.svg` files `faxbox.layout` produced (it prints each
   sheet's real trimmed dimensions when run — currently 3 sheets, each well
   under the 18"×24" fallback).
2. **Take the laser class first** if you haven't (required for the $1/min
   self-serve rate; runs ~monthly). Operator-assisted time is $75/hr +
   $2/min if you skip it.
3. **Kerf test cut, first, before anything else.** `BURN = 0.08` in
   `src/faxbox/config.py` is a *starting value*, not a calibrated one. Cut a
   small scrap test pattern (e.g. two interlocking finger-joint tabs) at
   that burn setting, check the fit, and adjust `BURN` + regenerate if the
   joints are too tight or too loose. Do this before cutting any real part.
4. **File format.** Bring the `sheet_*.svg` files, but be ready to
   re-export as PDF on-site — NYC Resistor's own tips page warns Inkscape's
   SVG export can get corrupted in their CorelDraw-based workflow and
   recommends PDF instead. If exporting from Inkscape, export PDF, not SVG.
5. **Suggested cut order: engrave, then cut.** Engrave the red "FAX MACHINE"
   text and the faceplate registration outlines *before* cutting the blue
   outlines free — once a piece is cut loose it's much harder to keep flat
   and registered under the laser head for engraving.
6. **Confirm the color convention verbally with staff.** This project uses
   blue=cut / red=engrave, but that's not a documented NYC Resistor
   requirement (see `docs/service-comparison.md`) — double-check before
   the job runs, and re-export/recolor if their software expects something
   different.
7. **Cut all 3 sheets, then dry-fit before gluing anything** — see
   "Assembly steps" above.
