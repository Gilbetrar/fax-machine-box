"""Shared finishing: laser rules, cut keep-out, trace, write, measure."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from . import raster as R
from . import vector as V
from .geometry import FACES, material_mask

OUT = Path(__file__).resolve().parents[1] / "out"


def finish(face_id: str, ink: np.ndarray, protect: np.ndarray | None = None,
           knock: bool = True, keepout_mm: float = R.KEEPOUT_MM,
           thicken_mm: float = 0.35) -> np.ndarray:
    """ink (bool, canvas at R.PPM) -> laser-legal mask clipped to the wood."""
    mat = material_mask(face_id, R.PPM, keepout_mm)
    assert mat.shape == ink.shape, (mat.shape, ink.shape)
    orig = ink & mat
    m = R.remove_small(orig, R.SPECK_MM2)
    m = R.thicken_to_min(m, thicken_mm)
    # close sub-minimum gaps first, then decide what counts as a large solid
    m = cv2.morphologyEx(R.u8(m), cv2.MORPH_CLOSE, R.disk(7)).astype(bool)
    if knock:
        m, _ = R.knock_out_solids(m, protect=protect, orient_from=orig)
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
    ds = V.trace(v.mask)
    V.write_svg(svg, ds, f.size_mm, f"{f.title} - {v.label}",
                f"Fax Machine box engrave art, face {face_id}, variant {v.id}. "
                f"Engrave-only: black fills = area engrave. Physical mm, part-local frame. "
                f"Source: {v.source}")
    V.preview_png(svg, png, 1200)
    ink = v.mask.mean()
    v.stats = {"ink_pct": round(100 * float(ink), 1), "paths": len(ds),
               "svg_kb": round(svg.stat().st_size / 1024)}
    return {"id": v.id, "label": v.label, "svg": f"out/{svg.name}", "png": f"out/{png.name}",
            "default": v.default, "notes": v.notes, "source": v.source, **v.stats}
