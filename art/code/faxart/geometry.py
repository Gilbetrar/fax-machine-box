"""Part geometry for the code-drawn engraving art (geometry v2).

Authoritative part data: `faxbox.partgeom` (zero-kerf outlines in each
part's local frame: origin at the bottom-left of the NOMINAL rectangle, x
right, y up, finger tabs sticking out) and `faxbox.assembly3d` (transforms
into box coordinates, which face is the exterior). Face ids are the part ids
of site/data/parts.json.

ART FRAME. Every art SVG is drawn as the face is SEEN FROM OUTSIDE the
finished box: canvas = the part's nominal rectangle, u to the right, v down,
in mm. How that maps onto the part-local frame (x, y):

    exterior '+' (local z+ faces out):        x = u,      y = H - v
    exterior '-', vertical part:              x = W - u,  y = H - v
    exterior '-', horizontal (lid, top):      x = u,      y = v

('-' means the outline as drawn in the cut file shows the INTERIOR face. For
vertical parts the mirror is taken across the vertical axis so the art stays
upright; for the lid and top panel it is taken across the front-rear axis so
the front stays the front.) For a '-' part the cut file has to be engraved
with the part turned over, i.e. with its outline mirrored the same way, so
the art lands on the outside face. `art_to_local` in the manifest is this
mapping as a 2x3 affine; `art_up` / `art_right` are the box directions of
-v / +u.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "src"))

from faxbox import assembly3d as A  # noqa: E402
from faxbox import partgeom as PG  # noqa: E402


@dataclass(frozen=True)
class Face:
    face_id: str      # = part id in site/data/parts.json
    title: str


FACES: dict[str, Face] = {f.face_id: f for f in [
    Face("left", "Left wall (parrot, FAX MACHINE)"),
    Face("right", "Right wall (Terrible Writers & Artists)"),
    Face("front", "Front wall (fax machine panel)"),
    Face("top", "Top panel (fixed, behind the lid)"),
    Face("lid", "Sliding lid"),
    Face("B_face", "Lower drawer faceplate: COLORS"),
    Face("T_face", "Upper drawer faceplate: Lines"),
    Face("B_left", "Lower drawer, left side (turkeys)"),
    Face("B_right", "Lower drawer, right side (alligator and seagull)"),
    Face("T_left", "Upper drawer, left side (gallery)"),
    Face("T_right", "Upper drawer, right side (bookshelf)"),
]}


def regenerate_svgs() -> None:
    """Kept for callers that also want output/*.svg fresh (proofs)."""
    from faxbox.generate_drawers import generate_drawer
    from faxbox.generate_lids import generate_lids
    from faxbox.shell_generator import generate_shell

    generate_shell()
    generate_drawer()
    generate_lids()


@lru_cache(maxsize=None)
def part(face_id: str):
    return PG.load_part(A.source_part(face_id))


@lru_cache(maxsize=None)
def plate(face_id: str):
    return A.all_plates()[face_id]


def size_mm(face_id: str) -> tuple[float, float]:
    g = part(face_id)
    return (round(g.width, 3), round(g.height, 3))


@lru_cache(maxsize=None)
def frame(face_id: str) -> dict:
    """exterior sign, art->local affine, art up/right in box coords."""
    P = plate(face_id)
    sign = P.outward_sign(A._view_reference(face_id))
    R = np.asarray(P.matrix())[:3, :3]
    W, H = size_mm(face_id)
    horizontal = abs(R[:, 2][2]) > 0.9            # thickness axis along box Z
    if sign > 0:
        M = [[1, 0, 0], [0, -1, H]]
    elif not horizontal:
        M = [[-1, 0, W], [0, -1, H]]
    else:
        M = [[1, 0, 0], [0, 1, 0]]
    M = np.array(M, float)
    right = R[:, :2] @ M[:, 0]                    # box direction of +u
    up = -(R[:, :2] @ M[:, 1])                    # box direction of -v
    return {"exterior_face": "+" if sign > 0 else "-", "horizontal": bool(horizontal),
            "art_to_local": M.tolist(),
            "art_right": [round(float(v), 6) + 0.0 for v in right],
            "art_up": [round(float(v), 6) + 0.0 for v in up]}


def local_to_art(face_id: str, pts: np.ndarray) -> np.ndarray:
    M = np.array(frame(face_id)["art_to_local"])
    # M is its own inverse for these three mappings (pure flips + offsets)
    return pts @ M[:, :2].T + M[:, 2]


def cut_polylines(face_id: str) -> list[tuple[str, np.ndarray]]:
    """[(kind, Nx2 art-mm points)]: the outline and every through-cut hole."""
    g = part(face_id)
    out = [("outer", local_to_art(face_id, np.asarray(g.outer.exterior.coords)))]
    for h in g.holes:
        out.append(("hole", local_to_art(face_id, np.asarray(h.exterior.coords))))
    return out


def material_mask(face_id: str, ppm: float, keepout_mm: float = 0.0) -> np.ndarray:
    """bool HxW over the art canvas: True where wood remains after cutting,
    shrunk by `keepout_mm` from every cut edge (outline, notches, holes)."""
    W, H = size_mm(face_id)
    Wp, Hp = int(round(W * ppm)), int(round(H * ppm))
    m = np.zeros((Hp, Wp), np.uint8)
    SH = 4

    def pts(a):
        return np.round((a * ppm - 0.5) * (1 << SH)).astype(np.int32).reshape(-1, 1, 2)

    polys = cut_polylines(face_id)
    cv2.fillPoly(m, [pts(polys[0][1])], 1, lineType=cv2.LINE_8, shift=SH)
    for _, p in polys[1:]:
        cv2.fillPoly(m, [pts(p)], 0, lineType=cv2.LINE_8, shift=SH)
    if keepout_mm > 0:
        r = max(1, int(round(keepout_mm * ppm)))
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
        m = cv2.erode(m, k, borderType=cv2.BORDER_CONSTANT, borderValue=0)
    return m.astype(bool)
