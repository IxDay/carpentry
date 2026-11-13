#!/usr/bin/env python3
"""Open the pocket mouths that the source models cover over.

In some Sketchfab joints a mortise is modelled with its walls but the mouth is
closed by a small "cap" polygon that lies in the same plane as the timber's big
outer face, which also spans the mouth. The hole is therefore invisible from
outside, and a key that is withdrawn leaves no hole behind. This drops each cap
and cuts its footprint out of the axis-aligned rectangle it sits in.

    python3 tools/open_pockets.py joints/sources/okkake-daisen-tsugi.json
    python3 tools/open_pockets.py --dry-run joints/sources/*.json
"""
import json
import sys

EPS = 1e-5


def axis_of(n):
    a = max(range(3), key=lambda i: abs(n[i]))
    return a if abs(n[a]) > 0.99 else None


def bbox(pts):
    return ([min(p[i] for p in pts) for i in range(3)],
            [max(p[i] for p in pts) for i in range(3)])


def is_rect(pts, a):
    if len(pts) != 4:
        return False
    u, v = [i for i in range(3) if i != a]
    return all(abs(p[a] - pts[0][a]) < EPS for p in pts) and \
        len({round(p[u], 5) for p in pts}) == 2 and \
        len({round(p[v], 5) for p in pts}) == 2


def open_pockets(faces):
    """Return (new_faces, number_of_caps_removed)."""
    rects = [(i, f, axis_of(f["normal"])) for i, f in enumerate(faces)]
    rects = [(i, f, a) for i, f, a in rects
             if a is not None and is_rect(f["points"], a)]
    caps = {}
    for i, f, a in rects:
        lo, hi = bbox(f["points"])
        for j, g, b in rects:
            if i == j or a != b or g["normal"][a] * f["normal"][a] <= 0:
                continue
            glo, ghi = bbox(g["points"])
            u, v = [k for k in range(3) if k != a]
            same_plane = abs(glo[a] - lo[a]) < EPS
            inside = all(glo[k] > lo[k] + EPS and ghi[k] < hi[k] - EPS
                         for k in (u, v))
            if same_plane and inside:
                caps.setdefault(j, set()).add(i)
    if not caps:
        return faces, 0

    holes = {}
    for j, owners in caps.items():
        # a cap inside several big faces belongs to the smallest
        i = min(owners, key=lambda k: _area(faces[k]))
        holes.setdefault(i, []).append(j)

    drop = set(caps)
    new = []
    for i, js in holes.items():
        f = faces[i]
        drop.add(i)
        a = axis_of(f["normal"])
        u, v = [k for k in range(3) if k != a]
        lo, hi = bbox(f["points"])
        hs = [bbox(faces[j]["points"]) for j in js]
        us = sorted({lo[u], hi[u]} | {h[0][u] for h in hs} | {h[1][u] for h in hs})
        vs = sorted({lo[v], hi[v]} | {h[0][v] for h in hs} | {h[1][v] for h in hs})
        p = f["points"]
        cross = ((p[1][u] - p[0][u]) * (p[2][v] - p[1][v])
                 - (p[1][v] - p[0][v]) * (p[2][u] - p[1][u]))
        for u0, u1 in zip(us, us[1:]):
            for v0, v1 in zip(vs, vs[1:]):
                cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
                if any(h[0][u] < cu < h[1][u] and h[0][v] < cv < h[1][v]
                       for h in hs):
                    continue
                quad = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
                if cross < 0:
                    quad.reverse()
                pts = []
                for pu, pv in quad:
                    q = [0.0, 0.0, 0.0]
                    q[a], q[u], q[v] = p[0][a], pu, pv
                    pts.append(q)
                g = {k: val for k, val in f.items() if k != "points"}
                g["points"] = pts
                new.append(g)
    return [f for i, f in enumerate(faces) if i not in drop] + new, len(caps)


def _area(f):
    lo, hi = bbox(f["points"])
    d = sorted(hi[i] - lo[i] for i in range(3))
    return d[1] * d[2]


def main(paths, dry):
    for path in paths:
        data = json.load(open(path))
        total = 0
        for piece in data[0]["pieces"]:
            for solid in piece["solids"]:
                solid["faces"], n = open_pockets(solid["faces"])
                total += n
        print(f"{path}: {total} pocket mouths" + (" (dry run)" if dry else ""))
        if total and not dry:
            with open(path, "w") as fh:
                json.dump(data, fh, indent=1)


if __name__ == "__main__":
    args = sys.argv[1:]
    dry = "--dry-run" in args
    main([a for a in args if a != "--dry-run"], dry)
