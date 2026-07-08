# HANDOFF — fax-machine-box

Updated 2026-07-07 on branch `iter2-retention` by the session that ran a
THIRD retention red-team pass (pass-3) and fixed its findings on top of the
earlier pass-2 fixes. Do not treat this file's timestamp as "nothing has
changed since v1" — issue #20 (lid + drawer retention) is now DONE on this
branch, including a full mechanism replacement AND a pass-3 fix round (see
below). Read DESIGN.md's "Retention (iteration 3)" section before touching
any retention geometry.

## TL;DR for the next agent

The project is **cut-ready with retention included**: 21 parts nested on 3
sheets + a kerf coupon + a 5-piece retention coupon, 192 tests green,
geometry adversarially reviewed (shell/drawer/lid geometry across 3 earlier
red-team passes on `main`, retention across a pass-2 AND pass-3 red-team
pass on this branch). There is no unfinished code and no open TODO. Your
job is wrap-up: sanity-check the final state, support Ben through cut day
(see README's checklist — kerf coupon, THEN retention coupon, THEN real
sheets), and merge this branch when Ben says go. Run
`.venv/bin/python -m pytest tests/ -q` before and after any change (no
shell-level `PYTHONPATH` override needed — `tests/conftest.py` now puts
this checkout's own `src/` at the front of `sys.path` at import time, so
even a git-worktree checkout tests its OWN code in-process, not just in
regeneration subprocesses — see pass-3 F1 below).

## Pass-3 red-team fixes (this session, on top of pass-2)

A pass-2 critic caught four more findings; all four are now fixed, with
tests proving each catches its own regression (mutate -> red -> revert ->
green):

- **F1 (CRITICAL)**: `tests/conftest.py`'s `os.environ["PYTHONPATH"]`
  assignment only affected subprocesses, not pytest's own in-process
  imports — a worktree checkout's test run could silently exercise a
  DIFFERENT checkout's `faxbox` code. Fixed with `sys.path.insert(0, ...)`
  at conftest import time (before any `faxbox` import in the session).
- **F2 (CRITICAL)**: the drawer's own Bottom panel is a solid sheet
  directly under the flexure nub's swept path — no clearance opening
  existed there before this fix, so the nub had nowhere to go. Fixed with
  a rectangular clearance slot per side wall through `generate_drawers.py`'s
  Bottom panel (`DRAWER_BOTTOM_SLOT_X_LENGTH` / `..._Y_SPAN` in config.py).
- **F3 (MAJOR)**: the drawer flexure's free tip rises MORE than its own
  designed nub engagement (it overhangs past the nub's load point), so the
  shared `DETENT_CLEARANCE` (2.5mm) cavity was too shallow for the drawer
  mechanism specifically — it would bind at ~1.85mm, short of the designed
  2.2mm engagement. Fixed with a `config._tip_rise` formula and per-
  mechanism cavities (`LID_DETENT_CAVITY` ≈2.5, unchanged;
  `DRAWER_DETENT_CAVITY` ≈3.47, deeper).
  - Verified: cavity has room within the drawer side's 53.5mm height, no
    web thinner than `MIN_WEB` (3.0mm) introduced.
- **F4 (MAJOR)**: catch-hole↔nub registration was untested end-to-end (a
  `CATCH_HOLE_X += 5.0` mutation stayed green), and
  `DRAWER_DETENT_NUB_BASE_WIDTH` was misnamed (its value is the nub's width
  at the FLOOR plane, not its actual widest "base"). Fixed with a new
  independent-datum registration test
  (`test_catch_hole_registers_with_nub_via_independent_datums`) and a
  rename/split into `NUB_WIDTH_AT_FLOOR_PLANE` / `NUB_WIDTH_AT_WALL_PLANE`.

See DESIGN.md's "Retention (iteration 3)" section for the full derivation
of each fix.

## What this project is

A laser-cut plywood storage box for Ben's "Fax Machine" pen-and-paper game:
12"×6.5"×5" envelope, front paper compartment with a sliding lid, rear bay
with two stacked drawers with flush faceplates, "FAX MACHINE" pixel-font
engraving. Both the lid and the drawers have spring-detent retention
(issue #20) so they don't slide out if the box tips. Python generators
(Boxes.py) emit SVGs; a test harness parses the actual SVG geometry and
gates correctness. The dimensions come from Ben's **fully functional
cardboard prototype**, so contents-fit is already physically validated.

## Current state — honest ledger

**Done and verified:**
- Issues #13–#19 all closed on `main` with evidence comments (GitHub).
- Issue #20 (retention) done on this branch, INCLUDING a full red-team
  pass that found the first drawer mechanism (a nub on the faceplate) was
  geometrically impossible — a faceplate is a Y-Z plate, the drawer
  travels along X (normal to that plate), so a laser-cut ramp there is
  never swept by the drawer's own motion. That mechanism was removed
  entirely (faceplate is back to its exact original blank) and replaced
  with a cantilever flexure in each drawer SIDE wall (an X-Z part, so its
  ramp genuinely cams). The lid mechanism's kinematics were always sound;
  only its beam strain was refit (nub moved from mid-beam to the beam's
  free end — see DESIGN.md).
- Full suite: **192 passed, 0 failed, 0 xfail** (`.venv/bin/python -m
  pytest tests/ -q`, ~17s — no shell-level `PYTHONPATH` override needed).
  The suite regenerates all SVGs first, so it always tests current code.
  `tests/conftest.py` forces this checkout's own `src/` onto BOTH the
  regeneration subprocess's PYTHONPATH AND the front of pytest's own
  in-process `sys.path` (pass-3 F1 — the env-var-only version could
  silently test a different checkout's code from a git WORKTREE, since it
  only affected subprocesses, not pytest's own already-resolved imports).
- Mutation-gate re-validated for `test_retention.py` (rewritten wholesale
  in the pass-2 session): 10/10 targeted mutations (wrong engagement depths, an
  inverted nub, a shifted notch, a broken mirror, a deleted release cut, a
  deleted coupon, a squared-off ramp, a plain-rectangle drawer side, a
  halved catch hole) each independently turn the suite red, then green
  again on revert. Full table in the PR description.
- Pass-3 mutation-gate (this session, all verified red -> green on
  revert): removing the F2 bottom-panel clearance slot, `CATCH_HOLE_X +=
  5.0`, and reverting `DRAWER_DETENT_CAVITY` to the old shared 2.5mm value
  (this last one required adding a new test — nothing previously caught
  it, since the strain test only checks bending stress, not cavity depth).
  See the PR #22 comment for the pass-3 summary.
- Burn compensation (previously "burn-neutral by design" for all
  hand-drawn retention shapes) is now applied consistently — see
  `faxbox/detent.py`'s module docstring for the exact model; the kerf-test
  square in `calibration.py` is the one deliberate exception (project
  rule: it measures kerf, it must not compensate for it).
- Bed size resolved: NYC Resistor runs an Epilog Fusion 32 60W, 32"×20"
  bed; sources in docs/service-comparison.md. All sheets fit both that and
  the conservative 24"×18" fallback `layout.py` still packs to.
- Outputs (regenerate any time, they're gitignored): `output/sheet_1..3.svg`
  (cut files, 21 parts total), `output/kerf_coupon.svg` (cut FIRST on
  scrap), `output/retention_coupon.svg` (cut SECOND on scrap — 5 pieces:
  Wall Flexure Sample, Lid Notch Strip, Drawer-Side Flexure Sample, Mock
  Sill Edge, Mock Floor Strip), `output/final_layout.svg` (reference only,
  too big for the bed).

**Open / not done:**
- Nothing has been physically cut. `BURN=0.08` and `FINGER_PLAY=0.1` are
  still UNCALIBRATED starting values — the coupon workflow in README steps
  3/3b exists precisely because of this, and now covers retention too
  (tune `LID_DETENT_ENGAGE` / `DRAWER_DETENT_ENGAGE` against the retention
  coupon after the kerf coupon, before cutting real parts).
- This branch (`iter2-retention`) has NOT been merged to `main` — it's
  pushed and PR #22 is open/updated, but merging is Ben's call, not
  automatic.
- The Fusion 32 bed size is medium-high confidence from web research; a
  five-second look at the machine on cut day is the final confirmation.
- Magnets (6mm discs, press-fit + CA) are the recorded fallback if either
  flexure proves too weak/brittle in practice or won't tune well on the
  coupon — not implemented, just documented (DESIGN.md, README) so it
  isn't rediscovered from scratch.

## Next concrete steps (in order)

1. Fresh-eyes check: `git pull` (this branch), run the suite, regenerate
   outputs, render the changed parts (walls, lid, drawer sides, bottom
   panel, shelf, coupon) and eyeball the retention features specifically —
   nub ramps, catch holes, the lid notch — since this is new geometry a
   quick visual pass is worth the five minutes.
2. Get Ben's go to merge `iter2-retention` into `main` (or continue
   iterating per his feedback on PR #22).
3. When Ben schedules the cut: walk him through README's cut-day
   checklist in order — kerf coupon (step 3) THEN retention coupon (step
   3b) THEN real sheets. Both coupon steps must not be skipped; the
   retention coupon in particular is the only real-world validation this
   project has for the drawer side-wall mechanism, which has never been
   physically cut. **Grain orientation is a hard gate** (README step 2) —
   both flexures depend on it.
4. After the physical cut: capture lessons into LEARNINGS.md and the
   calibrated `BURN`/`FINGER_PLAY`/`LID_DETENT_ENGAGE`/
   `DRAWER_DETENT_ENGAGE` values into config.py with a comment.

## Build/test baseline

`.venv/bin/python -m pytest tests/ -q` → `192 passed in ~17s` on branch
`iter2-retention` (verify current HEAD matches or is ahead). venv already
exists; if rebuilding: `python3 -m venv .venv && .venv/bin/pip install -e
".[dev]"` (Boxes.py comes from GitHub — needs network; PyPI "boxes" is the
wrong package).

## Decisions made (locked — do not relitigate)

- Ben's design decisions 2026-07-07: drawers open from the rear 6.5" face;
  engraving on the right 12" side wall; fixed top panel over the bay;
  sliding lid via through-slots entering from the front; NYC Resistor;
  uniform 3.175mm ply.
- Lid slot vertical clearance is 0.8mm, a documented deviation from SPEC's
  1.5mm (DESIGN.md explains why; README discloses it).
- Retention (issue #20, this branch): both the lid and the drawers have
  spring-detent retention, not a hard lock — documented in README "Know
  before you build". The drawer mechanism lives in the SIDE panels, not
  the faceplate (locked after the red-team finding above — do not move it
  back to the faceplate).
- Faceplates are the exact original v1 blank again (150.9 × 53.5, plain
  edges) — no retention feature of their own. Recessed 0.475mm when closed
  (the slide gap) — "near flush" is correct behavior, not a bug.
- `DETENT_SEVER_CLEARANCE` (1.5mm, both mechanisms): the gap kept between
  a nub's own ramped base and its release/sever cut, so the sever cut
  can't undercut the nub's base and leave it bridged to the fixed material
  outward of it. Verified against the actual drawn geometry before being
  generalized into a named constant — don't let a future edit shrink this
  toward zero without re-checking that bridging concern.

## Hard constraints

- **DESIGN.md is the single geometry authority.** Config implements it;
  tests enforce it. Change DESIGN.md first or not at all.
- **Never weaken a test to make it pass** (Ben's standing rule, enforced
  since issue #7). The red-team specifically hardened the suite with
  positional/mating assertions and a mutation-gate exercise — treat any
  urge to loosen a tolerance as a design smell.
- Boxes.py `FingerJoint play` is RELATIVE to thickness — generators must
  pass `FINGER_PLAY_RELATIVE`, never the raw mm value.
- The kerf square in calibration.py must stay burn-neutral (raw ctx path)
  — the ONE deliberate exception to "all retention geometry is now
  burn-compensated."

## Gotchas (full list in LEARNINGS.md — read it)

Highlights: 'f' and 'F' edges BOTH protrude one thickness (flush panel
joints need `fingerHolesAt` hole lines, not edge joints); a fingered edge
segment must equal its mating hole-row length exactly (CompoundEdge trick —
now also used for the drawer side wall's flexure zone, via a purpose-built
Edge subclass standing in for one CompoundEdge segment); `--reference 0`
required or Boxes.py draws a black calibration rectangle; ctx.fill()
unimplemented (engraving = hatched strokes); piece detection is
bbox-containment clustering with 0.2mm tolerance (tests/svg_utils.py);
`<text>` fill colors are live laser instructions (labels are gray for a
reason); a nub whose ramped base straddles its own sever cut is NOT fully
freed by it (see `DETENT_SEVER_CLEARANCE` above) — this bit the initial
implementation of the drawer flexure before the coupon math was checked
against the actual drawn geometry. Ben's terminal can't copy-paste — never
hand him commands to paste; run them yourself or write files.

## Where everything lives

- Repo: `Gilbetrar/fax-machine-box` (GitHub), local `~/AI/Projects/
  fax-machine-box`, branch `iter2-retention` (this work), PR #22.
- Geometry spec: `DESIGN.md`. Dimensions: `src/faxbox/config.py`.
- Generators: `src/faxbox/{shell_generator,generate_drawers,generate_lids,
  layout,calibration}.py`. Shared retention geometry helpers:
  `src/faxbox/detent.py`.
- Tests: `tests/` (svg_utils.py = parsing helpers; assembly-fit = config
  math; svg_geometry = real-SVG positional checks; retention = retention
  mechanism checks, rewritten this session; layout; laser requirements).
- History/rationale: `SESSION_LOG.md` (chronological), `LEARNINGS.md`
  (distilled), GitHub issues #12–#20 (decision record in comments).
- Cut-day instructions: `README.md` bottom half.
