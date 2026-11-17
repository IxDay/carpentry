#!/usr/bin/env python3
"""Build the connection metadata for the interactive house viewer.

The house GLB is one mesh per timber; the joinery is cut into those timbers, so
a joint is not a mesh of its own.  This tool records every connection as an
explicit instance: the member IDs it joins, a point at the joint, and the
member the marker should follow while the construction clip is running.

Nothing here is guessed from bounding boxes.  The instances follow the same
loops as ``author_house.py`` and are asserted against the members it actually
authored, so a renamed or removed timber fails the build instead of producing a
marker in mid-air.

    python3 tools/house_links.py      # -> house/connections.json
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import author_house as A  # noqa: E402
import house_geom as G  # noqa: E402
from house_anim import bbox  # noqa: E402

OUT = os.path.join(ROOT, "house", "connections.json")
JOINT_SRC = os.path.join(ROOT, "joints", "sources")

W, D = G.W, G.D
WH, DH = W / 2, D / 2


# ---------------------------------------------------------------------------
# Every connection family the frame actually models.  `catalog` names a joint
# specimen in the 34-joint catalog; `match` is "exact" when the house joint is
# the same detail, "related" when the catalog shows the same family in another
# configuration.  The reader links house-only details to the joint schedule.
KINDS = {
    "sill-corner": {
        "title": "Sill corner",
        "description": ("The two 土台 sill members are halved across each "
                        "other, alternating which wall keeps the top half."),
    },
    "post-sill": {
        "title": "Post on sill",
        "description": ("A through tenon on the post passes down through the "
                        "sill and is wedged below it."),
        "catalog": "shitakone-hozo-wari-kusabi",
        "match": "related",
    },
    "post-beam": {
        "title": "Beam into post",
        "description": ("A housed tenon at the end of the beam is pinned "
                        "through the post with a komisen peg."),
        "catalog": "naga-hozo-sashi-komisen-uchi",
        "match": "related",
    },
    "nuki-post": {
        "title": "貫 into post",
        "description": ("The 包み込み貫 is housed into the post and wedged on "
                        "the outer face; the post keeps a shelf under the "
                        "nuki's rebated end."),
        "catalog": "tsutsumikomi-nuki",
        "match": "exact",
    },
    "nuki-stud": {
        "title": "貫 through stud",
        "description": ("The nuki passes through a slot in the stud, "
                        "interrupting the stud rather than the nuki."),
        "catalog": "tsutsumikomi-nuki",
        "match": "related",
    },
    "brace": {
        "title": "Brace into post",
        "description": ("The 筋違 brace is let into the post face; its own "
                        "thickness forms the housing and no peg is used."),
    },
    "fire-beam": {
        "title": "火打梁 tie",
        "description": ("A diagonal 火打梁 ties the two sill or girder members "
                        "across the corner, resting on both."),
    },
    "joist-sleeper": {
        "title": "Joist half-lap",
        "description": ("The 根太 joist and the 大引 sleeper are halved 30 mm "
                        "each where they cross."),
    },
    "joist-sill": {
        "title": "Joist into sill",
        "description": "The joist end is housed 30 mm into the sill.",
    },
    "floorpost-sleeper": {
        "title": "床束 into sleeper",
        "description": "The short 床束 floor post tenons up into the 大引 sleeper.",
    },
    "floorpost-stone": {
        "title": "床束 on stone",
        "description": "The 床束 floor post bears on its foundation stone.",
    },
    "sleeper-sill": {
        "title": "Sleeper into sill",
        "description": "The 大引 sleeper end is housed into the end sill.",
    },
    "upperjoist-beam": {
        "title": "Upper joist half-lap",
        "description": "The upper 根太 is halved over the spine beam.",
    },
    "upperjoist-girder": {
        "title": "Upper joist into girder",
        "description": "The upper joist end is housed into the 胴差 girder.",
    },
    "roofbeam-plate": {
        "title": "小屋梁 into plate",
        "description": "The roof beam tenons into the inner face of the 軒桁 plate.",
        "catalog": "yatoi-hozo-shikuchi",
        "match": "related",
    },
    "roofpost-beam": {
        "title": "Roof post on beam",
        "description": ("The 小屋束 or 真束 tenons down into the top of the "
                        "roof beam."),
        "catalog": "yatoi-hozo-shikuchi",
        "match": "related",
    },
    "roofpost-purlin": {
        "title": "母屋 over roof post",
        "description": "The purlin is notched over the tenoned top of the roof post.",
        "catalog": "yatoi-hozo-shikuchi",
        "match": "related",
    },
    "roofpost-ridge": {
        "title": "真束 into ridge",
        "description": "The king post tenons into the ridge, which is notched over it.",
        "catalog": "yatoi-hozo-shikuchi",
        "match": "related",
    },
    "purlin-hip": {
        "title": "Purlin under hip",
        "description": "The 母屋 purlin end carries the 隅木 hip rafter where their lines cross.",
    },
    "ridge-hip": {
        "title": "Hip into ridge",
        "description": "The 隅木 hip rafter butts the end of the ridge.",
    },
    "hip-plate": {
        "title": "Hip over plate",
        "description": "The hip rafter passes over the corner where the two 軒桁 plates meet.",
    },
    "rafter-ridge": {
        "title": "Rafter at ridge",
        "description": "The common rafter butts the ridge at the top of the slope.",
    },
    "rafter-hip": {
        "title": "Rafter at hip",
        "description": "The common rafter is cut square against the hip rafter.",
    },
    "rafter-purlin": {
        "title": "Rafter over purlin",
        "description": "A birdsmouth notch seats the rafter over the 母屋 purlin.",
    },
    "rafter-plate": {
        "title": "Rafter over plate",
        "description": "A birdsmouth notch seats the rafter over the 軒桁 plate.",
    },
    "jack-hip": {
        "title": "Jack rafter at hip",
        "description": "The jack rafter is cut square against the hip rafter.",
    },
    "jack-plate": {
        "title": "Jack rafter over plate",
        "description": "The jack rafter is notched over the 軒桁 plate at the hipped end.",
    },
}

KIND_ORDER = {kind: i for i, kind in enumerate(KINDS)}
GROUP_LABELS = {
    "axis": "axis frame",
    "roof": "roof frame",
    "floor": "floor framing",
    "base": "foundation and stone",
}


def catalog_record(slug):
    path = os.path.join(JOINT_SRC, slug + ".json")
    with open(path) as fh:
        level = json.load(fh)[0]
    return {"slug": slug, "title": level["title"], "jp": level["jp"]}


def kind_record(kind):
    meta = KINDS[kind]
    record = {"title": meta["title"], "description": meta["description"]}
    if meta.get("catalog"):
        record["catalog"] = catalog_record(meta["catalog"])
        record["match"] = meta["match"]
    return record


# ---------------------------------------------------------------------------
def build_connections(house):
    """Return every connection instance in construction order."""
    conns = []
    seen = set()

    def add(kind, members, point, anchor):
        if kind not in KINDS:
            raise SystemExit("unknown connection kind %r" % kind)
        if anchor not in members:
            raise SystemExit("anchor %s is not a member of %s" % (anchor, kind))
        for pid in members:
            if pid not in house.members:
                raise SystemExit("connection %s names missing member %s"
                                 % (kind, pid))
        point = [round(float(v), 4) for v in point]
        key = (kind, tuple(sorted(members)), tuple(point))
        if key in seen:
            return
        seen.add(key)
        conns.append({"kind": kind, "members": list(members),
                      "point": point, "anchor": anchor})

    # -- sills ------------------------------------------------------------
    # The x sills keep their lower half, the z sills their upper half.
    for sx in (-1, 1):
        for sz in (-1, 1):
            x = "sill-x-" + ("f" if sz > 0 else "b")
            z = "sill-z-" + ("r" if sx > 0 else "l")
            add("sill-corner", [x, z], (sx * WH, 0.51, sz * DH), x)

    # -- posts on sills ---------------------------------------------------
    for ix, x in enumerate(G.XS):
        for iz, z in enumerate(G.ZS):
            post = "post-%d-%d" % (ix, iz)
            if iz == 0:
                primary = "sill-x-b"
            elif iz == 2:
                primary = "sill-x-f"
            elif ix == 0:
                primary = "sill-z-l"
            elif ix == len(G.XS) - 1:
                primary = "sill-z-r"
            else:
                primary = "sill-x-centre"
            add("post-sill", [post, primary], (x, G.SILL_TOP, z), primary)
            # At a corner the post passes through both half-lapped sills.
            if iz in (0, 2) and ix in (0, len(G.XS) - 1):
                other = "sill-z-" + ("l" if ix == 0 else "r")
                add("post-sill", [post, other], (x, G.SILL_TOP, z), other)

    # -- beams into posts -------------------------------------------------
    def beam_specs(axisname, fixed, y0, y1, width, group, name, index):
        coords = G.XS if axisname == "x" else G.ZS
        out = []
        for k in range(len(coords) - 1):
            if axisname == "x":
                pid = "beam-x-%d-%d-%d" % (index, round(y0 * 100), k)
                iz = 0 if fixed < 0 else (2 if fixed > 0 else 1)
                ends = [(k, iz), (k + 1, iz)]
            else:
                pid = "beam-z-%d-%d-%d" % (index, round(y0 * 100), k)
                ix = 0 if fixed < 0 else len(G.XS) - 1
                ends = [(ix, k), (ix, k + 1)]
            out.append({"id": pid, "axis": axisname, "fixed": fixed,
                        "y0": y0, "y1": y1, "width": width, "group": group,
                        "name": name, "index": index, "k": k, "ends": ends})
        return out

    beams = []
    for z in (-DH, DH):
        beams += beam_specs("x", z, G.F1 - G.GIRD, G.F1, 0.12,
                            "axis", "Gird", 0 if z < 0 else 2)
    for x in (-WH, WH):
        beams += beam_specs("z", x, G.F1 - G.GIRD, G.F1, 0.12,
                            "axis", "Gird", 0 if x < 0 else 3)
    beams += beam_specs("x", 0.0, G.F1 - G.BEAM, G.F1, 0.12,
                        "floor", "Floor beam", 1)
    for z in (-DH, DH):
        beams += beam_specs("x", z, G.BEAM2_TOP, G.WALL_TOP, 0.12,
                            "axis", "Plate", 0 if z < 0 else 2)
    for x in (-WH, WH):
        beams += beam_specs("z", x, G.BEAM2_TOP, G.WALL_TOP, 0.12,
                            "axis", "Plate", 0 if x < 0 else 3)

    for beam in beams:
        y = (beam["y0"] + beam["y1"]) / 2
        for ix, iz in beam["ends"]:
            post = "post-%d-%d" % (ix, iz)
            add("post-beam", [beam["id"], post],
                (G.XS[ix], y, G.ZS[iz]), post)

    # -- 貫 through posts and studs ---------------------------------------
    runs = []
    for y0 in (1.50, 2.55, 4.30, 5.35):
        for z in (-DH, DH):
            runs.append((y0, "x", z))
        for x in (-WH, WH):
            runs.append((y0 + 0.065, "z", x))

    for n, (y0, axisname, fixed) in enumerate(runs):
        coords = G.XS if axisname == "x" else G.ZS
        y = y0 + G.NUKI_H / 2
        suffix = "-up" if y0 >= G.F1 else ""
        for k in range(len(coords) - 1):
            nuki = "nuki-%d-%d" % (n, k)
            if axisname == "x":
                iz = 0 if fixed < 0 else 2
                ends = [(k, iz), (k + 1, iz)]
                stud = "stud-%s-%d%s" % ("b" if fixed < 0 else "f", k, suffix)
                stud_point = ((G.XS[k] + G.XS[k + 1]) / 2, y, fixed)
            else:
                ix = 0 if fixed < 0 else len(G.XS) - 1
                ends = [(ix, k), (ix, k + 1)]
                stud = "stud-%s-%d%s" % ("l" if fixed < 0 else "r", k, suffix)
                stud_point = (fixed, y, (G.ZS[k] + G.ZS[k + 1]) / 2)
            for ix, iz in ends:
                post = "post-%d-%d" % (ix, iz)
                add("nuki-post", [nuki, post],
                    (G.XS[ix], y, G.ZS[iz]), post)
            add("nuki-stud", [nuki, stud], stud_point, stud)

    # -- braces -----------------------------------------------------------
    def nearest(coords, value):
        return min(range(len(coords)), key=lambda i: abs(coords[i] - value))

    braces = []
    # Long walls, lower storey.
    for z in (-DH, DH):
        s = 1 if z > 0 else -1
        for k, (a, b) in enumerate(((-2.73, -0.91), (0.91, 2.73))):
            y0, y1 = G.SILL_TOP + 0.12, G.F1 - G.GIRD - 0.12
            if k == 0:
                p0, p1 = ((a + 0.12, y0, z + s * 0.02),
                          (b - 0.12, y1, z + s * 0.02))
            else:
                p0, p1 = ((b - 0.12, y0, z + s * 0.02),
                          (a + 0.12, y1, z + s * 0.02))
            braces.append(("brace-f-%s-%d" % ("f" if s > 0 else "b", k),
                           p0, p1, "long", z))
    # Long walls, upper storey.
    for z in (-DH, DH):
        s = 1 if z > 0 else -1
        for k, (a, b) in enumerate(((-2.73, -0.91), (0.91, 2.73))):
            y0, y1 = G.F1 + 0.12, G.WALL_TOP - G.GIRD - 0.12
            if k == 0:
                p0, p1 = ((b - 0.12, y0, z + s * 0.02),
                          (a + 0.12, y1, z + s * 0.02))
            else:
                p0, p1 = ((a + 0.12, y0, z + s * 0.02),
                          (b - 0.12, y1, z + s * 0.02))
            braces.append(("brace-u-%s-%d" % ("f" if s > 0 else "b", k),
                           p0, p1, "long", z))
    # End walls, one brace per storey.
    for x in (-WH, WH):
        s = 1 if x > 0 else -1
        for storey, (y0, y1) in enumerate(((G.SILL_TOP + 0.12,
                                            G.F1 - G.GIRD - 0.12),
                                           (G.F1 + 0.12,
                                            G.WALL_TOP - G.GIRD - 0.12))):
            b = 0.0 if storey == 0 else 1.82
            a = -1.82 if storey == 0 else 0.0
            p0 = (x + s * 0.02, y0, a + 0.12)
            p1 = (x + s * 0.02, y1, b - 0.12)
            braces.append(("brace-end-%s-%d" % ("r" if s > 0 else "l",
                                                storey),
                           p0, p1, "end", x))

    for pid, p0, p1, wall, fixed in braces:
        for p in (p0, p1):
            if wall == "long":
                ix = nearest(G.XS, p[0])
                iz = 0 if fixed < 0 else 2
            else:
                ix = 0 if fixed < 0 else len(G.XS) - 1
                iz = nearest(G.ZS, p[2])
            post = "post-%d-%d" % (ix, iz)
            add("brace", [pid, post], p, post)

    # -- 火打梁 corner ties -----------------------------------------------
    for level, (yc, d) in enumerate(((G.SILL_TOP + 0.045, 0.09),
                                     (G.F1 + 0.045, 0.09))):
        for x in (-WH, WH):
            for z in (-DH, DH):
                sx = 1 if x > 0 else -1
                sz = 1 if z > 0 else -1
                p0 = (x - sx * 0.06, yc, z - sz * 0.58)
                p1 = (x - sx * 0.58, yc, z - sz * 0.06)
                pid = "fire-%d-%s%s" % (level, "r" if sx > 0 else "l",
                                        "f" if sz > 0 else "b")
                if level == 0:
                    xm = "sill-x-" + ("f" if z > 0 else "b")
                    zm = "sill-z-" + ("r" if x > 0 else "l")
                else:
                    xm = "beam-x-%d-309-%d" % (0 if z < 0 else 2,
                                               0 if x < 0 else 2)
                    zm = "beam-z-%d-309-%d" % (0 if x < 0 else 3,
                                               0 if z < 0 else 1)
                point = ((p0[0] + p1[0]) / 2, yc, (p0[2] + p1[2]) / 2)
                add("fire-beam", [pid, xm, zm], point, xm)

    # -- ground-floor framing --------------------------------------------
    for x in (-1.82, -0.91, 0.0, 0.91, 1.82):
        for z in A.SLEEPER_Z:
            tag = "%d-%d" % (round(x * 100), round(z * 100))
            post = "floor-post-" + tag
            sleeper = "sleeper-%d" % round(z * 100)
            stone = "floor-stone-" + tag
            add("floorpost-sleeper", [post, sleeper], (x, 0.42, z), sleeper)
            add("floorpost-stone", [post, stone], (x, 0.15, z), stone)

    for z in A.SLEEPER_Z:
        sleeper = "sleeper-%d" % round(z * 100)
        for sx in (-1, 1):
            sill = "sill-z-" + ("l" if sx < 0 else "r")
            add("sleeper-sill", [sleeper, sill],
                (sx * (WH - 0.045), 0.465, z), sill)

    xs = [-2.5025 + i * 0.455 for i in range(12)]
    for i, x in enumerate(xs):
        joist = "joist-%02d" % i
        for z in A.SLEEPER_Z:
            sleeper = "sleeper-%d" % round(z * 100)
            add("joist-sleeper", [joist, sleeper], (x, 0.495, z), sleeper)
        add("joist-sleeper", [joist, "sill-x-centre"],
            (x, 0.495, 0.0), "sill-x-centre")
        for s in (-1, 1):
            sill = "sill-x-" + ("f" if s > 0 else "b")
            add("joist-sill", [joist, sill],
                (x, 0.535, s * (DH - 0.06)), sill)

    # -- second-floor joists ---------------------------------------------
    for i, x in enumerate((-2.275, -1.365, -0.455, 0.455, 1.365, 2.275)):
        joist = "joist-up-%02d" % i
        bay = 0 if x < -0.91 else (1 if x < 0.91 else 2)
        spine = "beam-x-1-303-%d" % bay
        add("upperjoist-beam", [joist, spine], (x, 3.165, 0.0), spine)
        for s, iz in ((-1, 0), (1, 2)):
            girder = "beam-x-%d-309-%d" % (iz, bay)
            add("upperjoist-girder", [joist, girder],
                (x, 3.195, s * (DH - 0.045)), girder)

    # -- roof beams and posts --------------------------------------------
    for i, x in enumerate((-1.82, 0.0, 1.82)):
        roofbeam = "roofbeam-%d" % i
        bay = 0 if x < -0.91 else (1 if x < 0.91 else 2)
        for s, iz in ((-1, 0), (1, 2)):
            plate = "beam-x-%d-618-%d" % (iz, bay)
            add("roofbeam-plate", [roofbeam, plate],
                (x, G.BEAM2_TOP + 0.09, s * 1.76), plate)

    roof_posts = [(0.0, 0.0, G.RIDGE_TOP - G.RIDGE + 0.04, "king")]
    for x in (-1.82, 0.0, 1.82):
        for z in (-G.PURLIN_Z, G.PURLIN_Z):
            roof_posts.append((x, z, G.PURLIN_TOP - G.PURLIN + 0.04, "strut"))

    for i, (x, z, top, name) in enumerate(roof_posts):
        roofpost = "roofpost-%d" % i
        bay = 0 if x < -0.91 else (1 if x < 0.91 else 2)
        roofbeam = "roofbeam-%d" % bay
        add("roofpost-beam", [roofpost, roofbeam],
            (x, G.WALL_TOP, z), roofbeam)
        if name == "king":
            add("roofpost-ridge", [roofpost, "ridge"], (x, top, z), "ridge")
        else:
            purlin = "purlin-b" if z < 0 else "purlin-f"
            add("roofpost-purlin", [roofpost, purlin], (x, top, z), purlin)

    # The purlins run between the hips and carry them at their ends.
    for z in (-G.PURLIN_Z, G.PURLIN_Z):
        purlin = "purlin-b" if z < 0 else "purlin-f"
        for sx in (-1, 1):
            hip = "hip-%s%s" % ("r" if sx > 0 else "l",
                                "f" if z > 0 else "b")
            add("purlin-hip", [purlin, hip],
                (sx * 1.82, G.PURLIN_TOP, z), purlin)

    # -- ridge, hips and common rafters ----------------------------------
    for sx in (-1, 1):
        for sz in (-1, 1):
            hip = "hip-%s%s" % ("r" if sx > 0 else "l",
                                "f" if sz > 0 else "b")
            add("ridge-hip", [hip, "ridge"],
                (sx * 0.91, G.RIDGE_TOP - 0.09, 0.0), "ridge")

    def roof_y(zabs):
        return G.EAVE_EDGE + (G.ROOF_RUN - zabs) * G.ROOF_SLOPE

    def at_z(p0, p1, z):
        t = (z - p0[2]) / (p1[2] - p0[2])
        return (p0[0] + (p1[0] - p0[0]) * t,
                p0[1] + (p1[1] - p0[1]) * t, z)

    for sx in (-1, 1):
        for sz in (-1, 1):
            hip = "hip-%s%s" % ("r" if sx > 0 else "l",
                                "f" if sz > 0 else "b")
            px = "beam-x-%d-618-%d" % (0 if sz < 0 else 2,
                                       0 if sx < 0 else 2)
            pz = "beam-z-%d-618-%d" % (0 if sx < 0 else 3,
                                       0 if sz < 0 else 1)
            frac = (WH - 0.91) / (3.33 - 0.91)
            y = ((G.RIDGE_TOP - 0.09)
                 + ((G.EAVE_EDGE - 0.09) - (G.RIDGE_TOP - 0.09)) * frac)
            add("hip-plate", [hip, px, pz],
                (sx * WH, y, sz * DH), px)

    n = 0
    for x in [-3.185 + i * 0.455 for i in range(15)]:
        z0 = max(0.0, abs(x) - 0.91)
        if z0 > 2.22:
            continue
        for s in (-1, 1):
            p0 = (x, roof_y(z0) - 0.045, s * z0)
            p1 = (x, roof_y(2.42) - 0.045, s * 2.42)
            rafter = "rafter-%d-%s" % (n, "f" if s > 0 else "b")
            n += 1
            if z0 <= 1e-9:
                add("rafter-ridge", [rafter, "ridge"], p0, "ridge")
            else:
                hip = "hip-%s%s" % ("r" if x > 0 else "l",
                                    "f" if s > 0 else "b")
                add("rafter-hip", [rafter, hip], p0, hip)
            for zc in (0.91, 1.82):
                if zc <= z0 + 0.08 or zc >= 2.34:
                    continue
                point = at_z(p0, p1, s * zc)
                if zc == 0.91:
                    purlin = "purlin-f" if s > 0 else "purlin-b"
                    add("rafter-purlin", [rafter, purlin], point, purlin)
                else:
                    bay = 0 if x < -0.91 else (1 if x < 0.91 else 2)
                    plate = "beam-x-%d-618-%d" % (0 if s < 0 else 2, bay)
                    add("rafter-plate", [rafter, plate], point, plate)

    # -- jack rafters on the hipped ends ---------------------------------
    for z in [-2.275 + i * 0.455 for i in range(11)]:
        x0 = 0.91 + abs(z)
        if x0 > 3.18:
            continue
        for s in (-1, 1):
            y0 = G.EAVE_EDGE + (G.ROOF_RUN + 0.91 - x0) * G.ROOF_SLOPE
            y1 = G.EAVE_EDGE
            p0 = (s * x0, y0 - 0.045, z)
            p1 = (s * 3.33, y1 - 0.045, z)
            rafter = "rafter-end-%d-%s" % (n, "r" if s > 0 else "l")
            n += 1
            hip = "hip-%s%s" % ("r" if s > 0 else "l",
                                "f" if z > 0 else "b")
            add("jack-hip", [rafter, hip], p0, hip)
            if x0 < 2.69:
                t = (2.73 - x0) / (3.33 - x0)
                point = (s * 2.73,
                         (y0 - 0.045) + ((y1 - 0.045) - (y0 - 0.045)) * t,
                         z)
                plate = "beam-z-%d-618-%d" % (0 if s < 0 else 3,
                                              0 if z < 0 else 1)
                add("jack-plate", [rafter, plate], point, plate)

    return conns


def main():
    house = A.build()
    pieces = house.build()
    conns = build_connections(house)

    # Stable IDs: order by family, then by position, then by members.
    conns.sort(key=lambda c: (KIND_ORDER[c["kind"]], c["point"],
                              c["members"]))
    for i, conn in enumerate(conns, 1):
        conn["id"] = "c%04d" % i

    piece_meta = {}
    for piece in pieces:
        center, size = bbox(piece)
        if center is None:
            raise SystemExit("empty piece %s" % piece["id"])
        piece_meta[piece["id"]] = {
            "name": piece["name"],
            "group": piece["group"],
            "center": [round(v, 4) for v in center],
            "size": [round(v, 4) for v in size],
            "connections": [],
        }

    kinds_used = {}
    for conn in conns:
        for pid in conn["members"]:
            piece_meta[pid]["connections"].append(conn["id"])
        kinds_used[conn["kind"]] = kinds_used.get(conn["kind"], 0) + 1

    for pid in house.members:
        if pid not in piece_meta:
            raise SystemExit("member %s did not produce a piece" % pid)
    for conn in conns:
        for pid in conn["members"]:
            if pid not in piece_meta:
                raise SystemExit("connection %s names unknown piece %s"
                                 % (conn["id"], pid))
        x, y, z = conn["point"]
        if not (-4.0 <= x <= 4.0 and -0.1 <= y <= 8.2 and -3.2 <= z <= 3.2):
            raise SystemExit("connection %s point out of frame: %s"
                             % (conn["id"], conn["point"]))

    used_kinds = {}
    for kind in KINDS:
        if kind in kinds_used:
            used_kinds[kind] = kind_record(kind)
            used_kinds[kind]["count"] = kinds_used[kind]

    data = {
        "version": 1,
        "generatedBy": "tools/house_links.py",
        "note": ("Explicit connection instances derived from the members and "
                 "joinery authored in tools/author_house.py. Points are in the "
                 "assembled pose, metres, Y up."),
        "house": {
            "title": "The house",
            "jp": "民家",
            "pieces": len(piece_meta),
            "connections": len(conns),
            "groups": GROUP_LABELS,
            "levels": {"F1": round(G.F1, 4),
                       "wallTop": round(G.WALL_TOP, 4)},
        },
        "kinds": used_kinds,
        "pieces": piece_meta,
        "connections": conns,
    }
    with open(OUT, "w") as fh:
        json.dump(data, fh, indent=1, sort_keys=False)
        fh.write("\n")

    print("wrote %s: %d pieces, %d connections, %d families"
          % (OUT, len(piece_meta), len(conns), len(used_kinds)))
    for kind, count in sorted(kinds_used.items(), key=lambda kv: KIND_ORDER[kv[0]]):
        print("  %-22s %3d" % (kind, count))
    empty = sum(1 for p in piece_meta.values() if not p["connections"])
    print("  %d pieces have no connection (foundation / ground)" % empty)


if __name__ == "__main__":
    main()
