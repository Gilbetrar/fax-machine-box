# HANDOFF — fax-machine-box (art-integration workstream)

**Date:** 2026-07-11 · **Branch:** `art-integration` (in `~/AI/Projects/fax-machine-box`), based on `main` @ 848ade8
**Pushed:** yes → origin (both branches)
**Tracking:** issue #25 (QA — CLOSED-equivalent, done + decisions recorded in comments), issue #20 (decision record), PR #22 open-experimental (DO NOT TOUCH)

## TL;DR for the next agent

**Your job: act on Ben's rev-3 proof-gate feedback (4 items, "BEN'S FEEDBACK" section below — he gave it 2026-07-11 and it has NOT been acted on), produce updated proofs to `~/Desktop/Mini/Fax Machine/`, and get his sign-off; only then proceed to trace + sheet integration (pipeline tail already de-risked, see "After the feedback").** The art placement pipeline is 3 revisions deep: rev 3 (full-bleed, snake-head-on-lid) is committed and its proofs are on Ben's Desktop (`art-proofs-rev3/`). Walls are APPROVED by Ben. Everything is committed + pushed on `art-integration`; suite is 217 green.

## What this project is

Laser-cut 3.175mm birch-ply box for Ben's "Fax Machine" pen-and-paper game (telephone pictionary). Front vertical paper compartment, two rear drawers, sliding lid, hand-drawn-style engraved artwork on 11 faces reproducing Ben's cardboard prototype art (AI-restyled to 1-bit hatch style, already generated + approved). Endgame: several boxes as gifts. `src/faxbox/config.py` + DESIGN.md = geometry source of truth. Deep adversarial QA of all cut geometry is DONE (2026-07-09, `docs/QA-REPORT-2026-07-09.md`): geometry verified clean; sheets Ponoko-conformant.

## BEN'S FEEDBACK (2026-07-11, verbatim intent — the work queue, in his priority order)

1. **Drawer sides — "the biggest issue right now": the split-generate-merge seams are bad.** The two halves of each stitched panel (4233 turkeys / 4235 alligator / 4237 gallery / 4239 bookshelf, files `IMG_<n>_ai_vS_stitched.png` in `art/ai-versions/final/`) have visibly different art styles on either side and/or lines that don't meet — "an obvious kind of shocking break in the middle." Ben: "you should be able to find a way to have these generate so these match better… worth doing some pretty big visual check against and maybe trying to handle these differently." → This likely means REGENERATING the drawer-side art (Gemini, key at `~/.config/gemini/api_key`, GEMINI_API_KEY in ~/.zshenv, model gemini-3-pro-image at 4K; ~$1/face-ish). Binding generation learnings in `art/ai-versions/SPECS.md` (sequential conditioning for halves, padded-canvas direct translation, no style-anchor with simple sources). Consider alternatives to split-generate: e.g. single-shot 21:9 with band composition (the ORIGINAL approach — its outputs were 2.3:1, too tall, but cover-fit now exists), or seam-blend fix-passes ("reproduce exactly, change only the seam region"). Whatever you do, build a REAL seam-quality visual check (render each stitched panel, look hard at the seam column with fresh eyes / a vision subagent quota'd to find mismatches) — Ben explicitly wants intense visual verification here.
2. **Faceplates (COLORS / Lines) — Ben's DECISION: don't full-bleed these; put the whole word BELOW the grip slot.** Current rev-3 balanced-fit is off anyway (doesn't reach the top edge, runs too close to the bottom finger teeth). Ben: "I actually think it's worth having those not bleed and shrinking those so the words are underneath the cut hole… put them all below the cut hole and small enough so the full text fits below." Geometry: faceplate 150.9 × 53.5mm; grip slot 30×15mm, horizontally centered, slot TOP 8mm below the part top edge → slot occupies the z-band 30.5–45.5mm (from bottom). The clear band below the slot is the bottom ~30.5mm × full width. Scale each word to sit fully in that band (respect ~2mm edge margins), centered. This also kills the current slot-through-the-"L"-of-COLORS problem. These are labels, not scenes — Ben is explicit they should be treated differently from the other faces.
3. **Lid/top-panel — snake variant ACCEPTED as fallback, but Ben wants to SEE a full-cat variant.** He likes the walls ("the fax machine, the bird spray painting… looks great") and the snake-on-lid version is "okay… I'd rather do that than nothing." He DISLIKES variant B ("a weird middle section that is centered"). He wants a variant where **the full cat is visible — window bottom/cat-end-justified** ("bottom-justified or right-justified on the cat side"): i.e. anchor the 301.25mm window at the FLORAL/CAT end of the fill-height-scaled panorama (the opposite anchoring from rev-3's head-anchored A variant; this trims the snake head instead). Produce it as a third variant proof (A = head-anchored current canonical, C = cat-anchored) + seam strips, deliver, let him pick. Note: whichever end is trimmed, the art stays rotated so the surviving front content rides the sliding lid — think through what lands on the lid in the C variant (the cat end) before rendering, and label the strips clearly.
4. **Right wall title vs lid slot — recommend + try a text shift.** The lid through-slot (76.2×4mm, near the top edge, front half of the wall) cuts through "FUN FOR" in the "Fun For Terrible Writers & Artists of All Ages" title, likely making it unreadable. Ben: "curious about your recommendation… maybe moving that specific piece of the text around and trying to move the text slightly to have those cuts be less painful… without breaking it." Options to evaluate: (a) programmatic raster shift of the title block within the art (deterministic pixel-region translate — allowed, it's post-processing not freehand vector), (b) Gemini single-change fix-pass ("reproduce exactly, change only: move the title text down/right N mm" — SPECS says single-change passes work well), (c) accept. Overlay the REAL slot geometry when judging (the proof builder does this). Recommendation + proof to Ben.

**Also still open from rev-3 flags (lower priority, fold into the same proof round):** lid front-lip white wedge (~19mm run where the head's diagonal boundary crosses the front edge — more overshoot crops the head tip; Ben hasn't ruled); drawer_side_1's clipped top text line (probably moot if #1 regenerates the art); lid rotation direction vs the physical box (unverifiable remotely; flagged in PLACEMENTS.md); Ben's QA open items #2–4 from `docs/QA-REPORT-2026-07-09.md` (game-component dims, turn-button bolt protrusion, ergonomics — all waiting on Ben, don't block art).

## Current state (honest ledger)

- **Branch `art-integration`, 5 commits ahead of main, all pushed.** main @ 848ade8 = post-QA state (its HANDOFF.md section is superseded by this file).
- **Art placement pipeline (rev 3) DONE + committed:** `scripts/art_postprocess.py` (deterministic; threshold → debts → robust-content-bbox → cover-fit full bleed; 4231: deshear (a −8.06° horizontal SHEAR, not rotation — top/bottom edges are level, don't "fix" it to a rotation) → 180° rotation (snake head to front) → fill-height 158.75mm → head-anchored 301.25mm window with 8mm front overshoot → split at 79mm). Outputs: `art/engrave/*.png` — 11 canonical 1-bit files + 2 `*_VARIANT_B*` (centered window — Ben dislikes it, superseded by his request for a cat-anchored variant C). Full per-face derivations/flags: `art/engrave/PLACEMENTS.md`.
- **Proof builder DONE:** `scripts/art_proofs.py` renders every placement over real part geometry (blue cuts on top of black art, real slot/hole positions, seam-continuity strips, contact sheet) → `scratch/art-proofs/`. Ben-visible mirror: `~/Desktop/Mini/Fax Machine/art-proofs-rev3/`.
- **Ben's verdicts so far:** left wall (parrot) + right wall (writers) APPROVED. Snake-on-lid acceptable pending the cat variant. Faceplates + drawer sides NOT approved (feedback #1/#2). Pixel "FAX MACHINE" text fully REMOVED (his order; commit eebbfe7) — walls carry ZERO red until reviewed art lands, tests enforce this.
- **Trace pilot DONE (left wall):** hybrid = centerline polylines (skeleton + spur-prune + Douglas-Peucker) for hatch + potrace fills for solids → 96.9% agreement, 13.4k pts; pure potrace-fill 99.5%, 31k pts (hobby-laser pick). `scratch/trace-pilot/RESULTS.md` (+ my addendum: the rumored Ponoko 3,000-point cap is REFUTED — existing sheet_2 has ~9.4k pts and quoted fine at $153). Ponoko format decision: red-hairline vector-line engrave for hatch, small black fills for solids; raster embed is a hard NO at Ponoko. `scratch/qa-docs/ponoko-engrave-format.md`.
- **Tests: 217 green** (`.venv/bin/python -m pytest tests/ -q`, ~6–22s). Regenerate outputs: the 6 `faxbox.*` module mains + `FAXBOX_PROVIDER=ponoko … -m faxbox.ponoko`; layout purges stale sheets automatically.
- **Untested/not started:** tracing the other 10 faces; sheet integration (no engrave layer is in any generator/sheet yet); quoting with art; everything physical.

## Next concrete steps (in order)

1. Read `art/engrave/PLACEMENTS.md`, `scratch/art-proofs/PROOFS.md`, `art/ai-versions/SPECS.md` (binding generation learnings). Look at the rev-3 proofs yourself.
2. **Feedback #2 (faceplates)** — pure placement change in `art_postprocess.py`, no regeneration; quick win.
3. **Feedback #3 (lid variant C)** + the front-lip wedge options — placement change + proof strips.
4. **Feedback #4 (right-wall title)** — evaluate shift options, recommend, proof. (Wall art itself is approved; only the title block moves.)
5. **Feedback #1 (drawer sides)** — the big one: regeneration experiments + a serious seam-quality visual check harness. Budget Gemini spend consciously (<$10 total was the whole art budget so far).
6. One proof round to Ben's Desktop (`~/Desktop/Mini/Fax Machine/<new folder>/`), get sign-off.
7. THEN the pipeline tail: trace all faces (hybrid, per trace-pilot), integrate engrave layers into generators/sheets (mind wall mirroring — art must land on EXTERIOR faces as drawn; lid/top-panel orientation per PLACEMENTS.md), update `tests/test_engrave_cut_clearance.py`'s EXPECTED_VIOLATIONS with a decision-record allowlist (Ben accepted art-over-holes 2026-07-10), extend the red-census tests, regenerate, fresh Ponoko quote (NO ordering).

## Decisions made (do not relitigate without Ben)

- Pixel FAX MACHINE text: REMOVED everywhere (Ben 2026-07-10, twice-confirmed). Walls must stay red-free until reviewed art lands (tests enforce).
- Art crosses joint holes: ACCEPTED ("eat the cost of those holes") — recorded in issue #25 comments + test comments.
- Full bleed everywhere EXCEPT faceplates (Ben 2026-07-11: labels go below the grip slot, no bleed).
- Snake head on the sliding lid (vs cat) unless the variant-C proof changes his mind; variant B (centered) rejected.
- Fabrication provider deliberately undecided; NO ordering until art done + Ben picks. Art style locked (hatch, direct translation). LLMs never freehand vectors — tracing tools/programmatic geometry only. Never engrave source photos.

## Gotchas & environment quirks

- **File delivery to Ben:** copy to `~/Desktop/Mini/Fax Machine/<subfolder>/` via loopback SSH (`ssh -o BatchMode=yes localhost 'cp … "$HOME/Desktop/Mini/…"'`) — direct Desktop writes are TCC-blocked; in-chat sends don't reach him. **Ben's terminal can't copy-paste** — never hand him commands; run things yourself.
- **Subagents:** Opus critics occasionally derail instantly (0 tool calls, garbled output) — respawn, don't debug. Subagent Writes of report files into repo scratch are sometimes permission-blocked — have them return findings inline and persist yourself. Verify critic claims by measurement before acting (two pass-1 QA claims were refuted; the "kerf under-compensation" was a bbox artifact of corner-relief arcs — flats are exact).
- **4231 master processing:** the deskew is a horizontal SHEAR (left edge leaned, top/bottom level) — a rotation would be wrong. The reserved grip capsule in the art was only usable in the rev-2 placement; rev 3 (full-bleed + rot180) abandons it — the real slot now cuts the head mosaic between the eyes (documented, Ben-accepted).
- **cover_fit had a real bug** (blank edge column when the bbox-edge ink lived in the cross-axis crop band) — fixed with an iterative bbox-within-window convergence loop; don't simplify it away.
- **tests/test_retention.py's `main_shell_svg` fixture** copies an explicit file list from `main:src/faxbox/` — if shell_generator gains a new import, ADD IT to that list (bit us with svglabels).
- **Renders for eyeballing:** `scripts/qa_render.py --sheets <files>` (defaults to ponoko sheets — pass your files explicitly); art proofs via `scripts/art_proofs.py` (no args).
- Boxes.py: labels via `move(label=…)` render engrave-red — every generator write site must call `svglabels.enforce_reference_labels()` (systemic guard tests exist). Ponoko flow: colors assigned per-file at quote time; text must be outlined/absent; wood cut ON the line, BURN baked in.
- google MCP: ben.bateman auth EXPIRED (gilbetrar works). Ben↔Clark record in iMessage (+12097285785). Asana revisit-marker task gid 1216374505254377; hardware-buy task 1216374505535107.
- Don't SendMessage a running subagent a spec change — kill and respawn.

## Hard constraints

1. NO fabrication ordering. 2. NO LLM-freehand vector art (tracing/programmatic only). 3. Do not touch PR #22. 4. Never weaken a test (extend/replace with decision records). 5. `art/ai-versions/final/` is frozen canon — post-process copies, never edit sources. 6. Placement gates: Ben sees proofs on his Desktop before tracing/integration proceeds.

## Where everything lives

- Branch `art-integration` (pushed). Key scripts: `scripts/art_postprocess.py`, `scripts/art_proofs.py`, `scripts/qa_render.py`.
- Engrave-ready art: `art/engrave/` (+ PLACEMENTS.md). Sources: `art/ai-versions/final/` (frozen) + SPECS.md (generation learnings). Face map: `art/FACES.md`.
- Proofs: `scratch/art-proofs/` (gitignored) → mirrored `~/Desktop/Mini/Fax Machine/art-proofs-rev3/`. Trace pilot: `scratch/trace-pilot/RESULTS.md`. Ponoko engrave research: `scratch/qa-docs/ponoko-engrave-format.md`.
- QA record (main): `docs/QA-REPORT-2026-07-09.md`, `scratch/qa-critics/*/FINDINGS*.md`, issue #25 comments.
- Gemini key: `~/.config/gemini/api_key`; credits topped up; total art spend <$10 so far.
