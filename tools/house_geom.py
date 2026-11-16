#!/usr/bin/env python3
"""Geometry helpers for the house frame in tools/author_house.py.

The house uses the same face schema as the joint sources.  Axis-aligned
members are built directly by author_joint.compile_solid; braces, rafters and
hip rafters are built in a local member frame (x along the member, y across,
z through the section) and transformed into place.
"""
import math

from author_joint import compile_solid, loft

# ---- palette (display sRGB; export.py shades and linearises) -------------
COLORS = {
    "post": (0.66, 0.39, 0.29),
    "beam": (0.74, 0.48, 0.35),
    "sill": (0.55, 0.33, 0.25),
    "brace": (0.80, 0.58, 0.42),
    "nuki": (0.69, 0.41, 0.30),
    "wedge": (0.38, 0.26, 0.18),
    "roof": (0.52, 0.57, 0.34),
    "rafter": (0.63, 0.68, 0.40),
    "purlin": (0.45, 0.51, 0.29),
    "floor": (0.43, 0.53, 0.61),
    "joist": (0.55, 0.65, 0.72),
    "sleeper": (0.37, 0.46, 0.54),
    "base": (0.70, 0.67, 0.62),
    "stone": (0.55, 0.53, 0.49),
    "ground": (0.80, 0.76, 0.70),
}

# ---- dimensions ----------------------------------------------------------
KEN = 1.82
NX, NZ = 3, 2
W, D = NX * KEN, NZ * KEN
XS = [-W / 2 + i * KEN for i in range(NX + 1)]
ZS = [-D / 2 + i * KEN for i in range(NZ + 1)]

POST = 0.12
STUD = 0.105
SILL = 0.12
GIRD = 0.18
BEAM = 0.24
SLEEPER = 0.09
JOIST = 0.06
BRACE = 0.09
FIRE = 0.09
RAFTER_W, RAFTER_H = 0.045, 0.09
PURLIN = 0.12
RIDGE = 0.15

FOUND_TOP = 0.45
SILL_TOP = 0.57
FLOOR_TOP = SILL_TOP + JOIST       # 0.63
F1 = SILL_TOP + 2.70               # top of the 2nd-floor beams, 3.27
F2 = F1 + 2.70                     # top of the wall plate, 5.97
EAVE_EDGE = F2                     # outer end of the rafters at the eave
OVERHANG = 0.60
ROOF_RUN = D / 2 + OVERHANG        # 2.42
RIDGE_TOP = 7.90
ROOF_RISE = RIDGE_TOP - EAVE_EDGE
WALL_TOP = EAVE_EDGE + (OVERHANG / ROOF_RUN) * ROOF_RISE - RAFTER_H
PURLIN_Z = KEN / 2                 # 0.91
PURLIN_TOP = (EAVE_EDGE + ((ROOF_RUN - PURLIN_Z) / ROOF_RUN) * ROOF_RISE
              - RAFTER_H)
BEAM2_TOP = WALL_TOP - GIRD        # 6.178, underside of the 軒桁
ROOF_SLOPE = ROOF_RISE / ROOF_RUN
NUKI_H = 0.105
NUKI_W = 0.12
TENON = 0.055                      # depth of a housed beam tenon


def norm(v):
    l = math.sqrt(sum(c * c for c in v)) or 1.0
    return [c / l for c in v]


def cross(a, b):
    return [a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


def add(a, b):
    return [a[i] + b[i] for i in range(3)]


def sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def mul(a, k):
    return [c * k for c in a]


def box(lo, hi):
    return ((lo[0], hi[0]), (lo[1], hi[1]), (lo[2], hi[2]))


def around(c, size):
    """Axis-aligned box of side `size` (a scalar or 3-list) around centre c."""
    s = [size] * 3 if isinstance(size, (int, float)) else list(size)
    return box([c[i] - s[i] / 2 for i in range(3)],
               [c[i] + s[i] / 2 for i in range(3)])


def tint(faces, color):
    for f in faces:
        f["color"] = list(color)
    return faces


def piece(pid, name, group, color, faces, extra=()):
    solids = [{"faces": tint(faces, color)}]
    if extra:
        solids.append({"faces": tint(extra, color)})
    return {"id": pid, "name": name, "kind": "timber", "group": group,
            "solids": solids}


def axis_piece(pid, name, group, color, lo, hi, cuts=(), adds=(), extra=()):
    faces = compile_solid([box(lo, hi)] + list(adds), list(cuts))
    return piece(pid, name, group, color, faces, extra)


def oriented_piece(pid, name, group, color, p0, p1, w, h,
                   cuts=(), adds=(), up=(0.0, 1.0, 0.0), extra=()):
    """A rectangular member between p0 and p1, with a local CSG section.

    Local x runs from p0 to p1; local y and z are the cross-section axes.  A
    cut or add box is ((x0,x1),(y0,y1),(z0,z1)) in that local frame.
    """
    d = sub(p1, p0)
    L = math.sqrt(sum(c * c for c in d))
    ex = norm(d)
    side = norm(cross(up, ex))
    ez = cross(ex, side)
    main = ((0.0, L), (-w / 2, w / 2), (-h / 2, h / 2))
    faces = compile_solid([main] + list(adds), list(cuts))

    def pt(q):
        return [p0[i] + q[0] * ex[i] + q[1] * side[i] + q[2] * ez[i]
                for i in range(3)]

    for f in faces:
        f["points"] = [pt(q) for q in f["points"]]
        n = f["normal"]
        f["normal"] = [n[0] * ex[i] + n[1] * side[i] + n[2] * ez[i]
                       for i in range(3)]
    # Extra faces (wedges, pegs) are supplied in world coordinates, the same
    # as axis_piece, so they are appended unchanged.
    return piece(pid, name, group, color, faces, extra)


def local_wedge(axis, a, b, sec_a, sec_b, color=None):
    """A lofted wedge in world coordinates (axis 0/1/2)."""
    return loft(axis, a, b, sec_a, sec_b,
                color=color or COLORS["wedge"])


def world_wedge(a, b, sec_a, sec_b, color=None):
    """Alias for loft, kept for readability in the frame code."""
    return local_wedge(a, b, sec_a, sec_b, color)
