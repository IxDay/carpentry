#!/usr/bin/env python3
"""Track timber collisions through the assemble animation.

`check_sources.py` proves the closed pose is clean, and `check_contact.py`
proves the pieces meet there, but neither watches the journey.  This tool
samples the exact `assemble` tracks that `bake.py` writes into the GLB and
checks every frame with numpy-backed mesh queries: probe points on one timber
(vertices, edge midpoints, triangle centroids) are tested against the other's
triangulated surface, and a probe that lands well inside the other timber is a
collision.  Boxes are built once and only translated per frame.

    python3 check_animation.py watari-ago-niju-hozo-shikuchi
    python3 check_animation.py                 # every source with an animation
    python3 check_animation.py --json <id>
"""
import glob
import json
import os
import sys

import numpy as np

import bake
import check_sources as cs

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "joints", "sources"))
NEAR = 1e-5                 # ignore probes sitting on the other piece's surface
DIRS = np.array([[0.3141, 0.2718, 0.6180],
                 [0.6180, -0.2718, 0.3141],
                 [-0.2718, 0.6180, 0.3141]])


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)[0]


def piece_data(piece):
    """Triangulated surface and probe points, in the piece's authored pose."""
    faces = [f for solid in piece["solids"] for f in solid["faces"]]
    tris = cs.tri_faces(faces)
    verts = np.asarray([p for tri in tris for p in tri], dtype=np.float64)
    fidx = np.arange(len(verts), dtype=np.int64).reshape(-1, 3)
    probes = []
    for face in faces:
        pts = np.asarray(face["points"], dtype=np.float64)
        probes.append(pts)
        probes.append((pts + np.roll(pts, -1, axis=0)) / 2.0)
    probes.append(np.asarray(tris, dtype=np.float64).mean(axis=1))
    return {
        "id": piece["id"],
        "vertices": verts,
        "faces": fidx,
        "probes": np.vstack(probes),
        "bmin": verts.min(axis=0),
        "bmax": verts.max(axis=0),
    }


def moved(data, off):
    """Return the translated probe points, triangle soup and bounding box."""
    d = np.asarray(off, dtype=np.float64)
    verts = data["vertices"] + d
    return (data["probes"] + d, verts[data["faces"]],
            data["bmin"] + d, data["bmax"] + d)


def boxes_overlap(a, b, eps=1e-4):
    return bool(np.all(a[0] <= b[1] + eps) and np.all(b[0] <= a[1] + eps))


def point_tri_dist(points, tris):
    """Vectorised closest distance from every point to every triangle.

    Ericson's closest-point-on-triangle test, evaluated as numpy arrays so a
    frame costs one batch of arithmetic rather than a Python loop per pair.
    """
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    ab, ac, bc = b - a, c - a, c - b
    ap = points[:, None, :] - a[None, :, :]
    bp = points[:, None, :] - b[None, :, :]
    cp = points[:, None, :] - c[None, :, :]
    d1 = np.einsum("nmk,mk->nm", ap, ab)
    d2 = np.einsum("nmk,mk->nm", ap, ac)
    d3 = np.einsum("nmk,mk->nm", bp, ab)
    d4 = np.einsum("nmk,mk->nm", bp, ac)
    d5 = np.einsum("nmk,mk->nm", cp, ab)
    d6 = np.einsum("nmk,mk->nm", cp, ac)
    va = d3 * d6 - d5 * d4
    vb = d5 * d2 - d1 * d6
    vc = d1 * d4 - d3 * d2
    denom = va + vb + vc
    with np.errstate(divide="ignore", invalid="ignore"):
        v = np.divide(vb, denom)
        w = np.divide(vc, denom)
    closest = a[None, :, :] + v[..., None] * ab[None, :, :] + \
        w[..., None] * ac[None, :, :]

    def frac(num, den):
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.divide(num, den, out=np.zeros_like(num), where=den != 0)

    A = np.broadcast_to(a, closest.shape)
    B = np.broadcast_to(b, closest.shape)
    C = np.broadcast_to(c, closest.shape)
    mask = (d1 <= 0) & (d2 <= 0)
    closest[mask] = A[mask]
    mask = (d3 >= 0) & (d4 <= d3)
    closest[mask] = B[mask]
    mask = (d6 >= 0) & (d5 <= d6)
    closest[mask] = C[mask]
    t = frac(d1, d1 - d3)
    mask = (vc <= 0) & (d1 >= 0) & (d3 <= 0)
    closest[mask] = (A + t[..., None] * ab[None, :, :])[mask]
    t = frac(d2, d2 - d6)
    mask = (vb <= 0) & (d2 >= 0) & (d6 <= 0)
    closest[mask] = (A + t[..., None] * ac[None, :, :])[mask]
    t = frac(d4 - d3, (d4 - d3) + (d5 - d6))
    mask = (va <= 0) & ((d4 - d3) >= 0) & ((d5 - d6) >= 0)
    closest[mask] = (B + t[..., None] * bc[None, :, :])[mask]
    d = points[:, None, :] - closest
    return np.linalg.norm(d, axis=2).min(axis=1)


def odd_ray_hits(points, tris, direction):
    """Parity of ray/triangle intersections for one direction, vectorised."""
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    e1, e2 = b - a, c - a
    h = np.cross(direction, e2)
    det = np.einsum("mk,mk->m", e1, h)
    s = points[:, None, :] - a[None, :, :]
    q = np.cross(s, e1)
    with np.errstate(divide="ignore", invalid="ignore"):
        u = np.divide(np.einsum("nmk,mk->nm", s, h), det)
        v = np.divide(np.einsum("nmk,k->nm", q, direction), det)
        t = np.divide(np.einsum("nmk,mk->nm", q, e2), det)
    hits = ((np.abs(det) > 1e-12) & (u >= 0) & (u <= 1) &
            (v >= 0) & (u + v <= 1) & (t > 1e-9))
    return hits.sum(axis=1) % 2 == 1


def point_inside(points, tris):
    """Majority vote of three rays, as in `check_sources.inside`."""
    votes = sum(odd_ray_hits(points, tris, d) for d in DIRS)
    return votes >= 2


def probe_inside(points, tris):
    """Which probes are genuinely inside a piece (surface points discounted)."""
    if not len(points):
        return np.zeros(0, dtype=bool)
    keep = point_tri_dist(points, tris) > NEAR
    result = np.zeros(len(points), dtype=bool)
    if keep.any():
        result[keep] = point_inside(points[keep], tris)
    return result


def check(path, fps=None):
    source = load(path)
    level = {"pieces": source["pieces"],
             "assemble": source.get("assemble") or {},
             "approach": source.get("approach") or {},
             "stages": source.get("stages") or []}
    anim = bake.assemble_animation(level, fps=fps) if fps else \
        bake.assemble_animation(level)
    if not anim:
        return source["id"], []
    tracks = anim["tracks"]
    data = {p["id"]: piece_data(p) for p in source["pieces"]}
    times = [t for t, _ in next(iter(tracks.values()))]
    hits = []
    # Pieces only translate, so a pair's verdict depends on their relative
    # offset alone: a clean pair is not tested again at an offset it has
    # already passed (most frames are the closed or exploded pose).
    clean = set()
    for t in times:
        # bake.py emits a key at every sample, so the key times are the frames.
        off = {}
        for pid, keys in tracks.items():
            for k, (tk, vk) in enumerate(keys):
                if abs(t - tk) < 1e-9:
                    off[pid] = vk
                    break
        posed = {pid: moved(d, off.get(pid, (0, 0, 0)))
                 for pid, d in data.items()}
        ids = list(data)
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                pts_a, tris_a, amin, amax = posed[a]
                pts_b, tris_b, bmin, bmax = posed[b]
                if not boxes_overlap((amin, amax), (bmin, bmax)):
                    continue
                rel = tuple(round(x - y, 6) for x, y in zip(
                    off.get(b, (0, 0, 0)), off.get(a, (0, 0, 0))))
                if (a, b, rel) in clean:
                    continue
                found = False
                for src, dst, pts, tris, lo, hi in (
                        (a, b, pts_a, tris_b, bmin, bmax),
                        (b, a, pts_b, tris_a, amin, amax)):
                    # A probe outside the other piece's box cannot be inside it.
                    pts = pts[np.all((pts >= lo) & (pts <= hi), axis=1)]
                    inside = probe_inside(pts, tris)
                    if inside.any():
                        p = pts[np.argmax(inside)]
                        hits.append({
                            "t": round(t, 4),
                            "pair": [src, dst],
                            "detail": "(%.4f, %.4f, %.4f)" % tuple(p),
                        })
                        found = True
                        break
                if not found:
                    clean.add((a, b, rel))
    return source["id"], hits


def main(argv):
    want = [a for a in argv if not a.startswith("--")]
    as_json = "--json" in argv
    fps = None
    for a in argv:
        if a.startswith("--fps="):
            fps = int(a.split("=", 1)[1])
    if not want:
        paths = sorted(glob.glob(os.path.join(SRC, "*.json")))
    else:
        paths = []
        for w in want:
            paths.append(w if os.path.exists(w)
                         else os.path.join(SRC, w + ".json"))
    report = []
    bad = 0
    for path in paths:
        jid, hits = check(path, fps=fps)
        report.append({"id": jid, "collisions": hits})
        if hits:
            bad += 1
            first = hits[0]
            print("FAIL %-34s %d collisions, first at t=%.2fs: %s -> %s @ %s"
                  % (jid, len(hits), first["t"], first["pair"][0],
                     first["pair"][1], first["detail"]))
            for hit in hits[:5]:
                print("      t=%.2fs  %s -> %s @ %s"
                      % (hit["t"], *hit["pair"], hit["detail"]))
            if len(hits) > 5:
                print("      ... %d more" % (len(hits) - 5))
        else:
            print("%-34s animation clear" % jid)
    if as_json:
        print(json.dumps(report, indent=1))
    if bad:
        print("%d of %d animations collide" % (bad, len(paths)))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
