# HANDOFF — fax-machine-box

**Date:** 2026-07-08 · **Branch:** `handoff/artwork-and-fabrication` (in `~/AI/Projects/fax-machine-box`)
**Tracking:** issue #20 (decision record in comments), PRs #21/#23/#24 merged, PR #22 open-experimental
**Pushed:** yes → origin

## TL;DR for the next agent

`main` is complete, merged, and green (**200 tests**): the box design, magnet+turn-button retention, PDF export, and a Ponoko provider mode are all done. Nothing has been physically cut. The two live workstreams are (1) **fabrication routing** — Ben is asking his friend **Clark** (fabrication guy, likely owns a laser) to cut it for plywood+lunch; a fully-configured **Ponoko quote (~$153) sits ON HOLD in Ben's account as fallback**; and (2) **exterior artwork reproduction** — 12 photos of the hand-drawn cardboard prototype are in `art/originals/`, to be reconstructed as vector-line + raster-tone engrave layers. Do not start cutting/ordering or artwork tracing on your own initiative — both wait on Ben (Clark's reply; pilot-face art approval).

## What this project is

A laser-cut 3.175mm-birch-ply box for Ben's "Fax Machine" pen-and-paper game (telephone-pictionary passed as "faxes" — see https://press.invincible.ink/game-pile-fax-machine/). The box IS the game kit: a front vertical compartment holding pre-cut paper (the main point: many same-size paper sets), two rear drawers for pens/colored pencils, sliding lid over the paper, "FAX MACHINE" engraving. Ben's fully-functional hand-drawn cardboard prototype (photos in `art/originals/`) provided the dimensions and carries dense colorful artwork he wants reproduced on wood. Endgame: several boxes as gifts for friends, with nice pen kits and paper-cutting done for them.

## Current state (honest ledger)

- **Done & verified:** main = v1 geometry + iteration-2 retention (magnet pair per drawer: leading wall ↔ divider; ONE turn-button on the FRONT wall exterior — side-wall version was proven zero-retention, see DESIGN.md) + PDF export (`scripts/export_pdf.py`) + Ponoko provider mode (`FAXBOX_PROVIDER=ponoko`, outputs in `output/ponoko/`, per-provider BURN; ponoko=0.10 for their published 0.20 kerf). 200 tests green via `.venv/bin/python -m pytest tests/ -q` (~18s; regenerates all SVGs first). Everything adversarially red-teamed; the mutation-hardened suite catches demonstrated green-but-broken geometry.
- **Configured & waiting (not paid):** Ponoko quote in Ben's account, ~$153 for 3 birch sheets, DFM passed, material Birch Plywood 0.126in selected, **Ben manually assigned blue=cutting / red=line-engraving in their dropdowns** (their new flow does NOT auto-map colors; docs verified: wood is cut ON the drawn line — only metals get auto kerf compensation — so our baked-in compensation is correct).
- **In progress / blocked on Ben:** (a) Clark outreach — Ben texting him; if in, we need Clark's laser make/model (CO2 vs diode) to add a provider entry, Ben buys Woodpeckers 18×24 1/8" birch 4-pack (amazon.com/dp/B07NWYSKXG), Ponoko quote gets abandoned; (b) artwork pilot — awaiting Ben's go on the parrot face.
- **Untested (physical):** everything — BURN=0.08 (nycr default) and 0.10 (ponoko) are book values until a kerf coupon is cut; magnet press-fit (gauges cut with the sheets); retention force. First cut self-calibrates: coupons are nested on the sheets.
- **Open-experimental:** PR #22 (`iter2-retention` branch) — spring-detent retention, 192 tests, 3-pass red-team cap reached, each pass found critical geometry. Labeled experimental; physical coupon validation mandatory before cutting; do not resume without Ben.

## The artwork workstream (newest, most context-heavy)

12 photos (IMG_4228–4239, ~31MB) in `art/originals/` show the prototype: bright yellow grounds, dripping black marker "FAX MACHINE" lettering, a finely-textured colored-pencil parrot (cap + spray can, IMG_4228 = long side face), rainbow lettering + drawn fax-machine panel with keypad (IMG_4232, front), mosaic-tile lid interior, more faces uncataloged. Ben wants a **high-quality black-and-white engraved reproduction** ("vector work and raster overlays"), and he rates this near-essential to the box's value.

**Agreed approach (Ben signed off on the shape of this):**
1. **Never engrave the photos directly** — they have tape glare, perspective skew, kitchen background.
2. Per-face digital reconstruction, two layers: **vector line layer** (trace linework with vtracer/potrace + hand cleanup → crisp engraved strokes) and **raster tone layer** (rebuild color fields as clean digital fills, then hand-tune a color→burn-tone map — NOT naive luminance: yellow→near-white light burn, feather texture→mid dither, marker→solid dark).
3. **Pilot face first: the parrot side (IMG_4228)** — it contains all three techniques. Produce 2–3 trace candidates at different detail levels, render side-by-side vs the original, **Ben judges and annotates**; dial parameters, then batch the remaining faces.
4. First step when resuming this: **catalog the 12 photos → box-face map** (which image is which face/orientation; note our design's lid slides vs the prototype's flip lid — art placement needs judgment).
5. Raster engraving renders differently on CO2 vs diode — final tone tuning waits for the target machine (Clark's answer), but tracing/cataloging can start now.
6. LLMs must not freehand-generate the vectors; use tracing tools, use the model for prep, parameter iteration, and side-by-side judging (Ben was explicitly told this and agreed).

## Next concrete steps (in order)

1. When Ben reports Clark's answer: **in** → get machine make/model, add a provider entry in `config.py` `PROVIDERS` (kerf from a coupon cut on his machine; start from CO2 0.20/diode ~0.15 book values), regenerate, remind Ben to buy the plywood 4-pack; **out** → Ben orders the held Ponoko quote (verify the 2D proof shows red as engraving one last time). If Ben wants artwork on box #1, files must be updated BEFORE ordering.
2. When Ben sends the go (or more photos): catalog `art/originals/` → face map (commit as `art/FACES.md`), then run the parrot-face pilot per above.
3. After any physical cut: record measured kerf + magnet fit (coupons are on the sheets) into the provider entry with a comment; capture lessons in LEARNINGS.md.
4. Iteration-2 hardware install (magnets/M3) per README once parts exist.

## Build / test baseline

`.venv/bin/python -m pytest tests/ -q` → **200 passed** at merge `f1d9098` (2026-07-08). Default outputs byte-identical to pre-Ponoko main (verified). Ponoko outputs: `FAXBOX_PROVIDER=ponoko .venv/bin/python -m faxbox.ponoko` → `output/ponoko/sheet_{1,2,3}.svg` (783×354, 789×338, 734×74mm; 23 pieces incl. turn button + combined coupon). Copies also at `~/Desktop/Mini/ponoko-order/` (verified byte-identical) and attached in Ben's Claude chat.

## Decisions made (do not relitigate) & open questions

- All v1 geometry decisions + iteration-2: magnets (4×6mm discs, divider↔drawer leading walls) + single front-wall turn-button; spring detents = experimental PR #22 only. Ben: "optimize for most-likely-to-work."
- Fabrication preference order: Clark (cheapest, restores iteration) → Ponoko (held quote) → NYC Resistor (class path; Ben's done a laser class before, not crazy but least preferred).
- Artwork: engraved B&W reproduction (vector+raster), NOT hand-recoloring, NOT UV printing.
- OPEN: which faces get art in wood v1 vs gift run; art on box #1 at all; Clark's machine; final color→tone map.

## Gotchas & environment quirks

- **Ponoko's new flow**: colors are NOT auto-mapped — laser actions are assigned per-file via dropdowns (Ben already did this on the held quote). Their homepage "±0.08mm accuracy" claim = machine accuracy/metals auto-comp; wood cuts on the drawn line (help article 4442594).
- **TCC/Desktop**: read/copy `~/Desktop/...` via `ssh -o BatchMode=yes localhost 'cp ...'` (see ~/AI/CLAUDE.md). macOS screenshot filenames contain a narrow no-break space before "PM" — glob, don't type the name.
- **Ben's terminal cannot copy-paste** — never hand him commands; run them or write files. He interacts with Asana/Gmail/Ponoko himself from task descriptions.
- Boxes.py `move(label=)` emits engrave-red text; standalone SVGs bypass layout.py's gray recolor (guard test exists in test_laser_requirements.py).
- 2D-cut geometry rules that bit us 3×: a flexure/cam works only if ONE part's plane contains BOTH travel and deflection axes; "blocking" requires swept-volume overlap in 3D that per-panel 2D tests cannot see — always render + eyeball, and red-team novel geometry (Ben's red-team skill; unbiased critics default + hypothesis-seeded critics added).
- Suite regeneration imports faxbox via sys.path from conftest — worktrees test their own tree now; don't trust suite results from before that fix if in a worktree.
- Asana GIDs: order task `1216374505254377` (rewritten for Clark-first plan), hardware-buy task `1216374505535107` (magnets/M3, still valid). An UNSENT Gmail draft to NYC Resistor exists — Ben was told to delete it; if it's still there, ignore it, never send it.
- Ben works manager-style: delegate to sonnet subagents, red-team important outputs, be token-efficient (see ~/AI/CLAUDE.md).

## Hard constraints

- DESIGN.md is the geometry authority; change it first or not at all. **Never weaken a test** (Ben-enforced). Kerf square stays burn-neutral. FingerJoint `play` is thickness-RELATIVE (pass `FINGER_PLAY_RELATIVE`). Default provider outputs must remain byte-stable unless deliberately changed.

## Where everything lives

- Repo `Gilbetrar/fax-machine-box`, local `~/AI/Projects/fax-machine-box`, main @ `f1d9098`. This handoff branch adds `art/originals/` + this file.
- Geometry: `DESIGN.md`; dims+providers: `src/faxbox/config.py`; generators: `src/faxbox/{shell_generator,generate_drawers,generate_lids,generate_hardware,layout,calibration,ponoko}.py`; tests incl. `test_retention.py`, `test_ponoko_export.py`, `test_laser_requirements.py`.
- History/rationale: SESSION_LOG.md, LEARNINGS.md, issues #12–#20, PR #22 comments (detent saga), PR #23/#24 bodies; auto-memory `fax-machine-box-project.md` (user-level).
- Artwork sources: `art/originals/IMG_4228–4239.jpeg`. Game rules/context: https://press.invincible.ink/game-pile-fax-machine/
