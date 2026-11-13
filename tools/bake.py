"""Bake a sunset light rig (warm low sun, cool sky ambient, cast shadows, AO)
into per-vertex colours and write unlit GLBs.

The app's assets are flat per-face colours. Here every face is subdivided into
a fine grid so shadow boundaries and occlusion gradients have vertices to land
on; each grid vertex gets its own display-sRGB colour, which is then linearised
for glTF COLOR_0. The output is meant for KHR_materials_unlit: the look is
static and viewer-independent.

Lighting is evaluated in display sRGB (like the app's own CPU shading):
    color = base * (ambient(n) * ao + sun * max(0, n.L) * visibility)
`visibility` is a ray cast towards the sun and `ao` a short hemisphere ray cast.
"""
import json, math, os, sys, argparse

from export import Mesh, write_glb, safe, newell, norm, srgb_to_linear


def linear_to_srgb(c):
    c = max(0.0, min(1.0, float(c)))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


# ---------------------------------------------------------------- light rig --
# High-key paper-sunrise look, matching the reference's face contrast: a
# bright cream sky fills from above, while a soft sun 61 degrees up and from
# the front-left (the app's own light direction) gives the strong vertical-face
# falloff seen in the screenshot. Shadows stay short and soft. The flat red
# disk in the preview is a graphic element, not the light direction.
AZ = math.radians(144.5)
EL = math.radians(48.0)
SUN = (math.cos(EL) * math.cos(AZ), math.sin(EL), math.cos(EL) * math.sin(AZ))
SUN_RGB = (1.00, 0.96, 0.90)     # pale warm direct light
SUN_I = 0.30
SKY_RGB = (0.88, 0.85, 0.80)     # cream sky fill, slightly warm
BOUNCE_RGB = (0.60, 0.60, 0.58)  # neutral side fill, dimmer than the sky
AMB_I = 0.88
AO_MIN = 0.80                    # keep contact shadows light and pastel
SUN_RAYS = 24                    # piece soft-shadow samples
SUN_RADIUS = 0.004               # penumbra scale (world units)
AO_RAYS = 8
AO_DIST = 0.55

# Paper wash: the reference is a low-contrast illustration, so lift and
# desaturate the final display colour very slightly.
PAPER = (0.945, 0.905, 0.835)
HAZE = 0.03
DESAT = 0.07

# The garden top is the shadow receiver, so it gets a denser sample budget and
# a small blur of the baked light field; that removes the visible contour steps
# left by per-vertex hit fractions.
GROUND_SUN_RAYS = 48
GROUND_AO_RAYS = 20
GROUND_AO_DIST = 0.09            # tight contact darkening only
GROUND_AO_STRENGTH = 0.40        # how much of the AO dip reaches the light
GROUND_BLUR = 0                  # gaussian radius in grid cells
GROUND_BLUR_SIGMA = 0.45

# The garden top is nearly white paper in the reference and its shadows are a
# gentle multiply, so it gets its own light term (calibrated against the
# screenshot: lit paper 253/246/233, shadow 212/206/202) instead of the
# stronger piece rig.
GROUND_AMB = (0.840, 0.840, 0.877)
GROUND_SUN = (0.168, 0.169, 0.138)

GRASS_TOP = (0.55, 0.65, 0.42)
GRASS_SIDE = (0.62, 0.60, 0.58)
GRAVEL_TOP = (0.99, 0.96, 0.90)
GRAVEL_SIDE = (0.827, 0.790, 0.726)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def unit(v):
    l = math.sqrt(dot(v, v))
    return (v[0] / l, v[1] / l, v[2] / l) if l > 1e-12 else (0.0, 1.0, 0.0)


def basis(n):
    t = (1.0, 0.0, 0.0) if abs(n[0]) < 0.9 else (0.0, 1.0, 0.0)
    u = unit(cross(t, n))
    v = cross(n, u)
    return u, v


# ---------------------------------------------------------------------- BVH --
def _slab(o, d, bmin, bmax, tmax):
    t0 = 0.0
    t1 = tmax
    for k in range(3):
        if abs(d[k]) < 1e-12:
            if o[k] < bmin[k] or o[k] > bmax[k]:
                return False
        else:
            inv = 1.0 / d[k]
            ta = (bmin[k] - o[k]) * inv
            tb = (bmax[k] - o[k]) * inv
            if ta > tb:
                ta, tb = tb, ta
            if ta > t0:
                t0 = ta
            if tb < t1:
                t1 = tb
            if t0 > t1:
                return False
    return True


def _ray_tri(o, d, a, b, c, tmax):
    e1 = sub(b, a)
    e2 = sub(c, a)
    p = cross(d, e2)
    det = dot(e1, p)
    if abs(det) < 1e-12:
        return False
    inv = 1.0 / det
    tv = sub(o, a)
    u = dot(tv, p) * inv
    if u < 0.0 or u > 1.0:
        return False
    q = cross(tv, e1)
    v = dot(d, q) * inv
    if v < 0.0 or u + v > 1.0:
        return False
    t = dot(e2, q) * inv
    return 1e-6 < t < tmax


class BVH:
    def __init__(self, tris, face_of=None):
        self.tris = tris
        self.face_of = face_of
        self.order = list(range(len(tris)))
        self.nodes = []
        if tris:
            self._build(0, len(tris), 4)

    def _build(self, lo, hi, leaf):
        idx = len(self.nodes)
        self.nodes.append(None)
        bmin = [1e30, 1e30, 1e30]
        bmax = [-1e30, -1e30, -1e30]
        for k in range(lo, hi):
            for p in self.tris[self.order[k]]:
                for i in range(3):
                    if p[i] < bmin[i]:
                        bmin[i] = p[i]
                    if p[i] > bmax[i]:
                        bmax[i] = p[i]
        if hi - lo <= leaf:
            self.nodes[idx] = (bmin, bmax, -1, -1, lo, hi)
            return idx
        cmin = [1e30] * 3
        cmax = [-1e30] * 3
        cen = {}
        for k in range(lo, hi):
            ti = self.order[k]
            a, b, c = self.tris[ti]
            m = ((a[0] + b[0] + c[0]) / 3.0,
                 (a[1] + b[1] + c[1]) / 3.0,
                 (a[2] + b[2] + c[2]) / 3.0)
            cen[ti] = m
            for i in range(3):
                cmin[i] = min(cmin[i], m[i])
                cmax[i] = max(cmax[i], m[i])
        axis = max(range(3), key=lambda i: cmax[i] - cmin[i])
        self.order[lo:hi] = sorted(self.order[lo:hi], key=lambda ti: cen[ti][axis])
        mid = (lo + hi) // 2
        left = self._build(lo, mid, leaf)
        right = self._build(mid, hi, leaf)
        self.nodes[idx] = (bmin, bmax, left, right, 0, 0)
        return idx

    def any_hit(self, o, d, tmax, skip_face=-1):
        stack = [0]
        nodes = self.nodes
        tris = self.tris
        order = self.order
        face_of = self.face_of
        while stack:
            bmin, bmax, left, right, lo, hi = nodes[stack.pop()]
            if not _slab(o, d, bmin, bmax, tmax):
                continue
            if left < 0:
                for k in range(lo, hi):
                    ti = order[k]
                    if face_of is not None and face_of[ti] == skip_face:
                        continue
                    if _ray_tri(o, d, *tris[ti], tmax):
                        return True
            else:
                stack.append(left)
                stack.append(right)
        return False


# ------------------------------------------------------------------ shading --
_ao_cache = {}
_GOLDEN = math.pi * (3.0 - math.sqrt(5.0))


def _ao_directions(count):
    dirs = _ao_cache.get(count)
    if dirs is None:
        dirs = []
        for i in range(count):
            r = math.sqrt((i + 0.5) / count)
            phi = i * _GOLDEN
            dirs.append((r * math.cos(phi), r * math.sin(phi),
                         math.sqrt(max(0.0, 1.0 - r * r))))
        _ao_cache[count] = dirs
    return dirs


def sun_visibility(bvh, p, n, skip, rays=None):
    rays = SUN_RAYS if rays is None else rays
    o = (p[0] + n[0] * 2e-4, p[1] + n[1] * 2e-4, p[2] + n[2] * 2e-4)
    if rays <= 1:
        return 0.0 if bvh.any_hit(o, SUN, 1e30, skip) else 1.0
    # Sample the sun's disk (not just its rim): a ring of point lights produces
    # a penumbra with one lobe per sample, which reads as several suns.
    u, v = basis(SUN)
    hits = 0
    for k in range(rays):
        r = SUN_RADIUS * math.sqrt((k + 0.5) / rays)
        ang = k * _GOLDEN
        off = (r * (math.cos(ang) * u[0] + math.sin(ang) * v[0]),
               r * (math.cos(ang) * u[1] + math.sin(ang) * v[1]),
               r * (math.cos(ang) * u[2] + math.sin(ang) * v[2]))
        d = unit((SUN[0] + off[0], SUN[1] + off[1], SUN[2] + off[2]))
        if not bvh.any_hit(o, d, 1e30, skip):
            hits += 1
    return hits / float(rays)


def ambient_occlusion(bvh, p, n, skip, rays=None, dist=None):
    rays = AO_RAYS if rays is None else rays
    dist = AO_DIST if dist is None else dist
    if rays <= 0:
        return 1.0
    u, v = basis(n)
    o = (p[0] + n[0] * 2e-4, p[1] + n[1] * 2e-4, p[2] + n[2] * 2e-4)
    open_ = 0
    for lx, ly, lz in _ao_directions(rays):
        d = (u[0] * lx + v[0] * ly + n[0] * lz,
             u[1] * lx + v[1] * ly + n[1] * lz,
             u[2] * lx + v[2] * ly + n[2] * lz)
        if not bvh.any_hit(o, d, dist, skip):
            open_ += 1
    return AO_MIN + (1.0 - AO_MIN) * open_ / float(rays)


def light_term(n, vis, ao):
    up = 0.5 + 0.5 * n[1]
    ndl = max(0.0, dot(n, SUN))
    return tuple((SKY_RGB[i] * up + BOUNCE_RGB[i] * (1.0 - up)) * AMB_I * ao
                 + SUN_RGB[i] * SUN_I * ndl * vis
                 for i in range(3))


def ground_light(vis, ao):
    # The reference paints a hard cut between lit paper and shadow, so collapse
    # the residual penumbra the ray sampling leaves behind.
    vis = 0.0 if vis <= 0.34 else (1.0 if vis >= 0.66 else (vis - 0.34) / 0.32)
    ao_eff = (1.0 - GROUND_AO_STRENGTH) + GROUND_AO_STRENGTH * ao
    return tuple(GROUND_AMB[i] * ao_eff + GROUND_SUN[i] * vis
                 for i in range(3))


def grade(base, k):
    c = [max(0.0, min(1.0, base[i] * k[i])) for i in range(3)]
    luma = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    out = []
    for i in range(3):
        v = c[i] * (1.0 - DESAT) + luma * DESAT
        v = v * (1.0 - HAZE) + PAPER[i] * HAZE
        out.append(max(0.0, min(1.0, v)))
    return tuple(out)


PIECE_DESAT = 0.40               # paper-wash: pull the wood towards taupe


def paper_base(base):
    """Pull a material colour towards its own luma. The reference model paints
    the wood as muted taupe rather than the app's saturated timber."""
    bl = 0.2126 * base[0] + 0.7152 * base[1] + 0.0722 * base[2]
    return tuple((base[i] * (1.0 - PIECE_DESAT) + bl * PIECE_DESAT) * 0.96
                 for i in range(3))


def shade(base, n, vis, ao):
    return grade(base, light_term(n, vis, ao))


# ------------------------------------------------------------------ grain --
# The reference has visible material grain: wood mottling, sand/gravel speckle
# and stone courses. Everything is baked into the vertex colours, so it stays
# static and unlit like the rest of the shading.
def _hash01(ix, iy, iz, seed=0):
    h = (ix * 374761393 + iy * 668265263 + iz * 1440662683 +
         seed * 1013904223) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return h / 4294967295.0


def _speckle(p, cell, amp, seed=0):
    ix = int(math.floor(p[0] / cell))
    iy = int(math.floor(p[1] / cell))
    iz = int(math.floor(p[2] / cell))
    return 1.0 + amp * (_hash01(ix, iy, iz, seed) - 0.5) * 2.0


def _mottle(p):
    x, y, z = p
    v = (math.sin(x * 2.7 + y * 1.3 + z * 1.9) +
         math.sin(x * 5.1 - y * 3.7 + z * 2.3 + 1.7) +
         math.sin(x * 1.1 + y * 4.3 - z * 3.1 + 0.6)) / 3.0
    return 1.0 + 0.022 * v


# Painted border strips: a real thin band of geometry at each face border,
# constant colour, so the outline stays crisp instead of fading across a
# subdivided triangle.
EDGE_STRIP_W = 0.007
EDGE_STRIP_DARK = 0.22
EDGE_STRIP_LIFT = 0.0012


def _edge_key(a, b):
    ka = (round(a[0], 4), round(a[1], 4), round(a[2], 4))
    kb = (round(b[0], 4), round(b[1], 4), round(b[2], 4))
    return (ka, kb) if ka <= kb else (kb, ka)


def coplanar_seams(faces):
    """Map face index -> edge keys that sit inside a flat surface, so the
    painted border only outlines real creases and silhouettes."""
    emap = {}
    for fi, f in enumerate(faces):
        pts = [tuple(float(x) for x in p) for p in f["points"]]
        if len(pts) < 3:
            continue
        given = f.get("normal")
        n = norm(tuple(float(x) for x in given)) if given else norm(newell(pts))
        for i in range(len(pts)):
            k = _edge_key(pts[i], pts[(i + 1) % len(pts)])
            emap.setdefault(k, []).append((fi, n))
    skip = {}
    for k, lst in emap.items():
        if len(lst) < 2:
            continue
        for fi, n in lst:
            for fj, m in lst:
                if fj != fi and dot(n, m) > 0.995:
                    skip.setdefault(fi, set()).add(k)
                    break
    return skip


def _add_edge_strips(m, pts, n, base, bvh, face_id, skip_edges=(),
                     dark=None, width=None, lift=None):
    if len(pts) < 3:
        return
    dark = EDGE_STRIP_DARK if dark is None else dark
    width = EDGE_STRIP_W if width is None else width
    lift = EDGE_STRIP_LIFT if lift is None else lift
    nv = float(len(pts))
    cen = (sum(p[0] for p in pts) / nv, sum(p[1] for p in pts) / nv,
           sum(p[2] for p in pts) / nv)
    vis = sun_visibility(bvh, cen, n, face_id)
    ao = ambient_occlusion(bvh, cen, n, face_id)
    b = tuple(min(1.0, base[i] * (1.0 - dark)) for i in range(3))
    col = tuple(srgb_to_linear(x) for x in shade(b, n, vis, ao))

    for i in range(len(pts)):
        a = pts[i]
        c = pts[(i + 1) % len(pts)]
        if _edge_key(a, c) in skip_edges:
            continue
        mx = 0.5 * (a[0] + c[0])
        my = 0.5 * (a[1] + c[1])
        mz = 0.5 * (a[2] + c[2])
        ix, iy, iz = cen[0] - mx, cen[1] - my, cen[2] - mz
        dn = ix * n[0] + iy * n[1] + iz * n[2]
        ix, iy, iz = ix - dn * n[0], iy - dn * n[1], iz - dn * n[2]
        L = math.sqrt(ix * ix + iy * iy + iz * iz)
        if L < 1e-9:
            continue
        ix, iy, iz = ix / L, iy / L, iz / L
        ox, oy, oz = n[0] * lift, n[1] * lift, n[2] * lift
        p0 = (a[0] + ox, a[1] + oy, a[2] + oz)
        p1 = (c[0] + ox, c[1] + oy, c[2] + oz)
        p2 = (c[0] + ox + ix * width, c[1] + oy + iy * width,
              c[2] + oz + iz * width)
        p3 = (a[0] + ox + ix * width, a[1] + oy + iy * width,
              a[2] + oz + iz * width)
        for tri in ((p0, p1, p2), (p0, p2, p3)):
            u = (tri[1][0] - tri[0][0], tri[1][1] - tri[0][1],
                 tri[1][2] - tri[0][2])
            v = (tri[2][0] - tri[0][0], tri[2][1] - tri[0][1],
                 tri[2][2] - tri[0][2])
            tn = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2],
                  u[0] * v[1] - u[1] * v[0])
            if dot(tn, n) < 0.0:
                tri = (tri[0], tri[2], tri[1])
            i0 = len(m.pos)
            for q in tri:
                m.pos.append(q)
                m.nrm.append(n)
                m.col.append(col)
            m.idx += [i0, i0 + 1, i0 + 2]


def _add_ground_strips(m, face, bvh, face_id, skip_edges=()):
    pts = [tuple(float(x) for x in p) for p in face["points"]]
    if len(pts) < 3:
        return
    n = tuple(float(x) for x in face["normal"])
    nv = float(len(pts))
    cen = (sum(p[0] for p in pts) / nv, sum(p[1] for p in pts) / nv,
           sum(p[2] for p in pts) / nv)
    base = tuple(float(x) for x in face["color"])
    vis = sun_visibility(bvh, cen, n, face_id, GROUND_SUN_RAYS)
    ao = ambient_occlusion(bvh, cen, n, face_id, GROUND_AO_RAYS,
                            GROUND_AO_DIST)
    b = tuple(min(1.0, base[i] * 0.60) for i in range(3))
    col = tuple(srgb_to_linear(x) for x in grade(b, ground_light(vis, ao)))
    for i in range(len(pts)):
        a = pts[i]
        c = pts[(i + 1) % len(pts)]
        if _edge_key(a, c) in skip_edges:
            continue
        mx = 0.5 * (a[0] + c[0])
        my = 0.5 * (a[1] + c[1])
        mz = 0.5 * (a[2] + c[2])
        ix, iy, iz = cen[0] - mx, cen[1] - my, cen[2] - mz
        dn = ix * n[0] + iy * n[1] + iz * n[2]
        ix, iy, iz = ix - dn * n[0], iy - dn * n[1], iz - dn * n[2]
        L = math.sqrt(ix * ix + iy * iy + iz * iz)
        if L < 1e-9:
            continue
        ix, iy, iz = ix / L, iy / L, iz / L
        ox, oy, oz = n[0] * EDGE_STRIP_LIFT, n[1] * EDGE_STRIP_LIFT, \
            n[2] * EDGE_STRIP_LIFT
        w = EDGE_STRIP_W
        p0 = (a[0] + ox, a[1] + oy, a[2] + oz)
        p1 = (c[0] + ox, c[1] + oy, c[2] + oz)
        p2 = (c[0] + ox + ix * w, c[1] + oy + iy * w, c[2] + oz + iz * w)
        p3 = (a[0] + ox + ix * w, a[1] + oy + iy * w, a[2] + oz + iz * w)
        for tri in ((p0, p1, p2), (p0, p2, p3)):
            u = (tri[1][0] - tri[0][0], tri[1][1] - tri[0][1],
                 tri[1][2] - tri[0][2])
            v = (tri[2][0] - tri[0][0], tri[2][1] - tri[0][1],
                 tri[2][2] - tri[0][2])
            tn = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2],
                  u[0] * v[1] - u[1] * v[0])
            if dot(tn, n) < 0.0:
                tri = (tri[0], tri[2], tri[1])
            i0 = len(m.pos)
            for q in tri:
                m.pos.append(q)
                m.nrm.append(n)
                m.col.append(col)
            m.idx += [i0, i0 + 1, i0 + 2]


def _brick_factor(p, n):
    """Subtle staggered stone courses on the garden sides."""
    y = p[1]
    s = p[0] * n[2] - p[2] * n[0]
    row_h, brick_w = 0.160, 0.520
    fy = y / row_h
    row = int(math.floor(fy))
    fy -= row
    dh = min(fy, 1.0 - fy) * row_h
    fs = s / brick_w + (0.5 if (row & 1) else 0.0)
    bi = int(math.floor(fs))
    fs -= bi
    dv = min(fs, 1.0 - fs) * brick_w
    f = 1.0
    f -= 0.065 * max(0.0, 1.0 - dh / 0.022)
    f -= 0.050 * max(0.0, 1.0 - dv / 0.020)
    f *= 1.0 + 0.05 * (_hash01(row, bi, 7, 23) - 0.5)
    # The reference plinth is darker towards the ground.
    depth = max(0.0, min(1.0, -y / 0.55))
    f *= 1.0 - 0.10 * depth
    return f


def _ground_grain(p, planks):
    g = _mottle(p) * _speckle(p, 0.020, 0.045, 9)
    if planks:
        pw = 0.115
        fx = p[0] / pw
        board = int(math.floor(fx))
        fx -= board
        d = min(fx, 1.0 - fx) * pw
        seam = max(0.0, 1.0 - d / 0.014)
        g *= 1.0 - 0.105 * seam
        # The reference planks are not all the same tone: each board carries a
        # little of its own warm/cool variation.
        g *= 1.0 + 0.022 * (_hash01(board, 3, 7, 31) - 0.5)
    return g


# --------------------------------------------------------------- subdivide --
def _fan(pts):
    return [(pts[0], pts[i], pts[i + 1]) for i in range(1, len(pts) - 1)]


def poly_area(pts):
    nx = ny = nz = 0.0
    for i in range(len(pts)):
        a = pts[i]
        b = pts[(i + 1) % len(pts)]
        nx += (a[1] - b[1]) * (a[2] + b[2])
        ny += (a[2] - b[2]) * (a[0] + b[0])
        nz += (a[0] - b[0]) * (a[1] + b[1])
    return 0.5 * math.sqrt(nx * nx + ny * ny + nz * nz)


# The app models carry a short tenon below the visible base (the stone posts
# and torii pillars have one). To sit a level on the garden, find the main
# footprint among the downward faces just above the lowest point and put that
# plane at y = 0; the tenon ends up buried below the turf.
CONTACT_BAND = 0.12
SINK = 0.002


def contact_shift(faces):
    if not faces:
        return 0.0
    min_y = min(q[1] for f in faces for q in f["points"])
    best_y = min_y
    best_a = -1.0
    for f in faces:
        n = f["normal"]
        if n[1] < -0.9:
            y = min(q[1] for q in f["points"])
            if y <= min_y + CONTACT_BAND:
                a = poly_area(f["points"])
                if a > best_a:
                    best_a, best_y = a, y
    return -(best_y + SINK)


def shift_face(face, dy):
    return dict(face, points=[(p[0], p[1] + dy, p[2])
                              for p in face["points"]])


def _surface_color(p, base, n, bvh, face_id, face_jitter, brick_n):
    vis = sun_visibility(bvh, p, n, face_id)
    ao = ambient_occlusion(bvh, p, n, face_id)
    g = face_jitter * _mottle(p) * _speckle(p, 0.030, 0.020, 5)
    if brick_n is not None:
        g *= _brick_factor(p, brick_n)
        # Stone reads a little sandier than the timber; only the garden sides
        # get this extra fine speckle.
        g *= _speckle(p, 0.024, 0.035, 21)
    tinted = tuple(min(1.0, base[i] * g) for i in range(3))
    return tuple(srgb_to_linear(x) for x in shade(tinted, n, vis, ao))


def _quad_dims(pts, detail):
    def d(a, b):
        return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 +
                         (a[2] - b[2]) ** 2)
    w = 0.5 * (d(pts[0], pts[1]) + d(pts[3], pts[2]))
    h = 0.5 * (d(pts[0], pts[3]) + d(pts[1], pts[2]))
    nu = int(min(512, max(1, math.ceil(w / max(detail, 1e-4)))))
    nv = int(min(512, max(1, math.ceil(h / max(detail, 1e-4)))))
    return nu, nv


def bake_quad(m, face, bvh, face_id, detail, skip_edges=()):
    """Rectangular grid for quad faces: thin planks keep their resolution
    along both axes instead of being squared on their longest edge."""
    pts = [tuple(float(x) for x in p) for p in face["points"]]
    given = tuple(float(x) for x in face["normal"])
    n = norm(given) if (given[0] or given[1] or given[2]) else norm(newell(pts))
    base = paper_base(tuple(float(x) for x in face["color"]))
    cen = (0.25 * (pts[0][0] + pts[1][0] + pts[2][0] + pts[3][0]),
           0.25 * (pts[0][1] + pts[1][1] + pts[2][1] + pts[3][1]),
           0.25 * (pts[0][2] + pts[1][2] + pts[2][2] + pts[3][2]))
    face_jitter = _speckle(cen, 0.31, 0.030, 11)
    brick_n = n if face.get("brick") else None
    nu, nv = _quad_dims(pts, detail)
    cache = {}
    vid = [[0] * (nu + 1) for _ in range(nv + 1)]
    p0, p1, p2, p3 = pts
    for j in range(nv + 1):
        v = j / nv
        for i in range(nu + 1):
            u = i / nu
            w00 = (1.0 - u) * (1.0 - v)
            w10 = u * (1.0 - v)
            w11 = u * v
            w01 = (1.0 - u) * v
            p = (p0[0] * w00 + p1[0] * w10 + p2[0] * w11 + p3[0] * w01,
                 p0[1] * w00 + p1[1] * w10 + p2[1] * w11 + p3[1] * w01,
                 p0[2] * w00 + p1[2] * w10 + p2[2] * w11 + p3[2] * w01)
            key = (round(p[0], 5), round(p[1], 5), round(p[2], 5))
            c = cache.get(key)
            if c is None:
                c = _surface_color(p, base, n, bvh, face_id, face_jitter,
                                   brick_n)
                cache[key] = c
            vid[j][i] = len(m.pos)
            m.pos.append(p)
            m.nrm.append(n)
            m.col.append(c)

    flip = dot((p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]),
               n) < 0.0
    for j in range(nv):
        for i in range(nu):
            a = vid[j][i]
            b = vid[j][i + 1]
            c = vid[j + 1][i]
            d = vid[j + 1][i + 1]
            if flip:
                m.idx += [a, b, c, b, d, c]
            else:
                m.idx += [a, c, b, b, c, d]

    _add_edge_strips(m, pts, n, base, bvh, face_id, skip_edges)


def bake_face(m, face, bvh, face_id, detail, skip_edges=()):
    """Bake one face into `m` as a barycentric grid per fan triangle."""
    pts = [tuple(float(x) for x in p) for p in face["points"]]
    if len(pts) < 3:
        return
    given = tuple(float(x) for x in face["normal"])
    n = norm(given) if (given[0] or given[1] or given[2]) else norm(newell(pts))
    base = paper_base(tuple(float(x) for x in face["color"]))
    maxedge = 0.0
    for i in range(len(pts)):
        d = sub(pts[i], pts[(i + 1) % len(pts)])
        maxedge = max(maxedge, math.sqrt(dot(d, d)))
    if face.get("grid"):
        N = int(min(512, max(1, face["grid"])))
    else:
        N = int(min(512, max(1, math.ceil(maxedge / max(detail, 1e-4)))))

    nv = float(len(pts))
    cen = (sum(p[0] for p in pts) / nv, sum(p[1] for p in pts) / nv,
           sum(p[2] for p in pts) / nv)
    face_jitter = _speckle(cen, 0.31, 0.030, 11)
    brick = bool(face.get("brick"))

    cache = {}
    vcache = {}

    def lcolor(p):
        key = (round(p[0], 5), round(p[1], 5), round(p[2], 5))
        c = cache.get(key)
        if c is None:
            vis = sun_visibility(bvh, p, n, face_id)
            ao = ambient_occlusion(bvh, p, n, face_id)
            g = face_jitter * _mottle(p) * _speckle(p, 0.030, 0.020, 5)
            if brick:
                g *= _brick_factor(p, n)
            tinted = tuple(min(1.0, base[i] * g) for i in range(3))
            c = tuple(srgb_to_linear(x) for x in shade(tinted, n, vis, ao))
            cache[key] = c
        return c

    def vid(p):
        key = (round(p[0], 5), round(p[1], 5), round(p[2], 5))
        i = vcache.get(key)
        if i is None:
            i = len(m.pos)
            m.pos.append(p)
            m.nrm.append(n)
            m.col.append(lcolor(p))
            vcache[key] = i
        return i

    for a, b, c in _fan(pts):
        grid = {}

        def vpos(i, j):
            key = (i, j)
            p = grid.get(key)
            if p is None:
                u = i / N
                v = j / N
                p = (a[0] + u * (b[0] - a[0]) + v * (c[0] - a[0]),
                     a[1] + u * (b[1] - a[1]) + v * (c[1] - a[1]),
                     a[2] + u * (b[2] - a[2]) + v * (c[2] - a[2]))
                grid[key] = p
            return p

        for i in range(N):
            for j in range(N - i):
                p00 = vpos(i, j)
                p10 = vpos(i + 1, j)
                p01 = vpos(i, j + 1)
                m.idx += [vid(p00), vid(p10), vid(p01)]
                if i + j + 1 < N:
                    p11 = vpos(i + 1, j + 1)
                    m.idx += [vid(p10), vid(p11), vid(p01)]

    _add_edge_strips(m, pts, n, base, bvh, face_id, skip_edges)


# ------------------------------------------------------------------- scene --
def ground_faces(lv):
    g = lv.get("garden") or {}
    h = float(g.get("half", 1.9))
    th = float(g.get("thickness", 0.5))
    turf = int(g.get("turf", 0))
    top = GRASS_TOP if turf else GRAVEL_TOP
    side = GRASS_SIDE if turf else GRAVEL_SIDE
    faces = [dict(points=[(-h, 0.0, -h), (h, 0.0, -h),
                          (h, 0.0, h), (-h, 0.0, h)],
                  normal=[0.0, 1.0, 0.0], color=list(top), fine=True)]
    edges = [((-h, -h), (h, -h), (0.0, 0.0, -1.0)),
             ((h, -h), (h, h), (1.0, 0.0, 0.0)),
             ((h, h), (-h, h), (0.0, 0.0, 1.0)),
             ((-h, h), (-h, -h), (-1.0, 0.0, 0.0))]
    for (px, pz), (qx, qz), nrm in edges:
        pts = [(px, 0.0, pz), (qx, 0.0, qz),
               (qx, -th, qz), (px, -th, pz)]
        wn = newell(pts)
        if dot(wn, nrm) < 0:
            pts.reverse()
        side_face = dict(points=pts, normal=list(nrm), color=list(side))
        if not turf:
            side_face["brick"] = True
        faces.append(side_face)
    return faces


def _gauss_kernel(radius, sigma):
    k = [math.exp(-(i * i) / (2.0 * sigma * sigma))
         for i in range(-radius, radius + 1)]
    s = sum(k)
    return [x / s for x in k]


def _blur_rows(rows, kernel):
    radius = len(kernel) // 2
    out = []
    for row in rows:
        n = len(row)
        blurred = []
        for i in range(n):
            r = g = b = 0.0
            for k, w in enumerate(kernel):
                j = i + k - radius
                if j < 0:
                    j = 0
                elif j >= n:
                    j = n - 1
                c = row[j]
                r += w * c[0]
                g += w * c[1]
                b += w * c[2]
            blurred.append((r, g, b))
        out.append(blurred)
    return out


def blur_field(field, radius, sigma):
    """Separable gaussian blur of a 2D list of 3-tuples (edge clamped)."""
    if radius <= 0:
        return
    kernel = _gauss_kernel(radius, sigma)
    rows = _blur_rows(field, kernel)
    nz = len(rows)
    nx = len(rows[0])
    cols = [[rows[j][i] for j in range(nz)] for i in range(nx)]
    cols = _blur_rows(cols, kernel)
    for j in range(nz):
        for i in range(nx):
            field[j][i] = cols[i][j]


def bake_ground_top(m, face, bvh, face_id, detail, planks=True,
                    skip_edges=()):
    """Regular grid + blurred light field: the shadow receiver needs a smooth
    gradient, not per-vertex hit fractions."""
    xs = [p[0] for p in face["points"]]
    zs = [p[2] for p in face["points"]]
    x0, x1 = min(xs), max(xs)
    z0, z1 = min(zs), max(zs)
    nx = max(1, int(math.ceil((x1 - x0) / max(detail, 1e-4))))
    nz = max(1, int(math.ceil((z1 - z0) / max(detail, 1e-4))))
    nrm = tuple(float(x) for x in face["normal"])
    y0 = float(face["points"][0][1])

    field = []
    for j in range(nz + 1):
        z = z0 + (z1 - z0) * j / nz
        row = []
        for i in range(nx + 1):
            p = (x0 + (x1 - x0) * i / nx, y0, z)
            vis = sun_visibility(bvh, p, nrm, face_id, GROUND_SUN_RAYS)
            ao = ambient_occlusion(bvh, p, nrm, face_id, GROUND_AO_RAYS,
                                    GROUND_AO_DIST)
            row.append(ground_light(vis, ao))
        field.append(row)
    blur_field(field, GROUND_BLUR, GROUND_BLUR_SIGMA)

    base = tuple(float(x) for x in face["color"])
    vid = [[0] * (nx + 1) for _ in range(nz + 1)]
    for j in range(nz + 1):
        z = z0 + (z1 - z0) * j / nz
        for i in range(nx + 1):
            p = (x0 + (x1 - x0) * i / nx, y0, z)
            k = field[j][i]
            g = _ground_grain(p, planks)
            tinted = tuple(min(1.0, base[q] * g) for q in range(3))
            c = tuple(srgb_to_linear(x) for x in grade(tinted, k))
            vid[j][i] = len(m.pos)
            m.pos.append(p)
            m.nrm.append(nrm)
            m.col.append(c)

    for j in range(nz):
        for i in range(nx):
            a = vid[j][i]
            b = vid[j][i + 1]
            c = vid[j + 1][i]
            d = vid[j + 1][i + 1]
            m.idx += [a, c, b, b, c, d]

    _add_ground_strips(m, face, bvh, face_id, skip_edges)


def bake_level(lv, ground=True, detail=0.06, detail_ground=0.015):
    """Return ([(piece_id, Mesh)], ground Mesh|None) with baked colours."""
    raw_faces = []
    for p in lv["pieces"]:
        fl = []
        for s in p["solids"]:
            for f in s.get("faces") or []:
                fl.append(f)
        raw_faces.append((p["id"], fl))
    dy = contact_shift([f for _, fl in raw_faces for f in fl])
    piece_faces = [(pid, [shift_face(f, dy) for f in fl])
                   for pid, fl in raw_faces]
    gfaces = ground_faces(lv) if ground else []

    all_faces = [f for _, fl in piece_faces for f in fl] + gfaces
    seams = coplanar_seams(all_faces)
    tris = []
    face_of = []
    for fi, f in enumerate(all_faces):
        pts = [tuple(float(x) for x in q) for q in f["points"]]
        if len(pts) >= 3:
            for a, b, c in _fan(pts):
                tris.append((a, b, c))
                face_of.append(fi)
    bvh = BVH(tris, face_of)

    meshes = []
    fi = 0
    def bake_any(m, f, face_id, det):
        pts = f["points"]
        if len(pts) == 4:
            bake_quad(m, f, bvh, face_id, det, seams.get(face_id, ()))
        else:
            bake_face(m, f, bvh, face_id, det, seams.get(face_id, ()))

    for pid, fl in piece_faces:
        m = Mesh()
        for f in fl:
            bake_any(m, f, fi, detail)
            fi += 1
        meshes.append((pid, m))
    gmesh = None
    if ground:
        gmesh = Mesh()
        turf = int((lv.get("garden") or {}).get("turf", 0))
        for f in gfaces:
            if f.get("fine"):
                bake_ground_top(gmesh, f, bvh, fi, detail_ground,
                                planks=not turf, skip_edges=seams.get(fi, ()))
            elif f.get("brick"):
                bake_any(gmesh, f, fi, 0.015)
            else:
                bake_any(gmesh, f, fi, detail)
            fi += 1
    return meshes, gmesh


def assemble_animation(lv, fps=24):
    """Loop assembled -> exploded -> assembled as glTF node translations.

    The source models are authored exploded; ``assemble`` holds the offset that
    closes each joint. Pegs and wedges are withdrawn along their own long axis
    first, before any timber moves, then driven back in after the timbers have
    closed. Moving them on the diagonal straight to their exploded pose would
    shear them through the surrounding timber.

    ``approach`` optionally gives a timber a final slide: the vector, relative
    to its closed pose, where it waits before sliding home (kanawa-tsugi's
    upper half drops in clear of the hooks, then slides along the pitch).
    """
    offsets = lv.get("assemble") or {}
    approach = lv.get("approach") or {}
    if not offsets or not any(any(abs(c) > 1e-9 for c in v)
                              for v in offsets.values()):
        return None

    dims = {}
    for p in lv["pieces"]:
        pts = [q for s in p["solids"] for f in s["faces"] for q in f["points"]]
        if not pts:
            continue
        mn = [min(q[i] for q in pts) for i in range(3)]
        mx = [max(q[i] for q in pts) for i in range(3)]
        dims[p["id"]] = [mx[i] - mn[i] for i in range(3)]
    if not dims:
        return None
    anchor = max(dims, key=lambda pid: dims[pid][0] * dims[pid][1]
                 * dims[pid][2])
    anchor_long = max(dims[anchor])

    def is_key(pid):
        # A peg or wedge: much shorter than the main timber in every direction.
        # (Split halves such as nimai-kama's blades are almost as long as the
        # anchor and stay on the direct path.)
        d = dims[pid]
        return max(d) < 0.6 * anchor_long

    def smooth(u):
        u = max(0.0, min(1.0, u))
        return u * u * (3.0 - 2.0 * u)

    def mix(a, b, u):
        return [a[i] + (b[i] - a[i]) * u for i in range(3)]

    def ease(t, a, b):
        return smooth((t - a) / (b - a)) if b > a else (1.0 if t >= b else 0.0)

    end = 6.0
    # Keys: out along the long axis, then aside to the exploded pose. Timbers:
    # only after the keys are clear. The assembly mirrors that order.
    k_ax0, k_ax1 = 0.9, 1.45
    k_rest0, k_rest1 = 1.45, 1.85
    b_out0, b_out1 = 1.9, 3.0
    b_in0, b_in1 = 3.3, 4.4
    k_in0, k_in1 = 4.45, 4.85
    k_ax_in1 = 5.5

    tracks = {}
    steps = int(round(end * fps))
    for pid, off in offsets.items():
        if not any(abs(c) > 1e-9 for c in off):
            continue
        home = [0.0, 0.0, 0.0]
        if is_key(pid):
            axis = max(range(3), key=lambda i: dims[pid][i])
            clear = [off[i] if i != axis else 0.0 for i in range(3)]
            keys = []
            for i in range(steps + 1):
                t = i / float(fps)
                if t <= k_ax0:
                    v = list(off)
                elif t < k_ax1:
                    v = mix(off, clear, ease(t, k_ax0, k_ax1))
                elif t < k_rest1:
                    v = mix(clear, home, ease(t, k_rest0, k_rest1))
                elif t < k_in0:
                    v = list(home)
                elif t < k_in1:
                    v = mix(home, clear, ease(t, k_in0, k_in1))
                elif t < k_ax_in1:
                    v = mix(clear, off, ease(t, k_in1, k_ax_in1))
                else:
                    v = list(off)
                keys.append((t, v))
        elif pid in approach:
            pre = [off[i] + approach[pid][i] for i in range(3)]
            b_mid = b_out0 + 0.4 * (b_out1 - b_out0)
            b_in_mid = b_in0 + 0.6 * (b_in1 - b_in0)
            keys = []
            for i in range(steps + 1):
                t = i / float(fps)
                if t <= b_out0:
                    v = list(off)
                elif t < b_mid:
                    v = mix(off, pre, ease(t, b_out0, b_mid))
                elif t < b_out1:
                    v = mix(pre, home, ease(t, b_mid, b_out1))
                elif t < b_in0:
                    v = list(home)
                elif t < b_in_mid:
                    v = mix(home, pre, ease(t, b_in0, b_in_mid))
                elif t < b_in1:
                    v = mix(pre, off, ease(t, b_in_mid, b_in1))
                else:
                    v = list(off)
                keys.append((t, v))
        else:
            keys = []
            for i in range(steps + 1):
                t = i / float(fps)
                if t <= b_out0:
                    v = list(off)
                elif t < b_out1:
                    v = mix(off, home, ease(t, b_out0, b_out1))
                elif t < b_in0:
                    v = list(home)
                elif t < b_in1:
                    v = mix(home, off, ease(t, b_in0, b_in1))
                else:
                    v = list(off)
                keys.append((t, v))
        tracks[pid] = keys
    return {"name": "assemble", "tracks": tracks}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", default="catalog.json")
    ap.add_argument("out", nargs="?", default="../joints")
    ap.add_argument("--level", action="append", default=[],
                    help="level id to bake (repeatable; default all)")
    ap.add_argument("--detail", type=float, default=0.06,
                    help="target sub-triangle edge length for pieces")
    ap.add_argument("--detail-ground", type=float, default=0.015,
                    help="target sub-triangle edge length for the garden top")
    ap.add_argument("--no-ground", action="store_true",
                    help="do not add the garden slab to level assemblies")
    ap.add_argument("--no-ao", action="store_true", help="disable ambient occlusion")
    ap.add_argument("--ao-dist", type=float, default=None,
                    help="ambient-occlusion ray length in metres (default 0.55)")
    ap.add_argument("--edge", type=float, default=None,
                    help="painted border strip width in metres (default 0.007)")
    ap.add_argument("--edge-lift", type=float, default=None,
                    help="border strip lift above the face in metres")
    ap.add_argument("--no-animation", action="store_true",
                    help="omit the assemble animation even if the level has one")
    ap.add_argument("--fps", type=int, default=24,
                    help="assemble animation sample rate (default 24)")
    ap.add_argument("--pieces", action="store_true",
                    help="also write one baked GLB per piece (default: level only)")
    ap.add_argument("--unlit", action="store_true", default=True)
    args = ap.parse_args()

    global AO_RAYS, GROUND_AO_RAYS, AO_DIST, EDGE_STRIP_W, EDGE_STRIP_LIFT
    if args.no_ao:
        AO_RAYS = 0
        GROUND_AO_RAYS = 0
    if args.ao_dist is not None:
        AO_DIST = args.ao_dist
    if args.edge is not None:
        EDGE_STRIP_W = args.edge
    if args.edge_lift is not None:
        EDGE_STRIP_LIFT = args.edge_lift

    cat = json.load(open(args.src))
    levels = [lv for lv in cat if not args.level or lv["id"] in args.level]
    if not levels:
        sys.exit("no matching levels")
    total = 0
    for lv in levels:
        lid = safe(lv["id"])
        credit = (lv.get("source") or {}).get("credit")
        meshes, gmesh = bake_level(lv, ground=not args.no_ground,
                                   detail=args.detail,
                                   detail_ground=args.detail_ground)
        ldir = os.path.join(args.out, lid)
        nodes = []
        tris = 0
        for pid, m in meshes:
            if m.empty():
                continue
            if args.pieces:
                write_glb(os.path.join(ldir, safe(pid) + ".glb"), [(pid, m)],
                          True, credit)
            nodes.append((pid, m))
            tris += len(m.idx) // 3
        if gmesh is not None and not gmesh.empty():
            nodes.append(("garden", gmesh))
            tris += len(gmesh.idx) // 3
        anim = None if args.no_animation else assemble_animation(lv, args.fps)
        write_glb(os.path.join(args.out, lid + ".glb"), nodes, True, credit,
                  [anim] if anim else None)
        total += tris
        print("%-14s %2d pieces  %6d tris" % (lv["id"], len(nodes), tris))
    print("baked %d levels, %d triangles -> %s" % (len(levels), total, args.out))


if __name__ == "__main__":
    main()
