# HANDOFF — fax-machine-box

Updated 2026-07-07 on branch `iter2-retention-magnets` (built off `main`,
NOT off the sibling `iter2-retention` branch/PR #22 — that branch holds an
alternative, more complex spring-detent mechanism; this branch is the
**recommended** iteration-2 path per Ben's issue #20 decision record: magnet
drawer retention + a lid turn-button). Everything below is committed and
pushed to this branch; PR #23 open to `main`, not merged.

**This branch went through adversarial review after the first push and was
corrected before anything was cut** — see "Adversarial-review findings
(fixed on this branch)" below before touching the lid-retention or magnet
coupon code; the ORIGINAL lid mechanism (a pivoting paddle on each side
wall) was geometrically incapable of retaining anything and has been
replaced.

## TL;DR for the next agent

`main` is cut-ready (v1, no retention: 21 parts nested on 3 sheets + a kerf
coupon, 164 tests green). **This branch adds iteration-2 retention** on top
of that: a magnet pair per drawer (drawer leading wall ↔ divider) and ONE
turn-button on the FRONT WALL (not the side walls — see below), per issue
#20's decision record. **187 tests green** (164 v1 + 23 retention tests),
all v1 tests untouched. Nothing physically cut yet on either mechanism. See
DESIGN.md's "Retention (iteration 2, magnets + turn-buttons)" section for
full geometry and derivations before touching anything; run
`.venv/bin/python -m pytest tests/ -q` before and after any change.

## Adversarial-review findings (fixed on this branch)

The first version of this branch shipped 183 tests green but had a
**critical, ship-blocking geometry bug** that the test suite itself never
caught — a reminder that green tests only check what someone thought to
assert.

1. **CRITICAL — the lid turn-button retained nothing.** The original
   design put a pivoting paddle on EACH side wall, just behind that wall's
   lid-slot mouth. Proof it could never work: a side-wall paddle sweeps
   that wall's own EXTERIOR plane (e.g. left wall Y −3.175→0), while the
   lid's edge riding in that wall's through-slot occupies Y 0.75→3.175 and
   exits by travelling along X — the two are disjoint volumes at every
   pivot position and paddle length; nothing was ever being blocked. Fixed
   by moving to ONE button on the FRONT WALL's exterior face (the plane the
   lid's own front edge actually crosses on exit). The side-wall pivot
   holes are gone; the side walls are now byte-identical to `main`'s v1
   geometry (verified against `main`'s own regenerated output, not just a
   source diff). A new "blocking test"
   (`test_button_up_envelope_blocks_lid_exit`) now asserts the button-up
   envelope actually overlaps the lid's exit cross-section — the assertion
   whose absence let the broken design ship in the first place.
2. **Shopping list was wrong.** README said 2× disc magnets; the design
   needs 4 (one attracting pair × 2 drawers). Fixed to 6× (4 + 2 spares),
   with hardware counts corrected to match the single button (1 bolt, 1
   nyloc, 2 washers, not 2/2/4).
3. **Magnet coupon measured the wrong thing.** The coupon's gauge holes
   were drawn burn-NEUTRAL (like the kerf square) while the real part holes
   are burn-COMPENSATED — so a labeled-5.65mm coupon hole was physically
   ~0.16mm different from what a labeled-5.65mm PART hole actually gets,
   eating ~46% of the 0.35mm press-fit budget before a magnet was ever
   pressed in. Fixed: the coupon now draws its gauge holes through the SAME
   `self.hole()` burn-compensated path as the real parts. The kerf square
   itself is untouched (it correctly stays burn-neutral — it measures the
   kerf, a different job).
4. **Drawer magnet leading-end float was undocumented.** The drawer has up
   to ±4.9mm of lateral play in the bay before the faceplate's own fit
   narrows it down in the final ~2.4mm of travel — the two magnet holes are
   not guaranteed dead-center-coaxial on first approach. DESIGN.md and
   README now state this plainly and prescribe a self-registering install
   (mark the drawer-side magnet's actual contact point through the divider
   hole during a dry test-fit, rather than trusting the nominal hole
   positions blindly).

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

**Done and verified (iteration 2, THIS branch, post adversarial-review fix):**
- Full suite: **187 passed, 0 failed, 0 xfail**
  (`.venv/bin/python -m pytest tests/ -q`, ~16s) — the original 164 v1
  tests untouched, plus 23 retention tests in `tests/test_retention.py`
  (19 original + 4 net new from the review fixes: front-wall pivot tests,
  side-wall regression guards, the blocking test, and the magnet-coupon
  cross-check). The suite regenerates all SVGs first, so it always tests
  current code.
- Magnet drawer retention: `MAGNET_DIA`/`MAGNET_PRESS_FIT`/`MAGNET_HOLE_DIA`
  (config.py), holes cut into the divider (2×, one per drawer) and each
  drawer's Back (leading) wall — verified coaxial at closed position via
  independent rear-wall/divider datums, not just self-consistency with the
  generator's own constants. Leading-end lateral float (±4.9mm bay play,
  narrowed only in the faceplate's final ~2.4mm of travel) is now
  documented in DESIGN.md/README with a self-registering install mitigation
  (finding #4).
- Lid turn-button, REV.B: ONE pivot hole, on the FRONT WALL's exterior face
  (`TURN_BUTTON_PIVOT_BOX_Y/Z` in config.py), not the side walls. 1
  standalone `Turn Button` piece (`output/hardware.svg`,
  `generate_hardware.py`, down from 2). A new blocking test
  (`test_button_up_envelope_blocks_lid_exit`) verifies the button-up
  envelope actually overlaps the lid's exit cross-section in both Y and Z
  with real margin, using the paddle's MEASURED reach off the real SVG, not
  assumed config values — the check whose absence let REV.A (side-wall
  paddles) ship despite being geometrically incapable of retention. The
  side walls are verified byte-identical to `main`'s own v1 output
  (`test_side_wall_matches_main_footprint`, diffed against a live
  regeneration of `main`'s source via `git show`, not just eyeballed).
- Magnet press-fit coupon (`output/magnet_coupon.svg`,
  `calibration.py`'s `generate_magnet_coupon()`): 4 gauge holes, now
  burn-COMPENSATED (same `self.hole()` path as the real part holes) instead
  of burn-neutral — a labeled-5.65mm gauge hole is now physically identical
  to a labeled-5.65mm part hole (finding #3). The kerf square stays
  burn-neutral, unchanged.
- All new/changed geometry visually verified via rendered PNGs (front wall,
  hardware, magnet coupon) — not just numerically; confirmed no pivot holes
  remain on either side wall.
- DESIGN.md, README.md, this file updated (REV.B mechanism description,
  corrected shopping list, single-button hardware counts, adversarial-review
  findings section, self-registering magnet install); `docs/` untouched.

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
   a comment. Don't fit the magnets/turn-button bolt until after the full
   dry-fit and glue-up (README "Iteration-2 retention hardware").

## Build/test baseline

`.venv/bin/python -m pytest tests/ -q` → `187 passed in ~16s` on this
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
  a lid turn-button is the recommended path** (this branch), chosen over
  the experimental spring-detent alternative (PR #22) for being the
  most-likely-to-work, tuning-free option. Ben is fine buying magnets + 1
  M3 bolt. See DESIGN.md's "Retention (iteration 2...)" section for the
  full geometry.
- **REV.B (adversarial review, 2026-07-07, locked): ONE turn-button on the
  FRONT WALL, not a pair on the side walls.** The original side-wall design
  (REV.A) was proven geometrically incapable of retention (disjoint
  sweep/travel volumes — see DESIGN.md section B) and was replaced before
  any part was cut. Do not revert to a side-wall pivot without re-solving
  that geometry problem from scratch.
- Flagged deviation (REV.B, minimal/sound, see DESIGN.md): the turn-button,
  rotated fully vertical, tips at box Z=127.5, standing proud in open air
  above/in front of the lid-slot region — accepted as harmless (nothing is
  there to hit) rather than shortening the button below its required reach
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
  requirements; `test_retention.py` = new this branch, 23 iteration-2 tests
  post adversarial-review fixes). `conftest.py` also picked up a PYTHONPATH
  fix (ported from
  branch `iter2-retention`'s red-team FIX4) so subprocess regeneration
  always tests THIS checkout's `src/`, not a stale editable-install path.
- History/rationale: `SESSION_LOG.md` (chronological), `LEARNINGS.md`
  (distilled), GitHub issues #12–#20 (decision record in comments).
- Cut-day instructions: `README.md` bottom half (now includes both
  coupons + the turn-button/magnet install order).
