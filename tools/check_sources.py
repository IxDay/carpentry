#!/usr/bin/env python3
"""Check joint sources in the closed pose: manifold, winding, no overlap.

`validate.py` checks the baked GLBs; this checks the geometry they came from.
Each source stores its pieces in the exploded pose and the `assemble` vector
that closes the joint, so the closed pose is the source shifted by `assemble`.
On that pose the tool verifies, for every piece:

* every edge is used by exactly two faces, in opposite directions (closed and
  consistently wound),
* every face's stored normal points the same way as its point order,
* no two timbers share volume (mating faces may touch, but not interpenetrate).

Overlap is probed with vertices, edge midpoints and triangle centroids, ignoring
points that lie on the other piece's surface; a probe well inside another piece
is a real interpenetration. Concave faces are triangulated by ear clipping, so
the imported sources can be checked too.

    python3 tools/check_sources.py                 # every joints/sources/*.json
    python3 tools/check_sources.py daimochi-tsugi  # by id or path
"""
import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "joints", "sources")
TOL = 1e-6
NEAR = 1e-5
PATCH = 5e-4      # ignore coplanar overlaps thinner than this (capture noise)


# ----------------------------------------------------------------- topology --
def closed_pieces(source):
    asm = source.get("assemble") or {}
    out = []
    for p in source["pieces"]:
        d = asm.get(p["id"], [0.0, 0.0, 0.0])
        faces = []
        for s in p["solids"]:
            for f in s["faces"]:
                faces.append({
                    "points": [[q[i] + d[i] for i in range(3)]
                               for q in f["points"]],
                    "normal": f["normal"],
                })
        out.append((p["id"], faces))
    return out


def newell(pts):
    nx = ny = nz = 0.0
    for i in range(len(pts)):
        a, b = pts[i], pts[(i + 1) % len(pts)]
        nx += (a[1] - b[1]) * (a[2] + b[2])
        ny += (a[2] - b[2]) * (a[0] + b[0])
        nz += (a[0] - b[0]) * (a[1] + b[1])
    return nx, ny, nz


def split_edges(faces):
    """Split each edge at any vertex lying on it, so T-junctions do not read as
    holes. The imported captures carry such junctions; the authored solids are
    already welded."""
    verts = sorted({tuple(round(c, 6) for c in q)
                    for f in faces for q in f["points"]})
    for f in faces:
        P = [tuple(float(c) for c in q) for q in f["points"]]
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
                w = [a[i] + d[i] * t / L2 for i in range(3)]
                if max(abs(w[i] - v[i]) for i in range(3)) < 1e-7:
                    on.append((t, list(v)))
            pts.extend(v for _, v in sorted(on))
        f["points"] = pts
    return faces


def check_topology(pid, faces):
    errs = []
    edges = {}
    for fi, f in enumerate(faces):
        pts = [tuple(round(c, 6) for c in q) for q in f["points"]]
        if len(pts) < 3:
            errs.append("%s: face %d has %d points" % (pid, fi, len(pts)))
            continue
        wn = newell([list(q) for q in pts])
        n = f["normal"]
        if wn[0] * n[0] + wn[1] * n[1] + wn[2] * n[2] <= 0:
            errs.append("%s: face %d winds against its normal" % (pid, fi))
        for a, b in zip(pts, pts[1:] + pts[:1]):
            if a == b:
                errs.append("%s: face %d has a zero-length edge" % (pid, fi))
                continue
            key = (a, b) if a < b else (b, a)
            edges.setdefault(key, []).append(1 if a < b else -1)
    for key, uses in edges.items():
        if len(uses) != 2:
            errs.append("%s: edge %s used by %d faces"
                        % (pid, key, len(uses)))
        elif sum(uses) != 0:
            errs.append("%s: edge %s wound the same way twice" % (pid, key))
    return errs


# -------------------------------------------------------------- triangulate --
def point_in_tri(p, a, b, c):
    def s(p1, p2, p3):
        return ((p1[0] - p3[0]) * (p2[1] - p3[1])
                - (p2[0] - p3[0]) * (p1[1] - p3[1]))
    d1, d2, d3 = s(p, a, b), s(p, b, c), s(p, c, a)
    neg = d1 < -1e-12 or d2 < -1e-12 or d3 < -1e-12
    pos = d1 > 1e-12 or d2 > 1e-12 or d3 > 1e-12
    return not (neg and pos)


def ear_clip(poly):
    n = len(poly)
    area = sum(poly[i][0] * poly[(i + 1) % n][1]
               - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    sign = 1.0 if area > 0 else -1.0
    idx = list(range(n))
    tris = []
    while len(idx) > 3:
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = poly[i0], poly[i1], poly[i2]
            cross = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
            if sign * cross <= 1e-12:
                continue
            if any(point_in_tri(poly[j], a, b, c)
                   for j in idx if j not in (i0, i1, i2)):
                continue
            tris.append((i0, i1, i2))
            idx.pop(k)
            break
        else:
            break
    if len(idx) == 3:
        tris.append(tuple(idx))
    return tris


def tri_faces(faces):
    tris = []
    for f in faces:
        pts = [tuple(float(c) for c in q) for q in f["points"]]
        if len(pts) == 3:
            tris.append(pts)
            continue
        n = f["normal"]
        a = max(range(3), key=lambda i: abs(n[i]))
        u, v = (a + 1) % 3, (a + 2) % 3
        poly = [(p[u], p[v]) for p in pts]
        for i0, i1, i2 in ear_clip(poly):
            tris.append([pts[i0], pts[i1], pts[i2]])
    return tris


# --------------------------------------------------------------- proximity --
def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def dist_to_tri(p, a, b, c):
    ab, ac, ap = sub(b, a), sub(c, a), sub(p, a)
    d1, d2 = dot(ab, ap), dot(ac, ap)
    if d1 <= 0 and d2 <= 0:
        return math.sqrt(dot(ap, ap))
    bp = sub(p, b)
    d3, d4 = dot(ab, bp), dot(ac, bp)
    if d3 >= 0 and d4 <= d3:
        return math.sqrt(dot(bp, bp))
    vc = d1 * d4 - d3 * d2
    if vc <= 0 and d1 >= 0 and d3 <= 0:
        v = d1 / (d1 - d3)
        return math.sqrt(dot(sub(p, (a[0] + v * ab[0], a[1] + v * ab[1],
                                    a[2] + v * ab[2])),
                             sub(p, (a[0] + v * ab[0], a[1] + v * ab[1],
                                    a[2] + v * ab[2]))))
    cp = sub(p, c)
    d5, d6 = dot(ab, cp), dot(ac, cp)
    if d6 >= 0 and d5 <= d6:
        return math.sqrt(dot(cp, cp))
    vb = d5 * d2 - d1 * d6
    if vb <= 0 and d2 >= 0 and d6 <= 0:
        w = d2 / (d2 - d6)
        q = (a[0] + w * ac[0], a[1] + w * ac[1], a[2] + w * ac[2])
        return math.sqrt(dot(sub(p, q), sub(p, q)))
    va = d3 * d6 - d5 * d4
    if va <= 0 and (d4 - d3) >= 0 and (d5 - d6) >= 0:
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        q = (b[0] + w * (c[0] - b[0]), b[1] + w * (c[1] - b[1]),
             b[2] + w * (c[2] - b[2]))
        return math.sqrt(dot(sub(p, q), sub(p, q)))
    denom = 1.0 / (va + vb + vc)
    v, w = vb * denom, vc * denom
    q = (a[0] + ab[0] * v + ac[0] * w,
         a[1] + ab[1] * v + ac[1] * w,
         a[2] + ab[2] * v + ac[2] * w)
    return math.sqrt(dot(sub(p, q), sub(p, q)))


def ray_hits(pt, d, tris):
    hits = 0
    for a, b, c in tris:
        e1, e2 = sub(b, a), sub(c, a)
        h = cross(d, e2)
        det = dot(e1, h)
        if abs(det) < 1e-12:
            continue
        inv = 1.0 / det
        s = sub(pt, a)
        u = dot(s, h) * inv
        if u < 0 or u > 1:
            continue
        q = cross(s, e1)
        v = dot(d, q) * inv
        if v < 0 or u + v > 1:
            continue
        if dot(e2, q) * inv > 1e-9:
            hits += 1
    return hits


DIRS = ((0.3141, 0.2718, 0.6180), (0.6180, -0.2718, 0.3141),
        (-0.2718, 0.6180, 0.3141))


def inside(pt, tris):
    votes = 0
    for d in DIRS:
        L = math.sqrt(dot(d, d))
        if ray_hits(pt, (d[0] / L, d[1] / L, d[2] / L), tris) % 2:
            votes += 1
    return votes >= 2


def probes(faces, tris):
    pts = []
    for f in faces:
        P = [tuple(float(c) for c in q) for q in f["points"]]
        pts.extend(P)
        for a, b in zip(P, P[1:] + P[:1]):
            pts.append(tuple((a[i] + b[i]) / 2 for i in range(3)))
    for a, b, c in tris:
        pts.append(tuple((a[i] + b[i] + c[i]) / 3 for i in range(3)))
    return pts


def check_overlap(pieces):
    errs = []
    tris = {pid: tri_faces(faces) for pid, faces in pieces}
    for i in range(len(pieces)):
        for j in range(i + 1, len(pieces)):
            ia, fa = pieces[i]
            ib, fb = pieces[j]
            for pid, other, tris_other in ((ia, fb, tris[ib]),
                                           (ib, fa, tris[ia])):
                hit = _probe_overlap(other, tris_other)
                if hit:
                    errs.append("%s and %s overlap near %s" % (ia, ib, hit))
                    break
            else:
                if _coplanar_overlap(fa, fb, tris[ia], tris[ib]):
                    errs.append("%s and %s overlap across a shared plane"
                                % (ia, ib))
    return errs


def _probe_overlap(other, tris_other):
    for p in probes(other, tris_other):
        if any(dist_to_tri(p, a, b, c) < NEAR for a, b, c in tris_other):
            continue
        if inside(p, tris_other):
            return "(%.4f, %.4f, %.4f)" % p
    return None


def edge_dist2(poly, su, sv):
    best = float("inf")
    n = len(poly)
    for i in range(n):
        au, av = poly[i]
        bu, bv = poly[(i + 1) % n]
        du, dv = bu - au, bv - av
        L2 = du * du + dv * dv
        t = 0.0 if L2 < 1e-18 else ((su - au) * du + (sv - av) * dv) / L2
        t = max(0.0, min(1.0, t))
        best = min(best, math.hypot(su - (au + t * du), sv - (av + t * dv)))
    return best


def pip2(poly, u, v, su, sv):
    inside_ = False
    n = len(poly)
    for i in range(n):
        au, av = poly[i][u], poly[i][v]
        bu, bv = poly[(i + 1) % n][u], poly[(i + 1) % n][v]
        if (av > sv) != (bv > sv):
            if su < au + (sv - av) * (bu - au) / (bv - av):
                inside_ = not inside_
    return inside_


def _coplanar_overlap(fa, fb, tris_a, tris_b):
    """Catch interpenetration whose vertices all sit on the other piece's
    surface: two faces lie in the same plane and one piece's interior lies on
    the wrong side of it, under the other's face."""
    for face_a in fa:
        pts_a = face_a["points"]
        na = face_a["normal"]
        L = math.sqrt(dot(na, na)) or 1.0
        na = (na[0] / L, na[1] / L, na[2] / L)
        da = dot(na, pts_a[0])
        a = max(range(3), key=lambda i: abs(na[i]))
        u, v = (a + 1) % 3, (a + 2) % 3
        for face_b in fb:
            nb = face_b["normal"]
            L = math.sqrt(dot(nb, nb)) or 1.0
            nb = (nb[0] / L, nb[1] / L, nb[2] / L)
            if abs(abs(dot(na, nb)) - 1.0) > 1e-6:
                continue
            if abs(dot(na, face_b["points"][0]) - da) > 1e-6:
                continue
            ba = [(p[u], p[v]) for p in pts_a]
            bb = [(p[u], p[v]) for p in face_b["points"]]
            lo = [max(min(q[0] for q in ba), min(q[0] for q in bb)),
                  max(min(q[1] for q in ba), min(q[1] for q in bb))]
            hi = [min(max(q[0] for q in ba), max(q[0] for q in bb)),
                  min(max(q[1] for q in ba), max(q[1] for q in bb))]
            if lo[0] >= hi[0] - PATCH or lo[1] >= hi[1] - PATCH:
                continue
            for i in range(1, 8):
                for j in range(1, 8):
                    su = lo[0] + (hi[0] - lo[0]) * i / 8.0
                    sv = lo[1] + (hi[1] - lo[1]) * j / 8.0
                    if not (pip2(ba, 0, 1, su, sv)
                            and pip2(bb, 0, 1, su, sv)):
                        continue
                    if min(edge_dist2(ba, su, sv),
                           edge_dist2(bb, su, sv)) < 0.002:
                        continue
                    p = [0.0, 0.0, 0.0]
                    p[u], p[v] = su, sv
                    p[a] = (da - na[u] * su - na[v] * sv) / na[a]
                    q = [p[k] - na[k] * 0.001 for k in range(3)]
                    if inside(q, tris_a) and inside(q, tris_b):
                        return True
    return False


# ---------------------------------------------------------------------- main --
def check(path):
    with open(path) as fh:
        source = json.load(fh)[0]
    pieces = closed_pieces(source)
    errs = []
    for pid, faces in pieces:
        errs.extend(check_topology(pid,
                                   split_edges(json.loads(json.dumps(faces)))))
    errs.extend(check_overlap(pieces))
    return source["id"], len(pieces), errs


def main(argv):
    want = argv[1:]
    if not want:
        paths = sorted(glob.glob(os.path.join(SRC, "*.json")))
    else:
        paths = []
        for w in want:
            p = w if os.path.exists(w) else os.path.join(SRC, w + ".json")
            paths.append(p)
    bad = 0
    for path in paths:
        jid, n, errs = check(path)
        if errs:
            bad += 1
            print("FAIL %s (%d pieces)" % (jid, n))
            for e in errs[:12]:
                print("   ", e)
            if len(errs) > 12:
                print("    ... %d more" % (len(errs) - 12))
        else:
            print("%-34s %2d pieces  closed, wound, no overlap" % (jid, n))
    if bad:
        print("%d of %d sources failed" % (bad, len(paths)))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
