"""Shared finishing: laser rules, cut keep-out, trace, write, measure."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from . import raster as R
from . import rules
from . import vector as V
from .geometry import FACES, material_mask, size_mm

OUT = Path(__file__).resolve().parents[1] / "out"


def finish(face_id: str, ink: np.ndarray, protect: np.ndarray | None = None,
           knock: bool = True, keepout_mm: float = R.KEEPOUT_MM,
           thicken_mm: float = 0.35, knock_min_area: float = 45.0) -> np.ndarray:
    """ink (bool, canvas at R.PPM) -> laser-legal mask clipped to the wood."""
    mat = material_mask(face_id, R.PPM, keepout_mm)
    assert mat.shape == ink.shape, (mat.shape, ink.shape)
    orig = ink & mat
    m = R.remove_small(orig, R.SPECK_MM2)
    m = R.thicken_to_min(m, thicken_mm)
    # close sub-minimum gaps first, then decide what counts as a large solid
    m = cv2.morphologyEx(R.u8(m), cv2.MORPH_CLOSE, R.disk(7)).astype(bool)
    if knock:
        m, _ = R.knock_out_solids(m, protect=protect, orient_from=orig,
                                 min_area_mm2=knock_min_area)
    return R.enforce_laser_rules(m, mat)


@dataclass
class Variant:
    id: str
    label: str
    mask: np.ndarray
    default: bool = False
    notes: str = ""
    source: str = ""
    stats: dict = field(default_factory=dict)


def emit(face_id: str, v: Variant) -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    f = FACES[face_id]
    stem = f"{face_id}__{v.id}"
    svg, png = OUT / f"{stem}.svg", OUT / f"{stem}.png"
    desc = (f"Fax Machine box engraving, part {face_id}, variant {v.id}. Black fills = area "
            f"engrave. Units mm; drawn as the face is seen from outside the box (see "
            f"art_to_local in art/code/manifest.json).")
    mat = material_mask(face_id, R.PPM, 0.42)
    mask = v.mask
    # verify-and-repair: measure the TRACED result per feature at 40 px/mm
    # and patch the bitmap where curve fitting left a thin sliver or a gap
    for it in range(10):
        ds = V.trace(mask)
        V.write_svg(svg, ds, size_mm(face_id), f"{f.title} - {v.label}", desc)
        ink40 = V.rasterize_svg(svg, rules.RULE_PPM)
        thin, gap, nt, ng = rules.violations(ink40)
        if nt == 0 and ng == 0:
            break
        k = int(rules.RULE_PPM / R.PPM)
        H, W = mask.shape
        def down(m40):
            m40 = m40[: H * k, : W * k]
            return m40.reshape(H, k, W, k).any(axis=(1, 3))
        grow = R.disk(5 if it < 3 else 7)
        mask = mask | (cv2.dilate(R.u8(down(gap)), grow).astype(bool) & mat)
        # a thin feature is nearly always a pointed stroke tip: fatten it into
        # a round cap rather than shortening the stroke (which just moves the tip)
        mask = mask | (cv2.dilate(R.u8(down(thin)), R.disk(5)).astype(bool) & mat)
        mask = R.enforce_laser_rules(mask, mat, rounds=1)
    v.mask = mask
    v.stats_rules = {"thin": nt, "gap": ng}
    V.preview_png(svg, png, 1200)
    ink = v.mask.mean()
    v.stats = {"ink_pct": round(100 * float(ink), 1), "paths": len(ds), **v.stats_rules,
               "svg_kb": round(svg.stat().st_size / 1024)}
    return {"id": v.id, "label": v.label, "svg": f"out/{svg.name}", "png": f"out/{png.name}",
            "default": v.default, "notes": v.notes, "source": v.source, **v.stats}
