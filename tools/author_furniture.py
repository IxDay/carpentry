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

The table's geometry, including the corrected leg pockets and the four
cross-rail wedges, lives in the coffee-table project (``table.py``); this tool
only places it in the catalogue frame, adds the explode and approach motion and
writes the source. The table stands 362 mm high (``dimensions.table_height``):
the top seats on the frame at 334 and the legs' 8 mm tabs enter its pockets.
"""
import argparse
import json
import os
import sys

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

# The wedges are modelled with the table (wedges.py in the coffee-table
# project).  Each is driven down beside a cross-rail tenon and its head is flush
# with the apron top, so the top rests on it: the planks must lift before a
# wedge can be drawn.  The wedges ride the same 60 mm lift (bake.py leaves a
# piece with an approach path on its timber track) and then rise clear.
WEDGE_IDS = ["wedge-rail-%s-%s" % (rail, where)
             for rail in ("left", "right") for where in ("near", "far")]
WEDGE_OFFSET = (0.0, 0.10, 0.0)
APPROACH.update({pid: [(0.0, 0.06, 0.0), (0.0, 0.06, 0.0)]
                 for pid in WEDGE_IDS})

# Part bounding box in the Coffee-table project: 1400 x 600 x 362 mm.
CENTRE_X = 700.0
CENTRE_Y = 0.0
FLOOR_Z = 0.0
SCALE = 0.001


def build_parts(project):
    """The coffee-table project's parts, placed and closed (``table.parts``)."""
    sys.path.insert(0, project)
    import dimensions as d
    from table import parts
    return parts(), d


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
