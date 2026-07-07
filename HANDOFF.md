# HANDOFF — fax-machine-box

Written 2026-07-07 by the session that rebuilt the geometry and ran the
red-team. Everything is committed and pushed to `main` (clean tree, nothing
local-only). You are the wrap-up agent.

## TL;DR for the next agent

The project is **cut-ready**: 21 parts nested on 3 sheets + a kerf coupon,
164 tests green, geometry adversarially reviewed across 3 red-team passes.
There is no unfinished code. Your job is wrap-up: sanity-check the final
state, support Ben through cut day (see README's 8-step checklist), and —
only if he asks — start iteration 2 (issue #20, retention). Read DESIGN.md
before touching anything; run `.venv/bin/python -m pytest tests/ -q` before
and after any change.

## What this project is

A laser-cut plywood storage box for Ben's "Fax Machine" pen-and-paper game:
12"×6.5"×5" envelope, front paper compartment with a sliding lid, rear bay
with two stacked drawers with flush faceplates, "FAX MACHINE" pixel-font
engraving. Python generators (Boxes.py) emit SVGs; a test harness parses the
actual SVG geometry and gates correctness. The dimensions come from Ben's
**fully functional cardboard prototype**, so contents-fit is already
physically validated.

## Current state — honest ledger

**Done and verified:**
- Issues #13–#19 all closed with evidence comments (GitHub).
- Full suite: **164 passed, 0 failed, 0 xfail** (`.venv/bin/python -m pytest
  tests/ -q`, ~13s). The suite regenerates all SVGs first, so it always
  tests current code.
- Red-team (4 Opus critics, 3 passes) found and we fixed: an
  assembly-impossible top-panel joint, red part labels that would have
  engraved, hollow engraving, an impossible README assembly order, a
  thickness-relative `play` unit bug, a self-defeating kerf-square, a
  grip-slot ligament bug, drawer in-stop. Details: SESSION_LOG.md
  (2026-07-07 entries) and the issue comments.
- Bed size resolved: NYC Resistor runs an Epilog Fusion 32 60W, 32"×20"
  bed; the scary "12×24" figure was a stale 2013 comment about their old
  machine (sources in docs/service-comparison.md). All sheets fit.
- Outputs (regenerate any time, they're gitignored): `output/sheet_1..3.svg`
  (cut files), `output/kerf_coupon.svg` (cut FIRST on scrap),
  `output/final_layout.svg` (reference only, too big for the bed).

**Open / not done:**
- Issue #20 (open, deferred by Ben): lid + drawer retention for the NEXT
  iteration. Ben explicitly said ship v1 without it. Do not start unless he
  asks.
- Nothing has been physically cut. BURN=0.08 and FINGER_PLAY=0.1 are
  UNCALIBRATED starting values — the coupon workflow in README step 3
  exists precisely because of this.
- The Fusion 32 bed size is medium-high confidence from web research; a
  five-second look at the machine on cut day is the final confirmation.

## Next concrete steps (in order)

1. Fresh-eyes check: `git pull`, run the suite, regenerate outputs, open
   the three sheet SVGs and eyeball them (piece labels are gray reference
   text; blue=cut, red=engrave hatching on the right wall only).
2. When Ben schedules the cut: walk him through README "Cut day at NYC
   Resistor" steps 1–8 in order. The coupon-first calibration (step 3) is
   the one thing that must not be skipped. If measured kerf ≠ 0.08:
   `BURN = (measured_square − 10.0)/2` in config.py, regenerate everything
   including the coupon, re-cut coupon, then cut sheets.
3. Consider exporting sheets to PDF before cut day — NYC Resistor's wiki
   warns their CorelDraw X5 import can mangle some SVGs (sheets are
   Inkscape-namespace-free, but PDF is the belt-and-suspenders).
4. After the physical cut: capture lessons into LEARNINGS.md and the
   calibrated BURN/FINGER_PLAY values into config.py with a comment.
5. Iteration 2 = issue #20, only on Ben's go.

## Build/test baseline

`.venv/bin/python -m pytest tests/ -q` → `164 passed in ~13s` at commit
`1302903` (verify current HEAD matches or is ahead). venv already exists;
if rebuilding: `python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"`
(Boxes.py comes from GitHub — needs network; PyPI "boxes" is the wrong
package).

## Decisions made (locked — do not relitigate)

- Ben's design decisions 2026-07-07: drawers open from the rear 6.5" face;
  engraving on the right 12" side wall; fixed top panel over the bay;
  sliding lid via through-slots entering from the front; NYC Resistor;
  uniform 3.175mm ply.
- Lid slot vertical clearance is 0.8mm, a documented deviation from SPEC's
  1.5mm (DESIGN.md explains why; README discloses it).
- No retention in v1 (Ben, this session): lid/drawers slide out when
  tipped; documented in README "Know before you build".
- Faceplates sit recessed 0.475mm when closed (the slide gap) — "near
  flush" is correct behavior, not a bug.

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
  fax-machine-box`, branch `main`, all pushed.
- Geometry spec: `DESIGN.md`. Dimensions: `src/faxbox/config.py`.
- Generators: `src/faxbox/{shell_generator,generate_drawers,generate_lids,
  layout,calibration}.py`.
- Tests: `tests/` (svg_utils.py = parsing helpers; assembly-fit = config
  math; svg_geometry = real-SVG positional checks; layout; laser
  requirements).
- History/rationale: `SESSION_LOG.md` (chronological), `LEARNINGS.md`
  (distilled), GitHub issues #12–#20 (decision record in comments).
- Cut-day instructions: `README.md` bottom half.
