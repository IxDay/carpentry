#!/usr/bin/env python3
"""Diagnostic for the closed pose: do the pieces actually touch / interlock?

`check_sources.py` proves each piece is a closed, correctly wound solid and that
no two pieces share volume.  It deliberately allows mating faces to touch, but
that means a joint whose pieces float a few millimetres apart still passes.
This tool adds the complementary checks:

* surface-to-surface distance between every pair of pieces (contact / gap),
* connectivity of the piece adjacency graph in the closed pose,
* a cheap "interlock" proxy (how much of one piece's surface sits inside the
  other piece's bounding box), which flags joints with no mortise/recess.

Usage:
    python3 tools/check_contact.py                 # every joints/sources/*.json
    python3 tools/check_contact.py daimochi-tsugi   # by id or path
    python3 tools/check_contact.py --json          # machine-readable report
"""
import glob
import json
import math
import os
import sys

import numpy as np

from check_sources import SRC, closed_pieces, tri_faces, probes

CONTACT = 1e-4      # <= 0.1 mm: touching (capture noise / chamfer tolerance)
NEAR = 2e-3         # <= 2 mm: suspicious, but may be a designed clearance
BBOX_FAR = 0.08     # skip detailed probe when bounding boxes are this far apart


# ----------------------------------------------------------- distance kernel --
def _safe_div(a, b):
    out = np.zeros_like(a)
    np.divide(a, b, out=out, where=np.abs(b) > 1e-15)
    return out


def points_to_tris(P, A, B, C, chunk=64):
    """Minimum Euclidean distance from each point in P to any triangle ABC.

    Vectorised Ericson closest-point-on-triangle.  P is (n,3); A,B,C are (m,3).
    Returns an array of n distances.
    """
    n, m = len(P), len(A)
    if not n or not m:
        return np.full(n, float("inf"))
    out = np.empty(n)
    Pp = P[:, None, :]
    Ab, Bb, Cb = A[None, :, :], B[None, :, :], C[None, :, :]
    ab, ac = Bb - Ab, Cb - Ab
    bc = Cb - Bb
    for lo in range(0, n, chunk):
        hi = min(lo + chunk, n)
        p = Pp[lo:hi]
        ap = p - Ab
        bp = p - Bb
        cp = p - Cb
        d1 = np.sum(ab * ap, axis=2)
        d2 = np.sum(ac * ap, axis=2)
        d3 = np.sum(ab * bp, axis=2)
        d4 = np.sum(ac * bp, axis=2)
        d5 = np.sum(ab * cp, axis=2)
        d6 = np.sum(ac * cp, axis=2)
        va = d3 * d6 - d5 * d4
        vb = d5 * d2 - d1 * d6
        vc = d1 * d4 - d3 * d2

        shape3 = d1.shape + (3,)
        qa = np.broadcast_to(Ab, shape3).copy()
        qb = np.broadcast_to(Bb, shape3).copy()
        qc = np.broadcast_to(Cb, shape3).copy()
        qab = Ab + ab * _safe_div(d1, d1 - d3)[..., None]
        qac = Ab + ac * _safe_div(d2, d2 - d6)[..., None]
        qbc = Bb + bc * _safe_div(d4 - d3, (d4 - d3) + (d5 - d6))[..., None]
        den = va + vb + vc
        inv = _safe_div(np.ones_like(den), den)
        qin = Ab + ab * (vb * inv)[..., None] + ac * (vc * inv)[..., None]

        m_a = (d1 <= 0) & (d2 <= 0)
        m_b = (d3 >= 0) & (d4 <= d3)
        m_c = (d6 >= 0) & (d5 <= d6)
        m_ab = ~m_a & ~m_b & (vc <= 0) & (d1 >= 0) & (d3 <= 0)
        m_ac = ~m_a & ~m_b & ~m_ab & (vb <= 0) & (d2 >= 0) & (d6 <= 0)
        m_bc = ~m_a & ~m_b & ~m_ab & ~m_ac & (va <= 0) & \
            ((d4 - d3) >= 0) & ((d5 - d6) >= 0)
        m_in = ~m_a & ~m_b & ~m_ab & ~m_ac & ~m_bc & (den > 1e-15)

        q = qa
        q = np.where(m_b[..., None], qb, q)
        q = np.where(m_c[..., None], qc, q)
        q = np.where(m_ab[..., None], qab, q)
        q = np.where(m_ac[..., None], qac, q)
        q = np.where(m_bc[..., None], qbc, q)
        q = np.where(m_in[..., None], qin, q)
        d = np.linalg.norm(p - q, axis=2)
        out[lo:hi] = np.min(d, axis=1)
    return out


def bbox(points):
    p = np.asarray(points, dtype=float)
    return p.min(axis=0), p.max(axis=0)


def bbox_distance(lo1, hi1, lo2, hi2):
    d = np.maximum(0.0, np.maximum(lo1 - hi2, lo2 - hi1))
    return float(np.linalg.norm(d))


def bbox_overlap(lo1, hi1, lo2, hi2):
    o = np.maximum(0.0, np.minimum(hi1, hi2) - np.maximum(lo1, lo2))
    return float(np.prod(o))


# ------------------------------------------------------------------- analysis --
def analyse(source):
    pieces = closed_pieces(source)
    ids = [pid for pid, _ in pieces]
    tris = {}
    probes_pts = {}
    boxes = {}
    for pid, faces in pieces:
        t = np.asarray(tri_faces(faces), dtype=float).reshape(-1, 3, 3)
        tris[pid] = t
        probes_pts[pid] = np.asarray(
            probes(faces, [[tuple(v) for v in tri] for tri in t]),
            dtype=float)
        pts = np.asarray([q for f in faces for q in f["points"]], dtype=float)
        boxes[pid] = bbox(pts)

    pairs = {}
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = ids[i], ids[j]
            lo1, hi1 = boxes[a]
            lo2, hi2 = boxes[b]
            bdist = bbox_distance(lo1, hi1, lo2, hi2)
            ov = bbox_overlap(lo1, hi1, lo2, hi2)
            if bdist > BBOX_FAR:
                pairs[(a, b)] = {
                    "distance": bdist, "bbox_overlap": ov,
                    "bbox_distance": bdist, "status": "far",
                }
                continue
            A, B, C = tris[a][:, 0, :], tris[a][:, 1, :], tris[a][:, 2, :]
            pa = probes_pts[b]
            da = points_to_tris(pa, A, B, C)
            A, B, C = tris[b][:, 0, :], tris[b][:, 1, :], tris[b][:, 2, :]
            pb = probes_pts[a]
            db = points_to_tris(pb, A, B, C)
            md = min(float(da.min(initial=float("inf"))),
                     float(db.min(initial=float("inf"))))
            # how much of each surface lies inside the other's bounding box
            def frac_inside(pts, lo, hi):
                if not len(pts):
                    return 0.0
                ok = np.all((pts >= lo - 1e-6) & (pts <= hi + 1e-6), axis=1)
                return float(ok.mean())
            inside_a = frac_inside(pa, lo1, hi1)  # B surface inside A box
            inside_b = frac_inside(pb, lo2, hi2)  # A surface inside B box
            status = ("contact" if md <= CONTACT else
                      "near" if md <= NEAR else "gap")
            pairs[(a, b)] = {
                "distance": md, "bbox_overlap": ov,
                "bbox_distance": bdist, "status": status,
                "inside_a": inside_a, "inside_b": inside_b,
            }

    # connectivity using contact-only edges
    adj = {pid: set() for pid in ids}
    for (a, b), info in pairs.items():
        if info["status"] == "contact":
            adj[a].add(b)
            adj[b].add(a)
    seen = set()
    comps = []
    for pid in ids:
        if pid in seen:
            continue
        stack, comp = [pid], []
        seen.add(pid)
        while stack:
            cur = stack.pop()
            comp.append(cur)
            for nb in adj[cur]:
                if nb not in seen:
                    seen.add(nb)
                    stack.append(nb)
        comps.append(sorted(comp))

    return {
        "id": source["id"],
        "pieces": ids,
        "pairs": pairs,
        "components": comps,
        "guidance": (source.get("guidance") or "").strip(),
    }


def report(info, verbose=False):
    pid = info["id"]
    comps = info["components"]
    print("%-38s %s" % (
        pid,
        "connected" if len(comps) == 1 else
        "DISCONNECTED (%d groups)" % len(comps)))
    if len(comps) > 1:
        for comp in comps:
            print("     group:", ", ".join(comp))
    rows = []
    for (a, b), p in info["pairs"].items():
        if p["status"] == "far":
            continue
        rows.append((p["distance"], a, b, p))
    rows.sort(reverse=True)
    for dist, a, b, p in rows:
        flag = p["status"].upper()
        print("     %-14s %-14s %-8s %7.2f mm  bboxOverlap=%7.4f  inside=%.2f/%.2f" % (
            a, b, flag, dist * 1000, p["bbox_overlap"] * 1e6,
            p.get("inside_a", 0), p.get("inside_b", 0)))
    return 0 if len(comps) == 1 else 1


def main(argv):
    want = [w for w in argv[1:] if not w.startswith("--")]
    as_json = "--json" in argv
    if not want:
        paths = sorted(glob.glob(os.path.join(SRC, "*.json")))
    else:
        paths = []
        for w in want:
            paths.append(w if os.path.exists(w) else os.path.join(SRC, w + ".json"))
    results = []
    bad = 0
    for path in paths:
        with open(path) as fh:
            source = json.load(fh)[0]
        info = analyse(source)
        results.append(info)
        if not as_json:
            bad += report(info)
    if as_json:
        json.dump(results, sys.stdout, indent=2, default=float)
        print()
    else:
        print("%d of %d sources have disconnected pieces in closed pose"
              % (bad, len(paths)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    sys.exit(main(sys.argv))
