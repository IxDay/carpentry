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
OFFSHEET_CREDIT = ("Original geometry authored for this collection from the "
                   "published descriptions of the joint; CC BY 4.0.")


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
    # Keep the exact coordinates of each vertex, not the rounded lookup key:
    # inserting a rounded key would move a real corner by up to 5e-7 and leave
    # a near-duplicate point in the face.
    verts = {}
    for f in faces:
        for q in f["points"]:
            verts.setdefault(tuple(round(c, 6) for c in q), list(q))
    keys = sorted(verts)
    out = []
    for f in faces:
        P = f["points"]
        pts = []
        for a, b in zip(P, P[1:] + P[:1]):
            pts.append(a)
            d = [b[i] - a[i] for i in range(3)]
            L2 = sum(c * c for c in d)
            L = math.sqrt(L2)
            on = []
            for k in keys:
                v = verts[k]
                t = sum((v[i] - a[i]) * d[i] for i in range(3))
                if t <= 0.0 or t >= L2:
                    continue
                # A vertex within a micron of an endpoint is that endpoint,
                # not an interior point on the edge.
                along = t / L
                if along < 1e-6 or L - along < 1e-6:
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


def joint(jid, title, jp, pieces, exploded, guidance="", tab=None,
          approach=None, credit=None, modifications=None):
    moved = [shift(p, exploded.get(p["id"], [0, 0, 0])) for p in pieces]
    out = {
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
            "modifications": modifications if modifications is not None else
                             "authored from the reference sheet in closed "
                             "pose, exploded for the assemble animation, sunset "
                             "lighting baked; the baking rig's ground slab is "
                             "omitted",
            "credit": credit or CREDIT,
        },
        "assemble": {pid: [round(-c, 9) for c in exploded.get(pid, [0, 0, 0])]
                     for pid in [p["id"] for p in pieces]},
        "pieces": moved,
    }
    # Joints that neither reference sheet shows sit in the site's second tab.
    if tab:
        out["tab"] = tab
    # Extra poses the assemble animation passes through on its way in, as
    # offsets from the closed pose (see bake.assemble_animation).
    if approach:
        out["approach"] = approach
    return out


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


# ---------------------------------------------------------------------------
# 四方差し: four beams meet one post at a single level. Two through-tenons at the
# same height would occupy the same core of the post, so each beam's 竿 is cut at
# its own level within the beam's depth: the two x beams stack in the lower half,
# the two z beams in the upper half. Each tenon runs through the post and 30 mm
# into the opposite beam's end, so the four beams tie one another, and a tapered
# plate komisen dropped through each pair from the post's top face pins the lot.
SQ_POST_TOP = 0.60
SQ_BEAM_W = 0.045           # half the beam's width, 90 wide
SQ_TENON_W = 0.03           # half the tenon's width, 60 wide
SQ_NOSE = 0.09              # tenon end, 30 mm inside the opposite beam
SQ_KEY_T = 0.015            # half the key's thickness, 30 deep


def sq_key(axis, tip, head, s0, s1):
    """Tapered plate komisen, full-size at `head` and eased 1.5 mm at `tip`.

    Sections are `(u, v)` rectangles in the two axes other than `axis`
    (`u = axis + 1`, `v = axis + 2`, both modulo 3), as `loft()` takes them.
    The key is driven tip-first, so the leading section is the smaller one and
    it wedges as it seats.
    """
    (u0, v0), (u1, v1) = s0, s1
    big = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    small = [(u0 + 0.0015, v0 + 0.0015), (u1 - 0.0015, v0 + 0.0015),
             (u1 - 0.0015, v1 - 0.0015), (u0 + 0.0015, v1 - 0.0015)]
    return loft(axis, tip, head, small, big)


SQ_SHIHOU = joint(
    "shihou-sashi-shikuchi", "Shihou-sashi-shikuchi", "四方差し",
    [
        piece("part-a", "Post",
              [[(-0.06, 0.06), (0.30, SQ_POST_TOP), (-0.06, 0.06)]],
              [[(-0.06, 0.06), (0.40, 0.44), (-SQ_TENON_W, SQ_TENON_W)],
               [(-0.06, 0.06), (0.44, 0.48), (-SQ_TENON_W, SQ_TENON_W)],
               [(-SQ_TENON_W, SQ_TENON_W), (0.48, 0.52), (-0.06, 0.06)],
               [(-SQ_TENON_W, SQ_TENON_W), (0.52, 0.56), (-0.06, 0.06)],
               [(0.030, 0.054), (0.379, 0.612), (-SQ_KEY_T, SQ_KEY_T)],
               [(-SQ_KEY_T, SQ_KEY_T), (0.459, 0.612), (0.030, 0.054)]]),
        piece("part-b", "Beam -x",
              [[(-0.40, -0.06), (0.40, 0.56), (-SQ_BEAM_W, SQ_BEAM_W)],
               [(-0.06, SQ_NOSE), (0.40, 0.44), (-SQ_TENON_W, SQ_TENON_W)]],
              [[(-SQ_NOSE, -0.06), (0.44, 0.48), (-SQ_TENON_W, SQ_TENON_W)],
               [(0.030, 0.054), (0.40, 0.44), (-SQ_KEY_T, SQ_KEY_T)]]),
        piece("part-c", "Beam +x",
              [[(0.06, 0.40), (0.40, 0.56), (-SQ_BEAM_W, SQ_BEAM_W)],
               [(-SQ_NOSE, 0.06), (0.44, 0.48), (-SQ_TENON_W, SQ_TENON_W)]],
              [[(0.06, SQ_NOSE), (0.40, 0.44), (-SQ_TENON_W, SQ_TENON_W)],
               [(0.030, 0.054), (0.44, 0.48), (-SQ_KEY_T, SQ_KEY_T)]]),
        piece("part-d", "Beam -z",
              [[(-SQ_BEAM_W, SQ_BEAM_W), (0.40, 0.56), (-0.40, -0.06)],
               [(-SQ_TENON_W, SQ_TENON_W), (0.48, 0.52), (-0.06, SQ_NOSE)]],
              [[(-SQ_TENON_W, SQ_TENON_W), (0.52, 0.56), (-SQ_NOSE, -0.06)],
               [(-SQ_KEY_T, SQ_KEY_T), (0.48, 0.52), (0.030, 0.054)]]),
        piece("part-e", "Beam +z",
              [[(-SQ_BEAM_W, SQ_BEAM_W), (0.40, 0.56), (0.06, 0.40)],
               [(-SQ_TENON_W, SQ_TENON_W), (0.52, 0.56), (-SQ_NOSE, 0.06)]],
              [[(-SQ_TENON_W, SQ_TENON_W), (0.48, 0.52), (0.06, SQ_NOSE)],
               [(-SQ_KEY_T, SQ_KEY_T), (0.52, 0.56), (0.030, 0.054)]]),
        piece("key-x", "Komisen", [], extra=sq_key(
            1, 0.392, 0.612, (-SQ_KEY_T, 0.030), (SQ_KEY_T, 0.054))),
        piece("key-z", "Komisen", [], extra=sq_key(
            1, 0.472, 0.612, (0.030, -SQ_KEY_T), (0.054, SQ_KEY_T))),
    ],
    {"part-b": [-0.32, 0.0, 0.0], "part-c": [0.32, 0.0, 0.0],
     "part-d": [0.0, 0.0, -0.32], "part-e": [0.0, 0.0, 0.32],
     "key-x": [0.0, 0.30, 0.0], "key-z": [0.0, 0.30, 0.0]},
    "Four 床梁 frame into one post at a single level. Two through-tenons cannot "
    "share a core, so each beam's 竿 is cut at its own level within the beam's "
    "depth: the two x beams stack in the lower half, the two z beams in the "
    "upper half. Each tenon passes clean through the post and 30 mm into the "
    "end of the beam opposite, so the four beams tie one another, and a plate "
    "komisen dropped through each pair of tenons from the post's top face, "
    "standing a little proud, pins the lot."
)


# ---------------------------------------------------------------------------
# 傾ぎ大入れ: a horizontal member housed full-section into the post's face, but
# with the seam cut at a slope instead of square. The beam's end runs deeper at
# the bottom, in under the post's overhanging cheek, so the post carries the
# whole load in bearing on the slope and the beam cannot lift out. The beam is
# withdrawn straight along its own axis; no key is needed.
KATAGI_TOP, KATAGI_BOT = 0.44, 0.32
KATAGI_FACE = -0.06         # the post's -x face, where the seam is cut
KATAGI_DEEP = -0.02         # how far the heel runs into the post

# Cross-sections in the x-y plane, extruded along z: the rebate is cut straight
# across the post's width, and the beam's slanted end spans its full width.
# Both are counter-clockwise; the post's starts at a vertex the bake's fan can
# see the whole of (the rebate would trap a fan started elsewhere).
KATAGI_POST = [(0.06, 0.0), (0.06, 0.72), (-0.06, 0.72),
               (-0.06, KATAGI_TOP), (KATAGI_DEEP, KATAGI_BOT),
               (-0.06, KATAGI_BOT), (-0.06, 0.0)]
KATAGI_BEAM = [(-0.64, KATAGI_BOT), (KATAGI_DEEP, KATAGI_BOT),
               (KATAGI_FACE, KATAGI_TOP), (-0.64, KATAGI_TOP)]

KATAGI = joint(
    "katagi-ooire", "Katagi-ooire", "傾ぎ大入れ",
    [
        piece("part-a", "Post", [], extra=loft(
            2, -0.06, 0.06, KATAGI_POST, KATAGI_POST)),
        piece("part-b", "Beam", [], extra=loft(
            2, -0.06, 0.06, KATAGI_BEAM, KATAGI_BEAM)),
    ],
    {"part-b": [-0.30, 0.0, 0.0]},
    "A full-section housing with the seam cut at a slope rather than square: "
    "the beam's end runs 40 mm deeper at the bottom, under the post's "
    "overhanging cheek, so the load bears on the slope and the beam cannot be "
    "lifted out."
)


# ---------------------------------------------------------------------------
# 追掛け大栓継ぎ（持ち出し継ぎ）: a long half-lap splice in which each timber's
# tenon is carried out past the other's shoulder, so its nose stands 20 mm
# proud of the finished surface and seats in a shallow recess. Two 大栓 are
# driven down through the lap, each passing through both tenons.
OK_BEAM = 0.06              # half the timber's section
OK_END = 0.36               # the far end of each timber
OK_LAP = 0.14               # half the overlap
OK_NOSE = 0.04              # how far the nose runs past the shoulder
OK_PROUD = 0.02             # how far it stands proud of the surface
OK_PEG_X = 0.025            # half the 大栓's width, 50 wide
OK_PEG_C = 0.06             # centre of each 大栓 from the lap's centre
OK_PEG_D = 0.02             # half its thickness along the member
OK_PEG_TOP = 0.075          # its head, 15 mm proud of the top face

OKKAKE_MOCHI = joint(
    "okkake-daisen-tsugi-mochidashi",
    "Okkake-daisen-tsugi (mochidashi)", "追掛け大栓継ぎ（持ち出し継ぎ）",
    [
        # A runs from -z, its tenon is the upper half of the lap and its nose
        # comes out on top of B. The bottom recess at its own lap end is the
        # seat for B's nose.
        piece("part-a", "Part A",
              [[(-OK_BEAM, OK_BEAM), (-OK_BEAM, OK_BEAM), (-OK_END, -OK_LAP)],
               [(-OK_BEAM, OK_BEAM), (0.0, OK_BEAM), (-OK_LAP, OK_LAP)],
               [(-OK_BEAM, OK_BEAM), (OK_PROUD, OK_BEAM + OK_PROUD),
                (OK_LAP, OK_LAP + OK_NOSE)]],
              [[(-OK_BEAM, OK_BEAM), (-OK_BEAM - 0.01, -OK_PROUD),
                (-OK_LAP - OK_NOSE, -OK_LAP)],
               [(-OK_PEG_X, OK_PEG_X), (-OK_BEAM - 0.01, OK_BEAM + 0.02),
                (-OK_PEG_C - OK_PEG_D, -OK_PEG_C + OK_PEG_D)],
               [(-OK_PEG_X, OK_PEG_X), (-OK_BEAM - 0.01, OK_BEAM + 0.02),
                (OK_PEG_C - OK_PEG_D, OK_PEG_C + OK_PEG_D)]]),
        # B is the same timber turned half round about x: lower tenon, nose
        # underneath A.
        piece("part-b", "Part B",
              [[(-OK_BEAM, OK_BEAM), (-OK_BEAM, OK_BEAM), (OK_LAP, OK_END)],
               [(-OK_BEAM, OK_BEAM), (-OK_BEAM, 0.0), (-OK_LAP, OK_LAP)],
               [(-OK_BEAM, OK_BEAM), (-OK_BEAM - OK_PROUD, -OK_PROUD),
                (-OK_LAP - OK_NOSE, -OK_LAP)]],
              [[(-OK_BEAM, OK_BEAM), (OK_PROUD, OK_BEAM + 0.01),
                (OK_LAP, OK_LAP + OK_NOSE)],
               [(-OK_PEG_X, OK_PEG_X), (-OK_BEAM - 0.02, OK_BEAM + 0.01),
                (-OK_PEG_C - OK_PEG_D, -OK_PEG_C + OK_PEG_D)],
               [(-OK_PEG_X, OK_PEG_X), (-OK_BEAM - 0.02, OK_BEAM + 0.01),
                (OK_PEG_C - OK_PEG_D, OK_PEG_C + OK_PEG_D)]]),
        piece("osen-a", "Osen", [[(-OK_PEG_X, OK_PEG_X),
                                 (-OK_BEAM, OK_PEG_TOP),
                                 (-OK_PEG_C - OK_PEG_D, -OK_PEG_C + OK_PEG_D)]]),
        piece("osen-b", "Osen", [[(-OK_PEG_X, OK_PEG_X),
                                 (-OK_BEAM, OK_PEG_TOP),
                                 (OK_PEG_C - OK_PEG_D, OK_PEG_C + OK_PEG_D)]]),
    ],
    {"part-b": [0.0, 0.0, 0.26], "osen-a": [0.0, 0.20, 0.0],
     "osen-b": [0.0, 0.20, 0.0]},
    "A long half-lap splice in which each tenon runs past the other timber's "
    "shoulder: its nose is carried out 20 mm proud of the surface into a "
    "shallow rebate, and two 大栓 driven down through the lap pin the two "
    "halves together."
)


# ---------------------------------------------------------------------------
# 胴付き蟻継ぎ: a dovetail splice cut in plan, the tenon running the full height
# of the section. The dovetail's mouth is 60 mm and its nose 100 mm, so the two
# timbers cannot pull apart along their length; the shoulders left either side
# of the mouth carry compression. The socket is open at B's top and bottom, so
# B is lowered over the standing tenon.

ARI_BEAM = 0.06             # half the 120 mm section
ARI_END = 0.36              # each timber's length
ARI_ROOT = 0.03             # half the tenon's width at the seam, 60 mm
ARI_NOSE = 0.05             # half its width at the nose, 100 mm
ARI_LEN = 0.14              # tenon length, from the seam

# Sections are (z, x) for an extrusion along y: positive shoelace area, the
# winding loft() expects.
ARI_A = [(-ARI_BEAM, -ARI_END), (ARI_BEAM, -ARI_END), (ARI_BEAM, 0.0),
         (ARI_ROOT, 0.0), (ARI_NOSE, ARI_LEN), (-ARI_NOSE, ARI_LEN),
         (-ARI_ROOT, 0.0), (-ARI_BEAM, 0.0)]
ARI_B = [(ARI_BEAM, 0.0), (ARI_BEAM, ARI_END), (-ARI_BEAM, ARI_END),
         (-ARI_BEAM, 0.0), (-ARI_ROOT, 0.0), (-ARI_NOSE, ARI_LEN),
         (ARI_NOSE, ARI_LEN), (ARI_ROOT, 0.0)]

DOUTSUKI_ARI = joint(
    "doutsuki-ari-tsugi", "Doutsuki-ari-tsugi", "胴付き蟻継ぎ",
    [
        piece("part-a", "Part A", [],
              extra=loft(1, -ARI_BEAM, ARI_BEAM, ARI_A, ARI_A)),
        piece("part-b", "Part B", [],
              extra=loft(1, -ARI_BEAM, ARI_BEAM, ARI_B, ARI_B)),
    ],
    {"part-b": [0.22, 0.24, 0.0]},
    "A dovetail cut in plan rather than in elevation: the tenon is 60 mm wide "
    "at the shoulders and 100 mm at the nose, so once B is lowered over it the "
    "two timbers cannot be pulled apart along their length. The socket runs "
    "the full 120 mm depth, which is what lets B drop straight down onto the "
    "tenon while the shoulders at the seam meet.",
    tab="extra",
    approach={"part-b": [[0.0, 0.24, 0.0]]},
    credit=OFFSHEET_CREDIT,
    modifications="authored from published descriptions of the joint in "
                  "closed pose, exploded for the assemble animation, sunset "
                  "lighting baked; the baking rig's ground slab is omitted",
)


# ---------------------------------------------------------------------------
# 包み込み貫: the nuki runs into a mortise that stops 90 mm into the 120 mm
# post, and the last 15 mm of its end is rebated 15 mm up from its underside.
# The post keeps a shelf under that rebate and a 30 mm wall beyond the end, so
# the end is wrapped: the nuki is offered up 15 mm high, run home over the
# shelf, then lowered onto it. A wedge driven into the 15 mm gap above the
# nuki's top face at the mouth holds it down.
TS_POST = 0.06              # half the 120 mm post
TS_TOP = 0.72               # post height
TS_T = 0.015                # half the nuki's 30 mm thickness
TS_Y0, TS_Y1 = 0.50, 0.62   # the nuki's height
TS_SLOT_TOP = TS_Y1 + 0.015  # 15 mm of clearance above it for the wedge
TS_END = 0.03               # insertion depth 90 mm from the near face at -0.06
TS_STEP = 0.015             # the rebate is 15 mm deep and 15 mm high
TS_NUKI_END = -0.42         # the free end of the nuki

# Seen along the member, the end's underside steps up 15 mm for its last
# 15 mm: the body bears on the mortise floor, the end on the shelf.
TS_NUKI = [(TS_NUKI_END, TS_Y0), (TS_END - TS_STEP, TS_Y0),
           (TS_END - TS_STEP, TS_Y0 + TS_STEP), (TS_END, TS_Y0 + TS_STEP),
           (TS_END, TS_Y1), (TS_NUKI_END, TS_Y1)]

TSUTSUMIKOMI = joint(
    "tsutsumikomi-nuki", "Tsutsumikomi-nuki", "包み込み貫",
    [
        # The post is cut by two overlapping mortises: the first runs the full
        # height of the slot from the mouth to the rebate's inner edge, the
        # second only from the shelf up, leaving the shelf under the end.
        piece("part-a", "Post",
              [[(-TS_POST, TS_POST), (0.0, TS_TOP), (-TS_POST, TS_POST)]],
              [[(-TS_POST, TS_END - TS_STEP), (TS_Y0, TS_SLOT_TOP),
                (-TS_T, TS_T)],
               [(-TS_POST, TS_END), (TS_Y0 + TS_STEP, TS_SLOT_TOP),
                (-TS_T, TS_T)]]),
        piece("part-b", "Nuki", [],
              extra=loft(2, -TS_T, TS_T, TS_NUKI, TS_NUKI)),
        # The wedge's top bears on the slot's ceiling; only its thick outer
        # end reaches down to the nuki's back.
        piece("wedge", "Kusabi", [],
              extra=loft(0, -0.12, -0.02,
                         [(TS_Y1, -TS_T), (TS_Y1, TS_T),
                          (TS_SLOT_TOP, TS_T), (TS_SLOT_TOP, -TS_T)],
                         [(TS_Y1 + 0.014, -TS_T), (TS_Y1 + 0.014, TS_T),
                          (TS_SLOT_TOP, TS_T), (TS_SLOT_TOP, -TS_T)])),
    ],
    {"part-b": [-0.36, 0.18, 0.0], "wedge": [-0.16, 0.0, 0.0]},
    "The nuki's end is wrapped by the post. It runs 90 mm into the 120 mm post "
    "and its last 15 mm is rebated 15 mm up from the underside; the post keeps "
    "a shelf under that rebate and a 30 mm wall beyond the end. Offer the nuki "
    "up 15 mm, run it home over the shelf, then lower it onto the shelf so the "
    "end is caught, and drive the wedge into the gap above its back.",
    tab="extra",
    approach={"part-b": [[-0.36, 0.015, 0.0], [0.0, 0.015, 0.0]]},
    credit=OFFSHEET_CREDIT,
    modifications="authored from published descriptions of the joint in "
                  "closed pose, exploded for the assemble animation, sunset "
                  "lighting baked; the baking rig's ground slab is omitted",
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
    if out.get("approach"):
        flipped = {}
        for pid, spec in out["approach"].items():
            if spec and isinstance(spec[0], (list, tuple)):
                flipped[pid] = [[round(-v[0], 9), v[1], v[2]] for v in spec]
            else:
                flipped[pid] = [round(-spec[0], 9), spec[1], spec[2]]
        out["approach"] = flipped
    return out


JOINTS += [mirror_x(j) for j in (TASUKI, SHITA_WARI, HANA_SEN,
                                 UWA_WARI, UWA_KOMISEN)]
JOINTS += [NAGA, KATA_KAMA, SAGE_KAMA, SQ_SHIHOU, KATAGI,
           OKKAKE_MOCHI, DOUTSUKI_ARI, mirror_x(TSUTSUMIKOMI)]


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
