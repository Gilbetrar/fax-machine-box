"""Generate cut-file sets for every stock thickness (2.8 ... 3.5 mm).

    python scripts/export_cutfiles.py [--out site/downloads] [--only 3.2 3.3]

For each thickness T this runs `python -m faxbox.cutset` in its own process
with FAXBOX_THICKNESS=T (the geometry reads T at import time), then writes

    <out>/T<T>/<bed>_sheet_N.svg|dxf          cut only: ponoko, xtool_s1, xtool_p2,
                                              glowforge_pro, generic_600x400
    <out>/T<T>/<bed>_sheet_N_engrave.svg|dxf  cut + engrave, same layout, default art
    <out>/T<T>/faces/<face>__<variant>.svg|dxf  one part per art variant (all variants)
    <out>/T<T>/coupon.svg|dxf                 test-fit coupon
    <out>/T<T>/set.json, README_engrave.txt
    <out>/fax-machine-box_T<T>.zip            cut only (sheets + coupon + set.json)
    <out>/fax-machine-box_T<T>_engrave.zip    cut + engrave (sheets + faces + coupon + README)
    <out>/manifest.json                       schema 2, see below

manifest.json (schema 2)
    schema: 2
    beds:   bed -> size, margin, spacing, sheets_by_thickness (same for both versions)
    engrave: colors, dxf_layers, dxf_note, conventions, default_variants,
             faces: face -> {title, part_id, flipped, exterior_face,
                             variants: [{id, label, default, notes, ink_pct}]}
    thicknesses: "3.2" -> {
        folder, zip, files, sheets          legacy keys = cut_only
        cut_only:    {zip, files, sheets: {bed: n}}
        cut_engrave: {zip, files, sheets: {bed: n}, default_variants}
        faces: face -> variant -> {svg, dxf, min_clearance_mm}   (paths inside folder)
    }
A site shows "Cut only" from cut_only and "Cut + engrave" from cut_engrave.

Everything is deterministic.  Do not commit the generated downloads when
they pass ~30 MB (the script prints the total and writes a .gitignore into
the output folder in that case).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
THICKNESSES = [round(2.8 + 0.1 * i, 1) for i in range(8)]
SIZE_LIMIT = 30 * 1024 * 1024


def _zip(path: Path, root: Path, names: list[str], top: str) -> None:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name in sorted(names):
            zi = zipfile.ZipInfo(f"{top}/{name}", (2026, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, (root / name).read_bytes())


def build_one(t: float, out: Path) -> dict:
    folder = out / f"T{t:.1f}"
    if folder.exists():
        shutil.rmtree(folder)
    env = dict(os.environ, FAXBOX_THICKNESS=str(t), PYTHONPATH=str(SRC))
    subprocess.run([sys.executable, "-m", "faxbox.cutset", str(folder)], check=True, env=env,
                   capture_output=True)
    info = json.loads((folder / "set.json").read_text())
    top = f"fax-machine-box_T{t:.1f}"
    cut_files = sorted(info["files"]) + ["set.json"]
    eng_files = sorted(f for f in info["engrave_files"] + info["face_files"]) + ["coupon.svg", "coupon.dxf", "set.json"]
    _zip(out / f"{top}.zip", folder, cut_files, top)
    _zip(out / f"{top}_engrave.zip", folder, eng_files, top)
    info["zip"] = f"{top}.zip"
    info["zip_engrave"] = f"{top}_engrave.zip"
    info["cut_files"] = cut_files
    info["eng_files"] = eng_files
    return info


def engrave_block(eg) -> dict:
    faces = {}
    for f in eg.faces():
        m = eg.art_manifest()[f]
        faces[f] = {"title": m["title"], "part_id": m["part_id"], "flipped": bool(m["engrave_part_flipped"]),
                    "exterior_face": m["exterior_face"],
                    "variants": [{"id": v["id"], "label": v["label"], "default": bool(v.get("default")),
                                  "notes": v.get("notes", ""), "ink_pct": v.get("ink_pct")}
                                 for v in m["variants"]]}
    return {
        "colors": {"cut": "#0000FF", "engrave_fill": "#000000", "engrave_line": "#FF0000"},
        "dxf_layers": {"cut": "CUT", "engrave": "ENGRAVE"},
        "dxf_note": "DXF has no fill attribute: the engraved art is closed polylines on layer ENGRAVE, "
                    "so set that layer to fill / raster in the laser software.",
        "conventions": [
            "Cuts are kerf-offset; engraving is not.",
            "Engraving stays at least 0.35 mm from every cut.",
            "Lay every part on the bed outside face up. Parts flagged 'flipped' are mirrored in the "
            "cut + engrave files for this; the art is not mirrored.",
            "The drawer faceplate glue-up outline of the cut-only files is left out of the cut + engrave files.",
        ],
        "default_variants": {f: eg.default_variant(f) for f in eg.faces()},
        "faces": faces,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "site" / "downloads"))
    ap.add_argument("--only", nargs="*", type=float)
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    ts = [t for t in THICKNESSES if not a.only or t in a.only]
    with ThreadPoolExecutor(max_workers=4) as ex:
        infos = list(ex.map(lambda t: build_one(t, out), ts))

    sys.path.insert(0, str(SRC))
    from faxbox import engrave as eg
    from faxbox.cutset import BEDS, HOBBY_AND_SERVICE_BEDS, README_ENGRAVE  # noqa: F401
    manifest = {"schema": 2, "beds": {}, "engrave": engrave_block(eg), "thicknesses": {}}
    for bed in HOBBY_AND_SERVICE_BEDS:
        w, h, margin, spacing = BEDS[bed]
        manifest["beds"][bed] = {"width_mm": w, "height_mm": h, "margin_mm": margin, "spacing_mm": spacing,
                                 "sheets_by_thickness": {}}
    for t, info in zip(ts, infos):
        key = f"{t:.1f}"
        sheets = {b: info["beds"][b]["sheets"] for b in HOBBY_AND_SERVICE_BEDS}
        faces = {}
        for f in eg.faces():
            faces[f] = {v["id"]: {"svg": f"faces/{f}__{v['id']}.svg", "dxf": f"faces/{f}__{v['id']}.dxf",
                                  "min_clearance_mm": info["engrave"]["min_clearance_mm"][f"{f}/{v['id']}"]}
                        for v in eg.variants(f)}
        manifest["thicknesses"][key] = {
            "folder": f"T{key}", "zip": info["zip"], "files": info["cut_files"], "sheets": sheets,
            "cut_only": {"zip": info["zip"], "files": info["cut_files"], "sheets": sheets},
            "cut_engrave": {"zip": info["zip_engrave"], "files": info["eng_files"], "sheets": sheets,
                            "default_variants": info["engrave"]["default_variants"]},
            "faces": faces,
        }
        for b in HOBBY_AND_SERVICE_BEDS:
            manifest["beds"][b]["sheets_by_thickness"][key] = sheets[b]
    (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n")

    total = sum(f.stat().st_size for f in out.rglob("*") if f.is_file())
    print(f"{len(ts)} sets, {total / 1024 / 1024:.1f} MB in {out}")
    gi = out / ".gitignore"
    if total > SIZE_LIMIT:
        gi.write_text("*\n!manifest.json\n!.gitignore\n")
        print("over 30 MB: wrote .gitignore, commit only manifest.json")
    elif gi.exists():
        gi.unlink()


if __name__ == "__main__":
    main()
