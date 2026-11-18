#!/usr/bin/env python3
"""Export a joint as printable meshes for a slicer such as Ultimaker Cura.

The catalogue sources store each timber in its exploded pose plus an
``assemble`` vector back to the closed joint.  For printing we want the closed
pose (a tenon is only the right size when it is seated), so this tool shifts
every piece home, triangulates its faces and lays the pieces out side by side
on the bed.

Output, in millimetres:

    <outdir>/<id>.3mf             all pieces as separate, named objects
    <outdir>/<id>_<piece>.stl     one binary STL per piece

3MF is the convenient one: Cura imports the file once and gives you one
selected object per timber, already sitting on the build plate.  STL has no
units, so the scale below is baked into the numbers either way.

    python3 export_print.py ../joints/sources/watari-ago-niju-hozo-shikuchi.json \
        --outdir ../print --scale 0.1

``--scale 0.1`` prints the joint at 1:10 (the 120 mm timbers come out 12 mm
square).  Use ``--scale 1`` for full size and ``--scale 0.05`` for 1:20.
"""
import argparse
import json
import os
import struct
import sys
import zipfile

from check_sources import tri_faces

GAP = 12.0                  # mm between pieces on the bed
BED = 220.0                 # mm, only used to warn when the row will not fit


# --------------------------------------------------------------- geometry --
def load_closed(path):
    """Return (id, [piece]) with every piece moved to the closed pose."""
    cat = json.load(open(path))
    j = cat[0]
    asm = j.get("assemble") or {}
    pieces = []
    for p in j["pieces"]:
        d = asm.get(p["id"], [0.0, 0.0, 0.0])
        faces = []
        for solid in p["solids"]:
            for f in solid["faces"]:
                faces.append({
                    "points": [[float(q[k]) + d[k] for k in range(3)]
                               for q in f["points"]],
                    "normal": f["normal"],
                })
        pieces.append((p["id"], p.get("name") or p["id"], faces))
    return j, pieces


def signed_volume(tris):
    """Six times the signed volume; positive when the winding is outward."""
    total = 0.0
    for a, b, c in tris:
        total += (a[0] * (b[1] * c[2] - b[2] * c[1])
                  - a[1] * (b[0] * c[2] - b[2] * c[0])
                  + a[2] * (b[0] * c[1] - b[1] * c[0]))
    return total


def piece_triangles(faces):
    tris = tri_faces(faces)
    if signed_volume(tris) < 0:          # source winding is inward; flip it
        tris = [(a, c, b) for a, b, c in tris]
    return tris


def rotations():
    """The 24 axis-aligned rotations with positive determinant."""
    out = []
    for perm in ((0, 1, 2), (0, 2, 1), (1, 0, 2),
                 (1, 2, 0), (2, 0, 1), (2, 1, 0)):
        for sx in (1, -1):
            for sy in (1, -1):
                for sz in (1, -1):
                    m = [None, None, None]
                    for i, p in enumerate(perm):
                        m[i] = [0.0, 0.0, 0.0]
                        m[i][p] = (sx, sy, sz)[i]
                    if (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1])
                            - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
                            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0])) > 0:
                        out.append(m)
    return out


def apply_rot(m, p):
    return tuple(m[i][0] * p[0] + m[i][1] * p[1] + m[i][2] * p[2]
                 for i in range(3))


def face_areas(tris):
    """Return (contact, overhang, zmin, top) for the piece in its pose.

    ``contact`` is the downward-facing area sitting on the bed, ``overhang``
    the downward-facing area above it, and ``top`` how high that overhang gets.
    """
    zmin = min(p[2] for t in tris for p in t)
    contact = overhang = top = 0.0
    for a, b, c in tris:
        u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
        n = (u[1] * v[2] - u[2] * v[1],
             u[2] * v[0] - u[0] * v[2],
             u[0] * v[1] - u[1] * v[0])
        area = 0.5 * (n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5
        if area <= 0 or n[2] / (2.0 * area) >= -0.9:
            continue
        if all(abs(p[2] - zmin) < 1e-6 for p in (a, b, c)):
            contact += area
        else:
            overhang += area
            top = max(top, a[2], b[2], c[2])
    return contact, overhang, zmin, top - zmin


def rest_on_face(tris):
    """Sit the piece on z = 0, changing its pose only if it would hang.

    Printing each timber in the pose it holds in the joint is the least
    surprising layout and keeps the assembled joint readable next to the parts.
    A pose is accepted when almost all of its downward-facing area is on the
    bed; otherwise the 24 axis-aligned rotations are scored on contact minus
    twice the overhang, and the best one is used.  The beam is the piece that
    needs this: its 18 mm chin hangs below the body, so at rest most of the
    beam would print in mid-air, while flipped it sits flat with the chin up.
    """
    contact, overhang, _, top = face_areas(tris)
    if overhang <= 0.15 * contact:
        r = tris
    else:
        best = None
        for m in rotations():
            cand = [[apply_rot(m, p) for p in t] for t in tris]
            c, o, _, _ = face_areas(cand)
            score = c - 2.0 * o
            if best is None or round(score, 6) > round(best[0], 6):
                best = (score, cand)
        r = best[1]
        _, overhang, _, top = face_areas(r)
    zmin = min(p[2] for t in r for p in t)
    return ([[(p[0], p[1], p[2] - zmin) for p in t] for t in r], overhang, top)


def to_bed(tris, scale):
    """Metres -> millimetres and y-up -> z-up.

    (x, y, z) -> (x, -z, y) is a rotation, so triangle winding is preserved.
    The piece is not moved to the origin; ``layout`` does that.
    """
    s = scale * 1000.0
    return [tuple((p[0] * s, -p[2] * s, p[1] * s) for p in t) for t in tris]


def support_note(overhang, top):
    if overhang < 1e-6:
        return "flat, no supports"
    if top <= 12.0:                      # a shallow pocket ceiling, bridged
        return "%.0f mm2 bridge" % overhang
    return "%.0f mm2 needs supports" % overhang


def bbox(flat):
    return ([min(p[k] for p in flat) for k in range(3)],
            [max(p[k] for p in flat) for k in range(3)])


def layout(pieces):
    """Drop every piece onto z = 0 and pack them left to right along x.

    Each piece keeps its own footprint; ``GAP`` separates the bounding boxes so
    the slicer shows them as distinct objects rather than one merged blob.
    """
    placed = []
    x = 0.0
    for pid, name, tris in pieces:
        lo, hi = bbox([p for t in tris for p in t])
        dx, dy, dz = x - lo[0], -lo[1], -lo[2]
        moved = [[tuple((p[0] + dx, p[1] + dy, p[2] + dz)) for p in t]
                 for t in tris]
        placed.append((pid, name, moved))
        x += (hi[0] - lo[0]) + GAP
    return placed, x - GAP


# ----------------------------------------------------------------- 3mf out --
CT = """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>
"""
RELS = """<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>
"""


def write_3mf(path, title, pieces):
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">',
             ' <metadata name="Title">%s</metadata>' % esc(title),
             ' <metadata name="Application">carpentry export_print.py</metadata>',
             ' <resources>']
    for i, (pid, name, tris) in enumerate(pieces, start=1):
        verts, index = {}, []
        for tri in tris:
            for p in tri:
                key = (round(p[0], 6), round(p[1], 6), round(p[2], 6))
                if key not in verts:
                    verts[key] = len(verts)
                index.append(verts[key])
        parts.append('  <object id="%d" name="%s" type="model">' % (i, esc(name)))
        parts.append('   <mesh>')
        parts.append('    <vertices>')
        for key in verts:
            parts.append('     <vertex x="%.6f" y="%.6f" z="%.6f"/>' % key)
        parts.append('    </vertices>')
        parts.append('    <triangles>')
        for k in range(0, len(index), 3):
            parts.append('     <triangle v1="%d" v2="%d" v3="%d"/>'
                         % (index[k], index[k + 1], index[k + 2]))
        parts.append('    </triangles>')
        parts.append('   </mesh>')
        parts.append('  </object>')
    parts.append(' </resources>')
    parts.append(' <build>')
    for i in range(1, len(pieces) + 1):
        parts.append('  <item objectid="%d"/>' % i)
    parts.append(' </build>')
    parts.append('</model>')
    model = "\n".join(parts) + "\n"
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", CT)
        z.writestr("_rels/.rels", RELS)
        z.writestr("3D/3dmodel.model", model)


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            .replace('"', "&quot;"))


# ----------------------------------------------------------------- stl out --
def write_stl(path, tris):
    with open(path, "wb") as fh:
        fh.write(("binary STL, mm, " + os.path.basename(path)).encode()[:80]
                 .ljust(80, b" "))
        fh.write(struct.pack("<I", len(tris)))
        for a, b, c in tris:
            u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
            v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
            n = (u[1] * v[2] - u[2] * v[1],
                 u[2] * v[0] - u[0] * v[2],
                 u[0] * v[1] - u[1] * v[0])
            ln = (n[0] ** 2 + n[1] ** 2 + n[2] ** 2) ** 0.5 or 1.0
            fh.write(struct.pack("<3f", n[0] / ln, n[1] / ln, n[2] / ln))
            fh.write(struct.pack("<9f", *a, *b, *c))
            fh.write(struct.pack("<H", 0))


# -------------------------------------------------------------------- main --
def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("--outdir", default="../print")
    ap.add_argument("--scale", type=float, default=0.1,
                    help="print scale, 0.1 = 1:10 (default), 1.0 = 1:1")
    ap.add_argument("--gap", type=float, default=None)
    args = ap.parse_args(argv)

    if args.gap is not None:
        GAP = args.gap
    j, pieces = load_closed(args.src)
    jid = j["id"]

    scaled = []
    for pid, name, faces in pieces:
        tris = piece_triangles(faces)
        bed = to_bed(tris, args.scale)
        oriented, overhang, top = rest_on_face(bed)
        scaled.append((pid, name, oriented, (overhang, top)))
    placed, row = layout([(pid, name, t) for pid, name, t, _ in scaled])

    os.makedirs(args.outdir, exist_ok=True)
    path3mf = os.path.join(args.outdir, jid + ".3mf")
    write_3mf(path3mf, j["title"], placed)

    for pid, name, tris in placed:
        write_stl(os.path.join(args.outdir, "%s_%s.stl" % (jid, pid)), tris)

    print("%s  scale 1:%g" % (jid, 1.0 / args.scale))
    over = {pid: a for pid, _, _, a in scaled}
    for pid, name, tris in placed:
        lo, hi = bbox([p for t in tris for p in t])
        print("  %-10s %-10s %6d tris   %5.1f x %5.1f x %5.1f mm   %s"
              % (pid, name, len(tris), hi[0] - lo[0], hi[1] - lo[1],
                 hi[2] - lo[2],
                 support_note(*over[pid])))
    print("  row %.1f mm along the bed; wrote %s and %d STL%s"
          % (row, path3mf, len(placed), "" if len(placed) == 1 else "s"))
    if row > BED:
        print("  note: the row is wider than a %g mm bed; move pieces apart in "
              "the slicer" % BED)


if __name__ == "__main__":
    main(sys.argv[1:])
