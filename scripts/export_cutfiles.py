"""Generate cut-file sets for every stock thickness (2.8 ... 3.5 mm).

    python scripts/export_cutfiles.py [--out site/downloads] [--only 3.2 3.3]

For each thickness T this runs `python -m faxbox.cutset` in its own process
with FAXBOX_THICKNESS=T (the geometry reads T at import time), then writes

    <out>/T<T>/<bed>_sheet_N.svg|dxf     ponoko, xtool_s1, xtool_p2,
                                         glowforge_pro, generic_600x400
    <out>/T<T>/coupon.svg|dxf            test-fit coupon
    <out>/T<T>/set.json                  what is on which sheet
    <out>/fax-machine-box_T<T>.zip       the folder, deterministic
    <out>/manifest.json                  thickness -> files, bed -> sheets

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


def build_one(t: float, out: Path) -> dict:
    folder = out / f"T{t:.1f}"
    if folder.exists():
        shutil.rmtree(folder)
    env = dict(os.environ, FAXBOX_THICKNESS=str(t), PYTHONPATH=str(SRC))
    subprocess.run([sys.executable, "-m", "faxbox.cutset", str(folder)], check=True, env=env,
                   capture_output=True)
    info = json.loads((folder / "set.json").read_text())
    zpath = out / f"fax-machine-box_T{t:.1f}.zip"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(folder.iterdir()):
            zi = zipfile.ZipInfo(f"fax-machine-box_T{t:.1f}/{f.name}", (2026, 1, 1, 0, 0, 0))
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = 0o644 << 16
            z.writestr(zi, f.read_bytes())
    info["zip"] = zpath.name
    return info


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
    manifest = {"thicknesses": {}, "beds": {}}
    from faxbox.cutset import BEDS, HOBBY_AND_SERVICE_BEDS
    for bed in HOBBY_AND_SERVICE_BEDS:
        w, h, margin, spacing = BEDS[bed]
        manifest["beds"][bed] = {"width_mm": w, "height_mm": h, "margin_mm": margin, "spacing_mm": spacing,
                                 "sheets_by_thickness": {}}
    for t, info in zip(ts, infos):
        key = f"{t:.1f}"
        manifest["thicknesses"][key] = {
            "folder": f"T{key}", "zip": info["zip"],
            "files": sorted(info["files"]),
            "sheets": {b: info["beds"][b]["sheets"] for b in HOBBY_AND_SERVICE_BEDS},
        }
        for b in HOBBY_AND_SERVICE_BEDS:
            manifest["beds"][b]["sheets_by_thickness"][key] = info["beds"][b]["sheets"]
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
