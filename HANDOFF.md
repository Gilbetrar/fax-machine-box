# HANDOFF — fax-machine-box

**Date:** 2026-07-09 (evening) · **Branch:** `main` (in `~/AI/Projects/fax-machine-box`)
**Tracking:** issue #20 (decision record), **issue #25 (THE next agent's job — deep QA)**, PR #22 open-experimental (do not touch)
**Pushed:** yes → origin

## TL;DR for the next agent

**Your job is issue #25: intense, adversarial, ground-up QA of the generated cut files.** Read it first — it has the full mandate, attack plan, and constraints. Why it exists: on 2026-07-09 the first outside human to view our sheets (Clark, friend with a laser) instantly spotted a real visual defect (faceplate's red registration outline drawn with 1.0mm open corners + round caps) that had survived 200 green tests and multiple red-team passes. That specific defect is fixed (0.3mm setback now — the gap is DELIBERATE, read the `_draw_engraved_rect_outline` docstring before "improving" it), but Ben's trust in our QA is broken and he wants files proven correct, not assumed correct. Do NOT start fabrication, do NOT integrate art, do NOT anchor on any fabrication provider — just make the geometry bulletproof and the QA repeatable.

Everything else (art, fabrication path, Clark reply) is **paused on Ben** — status below so you don't re-derive it.

## What this project is

A laser-cut 3.175mm-birch-ply box for Ben's "Fax Machine" pen-and-paper game (telephone-pictionary as "faxes" — https://press.invincible.ink/game-pile-fax-machine/). The box IS the game kit: front vertical compartment for pre-cut paper, two rear drawers for pens/pencils, sliding lid, engraved artwork on 10 faces reproducing Ben's hand-drawn cardboard prototype. Endgame: several boxes as gifts. `src/faxbox/config.py` is the single source of truth for all dimensions (mm).

## Current state (honest ledger)

- **Geometry/code:** main is green (**200 tests**, re-verified 2026-07-09 after the registration-outline fix). Outputs regenerate deterministically. NOTHING has been physically cut. **Ben explicitly does not trust the QA level** — that's issue #25.
- **Registration-outline fix (2026-07-09, committed):** `generate_drawers.py::_draw_engraved_rect_outline` corner setback 1.0mm → 0.3mm. The setback exists on purpose (Cairo merges exactly-touching same-style segments into one path; the clustering test harness would misread a closed rect covering ~99% of the faceplate as a nested piece). Sheets regenerated.
- **Artwork: GENERATION COMPLETE, awaiting Ben's sign-off.** All 10 faces exist as hand-drawn-style B&W hatch images (Ben's chosen style: NO halftone dots, NO stylization — direct translation of his originals). Canonical set: `art/ai-versions/final/` (11 files, committed), mirrored to `~/Desktop/Mini/Fax Machine/final-set/`. Full pipeline documentation + per-face learnings: `art/ai-versions/SPECS.md` (READ IT before regenerating anything — sequential conditioning for split faces is mandatory). Post-processing (1-bit threshold, deskew of the lid master, exact-ratio crops, panel-overlay proofs, tracing, sheet integration) has NOT started — see `art/ai-versions/BRIEF.md` for that pipeline. ~282MB of intermediate candidates live UNCOMMITTED in `art/ai-versions/` (gitignored; regenerable via Gemini for ~$5; some mirrored in `~/Desktop/Mini/Fax Machine/proofs-archive/`).
- **Gemini image API:** key installed at `~/.config/gemini/api_key` + `GEMINI_API_KEY` in `~/.zshenv`; prepaid credits topped up; model `gemini-3-pro-image` at 4K. Total art spend so far <$10.
- **Fabrication: DELIBERATELY UNDECIDED (Ben, 2026-07-09 — supersedes "Ponoko only").** Do not anchor on Ponoko vs friend-cut. Requirement instead: rebuilding sheets for a differently-sized bed must be verified easy (part of issue #25). Held Ponoko quote ~$153 still parked; **no ordering until art sign-off AND QA (#25) done AND Ben picks a path.**
- **Clark/Pete thread: awaiting Ben.** Clark (friend, small laser) got the 7/8-era ponoko-order sheet bundle by email, caught the registration-outline defect, and says "Pete" (identity unknown, in no record) is busy with Edinburgh Fringe (Aug 7–31) but could maybe make boxes September+. Open questions ONLY Ben can answer: who is Pete / whose laser / bed size (largest panel 298.45mm — a small bed may not fit it); reopen friend path or not; what to reply. A reply gist was suggested to Ben 2026-07-09; he hasn't sent/decided anything.
- **Untested (physical):** everything — kerf values (ponoko 0.10 / nycr 0.08) are book values; magnet press-fit; retention force. Calibration coupons are nested on the sheets.
- **Open-experimental:** PR #22 spring detents — do not resume without Ben.

## Next concrete steps (in order)

1. **Do issue #25** (deep QA). Fresh agent, fresh eyes, adversarial. Build the render-based visual QA class that actually catches things; re-derive geometry independently; simulate assembly; audit the engrave layer; verify bed-size portability. Fix what's wrong, add regression tests, write the QA report.
2. **When Ben signs off on art** (`~/Desktop/Mini/Fax Machine/final-set/`): run the BRIEF.md post-processing pipeline (threshold → deskew lid master → exact crops per SPECS.md table → panel-overlay proofs with keep-outs → Ben gate → trace with potrace ONLY → integrate into sheets).
3. **When Ben answers the Clark/Pete questions:** he replies to Clark himself (he can't paste — never hand him text to copy); if friend path reopens, get bed size and add a provider entry.
4. **When 1–3 done:** regenerate sheets with art, fresh quote (or friend files), Ben orders/arranges. After the cut: record measured kerf + magnet fit into the provider entry; lessons → LEARNINGS.md.

## Build / test baseline

`.venv/bin/python -m pytest tests/ -q` → **200 passed, ~18s** (verified 2026-07-09 after the gap fix). Outputs: `.venv/bin/python -m faxbox.generate_drawers` (and sibling modules); Ponoko sheets: `FAXBOX_PROVIDER=ponoko .venv/bin/python -m faxbox.ponoko` → `output/ponoko/sheet_{1,2,3}.svg`. Blue-path closure spot-check: `python3 scripts/check_closure.py` (20/20 clean — but READ ITS LIMITS, listed in issue #25).

## Decisions made (do not relitigate without Ben)

- **Art style (Ben, 2026-07-09):** loose hand-drawn hatching, solid-black display lettering, DIRECT translation of the originals only — he explicitly rejected halftone-dot renderings ("polka dot-y") and all stylized variants. Style anchor: `art/ai-versions/final/IMG_4230_ai_vH2.png`.
- **Drawer sides use split-generate-merge** (Ben's own idea, validated): cut source at a quiet column, generate halves sequentially (right half conditioned on finished left + full original + exclusion list), butt-join. Cut fractions + all learnings in SPECS.md.
- **Lid art spans BOTH the sliding lid and the fixed top panel** as one continuous panorama (field 301.25×158.75mm, seam at 26.22% from front, 5.8mm vertical step at the seam — geometry derivation in SPECS.md STATUS block). Master: `final/IMG_4231_ai_vT1_master.png` + seam preview.
- **Face map settled 2026-07-08** (`art/FACES.md`); drawer backs and box rear get no art; bottom out of scope.
- **Fabrication method: open** (2026-07-09) — supersedes the 7/8 "Clark DROPPED, Ponoko only" record in issue #20.
- **Standing artwork rules:** LLMs never freehand vectors — tracing tools only (potrace/vtracer); never engrave source photos directly; model does prep/parameters/judging.

## Gotchas & environment quirks

- **File delivery to Ben: copy to `~/Desktop/Mini/<subfolder>/`** via loopback SSH (`ssh -o BatchMode=yes localhost 'cp ... "$HOME/Desktop/Mini/..."'`) — in-chat sends don't reach him; Desktop is TCC-protected for direct reads (see ~/AI/CLAUDE.md). All fax material on the Mini is consolidated under `~/Desktop/Mini/Fax Machine/` (Ben's request).
- **Ben's terminal cannot copy-paste** — never hand him commands or reply text to paste; run things yourself or write files.
- **Screenshot filenames** from macOS contain a narrow no-break space before "AM/PM" — glob (`Screenshot*3.16*`) instead of typing the name.
- **Gemini generation learnings** (hard-won, in SPECS.md, binding): padded-canvas direct translation beats instruction-following; NEVER pass a style-anchor image alongside simple/lettering-only sources (content bleed — it happened 3×); single-change fix passes work; model CANNOT reliably straighten a tilted composition (deskew deterministically in post instead); residual color tints die at threshold time — don't chase them with re-rolls.
- **Google MCP:** ben.bateman account auth is EXPIRED (re-auth flow was triggered 2026-07-09, port 8001; Ben may or may not have completed it). gilbetrar account works. Clark's email thread lives in ben.bateman — unauditable until re-auth.
- **iMessage MCP works** and is the record of the Ben↔Clark outreach (2026-07-08, handle +12097285785).
- **Thresholding lesson:** naive local-mean adaptive threshold hollows thick marker strokes; fix = large (251px) morphological-close background estimate then diff (`art/pilot/extract_lines.py`, PARAMS.md).
- **Ponoko flow:** colors NOT auto-mapped — laser ops assigned per-file via dropdowns at quote time; wood cuts ON the line (no auto kerf comp for wood), our baked-in BURN compensation is correct. Text must be outlined; Ponoko sheets carry no reference labels (parts identified via `data-part` attrs).
- **Boxes.py 'f'/'F' edges** both protrude up to one thickness (phase complements) — size-band tests account for it.
- **2D-geometry lesson (bit us 3×):** flexure/cam works only if ONE part's plane contains BOTH travel and deflection axes; per-panel 2D tests can't see 3D swept-volume blocking — render + eyeball + red-team novel geometry.
- **Subagents + mid-flight spec changes:** don't SendMessage a running subagent a spec change (it read one as prompt injection once); kill and respawn.
- **Asana:** order task gid `1216374505254377` "⏸️ PAUSED — Fax box: order cut online (Ponoko) AFTER artwork is final", due 2026-07-31 as revisit marker (MCP can't clear due dates). NOTE: task wording predates the 7/9 "provider undecided" decision. Hardware-buy task `1216374505535107` (6× 6mm N35 magnets, M3×12 bolt, nyloc, washers) still open.
- Ben works manager-style: delegate high-token work to sonnet/haiku subagents; red-team important outputs (`~/AI/CLAUDE.md`).

## Hard constraints

1. **No fabrication ordering** until: art sign-off + issue #25 QA done + Ben picks a provider.
2. **No LLM-freehand vector art** — tracing tools only.
3. **Do not touch PR #22.**
4. **Never claim QA confidence from the existing test suite alone** — that's the failure mode that created issue #25.

## Where everything lives

- Branch: `main`, pushed. This file: repo root.
- Art: `art/ai-versions/final/` (canonical, committed) · `art/ai-versions/SPECS.md` (specs + pipeline learnings) · `art/ai-versions/BRIEF.md` (post-processing pipeline) · `art/FACES.md` (face map) · `art/trimmed/` (sources) · `art/pilot/` (old potrace pilot — superseded for style, tooling still relevant).
- Uncommitted-by-design: `art/ai-versions/*.png` top level (intermediates, gitignored, ~282MB) · `scratch/` (renders/analysis from QA sessions, gitignored).
- Tools: `scripts/check_closure.py` (blue-path closure checker, committed).
- Ben-visible mirror: `~/Desktop/Mini/Fax Machine/{final-set,proofs-archive,source-drawings,pilot-traces,specs,ponoko-order}/`.
- Gemini key: `~/.config/gemini/api_key`; generation scripts from this session are in the session scratchpad (not the repo) — SPECS.md carries everything needed to rewrite them.
