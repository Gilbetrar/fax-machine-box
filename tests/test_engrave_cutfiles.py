"""Engraving art in the downloadable cut files (faxbox.engrave, faxbox.cutset).

Covers
  * the cut+engrave sheets keep the layout of the cut-only sheets,
  * the colour / layer conventions (blue cut, black fill, DXF layers CUT and
    ENGRAVE),
  * engraving never touches a cut: at least 0.35 mm clear, inside the
    material, for every part and every art variant, checked on the WRITTEN
    files, at the default thickness and at both ends of the stock range,
  * parts whose drawn outline shows the interior face are mirrored so they
    lie exterior face up, and the art is not mirrored.  The 3D proof maps the
    mirrored cut outline back through the bed-to-part rotation and the
    part's own transform and checks it fills exactly the volume of the
    original, that the finger joints still mate, and that the art lands on
    the outside face the right way up.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import shapely
from shapely.affinity import affine_transform, translate
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from faxbox import assembly3d as a3
from faxbox import config as c
from faxbox import cutset as cs
from faxbox import engrave as eg

ROOT = Path(__file__).resolve().parent.parent
T = c.T

EXPECTED_DEFAULTS = {"left": "solid", "right": "nofunfor", "top": "a", "lid": "a"}
FLIPPED = {"top", "lid", "B_face", "T_face", "B_left", "T_left"}
NOT_FLIPPED = {"left", "right", "front", "B_right", "T_right"}


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("engrave_set")
    info = cs.build_set(out)
    return out, info


@pytest.fixture(scope="module")
def items(tmp_path_factory):
    return cs.generate_items(tmp_path_factory.mktemp("items"))


@pytest.fixture(scope="module")
def art_items(items):
    return [it for it in items if it.face]


@pytest.fixture(scope="module")
def plates():
    return a3.all_plates()


# --- sheet parsing helpers ---------------------------------------------------------------------

def parse_sheet(path: Path):
    """[{part, face, cuts: [subs], fills: [subs], strokes: [subs], attrs}] per part group."""
    txt = path.read_text()
    parts = []
    for m in re.finditer(r"<g ([^>]*)>(.*?)</g>", txt, flags=re.S):
        attrs = dict(re.findall(r'([\w-]+)="([^"]*)"', m.group(1)))
        rec = {"attrs": attrs, "part": attrs["data-part"], "cuts": [], "fills": [], "strokes": []}
        for p in re.finditer(r"<path ([^>]*?)/>", m.group(2)):
            a = dict(re.findall(r'([\w-]+)="([^"]*)"', p.group(1)))
            subs = eg.parse_subpaths(a["d"])
            if a.get("stroke") == "rgb(0,0,255)":
                rec["cuts"].extend(subs)
            elif a.get("fill") == "#000000":
                rec["fills"].extend(subs)
            elif a.get("stroke") == "rgb(255,0,0)":
                rec["strokes"].extend(subs)
            else:
                raise AssertionError(a)
        parts.append(rec)
    return parts


def written_clearance(rec: dict, tol: float = 0.002) -> dict:
    """Engrave-to-cut figures computed only from what is in the file."""
    cut_flat = eg.flatten(rec["cuts"], tol)
    cut_lines = unary_union([LineString(p + ([p[0]] if closed else [])) for p, closed in cut_flat if len(p) > 1])
    rings = sorted((Polygon(p).buffer(0) for p, closed in cut_flat if closed and len(p) > 2), key=lambda r: -r.area)
    material = rings[0]
    for h in rings[1:]:
        material = material.difference(h)
    flat = eg.flatten(rec["fills"], tol)
    ink_rings = [Polygon(p).buffer(0) for p, _ in flat if len(p) > 2]
    ink = unary_union([p for p, _ in eg.ink_components(ink_rings)]) if ink_rings else Polygon()
    for sub in rec["strokes"]:
        ink = ink.union(LineString([q for pts, _ in eg.flatten([sub], tol) for q in pts]))
    return {"distance": cut_lines.distance(ink) if not ink.is_empty else np.inf,
            "outside": ink.difference(material).area,
            "crosses": cut_lines.intersects(ink) if not ink.is_empty else False,
            "ink_area": ink.area}


# --- defaults / schema of the art ------------------------------------------------------------------

def test_default_variants_are_the_agreed_ones():
    d = cs.default_variants()
    assert len(d) == 11
    for face, var in EXPECTED_DEFAULTS.items():
        assert d[face] == var
    for face, var in d.items():
        if face not in EXPECTED_DEFAULTS:
            assert len(eg.variants(face)) == 1


def test_flip_flags_match_the_art_manifest(plates):
    """The manifest flags agree with the 3D model: a part is flipped exactly when
    its drawn (local +z) face points into the box."""
    assert {f for f in eg.faces() if eg.is_flipped(f)} == FLIPPED
    for f in eg.faces():
        P = plates[f]
        assert (P.outward_sign(a3._view_reference(f)) < 0) == eg.is_flipped(f), f


# --- layout and conventions ----------------------------------------------------------------------

def test_engrave_sheets_keep_the_cut_layout(built):
    out, info = built
    for bed, b in info["beds"].items():
        for n in range(1, b["sheets"] + 1):
            plain = parse_sheet(out / f"{bed}_sheet_{n}.svg")
            eng = parse_sheet(out / f"{bed}_sheet_{n}_engrave.svg")
            assert [p["part"] for p in plain] == [p["part"] for p in eng]
            for a, e in zip(plain, eng):
                if e["attrs"].get("data-engrave"):
                    assert a["attrs"].get("data-engrave") is None
                ba = unary_union([LineString(p) for p, _ in eg.flatten(a["cuts"], 0.05)]).bounds
                be = unary_union([LineString(p) for p, _ in eg.flatten(e["cuts"], 0.05)]).bounds
                assert np.allclose(ba, be, atol=0.01), (bed, n, a["part"], ba, be)
    assert "ponoko_sheet_1_engrave.svg" in " ".join(info["engrave_files"])


def test_art_parts_are_the_eleven_faces_and_stay_upright(built):
    out, info = built
    for bed, b in info["beds"].items():
        seen = []
        for n in range(1, b["sheets"] + 1):
            for rec in parse_sheet(out / f"{bed}_sheet_{n}_engrave.svg"):
                if rec["attrs"].get("data-engrave"):
                    seen.append(rec["attrs"]["data-engrave"].split("/")[0])
                    assert rec["fills"], rec["part"]
                    assert (rec["attrs"].get("data-mirrored") is not None) == (seen[-1] in FLIPPED)
        assert sorted(seen) == sorted(eg.faces()), bed
    # default variants are the ones on the sheets
    rec = next(r for r in parse_sheet(out / "ponoko_sheet_1_engrave.svg") if r["attrs"].get("data-engrave", "").startswith("left/"))
    assert rec["attrs"]["data-engrave"] == "left/solid"


def test_colours_and_no_text(built):
    out, info = built
    for f in list(out.glob("*_engrave.svg")) + list((out / "faces").glob("*.svg")):
        txt = f.read_text()
        assert "<text" not in txt
        assert set(re.findall(r'stroke="([^"]+)"', txt)) <= {"rgb(0,0,255)", "rgb(255,0,0)"}
        assert set(re.findall(r'fill="([^"]+)"', txt)) <= {"none", "#000000"}
        assert 'stroke="rgb(0,0,255)"' in txt and 'fill="#000000"' in txt
        assert 'stroke-width="0.0762"' in txt              # hairline
    # cut-only files stay cut-only and carry the generator's glue-up outline on the faceplates
    plain = (out / "ponoko_sheet_2.svg").read_text() + (out / "ponoko_sheet_1.svg").read_text()
    assert "#000000" not in plain


def test_dxf_layers(built):
    out, _ = built
    for name in ("ponoko_sheet_1_engrave", "faces/left__solid", "faces/lid__a"):
        dxf = (out / f"{name}.dxf").read_text()
        svg = parse_sheet(out / f"{name}.svg")
        assert dxf.rstrip().endswith("EOF")
        layers = re.findall(r"POLYLINE\n8\n(\w+)\n66\n1\n70\n(\d)", dxf)
        cut = [cl for l, cl in layers if l == "CUT"]
        eng = [cl for l, cl in layers if l == "ENGRAVE"]
        assert set(l for l, _ in layers) == {"CUT", "ENGRAVE"}
        assert len(cut) == sum(len(r["cuts"]) for r in svg)
        assert all(cl == "1" for cl in eng), "engrave fills must be closed polylines"
        assert len(eng) >= sum(len(r["fills"]) for r in svg) * 0.95   # DXF thinning never drops a ring wholesale
        assert "LAYER\n2\nCUT" in dxf and "LAYER\n2\nENGRAVE" in dxf


def test_every_variant_has_a_face_file(built):
    out, info = built
    want = {f"{f}__{v['id']}" for f in eg.faces() for v in eg.variants(f)}
    have = {Path(p).stem for p in info["face_files"] if p.endswith(".svg")}
    assert have == want
    for stem in want:
        face, var = stem.split("__")
        rec = parse_sheet(out / "faces" / f"{stem}.svg")
        assert len(rec) == 1 and rec[0]["attrs"]["data-engrave"] == f"{face}/{var}"
        assert (out / "faces" / f"{stem}.dxf").exists()


def test_engrave_is_not_kerf_offset(art_items):
    """Cuts carry the kerf offset (piece outline = nominal grown by BURN); art
    is placed from the nominal frame with no offset."""
    for it in art_items:
        g = a3.pg.load_part(it.src)
        cuts, _ = cs.bed_subpaths(it)
        mat, _ = cs.cut_geometry(cuts)
        # unflipped frame check on the outline bounds: burned bbox is nominal + tabs + 2*BURN
        gb = g.outer.bounds
        mb = mat.bounds
        assert abs((mb[2] - mb[0]) - (gb[2] - gb[0] + 2 * cs.BURN)) < 0.02, it.name
        assert abs((mb[3] - mb[1]) - (gb[3] - gb[1] + 2 * cs.BURN)) < 0.02, it.name


# --- registration: art frame, burn, and the part's own outline ----------------------------------

def _bed_material(item):
    cuts, _ = cs.bed_subpaths(item)
    mat, _ = cs.cut_geometry(cuts)
    return mat


def _zero_kerf_bed(item):
    """Bed-frame material with the kerf taken back out (what the laser leaves)."""
    return _bed_material(item).buffer(-cs.BURN, quad_segs=32)


def test_pieces_register_to_the_part_outlines(art_items):
    """Zero-kerf part outline, placed with the registration affine and
    optionally mirrored, grown by BURN reproduces the piece outline.  Proves
    the letter -> part mapping and the registration used for the art."""
    for it in art_items:
        g = a3.pg.load_part(it.src)
        m = eg.compose(eg.bed_flip(it.piece, it.face), eg.local_to_piece(it.piece, it.src, cs.BURN))
        solid = affine_transform(g.solid, [m[0], m[2], m[1], m[3], m[4], m[5]])
        mat = _bed_material(it)

        def sym(dx=0.0, dy=0.0):
            grown = translate(solid, dx, dy).buffer(cs.BURN, quad_segs=32)
            return grown.symmetric_difference(mat).area

        # slits narrower than the kerf (the 0.05 mm hole-row breakouts) merge when grown:
        # that is the small residue on the shell walls
        s0 = sym()
        assert s0 / mat.area < 2e-3, (it.name, s0)
        for dx, dy in ((0.05, 0), (-0.05, 0), (0, 0.05), (0, -0.05)):
            assert sym(dx, dy) > s0 + 2.0, (it.name, dx, dy)      # registration is sharp to 0.05 mm


@pytest.mark.parametrize("face", sorted(FLIPPED | NOT_FLIPPED))
def test_art_is_never_mirrored_on_the_bed(face, art_items):
    """With the part exterior-up, art coordinates equal bed coordinates up to a
    translation: identity linear part, for every face."""
    it = next(i for i in art_items if i.face == face)
    m = eg.art_to_piece_svg(it.piece, face, it.src, cs.BURN)
    assert (m[0], m[1], m[2], m[3]) == (1.0, 0.0, 0.0, 1.0), (face, m)
    # and the art canvas (nominal rectangle) sits inside the piece bbox
    w, h = eg.art_size(face)
    x0, y0 = eg.apply(m, 0, 0)
    x1, y1 = eg.apply(m, w, h)
    pc = it.piece
    assert pc.xmin - 1e-6 <= x0 and x1 <= pc.xmin + pc.width + 1e-6
    assert pc.ymin - 1e-6 <= y0 and y1 <= pc.ymin + pc.height + 1e-6


# --- the 3D proof ----------------------------------------------------------------------------------------

def _rot_bed_to_local(kind, X0, Y0):
    """Rigid motion, bed physical frame (X right, Y up the sheet, Z up) ->
    part-local frame (x right, y up, z thickness), for a part lying on the bed
    with `kind` of flip.  Turning a part over is a 180 degree rotation about
    an in-plane axis: Y axis for 'v', X axis for 'h'."""
    if kind is None:
        R = np.diag([1.0, 1.0, 1.0])
        t = np.array([-X0, -Y0, 0.0])
    elif kind == "v":
        R = np.diag([-1.0, 1.0, -1.0])
        t = np.array([X0, -Y0, T])
    else:
        R = np.diag([1.0, -1.0, -1.0])
        t = np.array([-X0, Y0, T])
    assert abs(np.linalg.det(R) - 1.0) < 1e-12          # a real rotation, not a mirror
    return R, t


def _round_trip(it, P, solid_bed_svg):
    """Bed outline (SVG coords, y down) -> physical bed frame -> part-local frame
    through the physical rotation, aligned by bounding box."""
    g = P.part
    kind = eg.flip_kind(it.face)
    bed_phys = affine_transform(solid_bed_svg, [1, 0, 0, -1, 0, 0])      # X = x, Y = -y
    bx0, by0, bx1, by1 = bed_phys.bounds
    lx0, ly0, lx1, ly1 = g.solid.bounds
    # translation chosen so the rotated bbox lands on the part's bbox
    if kind is None:
        X0, Y0 = bx0 - lx0, by0 - ly0
    elif kind == "v":
        X0, Y0 = bx1 + lx0, by0 - ly0
    else:
        X0, Y0 = bx0 - lx0, by1 + ly0
    R, t = _rot_bed_to_local(kind, X0, Y0)
    a, b, d, e = R[0, 0], R[0, 1], R[1, 0], R[1, 1]
    return kind, R, t, affine_transform(bed_phys, [a, b, d, e, t[0], t[1]])


@pytest.fixture(scope="module")
def proofs(art_items, plates):
    """Per art part: the written cut outline (kerf removed again) mapped back to
    the part-local frame."""
    out = {}
    for it in art_items:
        P = plates[it.face]
        kind, R, t, local = _round_trip(it, P, _zero_kerf_bed(it))
        out[it.face] = (it, P, kind, R, t, local)
    return out


@pytest.fixture(scope="module")
def proofs_exact(art_items, plates):
    """Same chain on the zero-kerf outline (no kerf rounding), for the joint check."""
    out = {}
    for it in art_items:
        P = plates[it.face]
        m = eg.compose(eg.bed_flip(it.piece, it.face), eg.local_to_piece(it.piece, it.src, 0.0))
        bed = affine_transform(P.local, [m[0], m[2], m[1], m[3], m[4], m[5]])
        kind, R, t, local = _round_trip(it, P, bed)
        out[it.face] = (it, P, kind, R, t, local)
    return out


@pytest.mark.parametrize("face", sorted(FLIPPED | NOT_FLIPPED))
def test_mirrored_cut_outline_fills_the_same_volume(face, proofs):
    """Mirrored cut outline -> bed-to-part rotation -> part's own transform: the
    same volume as the original plate."""
    it, P, kind, R, t, local = proofs[face]
    assert (kind is not None) == (face in FLIPPED)
    orig = P.local
    sym = local.symmetric_difference(orig).area
    assert sym / orig.area < 2e-3, (face, sym, orig.area)
    # same plate, other representation: volume of the intersection in box space
    P2 = a3.Plate(face)
    P2.local = local
    vol_orig = orig.area * (P.rc[1] - P.rc[0])
    inter = a3.pair_volume(P2, P2.geom, P, P.geom)
    assert inter / vol_orig > 0.998, (face, inter, vol_orig)
    assert abs(P2.geom.area - P.geom.area) / P.geom.area < 2e-3


def test_exterior_face_is_up_and_art_is_upright_in_the_box(proofs):
    """Bed top face -> part-local z -> box direction: it is the exterior face of
    the finished box, and the art axes (u right, v down on the bed) point the
    way the art manifest says (right, and 'up' = -v)."""
    for face, (it, P, kind, R, t, local) in proofs.items():
        m = np.asarray(P.matrix())
        top_local_z = (R @ np.array([0.0, 0.0, 1.0]))[2]            # bed up -> local z axis sign
        outward_local_z = P.outward_sign(a3._view_reference(face))   # +1: local +z points out
        assert top_local_z * outward_local_z > 0, face               # bed-up is outward
        right_box = m[:3, :3] @ (R @ np.array([1.0, 0.0, 0.0]))
        up_box = m[:3, :3] @ (R @ np.array([0.0, 1.0, 0.0]))          # bed Y up = art -v
        man = eg.art_manifest()[face]
        assert np.allclose(right_box, man["art_right"], atol=1e-6), (face, right_box, man["art_right"])
        assert np.allclose(up_box, man["art_up"], atol=1e-6), (face, up_box, man["art_up"])


def test_finger_joints_still_mate_with_the_flipped_parts(proofs_exact, plates):
    """Replace every art part by its mirrored-and-turned-back outline: identical
    to the original, same tab count, no interference, every finger hole still
    filled."""
    Q = dict(plates)
    for face, (it, P, kind, R, t, local) in proofs_exact.items():
        assert local.symmetric_difference(P.local).area < 1e-6, face
        P2 = a3.Plate(face)
        P2.local = local
        P2.holes_local = [h for h in P.holes_local]
        Q[face] = P2
    total, bad = a3.tab_report(Q)
    assert total >= 270 and not bad, bad[:3]
    assert a3.interferences(Q, thr=1.0) == a3.interferences(plates, thr=1.0) == []
    assert a3.unfilled_finger_holes(Q) == a3.unfilled_finger_holes(plates) == []


def test_turning_over_needs_the_art_mirror_only_on_flipped_parts(art_items):
    """Control: with the outline left as drawn, the art would come out mirrored
    on exactly the flipped parts (the chain from art to piece has determinant -1
    there and +1 elsewhere).  The bed flip is what turns that back."""
    for it in art_items:
        raw = eg.compose(eg.local_to_piece(it.piece, it.src, cs.BURN), eg.art_to_local(it.face))
        assert eg.det(raw) == (-1.0 if it.face in FLIPPED else 1.0), it.face
        assert eg.det(eg.bed_flip(it.piece, it.face)) == (-1.0 if it.face in FLIPPED else 1.0)


def test_flipped_outlines_are_symmetric_under_the_turn_over(plates):
    """Design property that keeps the joints mating whichever side is up: the
    outline of every flipped part equals its own mirror image (to the 0.05 mm
    breakout slits)."""
    for face in FLIPPED:
        L = plates[face].local
        x0, y0, x1, y1 = L.bounds
        kind = eg.flip_kind(face)
        m = [-1, 0, 0, 1, x0 + x1, 0] if kind == "v" else [1, 0, 0, -1, 0, y0 + y1]
        assert affine_transform(L, m).symmetric_difference(L).area < 0.1, face


# --- engraving stays off the cuts --------------------------------------------------------------------

MIN_CLEAR = cs.CLEARANCE_MIN


def _check_set(out: Path):
    for f in sorted(out.glob("*_engrave.svg")) + sorted((out / "faces").glob("*.svg")):
        for rec in parse_sheet(f):
            if not rec["fills"] and not rec["strokes"]:
                continue
            r = written_clearance(rec)
            where = (f.name, rec["part"], rec["attrs"].get("data-engrave"))
            assert not r["crosses"], where
            assert r["outside"] < 1e-3, (where, r["outside"])
            assert r["distance"] >= MIN_CLEAR - 1e-9, (where, r["distance"])


def test_no_engrave_crosses_a_cut_and_all_stay_clear(built):
    out, info = built
    _check_set(out)
    clear = info["engrave"]["min_clearance_mm"]
    assert len(clear) == 15
    assert min(clear.values()) >= MIN_CLEAR


def test_art_is_substantial_after_clearance_trim(built):
    """The trim must not eat the art: ink area stays within 1% of the art's own."""
    out, info = built
    for f in (out / "faces").glob("*.svg"):
        rec = parse_sheet(f)[0]
        face, var = rec["attrs"]["data-engrave"].split("/")
        art = eg.load_art(face, var)
        rings = [Polygon(p).buffer(0) for ap in art for p, _ in eg.flatten(ap.subs, 0.01) if len(p) > 2]
        ink = sum(p.area for p, _ in eg.ink_components(rings))
        got = written_clearance(rec)["ink_area"]
        assert abs(got - ink) / ink < 0.01, (f.name, got, ink)


@pytest.mark.parametrize("t", [2.8, 3.5])
def test_clearance_holds_at_both_ends_of_the_stock_range(t, tmp_path):
    """Own process: the geometry reads FAXBOX_THICKNESS at import."""
    code = (
        "import sys, json; from pathlib import Path; from faxbox import cutset as cs;"
        "cs.build_set(Path(sys.argv[1]))"
    )
    env = dict(os.environ, FAXBOX_THICKNESS=str(t), PYTHONPATH=str(ROOT / "src"))
    r = subprocess.run([sys.executable, "-c", code, str(tmp_path)], env=env, capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr[-2000:]
    _check_set(tmp_path)
    info = json.loads((tmp_path / "set.json").read_text())
    assert min(info["engrave"]["min_clearance_mm"].values()) >= MIN_CLEAR


def test_exporter_manifest_schema(tmp_path):
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "export_cutfiles.py"), "--out", str(tmp_path), "--only", "3.2"],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr[-2000:]
    m = json.loads((tmp_path / "manifest.json").read_text())
    assert m["schema"] == 2
    e = m["engrave"]
    assert e["colors"]["cut"] == "#0000FF" and e["colors"]["engrave_fill"] == "#000000"
    assert e["dxf_layers"] == {"cut": "CUT", "engrave": "ENGRAVE"}
    assert "fill" in e["dxf_note"].lower() and "raster" in e["dxf_note"].lower()
    assert set(e["faces"]) == set(eg.faces())
    assert e["faces"]["lid"]["flipped"] is True and e["faces"]["left"]["flipped"] is False
    assert [v["id"] for v in e["faces"]["top"]["variants"]] == ["a", "c"]
    assert e["default_variants"]["right"] == "nofunfor"
    s = m["thicknesses"]["3.2"]
    for kind in ("cut_only", "cut_engrave"):
        v = s[kind]
        assert (tmp_path / v["zip"]).exists()
        assert set(v["sheets"]) == set(m["beds"])
        for f in v["files"]:
            assert (tmp_path / s["folder"] / f).exists(), f
    assert all(f.endswith((".svg", ".dxf")) or f in ("set.json", "README_engrave.txt") for f in s["cut_engrave"]["files"])
    assert "README_engrave.txt" in s["cut_engrave"]["files"]
    assert any(f.startswith("faces/") for f in s["cut_engrave"]["files"])
    assert not any(f.endswith("_engrave.svg") for f in s["cut_only"]["files"])
    assert s["faces"]["lid"]["a"]["svg"] == "faces/lid__a.svg"
    assert s["faces"]["lid"]["a"]["min_clearance_mm"] >= MIN_CLEAR
    # legacy keys the first site data used
    assert s["zip"] == s["cut_only"]["zip"] and s["files"] == s["cut_only"]["files"]
