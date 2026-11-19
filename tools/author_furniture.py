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
# Draw-bore pins are the same timber, soaked a shade darker so the pegs read.
PIN_WOOD = [0.7176470588235294, 0.5607843137254902, 0.3607843137254902]

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

# The rail pins are driven from above, under the top, so they cannot be pulled
# out until the top has lifted: they ride the same 60 mm lift as the planks
# (bake.py leaves a piece with an approach path on its timber track).
APPROACH.update({pid: [(0.0, 0.06, 0.0), (0.0, 0.06, 0.0)] for pid in (
    "pin-rail-left-near", "pin-rail-left-far",
    "pin-rail-right-near", "pin-rail-right-far")})

# Draw-bore pins, six millimetres of peg through two timbers apiece:
#
#   * one through each leg into the end-apron tenon, driven from the leg's
#     outer face (the tenon's hidden wedge slot sits below the peg);
#   * one down through each long apron into a cross-rail tenon, the head sunk
#     2 mm below the apron top because the top rests there;
#   * one through each outer top plank's edge into a leg tab.
#
# Entries are (id, name, start end, finish end, timbers crossed, explode).
# Positions are millimetres in the coffee-table frame used by build_parts;
# the explode vector is metres in the catalogue frame and runs along the peg.
PIN_R = 3.0
PIN_BORE = 3.2
PINS = [
    ("pin-corner-near-left", "front left corner pin",
     (47, -222, 315), (104, -222, 315),
     ("leg-near-left", "apron-end-left"), (-0.09, 0.0, 0.0)),
    ("pin-corner-near-right", "front right corner pin",
     (1296, -222, 315), (1353, -222, 315),
     ("leg-near-right", "apron-end-right"), (0.09, 0.0, 0.0)),
    ("pin-corner-far-left", "back left corner pin",
     (47, 222, 315), (104, 222, 315),
     ("leg-far-left", "apron-end-left"), (-0.09, 0.0, 0.0)),
    ("pin-corner-far-right", "back right corner pin",
     (1296, 222, 315), (1353, 222, 315),
     ("leg-far-right", "apron-end-right"), (0.09, 0.0, 0.0)),
    ("pin-rail-left-near", "front left rail pin",
     (492, -234, 267), (492, -234, 332),
     ("apron-side-near", "rail-cross-left"), (0.0, 0.10, 0.0)),
    ("pin-rail-left-far", "back left rail pin",
     (492, 234, 267), (492, 234, 332),
     ("apron-side-far", "rail-cross-left"), (0.0, 0.10, 0.0)),
    ("pin-rail-right-near", "front right rail pin",
     (908, -234, 267), (908, -234, 332),
     ("apron-side-near", "rail-cross-right"), (0.0, 0.10, 0.0)),
    ("pin-rail-right-far", "back right rail pin",
     (908, 234, 267), (908, 234, 332),
     ("apron-side-far", "rail-cross-right"), (0.0, 0.10, 0.0)),
    ("pin-top-near-left", "front left top pin",
     (77, -303, 338), (77, -258, 338),
     ("top-near-outer", "leg-near-left"), (0.0, 0.0, -0.10)),
    ("pin-top-near-right", "front right top pin",
     (1323, -303, 338), (1323, -258, 338),
     ("top-near-outer", "leg-near-right"), (0.0, 0.0, -0.10)),
    ("pin-top-far-left", "back left top pin",
     (77, 303, 338), (77, 258, 338),
     ("top-far-outer", "leg-far-left"), (0.0, 0.0, 0.10)),
    ("pin-top-far-right", "back right top pin",
     (1323, 303, 338), (1323, 258, 338),
     ("top-far-outer", "leg-far-right"), (0.0, 0.0, 0.10)),
]
PIN_OFFSETS = {p[0]: p[5] for p in PINS}

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


def _peg(a, b, radius, sides=16):
    """A faceted peg from a to b: a 16-gon reads round and bakes cheaply.

    The bores use the same prism at ``PIN_BORE``, so the hole's rim and the
    peg's facets share their corners and the mesh stays closed.
    """
    va, vb = cq.Vector(*a), cq.Vector(*b)
    axis = vb - va
    normal = axis.normalized()
    ref = cq.Vector(1, 0, 0) if abs(normal.x) < 0.9 else cq.Vector(0, 0, 1)
    xdir = ref.cross(normal).normalized()
    plane = cq.Plane(origin=va, xDir=xdir, normal=normal)
    return cq.Workplane(plane).polygon(sides, 2 * radius) \
        .extrude(axis.Length).val()


def add_pins(parts):
    """Bore each pin's hole and add the pegs as pieces.

    The peg is checked against the timbers before anything is cut: sampling
    the pin's axis must find exactly the timbers named in ``PINS``, so a pin
    can never quietly bore a third piece or miss one it was meant to lock.
    """
    shapes = {pid: sh.val() for pid, _name, sh in parts}
    for pid, _name, a, b, timbers, _explode in PINS:
        va, vb = cq.Vector(*a), cq.Vector(*b)
        axis = vb - va
        length = axis.Length
        axis = axis.normalized()
        crossed = set()
        for i in range(61):
            p = va + axis * (length * i / 60.0)
            for tid, sh in shapes.items():
                if sh.isInside((p.x, p.y, p.z), 1e-6):
                    crossed.add(tid)
        if crossed != set(timbers):
            raise SystemExit("pin %s crosses %s, expected %s"
                             % (pid, sorted(crossed), sorted(timbers)))

    pegs = []
    for pid, name, a, b, timbers, _explode in PINS:
        # The rail pins are driven from above: their bore opens through the
        # apron top, leaving the head sunk 2 mm in a recess, so the peg can be
        # drawn out again (a blind bore under a 2 mm skin would trap it).
        top = (b[0], b[1], b[2] + 4) if pid.startswith("pin-rail") else b
        hole = _peg(a, top, PIN_BORE)
        for tid in timbers:
            shapes[tid] = shapes[tid].cut(hole)
        pegs.append((pid, name,
                     cq.Workplane("XY", obj=_peg(a, b, PIN_R))))

    out = [(pid, name, cq.Workplane("XY", obj=shapes[pid]))
           for pid, name, _sh in parts]
    out += pegs
    return out


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
    return add_pins(parts), d


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
        offset = EXPLODE.get(pid) or PIN_OFFSETS.get(pid) or (0.0, 0.0, 0.0)
        peg = pid in PIN_OFFSETS
        upos, tris = to_source(shape, offset,
                               PIN_WOOD if peg else WOOD, 0.2)
        faces = ij.build_faces(upos, tris, 1.0, 0.0, 0.0, 0.0,
                               PIN_WOOD if peg else WOOD, 0.04)
        pieces.append({"id": pid, "name": name, "kind": "furniture",
                       "role": "pin" if peg else "timber",
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
            "are recessed over the legs' 8 mm locating tabs. Twelve draw-bore pins "
            "lock it: one through each leg into an end-apron tenon, one down "
            "through each long apron into a cross-rail tenon, and one through "
            "each outer top plank into a leg tab. The pins withdraw first, then "
            "the top lifts off as one piece and fans open, which is how the "
            "frame's joinery is shown."),
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
                "frame, twelve draw-bore pins added to lock the joints, exploded "
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
