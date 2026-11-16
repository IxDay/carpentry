#!/usr/bin/env python3
"""Author the open structural frame of the two-storey house in house*.jpg.

The house is a 3 x 2 ken frame (5.46 x 3.64 m) on a 1.82 m grid.  The timbers
are full-length members and the joinery is cut where they meet.  The same face
schema as the joint sources is used, so export.py can write one GLB with a mesh
node per timber and no per-face subdivision.

    python3 tools/author_house.py      # -> house/source.json
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import house_geom as G  # noqa: E402
from author_joint import loft  # noqa: E402

OUT = os.path.join(ROOT, "house")
SRC = os.path.join(OUT, "source.json")

P = G.POST
HALF = P / 2


class House:
    def __init__(self):
        self.members = {}
        self.order = []
        self.posts = {}

    def add(self, pid, name, group, color, kind, *args, **kw):
        if pid in self.members:
            raise SystemExit("duplicate member %s" % pid)
        self.members[pid] = {"pid": pid, "name": name, "group": group,
                             "color": color, "kind": kind, "args": args,
                             "kw": kw, "cuts": [], "adds": [], "extra": []}
        self.order.append(pid)
        return pid

    def cut(self, pid, b):
        self.members[pid]["cuts"].append(b)

    def addbox(self, pid, b):
        self.members[pid]["adds"].append(b)

    def extra(self, pid, faces):
        self.members[pid]["extra"].extend(faces)

    def build(self):
        pieces = []
        for pid in self.order:
            m = self.members[pid]
            if m["kind"] == "axis":
                lo, hi = m["args"]
                p = G.axis_piece(pid, m["name"], m["group"], m["color"],
                                 lo, hi, m["cuts"], m["adds"], m["extra"])
            else:
                p0, p1, w, h = m["args"]
                p = G.oriented_piece(pid, m["name"], m["group"], m["color"],
                                     p0, p1, w, h, m["cuts"], m["adds"],
                                     m["kw"].get("up", (0.0, 1.0, 0.0)),
                                     m["extra"])
            pieces.append(p)
        return pieces


def axis(h, pid, name, group, color, lo, hi):
    return h.add(pid, name, group, color, "axis", lo, hi)


def oriented(h, pid, name, group, color, p0, p1, w, hgt, up=(0, 1, 0),
             cut=()):
    pid = h.add(pid, name, group, color, "oriented", p0, p1, w, hgt,
                up=up)
    for b in cut:
        h.cut(pid, b)
    return pid


# ---------------------------------------------------------------------------
# Foundation, plinth and sills
def foundation(h):
    # thin ground plinth under the whole footprint
    axis(h, "base-plinth", "Plinth", "base", G.COLORS["ground"],
         (-G.W / 2 - 0.45, -0.02, -G.D / 2 - 0.45),
         (G.W / 2 + 0.45, 0.02, G.D / 2 + 0.45))
    fw = 0.18
    # perimeter strip footings
    for z in (-G.D / 2, G.D / 2):
        axis(h, "base-foot-x-%s" % ("f" if z > 0 else "b"), "Strip footing",
             "base", G.COLORS["base"],
             (-G.W / 2 - 0.09, 0.02, z - fw / 2),
             (G.W / 2 + 0.09, G.FOUND_TOP, z + fw / 2))
    for x in (-G.W / 2, G.W / 2):
        axis(h, "base-foot-z-%s" % ("r" if x > 0 else "l"), "Strip footing",
             "base", G.COLORS["base"],
             (x - fw / 2, 0.02, -G.D / 2 + fw / 2),
             (x + fw / 2, G.FOUND_TOP, G.D / 2 - fw / 2))
    # interior pad footings under the floor posts
    for x in G.XS:
        for z in (-G.PURLIN_Z, 0.0, G.PURLIN_Z):
            axis(h, "base-pad-%d-%d" % (G.XS.index(x), int(z * 100)),
                 "Pad footing", "base", G.COLORS["base"],
                 (x - 0.18, 0.02, z - 0.18), (x + 0.18, 0.10, z + 0.18))
            axis(h, "stone-%d-%d" % (G.XS.index(x), int(z * 100)),
                 "Foundation stone", "base", G.COLORS["stone"],
                 (x - 0.12, 0.10, z - 0.12), (x + 0.12, 0.15, z + 0.12))


def sill_member(h, pid, name, group, color, lo, hi, corners):
    """A 土台 member with half-lapped ends; corners = axis ('x' or 'z')."""
    axis(h, pid, name, group, color, lo, hi)
    for sign in (-1, 1):
        if corners == "x":
            c = sign * G.W / 2
            h.cut(pid, G.box((c - 0.06, 0.51, lo[2]), (c + 0.06, hi[1], hi[2])))
        else:
            c = sign * G.D / 2
            h.cut(pid, G.box((lo[0], 0.45, c - 0.06), (hi[0], 0.51, c + 0.06)))


def sills(h):
    for z in (-G.D / 2, G.D / 2):
        tag = "f" if z > 0 else "b"
        sill_member(h, "sill-x-" + tag, "Sill", "axis",
                    G.COLORS["sill"],
                    (-G.W / 2, G.FOUND_TOP, z - 0.06),
                    (G.W / 2, G.SILL_TOP, z + 0.06), "x")
    for x in (-G.W / 2, G.W / 2):
        tag = "r" if x > 0 else "l"
        sill_member(h, "sill-z-" + tag, "Sill", "axis",
                    G.COLORS["sill"],
                    (x - 0.06, G.FOUND_TOP, -G.D / 2),
                    (x + 0.06, G.SILL_TOP, G.D / 2), "z")
    # centre sill, at sleeper level so the joists can pass over it
    axis(h, "sill-x-centre", "Centre sill", "floor", G.COLORS["sleeper"],
         (-G.W / 2, 0.42, -0.06),
         (G.W / 2, 0.51, 0.06))


def posts(h):
    for ix, x in enumerate(G.XS):
        for iz, z in enumerate(G.ZS):
            pid = "post-%d-%d" % (ix, iz)
            h.posts[(ix, iz)] = (x, z)
            # interior posts stop at the second-floor spine beam; the roof is
            # carried by the perimeter and the 小屋梁 bents
            top = G.F1 if iz == 1 else G.WALL_TOP
            axis(h, pid, "Post", "axis", G.COLORS["post"],
                 (x - HALF, G.SILL_TOP, z - HALF),
                 (x + HALF, top, z + HALF))
            # through tenon into the sill, with a peg below it
            h.addbox(pid, G.box((x - 0.03, G.FOUND_TOP - 0.02, z - 0.03),
                                (x + 0.03, G.SILL_TOP, z + 0.03)))
            h.extra(pid, [{"points": [[x - 0.05, G.FOUND_TOP - 0.02, z - 0.012],
                                      [x + 0.05, G.FOUND_TOP - 0.02, z - 0.012],
                                      [x + 0.05, G.FOUND_TOP - 0.02, z + 0.012],
                                      [x - 0.05, G.FOUND_TOP - 0.02, z + 0.012]],
                           "normal": [0, -1, 0], "color": G.COLORS["wedge"]}])
    # perimeter studs, two per bay on the long faces and one per bay on the ends
    for z in (-G.D / 2, G.D / 2):
        tag = "f" if z > 0 else "b"
        for i in range(G.NX):
            x = (G.XS[i] + G.XS[i + 1]) / 2
            pid = "stud-%s-%d" % (tag, i)
            axis(h, pid, "Stud", "axis", G.COLORS["post"],
                 (x - G.STUD / 2, G.SILL_TOP, z - G.STUD / 2),
                 (x + G.STUD / 2, G.F1 - G.GIRD, z + G.STUD / 2))
            axis(h, "stud-%s-%d-up" % (tag, i), "Stud", "axis",
                 G.COLORS["post"],
                 (x - G.STUD / 2, G.F1, z - G.STUD / 2),
                 (x + G.STUD / 2, G.WALL_TOP - G.GIRD, z + G.STUD / 2))
    for x in (-G.W / 2, G.W / 2):
        tag = "r" if x > 0 else "l"
        for i in range(G.NZ):
            z = (G.ZS[i] + G.ZS[i + 1]) / 2
            pid = "stud-%s-%d" % (tag, i)
            axis(h, pid, "Stud", "axis", G.COLORS["post"],
                 (x - G.STUD / 2, G.SILL_TOP, z - G.STUD / 2),
                 (x + G.STUD / 2, G.F1 - G.GIRD, z + G.STUD / 2))
            axis(h, "stud-%s-%d-up" % (tag, i), "Stud", "axis",
                 G.COLORS["post"],
                 (x - G.STUD / 2, G.F1, z - G.STUD / 2),
                 (x + G.STUD / 2, G.WALL_TOP - G.GIRD, z + G.STUD / 2))


# ---------------------------------------------------------------------------
# Small joint helpers
CLR = 0.002


def wedge_faces(lo, hi):
    """A dark wedge/peg box, returned as extra faces for a member."""
    from author_joint import compile_solid
    faces = compile_solid([G.box(lo, hi)], [])
    for f in faces:
        f["color"] = G.COLORS["wedge"]
    return faces


def post_housing(h, ix, iz, axis, d, y, height, width, depth):
    """Cut a housing/mortise in a post from one face.

    axis is the member axis ('x' or 'z'), d = -1/+1 the face it enters from,
    (y, height) the mortise centre and height, width the mortise across the
    member, depth into the post.
    """
    x, z = h.posts[(ix, iz)]
    if axis == "x":
        face = x + d * HALF
        lo, hi = sorted((face, face - d * depth))
        a, b = z - width / 2, z + width / 2
        h.cut("post-%d-%d" % (ix, iz),
              G.box((lo, y - height / 2, a), (hi, y + height / 2, b)))
    else:
        face = z + d * HALF
        lo, hi = sorted((face, face - d * depth))
        a, b = x - width / 2, x + width / 2
        h.cut("post-%d-%d" % (ix, iz),
              G.box((a, y - height / 2, lo), (b, y + height / 2, hi)))


def housed_beam(h, pid, name, axisname, fixed, a, b, y0, y1, width, group,
                color, ix0, iz0, ix1, iz1):
    """A beam between two posts, with housed tenons at both ends."""
    yc = (y0 + y1) / 2
    tenon_h = min(0.10, (y1 - y0) * 0.55)
    tenon_w = min(0.065, width * 0.55)
    if axisname == "x":
        axis(h, pid, name, group, color,
             (a + HALF, y0, fixed - width / 2),
             (b - HALF, y1, fixed + width / 2))
        for px, ix, d in ((a, ix0, 1), (b, ix1, -1)):
            h.addbox(pid, G.box((px + d * (HALF - G.TENON),
                                 yc - tenon_h / 2,
                                 fixed - tenon_w / 2),
                                (px + d * (HALF + 0.001),
                                 yc + tenon_h / 2,
                                 fixed + tenon_w / 2)))
            post_housing(h, ix, iz0, "x", d, yc, tenon_h + 2 * CLR,
                         tenon_w + 2 * CLR, G.TENON)
            # komisen peg through the post, locking the tenon
            h.extra(pid, wedge_faces(
                (px - 0.0125, yc - 0.0125, fixed - HALF - 0.008),
                (px + 0.0125, yc + 0.0125, fixed + HALF + 0.008)))
    else:
        axis(h, pid, name, group, color,
             (fixed - width / 2, y0, a + HALF),
             (fixed + width / 2, y1, b - HALF))
        for pz, iz, d in ((a, iz0, 1), (b, iz1, -1)):
            h.addbox(pid, G.box((fixed - tenon_w / 2,
                                 yc - tenon_h / 2,
                                 pz + d * (HALF - G.TENON)),
                                (fixed + tenon_w / 2,
                                 yc + tenon_h / 2,
                                 pz + d * (HALF + 0.001))))
            post_housing(h, ix0, iz, "z", d, yc, tenon_h + 2 * CLR,
                         tenon_w + 2 * CLR, G.TENON)
            h.extra(pid, wedge_faces(
                (fixed - HALF - 0.008, yc - 0.0125, pz - 0.0125),
                (fixed + HALF + 0.008, yc + 0.0125, pz + 0.0125)))


def beam_ring(h, axisname, fixed, y0, y1, width, group, color, name, index):
    """One beam per bay along a wall/fixed line."""
    coords = G.XS if axisname == "x" else G.ZS
    for k in range(len(coords) - 1):
        a, b = coords[k], coords[k + 1]
        if axisname == "x":
            pid = "beam-x-%d-%d-%d" % (index, round(y0 * 100), k)
            housed_beam(h, pid, name, "x", fixed, a, b, y0, y1, width,
                        group, color, k, index, k + 1, index)
        else:
            pid = "beam-z-%d-%d-%d" % (index, round(y0 * 100), k)
            housed_beam(h, pid, name, "z", fixed, a, b, y0, y1, width,
                        group, color, index, k, index, k + 1)


# ---------------------------------------------------------------------------
# 床組 - ground-floor framing
SLEEPER_Z = (-1.40, -0.91, 0.91, 1.40)


def floor(h):
    # short posts (床束) on stones, under the sleepers
    for x in (-1.82, -0.91, 0.0, 0.91, 1.82):
        for z in SLEEPER_Z:
            tag = "%d-%d" % (round(x * 100), round(z * 100))
            fpid = "floor-post-" + tag
            axis(h, fpid, "Floor post", "floor", G.COLORS["sleeper"],
                 (x - 0.045, 0.15, z - 0.045), (x + 0.045, 0.42, z + 0.045))
            # tenon up into the sleeper
            h.addbox(fpid, G.box((x - 0.03, 0.42, z - 0.03),
                                 (x + 0.03, 0.47, z + 0.03)))
            axis(h, "floor-stone-" + tag, "Floor stone", "base",
                 G.COLORS["stone"],
                 (x - 0.09, 0.02, z - 0.09), (x + 0.09, 0.15, z + 0.09))
    # 大引: sleepers along the long axis, sitting on the floor posts
    for z in SLEEPER_Z:
        tag = "%d" % round(z * 100)
        pid = "sleeper-" + tag
        axis(h, pid, "Sleeper", "floor", G.COLORS["sleeper"],
             (-G.W / 2 + 0.06, 0.42, z - 0.045),
             (G.W / 2 - 0.06, 0.51, z + 0.045))
        for x in (-1.82, -0.91, 0.0, 0.91, 1.82):
            h.cut(pid, G.box((x - 0.031, 0.42, z - 0.031),
                             (x + 0.031, 0.47, z + 0.031)))
        # housed ends in the end sills
        for sx in (-1, 1):
            h.addbox(pid, G.box((sx * (G.W / 2 - 0.06), 0.42, z - 0.045),
                                (sx * (G.W / 2 - 0.03), 0.51, z + 0.045)))
            h.cut("sill-z-" + ("l" if sx < 0 else "r"),
                  G.box((sx * (G.W / 2 - 0.061), 0.42, z - 0.046),
                        (sx * (G.W / 2 - 0.03), 0.51, z + 0.046)))
    # 根太: joists at 455 mm centres, half-lapped over the sleepers
    xs = [-2.5025 + i * 0.455 for i in range(12)]
    for i, x in enumerate(xs):
        pid = "joist-%02d" % i
        axis(h, pid, "Joist", "floor", G.COLORS["joist"],
             (x - 0.03, 0.48, -G.D / 2 + 0.06),
             (x + 0.03, 0.57, G.D / 2 - 0.06))
        for z, sid in [(z, "sleeper-%d" % round(z * 100))
                       for z in SLEEPER_Z] + [(0.0, "sill-x-centre")]:
            # half-lap: 30 mm out of the joist, 30 mm out of the sleeper
            h.cut(pid, G.box((x - 0.031, 0.48, z - 0.046),
                             (x + 0.031, 0.51, z + 0.046)))
            h.cut(sid, G.box((x - 0.032, 0.48, z - 0.05),
                             (x + 0.032, 0.51, z + 0.05)))
        # housed ends in the front and back sills
        for s in (-1, 1):
            zs = s * (G.D / 2 - 0.06)
            h.addbox(pid, G.box((x - 0.03, 0.51, zs),
                                (x + 0.03, 0.56,
                                 s * (G.D / 2 - 0.06 - 0.03))))
            h.cut("sill-x-" + ("f" if s > 0 else "b"),
                  G.box((x - 0.032, 0.51, zs - 0.001),
                        (x + 0.032, 0.56, zs + 0.031 * s)))
    # the centre member is a sleeper, not a full sill, so the joists pass over
    # it at the same level
    h.members["sill-x-centre"]["color"] = G.COLORS["sleeper"]


# ---------------------------------------------------------------------------
# 軸組 - second-floor beams and wall plates
def beams(h):
    # 胴差 at the second-floor line
    for z in (-G.D / 2, G.D / 2):
        beam_ring(h, "x", z, G.F1 - G.GIRD, G.F1, 0.12, "axis",
                  G.COLORS["beam"], "Gird", 0 if z < 0 else 2)
    for x in (-G.W / 2, G.W / 2):
        beam_ring(h, "z", x, G.F1 - G.GIRD, G.F1, 0.12, "axis",
                  G.COLORS["beam"], "Gird", 0 if x < 0 else 3)
    # 床梁 down the middle, carried by the two interior posts
    beam_ring(h, "x", 0.0, G.F1 - G.BEAM, G.F1, 0.12, "floor",
              G.COLORS["floor"], "Floor beam", 1)
    # 軒桁 at the top of the posts, just under the rafters
    for z in (-G.D / 2, G.D / 2):
        beam_ring(h, "x", z, G.BEAM2_TOP, G.WALL_TOP, 0.12, "axis",
                  G.COLORS["beam"], "Plate", 0 if z < 0 else 2)
    for x in (-G.W / 2, G.W / 2):
        beam_ring(h, "z", x, G.BEAM2_TOP, G.WALL_TOP, 0.12, "axis",
                  G.COLORS["beam"], "Plate", 0 if x < 0 else 3)


def nuki(h):
    """包み込み貫: a housed nuki in every bay, at four levels.

    Long-wall and end-wall nuki are at slightly different heights so they miss
    each other inside the corner posts.
    """
    runs = []
    for y0 in (1.50, 2.55, 4.30, 5.35):
        for z in (-G.D / 2, G.D / 2):
            runs.append((y0, "x", z))
        for x in (-G.W / 2, G.W / 2):
            runs.append((y0 + 0.065, "z", x))
    for n, (y0, axisname, fixed) in enumerate(runs):
        coords = G.XS if axisname == "x" else G.ZS
        for k in range(len(coords) - 1):
            a, b = coords[k], coords[k + 1]
            pid = "nuki-%d-%d" % (n, k)
            if axisname == "x":
                axis(h, pid, "Nuki", "axis", G.COLORS["nuki"],
                     (a + HALF - 0.015, y0, fixed - G.NUKI_W / 2),
                     (b - HALF + 0.015, y0 + G.NUKI_H,
                      fixed + G.NUKI_W / 2))
                pz = 0 if fixed < 0 else 2
                for px, ix, d in ((a, k, 1), (b, k + 1, -1)):
                    post_housing(h, ix, pz, "x", d,
                                 y0 + G.NUKI_H / 2, G.NUKI_H + 2 * CLR,
                                 G.NUKI_W + 2 * CLR, 0.015)
                    sign = 1 if fixed > 0 else -1
                    zz = fixed + sign * (G.NUKI_W / 2 - 0.005)
                    h.extra(pid, wedge_faces(
                        (px - 0.035, y0 + 0.005, zz),
                        (px + 0.035, y0 + 0.035, zz + sign * 0.017)))
            else:
                axis(h, pid, "Nuki", "axis", G.COLORS["nuki"],
                     (fixed - G.NUKI_W / 2, y0, a + HALF - 0.015),
                     (fixed + G.NUKI_W / 2, y0 + G.NUKI_H,
                      b - HALF + 0.015))
                px = 0 if fixed < 0 else 3
                for pz, iz, d in ((a, k, 1), (b, k + 1, -1)):
                    post_housing(h, px, iz, "z", d,
                                 y0 + G.NUKI_H / 2, G.NUKI_H + 2 * CLR,
                                 G.NUKI_W + 2 * CLR, 0.015)
                    sign = 1 if fixed > 0 else -1
                    xx = fixed + sign * (G.NUKI_W / 2 - 0.005)
                    h.extra(pid, wedge_faces(
                        (xx, y0 + 0.005, pz - 0.035),
                        (xx + sign * 0.017, y0 + 0.035, pz + 0.035)))


# ---------------------------------------------------------------------------
# 筋違 - braces, and 火打梁 - corner fire beams
def brace_member(h, pid, p0, p1, normal):
    """A brace let into the post and beam faces.  Its ends overlap the posts by
    the thickness of the member, which is the housing; no separate peg."""
    oriented(h, pid, "Brace", "axis", G.COLORS["brace"], p0, p1,
             0.09, 0.105, up=normal)


def braces(h):
    # long walls, ground floor: both outer bays, leaning in towards the centre
    for z in (-G.D / 2, G.D / 2):
        s = 1 if z > 0 else -1
        for k, (a, b) in enumerate(((-2.73, -0.91), (0.91, 2.73))):
            y0, y1 = G.SILL_TOP + 0.12, G.F1 - G.GIRD - 0.12
            if k == 0:
                p0 = (a + 0.12, y0, z + s * 0.02)
                p1 = (b - 0.12, y1, z + s * 0.02)
            else:
                p0 = (b - 0.12, y0, z + s * 0.02)
                p1 = (a + 0.12, y1, z + s * 0.02)
            brace_member(h, "brace-f-%s-%d" % ("f" if s > 0 else "b", k),
                         p0, p1, (0, 0, s))
    # long walls, upper floor
    for z in (-G.D / 2, G.D / 2):
        s = 1 if z > 0 else -1
        for k, (a, b) in enumerate(((-2.73, -0.91), (0.91, 2.73))):
            y0, y1 = G.F1 + 0.12, G.WALL_TOP - G.GIRD - 0.12
            if k == 0:
                p0 = (b - 0.12, y0, z + s * 0.02)
                p1 = (a + 0.12, y1, z + s * 0.02)
            else:
                p0 = (a + 0.12, y0, z + s * 0.02)
                p1 = (b - 0.12, y1, z + s * 0.02)
            brace_member(h, "brace-u-%s-%d" % ("f" if s > 0 else "b", k),
                         p0, p1, (0, 0, s))
    # end walls, one brace per storey
    for x in (-G.W / 2, G.W / 2):
        s = 1 if x > 0 else -1
        for storey, (y0, y1) in enumerate(((G.SILL_TOP + 0.12,
                                            G.F1 - G.GIRD - 0.12),
                                           (G.F1 + 0.12,
                                            G.WALL_TOP - G.GIRD - 0.12))):
            b = 0.0 if storey == 0 else 1.82
            a = -1.82 if storey == 0 else 0.0
            p0 = (x + s * 0.02, y0, a + 0.12)
            p1 = (x + s * 0.02, y1, b - 0.12)
            brace_member(h, "brace-end-%s-%d" % ("r" if s > 0 else "l",
                                                storey), p0, p1, (s, 0, 0))


def fire_beams(h):
    """Diagonal corner ties at sill and second-floor level."""
    for level, (yc, d) in enumerate(((G.SILL_TOP + 0.045, 0.09),
                                     (G.F1 + 0.045, 0.09))):
        for x in (-G.W / 2, G.W / 2):
            for z in (-G.D / 2, G.D / 2):
                sx = 1 if x > 0 else -1
                sz = 1 if z > 0 else -1
                p0 = (x - sx * 0.06, yc, z - sz * 0.58)
                p1 = (x - sx * 0.58, yc, z - sz * 0.06)
                pid = "fire-%d-%s%s" % (level, "r" if sx > 0 else "l",
                                        "f" if sz > 0 else "b")
                oriented(h, pid, "Fire beam", "axis", G.COLORS["beam"],
                         p0, p1, d, d, up=(0, 1, 0))


# ---------------------------------------------------------------------------
# 小屋組 - roof frame
def roof_y(zabs):
    return G.EAVE_EDGE + (G.ROOF_RUN - zabs) * G.ROOF_SLOPE


def roof(h):
    # 小屋梁 across the short direction, mid-bay on the long walls
    for i, x in enumerate((-1.82, 0.0, 1.82)):
        pid = "roofbeam-%d" % i
        axis(h, pid, "Roof beam", "roof", G.COLORS["roof"],
             (x - 0.06, G.BEAM2_TOP, -1.76),
             (x + 0.06, G.BEAM2_TOP + 0.18, 1.76))
        # tenons into the wall plates
        for s, iz in ((-1, 0), (1, 2)):
            h.addbox(pid, G.box((x - 0.03, G.BEAM2_TOP + 0.04, s * 1.76),
                                (x + 0.03, G.BEAM2_TOP + 0.14,
                                 s * 1.82)))
            bay = 0 if x < -0.91 else (1 if x < 0.91 else 2)
            plate = "beam-x-%d-618-%d" % (iz, bay)
            zz = 1.76 if s > 0 else -1.82
            h.cut(plate, G.box((x - 0.032, G.BEAM2_TOP + 0.039, zz),
                               (x + 0.032, G.BEAM2_TOP + 0.141, zz + 0.061)))
    # 小屋束 and 真束
    posts = [(0.0, 0.0, G.RIDGE_TOP - G.RIDGE + 0.04, "king")]
    for x in (-1.82, 0.0, 1.82):
        for z in (-G.PURLIN_Z, G.PURLIN_Z):
            posts.append((x, z, G.PURLIN_TOP - G.PURLIN + 0.04, "strut"))
    for i, (x, z, top, kind) in enumerate(posts):
        pid = "roofpost-%d" % i
        s = 0.06 if kind == "king" else 0.0525
        axis(h, pid, "King post" if kind == "king" else "Roof strut",
             "roof", G.COLORS["roof"],
             (x - s, G.WALL_TOP, z - s), (x + s, top, z + s))
        h.addbox(pid, G.box((x - s, G.WALL_TOP - 0.05, z - s),
                            (x + s, G.WALL_TOP, z + s)))
        # cut the roof beam for the tenon
        rpid = "roofbeam-%d" % (0 if x < -0.91 else (1 if x < 0.91 else 2))
        h.cut(rpid, G.box((x - s, G.WALL_TOP - 0.051, z - s),
                          (x + s, G.WALL_TOP + 0.001, z + s)))
    # 母屋: short purlins between the hips
    for z in (-G.PURLIN_Z, G.PURLIN_Z):
        pid = "purlin-%s" % ("b" if z < 0 else "f")
        axis(h, pid, "Purlin", "roof", G.COLORS["purlin"],
             (-1.82, G.PURLIN_TOP - G.PURLIN, z - 0.06),
             (1.82, G.PURLIN_TOP, z + 0.06))
        for x in (-1.82, 0.0, 1.82):
            h.cut(pid, G.box((x - 0.061, G.PURLIN_TOP - G.PURLIN,
                              z - 0.061),
                             (x + 0.061, G.PURLIN_TOP - G.PURLIN + 0.041,
                              z + 0.061)))
    # 棟木
    axis(h, "ridge", "Ridge", "roof", G.COLORS["roof"],
         (-0.91, G.RIDGE_TOP - G.RIDGE, -G.RIDGE / 2),
         (0.91, G.RIDGE_TOP, G.RIDGE / 2))
    h.cut("ridge", G.box((-0.061, G.RIDGE_TOP - G.RIDGE, -0.061),
                         (0.061, G.RIDGE_TOP - G.RIDGE + 0.041, 0.061)))
    # 隅木: hips from the ridge ends to the eave corners
    for sx in (-1, 1):
        for sz in (-1, 1):
            pid = "hip-%s%s" % ("r" if sx > 0 else "l",
                                "f" if sz > 0 else "b")
            oriented(h, pid, "Hip rafter", "roof", G.COLORS["rafter"],
                     (sx * 0.91, G.RIDGE_TOP - 0.09, 0.0),
                     (sx * 3.33, G.EAVE_EDGE - 0.09, sz * 2.42),
                     0.12, 0.18, up=(0, 1, 0))
    # 垂木: common rafters down the two long slopes, trimmed at the hips
    xs = [-3.185 + i * 0.455 for i in range(15)]
    n = 0
    for x in xs:
        z0 = max(0.0, abs(x) - 0.91)
        if z0 > 2.22:
            continue
        for s in (-1, 1):
            zs = s * 2.42
            p0 = (x, roof_y(z0) - 0.045, s * z0)
            p1 = (x, roof_y(2.42) - 0.045, zs)
            L = math.sqrt((p1[1] - p0[1]) ** 2 + (p1[2] - p0[2]) ** 2)
            cuts = []
            for zc in (0.91, 1.82):
                if zc <= z0 + 0.08 or zc >= 2.34:
                    continue
                u = (zc - z0) / (2.42 - z0) * L
                cuts.append(G.box((u - 0.04, -0.04, -0.045),
                                  (u + 0.04, 0.04, -0.015)))
            oriented(h, "rafter-%d-%s" % (n, "f" if s > 0 else "b"),
                     "Rafter", "roof", G.COLORS["rafter"], p0, p1,
                     0.045, 0.09, cut=cuts)
            n += 1
    # 垂木 on the two hipped ends, from the hip line to the eave
    for z in [-2.275 + i * 0.455 for i in range(11)]:
        x0 = 0.91 + abs(z)
        if x0 > 3.18:
            continue
        for s in (-1, 1):
            y0 = G.EAVE_EDGE + (G.ROOF_RUN + 0.91 - x0) * G.ROOF_SLOPE
            y1 = G.EAVE_EDGE
            p0 = (s * x0, y0 - 0.045, z)
            p1 = (s * 3.33, y1 - 0.045, z)
            L = math.sqrt((p1[0] - p0[0]) ** 2 + (p1[1] - p0[1]) ** 2)
            cuts = []
            if x0 < 2.69:
                u = (2.73 - x0) / (3.33 - x0) * L
                cuts.append(G.box((u - 0.04, -0.04, -0.045),
                                  (u + 0.04, 0.04, -0.015)))
            oriented(h, "rafter-end-%d-%s" % (n, "r" if s > 0 else "l"),
                     "Jack rafter", "roof", G.COLORS["rafter"], p0, p1,
                     0.045, 0.09, cut=cuts)
            n += 1


def stud_cuts(h):
    """The 貫 is housed into the studs as well as the posts: cut a slot through
    each perimeter stud at the four nuki levels, so the nuki is continuous and
    the stud is interrupted rather than passing through it."""
    levels_x = (1.50, 2.55, 4.30, 5.35)
    levels_z = (1.565, 2.615, 4.365, 5.415)
    for pid in list(h.order):
        if not pid.startswith("stud-"):
            continue
        wall = pid.split("-")[1]
        levels = levels_x if wall in ("f", "b") else levels_z
        lo, hi = h.members[pid]["args"]
        for y0 in levels:
            h.cut(pid, G.box((lo[0] - 0.001, y0 - 0.002, lo[2] - 0.001),
                             (hi[0] + 0.001, y0 + G.NUKI_H + 0.002,
                              hi[2] + 0.001)))


def upper_floor(h):
    """Sparse second-floor 根太, half-lapped over the spine beam."""
    for i, x in enumerate((-2.275, -1.365, -0.455, 0.455, 1.365, 2.275)):
        pid = "joist-up-%02d" % i
        axis(h, pid, "Upper joist", "floor", G.COLORS["joist"],
             (x - 0.03, 3.15, -G.D / 2 + 0.06),
             (x + 0.03, G.F1, G.D / 2 - 0.06))
        # half-lap where it crosses the spine beam
        h.cut(pid, G.box((x - 0.031, 3.15, -0.061),
                         (x + 0.031, 3.18, 0.061)))
        bay = 0 if x < -0.91 else (1 if x < 0.91 else 2)
        h.cut("beam-x-1-303-%d" % bay,
              G.box((x - 0.032, 3.15, -0.061),
                    (x + 0.032, 3.181, 0.061)))
        # housed into the front and back girders
        for s, iz in ((-1, 0), (1, 2)):
            zs = s * (G.D / 2 - 0.06)
            h.addbox(pid, G.box((x - 0.03, 3.15, zs),
                                (x + 0.03, 3.24, s * (G.D / 2 - 0.03))))
            h.cut("beam-x-%d-309-%d" % (iz, bay),
                  G.box((x - 0.031, 3.15, zs - 0.001),
                        (x + 0.031, 3.181, zs + 0.031 * s)))


def build():
    h = House()
    foundation(h)
    sills(h)
    posts(h)
    floor(h)
    braces(h)
    fire_beams(h)
    beams(h)
    upper_floor(h)
    nuki(h)
    stud_cuts(h)
    roof(h)
    return h


def write_source(pieces):
    source = {
        "title": "The house",
        "author": "Japanese joinery project",
        "authorUrl": "https://github.com/ixday/carpentry",
        "url": "https://github.com/ixday/carpentry",
        "license": "CC BY 4.0",
        "licenseUrl": "http://creativecommons.org/licenses/by/4.0/",
        "modifications": (
            "authored from the reference drawings house.jpg and house-2.jpg; "
            "open structural frame, no wall or roof finishes; unbuild/rebuild "
            "animation derived at export; sunset lighting baked"),
        "credit": ("Original geometry authored for this collection from the "
                   "reference drawings; CC BY 4.0."),
    }
    level = {
        "id": "house",
        "index": 0,
        "chapter": 0,
        "number": 0,
        "title": "The house",
        "jp": "民家",
        "gloss": "A 3 x 2 ken frame, 5.46 x 3.64 m, two storeys and a hip roof.",
        "guidance": "",
        "forReal": "",
        "fact": "",
        "scale": 1.0,
        "gift": "",
        "mark": "",
        "masterOf": "",
        "source": source,
        "pieces": pieces,
    }
    os.makedirs(OUT, exist_ok=True)
    with open(SRC, "w") as f:
        json.dump([level], f, indent=1)
    tris = sum(len(s.get("faces") or []) for p in pieces for s in p["solids"])
    print("wrote %s: %d members, %d faces" % (SRC, len(pieces), tris))


def main():
    h = build()
    pieces = h.build()
    write_source(pieces)


if __name__ == "__main__":
    main()
