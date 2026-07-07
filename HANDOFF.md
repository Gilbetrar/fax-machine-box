# HANDOFF — fax-machine-box

Updated 2026-07-07 on branch `iter2-retention-magnets` (built off `main`,
NOT off the sibling `iter2-retention` branch/PR #22 — that branch holds an
alternative, more complex spring-detent mechanism; this branch is the
**recommended** iteration-2 path per Ben's issue #20 decision record: magnet
drawer retention + lid turn-buttons). Everything below is committed and
pushed to this branch; PR open to `main`, not merged.

## TL;DR for the next agent

`main` is cut-ready (v1, no retention: 21 parts nested on 3 sheets + a kerf
coupon, 164 tests green). **This branch adds iteration-2 retention** on top
of that: a magnet pair per drawer (drawer leading wall ↔ divider) and
turn-buttons at the lid slot mouths, per issue #20's decision record. 183
tests green (164 v1 + 19 new retention tests), all v1 tests untouched.
Nothing physically cut yet on either mechanism. See DESIGN.md's "Retention
(iteration 2, magnets + turn-buttons)" section for full geometry and
derivations before touching anything; run
`.venv/bin/python -m pytest tests/ -q` before and after any change.

## What this project is

A laser-cut plywood storage box for Ben's "Fax Machine" pen-and-paper game:
12"×6.5"×5" envelope, front paper compartment with a sliding lid, rear bay
with two stacked drawers with flush faceplates, "FAX MACHINE" pixel-font
engraving. Python generators (Boxes.py) emit SVGs; a test harness parses the
actual SVG geometry and gates correctness. The dimensions come from Ben's
**fully functional cardboard prototype**, so contents-fit is already
physically validated.

## Current state — honest ledger

**Done and verified (v1, on `main`):**
- Issues #13–#19 all closed with evidence comments (GitHub).
- Bed size resolved: NYC Resistor runs an Epilog Fusion 32 60W, 32"×20"
  bed; the scary "12×24" figure was a stale 2013 comment about their old
  machine (sources in docs/service-comparison.md). All sheets fit.
- Red-team (4 Opus critics, 3 passes) found and we fixed: an
  assembly-impossible top-panel joint, red part labels that would have
  engraved, hollow engraving, an impossible README assembly order, a
  thickness-relative `play` unit bug, a self-defeating kerf-square, a
  grip-slot ligament bug, drawer in-stop. Details: SESSION_LOG.md
  (2026-07-07 entries) and the issue comments.

**Done and verified (iteration 2, THIS branch):**
- Full suite: **183 passed, 0 failed, 0 xfail**
  (`.venv/bin/python -m pytest tests/ -q`, ~15s) — the original 164 v1
  tests untouched, plus 19 new tests in `tests/test_retention.py`. The
  suite regenerates all SVGs first, so it always tests current code.
- Magnet drawer retention: `MAGNET_DIA`/`MAGNET_PRESS_FIT`/`MAGNET_HOLE_DIA`
  (config.py), holes cut into the divider (2×, one per drawer) and each
  drawer's Back (leading) wall — verified coaxial at closed position via
  independent rear-wall/divider datums, not just self-consistency with the
  generator's own constants.
- Lid turn-buttons: pivot holes cut into both side walls (mirrored), 2 new
  standalone `Turn Button` pieces (`output/hardware.svg`,
  `generate_hardware.py`) with sufficient pivot-to-tip reach, verified clear
  of the engrave zone and all other wall features.
- Magnet press-fit coupon (`output/magnet_coupon.svg`,
  `calibration.py`'s `generate_magnet_coupon()`): 4 burn-neutral gauge holes.
- All new geometry visually verified via rendered PNGs (divider, both side
  walls, drawer Back panel, turn button, magnet coupon) — not just
  numerically.
- DESIGN.md, README.md updated (new "Retention (iteration 2...)" section,
  shopping list, cut-day additions); `docs/` untouched.

**Open / not done:**
- **This PR is not merged.** It's the recommended path vs. the experimental
  spring-detent alternative on PR #22 (branch `iter2-retention`) — Ben
  reviews both before picking one to merge.
- Nothing has been physically cut on EITHER iteration. BURN=0.08,
  FINGER_PLAY=0.1, and (new) MAGNET_PRESS_FIT=0.35 are all UNCALIBRATED
  starting values — the coupon workflow (README "Cut-day checklist" steps
  3/3a) exists precisely because of this.
- The Fusion 32 bed size is medium-high confidence from web research; a
  five-second look at the machine on cut day is the final confirmation.

## Next concrete steps (in order)

1. Ben reviews this PR against PR #22 (spring detents) and picks one (or
   neither) to merge to `main`.
2. Fresh-eyes check on whichever gets merged: `git pull`, run the suite,
   regenerate outputs, open the sheet SVGs + `hardware.svg` +
   `magnet_coupon.svg` and eyeball them (piece labels are gray reference
   text; blue=cut, red=engrave hatching on the right wall only).
3. When Ben schedules the cut: walk him through README "Cut-day checklist"
   steps 1–8 in order. The coupon-first calibration (steps 3, 3a) is the
   one thing that must not be skipped — if measured kerf ≠ 0.08:
   `BURN = (measured_square − 10.0)/2` in config.py, regenerate everything
   including BOTH coupons, re-cut both, then cut sheets. If this branch
   (magnets) was merged, also press-fit-test the magnet coupon and set
   `MAGNET_PRESS_FIT` before cutting the divider/drawer parts.
4. Consider exporting sheets to PDF before cut day — NYC Resistor's wiki
   warns their CorelDraw X5 import can mangle some SVGs (sheets are
   Inkscape-namespace-free, but PDF is the belt-and-suspenders).
5. After the physical cut: capture lessons into LEARNINGS.md and the
   calibrated BURN/FINGER_PLAY/MAGNET_PRESS_FIT values into config.py with
   a comment. Don't fit the magnets/turn-button bolts until after the full
   dry-fit and glue-up (README "Iteration-2 retention hardware").

## Build/test baseline

`.venv/bin/python -m pytest tests/ -q` → `183 passed in ~15s` on this
branch (verify current HEAD matches or is ahead); `main` alone is `164
passed in ~13s` at commit `34dda01`. venv already exists; if rebuilding:
`python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"` (Boxes.py comes
from GitHub — needs network; PyPI "boxes" is the wrong package).

## Decisions made (locked — do not relitigate)

- Ben's design decisions 2026-07-07: drawers open from the rear 6.5" face;
  engraving on the right 12" side wall; fixed top panel over the bay;
  sliding lid via through-slots entering from the front; NYC Resistor;
  uniform 3.175mm ply.
- Lid slot vertical clearance is 0.8mm, a documented deviation from SPEC's
  1.5mm (DESIGN.md explains why; README discloses it).
- No retention in v1 (Ben, prior session): lid/drawers slide out when
  tipped; documented in README "Know before you build".
- Faceplates sit recessed 0.475mm when closed (the slide gap) — "near
  flush" is correct behavior, not a bug.
- **Iteration 2 retention mechanism (Ben, issue #20, 2026-07-07): magnets +
  turn-buttons is the recommended path** (this branch), chosen over the
  experimental spring-detent alternative (PR #22) for being the
  most-likely-to-work, tuning-free option. Ben is fine buying magnets + 2
  M3 bolts. See DESIGN.md's "Retention (iteration 2...)" section for the
  full geometry.
- Flagged deviation (this branch, minimal/sound, see DESIGN.md): the
  turn-button, rotated fully vertical, overhangs 2.5mm above the wall's own
  top edge (not just "into the rail zone" as first anticipated) — accepted
  as harmless rather than shortening the button below its required reach
  margin.

## Hard constraints

- **DESIGN.md is the single geometry authority.** Config implements it;
  tests enforce it. Change DESIGN.md first or not at all.
- **Never weaken a test to make it pass** (Ben's standing rule, enforced
  since issue #7). The red-team specifically hardened the suite with
  positional/mating assertions that catch demonstrated green-but-broken
  mutations — treat any urge to loosen a tolerance as a design smell.
- Boxes.py `FingerJoint play` is RELATIVE to thickness — generators must
  pass `FINGER_PLAY_RELATIVE`, never the raw mm value.
- The kerf square in calibration.py must stay burn-neutral (raw ctx path).

## Gotchas (full list in LEARNINGS.md — read it)

Highlights: 'f' and 'F' edges BOTH protrude one thickness (flush panel
joints need `fingerHolesAt` hole lines, not edge joints); a fingered edge
segment must equal its mating hole-row length exactly (CompoundEdge trick);
`--reference 0` required or Boxes.py draws a black calibration rectangle;
ctx.fill() unimplemented (engraving = hatched strokes); piece detection is
bbox-containment clustering with 0.2mm tolerance (tests/svg_utils.py);
`<text>` fill colors are live laser instructions (labels are gray for a
reason). Ben's terminal can't copy-paste — never hand him commands to paste;
run them yourself or write files.

## Where everything lives

- Repo: `Gilbetrar/fax-machine-box` (GitHub), local `~/AI/Projects/
  fax-machine-box`, branch `iter2-retention-magnets` (PR to `main`, not
  merged), all pushed.
- Geometry spec: `DESIGN.md` (see "Retention (iteration 2...)" section).
  Dimensions: `src/faxbox/config.py`.
- Generators: `src/faxbox/{shell_generator,generate_drawers,generate_lids,
  layout,calibration,generate_hardware}.py` (`generate_hardware.py` is new
  this branch).
- Tests: `tests/` (svg_utils.py = parsing helpers; assembly-fit = config
  math; svg_geometry = real-SVG positional checks; layout; laser
  requirements; `test_retention.py` = new this branch, the 19 iteration-2
  tests). `conftest.py` also picked up a PYTHONPATH fix (ported from
  branch `iter2-retention`'s red-team FIX4) so subprocess regeneration
  always tests THIS checkout's `src/`, not a stale editable-install path.
- History/rationale: `SESSION_LOG.md` (chronological), `LEARNINGS.md`
  (distilled), GitHub issues #12–#20 (decision record in comments).
- Cut-day instructions: `README.md` bottom half (now includes both
  coupons + the turn-button/magnet install order).
