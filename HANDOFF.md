# HANDOFF — fax-machine-box

**Date:** 2026-07-08 (evening pause) · **Branch:** `main` (in `~/AI/Projects/fax-machine-box`)
**Tracking:** issue #20 (decision record in comments, incl. today's), PR #22 open-experimental (do not touch)
**Pushed:** yes → origin

## TL;DR for the next agent

`main` is complete and green (**200 tests**); nothing has been physically cut. Today the artwork workstream went live: the face map is SETTLED (all decisions in `art/FACES.md`), a parrot-face line-trace pilot produced 3 candidates (`art/pilot/`), and clean uncropped-pixel crops of all 12 prototype photos were made for Ben to share with **other image models** (`art/trimmed/`, mirrored to `~/Desktop/Mini/Fax Machine Illuistrations/trimmed/`). **Fabrication is PAUSED, gated on artwork** — Clark path dropped, ordering will be online (Ponoko) only after the engrave art is final. The immediate wait: Ben saw the pilot candidates, said **"OK, but I think we can probably do a lot better,"** and is gathering opinions/outputs from other image models. Do NOT start batch-tracing the other faces with the current pilot settings — wait for Ben's verdict and whatever the other models suggest, then iterate the pipeline.

## What this project is

A laser-cut 3.175mm-birch-ply box for Ben's "Fax Machine" pen-and-paper game (telephone-pictionary as "faxes" — https://press.invincible.ink/game-pile-fax-machine/). The box IS the game kit: front vertical compartment for pre-cut paper, two rear drawers for pens/pencils, sliding lid, "FAX MACHINE" engraving. Ben's hand-drawn cardboard prototype provided dimensions and carries dense colorful artwork he wants reproduced on the wood as **high-quality B&W engraving (vector line layer + raster tone layer)**. Endgame: several boxes as gifts, with pen kits and paper pre-cut.

## Current state (honest ledger)

- **Done & verified:** main = v1 geometry + magnet/turn-button retention + PDF export + Ponoko provider mode. **200 tests green** (`.venv/bin/python -m pytest tests/ -q`, ~18s, re-verified today at pickup AND at this handoff). Default outputs byte-stable.
- **Done today (all committed on main):**
  - `art/FACES.md` — photo→face catalog **with Ben's final decisions** (see below).
  - `art/pilot/` — parrot-face (IMG_4228) line-trace pilot: perspective-corrected original, linework mask, 3 traced candidates (A=potrace smooth/clean, B=potrace more specks, C=vtracer polygon style), `PARAMS.md` (full pipeline doc — READ IT before redoing any tracing), `extract_lines.py`. The big `compare_*.png` montages are gitignored (recreatable; copies at `~/Desktop/Mini/fax-pilot/`).
  - `art/trimmed/` — **plain crops** (NO perspective correction — Ben explicitly forbade warping for these) of all 12 photos, full res, artwork never clipped. Mirrored to `~/Desktop/Mini/Fax Machine Illuistrations/trimmed/` for Ben to share with other image models.
  - README Ponoko section now carries a **⏸️ FABRICATION PAUSED** banner; Asana order task rewritten (see Gotchas).
- **Awaiting Ben (the only blockers):**
  1. **Pilot verdict** — he rated the candidates "OK, but we can probably do a lot better" and is consulting other image models using the trimmed crops. Expect him to return with ideas/outputs; iterate the trace pipeline against that.
  2. Nothing else — Clark is moot, Ponoko is deliberately parked.
- **Untested (physical):** everything — kerf values (nycr 0.08 / ponoko 0.10) are book values; magnet press-fit; retention force. Coupons are nested on the sheets and self-calibrate at first cut.
- **Open-experimental:** PR #22 spring detents — experimental, physical coupon validation mandatory, do not resume without Ben.

## Decisions made TODAY (do not relitigate — recorded in FACES.md + issue #20 comment)

- **Face map (Ben, 2026-07-08):** writers panel (IMG_4230) = second main-box long side; the four scene panels — turkeys (4233), alligator (4235), gallery (4237), bookshelf (4239) — = the four **drawer sides**, assignment among sides doesn't matter; drawer fronts = "COLORS" (4236) / "Lines" (4238), either drawer; **drawer backs get no art**; main-box back: none assigned.
- **Lid:** IMG_4231 panorama transposed onto the sliding lid top; the mosaic snake/dragon head may run off the retracting edge — Ben accepts it won't read like the flip lid. Lid-interior mosaic + edge trims **dropped**.
- **Fabrication: Clark DROPPED; online (Ponoko) AFTER art is final.** The held ~$153 quote's uploaded files have NO artwork — when art is done, regenerate sheets with engrave layers and configure a **fresh** quote (blue=cut, red=line-engrave via their dropdowns; verify the 2D proof). Never order before art sign-off.
- **Standing artwork rules (from 7/8 handoff, still binding):** LLMs must NOT freehand-generate vectors — tracing tools only (potrace/vtracer); model does prep, parameters, judging. Never engrave the photos directly. Raster tone layer waits for the target machine (Ponoko = CO2, Speedy-class).
- For these SHARE files Ben wants zero warping; but geometric normalization for the ENGRAVE pipeline is a separate, still-open decision to make per-face with Ben looking at results.

## Next concrete steps (in order)

1. **When Ben returns with other-model feedback / pilot verdict:** iterate the line-trace pipeline. Known headroom: cleaner masks, stroke-width preservation, centerline vs outline tracing, per-region parameters (lettering vs feather hatching). If he picks a candidate as-is: clean the known mask artifacts (taped-hole blob top-left, tape-glare specks top-right, bottom frame-edge line — all documented in `art/pilot/PARAMS.md`), then batch the remaining faces with the settled map in FACES.md.
2. **After line art is approved per face:** build the raster tone layer (color→burn-tone map, hand-tuned: yellow→near-white, feather texture→mid dither, marker→solid dark) — needs machine known (Ponoko CO2 if ordering online).
3. **Art done →** integrate engrave layers into the Ponoko sheets (`src/faxbox/ponoko.py` / layout), regenerate, configure fresh Ponoko quote, un-pause the Asana task, Ben orders.
4. **After the physical cut:** record measured kerf + magnet fit (coupons are on the sheets) into the provider entry; lessons → LEARNINGS.md.
5. Iteration-2 hardware install (magnets/M3) per README once parts exist.

## Build / test baseline

`.venv/bin/python -m pytest tests/ -q` → **200 passed** (re-run at this handoff, 2026-07-08 evening). Ponoko outputs regenerate via `FAXBOX_PROVIDER=ponoko .venv/bin/python -m faxbox.ponoko` → `output/ponoko/sheet_{1,2,3}.svg`. Note: `opencv-python-headless` was pip-installed into `.venv` today (for line extraction); tests unaffected.

## Gotchas & environment quirks

- **File delivery to Ben: copy files to `~/Desktop/Mini/<subfolder>/`** — he views that folder from another computer; in-chat file sends do NOT reach him. Desktop is TCC-protected: wrap in loopback SSH, e.g. `ssh -o BatchMode=yes localhost 'cp ... "$HOME/Desktop/Mini/X/"'` (see ~/AI/CLAUDE.md). Note the existing folder is spelled **"Fax Machine Illuistrations"** (sic).
- **Ben's terminal cannot copy-paste** — never hand him commands; run them yourself or write files.
- **Subagents + mid-flight spec changes:** a SendMessage relayed into a running subagent's transcript got flagged BY THE SUBAGENT as prompt injection and ignored (it finished with the outdated spec; 7 files had to be redone by a fresh agent). If a task's spec changes mid-flight, prefer killing and respawning with the new spec, or expect to verify compliance afterwards.
- **Image tooling (installed today):** ImageMagick + potrace via brew; **vtracer has NO brew formula** — installed via `cargo install vtracer` → `~/.cargo/bin/vtracer` (0.6.5). ImageMagick `-annotate`/`montage -label` needs explicit `-font /System/Library/Fonts/Helvetica.ttc` (empty font list on this machine).
- **Thresholding lesson (will bite on every face):** naive local-mean adaptive threshold makes thick marker strokes come out HOLLOW (stroke interiors read as background). Fix: estimate background with a large (251px) grayscale morphological close, then diff. Full detail in `art/pilot/PARAMS.md`.
- **Ponoko flow:** colors are NOT auto-mapped — laser actions assigned per-file via dropdowns at quote time; wood cuts ON the drawn line (only metals get auto kerf comp), so our baked-in BURN compensation is correct.
- **Asana:** order task gid `1216374505254377`, renamed "⏸️ PAUSED — Fax box: order cut online (Ponoko) AFTER artwork is final", due pushed to **2026-07-31 as a revisit marker** (the MCP tool cannot clear due dates — only overwrite them). Hardware-buy task `1216374505535107` (magnets/M3) still valid. Old note: an unsent NYCR Gmail draft may exist — ignore, never send.
- Boxes.py `move(label=)` emits engrave-red text; standalone SVGs bypass layout.py's gray recolor (guard test exists).
- 2D-geometry lesson (bit us 3×): flexure/cam works only if ONE part's plane contains BOTH travel and deflection axes; "blocking" needs swept-volume overlap in 3D that per-panel 2D tests can't see — render + eyeball + red-team novel geometry.
- Ben works manager-style: delegate high-token work to sonnet subagents, red-team important outputs (see ~/AI/CLAUDE.md).

## Hard constraints

- DESIGN.md is the geometry authority; change it first or not at all. **Never weaken a test.** Kerf square stays burn-neutral. FingerJoint `play` is thickness-relative (`FINGER_PLAY_RELATIVE`). Default provider outputs stay byte-stable unless deliberately changed. **No LLM-freehand vector art.** **No fabrication ordering until art sign-off.**

## Where everything lives

- Repo `Gilbetrar/fax-machine-box`, local `~/AI/Projects/fax-machine-box`, `main` (this handoff commit). Geometry: `DESIGN.md`; dims+providers: `src/faxbox/config.py`; generators: `src/faxbox/*.py`; tests incl. `test_retention.py`, `test_ponoko_export.py`, `test_laser_requirements.py`.
- Artwork: originals `art/originals/`, face map + decisions `art/FACES.md`, pilot `art/pilot/` (read `PARAMS.md`), clean crops `art/trimmed/`.
- Ben-visible mirrors: `~/Desktop/Mini/Fax Machine Illuistrations/trimmed/` (12 crops), `~/Desktop/Mini/fax-pilot/` (pilot comparisons).
- History/rationale: SESSION_LOG.md, LEARNINGS.md, issues #12–#20 (today's decision comment on #20), PR #22 (detent saga), PR #23/#24 bodies; auto-memory `fax-machine-box-project.md`.
