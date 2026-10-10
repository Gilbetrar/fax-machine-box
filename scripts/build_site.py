"""Prepare site/ for deploy.

    python scripts/build_site.py            # stamp versions only
    python scripts/build_site.py --art      # also copy art/code/out + manifest into the site

What it does:
1. (--art) copies art/code/out/* to site/art/, writes 640 px copies to site/art/sm/
   for phones, and copies art/code/manifest.json to site/data/art-manifest.json
   with a `png_sm` path added to every variant.
2. Hashes everything the page loads (js, css, data, art manifest, render index)
   and stamps that hash into site/js/version.js and the import map, script and
   stylesheet URLs in site/index.html, so a deploy never pairs new HTML with
   cached old JS or data.

Pre-rendered build-guide pictures (site/img/render/) come from
scripts/site_prerender.py, which needs a browser; run it after the geometry
changes, then run this script.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"


def copy_art() -> None:
    from PIL import Image  # only needed for --art

    src = ROOT / "art" / "code" / "out"
    dst = SITE / "art"
    sm = dst / "sm"
    if dst.exists():
        shutil.rmtree(dst)
    sm.mkdir(parents=True)
    for f in sorted(src.iterdir()):
        if f.suffix.lower() not in (".png", ".svg"):
            continue
        shutil.copy2(f, dst / f.name)
        if f.suffix.lower() == ".png":
            im = Image.open(f)
            im.thumbnail((640, 640))
            im.save(sm / f.name, optimize=True)
    man = json.loads((ROOT / "art" / "code" / "manifest.json").read_text())
    for face in man.get("faces", {}).values():
        for v in face.get("variants", []):
            if v.get("png"):
                v["png_sm"] = "art/sm/" + Path(v["png"]).name
    (SITE / "data" / "art-manifest.json").write_text(json.dumps(man, indent=1) + "\n")
    print(f"art: {len(list(dst.glob('*')))} files, small textures in {sm.relative_to(ROOT)}")


def optimize_renders() -> None:
    """Shrink the pre-rendered line-art PNGs (they are drawn at 2x)."""
    from PIL import Image

    d = SITE / "img" / "render"
    before = after = 0
    for f in sorted(d.glob("*.png")):
        before += f.stat().st_size
        im = Image.open(f).convert("RGBA")
        if f.name != "hero.png":
            im.thumbnail((1200, 1200))
            im = im.quantize(colors=96, method=Image.Quantize.FASTOCTREE)
        im.save(f, optimize=True)
        after += f.stat().st_size
    if before:
        print(f"renders: {before // 1024} KB -> {after // 1024} KB")


def site_hash() -> str:
    h = hashlib.sha256()
    for pattern in ("js/*.js", "css/*.css", "data/*.json", "img/render/index.json", "img/render/*.png", "downloads/manifest.json"):
        for f in sorted(SITE.glob(pattern)):
            if f.name == "version.js":
                continue
            h.update(f.name.encode())
            h.update(f.read_bytes())
    return h.hexdigest()[:10]


def stamp(v: str) -> None:
    (SITE / "js" / "version.js").write_text(
        "// Rewritten by scripts/build_site.py with a content hash, so a deploy never pairs new HTML with stale files.\n"
        f"export const V = '{v}';\n")
    html = (SITE / "index.html").read_text()
    imports = {
        "three": f"./vendor/three/build/three.module.min.js",
        "three/addons/": "./vendor/three/examples/jsm/",
    }
    for f in sorted((SITE / "js").glob("*.js")):
        imports[f"./js/{f.name}"] = f"./js/{f.name}?v={v}"
    block = '<script type="importmap">\n' + json.dumps({"imports": imports}, indent=1) + "\n</script>"
    html, n = re.subn(r'<script type="importmap">.*?</script>', lambda m: block, html, flags=re.S)
    assert n == 1, "import map not found"
    html = re.sub(r'(href="css/site\.css)(\?v=[^"]*)?"', rf'\1?v={v}"', html)
    html = re.sub(r'(src="js/page\.js)(\?v=[^"]*)?"', rf'\1?v={v}"', html)
    (SITE / "index.html").write_text(html)
    print("version", v)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--art", action="store_true", help="copy art/code/out into the site first")
    a = ap.parse_args()
    if a.art:
        copy_art()
    optimize_renders()
    stamp(site_hash())


if __name__ == "__main__":
    main()
