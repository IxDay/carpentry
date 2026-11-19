#!/usr/bin/env python3
"""Import a CadQuery furniture project as a catalogue-shaped model source.

The first piece is the coffee table in ``~/Documents/Dev/platipy/coffee-table``:
four legs, four aprons, two cross rails and a four-plank top, assembled from the
part solids in that project and written in the catalogue's metre, y-up form so
that ``bake.py`` can give it the same paper-sunrise lighting and ``assemble``
clip as the joints.

CadQuery is not a dependency of this repository, so run the tool with the
coffee-table project's own environment:

    cd ~/Documents/Dev/platipy/coffee-table
    pixi run python ~/Documents/Dev/misc/joinery/tools/author_furniture.py

The table is published as a whole piece. The top is the moving part: the clip
lifts the four planks off the frame and fans them out, so the frame's joinery is
visible in the open pose. The offsets live in ``EXPLODE`` below and become the
``assemble`` vectors, exactly as in ``author_joint.py``.

Two things in the source project do not close, and are resolved here:

* The top's leg pockets are 40-60 mm from the outer edge, but the legs sit at
  30-50 mm once their apron notches are lined up with the long aprons. The
  pockets are re-cut 10 mm outboard on the outer planks; nothing else on the
  top changes.
* ``total_height = 370`` in ``dimensions.py`` is 8 mm more than the modelled
  parts reach. The apron tops and the legs' shoulders are at 334, the top is
  28 thick, so the table is 362 high. The top seats on 334 and the legs' 8 mm
  tabs enter the top's pockets. The published height is 362.
"""
import argparse
import json
import os
import sys

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import import_joint as ij  # noqa: E402  (needs HERE on the path)

# Display-sRGB wood colour, the same timber as the authored joints.
WOOD = [0.9137254901960784, 0.7607843137254902, 0.5490196078431373]
# Wedges are the same timber, a shade darker so they read.
WEDGE_WOOD = [0.7176470588235294, 0.5607843137254902, 0.3607843137254902]

# (piece id, name, explode offset in metres, in the catalogue frame)
EXPLODE = {
    "top-near-outer": (0.0, 0.20, -0.16),
    "top-near-inner": (0.0, 0.26, -0.04),
    "top-far-inner": (0.0, 0.26, 0.04),
    "top-far-outer": (0.0, 0.20, 0.16),
}

# The top's outer planks sit over the legs' 8 mm tabs with no side clearance,
# so the fan has to start with a straight lift; a diagonal would drag the
# pocket walls sideways through the tabs.  The planks then rise to their own
# heights (the inner pair higher) and only slide sideways once they are stacked
# clear of one another.
APPROACH = {
    pid: [(0.0, 0.06, 0.0), (0.0, e[1], 0.0)] for pid, e in EXPLODE.items()
}

# Each cross-rail tenon is locked in its long-apron mortise by a wood wedge
# driven down from the apron top into a tapered gap beside the tenon, 3 mm wide
# at the top and 1.5 mm at the bottom.  The head is flush with the apron top,
# so the top rests on it and the planks must lift before a wedge can be drawn:
# the wedges ride the same 60 mm lift (bake.py leaves a piece with an approach
# path on its timber track) and then rise clear.
#
# (id, name, apron, rail, x of the tenon's edge, direction towards the gap in x,
# y of the apron's inner face, direction into the apron in y)
WEDGE_DEPTH = 8.0        # the tenon's length, the mortise's depth
WEDGE_BOTTOM = 280.0     # the mortise's floor in z; the apron top is 334
WEDGE_TOP = 334.0
WEDGES = [
    ("wedge-rail-left-near", "front left cross-rail wedge",
     "apron-side-near", "rail-cross-left", 499.0, 1, -230.0, -1),
    ("wedge-rail-left-far", "back left cross-rail wedge",
     "apron-side-far", "rail-cross-left", 499.0, 1, 230.0, 1),
    ("wedge-rail-right-near", "front right cross-rail wedge",
     "apron-side-near", "rail-cross-right", 901.0, -1, -230.0, -1),
    ("wedge-rail-right-far", "back right cross-rail wedge",
     "apron-side-far", "rail-cross-right", 901.0, -1, 230.0, 1),
]
WEDGE_OFFSET = (0.0, 0.10, 0.0)
WEDGE_IDS = [w[0] for w in WEDGES]
APPROACH.update({pid: [(0.0, 0.06, 0.0), (0.0, 0.06, 0.0)]
                 for pid in WEDGE_IDS})

# Part bounding box in the Coffee-table project: 1400 x 600 x 362 mm.
CENTRE_X = 700.0
CENTRE_Y = 0.0
FLOOR_Z = 0.0
SCALE = 0.001


def xform(shape, rot_z=0.0, translate=(0.0, 0.0, 0.0), mirror_y=False):
    """Mirror in y, then turn about z, then translate (millimetres)."""
    out = shape
    if mirror_y:
        out = out.mirror("XZ")
    if rot_z:
        out = out.rotate((0, 0, 0), (0, 0, 1), rot_z)
    if any(translate):
        out = out.translate(translate)
    return out


def fixed_top_external(top_external):
    """Re-cut the outer planks' leg pockets 10 mm outboard (see module doc)."""
    # The authored pocket sits at y 40..60 on a plank whose local y runs 0..150.
    # Fill it, then cut the corrected pocket at y 30..50. Both ends of the plank
    # carry a pocket (x 50..104 and 1296..1350).
    old = (cq.Workplane("XY")
           .pushPoints([(77, 50), (1323, 50)])
           .rect(54, 20).extrude(8))
    new = (cq.Workplane("XY")
           .pushPoints([(77, 40), (1323, 40)])
           .rect(54, 20).extrude(8))
    return top_external.union(old).cut(new)


def _wedge(x, dx, y, dy):
    """The tapered gap (and so the wedge) beside a tenon, in millimetres."""
    pts = [(x, WEDGE_BOTTOM), (x + dx * 1.5, WEDGE_BOTTOM),
           (x + dx * 3.0, WEDGE_TOP), (x, WEDGE_TOP)]
    plane = cq.Workplane("XZ", origin=(0, y, 0))
    # The XZ plane faces -y, so a positive extrusion runs towards -y.
    return plane.polyline(pts).close().extrude(-dy * WEDGE_DEPTH).val()


def add_wedges(parts):
    """Cut each wedge's gap into its long apron and add the wedge as a piece."""
    shapes = {pid: sh.val() for pid, _name, sh in parts}
    wedges = []
    for pid, name, apron, _rail, x, dx, y, dy in WEDGES:
        wedge = _wedge(x, dx, y, dy)
        shapes[apron] = shapes[apron].cut(wedge)
        wedges.append((pid, name, cq.Workplane("XY", obj=wedge)))
    out = [(pid, name, cq.Workplane("XY", obj=shapes[pid]))
           for pid, name, _sh in parts]
    return out + wedges


def build_parts(project):
    """Import the Coffee-table parts and place them in the table's frame."""
    sys.path.insert(0, project)
    import dimensions as d  # noqa: F401  (the project's parameters)
    from aprons import end_apron, end_apron_internal, side_apron
    from legs import leg
    from top_external import top_external
    from top_internal import top_internal

    # The frame is built in y 0..600; the top is centred on y 0. Translate the
    # whole frame by -300 so both use the top's frame.
    fy = -d.total_width / 2.0

    parts = [
        ("leg-near-left", "front left leg",
         xform(leg, 0, (77, fy + 30, 0))),
        ("leg-near-right", "front right leg",
         xform(leg, 0, (1323, fy + 30, 0))),
        ("leg-far-left", "back left leg",
         xform(leg, 180, (77, fy + 570, 0))),
        ("leg-far-right", "back right leg",
         xform(leg, 180, (1323, fy + 570, 0))),
        # The long aprons carry the cross-rail mortises on their inner face, so
        # the near one is mirrored to keep that face towards the table centre.
        ("apron-side-near", "front long apron",
         xform(side_apron, 0, (30, fy + 60, 302), mirror_y=True)),
        ("apron-side-far", "back long apron",
         xform(side_apron, 0, (30, fy + 540, 302))),
        ("apron-end-left", "left end apron",
         xform(end_apron, 90, (77, fy + 99, 302))),
        ("apron-end-right", "right end apron",
         xform(end_apron, 90, (1323, fy + 99, 302))),
        ("rail-cross-left", "left cross rail",
         xform(end_apron_internal, 90, (492, fy + 415, 302))),
        ("rail-cross-right", "right cross rail",
         xform(end_apron_internal, 90, (908, fy + 415, 302))),
    ]

    top = fixed_top_external(top_external)
    parts += [
        ("top-near-outer", "front outer top plank",
         xform(top, 0, (0, -2 * d.top_width, 334))),
        ("top-near-inner", "front inner top plank",
         xform(top_internal, 0, (0, -d.top_width, 334))),
        ("top-far-inner", "back inner top plank",
         xform(top_internal, 0, (0, 0, 334))),
        ("top-far-outer", "back outer top plank",
         top.mirror("XZ", basePointVector=(0, d.top_width, 0))
         .translate((0, 0, 334))),
    ]
    return add_wedges(parts), d


def check(parts):
    """Every part must be one closed solid and no two may interpenetrate."""
    problems = 0
    for pid, _name, shape in parts:
        solid = shape.val()
        if len(solid.Solids()) != 1 or not solid.isValid():
            print("  %-18s not one valid solid" % pid)
            problems += 1
        for other_id, _n, other in parts:
            if other_id <= pid:
                continue
            try:
                inter = solid.intersect(other.val())
            except Exception as exc:  # disjoint solids can raise in OCC
                print("  %-18s / %-18s intersect failed: %s" % (pid, other_id, exc))
                problems += 1
                continue
            volume = inter.Volume() if inter else 0.0
            if volume > 1e-6:
                print("  %-18s / %-18s overlap %.2f mm3" % (pid, other_id, volume))
                problems += 1
    return problems


def to_source(shape, offset, colour=WOOD, detail=0.2):
    """CadQuery millimetres/z-up -> catalogue metres/y-up, then explode."""
    vertices, triangles = shape.val().tessellate(detail)
    pos = [(v.x, v.y, v.z) for v in vertices]

    def xf(p):
        return (
            round((p[0] - CENTRE_X) * SCALE + offset[0], 6),
            round((p[2] - FLOOR_Z) * SCALE + offset[1], 6),
            round((p[1] - CENTRE_Y) * SCALE + offset[2], 6),
        )

    upos = [xf(p) for p in pos]
    # Weld per part: tessellation repeats vertices along shared edges.
    key, welded, remap = {}, [], []
    for p in upos:
        k = tuple(round(c, 6) for c in p)
        if k not in key:
            key[k] = len(welded)
            welded.append(p)
        remap.append(key[k])
    tris = []
    for a, b, c in triangles:
        # The frame swap (y, z) -> (z, y) is a reflection, so reverse each
        # triangle as well; otherwise every part is inside-out and lit from
        # within, and a single-sided glTF material would cull its outside.
        t = (remap[a], remap[c], remap[b])
        if len(set(t)) == 3:
            tris.append(t)
    volume = sum(ij.dot(ij.cross(welded[a], welded[b]), welded[c])
                 for a, b, c in tris) / 6.0
    if volume <= 0.0:
        raise SystemExit("part did not come out wound outwards (volume %.6f)"
                         % volume)
    return welded, tris


def write_source(parts, out_path):
    pieces = []
    assemble = {}
    for pid, name, shape in parts:
        offset = EXPLODE.get(pid) or (WEDGE_OFFSET if pid in WEDGE_IDS else (0.0, 0.0, 0.0))
        peg = pid in WEDGE_IDS
        upos, tris = to_source(shape, offset,
                               WEDGE_WOOD if peg else WOOD, 0.2)
        faces = ij.build_faces(upos, tris, 1.0, 0.0, 0.0, 0.0,
                               WEDGE_WOOD if peg else WOOD, 0.04)
        pieces.append({"id": pid, "name": name, "kind": "furniture",
                       "role": "wedge" if peg else "timber",
                       "solids": [{"faces": faces}]})
        assemble[pid] = [round(-c, 9) for c in offset]

    level = {
        "id": "coffee-table",
        "index": -1,
        "chapter": 0,
        "number": 0,
        "title": "Coffee table",
        "jp": "",
        "gloss": "",
        "guidance": (
            "Four legs are notched on their outer faces to take the long aprons, "
            "which run the whole length and are themselves mortised for two cross "
            "rails. The end aprons are tenoned through the legs and the long "
            "aprons and wedged outside; the top is four planks whose outer boards "
            "are recessed over the legs' 8 mm locating tabs, and the planks lock "
            "together through the aprons and rails. Four wood wedges, driven "
            "down beside each cross-rail tenon, lock the rails into the long "
            "aprons. The top lifts, the wedges rise clear, and the planks fan "
            "open, which is how the frame's joinery is shown."),
        "fact": "",
        "forReal": "",
        "scale": 1.0,
        "gift": "",
        "mark": "",
        "masterOf": "",
        "source": {
            "title": "Coffee table",
            "author": "Maxime Vidori",
            "authorUrl": "https://github.com/IxDay/coffee-table",
            "url": "https://github.com/IxDay/coffee-table",
            "license": "CC BY 4.0",
            "licenseUrl": "http://creativecommons.org/licenses/by/4.0/",
            "modifications": (
                "Designed in CadQuery; parts imported and assembled here, the "
                "outer top planks' leg pockets re-cut 10 mm outboard to seat the "
                "frame, four wedges added to lock the cross rails, exploded "
                "and given the catalogue's paper-sunrise lighting"),
        },
        "tab": "furniture",
        "dimensions": "1400 \u00d7 600 \u00d7 362 mm",
        "duration": 10.0,
        "approach": APPROACH,
        "assemble": assemble,
        "pieces": pieces,
    }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as fh:
        json.dump([level], fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    return level


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--coffee-table",
                    default=os.path.expanduser("~/Documents/Dev/platipy/coffee-table"),
                    help="path to the CadQuery coffee-table project")
    ap.add_argument("--out",
                    default=os.path.join(ROOT, "furniture", "sources",
                                         "coffee-table.json"))
    args = ap.parse_args()

    parts, _d = build_parts(args.coffee_table)
    print("imported %d parts" % len(parts))
    problems = check(parts)
    if problems:
        sys.exit("%d geometry problem(s); source not written" % problems)
    level = write_source(parts, args.out)
    faces = sum(len(s["faces"]) for p in level["pieces"] for s in p["solids"])
    print("coffee-table  %2d pieces  %4d faces -> %s"
          % (len(level["pieces"]), faces, args.out))


if __name__ == "__main__":
    main()
