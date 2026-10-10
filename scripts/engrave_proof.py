"""Proof renders for the cut + engrave files: a part as it lies on the laser
bed (outside face up, from the written cut+engrave sheet) next to the same part
as it looks on the finished box, built independently from the 3D model.

    python scripts/engrave_proof.py OUT_DIR [--thickness 3.2]

For each part it takes the bed art (bed -> part-local through the physical
turn-over rotation -> faxbox.assembly3d plate transform -> box coordinates) and
draws it in an orthographic view from outside the box:

    top, lid            from above, front of the box at the bottom
    faceplates          from the front
    drawer left sides   from the left

Writes proof_lid_top.png, proof_faceplates.png, proof_drawer_left.png (flat
sheet crop on the left, 3D exterior view on the right).
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--thickness", default="3.2")
    a = ap.parse_args()
    os.environ["FAXBOX_THICKNESS"] = a.thickness
    sys.path.insert(0, str(ROOT / "src"))

    import cairosvg
    import numpy as np
    from PIL import Image
    import io
    from shapely.affinity import affine_transform

    from faxbox import assembly3d as a3
    from faxbox import cutset as cs
    from faxbox import engrave as eg

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    T = cs.T
    with tempfile.TemporaryDirectory() as td:
        items = {it.face: it for it in cs.generate_items(Path(td)) if it.face}
    plates = a3.all_plates()

    def chain(face):
        """bed SVG (x, y) at the art surface -> box (X, Y, Z)."""
        it, P = items[face], plates[face]
        kind = eg.flip_kind(face)
        mat, _ = cs.cut_geometry(cs.bed_subpaths(it)[0])
        bed = affine_transform(mat.buffer(-cs.BURN, quad_segs=32), [1, 0, 0, -1, 0, 0])
        bx0, by0, bx1, by1 = bed.bounds
        lx0, ly0, lx1, ly1 = P.part.solid.bounds
        if kind is None:
            R, o = np.eye(3), (bx0 - lx0, by0 - ly0)
            t = np.array([-o[0], -o[1], 0.0])
        elif kind == "v":
            R = np.diag([-1.0, 1.0, -1.0])
            t = np.array([bx1 + lx0, -(by0 - ly0), T])
        else:
            R = np.diag([1.0, -1.0, -1.0])
            t = np.array([-(bx0 - lx0), by1 + ly0, T])
        M = np.asarray(P.matrix())

        def f(x, y):
            local = R @ np.array([x, -y, T]) + t        # bed top face
            return (M @ np.array([*local, 1.0]))[:3]
        return f

    def view_xy(kind, p):
        X, Y, Z = p
        return {"top": (Y, -X), "front": (Y, -Z), "left": (-X, -Z)}[kind]

    def draw(face, view, scale=4.0):
        """SVG group (strings) of the exterior view of one part."""
        it, P = items[face], plates[face]
        f = chain(face)
        cuts, engrave = cs.bed_subpaths(it, eg.default_variant(face))
        paths = []
        for kind, subs in engrave:
            if kind != "fill":
                continue
            d = []
            for pts, closed in eg.flatten(subs, 0.02):
                q = [view_xy(view, f(x, y)) for x, y in pts]
                d.append("M" + " ".join(f"{u * scale:.2f},{v * scale:.2f}" for u, v in q) + "Z")
            paths.append('<path fill-rule="evenodd" fill="#000" d="' + "".join(d) + '"/>')
        # outline: zero-kerf plate in box coordinates
        outline = []
        g = P.geom
        ring = list(g.exterior.coords) if g.geom_type == "Polygon" else []
        pts = []
        for x, y in ring:
            b = np.zeros(3)
            b[P.ia], b[P.ib], b[P.ic] = x, y, P.rc[1]
            pts.append(view_xy(view, b))
        outline = "M" + " ".join(f"{u * scale:.2f},{v * scale:.2f}" for u, v in pts) + "Z"
        base = f'<path fill="#e9dcc3" stroke="#0000ff" stroke-width="0.6" d="{outline}"/>'
        return base + "".join(paths), pts

    def png(svg, w):
        return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=svg.encode(), output_width=w, background_color="white")))

    def flat(face, width):
        it = items[face]
        sheet = [(it, 10.0, 10.0, False)]
        with tempfile.TemporaryDirectory() as td:
            svg, dxf = Path(td) / "p.svg", Path(td) / "p.dxf"
            cs.write_engrave_sheet(sheet, "face", 1, 1, svg, dxf, it.name, {face: eg.default_variant(face)})
            txt = svg.read_text().replace('stroke-width="0.0762"', 'stroke-width="0.3"')
        return png(txt, width)

    def panel(groups, title, flats, fname, view):
        # 3D exterior view
        allpts = [p for g, pts in groups for p in pts]
        us, vs = [p[0] for p in allpts], [p[1] for p in allpts]
        scale = 4.0
        x0, y0 = min(us) * scale - 20, min(vs) * scale - 20
        w, h = (max(us) - min(us)) * scale + 40, (max(vs) - min(vs)) * scale + 40
        svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.0f}" height="{h:.0f}" viewBox="{x0:.1f} {y0:.1f} {w:.1f} {h:.1f}">'
               + "".join(g for g, _ in groups) + "</svg>")
        right = png(svg, 900)
        left = [flat(f, 900) for f in flats]
        H = sum(im.height for im in left)
        W = 900 + 900 + 30
        canvas = Image.new("RGB", (W, max(H, right.height) + 50), "white")
        y = 50
        for im in left:
            canvas.paste(im, (0, y))
            y += im.height
        canvas.paste(right, (930, 50))
        from PIL import ImageDraw
        d = ImageDraw.Draw(canvas)
        d.text((10, 10), "On the laser bed: written cut + engrave file, outside face up", fill="black")
        d.text((940, 10), title, fill="black")
        canvas.save(out / fname)

    lid_top = [draw("top", "top"), draw("lid", "top")]
    panel(lid_top, "Finished box seen from above (front at the bottom): top panel + lid", ["lid", "top"], "proof_lid_top.png", "top")
    fp = [draw("B_face", "front"), draw("T_face", "front")]
    panel(fp, "Finished box seen from the front: drawer faceplates", ["B_face", "T_face"], "proof_faceplates.png", "front")
    dl = [draw("B_left", "left"), draw("T_left", "left")]
    panel(dl, "Finished box seen from the left: drawer left sides", ["B_left", "T_left"], "proof_drawer_left.png", "left")
    print("wrote", sorted(p.name for p in out.glob("proof_*.png")))


if __name__ == "__main__":
    main()
