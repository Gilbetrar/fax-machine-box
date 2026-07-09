#!/usr/bin/env python3
"""Diagnose non-closing / near-miss blue (#0000FF) cut contours in faxbox's
generated laser-cut SVGs.

Background: a collaborator reported that some blue cut lines in the
generated SVGs are "wonky and don't make it to the edge" -- i.e. visible
endpoint gaps at corners, segments stopping short, or stray/misaligned
segments. The existing test suite (tests/) only asserts bounding-box size
bands, so this class of defect is completely untested. This script is a
one-off diagnostic (not wired into the test suite) to find and quantify the
problem before anyone touches the generator code.

What it does, per file:
  1. Parses every top-level <g> (Boxes.py emits one group per physical
     part; faxbox.layout re-emits the same shape for nested sheets, adding
     a `data-part` attribute). No group carries an SVG `transform`
     attribute in this codebase's current output (verified by inspection),
     so path coordinates are used as-is; a defensive transform-matrix
     applier is still included in case that ever changes.
  2. Extracts every <path> with stroke="rgb(0,0,255)" (blue = cut) and
     manually tokenizes its `d` attribute (only ever M/L/H/V/C/Z, all
     absolute, in every SVG this project currently emits -- verified by
     grep before writing this parser; see the "known limitations" note
     below for what is NOT handled).
  3. Splits each <path> into subpaths at each `M`. For each subpath:
       - If it ends in an explicit `Z`, the SVG spec still draws an
         implicit closing line from the last drawn point back to the
         subpath's start point *even when those two points don't
         coincide* (confirmed against svgpathtools' own parser, which
         inserts exactly that Line segment). So a subpath that "closes"
         syntactically can still render a real, visible diagonal chord if
         its last real vertex drifted away from its start vertex. This
         script computes that drift distance for every Z-closed subpath
         and flags it if it exceeds tolerance -- this is the leading
         hypothesis for "wonky lines that don't make it to the edge".
       - If it has NO explicit Z (a genuinely open polyline), its two free
         endpoints are chain-matched (within tolerance) against every
         other open subpath's free endpoints in the same part, the same
         way a viewer's eye would try to trace a continuous cut line
         across multiple <path> elements. Anything left unmatched is a
         real dangling endpoint.
       - Independently of the above, EVERY subpath's two endpoints
         (start, and last-drawn-point-before-any-implicit-Z) are compared
         pairwise against every other subpath's endpoints in the same
         part, to catch near-miss corners: two separate blue subpaths
         whose corners are supposed to meet but land a fraction of a
         millimeter apart.
  4. Reports, per file and per part: subpath count, any self-closing-gap
     ("Z chord") defects, any dangling open endpoints, and any near-miss
     endpoint pairs, each with the offending coordinates and the gap size
     in mm.

Tolerances (per the task spec):
  - CLOSE_TOL_MM = 0.05  -- gaps at or below this are "closed" (float noise).
  - NEAR_MISS_MM = 0.5   -- gaps in (CLOSE_TOL_MM, NEAR_MISS_MM] are
    "near-miss" (the "doesn't quite reach the edge" symptom).
  - Anything above NEAR_MISS_MM is a hard break / large chord.

Known limitations (kept deliberately simple -- this is a diagnostic, not
production code):
  - Only handles absolute M/L/H/V/C/Z commands (matches every blue path in
    every SVG this project currently emits; would need extending for A
    (arc) or lowercase/relative commands if the generator ever adds them).
  - For C (cubic Bezier) segments, only the segment's *endpoint* is used
    for closure/adjacency math (control points don't affect where the cut
    line starts/ends, only its curvature in between).
  - "Stray/misaligned segment" (a whole subpath floating away from the
    rest of the part, not just a corner gap) is not specifically detected
    beyond what the near-miss/dangling-endpoint checks happen to catch;
    flag visually if the numeric checks come back clean but the complaint
    persists.

Usage:
    .venv/bin/python scratch/check_closure.py [file_or_dir ...]

With no arguments, scans every *.svg in output/ and output/ponoko/
(recursively, but those two dirs are flat so that's every current output).
"""

from __future__ import annotations

import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from xml.etree import ElementTree as ET

SVG_NS = "{http://www.w3.org/2000/svg}"

CLOSE_TOL_MM = 0.05
NEAR_MISS_MM = 0.5

BLUE = "rgb(0,0,255)"


# --- geometry -----------------------------------------------------------

Point = complex  # x + yj, matches svgpathtools' convention


def dist(a: Point, b: Point) -> float:
    return abs(a - b)


_MATRIX_RE = re.compile(r"matrix\(\s*([^)]+)\)")
_TRANSLATE_RE = re.compile(r"translate\(\s*([^)]+)\)")


def parse_transform(transform: str | None) -> tuple[float, float, float, float, float, float]:
    """Return (a,b,c,d,e,f) for an SVG transform attribute. Identity if
    none/unrecognized. Defensive only -- no group in this codebase's
    current output carries a transform on a path-bearing <g> (verified by
    grep), but a nested/product change could introduce one."""
    a, b, c, d, e, f = 1.0, 0.0, 0.0, 1.0, 0.0, 0.0
    if not transform:
        return a, b, c, d, e, f
    m = _MATRIX_RE.search(transform)
    if m:
        nums = [float(x) for x in re.split(r"[\s,]+", m.group(1).strip()) if x]
        if len(nums) == 6:
            return tuple(nums)  # type: ignore[return-value]
    t = _TRANSLATE_RE.search(transform)
    if t:
        nums = [float(x) for x in re.split(r"[\s,]+", t.group(1).strip()) if x]
        if len(nums) == 1:
            return 1.0, 0.0, 0.0, 1.0, nums[0], 0.0
        if len(nums) == 2:
            return 1.0, 0.0, 0.0, 1.0, nums[0], nums[1]
    return a, b, c, d, e, f


def apply_transform(m: tuple[float, float, float, float, float, float], p: Point) -> Point:
    a, b, c, d, e, f = m
    x, y = p.real, p.imag
    return complex(a * x + c * y + e, b * x + d * y + f)


# --- path tokenizing ------------------------------------------------------

_TOKEN_RE = re.compile(r"([MLHVCZ])|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)")
_HANDLED_COMMANDS = set("MLHVCZ")


@dataclass
class Subpath:
    path_index: int  # which <path> element within the part this came from
    subpath_index: int  # which M-block within that <path>
    start: Point
    last_drawn: Point  # last point actually drawn (before any implicit Z line)
    has_explicit_z: bool
    n_points: int  # number of vertices visited (M + each L/H/V/C endpoint)


def tokenize_d(d: str) -> list[tuple[str, list[float]]]:
    """Split a `d` string into (command, [numbers]) ops. Raises if it sees a
    command letter this project has never emitted (see module docstring)."""
    tokens = _TOKEN_RE.findall(d)
    ops: list[tuple[str, list[float]]] = []
    cur_cmd = None
    cur_nums: list[float] = []
    for letter, num in tokens:
        if letter:
            if letter not in _HANDLED_COMMANDS:
                raise ValueError(f"Unhandled path command {letter!r} -- parser needs extending. d={d[:80]!r}")
            if cur_cmd is not None:
                ops.append((cur_cmd, cur_nums))
            cur_cmd = letter
            cur_nums = []
        else:
            cur_nums.append(float(num))
    if cur_cmd is not None:
        ops.append((cur_cmd, cur_nums))
    return ops


_ARITY = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "Z": 0}


def parse_subpaths(d: str, path_index: int) -> list[Subpath]:
    """Walk a `d` string (absolute M/L/H/V/C/Z only) and return one Subpath
    per M-separated block, each carrying its start point, its last-drawn
    point (before any implicit Z closing line), and whether it had an
    explicit Z."""
    ops = tokenize_d(d)
    subpaths: list[Subpath] = []
    cur: Point = 0j
    start: Point | None = None
    subpath_idx = -1
    has_z = False
    n_points = 0

    def flush():
        nonlocal start, has_z, n_points
        if start is not None:
            subpaths.append(
                Subpath(
                    path_index=path_index,
                    subpath_index=subpath_idx,
                    start=start,
                    last_drawn=cur,
                    has_explicit_z=has_z,
                    n_points=n_points,
                )
            )

    for cmd, nums in ops:
        arity = _ARITY[cmd]
        if arity and len(nums) % arity != 0:
            raise ValueError(f"{cmd} expects multiples of {arity} numbers, got {nums}")
        if cmd == "M":
            # A new M inside the same <path> starts a new subpath (per the
            # SVG spec, repeated coordinate pairs after the first are
            # treated as implicit L's, but Boxes.py/faxbox never emit that
            # pattern -- one M starts exactly one subpath in every d seen
            # in this project).
            flush()
            subpath_idx += 1
            has_z = False
            n_points = 1
            x, y = nums[0], nums[1]
            cur = complex(x, y)
            start = cur
            # any extra pairs after the first (implicit L) -- handle just in case
            for i in range(2, len(nums), 2):
                cur = complex(nums[i], nums[i + 1])
                n_points += 1
        elif cmd == "L":
            for i in range(0, len(nums), 2):
                cur = complex(nums[i], nums[i + 1])
                n_points += 1
        elif cmd == "H":
            for x in nums:
                cur = complex(x, cur.imag)
                n_points += 1
        elif cmd == "V":
            for y in nums:
                cur = complex(cur.real, y)
                n_points += 1
        elif cmd == "C":
            for i in range(0, len(nums), 6):
                cur = complex(nums[i + 4], nums[i + 5])
                n_points += 1
        elif cmd == "Z":
            has_z = True
            # cur is NOT reset here -- we want last_drawn to remain the
            # last real vertex, so the caller can measure the implicit
            # closing-line length itself.
    flush()
    return subpaths


# --- SVG loading ------------------------------------------------------------

@dataclass
class PartResult:
    file: str
    part_label: str
    group_id: str
    n_blue_paths: int
    subpaths: list[Subpath] = field(default_factory=list)
    z_gaps: list[tuple[Subpath, float]] = field(default_factory=list)  # (subpath, gap_mm)
    dangling: list[tuple[Subpath, str]] = field(default_factory=list)  # (subpath, which end: 'start'/'end')
    near_misses: list[tuple[Subpath, str, Subpath, str, float]] = field(default_factory=list)


def load_parts(svg_path: Path) -> list[PartResult]:
    tree = ET.parse(svg_path)
    root = tree.getroot()
    results: list[PartResult] = []

    groups = root.findall(f"{SVG_NS}g")
    for gi, g in enumerate(groups):
        part_label = g.get("data-part")
        if not part_label:
            text_el = g.find(f"{SVG_NS}text")
            if text_el is not None and text_el.text:
                part_label = text_el.text.strip()
            else:
                part_label = g.get("id", f"g{gi}")
        group_id = g.get("id", f"g{gi}")

        gm = parse_transform(g.get("transform"))

        blue_paths = [p for p in g.findall(f"{SVG_NS}path") if p.get("stroke") == BLUE and p.get("d")]
        if not blue_paths:
            continue

        pr = PartResult(file=str(svg_path), part_label=part_label, group_id=group_id, n_blue_paths=len(blue_paths))

        all_subpaths: list[Subpath] = []
        for pi, p in enumerate(blue_paths):
            d = p.get("d")
            try:
                sps = parse_subpaths(d, path_index=pi)
            except ValueError as e:
                print(f"  !! PARSE ERROR in {svg_path} part {part_label!r} path {pi}: {e}", file=sys.stderr)
                continue
            if gm != (1.0, 0.0, 0.0, 1.0, 0.0, 0.0):
                sps = [
                    Subpath(
                        path_index=sp.path_index,
                        subpath_index=sp.subpath_index,
                        start=apply_transform(gm, sp.start),
                        last_drawn=apply_transform(gm, sp.last_drawn),
                        has_explicit_z=sp.has_explicit_z,
                        n_points=sp.n_points,
                    )
                    for sp in sps
                ]
            all_subpaths.extend(sps)

        pr.subpaths = all_subpaths

        # --- check 1: self-closing gap ---
        # A subpath is "closed" if its last drawn point coincides with its
        # start point -- whether that's via an explicit `Z` (Boxes.py's own
        # direct output: parse_subpaths' `Z` doesn't move `cur`, so
        # last_drawn stays the last real vertex, and the SVG renderer draws
        # an implicit closing line even if that vertex is nowhere near
        # `start`) OR via an explicit trailing `L` back to the start point
        # (what faxbox.layout's svgpathtools-based re-serialization emits
        # instead of `Z` for sheet_*.svg/final_layout.svg -- confirmed by
        # inspection: svgpathtools.Path.d() with its default
        # use_closed_attrib=False never emits a trailing `Z`, but the
        # closing Line segment parse_path() inserted while reading the
        # *original* Boxes.py `Z` is still in the segment list and gets
        # serialized as a plain `L`). Either way, what matters for a laser
        # is only whether the last drawn point lands back on the start
        # point -- so both cases are checked identically here.
        open_sps: list[Subpath] = []
        for sp in all_subpaths:
            if sp.n_points <= 1:
                continue
            gap = dist(sp.last_drawn, sp.start)
            if gap <= CLOSE_TOL_MM:
                continue  # cleanly self-closed (Z or explicit closing L) -- fine
            if gap <= NEAR_MISS_MM:
                pr.z_gaps.append((sp, gap))  # small self-closing chord/gap
            else:
                # Large enough that this isn't plausibly "meant to
                # self-close" -- treat as a real open end and try to
                # chain-match it against sibling subpaths in the same part
                # before calling it dangling.
                open_sps.append(sp)

        # --- check 2: chain-match genuinely open subpaths (large self-gap) ---
        # each open subpath contributes 2 free ends: ('start', pt) and ('end', pt)
        free_ends: list[tuple[Subpath, str, Point]] = []
        for sp in open_sps:
            free_ends.append((sp, "start", sp.start))
            free_ends.append((sp, "end", sp.last_drawn))

        matched = set()
        for i, (sp_a, which_a, pt_a) in enumerate(free_ends):
            key_a = (id(sp_a), which_a)
            if key_a in matched:
                continue
            best_j = None
            best_d = math.inf
            for j, (sp_b, which_b, pt_b) in enumerate(free_ends):
                if i == j or sp_a is sp_b:
                    continue
                key_b = (id(sp_b), which_b)
                if key_b in matched:
                    continue
                d_ = dist(pt_a, pt_b)
                if d_ < best_d:
                    best_d = d_
                    best_j = j
            if best_j is not None and best_d <= CLOSE_TOL_MM:
                sp_b, which_b, _ = free_ends[best_j]
                matched.add(key_a)
                matched.add((id(sp_b), which_b))

        for sp, which, pt in free_ends:
            if (id(sp), which) not in matched:
                pr.dangling.append((sp, which))

        # --- check 3: near-miss endpoint pairs across DIFFERENT subpaths ---
        all_ends: list[tuple[Subpath, str, Point]] = []
        for sp in all_subpaths:
            all_ends.append((sp, "start", sp.start))
            all_ends.append((sp, "end", sp.last_drawn))

        seen_pairs = set()
        for i in range(len(all_ends)):
            sp_a, which_a, pt_a = all_ends[i]
            for j in range(i + 1, len(all_ends)):
                sp_b, which_b, pt_b = all_ends[j]
                if sp_a is sp_b:
                    continue  # that's check 1's job
                d_ = dist(pt_a, pt_b)
                if CLOSE_TOL_MM < d_ <= NEAR_MISS_MM:
                    pair_key = tuple(sorted([(sp_a.path_index, sp_a.subpath_index, which_a), (sp_b.path_index, sp_b.subpath_index, which_b)]))
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)
                    pr.near_misses.append((sp_a, which_a, sp_b, which_b, d_))

        results.append(pr)

    return results


# --- reporting ------------------------------------------------------------

def fmt_pt(p: Point) -> str:
    return f"({p.real:.3f}, {p.imag:.3f})"


def report(results: list[PartResult]) -> tuple[int, int, int]:
    total_zgaps = total_dangling = total_nearmiss = 0
    for pr in results:
        issues = pr.z_gaps or pr.dangling or pr.near_misses
        if not issues:
            continue
        print(f"\n--- {pr.file}  part={pr.part_label!r} (group {pr.group_id}, {pr.n_blue_paths} blue paths, {len(pr.subpaths)} subpaths) ---")
        for sp, gap in sorted(pr.z_gaps, key=lambda t: -t[1]):
            severity = "HARD OPEN" if gap > NEAR_MISS_MM else "near-miss"
            print(
                f"  [Z-CLOSE GAP: {severity}] path#{sp.path_index} subpath#{sp.subpath_index}: "
                f"start={fmt_pt(sp.start)}  last_drawn={fmt_pt(sp.last_drawn)}  gap={gap:.4f}mm"
            )
            total_zgaps += 1
        for sp, which in pr.dangling:
            pt = sp.start if which == "start" else sp.last_drawn
            print(f"  [DANGLING OPEN END] path#{sp.path_index} subpath#{sp.subpath_index} ({which}) at {fmt_pt(pt)} -- no matching endpoint within {CLOSE_TOL_MM}mm")
            total_dangling += 1
        for sp_a, which_a, sp_b, which_b, d_ in sorted(pr.near_misses, key=lambda t: t[4]):
            pt_a = sp_a.start if which_a == "start" else sp_a.last_drawn
            pt_b = sp_b.start if which_b == "start" else sp_b.last_drawn
            print(
                f"  [NEAR-MISS CORNER] path#{sp_a.path_index}/sub#{sp_a.subpath_index}({which_a}) {fmt_pt(pt_a)}  <->  "
                f"path#{sp_b.path_index}/sub#{sp_b.subpath_index}({which_b}) {fmt_pt(pt_b)}   gap={d_:.4f}mm"
            )
            total_nearmiss += 1
    return total_zgaps, total_dangling, total_nearmiss


def main(argv: list[str]) -> int:
    if argv:
        targets: list[Path] = []
        for a in argv:
            p = Path(a)
            if p.is_dir():
                targets.extend(sorted(p.glob("*.svg")))
            else:
                targets.append(p)
    else:
        repo_root = Path(__file__).resolve().parent.parent
        targets = sorted((repo_root / "output").glob("*.svg")) + sorted((repo_root / "output" / "ponoko").glob("*.svg"))

    print(f"Scanning {len(targets)} SVG file(s) for non-closing / near-miss blue cut contours")
    print(f"Tolerances: CLOSE<= {CLOSE_TOL_MM}mm, NEAR-MISS in ({CLOSE_TOL_MM}, {NEAR_MISS_MM}]mm, HARD-OPEN > {NEAR_MISS_MM}mm")

    grand_zgaps = grand_dangling = grand_nearmiss = 0
    clean_files = []
    for t in targets:
        if not t.exists():
            print(f"\n!! MISSING: {t}", file=sys.stderr)
            continue
        try:
            results = load_parts(t)
        except ET.ParseError as e:
            print(f"\n!! XML PARSE ERROR in {t}: {e}", file=sys.stderr)
            continue
        z, d_, n = report(results)
        grand_zgaps += z
        grand_dangling += d_
        grand_nearmiss += n
        if z == 0 and d_ == 0 and n == 0:
            clean_files.append(str(t))

    print("\n" + "=" * 78)
    print(f"TOTALS across all scanned files: {grand_zgaps} Z-close gaps, {grand_dangling} dangling open ends, {grand_nearmiss} near-miss corner pairs")
    print(f"Clean files (no issues found): {len(clean_files)}/{len(targets)}")
    for f in clean_files:
        print(f"  OK  {f}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
