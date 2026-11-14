#!/usr/bin/env python3
"""Author the joints that have no licensed source model.

The Sketchfab collector only covers the splice families; the column-and-beam
(`shikuchi`) joints on the reference sheet have to be modelled here. Each one is
built as a union of axis-aligned boxes minus a set of box-shaped cuts, which is
enough for square tenons, mortises, housings and pegs. Box CSG cannot taper, so
driven wedges and pegs are lofted prisms: two parallel sections joined by planar
quads. The box boundary is extracted on the exact grid (no voxels) and coplanar
cells are merged back into rectangles, the same face shape `import_joint.py`
produces.

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
import math
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


def loft(axis, a, b, sec_a, sec_b, color=COLOR):
    """Closed prism between two parallel cross-sections, for tapers.

    `axis` is the extrusion axis; `a`, `b` the two positions along it. Each
    section is a list of `(u, v)` points in the two remaining axes (u = axis+1,
    v = axis+2, both modulo 3), running counter-clockwise seen from +axis, and
    the two sections must have the same number of points. The two caps plus one
    quad per side make a closed, outward-wound shell.
    """
    u, v = (axis + 1) % 3, (axis + 2) % 3

    def pt(pos, s):
        p = [0.0, 0.0, 0.0]
        p[axis], p[u], p[v] = pos, s[0], s[1]
        return p

    A = [pt(a, s) for s in sec_a]
    B = [pt(b, s) for s in sec_b]
    n = len(sec_a)

    def normal(pts):
        nx = ny = nz = 0.0
        for i in range(len(pts)):
            p, q = pts[i], pts[(i + 1) % len(pts)]
            nx += (p[1] - q[1]) * (p[2] + q[2])
            ny += (p[2] - q[2]) * (p[0] + q[0])
            nz += (p[0] - q[0]) * (p[1] + q[1])
        L = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        return [nx / L, ny / L, nz / L]

    faces = []
    for pts in (A[::-1], B):
        faces.append({"points": [list(p) for p in pts],
                      "normal": normal(pts), "color": color})
    for i in range(n):
        j = (i + 1) % n
        pts = [A[i], A[j], B[j], B[i]]
        faces.append({"points": [list(p) for p in pts],
                      "normal": normal(pts), "color": color})
    return faces


def piece(pid, name, add, cut=(), extra=()):
    faces = compile_solid(add, cut) + list(extra)
    return {"id": pid, "name": name, "kind": "joint",
            "solids": [{"faces": weld_edges(faces)}]}


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


# ---------------------------------------------------------------------------
# 小根ホゾ: the tenon is cut in two tiers. The full-section 大根 (large root) sits
# at the beam's shoulder; past the vertical step (腰) the narrower 小根 (small
# root) runs on into the post. In the 下 (lower) variants the nose is flush with
# the tenon's underside, in the 上 (upper) variants with its top.
KONE_END = -0.06            # post's near face = beam's shoulder
KONE_WAIST = -0.02          # 腰, where the big root ends
KONE_Y0, KONE_Y1 = 0.44, 0.52
KONE_TIER = 0.04
KONE_BIG_Z = 0.04
KONE_NOSE_Z = 0.032
BODY_Y0, BODY_Y1 = 0.42, 0.54
POST_BOX = [(-0.06, 0.06), (0.0, 0.72), (-0.06, 0.06)]


def big_root():
    return [(KONE_END, KONE_WAIST), (KONE_Y0, KONE_Y1),
            (-KONE_BIG_Z, KONE_BIG_Z)]


def nose(x1, y0, y1, z=KONE_NOSE_Z):
    return [(KONE_WAIST, x1), (y0, y1), (-z, z)]


def beam(add, cut=(), extra=()):
    body = [(-0.40, KONE_END), (BODY_Y0, BODY_Y1), (-0.06, 0.06)]
    return piece("part-b", "Beam", [body] + add, cut, extra)


def split_wedge(x0, x1, yc, z0, z1):
    """One of two tapered wedges in a horizontal kerf, thin end inboard."""
    def sec(h):
        return [(yc - h, z0), (yc + h, z0), (yc + h, z1), (yc - h, z1)]
    return loft(0, x0, x1, sec(0.0020), sec(0.0039))


def kerf(yc):
    return [(0.03, 0.09), (yc - 0.004, yc + 0.004),
            (-KONE_NOSE_Z, KONE_NOSE_Z)]


# 下小根ホゾ（襷掛付）: blind, and the small root is forked into two prongs that
# straddle a vertical 襷 bridge left standing in the post.
TASUKI = joint(
    "shitakone-hozo-tasuki-gake", "Shitakone-hozo-tasuki-gake",
    "下小根ホゾ（襷掛付）",
    [
        piece("part-a", "Post", [POST_BOX],
              [[(KONE_END, KONE_WAIST), (KONE_Y0, KONE_Y1),
                (-KONE_BIG_Z, KONE_BIG_Z)],
               [(KONE_WAIST, 0.03), (KONE_Y0, KONE_Y0 + KONE_TIER),
                (-KONE_NOSE_Z, -0.008)],
               [(KONE_WAIST, 0.03), (KONE_Y0, KONE_Y0 + KONE_TIER),
                (0.008, KONE_NOSE_Z)]]),
        beam([big_root(),
              [(KONE_WAIST, 0.03), (KONE_Y0, KONE_Y0 + KONE_TIER),
               (-KONE_NOSE_Z, -0.008)],
              [(KONE_WAIST, 0.03), (KONE_Y0, KONE_Y0 + KONE_TIER),
               (0.008, KONE_NOSE_Z)]]),
    ],
    {"part-a": [0.30, 0.0, 0.0]},
    "The tenon is blind, so nothing shows on the post's far face. Its small "
    "root is forked into two prongs and the post keeps a vertical 襷 bridge "
    "between the two mortise pockets, so the joint resists sideways pull as "
    "well as withdrawal."
)

# 下小根ホゾ割り楔打ち: through, the small root protruding 30 mm, split by a
# horizontal kerf and spread by two wedges driven in from the far face.
SHITA_WARI = joint(
    "shitakone-hozo-wari-kusabi", "Shitakone-hozo-wari-kusabi",
    "下小根ホゾ割り楔打ち",
    [
        piece("part-a", "Post", [POST_BOX],
              [[(KONE_END, KONE_WAIST), (KONE_Y0, KONE_Y1),
                (-KONE_BIG_Z, KONE_BIG_Z)],
               [(KONE_WAIST, 0.06), (KONE_Y0, KONE_Y0 + KONE_TIER),
                (-KONE_NOSE_Z, KONE_NOSE_Z)]]),
        beam([big_root(), nose(0.09, KONE_Y0, KONE_Y0 + KONE_TIER)],
             [kerf(0.461)]),
        piece("wedge-l", "Wedge", [], extra=split_wedge(0.035, 0.09, 0.461,
                                                        -0.030, -0.002)),
        piece("wedge-r", "Wedge", [], extra=split_wedge(0.035, 0.09, 0.461,
                                                        0.002, 0.030)),
    ],
    {"part-a": [0.30, 0.0, 0.0],
     "wedge-l": [0.10, 0.0, -0.055], "wedge-r": [0.10, 0.0, 0.055]},
    "The lower small root passes through the post and stands 30 mm proud. Two "
    "wedges driven into its horizontal kerf from the far face lift the upper "
    "half against the 腰, so the tenon cannot work loose."
)

# 下小根ホゾ鼻栓打ち: through, the protruding nose locked by a tapered vertical
# peg driven down through it just behind the post.
HANA_SEN = joint(
    "shitakone-hozo-hana-sen", "Shitakone-hozo-hana-sen", "下小根ホゾ鼻栓打ち",
    [
        piece("part-a", "Post", [POST_BOX],
              [[(KONE_END, KONE_WAIST), (KONE_Y0, KONE_Y1),
                (-KONE_BIG_Z, KONE_BIG_Z)],
               [(KONE_WAIST, 0.06), (KONE_Y0, KONE_Y0 + KONE_TIER),
                (-KONE_NOSE_Z, KONE_NOSE_Z)]]),
        beam([big_root(), nose(0.09, KONE_Y0, KONE_Y0 + KONE_TIER)],
             [[(0.061, 0.074), (KONE_Y0, KONE_Y0 + KONE_TIER),
               (-0.0065, 0.0065)]]),
        piece("peg", "Nose Peg", [],
              extra=loft(1, 0.425, 0.515,
                         [(-0.0055, 0.0620), (0.0055, 0.0620),
                          (0.0055, 0.0730), (-0.0055, 0.0730)],
                         [(-0.0060, 0.0615), (0.0060, 0.0615),
                          (0.0060, 0.0735), (-0.0060, 0.0735)])),
    ],
    {"part-a": [0.30, 0.0, 0.0], "peg": [0.0, 0.14, 0.0]},
    "The lower small root protrudes through the post and a tapered 鼻栓 is "
    "driven down through its nose, hard against the post's far face, so the "
    "tenon is blocked from withdrawing."
)

# 上小根ホゾ割り楔打ち: the same wedged through joint with the small tier on top.
UWA_WARI = joint(
    "uwakone-hozo-wari-kusabi", "Uwakone-hozo-wari-kusabi",
    "上小根ホゾ割り楔打ち",
    [
        piece("part-a", "Post", [POST_BOX],
              [[(KONE_END, KONE_WAIST), (KONE_Y0, KONE_Y1),
                (-KONE_BIG_Z, KONE_BIG_Z)],
               [(KONE_WAIST, 0.06), (KONE_Y0 + KONE_TIER, KONE_Y1),
                (-KONE_NOSE_Z, KONE_NOSE_Z)]]),
        beam([big_root(), nose(0.09, KONE_Y0 + KONE_TIER, KONE_Y1)],
             [kerf(0.500)]),
        piece("wedge-l", "Wedge", [], extra=split_wedge(0.035, 0.09, 0.500,
                                                        -0.030, -0.002)),
        piece("wedge-r", "Wedge", [], extra=split_wedge(0.035, 0.09, 0.500,
                                                        0.002, 0.030)),
    ],
    {"part-a": [0.30, 0.0, 0.0],
     "wedge-l": [0.10, 0.0, -0.055], "wedge-r": [0.10, 0.0, 0.055]},
    "The upper small root passes through the post, so the 腰 sits low and the "
    "full-section big root bears in the shallow housing below it. The kerf is "
    "spread by two wedges driven in from the far face."
)

# 上小根ホゾ打ち抜き込み栓打ち: through, locked by a horizontal komisen driven
# right through the post's cheeks and the big root, cut flush on both faces.
UWA_KOMISEN = joint(
    "uwakone-hozo-uchi-nuki-komisen", "Uwakone-hozo-uchi-nuki-komisen",
    "上小根ホゾ打ち抜き込み栓打ち",
    [
        piece("part-a", "Post", [POST_BOX],
              [[(KONE_END, KONE_WAIST), (KONE_Y0, KONE_Y1),
                (-KONE_BIG_Z, KONE_BIG_Z)],
               [(KONE_WAIST, 0.06), (KONE_Y0 + KONE_TIER, KONE_Y1),
                (-KONE_NOSE_Z, KONE_NOSE_Z)],
               [(-0.05, -0.03), (0.45, 0.47), (-0.06, 0.06)]]),
        beam([big_root(), nose(0.09, KONE_Y0 + KONE_TIER, KONE_Y1)],
             [[(-0.05, -0.03), (0.45, 0.47), (-KONE_BIG_Z, KONE_BIG_Z)]]),
        piece("key", "Komisen", [],
              extra=loft(2, -0.0599, 0.0599,
                         [(-0.0499, 0.4501), (-0.0301, 0.4501),
                          (-0.0301, 0.4699), (-0.0499, 0.4699)],
                         [(-0.0490, 0.4510), (-0.0310, 0.4510),
                          (-0.0310, 0.4690), (-0.0490, 0.4690)])),
    ],
    {"part-a": [0.30, 0.0, 0.0], "key": [0.0, 0.0, 0.20]},
    "The upper small root passes through the post and carries the 腰; a square "
    "込み栓 is driven horizontally through the post's cheeks and the big root "
    "and cut off flush with both faces, so the joint cannot be pulled apart."
)


# ---------------------------------------------------------------------------
# 長ホゾ差し込み栓打ち: an untiered long tenon runs right through the post and
# stands proud; a tapered komisen pierces both post and tenon from the side.
NAGA = joint(
    "naga-hozo-sashi-komisen-uchi", "Naga-hozo-sashi-komisen-uchi",
    "長ホゾ差し込み栓打ち",
    [
        piece("part-a", "Post", [POST_BOX],
              [[(-0.06, 0.06), (0.42, 0.50), (-0.045, 0.045)],
               [(-0.010, 0.010), (0.450, 0.470), (-0.06, 0.06)]]),
        piece("part-b", "Beam",
              [[(-0.40, -0.06), (0.40, 0.52), (-0.06, 0.06)],
               [(-0.06, 0.105), (0.42, 0.50), (-0.045, 0.045)]],
              [[(-0.010, 0.010), (0.450, 0.470), (-0.045, 0.045)]]),
        piece("key", "Komisen", [],
              extra=loft(2, -0.0599, 0.0599,
                         [(-0.0099, 0.4501), (0.0099, 0.4501),
                          (0.0099, 0.4699), (-0.0099, 0.4699)],
                         [(-0.0095, 0.4505), (0.0095, 0.4505),
                          (0.0095, 0.4695), (-0.0095, 0.4695)])),
    ],
    {"part-a": [0.25, 0.0, 0.0], "key": [0.0, 0.0, 0.16]},
    "The long tenon passes clean through the post and stands 45 mm proud, so "
    "the joint reads as a true through-tenon. A tapered 込み栓 is driven "
    "sideways through post and tenon and cut off flush with both cheeks."
)


# ---------------------------------------------------------------------------
# 片鎌ホゾ差し: a post foot with a one-sided hook (鎌) on its tenon. The sill's
# mortise is open at its end, so the post slides in along the sill; the hook
# travels under the sill's lip and then cannot be lifted out, which is what the
# single-sided kama is for.
KAMA_SILL_Y0, KAMA_SILL_Y1 = 0.0, 0.12
KAMA_SLOT_END = 0.16          # open end of the sill's slot
KAMA_SLOT_X0 = -0.031         # blind end, 1 mm clear of the tenon
KAMA_FLOOR = 0.039            # 1 mm below the tenon's underside
KAMA_TENON_Z = 0.030
KAMA_HOOK_Z = 0.050
KAMA_HOOK_Y = 0.056
KATA_KAMA = joint(
    "kata-kama-hozo-sashi", "Kata-kama-hozo-sashi", "片鎌ホゾ差し",
    [
        piece("part-a", "Sill",
              [[(-0.45, KAMA_SLOT_END), (KAMA_SILL_Y0, KAMA_SILL_Y1),
                (-0.06, 0.06)]],
              [[(KAMA_SLOT_X0, KAMA_SLOT_END), (KAMA_FLOOR, KAMA_SILL_Y1),
                (-0.031, 0.031)],
               [(KAMA_SLOT_X0, KAMA_SLOT_END), (KAMA_FLOOR, 0.057),
                (KAMA_TENON_Z, 0.057)]]),
        piece("part-b", "Post",
              [[(-0.06, 0.06), (KAMA_SILL_Y1, 0.80), (-0.06, 0.06)],
               [(-0.03, 0.03), (KAMA_FLOOR + 0.001, KAMA_SILL_Y1),
                (-KAMA_TENON_Z, KAMA_TENON_Z)],
               [(-0.03, 0.03), (KAMA_FLOOR + 0.001, KAMA_HOOK_Y),
                (KAMA_TENON_Z, KAMA_HOOK_Z)]]),
    ],
    {"part-b": [0.26, 0.14, 0.0]},
    "The tenon carries a 鎌 hook along one lower edge only. The sill's mortise "
    "is a slot open at the sill's end, so the post is slid in along the sill: "
    "the hook runs under the sill's lip and the post can no longer be lifted "
    "out, while the square face of the hook bears on the lip under uplift. The "
    "post's shoulder seats on the sill and its tenon clears the mortise floor."
)


# ---------------------------------------------------------------------------
# 下げ鎌（大入れ）: the end of a 貫 is cut with a 鎌 hook on its underside and
# dropped into the post's mortise. The mortise is one hook deeper than the nuki,
# so the nuki goes in raised and level; when it is lowered the hook falls behind
# the post's far face and bears on it, and a wedge over the nose locks it down.

SAGE_Y0 = 0.50              # mortise floor = nuki underside
SAGE_BODY = 0.045           # nuki thickness
SAGE_HOOK = 0.015           # 引っ掛かり, depth of the kama below the nuki
SAGE_GAP = 0.015            # wedge space above the nuki
SAGE_Y1 = SAGE_Y0 + SAGE_BODY
SAGE_CEIL = SAGE_Y1 + SAGE_GAP
SAGE_Z = 0.045              # half the nuki's width; 15 mm cheeks remain
SAGE_NOSE = 0.13            # nuki end, 70 mm past the post's far face
SAGE_WEDGE = [(-0.04, SAGE_Y1), (0.11, SAGE_Y1),
              (0.11, SAGE_CEIL - 0.0075), (0.05, SAGE_CEIL),
              (-0.04, SAGE_CEIL)]
SAGE_KAMA = joint(
    "sage-kama-oire", "Sage-kama-oire", "下げ鎌（大入れ）",
    [
        piece("part-a", "Post",
              [[(-0.06, 0.06), (0.0, 0.72), (-0.06, 0.06)]],
              [[(-0.06, 0.06), (SAGE_Y0, SAGE_CEIL), (-SAGE_Z, SAGE_Z)]]),
        piece("part-b", "Nuki",
              [[(-0.26, SAGE_NOSE), (SAGE_Y0, SAGE_Y1),
                (-SAGE_Z, SAGE_Z)],
               [(0.06, SAGE_NOSE), (SAGE_Y0 - SAGE_HOOK, SAGE_Y0),
                (-SAGE_Z, SAGE_Z)]]),
        piece("wedge", "Wedge", [],
              extra=loft(2, -SAGE_Z, SAGE_Z, SAGE_WEDGE, SAGE_WEDGE)),
    ],
    {"part-b": [-0.24, 0.26, 0.0], "wedge": [0.16, 0.18, 0.0]},
    "The nuki's end is cut with a 鎌 hook on its underside. The mortise is one "
    "hook deeper than the nuki, so the nuki is offered up raised, run home and "
    "then dropped: the hook falls behind the post's far face and bears on it, "
    "so the nuki cannot be pulled back out. A wedge driven in over the nose "
    "seats the nuki on the mortise floor and keeps the hook tight. The nuki is "
    "housed at its full section with no shoulder — 大入れ — and the mortise "
    "runs right through the post, leaving a narrow cheek either side."
)


def mirror_x(j):
    """Mirror a joint through the x=0 plane.

    The site's camera sits at `38deg 64deg`, i.e. off +x/+z, so a beam run in
    from -x would show its back to the viewer and hide the mortise mouth. The
    tenon family is modelled with the beam on -x for readable coordinates and
    flipped here, which also keeps every face outward-wound.
    """
    out = json.loads(json.dumps(j))
    for p in out["pieces"]:
        for s in p["solids"]:
            for f in s["faces"]:
                f["points"] = [[round(-q[0], 9), q[1], q[2]]
                               for q in f["points"]][::-1]
                f["normal"] = [-f["normal"][0], f["normal"][1], f["normal"][2]]
    out["assemble"] = {pid: [round(-v[0], 9), v[1], v[2]]
                       for pid, v in out["assemble"].items()}
    return out


JOINTS += [mirror_x(j) for j in (TASUKI, SHITA_WARI, HANA_SEN,
                                 UWA_WARI, UWA_KOMISEN)]
JOINTS += [NAGA, KATA_KAMA, SAGE_KAMA]


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
