#!/usr/bin/env python3
"""Author the joints that have no licensed source model.

The Sketchfab collector only covers the splice families; the column-and-beam
(`shikuchi`) joints on the reference sheet have to be modelled here. Each one is
built as a union of axis-aligned boxes minus a set of box-shaped cuts, which is
enough for square tenons, mortises, housings and pegs. The boundary is extracted
on the exact box grid (no voxels) and coplanar cells are merged back into
rectangles, the same face shape `import_joint.py` produces.

    python3 tools/author_joint.py                 # all authored joints
    python3 tools/author_joint.py daimochi-tsugi  # one by id

Coordinates are metres, in the **closed** pose. For each piece `EXPLODED` gives
the vector it is drawn away from the closed joint by; the source stores the
moved geometry and `assemble = -EXPLODED`. Keys carry an axial clearance plus a
lateral "aside" component, which is what bake.py uses to withdraw them straight
out of their holes before moving them clear.

The geometry is original, not derived from a Sketchfab model: the sources credit
the project and are released CC BY 4.0.
"""
import json
import os
import sys

COLOR = [0.9137254901960784, 0.7607843137254902, 0.5490196078431373]
JP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "joints",
                  "sources")

CREDIT = ("Original geometry authored for this collection from the reference "
          "sheet 柱（軸組）の納まり; CC BY 4.0.")


def compile_solid(add, cut):
    """Boundary of (union of add boxes) minus (union of cut boxes)."""
    boxes = [b for b in add] + [b for b in cut]
    coords = []
    for axis in range(3):
        coords.append(sorted({round(b[axis][i], 9) for b in boxes
                              for i in (0, 1)}))
    n = [len(c) - 1 for c in coords]

    def inside(box, p):
        return all(box[i][0] < p[i] < box[i][1] for i in range(3))

    solid = set()
    for i in range(n[0]):
        for j in range(n[1]):
            for k in range(n[2]):
                c = ((coords[0][i] + coords[0][i + 1]) / 2,
                     (coords[1][j] + coords[1][j + 1]) / 2,
                     (coords[2][k] + coords[2][k + 1]) / 2)
                if any(inside(b, c) for b in add) and \
                        not any(inside(b, c) for b in cut):
                    solid.add((i, j, k))

    # group boundary cells by (axis, plane, direction) and merge rectangles
    groups = {}
    for (i, j, k) in solid:
        cell = (i, j, k)
        for a in range(3):
            for d in (-1, 1):
                nb = list(cell)
                nb[a] += d
                if tuple(nb) in solid:
                    continue
                plane = coords[a][cell[a] + 1] if d > 0 else coords[a][cell[a]]
                u, v = (a + 1) % 3, (a + 2) % 3
                groups.setdefault((a, d, round(plane, 9)), set()).add(
                    (cell[u], cell[v]))

    faces = []
    for (a, d, plane), cells in sorted(groups.items()):
        u, v = (a + 1) % 3, (a + 2) % 3
        cells = set(cells)
        while cells:
            ui, vi = min(cells)
            v1 = vi
            while (ui, v1 + 1) in cells:
                v1 += 1
            u1 = ui
            while all((u1 + 1, vv) in cells for vv in range(vi, v1 + 1)):
                u1 += 1
            for uu in range(ui, u1 + 1):
                for vv in range(vi, v1 + 1):
                    cells.discard((uu, vv))
            u0, u1c = coords[u][ui], coords[u][u1 + 1]
            v0, v1c = coords[v][vi], coords[v][v1 + 1]
            uv = [(u0, v0), (u1c, v0), (u1c, v1c), (u0, v1c)]
            if d < 0:
                uv = [uv[0], uv[3], uv[2], uv[1]]
            pts = []
            for (uu, vv) in uv:
                p = [0.0, 0.0, 0.0]
                p[a] = plane
                p[u] = uu
                p[v] = vv
                pts.append([round(c, 9) for c in p])
            normal = [0.0, 0.0, 0.0]
            normal[a] = float(d)
            faces.append({"points": pts, "normal": normal, "color": COLOR})
    return weld_edges(faces)


def weld_edges(faces):
    """Split each edge at any vertex that lies on it, removing T-junctions.

    The greedy rectangle merge leaves one face's edge running past the corner of
    a neighbouring face; splitting the long edge at that corner makes every edge
    shared by exactly two faces, as the imported meshes are.
    """
    verts = sorted({tuple(round(c, 6) for c in q)
                    for f in faces for q in f["points"]})
    out = []
    for f in faces:
        P = f["points"]
        pts = []
        for a, b in zip(P, P[1:] + P[:1]):
            pts.append(a)
            d = [b[i] - a[i] for i in range(3)]
            L2 = sum(c * c for c in d)
            on = []
            for v in verts:
                t = sum((v[i] - a[i]) * d[i] for i in range(3))
                if t <= 1e-9 or t >= L2 - 1e-9:
                    continue
                if t / L2 > 1.0 - 1e-9:
                    continue
                w = [a[i] + d[i] * t / L2 for i in range(3)]
                if max(abs(w[i] - v[i]) for i in range(3)) < 1e-7:
                    on.append((t, list(v)))
            for _, v in sorted(on):
                pts.append(v)
        out.append({"points": pts, "normal": f["normal"],
                    "color": f["color"]})
    return out


def piece(pid, name, add, cut=()):
    return {"id": pid, "name": name, "kind": "joint",
            "solids": [{"faces": compile_solid(add, cut)}]}


def shift(piece_def, delta):
    out = json.loads(json.dumps(piece_def))
    for s in out["solids"]:
        for f in s["faces"]:
            f["points"] = [[round(q[i] + delta[i], 9) for i in range(3)]
                           for q in f["points"]]
    return out


def joint(jid, title, jp, pieces, exploded, guidance=""):
    moved = [shift(p, exploded.get(p["id"], [0, 0, 0])) for p in pieces]
    return {
        "id": jid, "index": -1, "chapter": 0, "number": 0,
        "title": title, "jp": jp, "gloss": "", "guidance": guidance,
        "forReal": "", "fact": "", "scale": 1.0, "gift": "", "mark": "",
        "masterOf": "",
        "source": {
            "title": title,
            "author": "Japanese joinery project",
            "authorUrl": "https://github.com/ixday/carpentry",
            "url": "https://github.com/ixday/carpentry",
            "license": "CC BY 4.0",
            "licenseUrl": "http://creativecommons.org/licenses/by/4.0/",
            "modifications": "authored from the reference sheet in closed "
                             "pose, exploded for the assemble animation, sunset "
                             "lighting baked; the baking rig's ground slab is "
                             "omitted",
            "credit": CREDIT,
        },
        "assemble": {pid: [round(-c, 9) for c in exploded.get(pid, [0, 0, 0])]
                     for pid in [p["id"] for p in pieces]},
        "pieces": moved,
    }


# ---------------------------------------------------------------------------
# 台持ち継ぎ（真継ぎ）: square butt splice with a housed tenon that bears on the
# mortise floor (the "shelf"), drawn tight by a komisen through the cheeks.
BEAM = 0.12
TENON = 0.06
DAIMOCHI = joint(
    "daimochi-tsugi", "Daimochi-tsugi", "台持ち継ぎ",
    [
        piece("part-a", "Part A",
              [[(-0.45, 0.0), (0.0, BEAM), (0.0, BEAM)],
               [(0.0, 0.05), (0.09, BEAM), (0.0, BEAM)],
               [(0.0, 0.10), (0.03, 0.09), (0.03, 0.09)]],
              [[(0.02, 0.05), (0.045, 0.075), (0.03, 0.09)]]),
        piece("part-b", "Part B",
              [[(0.0, 0.45), (0.0, BEAM), (0.0, BEAM)]],
              [[(0.0, 0.05), (0.09, BEAM), (0.0, BEAM)],
               [(0.0, 0.10), (0.03, 0.09), (0.03, 0.09)],
               [(0.02, 0.05), (0.045, 0.075), (0.0, BEAM)]]),
        piece("key", "Komisen",
              [[(0.02, 0.05), (0.045, 0.075), (-0.02, 0.155)]]),
    ],
    {"part-b": [0.30, 0.0, 0.0], "key": [0.0, 0.14, 0.28]},
    "真継ぎ (square butt) with a 50 mm shelf carrying the upper half, a housed "
    "tenon resting on the mortise floor, and a komisen through the cheeks."
)


# ---------------------------------------------------------------------------
# 雇いホゾ: a loose tenon seats in the post and the beam is slid over it.
YATOI = joint(
    "yatoi-hozo-shikuchi", "Yatoi-hozo-shikuchi", "雇い枘仕口",
    [
        piece("part-a", "Post",
              [[(-0.06, 0.06), (0.0, 0.72), (-0.06, 0.06)]],
              [[(-0.06, 0.0), (0.44, 0.52), (-0.04, 0.04)]]),
        piece("part-b", "Beam",
              [[(-0.56, -0.06), (0.42, 0.54), (-0.06, 0.06)]],
              [[(-0.14, -0.06), (0.44, 0.52), (-0.04, 0.04)]]),
        piece("key", "Loose Tenon",
              [[(-0.14, 0.0), (0.44, 0.52), (-0.04, 0.04)]]),
    ],
    {"part-b": [-0.26, 0.0, 0.0]},
    "The loose tenon stays seated in the post; the beam's blind mortise slides "
    "over it, so the tenon is revealed when the beam is withdrawn."
)


# ---------------------------------------------------------------------------
# 三方差し（T字）: a tenon dropped into an open-topped housing, so the mortise
# is open on three faces (top and both sides). A vertical komisen locks it.
SAMPO = joint(
    "sampo-sashi-shikuchi", "Sampo-sashi-shikuchi", "三方差し仕口",
    [
        piece("part-a", "Post",
              [[(-0.06, 0.06), (0.0, 0.60), (-0.06, 0.06)]],
              [[(-0.04, 0.02), (0.48, 0.60), (-0.06, 0.06)],
               [(-0.03, 0.0), (0.46, 0.48), (-0.03, 0.0)]]),
        piece("part-b", "Beam",
              [[(-0.06, 0.64), (0.60, 0.72), (-0.06, 0.06)],
               [(-0.04, 0.02), (0.48, 0.60), (-0.06, 0.06)]],
              [[(-0.03, 0.0), (0.48, 0.72), (-0.03, 0.0)]]),
        piece("key", "Komisen",
              [[(-0.03, 0.0), (0.46, 0.74), (-0.03, 0.0)]]),
    ],
    {"part-b": [0.0, 0.30, 0.0], "key": [0.0, 0.30, 0.12]},
    "The post's end is housed through its width, so the mortise opens on the "
    "top and both sides (three faces); the beam's tenon drops in and the "
    "komisen is driven down through beam, tenon and post."
)


# ---------------------------------------------------------------------------
# 二方差し（L字）: the mortise is a notch on two adjacent faces of the post,
# with the beam's corner tongue in it. A vertical komisen locks the tongue.
NIHO = joint(
    "niho-sashi-shikuchi", "Niho-sashi-shikuchi", "二方差し仕口",
    [
        piece("part-a", "Post",
              [[(-0.06, 0.06), (0.0, 0.72), (-0.06, 0.06)]],
              [[(-0.06, 0.0), (0.42, 0.54), (0.0, 0.06)],
               [(-0.045, -0.015), (0.38, 0.42), (0.015, 0.045)]]),
        piece("part-b", "Beam",
              [[(-0.56, -0.06), (0.42, 0.54), (-0.06, 0.06)],
               [(-0.06, 0.0), (0.42, 0.54), (0.0, 0.06)]],
              [[(-0.045, -0.015), (0.42, 0.54), (0.015, 0.045)]]),
        piece("key", "Komisen",
              [[(-0.045, -0.015), (0.38, 0.56), (0.015, 0.045)]]),
    ],
    {"part-b": [-0.26, 0.0, 0.0], "key": [0.0, 0.22, 0.0]},
    "The post's corner is notched on two adjacent faces (L-shaped in plan); the "
    "beam's corner tongue fills it and the komisen is driven down into the post."
)

JOINTS = [DAIMOCHI, YATOI, SAMPO, NIHO]


def main(argv):
    want = set(argv[1:])
    for j in JOINTS:
        if want and j["id"] not in want:
            continue
        path = os.path.join(JP, j["id"] + ".json")
        with open(path, "w") as fh:
            json.dump([j], fh, indent=1)
        faces = sum(len(s["faces"]) for p in j["pieces"] for s in p["solids"])
        print("%-24s %d pieces  %d faces  -> %s"
              % (j["id"], len(j["pieces"]), faces, path))


if __name__ == "__main__":
    main(sys.argv)
