"""Per-feature laser rules on the art AS EXPORTED: after faxbox.cutset has
placed it on the part and trimmed it back from the burnt cut edge.

Run with FAXBOX_THICKNESS=T in the environment (the geometry reads it at
import). Prints one JSON line per (kerf, part, variant):
  {"T", "kerf", "item", "variant", "thin", "gap", "thin_at", "gap_at"}

usage: FAXBOX_THICKNESS=3.2 trimmed_check.py [kerf ...]
"""
import json
import os
import sys
import tempfile
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage as ndi

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "src"))
from faxart import rules  # noqa: E402
from faxbox import cutset as cs  # noqa: E402
from faxbox import engrave as eg  # noqa: E402

PPM = rules.RULE_PPM


def raster(geom, x0, y0, W, H):
    m = np.zeros((int(round(H * PPM)) + 2, int(round(W * PPM)) + 2), np.uint8)
    polys = list(geom.geoms) if hasattr(geom, "geoms") else [geom]

    def pts(c):
        a = (np.asarray(c)[:, :2] - (x0, y0)) * PPM
        return np.round(a * 16).astype(np.int32).reshape(-1, 1, 2)

    for p in polys:
        if p.geom_type != "Polygon" or p.is_empty:
            continue
        cv2.fillPoly(m, [pts(p.exterior.coords)], 1, lineType=cv2.LINE_8, shift=4)
        for r in p.interiors:
            cv2.fillPoly(m, [pts(r.coords)], 0, lineType=cv2.LINE_8, shift=4)
    return m.astype(bool)


def where(mask, x0, y0):
    lab, n = ndi.label(mask, structure=np.ones((3, 3)))
    out = []
    for sl in ndi.find_objects(lab)[:5]:
        out.append((round(x0 + (sl[1].start + sl[1].stop) / 2 / PPM, 1),
                    round(y0 + (sl[0].start + sl[0].stop) / 2 / PPM, 1)))
    return out


def main():
    T = float(os.environ["FAXBOX_THICKNESS"])
    kerfs = [float(k) for k in sys.argv[1:]] or [0.12, 0.20]
    for kerf in kerfs:
        items = cs.generate_items(Path(tempfile.mkdtemp()), kerf)
        for it in items:
            if not it.face:
                continue
            for v in eg.variants(it.face):
                r = cs.clearance(it, v["id"])
                ink = r["ink"]
                if ink.is_empty:
                    continue
                x0, y0, x1, y1 = r["material"].bounds
                m = raster(ink.buffer(0), x0, y0, x1 - x0, y1 - y0)
                thin, gap, nt, ng = rules.violations(m, line_mm=rules.RULE_LINE_MM, gap_mm=rules.RULE_GAP_MM)
                # a 'gap' at the burnt edge is the trim itself, not a gap
                # between two engraved areas: only count gaps fully inside
                # the material, away from the cut edge
                mat = raster(r["material"], x0, y0, x1 - x0, y1 - y0)
                inner = ndi.distance_transform_edt(mat) > (cs.KEEPOUT + 0.1) * PPM
                gap &= inner
                lab, n = ndi.label(gap, structure=np.ones((3, 3)))
                ng = int((np.bincount(lab.ravel())[1:] >= rules.FEATURE_MM2 * PPM ** 2).sum())
                print(json.dumps({"T": T, "kerf": kerf, "item": it.name, "face": it.face,
                                  "variant": v["id"], "thin": nt, "gap": ng,
                                  "thin_at": where(thin, x0, y0), "gap_at": where(gap, x0, y0)}),
                      flush=True)


if __name__ == "__main__":
    main()
