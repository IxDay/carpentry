#!/usr/bin/env python3
"""Author the joint details that only exist in the house frame.

The 34 specimens on the two reference sheets stop at column-and-beam (shikuchi)
and splice (tsugite) joinery.  The house uses more: braces let into post faces,
halved floor framing, a birdsmouth over a purlin, a hip butting the ridge, and
so on.  This script builds one representative specimen for each of those house
connection families, at the same 120 mm timber scale as the other joints, so the
house viewer can link a connection to a real model instead of only to the
schedule.

The geometry is original, authored for this collection from the house frame's
joints; it is released CC BY 4.0.  Most pieces are box CSG, like author_joint.py.
Sloped members are built in a local frame; two extras are needed there:

* ``trim`` clips a piece with an arbitrary plane and stitches the cut cap, for
  square-cut hip and rafter ends where they meet another member;
* ``profile_piece`` extrudes a 2D side profile across the member width, so a
  rafter can carry a real birdsmouth with a horizontal seat rather than a notch
  parallel to its own underside.

After regenerating, run check_sources.py and bake.py.
"""
import json
import math
import os
import sys

from author_joint import COLOR, joint, weld_edges
import house_geom as G

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCES = os.path.join(HERE, "..", "joints", "sources")

DETAIL_CREDIT = ("Original geometry authored for this collection from the "
                 "house frame's connections; CC BY 4.0.")
DETAIL_MODS = ("authored in closed pose from the house frame's joinery, "
               "exploded for the assemble animation, sunset lighting baked; "
               "the baking rig's ground slab is omitted")

EPS = 1e-7


# --------------------------------------------------------------- plane trim --
def _newell(pts):
    nx = ny = nz = 0.0
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        nx += (a[1] - b[1]) * (a[2] + b[2])
        ny += (a[2] - b[2]) * (a[0] + b[0])
        nz += (a[0] - b[0]) * (a[1] + b[1])
    return [nx, ny, nz]


def _dominant_color(faces):
    from collections import Counter
    colors = Counter(tuple(round(c, 6) for c in f.get("color", COLOR))
                     for f in faces)
    return list(colors.most_common(1)[0][0])


def _make_face(pts, want):
    """A face with its point order wound to agree with `want`."""
    pts = [list(q) for q in pts]
    n = _newell(pts)
    if sum(n[i] * want[i] for i in range(3)) < 0:
        pts.reverse()
    n = _newell(pts)
    L = math.sqrt(sum(c * c for c in n)) or 1.0
    return {"points": pts, "normal": [c / L for c in n], "color": list(COLOR)}


def _clip_faces(faces, point, normal, keep_le=True):
    """Clip polygons to one side of a plane and cap the cut.

    The cut side is ``dot(p - point, normal) <= 0`` when `keep_le` is true; the
    cap's outward normal is then ``+normal``.  Only convex timber prisms are
    trimmed this way, so the cut is a single loop.
    """
    n = G.norm(normal)
    out = []
    segments = []
    for f in faces:
        pts = [[float(c) for c in q] for q in f["points"]]
        new = []
        crossings = []
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            da = sum((a[k] - point[k]) * n[k] for k in range(3))
            db = sum((b[k] - point[k]) * n[k] for k in range(3))
            ia = da <= EPS if keep_le else da >= -EPS
            ib = db <= EPS if keep_le else db >= -EPS
            if ia:
                new.append(a)
            if ia != ib:
                t = da / (da - db)
                q = [a[k] + (b[k] - a[k]) * t for k in range(3)]
                q = [round(c, 6) for c in q]
                new.append(q)
                crossings.append(q)
        if len(crossings) == 2:
            segments.append((crossings[0], crossings[1]))
        clean = []
        for q in new:
            if not clean or max(abs(q[k] - clean[-1][k])
                                for k in range(3)) > 1e-7:
                clean.append(q)
        if len(clean) > 1 and max(abs(clean[0][k] - clean[-1][k])
                                  for k in range(3)) < 1e-7:
            clean.pop()
        if len(clean) >= 3:
            out.append({"points": clean, "normal": list(f["normal"]),
                        "color": list(f.get("color", COLOR))})

    # Stitch the cut segments into a loop, then add it as the cap.
    def key(q):
        return tuple(round(c, 6) for c in q)

    adj = {}
    for a, b in segments:
        ka, kb = key(a), key(b)
        if ka == kb:
            continue
        adj.setdefault(ka, []).append(kb)
        adj.setdefault(kb, []).append(ka)
    used = set()
    for start in list(adj):
        if start in used:
            continue
        loop = [start]
        used.add(start)
        cur = start
        while True:
            nxt = [q for q in adj[cur] if q not in used]
            if not nxt:
                break
            nxt = nxt[0]
            used.add(nxt)
            loop.append(nxt)
            cur = nxt
            if cur == start:
                break
        if len(loop) < 3:
            continue
        pts = [list(q) for q in loop]
        want = n if keep_le else [-c for c in n]
        out.append(_make_face(pts, want))
    return out


def trim(piece_def, point, normal, keep_le=True):
    """Trim a piece with a plane and cap the cut."""
    out = {k: v for k, v in piece_def.items()}
    solids = []
    for solid in piece_def["solids"]:
        faces = _clip_faces(solid["faces"], point, normal, keep_le)
        if faces:
            solids.append({"faces": weld_edges(faces)})
    out["solids"] = solids
    return out


# ------------------------------------------------------------- profile prism --
def profile_piece(pid, name, color, p0, p1, w, profile, up=(0.0, 1.0, 0.0)):
    """Extrude a 2D profile (list of ``(x, z)`` points, CCW) across the width.

    Local x runs from `p0` to `p1`, local y is the width direction and local z
    the member depth, matching ``house_geom.oriented_piece``.  This is used for
    a birdsmouth, whose horizontal seat is a sloped line in the member frame.
    """
    d = G.sub(p1, p0)
    L = math.sqrt(sum(c * c for c in d))
    ex = G.norm(d)
    side = G.norm(G.cross(up, ex))
    ez = G.cross(ex, side)

    def world(x, y, z):
        return [p0[i] + x * ex[i] + y * side[i] + z * ez[i] for i in range(3)]

    faces = []
    for y, want in ((-w / 2, [-c for c in side]), (w / 2, side)):
        faces.append(_make_face([world(x, y, z) for x, z in profile], want))
    n = len(profile)
    for i in range(n):
        a, b = profile[i], profile[(i + 1) % n]
        dx, dz = b[0] - a[0], b[1] - a[1]
        # For a CCW polygon the outward normal is (dz, -dx) in the x-z plane.
        want = [dz * ex[k] - dx * ez[k] for k in range(3)]
        pts = [world(a[0], -w / 2, a[1]), world(b[0], -w / 2, b[1]),
               world(b[0], w / 2, b[1]), world(a[0], w / 2, a[1])]
        faces.append(_make_face(pts, want))
    return G.piece(pid, name, "detail", color, faces)


# ------------------------------------------------------------------ helpers --
def axis(pid, name, color, lo, hi, cuts=(), adds=()):
    return G.axis_piece(pid, name, "detail", color, lo, hi,
                        cuts=cuts, adds=adds)


def oriented(pid, name, color, p0, p1, w, h, up=(0.0, 1.0, 0.0)):
    return G.oriented_piece(pid, name, "detail", color, p0, p1, w, h, up=up)


def _yaw_vector(v, ca, sa):
    return [v[0] * ca + v[2] * sa, v[1], -v[0] * sa + v[2] * ca]


def yaw_detail(pieces, exploded, degrees):
    """Turn a whole detail about y, geometry and explode offsets alike."""
    a = math.radians(degrees)
    ca, sa = math.cos(a), math.sin(a)
    for p in pieces:
        for s in p["solids"]:
            for f in s["faces"]:
                f["points"] = [_yaw_vector(q, ca, sa) for q in f["points"]]
                f["normal"] = _yaw_vector(f["normal"], ca, sa)
    # The explode vector is stored as `assemble` and added back by the checks,
    # so it must stay on the same 1 µm grid as the geometry.
    return pieces, {k: [round(c, 6) for c in _yaw_vector(v, ca, sa)]
                    for k, v in exploded.items()}


def detail(jid, title, jp, pieces, exploded, guidance, camera=None, yaw=0.0):
    if yaw:
        pieces, exploded = yaw_detail(pieces, exploded, yaw)
    out = joint(jid, title, jp, pieces, exploded, guidance,
                tab="house-details", credit=DETAIL_CREDIT,
                modifications=DETAIL_MODS)
    if camera:
        out["camera"] = camera
    return out


def corner_plates(color):
    """Two 120 mm sills/plates half-lapped at a right-angled corner."""
    return [
        axis("part-a", "Sill X", color,
             (-0.75, -HALF, -HALF), (0.15, HALF, HALF),
             cuts=[G.box((-HALF, 0.0, -HALF), (HALF, HALF, HALF))]),
        axis("part-b", "Sill Z", color,
             (-HALF, -HALF, -0.75), (HALF, HALF, 0.15),
             cuts=[G.box((-HALF, -HALF, -HALF), (HALF, 0.0, HALF))]),
    ]


def rafter_profile(L, h, x0, x1, z0, z1):
    """A 90 mm deep side profile with a seat between x0 and x1."""
    lo = -h / 2
    hi = h / 2
    return [(0.0, lo), (x0, lo), (x0, z0), (x1, z1), (x1, lo),
            (L, lo), (L, hi), (0.0, hi)]


def seated_rafter(pid, name, color, p0, p1, w, h, seat_y, z0, z1):
    """A rafter with a horizontal birdsmouth seat over world z0..z1.

    `seat_y` is the height of the seat (the purlin or plate top plus a hair of
    clearance); the seat is horizontal in world space even though the member
    itself slopes.
    """
    d = G.sub(p1, p0)
    L = math.sqrt(sum(c * c for c in d))
    ex = G.norm(d)
    ez = G.cross(ex, G.norm(G.cross((0.0, 1.0, 0.0), ex)))
    # World y along the member: p0.y + x*ex.y + z*ez.y.
    def x_at(z):
        return (z - p0[2]) / ex[2]

    def z_seat(x):
        return (seat_y - p0[1] - x * ex[1]) / ez[1]

    x0, x1 = x_at(z0), x_at(z1)
    lo = -h / 2
    a, b = z_seat(x0), z_seat(x1)
    a = max(lo + 0.002, min(h / 2 - 0.002, a))
    b = max(lo + 0.002, min(h / 2 - 0.002, b))
    return profile_piece(pid, name, color, p0, p1, w,
                         rafter_profile(L, h, x0, x1, a, b))


# -- 1. sill corner ---------------------------------------------------------
SILL = 0.12
HALF = SILL / 2

SILL_CORNER = detail(
    "sill-corner", "Sill corner", "土台の留め",
    corner_plates(G.COLORS["sill"]),
    {"part-b": [0.0, 0.35, 0.0]},
    "Two 土台 sills cross at the corner and are halved into each other: the "
    "x-sill keeps its lower half, the z-sill its upper half, and the two "
    "alternate from corner to corner around the frame."
)


# -- 2. brace into post -----------------------------------------------------
POST = 0.12
BRACE_W, BRACE_H = 0.09, 0.105
# The brace is 105 mm deep through the wall. Its inner face bears on the
# bottom of the 10 mm housing cut into the post face (x = 0.050).
BRACE_POST = detail(
    "brace-into-post", "Brace into post", "筋違",
    [
        axis("part-a", "Post", G.COLORS["post"],
             (-0.06, -0.45, -0.06), (0.06, 0.55, 0.06),
             cuts=[G.box((0.050, -0.42, -0.08), (0.0605, -0.24, 0.08))]),
        oriented("part-b", "Brace", G.COLORS["brace"],
                 (0.1025, -0.35, 0.0), (0.1025, 0.40, 0.75),
                 BRACE_W, BRACE_H, up=(1.0, 0.0, 0.0)),
    ],
    {"part-b": [0.36, 0.0, 0.0]},
    "The 筋違 brace is let into the post face. Its own 90 mm thickness forms "
    "the housing, so there is no peg and no tenon: the end sits in the shallow "
    "notch and the brace withdraws square to the wall.",
    yaw=-90.0
)


# -- 3. fire-beam tie -------------------------------------------------------
# The 火打梁 is not just laid on the sills: the traditional detail is a
# かたぎ大入れ, a 30 mm deep housing cut into the top of each sill for a
# matching foot on the diagonal tie (see the Flat35 / carpentry-school details
# referenced in joints/README.md).  The feet are 60 x 40 mm tenons in the
# member's local frame; the sill housings are square pockets large enough to
# clear the 45-degree plan footprint.
FIRE_P0 = (-0.46, 0.105, 0.0)
FIRE_P1 = (0.0, 0.105, -0.46)
FIRE_L = math.sqrt(sum((FIRE_P1[i] - FIRE_P0[i]) ** 2 for i in range(3)))
FIRE_FOOT = 0.04
FIRE_DROP = 0.03

def _sill_with_housing(lo, hi, corner_cut, housing):
    p = G.axis_piece("sill", "sill", "detail", G.COLORS["sill"], lo, hi,
                     cuts=[corner_cut, housing])
    return p["solids"]


FIRE_PIECES = corner_plates(G.COLORS["sill"])
# housing in the x sill, under the tie's near foot
FIRE_PIECES[0]["solids"] = _sill_with_housing(
    (-0.75, -HALF, -HALF), (0.15, HALF, HALF),
    G.box((-HALF, 0.0, -HALF), (HALF, HALF, HALF)),
    G.box((-0.49, HALF - FIRE_DROP - EPS, -0.055),
          (-0.42, HALF + EPS, 0.025)))
# housing in the z sill, under the tie's far foot
FIRE_PIECES[1]["solids"] = _sill_with_housing(
    (-HALF, -HALF, -0.75), (HALF, HALF, 0.15),
    G.box((-HALF, -HALF, -HALF), (HALF, 0.0, HALF)),
    G.box((-0.025, HALF - FIRE_DROP - EPS, -0.49),
          (0.025, HALF + EPS, -0.42)))
FIRE_PIECES.append(
    G.oriented_piece("part-c", "Fire beam", "detail", G.COLORS["beam"],
                     FIRE_P0, FIRE_P1, 0.09, 0.09,
                     adds=[((0.0, FIRE_FOOT), (-0.03, 0.03),
                            (-0.045 - FIRE_DROP, -0.045)),
                           ((FIRE_L - FIRE_FOOT, FIRE_L), (-0.03, 0.03),
                            (-0.045 - FIRE_DROP, -0.045))],
                     up=(0.0, 1.0, 0.0)))

FIRE_BEAM = detail(
    "fire-beam-tie", "Fire-beam tie", "火打梁",
    FIRE_PIECES,
    {"part-c": [0.0, 0.38, 0.0]},
    "A 火打梁 ties the two 土台 sills across the corner. Each end carries a "
    "60 x 40 mm foot 30 mm deep in a matching かたぎ大入れ housing cut into "
    "the sill top, so the diagonal tie is held in plan as well as in bearing.",
    yaw=-45.0
)


# -- 4. joist half-lap ------------------------------------------------------
JOIST_HALF_LAP = detail(
    "joist-half-lap", "Joist half-lap", "根太の相欠き",
    [
        axis("part-a", "Sleeper", G.COLORS["sleeper"],
             (-0.75, 0.0, -0.045), (0.75, 0.09, 0.045),
             cuts=[G.box((-0.03, 0.06, -0.06), (0.03, 0.09, 0.06))]),
        axis("part-b", "Joist", G.COLORS["joist"],
             (-0.03, 0.03, -0.75), (0.03, 0.12, 0.75),
             cuts=[G.box((-0.03, 0.03, -0.045), (0.03, 0.06, 0.045))]),
    ],
    {"part-b": [0.0, 0.36, 0.0]},
    "The 根太 joist crosses the 大引 sleeper with 30 mm taken out of each: "
    "the sleeper keeps its lower half, the joist its upper half, and the two "
    "meet on a common bearing plane so the floor stays level."
)


# -- 5. joist into sill -----------------------------------------------------
JOIST_SILL = detail(
    "joist-into-sill", "Joist into sill", "根太の土台差し",
    [
        axis("part-a", "Sill", G.COLORS["sill"],
             (-0.75, 0.0, -0.06), (0.75, 0.12, 0.06),
             cuts=[G.box((-0.03, 0.02, -0.061), (0.03, 0.07, -0.03))]),
        axis("part-b", "Joist", G.COLORS["joist"],
             (-0.03, 0.02, -0.75), (0.03, 0.11, -0.06),
             adds=[G.box((-0.03, 0.02, -0.06), (0.03, 0.07, -0.03))]),
    ],
    {"part-b": [0.0, 0.0, -0.38]},
    "The 根太 joist end is housed 30 mm into the 土台 sill. Its lower 50 mm "
    "runs on as a tenon into the sill, and the full-depth body stops against "
    "the sill face.",
    yaw=-90.0
)


# -- 6. floor post into sleeper --------------------------------------------
FLOORPOST_SLEEPER = detail(
    "floor-post-into-sleeper", "Floor post into sleeper", "床束の大引差し",
    [
        axis("part-a", "Sleeper", G.COLORS["sleeper"],
             (-0.75, 0.0, -0.045), (0.75, 0.09, 0.045),
             cuts=[G.box((-0.032, 0.0, -0.032), (0.032, 0.05, 0.032))]),
        axis("part-b", "Floor post", G.COLORS["sleeper"],
             (-0.045, -0.50, -0.045), (0.045, 0.0, 0.045),
             adds=[G.box((-0.03, 0.0, -0.03), (0.03, 0.05, 0.03))]),
    ],
    {"part-b": [0.0, -0.38, 0.0]},
    "The short 床束 floor post carries a 60 mm tenon up into the 大引 sleeper. "
    "The post body stops under the sleeper and the tenon fills the mortise, "
    "so the floor load passes straight down to the stone."
)


# -- 7. floor post on stone -------------------------------------------------
FLOORPOST_STONE = detail(
    "floor-post-on-stone", "Floor post on stone", "床束の礎石",
    [
        axis("part-a", "Floor stone", G.COLORS["stone"],
             (-0.09, -0.13, -0.09), (0.09, 0.0, 0.09)),
        axis("part-b", "Floor post", G.COLORS["sleeper"],
             (-0.045, 0.0, -0.045), (0.045, 0.45, 0.045)),
    ],
    {"part-b": [0.0, 0.38, 0.0]},
    "The 床束 floor post stands directly on its 礎石 stone. There is no "
    "tenon: the post bears on the dressed top, and the stone carries the load "
    "into the ground."
)


# -- 8. sleeper into sill ---------------------------------------------------
SLEEPER_SILL = detail(
    "sleeper-into-sill", "Sleeper into sill", "大引の土台差し",
    [
        axis("part-a", "Sill", G.COLORS["sill"],
             (-0.06, 0.0, -0.75), (0.06, 0.12, 0.75),
             cuts=[G.box((-0.061, 0.015, -0.045), (0.03, 0.105, 0.045))]),
        axis("part-b", "Sleeper", G.COLORS["sleeper"],
             (-0.75, 0.015, -0.045), (0.03, 0.105, 0.045)),
    ],
    {"part-b": [-0.40, 0.0, 0.0]},
    "The 大引 sleeper end is housed into the end 土台 sill. The sleeper runs "
    "90 mm into the 120 mm sill, leaving a 30 mm wall of sill beyond it, and "
    "the shoulders sit against the sill face."
)


# -- 9. upper joist half-lap -----------------------------------------------
UPPER_JOIST_BEAM = detail(
    "upper-joist-half-lap", "Upper joist half-lap", "二階根太の相欠き",
    [
        axis("part-a", "Spine beam", G.COLORS["floor"],
             (-0.75, 0.0, -0.06), (0.75, 0.18, 0.06),
             cuts=[G.box((-0.03, 0.12, -0.061), (0.03, 0.18, 0.061))]),
        axis("part-b", "Upper joist", G.COLORS["joist"],
             (-0.03, 0.06, -0.75), (0.03, 0.18, 0.75),
             cuts=[G.box((-0.03, 0.06, -0.045), (0.03, 0.12, 0.045))]),
    ],
    {"part-b": [0.0, 0.40, 0.0]},
    "The upper 根太 is halved over the 床梁 spine beam: 60 mm out of the beam "
    "top and 60 mm out of the joist underside, so the joist top finishes "
    "flush with the beam and the two share a bearing plane."
)


# -- 10. upper joist into girder -------------------------------------------
UPPER_JOIST_GIRDER = detail(
    "upper-joist-into-girder", "Upper joist into girder",
    "二階根太の胴差差し",
    [
        axis("part-a", "Girder", G.COLORS["beam"],
             (-0.75, 0.0, -0.06), (0.75, 0.18, 0.06),
             cuts=[G.box((-0.03, 0.06, -0.061), (0.03, 0.18, -0.03))]),
        axis("part-b", "Upper joist", G.COLORS["joist"],
             (-0.03, 0.06, -0.75), (0.03, 0.18, -0.06),
             adds=[G.box((-0.03, 0.06, -0.06), (0.03, 0.18, -0.03))]),
    ],
    {"part-b": [0.0, 0.0, -0.42]},
    "The upper 根太 end is housed 30 mm into the 胴差 girder. The joist body "
    "stops at the girder face and a full-section stub runs into the shallow "
    "housing, with the girder left whole beyond it.",
    yaw=-90.0
)


# -- 11. purlin under hip ---------------------------------------------------
PURLIN_HIP = detail(
    "purlin-under-hip", "Purlin under hip", "母屋と隅木",
    [
        axis("part-a", "Purlin", G.COLORS["purlin"],
             (-0.75, 0.0, -0.06), (0.75, 0.12, 0.06)),
        oriented("part-b", "Hip rafter", G.COLORS["rafter"],
                 (-0.30, -0.0805, -0.56), (0.70, 0.4195, 0.44),
                 0.09, 0.105, up=(0.0, 1.0, 0.0)),
    ],
    {"part-b": [0.18, 0.36, 0.18]},
    "The 母屋 purlin crosses under the 隅木 hip rafter where their lines meet "
    "in plan. The hip bears on the purlin top and runs on down the slope; the "
    "purlin carries the hip at the crossing.",
    yaw=-45.0
)


# -- 12. hip into ridge -----------------------------------------------------
RIDGE_HIP = detail(
    "hip-into-ridge", "Hip into ridge", "隅木と棟木",
    [
        axis("part-a", "Ridge", G.COLORS["roof"],
             (-0.75, 0.0, -0.075), (0.0, 0.15, 0.075)),
        trim(oriented("part-b", "Hip rafter", G.COLORS["rafter"],
                      (0.0, 0.075, 0.0), (0.80, -0.25, 0.80),
                      0.09, 0.105, up=(0.0, 1.0, 0.0)),
             (0.0, 0.0, 0.0), (1.0, 0.0, 0.0), keep_le=False),
    ],
    {"part-b": [0.42, -0.12, 0.42]},
    "The 隅木 hip butts the end of the 棟木 ridge. Its end is cut square to "
    "the ridge's end face, so the two meet on a vertical plane and the hip "
    "runs down the corner of the roof from there.",
    yaw=-45.0
)


# -- 13. hip over plate -----------------------------------------------------
HIP_PLATE_PIECES = corner_plates(G.COLORS["beam"])
HIP_PLATE_PIECES.append(
    oriented("part-c", "Hip rafter", G.COLORS["rafter"],
             (0.0, 0.10070, 0.0), (0.70, 0.45070, 0.70),
             0.09, 0.105, up=(0.0, 1.0, 0.0)))

HIP_PLATE = detail(
    "hip-over-plate", "Hip over plate", "隅木と軒桁",
    HIP_PLATE_PIECES,
    {"part-c": [0.18, 0.36, 0.18]},
    "The 隅木 hip passes over the corner where the two 軒桁 plates meet. The "
    "plates are halved into each other at the corner, and the hip bears on "
    "the top, carrying the roof plane out over the eave.",
    yaw=-45.0
)


# -- 14. rafter at ridge ----------------------------------------------------
RAFTER_RIDGE = detail(
    "rafter-at-ridge", "Rafter at ridge", "垂木と棟木",
    [
        axis("part-a", "Ridge", G.COLORS["roof"],
             (-0.75, 0.0, -0.075), (0.75, 0.15, 0.075)),
        trim(oriented("part-b", "Rafter", G.COLORS["rafter"],
                      (0.0, -0.26, -0.78), (0.0, 0.1095, -0.02),
                      0.045, 0.09, up=(0.0, 1.0, 0.0)),
             (0.0, 0.0, -0.075), (0.0, 0.0, 1.0), keep_le=True),
    ],
    {"part-b": [0.0, -0.15, -0.42]},
    "The common 垂木 butts the side of the 棟木 ridge at the top of the slope. "
    "Its end is cut square to the ridge face, and the ridge runs on past the "
    "pair of rafters on either side.",
    yaw=-90.0
)


# -- 15. rafter at hip ------------------------------------------------------
HIP_LINE = ((-0.60, -0.10, -0.60), (0.60, 0.50, 0.60))
HIP_SIDE = G.norm(G.cross((0.0, 1.0, 0.0), G.sub(HIP_LINE[1], HIP_LINE[0])))
HIP_POINT = [HIP_LINE[0][k] + 0.045 * HIP_SIDE[k] for k in range(3)]

RAFTER_HIP = detail(
    "rafter-at-hip", "Rafter at hip", "垂木と隅木",
    [
        oriented("part-a", "Hip rafter", G.COLORS["rafter"],
                 HIP_LINE[0], HIP_LINE[1], 0.09, 0.105, up=(0.0, 1.0, 0.0)),
        trim(oriented("part-b", "Rafter", G.COLORS["rafter"],
                      (0.0, -0.26, -0.78), (0.0, 0.34, 0.12),
                      0.045, 0.09, up=(0.0, 1.0, 0.0)),
             HIP_POINT, HIP_SIDE, keep_le=False),
    ],
    {"part-b": [0.0, -0.12, -0.42]},
    "The common 垂木 is cut square against the 隅木 hip rafter. The hip runs "
    "diagonally down the corner and the rafter end meets its side, so the "
    "rafters step down the hip with square cuts rather than crossing it.",
    yaw=-45.0
)


# -- 16. rafter over purlin -------------------------------------------------
RAFTER_PURLIN = detail(
    "rafter-over-purlin", "Rafter over purlin", "垂木と母屋",
    [
        axis("part-a", "Purlin", G.COLORS["purlin"],
             (-0.75, 0.0, -0.06), (0.75, 0.12, 0.06)),
        seated_rafter("part-b", "Rafter", G.COLORS["rafter"],
                      (0.0, -0.1342, -0.75), (0.0, 0.4658, 0.75),
                      0.045, 0.09, 0.120, -0.06, -0.01),
    ],
    {"part-b": [0.0, 0.38, 0.0]},
    "A 鳥口 birdsmouth seats the 垂木 rafter over the 母屋 purlin. At this "
    "4寸 (0.4) roof slope the notch has a 50 mm horizontal seat on the purlin "
    "top and a 20 mm plumb cheek at its lower end, the usual 立水 : 座 = 2 : 5 "
    "proportion, so the rafter cannot slide down the slope.",
    yaw=90.0
)


# -- 17. rafter over plate --------------------------------------------------
RAFTER_PLATE = detail(
    "rafter-over-plate", "Rafter over plate", "垂木と軒桁",
    [
        axis("part-a", "Plate", G.COLORS["beam"],
             (-0.75, 0.0, -0.06), (0.75, 0.12, 0.06)),
        seated_rafter("part-b", "Rafter", G.COLORS["rafter"],
                      (0.0, -0.1342, -0.75), (0.0, 0.4658, 0.75),
                      0.045, 0.09, 0.120, -0.06, -0.01),
    ],
    {"part-b": [0.0, 0.38, 0.0]},
    "The 垂木 rafter is notched over the 軒桁 plate at the eave with the same "
    "4寸 birdsmouth: a 50 mm horizontal seat and a 20 mm plumb cheek, with the "
    "rafter running on past the plate to the eave edge.",
    yaw=90.0
)


# -- 18. jack rafter at hip -------------------------------------------------
JACK_HIP = detail(
    "jack-rafter-at-hip", "Jack rafter at hip", "短垂木と隅木",
    [
        oriented("part-a", "Hip rafter", G.COLORS["rafter"],
                 HIP_LINE[0], HIP_LINE[1], 0.09, 0.105, up=(0.0, 1.0, 0.0)),
        trim(oriented("part-b", "Jack rafter", G.COLORS["rafter"],
                      (0.0, -0.26, -0.72), (0.0, 0.34, 0.12),
                      0.045, 0.09, up=(0.0, 1.0, 0.0)),
             HIP_POINT, HIP_SIDE, keep_le=False),
    ],
    {"part-b": [0.0, -0.12, -0.42]},
    "A 短垂木 jack rafter is cut square against the 隅木 hip. It is shorter "
    "than the common rafters because it starts at the hip and stops at the "
    "next purlin or at the eave.",
    yaw=-45.0
)


# -- 19. jack rafter over plate --------------------------------------------
JACK_PLATE = detail(
    "jack-rafter-over-plate", "Jack rafter over plate", "短垂木と軒桁",
    [
        axis("part-a", "Plate", G.COLORS["beam"],
             (-0.75, 0.0, -0.06), (0.75, 0.12, 0.06)),
        seated_rafter("part-b", "Jack rafter", G.COLORS["rafter"],
                      (0.0, -0.1342, -0.75), (0.0, 0.3738, 0.52),
                      0.045, 0.09, 0.120, -0.06, -0.01),
    ],
    {"part-b": [0.0, 0.38, 0.0]},
    "At the hipped end a 短垂木 jack rafter is notched over the 軒桁 plate with "
    "a 鳥口 birdsmouth. The plate carries the jack rafter where it meets the "
    "eave, and the rafter stops against the hip above.",
    yaw=90.0
)


DETAILS = [
    SILL_CORNER, BRACE_POST, FIRE_BEAM, JOIST_HALF_LAP, JOIST_SILL,
    FLOORPOST_SLEEPER, FLOORPOST_STONE, SLEEPER_SILL, UPPER_JOIST_BEAM,
    UPPER_JOIST_GIRDER, PURLIN_HIP, RIDGE_HIP, HIP_PLATE, RAFTER_RIDGE,
    RAFTER_HIP, RAFTER_PURLIN, RAFTER_PLATE, JACK_HIP, JACK_PLATE,
]


def round_points(level):
    """Keep every vertex on the 1 µm grid the sources and checks use.

    Sloped members map local grid points through an irrational frame, so their
    coordinates carry long decimal tails.  The checker keys vertices at six
    decimals, and a tailed vertex can look like a separate point sitting a
    fraction of a micron along its own edge.  Rounding here keeps the stored
    geometry and the checker's keys identical.
    """
    for p in level["pieces"]:
        for s in p["solids"]:
            for f in s["faces"]:
                f["points"] = [[round(c, 6) for c in q] for q in f["points"]]


def main(argv):
    want = set(argv[1:])
    os.makedirs(SOURCES, exist_ok=True)
    for j in DETAILS:
        if want and j["id"] not in want:
            continue
        round_points(j)
        path = os.path.join(SOURCES, j["id"] + ".json")
        with open(path, "w") as fh:
            json.dump([j], fh, indent=1)
        faces = sum(len(s["faces"]) for p in j["pieces"] for s in p["solids"])
        print("%-30s %d pieces %4d faces -> %s"
              % (j["id"], len(j["pieces"]), faces, path))


if __name__ == "__main__":
    main(sys.argv)
