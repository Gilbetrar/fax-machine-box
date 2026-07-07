# Laser Cutting Service Comparison

Comparison of services for cutting 1/8" (3.175mm) plywood parts for the fax machine box validation cut.

## Project Requirements

- **Material:** 1/8" plywood (Baltic Birch preferred)
- **Parts:** Outer shell, 2 drawers, 2 lids, internal dividers
- **Estimated sheet size:** ~12" x 24" (one sheet should fit all parts)
- **Complexity:** Finger joints, engraving on front panel
- **File format:** SVG (boxes.py output)

## Service Comparison

| Service | Location | Pricing Model | Est. Cost | Turnaround | Min Order |
|---------|----------|--------------|-----------|------------|-----------|
| NYC Resistor | Brooklyn, NY | $1/min self-operated | ~$20-40 | Same day | None |
| SendCutSend | Online (Reno, NV) | Per-part, instant quote | ~$30-60 | 1-3 days | None |
| Ponoko | Online (Oakland, CA) | Per-part, instant quote | ~$40-80 | 5-10 days | None |
| Laser-CutZ | NYC | $500/hr, $750 min | $750+ | Same day | $750 |

## Detailed Analysis

### 1. NYC Resistor (RECOMMENDED for Validation)

**Website:** https://www.nycresistor.com/laser/

**Pricing:**
- $1/min self-operated (after taking laser class)
- $75/hr + $2/min with operator assistance
- Materials available for purchase on-site, or bring your own

**Pros:**
- Cheapest option for a single validation cut (~$20-40)
- Same-day turnaround
- Can iterate quickly on site
- 32" x 20" bed size fits all parts
- Community support if issues arise

**Cons:**
- Must take laser class first (taught monthly)
- Limited hours (Mon/Thu craft nights 6:30-9pm best times)
- Need to bring materials or buy on-site

**Best for:** First validation cut, iteration, learning

---

### 2. SendCutSend

**Website:** https://sendcutsend.com/

**Pricing:**
- Per-part pricing based on material, thickness, and complexity
- Volume discounts up to 70% for bulk orders
- Free shipping on orders over $39

**Materials:**
- Baltic Birch plywood: 1/8" (0.125"), 5/32" (0.157"), 3/10" (0.295"), 1/2" (0.472")
- MDF also available

**Pros:**
- Instant online quotes (upload SVG)
- No minimum order
- Professional quality with tight tolerances (±0.009")
- Fast shipping (1-3 business days)
- Free shipping on orders over $39

**Cons:**
- Online-only (can't iterate in person)
- Shipping adds to timeline
- Slightly more expensive than self-cut options

**Best for:** Production runs, consistent quality, time-constrained users

---

### 3. Ponoko

**Website:** https://www.ponoko.com/

**Pricing:**
- Per-part pricing, quote required
- 55% off for Prime members
- No minimum order, free shipping

**Materials:**
- Birch plywood available
- Wide selection of materials (200+)

**Pros:**
- Well-established service (used by Apple)
- Good material selection
- Free shipping

**Cons:**
- Ships from Oakland (longer transit to East Coast)
- Slower turnaround (5-10 days typical)
- Must create account to get quotes

**Best for:** Users already familiar with Ponoko, specific material needs

---

### 4. Laser-CutZ

**Website:** https://www.lasercutz.com/

**Pricing (as of Feb 2025):**
- $500/hour base rate
- $750 minimum charge
- $1,000 minimum for walk-ins without appointments
- B2B only (requires tax-exempt status)

**Pros:**
- Local NYC service
- Same-day available
- High-end equipment

**Cons:**
- Very expensive ($750 minimum!)
- B2B only, not suitable for personal projects
- Recent price increases due to tariffs

**Best for:** Commercial/B2B projects with budget, NOT for validation cuts

---

## Recommendation

**For the first validation cut: NYC Resistor**

**Reasoning:**
1. **Cheapest option:** ~$20-40 vs $750 minimum at Laser-CutZ
2. **Fastest iteration:** Can adjust and recut on-site same day
3. **Learning opportunity:** Understand the process before ordering production runs
4. **Local support:** Community can help troubleshoot fit issues

**Action items:**
1. Sign up for NYC Resistor laser class (check website for dates)
2. After class, schedule time at craft night (Mon/Thu 6:30-9pm)
3. Bring 1/8" plywood sheet (~$15-20 from local hardware store)
4. Cut all parts, test assembly on-site if time permits

**For production runs (after validation):** Switch to SendCutSend for consistent quality and convenience.

---

## Cost Estimate Breakdown

Assuming ~20-30 minutes of cutting time for all parts:

| Service | Material | Cutting | Shipping | Total |
|---------|----------|---------|----------|-------|
| NYC Resistor | $15-20 (BYO) | $20-30 | $0 | **$35-50** |
| SendCutSend | Included | ~$40-60 | Free | **$40-60** |
| Ponoko | Included | ~$50-80 | Free | **$50-80** |

*Note: Online service estimates are rough. Upload SVGs for accurate quotes.*

## File Preparation Notes

- **SVG format:** All services accept SVG
- **Cut color:** Black lines for cuts (Ponoko: blue for cuts, red for engraving)
- **Engraving:** Currently uses red in SVG for "FAX MACHINE" text
- **Kerf:** 0.1mm configured; may need adjustment per machine

---

## NYC Resistor cutting constraints (verified 2026-07-07)

Live web research against NYC Resistor's own site and wiki, done for issue
#19 (the release-gate sheet-nesting rewrite). Every claim below is tagged
with its source URL; anything not confirmed on a live, currently-fetchable
page is called out explicitly rather than assumed.

### Laser bed / working area -- AMBIGUOUS, fallback used

The laser page (https://www.nycresistor.com/laser/) and the wiki
(https://wiki.nycresistor.com/wiki/Laser, last edited 2026-07-07) both state
the machine is an **Epilog Fusion 32, 60W** with a **32in x 20in** bed.
However, a comment on the `/laser/` page itself disputes this, claiming the
actual *cuttable* work area is smaller -- **12in x 24in** -- and no NYC
Resistor page reconciles the two figures.

This is exactly the "ambiguous bed size" case issue #19's instructions call
for a conservative fallback on. Per that instruction, **this project does
not trust either disputed figure** and instead plans against:

> **Sheet size used by `src/faxbox/layout.py`: 18in x 24in (457.2mm x
> 609.6mm).** `SHEET_WIDTH_MM` / `SHEET_HEIGHT_MM` in that file are the
> single place to update once the real bed is confirmed in person.

This fallback is smaller than the disputed 32in figure in both directions
and smaller than the 20in figure in one direction, so it should be safe to
plan against without visiting first -- but **verify the actual bed in person
before cut day**, since neither on-site figure has been independently
confirmed.

### Accepted file formats / color convention

Their wiki tips page
(https://wiki.nycresistor.com/wiki/Laser_Tips_and_Tricks, last edited
2026-07-07, verified directly) documents a CorelDraw X5-based workflow
importing **SVG, EPS, or PDF**. It specifically warns that **Inkscape's SVG
export "gets corrupted"** and recommends **exporting PDF from Inkscape
instead**; EPS works if imported "as curves." Illustrator users are told to
export PDF/EPS at Acrobat 5.0 compatibility with "Preserve Illustrator
Editing Capabilities" unchecked, and to set cut-line strokes to **0.216pt
max** ("hairline").

**Could not verify:** no NYC Resistor page we could reach states an official
red/blue engrave/cut color convention. The blue-cut/red-engrave scheme this
project uses is Ben's own choice (DESIGN.md's "Decisions" section), not a
documented NYC Resistor requirement.

**Action before cut day:** bring `sheet_*.svg`, but be ready to re-export as
PDF on the spot if CorelDraw chokes on raw SVG import (per the tips page
above); confirm verbally with staff/proctor whether they expect a specific
cut/engrave color convention.

### Material rules

Per https://www.nycresistor.com/laser/ (verified directly): **bring-your-own
material is explicitly welcomed** ("You're also welcome to bring your
own"), and NYC Resistor also sells limited material on-site (email ahead to
confirm stock). Allowed: acrylic (<=1/4in), wood ("not pressure treated"),
aluminum (etch only), paper/cardboard. Prohibited: anything chlorine-based
(vinyl, many plastics), metal other than aluminum etch, glass (etch only, no
cutting). **Could not verify:** no explicit statement on MDF specifically,
or on plywood glue/coating restrictions -- not stated either way. This
project's material (1/8in / 3.175mm plywood) is not flagged as a problem
anywhere on the site.

### Pricing

Two sources disagree; the newer one governs:

- Current page (https://www.nycresistor.com/laser/, verified directly):
  self-serve **$1/min** (requires taking the laser class first), or
  operator-assisted **$75/hr + $2/min**.
- Wiki pricing page (https://wiki.nycresistor.com/wiki/Laser_Pricing,
  verified directly) is explicitly dated **"current as of May 26, 2016"**
  and marked "subject to change without notice" -- treated as **stale, not
  used** for budgeting.

The laser class required for the self-serve rate runs "usually once a
month" and is still active (a 2026-04-13-dated class listing was live at
research time). No separate membership requirement is stated for laser
access itself.

### Machine

**Epilog Fusion 32, 60W** -- stated on both
https://www.nycresistor.com/laser/ and
https://wiki.nycresistor.com/wiki/Laser (verified directly).

### Sources checked (access date: 2026-07-07)

| URL | Status |
|---|---|
| https://www.nycresistor.com/participate/laser/ | reachable (serves the same content as `/laser/`) |
| https://www.nycresistor.com/laser/ | reachable, verified directly |
| https://wiki.nycresistor.com/wiki/Laser | reachable, verified directly |
| https://wiki.nycresistor.com/wiki/Laser_Pricing | reachable, but stale (dated 2016) |
| https://wiki.nycresistor.com/wiki/Laser_Power | reachable |
| https://wiki.nycresistor.com/wiki/Laser_Tips_and_Tricks | reachable, verified directly |

### What we could NOT verify

- The real cuttable bed size (32in x 20in stated vs. 12in x 24in disputed in
  a page comment) -- this project uses the conservative 18in x 24in fallback
  instead of trusting either figure.
- Any official red/blue cut/engrave color convention.
- Any MDF-specific or plywood-glue-specific material restriction.
