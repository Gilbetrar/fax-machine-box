#!/usr/bin/env python3
"""Build the code-drawn engraving art.

    .venv/bin/python art/code/build.py            # every face
    .venv/bin/python art/code/build.py left_wall  # just some faces

Writes art/code/out/<face>__<variant>.svg + .png and art/code/manifest.json.
Deterministic: fixed seeds, fixed source crops, no network, no image models.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from faxart.finish import emit  # noqa: E402
from faxart import ai_faces, faceplate_faces, lid_faces  # noqa: E402
from faxart.faces import RECIPES  # noqa: E402

RECIPES = {**RECIPES, **ai_faces.RECIPES, **lid_faces.RECIPES, **faceplate_faces.RECIPES}
from faxart.geometry import FACES, frame, size_mm  # noqa: E402

MANIFEST = HERE / "manifest.json"

STYLE = {
    "name": "traced-line + coded hatch",
    "description": (
        "Ben's hand-drawn linework traced to smooth vector fills, keeping the marker's "
        "stroke-weight variation. Shading is redrawn in code as hand-style hatching "
        "(per-stroke angle jitter, wobble, ragged ends) at laser-safe spacing. "
        "Large solids get gap channels unless they are display lettering. Rules: "
        "every line >= 0.25 mm, every gap >= 0.30 mm, no islands < 0.09 mm2, at least 0.4 mm clear of every cut."
    ),
}


def main(argv: list[str]) -> None:
    wanted = argv or list(FACES)
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {"faces": {}}
    for face_id in wanted:
        t0 = time.time()
        variants = RECIPES[face_id](face_id)
        f = FACES[face_id]
        entries = [emit(face_id, v) for v in variants]
        manifest["faces"][face_id] = {
            "part_id": face_id, "title": f.title, "size_mm": list(size_mm(face_id)),
            "frame": "exterior view: u right, v down, mm, over the part's nominal rectangle",
            **{k: v for k, v in frame(face_id).items() if k != "horizontal"},
            "engrave_part_flipped": frame(face_id)["exterior_face"] == "-",
            "variants": entries,
        }
        print(f"{face_id}: " + ", ".join(f"{e['id']} {e['ink_pct']}%" for e in entries)
              + f"  ({time.time() - t0:.0f}s)")
    manifest["faces"] = {k: manifest["faces"][k] for k in FACES if k in manifest["faces"]}
    manifest["style"] = STYLE
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")


if __name__ == "__main__":
    main(sys.argv[1:])
