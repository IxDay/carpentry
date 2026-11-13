#!/usr/bin/env python3
"""Turn a WebGL capture of a Sketchfab model into a catalog-shaped joint.

The capture is written by ``tools/sketchfab_capture.mjs``: it records the
viewer's buffers (quantised positions, octahedral normals, index buffers) plus
the uniforms and GLSL that decode them. This tool rebuilds the mesh, splits it
into its separate timbers, merges coplanar triangles back into polygons, and
writes one level (a one-element list) that ``bake.py`` / ``preview.py`` can read
directly.

    python3 import_joint.py caps/UID.json joints/sources/kanawa-tsugi.json \
        --id kanawa-tsugi --title Kanawa-tsugi --uid 713b...
"""
import argparse
import collections
import json
import math
import os
import re
import struct

# --------------------------------------------------------------- decoding ---
def decode_capture(path):
    cap = json.load(open(path))
    buf = {b["bound"]: bytes(b["bytes"]) for b in cap["buffers"]}

    pos_buf = next(a["buf"] for a in cap["attribs"]
                   if a["index"] == 0 and a["size"] == 4 and a["type"] == 5123)
    nrm_buf = next(a["buf"] for a in cap["attribs"]
                   if a["index"] == 1 and a["size"] == 2 and a["type"] == 5122)

    uniforms = cap["programs"][0]["uniforms"]
    qvs, qvt = uniforms["uQVS"], uniforms["uQVT"]
    src = next(s for s in cap["shaders"] if "uQVS" in s)
    m = re.search(r"\* uQVS ([*/]) vec3\(([^)]*)\)\.([xyz]{3})", src)
    op, vals, perm = m.group(1), [float(x) for x in m.group(2).split(",")], m.group(3)
    div = [vals["xyz".index(c)] for c in perm]
    scale = [qvs[i] / div[i] if op == "/" else qvs[i] * div[i] for i in range(3)]

    raw = struct.unpack("<%dH" % (len(buf[pos_buf]) // 2), buf[pos_buf])
    pos = []
    for i in range(0, len(raw), 4):
        vx, vy, vz, vw = [raw[i + k] / 65535.0 for k in range(4)]
        pos.append(((vx + vw) * scale[0] + qvt[0],
                    (vy + vw) * scale[1] + qvt[1],
                    (vz + vw) * scale[2] + qvt[2]))

    nh = struct.unpack("<%dh" % (len(buf[nrm_buf]) // 2), buf[nrm_buf])

    def octa(x, y):
        x /= 32767.0
        y /= 32767.0
        z = min(1.0, x * x + y * y)
        return (2 * x * math.sqrt(max(0.0, 1 - z)),
                2 * y * math.sqrt(max(0.0, 1 - z)),
                1 - 2 * z)

    nrm = [octa(nh[i], nh[i + 1]) for i in range(0, len(nh), 2)]

    def strip_tris(idx):
        out, run = [], []
        for i in idx:
            if i == 65535:
                run = []
                continue
            run.append(i)
            if len(run) >= 3:
                a, c, b = run[-3], run[-2], run[-1]
                if len(set((a, c, b))) == 3:
                    out.append((a, c, b) if len(run) % 2 == 0 else (a, b, c))
        return out

    tris = []
    for d in cap["draws"]:
        idx = struct.unpack("<%dH" % (len(buf[d["elem"]]) // 2), buf[d["elem"]])
        if d["mode"] == 5:
            tris += strip_tris(idx[:d["count"]])
        elif d["mode"] == 4:
            tris += [(idx[i], idx[i + 1], idx[i + 2])
                     for i in range(0, min(d["count"], len(idx)), 3)]
    # Draws repeat every frame (and for shadow + colour passes).
    seen, uniq = set(), []
    for t in tris:
        k = tuple(sorted(t))
        if k in seen:
            continue
        seen.add(k)
        uniq.append(t)
    return pos, nrm, uniq


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def norm(v):
    l = math.sqrt(dot(v, v))
    return (v[0] / l, v[1] / l, v[2] / l)


# ----------------------------------------------------------- mesh building --
def weld_positions(pos):
    key, uid = {}, []
    for p in pos:
        k = tuple(round(c, 5) for c in p)
        if k not in key:
            key[k] = len(key)
        uid.append(key[k])
    upos = [None] * len(key)
    for k, i in key.items():
        upos[i] = k
    return upos, uid


def orient_and_split(upos, uid, nrm, tris):
    """Drop degenerate triangles, fix winding against the author's normals,
    and return per-component triangle lists of welded indices."""
    kept = []
    for t in tris:
        ids = [uid[i] for i in t]
        if len(set(ids)) < 3:
            continue
        a, b, c = [upos[i] for i in ids]
        gn = norm(cross(sub(b, a), sub(c, a)))
        if dot(gn, gn) < 0.5:
            continue
        avg = tuple(sum(nrm[i][k] for i in t) for k in range(3))
        if dot(gn, avg) < 0:
            ids = (ids[0], ids[2], ids[1])
        kept.append(tuple(ids))

    parent = list(range(len(upos)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for t in kept:
        for a, b in ((t[0], t[1]), (t[1], t[2])):
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb
    comps = collections.defaultdict(list)
    for t in kept:
        comps[find(t[0])].append(t)
    return list(comps.values())


def plane_key(n, p):
    return (round(n[0], 4), round(n[1], 4), round(n[2], 4), round(dot(n, p), 4))


def boundary_loops(ts):
    cnt = collections.Counter()
    for t in ts:
        for k in range(3):
            a, b = t[k], t[(k + 1) % 3]
            cnt[(a, b) if a < b else (b, a)] += 1
    bedges = [e for e, c in cnt.items() if c == 1]
    adj = collections.defaultdict(list)
    for a, b in bedges:
        adj[a].append(b)
        adj[b].append(a)
    loops, seen = [], set()
    for a, b in bedges:
        if (a, b) in seen:
            continue
        loop = [a, b]
        seen.add((a, b))
        seen.add((b, a))
        prev, cur = a, b
        while cur != loop[0]:
            nxt = None
            for x in adj[cur]:
                if x != prev and (cur, x) not in seen:
                    nxt = x
                    break
            if nxt is None:
                break
            seen.add((cur, nxt))
            seen.add((nxt, cur))
            loop.append(nxt)
            prev, cur = cur, nxt
        loops.append(loop[:-1] if loop and loop[-1] == loop[0] else loop)
    return loops


def simplify_loop(loop, upos):
    pts = [upos[i] for i in loop]
    changed = True
    while changed and len(pts) > 3:
        changed = False
        out, m = [], len(pts)
        for i in range(m):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % m]
            u, v = sub(b, a), sub(c, b)
            cr = cross(u, v)
            if math.sqrt(dot(cr, cr)) <= 1e-6 * max(1.0, math.sqrt(dot(u, u))):
                changed = True
                continue
            out.append(b)
        pts = out
    return pts


def area2(pts, n):
    s = 0.0
    for i in range(len(pts)):
        s += dot(cross(pts[i], pts[(i + 1) % len(pts)]), n)
    return 0.5 * s


def ear_clip(pts, n):
    if area2(pts, n) < 0:
        pts = list(reversed(pts))
    idx = list(range(len(pts)))
    out, guard = [], 0

    def inside(p, a, b, c):
        def side(x, y):
            return dot(cross(sub(y, x), sub(p, x)), n)
        return (side(a, b) >= -1e-12 and side(b, c) >= -1e-12
                and side(c, a) >= -1e-12)

    while len(idx) > 3 and guard < 10000:
        guard += 1
        m = len(idx)
        clipped = False
        for k in range(m):
            ia, ib, ic = idx[k - 1], idx[k], idx[(k + 1) % m]
            a, b, c = pts[ia], pts[ib], pts[ic]
            if dot(cross(sub(b, a), sub(c, b)), n) <= 1e-12:
                continue
            if any(j not in (ia, ib, ic) and inside(pts[j], a, b, c) for j in idx):
                continue
            out.append((ia, ib, ic))
            idx.pop(k)
            clipped = True
            break
        if not clipped:
            break
    if len(idx) == 3:
        out.append(tuple(idx))
    return out


def build_faces(upos, tris, scale, cx, cz, miny, wood, detail):
    """One piece's triangles -> flat faces (quads kept, others ear-clipped)."""
    def xf(p):
        return [round((p[0] - cx) * scale, 6),
                round((p[1] - miny) * scale, 6),
                round((p[2] - cz) * scale, 6)]

    groups = {}
    for t in tris:
        n = norm(cross(sub(upos[t[1]], upos[t[0]]), sub(upos[t[2]], upos[t[0]])))
        groups.setdefault(plane_key(n, upos[t[0]]), []).append(t)

    def tri_area(t):
        return 0.5 * math.sqrt(dot(cross(sub(upos[t[1]], upos[t[0]]),
                                       sub(upos[t[2]], upos[t[0]])),
                                 cross(sub(upos[t[1]], upos[t[0]]),
                                       sub(upos[t[2]], upos[t[0]]))))

    def tri_faces(gts, n):
        # Fallback for planes whose outline does not trace cleanly (multiple
        # touching notches, holes, non-manifold vertices): keep the authored
        # triangles. The baker skips borders between coplanar faces, so these
        # stay seamless.
        out = []
        for t in gts:
            nrm = norm(cross(sub(upos[t[1]], upos[t[0]]),
                             sub(upos[t[2]], upos[t[0]])))
            if dot(nrm, n) < 0:
                t = (t[0], t[2], t[1])
            out.append({"points": [xf(upos[i]) for i in t],
                        "normal": [round(c, 9) for c in n],
                        "color": wood})
        return out

    faces = []
    for (nx, ny, nz, _d), gts in groups.items():
        n = norm((nx, ny, nz))
        loops = boundary_loops(gts)
        polys = []
        simple = True
        for loop in loops:
            pts = simplify_loop(loop, upos)
            if len(pts) < 3:
                continue
            keys = {(round(p[0], 5), round(p[1], 5), round(p[2], 5))
                    for p in pts}
            if len(keys) != len(pts):
                simple = False
                break
            if area2(pts, n) < 0:
                pts = list(reversed(pts))
            polys.append(pts)
        total = sum(tri_area(t) for t in gts)
        got = sum(abs(area2(p, n)) for p in polys)
        if (not simple or not polys or
                abs(got - total) > 1e-4 + 0.02 * total):
            faces += tri_faces(gts, n)
            continue
        for pts in polys:
            if len(pts) <= 4:
                faces.append({"points": [xf(p) for p in pts],
                              "normal": [round(c, 9) for c in n],
                              "color": wood})
            else:
                maxe = 0.0
                for i in range(len(pts)):
                    e = sub(pts[i], pts[(i + 1) % len(pts)])
                    maxe = max(maxe, math.sqrt(dot(e, e)) * scale)
                grid = max(1, min(512, int(math.ceil(maxe / detail))))
                for ia, ib, ic in ear_clip(pts, n):
                    faces.append({"points": [xf(pts[ia]), xf(pts[ib]), xf(pts[ic])],
                                  "normal": [round(c, 9) for c in n],
                                  "color": wood, "grid": grid})
    return faces


# --------------------------------------------------------------- assembly ---
def bbox_of(faces):
    pts = [q for f in faces for q in f["points"]]
    mn = [min(p[i] for p in pts) for i in range(3)]
    mx = [max(p[i] for p in pts) for i in range(3)]
    return mn, mx


def assemble_offsets(pieces):
    """Where each timber sits once the joint is closed.

    The author's viewer shows every joint exploded. The two big timbers are
    slid back together along the member axis; then each small key, peg or wedge
    follows the timber it was drawn next to and is driven home until it is
    flush with that timber's surface.
    """
    info = []
    for p in pieces:
        mn, mx = bbox_of([f for s in p["solids"] for f in s["faces"]])
        dims = [mx[i] - mn[i] for i in range(3)]
        vol = dims[0] * dims[1] * dims[2]
        info.append({"id": p["id"], "mn": mn, "mx": mx, "dims": dims,
                     "vol": vol, "c": [(mn[i] + mx[i]) / 2 for i in range(3)],
                     "long": max(range(3), key=lambda i: dims[i])})
    anchor = max(info, key=lambda q: q["vol"])
    big = [q for q in info if q["vol"] >= 0.35 * anchor["vol"]]
    offsets = {anchor["id"]: [0.0, 0.0, 0.0]}
    gap = 0.001

    for q in big:
        if q is anchor:
            continue
        delta = [q["c"][i] - anchor["c"][i] for i in range(3)]
        sep = max(range(3), key=lambda i: abs(delta[i]))
        off = [0.0, 0.0, 0.0]
        parallel = (anchor["dims"][anchor["long"]] > 0
                    and q["dims"][anchor["long"]] > 0.5 * anchor["dims"][anchor["long"]])
        if parallel and anchor["long"] == q["long"]:
            # Two halves of one member: align the cross-section, then close
            # the gap along the member if the halves are not interlocked.
            for ax in range(3):
                if ax == anchor["long"]:
                    continue
                if abs(delta[ax]) > 0.12 * max(anchor["dims"][ax], 1e-6):
                    off[ax] = -delta[ax]
            lo = anchor["long"]
            a0, a1 = anchor["mn"][lo], anchor["mx"][lo]
            b0, b1 = q["mn"][lo], q["mx"][lo]
            if b0 >= a1 + gap:
                off[lo] = (a1 + gap) - b0
            elif b1 <= a0 - gap:
                off[lo] = (a0 - gap) - b1
        else:
            # Tenon: slide it into the mortise half a post deep.
            perp = [i for i in range(3) if i != sep]
            depth = 0.5 * min(anchor["dims"][i] for i in perp)
            if delta[sep] > 0:
                off[sep] = (anchor["mx"][sep] - depth) - q["mn"][sep]
            else:
                off[sep] = (anchor["mn"][sep] + depth) - q["mx"][sep]
        offsets[q["id"]] = [round(v, 6) for v in off]

    def gap_to(q, parent):
        total = 0.0
        for i in range(3):
            g = max(q["mn"][i] - parent["mx"][i],
                    parent["mn"][i] - q["mx"][i], 0.0)
            total += g * g
        return total

    for q in info:
        if q in big:
            continue
        # The key lies beside the timber it belongs to in the exploded view:
        # adopt that timber's travel, then drive the key in until it is flush.
        parent = min(big, key=lambda b: gap_to(q, b))
        off = list(offsets[parent["id"]])
        p_mn = [parent["mn"][i] + off[i] for i in range(3)]
        p_mx = [parent["mx"][i] + off[i] for i in range(3)]
        q_mn = [q["mn"][i] + off[i] for i in range(3)]
        q_mx = [q["mx"][i] + off[i] for i in range(3)]
        axis, best = max(((i, max(q_mn[i] - p_mx[i], p_mn[i] - q_mx[i], 0.0))
                          for i in range(3)), key=lambda t: t[1])
        if best > 2 * gap:
            depth = min(q["dims"][axis], p_mx[axis] - p_mn[axis])
            if q_mn[axis] >= p_mx[axis]:
                off[axis] += (p_mx[axis] - depth) - q_mn[axis]
            else:
                off[axis] += (p_mn[axis] + depth) - q_mx[axis]
        offsets[q["id"]] = [round(v, 6) for v in off]
    return offsets


# ----------------------------------------------------------------- naming ---
def name_pieces(piece_faces):
    """Largest timbers first, stubby end/loose pieces last."""
    stats = []
    for faces in piece_faces:
        mn, mx = bbox_of(faces)
        dims = [mx[i] - mn[i] for i in range(3)]
        stats.append((dims[0] * dims[1] * dims[2], faces))
    stats.sort(key=lambda s: -s[0])
    names, nkeys = [], 0
    for i, (vol, _f) in enumerate(stats):
        if i < 2:
            names.append("part-" + "ab"[i])
        else:
            nkeys += 1
            names.append("key" if nkeys == 1 else "key-%d" % nkeys)
    return [n for n in names], [f for _v, f in stats]


def build_level(capture, meta, detail=0.06, scale=0.001):
    pos, nrm, tris = decode_capture(capture)
    upos, uid = weld_positions(pos)
    comps = orient_and_split(upos, uid, nrm, tris)

    all_pts = [upos[i] for c in comps for t in c for i in t]
    miny = min(p[1] for p in all_pts)
    cx = 0.5 * (min(p[0] for p in all_pts) + max(p[0] for p in all_pts))
    cz = 0.5 * (min(p[2] for p in all_pts) + max(p[2] for p in all_pts))

    wood = [0.9137254901960784, 0.7607843137254902, 0.5490196078431373]
    face_sets = [build_faces(upos, c, scale, cx, cz, miny, wood, detail)
                 for c in comps]
    names, ordered = name_pieces(face_sets)

    pieces = []
    for pid, faces in zip(names, ordered):
        pieces.append({"id": pid, "name": pid.replace("-", " ").title(),
                       "kind": "joint", "solids": [{"faces": faces}]})

    level = {
        "id": meta["id"],
        "index": -1,
        "chapter": 0,
        "number": 0,
        "title": meta["title"],
        "jp": meta.get("jp", ""),
        "gloss": meta.get("gloss", ""),
        "guidance": meta.get("guidance", ""),
        "forReal": "",
        "fact": "",
        "scale": 1.0,
        "gift": "",
        "mark": "",
        "masterOf": "",
        "source": meta["source"],
        "assemble": assemble_offsets(pieces),
        "pieces": pieces,
    }
    return level


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("capture")
    ap.add_argument("out")
    ap.add_argument("--id", required=True)
    ap.add_argument("--title", default=None)
    ap.add_argument("--jp", default="")
    ap.add_argument("--gloss", default="")
    ap.add_argument("--guidance", default="")
    ap.add_argument("--uid", required=True, help="Sketchfab model uid")
    ap.add_argument("--author", default="thejoinery")
    ap.add_argument("--author-url", default="https://sketchfab.com/thejoinery")
    ap.add_argument("--license", default="CC BY 4.0")
    ap.add_argument("--license-url",
                    default="http://creativecommons.org/licenses/by/4.0/")
    ap.add_argument("--url", default=None,
                    help="canonical model page (default: uid-only Sketchfab URL)")
    ap.add_argument("--detail", type=float, default=0.06)
    args = ap.parse_args()

    title = args.title or args.id.replace("-", " ").title()
    source = {
        "title": title,
        "author": args.author,
        "authorUrl": args.author_url,
        "url": args.url or ("https://sketchfab.com/3d-models/" + args.uid),
        "license": args.license,
        "licenseUrl": args.license_url,
        "modifications": ("split into its separate timbers, flat normals "
                          "rebuilt, scaled from millimetres to metres, centred "
                          "on x/z with the lowest point at y=0, coplanar faces "
                          "merged, sunset lighting baked; the baking rig's "
                          "ground slab is omitted"),
        "credit": ('"%s" by %s (%s), %s (%s). Modified: split into timbers, '
                   'flat normals rebuilt, scaled from millimetres, sunset '
                   'lighting baked, ground omitted.'
                   % (title, args.author, args.author_url, args.license,
                      args.license_url)),
    }
    level = build_level(args.capture, {
        "id": args.id, "title": title, "jp": args.jp, "gloss": args.gloss,
        "guidance": args.guidance, "source": source,
    }, detail=args.detail)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    json.dump([level], open(args.out, "w"), indent=1)
    print("%-38s %d pieces" % (args.id, len(level["pieces"])))
    for p in level["pieces"]:
        nf = sum(len(s["faces"]) for s in p["solids"])
        print("   %-8s %3d faces  offset %s" % (p["id"], nf,
              level["assemble"][p["id"]]))


if __name__ == "__main__":
    main()
