"""Part geometry for the code-drawn engraving art.

Every face is drawn in its PART-LOCAL SVG frame: the same x/y axes the
generator uses for that piece in output/*.svg (no flip, no rotation), with
the art canvas = the DESIGN.md nominal blank, centred on the drawn piece
bbox (the same convention scripts/art_proofs.py uses). So an art SVG can be
dropped onto its piece by a pure translation:

    art origin (0,0) == (piece_bbox_centre - nominal/2) in the piece SVG.

Orientation facts this relies on (see scripts/art_proofs.py PROOFS.md):
- walls are drawn exterior-face-up; Right Wall front = local x 0 (left),
  Left Wall front = local x max (right; the generator mirrors it);
- Top Panel: local x 0 = front (divider side, plain edge), y = box Y;
- Sliding Lid: portrait, local x 0..79 = depth from the FRONT, y = width;
  its 158.75 mm art field is centred in the 163.6 mm blank (the 2.4 mm side
  strips ride hidden in the wall slots);
- drawer sides: local y max = finger-jointed bottom edge;
- faceplate: grip slot near local y min (top).
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
import svgpathtools

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "tests"))
sys.path.insert(0, str(REPO / "src"))

from svg_utils import design_pieces, find_piece_by_label, normalize_color  # noqa: E402

OUTPUT_SVG_DIR = REPO / "output"


@dataclass(frozen=True)
class Face:
    face_id: str          # matches scripts/art_proofs.py PartSpec.key
    svg_file: str
    label: str            # generator piece label
    size_mm: tuple[float, float]
    title: str


FACES: dict[str, Face] = {f.face_id: f for f in [
    Face("left_wall", "outer_shell.svg", "Left Wall", (298.45, 127.0), "Left wall (parrot, FAX MACHINE)"),
    Face("right_wall", "outer_shell.svg", "Right Wall", (298.45, 127.0), "Right wall (Terrible Writers & Artists)"),
    Face("front_wall", "outer_shell.svg", "Front Wall", (158.75, 118.025), "Front wall (fax machine panel)"),
    Face("top_panel", "outer_shell.svg", "Top Panel", (222.25, 158.75), "Top panel (fixed, behind the lid)"),
    Face("sliding_lid", "lids.svg", "Sliding Lid", (79.0, 163.6), "Sliding lid"),
    Face("faceplate_colors", "drawer.svg", "Faceplate", (150.9, 53.5), "Drawer faceplate: COLORS"),
    Face("faceplate_lines", "drawer.svg", "Faceplate", (150.9, 53.5), "Drawer faceplate: Lines"),
    Face("drawer_side_1", "drawer.svg", "Left Side", (212.25, 50.325), "Drawer side 1 (turkeys)"),
    Face("drawer_side_2", "drawer.svg", "Right Side", (212.25, 50.325), "Drawer side 2 (alligator and seagull)"),
    Face("drawer_side_3", "drawer.svg", "Left Side", (212.25, 50.325), "Drawer side 3 (gallery)"),
    Face("drawer_side_4", "drawer.svg", "Right Side", (212.25, 50.325), "Drawer side 4 (bookshelf)"),
]}


def regenerate_svgs() -> None:
    from faxbox.generate_drawers import generate_drawer
    from faxbox.generate_lids import generate_lids
    from faxbox.shell_generator import generate_shell

    generate_shell()
    generate_drawer()
    generate_lids()


def _poly(d: str, step_mm: float = 0.05) -> np.ndarray:
    path = svgpathtools.parse_path(d)
    pts = []
    for seg in path:
        n = max(2, int(seg.length() / step_mm) + 1)
        for i in range(n):
            p = seg.point(i / (n - 1))
            pts.append((p.real, p.imag))
    return np.array(pts, dtype=np.float64)


@lru_cache(maxsize=None)
def piece_for(face_id: str):
    f = FACES[face_id]
    pieces = design_pieces(OUTPUT_SVG_DIR / f.svg_file)
    piece = find_piece_by_label(pieces, f.label)
    if piece is None:
        raise RuntimeError(f"piece {f.label!r} not in {f.svg_file}")
    return piece


def art_origin(face_id: str) -> tuple[float, float]:
    """Piece-SVG coordinate of the art canvas's (0,0)."""
    f = FACES[face_id]
    bb = piece_for(face_id).bbox
    cx, cy = (bb.xmin + bb.xmax) / 2, (bb.ymin + bb.ymax) / 2
    return cx - f.size_mm[0] / 2, cy - f.size_mm[1] / 2


def cut_polylines(face_id: str) -> list[tuple[str, np.ndarray]]:
    """[(kind, Nx2 points in ART mm)] for the outline ('outer') and every
    blue cut hole ('hole'). Red engraves (legacy labels) are ignored."""
    piece = piece_for(face_id)
    ox, oy = art_origin(face_id)
    out = [("outer", _poly(piece.outer.d) - (ox, oy))]
    for h in piece.holes:
        if normalize_color(h.stroke) == "blue":
            out.append(("hole", _poly(h.d) - (ox, oy)))
    return out


def material_mask(face_id: str, ppm: float, keepout_mm: float = 0.0) -> np.ndarray:
    """bool HxW over the art canvas: True where wood remains after cutting,
    shrunk by `keepout_mm` from every cut edge (outline notches + holes)."""
    f = FACES[face_id]
    W, H = int(round(f.size_mm[0] * ppm)), int(round(f.size_mm[1] * ppm))
    m = np.zeros((H, W), np.uint8)
    SH = 4  # cv2 fixed-point sub-pixel bits

    def pts(a):
        return np.round((a * ppm - 0.5) * (1 << SH)).astype(np.int32).reshape(-1, 1, 2)

    polys = cut_polylines(face_id)
    cv2.fillPoly(m, [pts(polys[0][1])], 1, lineType=cv2.LINE_8, shift=SH)
    for kind, p in polys[1:]:
        cv2.fillPoly(m, [pts(p)], 0, lineType=cv2.LINE_8, shift=SH)
    if keepout_mm > 0:
        r = max(1, int(round(keepout_mm * ppm)))
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
        # erode with a border of 0 so the canvas edge also counts as a cut edge
        m = cv2.erode(m, k, borderType=cv2.BORDER_CONSTANT, borderValue=0)
    return m.astype(bool)
