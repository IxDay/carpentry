#!/usr/bin/env python3
"""Author multi-beam connection specimens for the joint catalogue.

This tool adds the two specimens whose geometry has direct written backing but
which the 32-sheet catalogue omits:

    watari-ago-shikuchi      渡り頸仕口     two beams crossing over a post
    shihou-sashi-shachi-sen  四方差し車知栓  four beams, paired wedge keys

Geometry uses the same box-CSG and loft helpers as ``author_joint.py``.  The
post takes one tenon per direction, each at its own level inside the beam depth
so that no two tenons share the post's core.  Paired shachi-sen pass through
each tenon from opposite faces.

    python3 author_multi.py                       # all specimens
    python3 author_multi.py watari-ago-shikuchi   # one

Sources are written with the catalogue metadata from ``joint_meta`` already
stamped on.  Bake and preview them with the standard pipeline afterwards.
"""
import json
import os
import sys

from author_joint import (COLOR, JP, OFFSHEET_CREDIT, joint, loft, piece,
                          shift)
from joint_meta import apply as apply_meta

# ----------------------------------------------------------------------------
# Shared dimensions, in metres, in the closed pose.
P = 0.06                    # post half-width, 120 mm square
POST_Y0, POST_Y1 = 0.24, 0.66
BEAM_HALF = 0.045           # 90 mm wide beams
TENON_HALF = 0.030          # 60 mm wide tenons
TENON_LEN = 0.10            # how far the tenon runs into the post
BEAM_OUT = 0.40             # the free end of a beam
KEY_HALF = 0.015            # 30 mm square keys
KEY_TAPER = 0.0015          # ease at the driven tip

POST = [(-P, P), (POST_Y0, POST_Y1), (-P, P)]
KEY_MODS = ("authored from the naming convention and published descriptions "
            "of the joint in closed pose, exploded for the assemble animation, "
            "sunset lighting baked; the baking rig's ground slab is omitted")

# One level per direction, stacked inside the beam's depth.  Each entry is
# (axis, sign, y0, y1): axis 0 = beams along x, axis 1 = beams along z.
X_BANDS = [(0, -1, 0.40, 0.44), (0, +1, 0.44, 0.48)]
Z_BANDS = [(1, -1, 0.48, 0.52), (1, +1, 0.52, 0.56)]
BEAM_Y = (0.40, 0.56)


def band_key_y(y0, y1):
    return ((y0 + y1) / 2 - KEY_HALF, (y0 + y1) / 2 + KEY_HALF)


def tenon_box(axis, sign, y0, y1):
    """The tenon pocket, from the post face inwards, at its own level."""
    if axis == 0:
        return ((-P, -P + TENON_LEN) if sign < 0 else (P - TENON_LEN, P),
                (y0, y1), (-TENON_HALF, TENON_HALF))
    return ((-TENON_HALF, TENON_HALF), (y0, y1),
            (-P, -P + TENON_LEN) if sign < 0 else (P - TENON_LEN, P))


def beam_body(axis, sign):
    if axis == 0:
        return ((-BEAM_OUT, -P) if sign < 0 else (P, BEAM_OUT),
                BEAM_Y, (-BEAM_HALF, BEAM_HALF))
    return ((-BEAM_HALF, BEAM_HALF), BEAM_Y,
            (-BEAM_OUT, -P) if sign < 0 else (P, BEAM_OUT))


def key_axis(axis, sign, y0, y1):
    """A tapered shachi-sen through a tenon, driven from that beam's side.

    Returns the key faces and the matching rectangular hole (in the post and
    in the tenon).  The hole is the key's full section, so the thick head bears
    on the hole wall and the pair reads as a driven lock in the animation.
    """
    ylo, yhi = band_key_y(y0, y1)
    at = sign * 0.024            # the tenon, just inside the post's face
    if axis == 0:                # beam along x -> key driven along z
        u0, u1 = at - KEY_HALF, at + KEY_HALF
        hole = ((u0, u1), (ylo, yhi), (-P, P))
        lo, hi = -P - 0.008, P
        faces = loft(2, lo, hi,
                     [(u0 + KEY_TAPER, ylo + KEY_TAPER),
                      (u1 - KEY_TAPER, ylo + KEY_TAPER),
                      (u1 - KEY_TAPER, yhi - KEY_TAPER),
                      (u0 + KEY_TAPER, yhi - KEY_TAPER)],
                     [(u0, ylo), (u1, ylo), (u1, yhi), (u0, yhi)])
        # The tapered tip protrudes at -z; withdraw it back out that side.
        move = [0.0, 0.0, -0.18]
    else:                        # beam along z -> key driven along x
        u0, u1 = at - KEY_HALF, at + KEY_HALF
        hole = ((-P, P), (ylo, yhi), (u0, u1))
        lo, hi = -P - 0.008, P
        faces = loft(0, lo, hi,
                     [(ylo + KEY_TAPER, u0 + KEY_TAPER),
                      (yhi - KEY_TAPER, u0 + KEY_TAPER),
                      (yhi - KEY_TAPER, u1 - KEY_TAPER),
                      (ylo + KEY_TAPER, u1 - KEY_TAPER)],
                     [(ylo, u0), (yhi, u0), (yhi, u1), (ylo, u1)])
        move = [-0.18, 0.0, 0.0]
    return faces, hole, move


def make_series(jid, title, jp, bands, note=""):
    pieces = []
    exploded = {}
    holes = []
    keys = []
    for axis, sign, y0, y1 in bands:
        pid = "beam-%s%s" % ("x" if axis == 0 else "z", "n" if sign < 0 else "p")
        label = "Beam %s%s" % ("x" if axis == 0 else "z", "-" if sign < 0 else "+")
        faces, hole, move = key_axis(axis, sign, y0, y1)
        # The key passes through both the post cheek and the beam's tenon, so
        # the matching hole must be cut from the tenon too or the solids overlap.
        pieces.append(piece(pid, label,
                            [beam_body(axis, sign), tenon_box(axis, sign, y0, y1)],
                            cut=[hole]))
        exploded[pid] = ([(-0.30 if sign < 0 else 0.30), 0.0, 0.0] if axis == 0
                         else [0.0, 0.0, (-0.30 if sign < 0 else 0.30)])
        kid = "key-%s%s" % ("x" if axis == 0 else "z", "n" if sign < 0 else "p")
        keys.append(piece(kid, "Shachi-sen", [], extra=faces))
        exploded[kid] = move
        holes.append(hole)

    cut = [tenon_box(axis, sign, y0, y1) for axis, sign, y0, y1 in bands] + holes
    pieces.insert(0, piece("part-a", "Post", [POST], cut))
    pieces.extend(keys)

    j = joint(jid, title, jp, pieces, exploded, note,
              tab="extra", credit=OFFSHEET_CREDIT, modifications=KEY_MODS)
    return apply_meta(j)


# ---------------------------------------------------------------------------
# 渡り頸: two beams crossing at right angles over a post, each halved at the
# cross so the upper one's neck straddles the lower one without cutting into
# the supporting post.  This is the common floor/roof crossing the sheets omit.
W_POST_TOP = 0.42
W_DEPTH = (W_POST_TOP, W_POST_TOP + 0.12)
W_HALF = 0.045
W_CROSS = 0.045
W_MID = W_POST_TOP + 0.06
WATARI = joint(
    "watari-ago-shikuchi", "Watari-ago-shikuchi", "渡り頸仕口",
    [
        piece("post", "Post", [[(-P, P), (0.0, W_POST_TOP), (-P, P)]]),
        # Lower beam runs along x; its top half is removed at the cross.
        piece("beam-x", "Beam x",
              [[(-BEAM_OUT, BEAM_OUT), W_DEPTH, (-W_HALF, W_HALF)]],
              [[(-W_CROSS, W_CROSS), (W_MID, W_DEPTH[1]),
                (-W_HALF, W_HALF)]]),
        # Upper beam runs along z; its bottom half is removed at the cross.
        piece("beam-z", "Beam z",
              [[(-W_HALF, W_HALF), W_DEPTH, (-BEAM_OUT, BEAM_OUT)]],
              [[(-W_HALF, W_HALF), (W_DEPTH[0], W_MID),
                (-W_CROSS, W_CROSS)]]),
    ],
    {"beam-x": [-0.34, 0.0, 0.0], "beam-z": [0.0, 0.24, 0.0]},
    "A crossing lap: each 90 mm beam is halved where the two cross, so the "
    "upper beam's 頸 straddles the lower beam and the pair sit on the post "
    "without a mortise in the post itself. 下山 recommends 渡りあご for a "
    "90 mm+ joist because it fixes the joist without damaging the beam.",
    tab="extra", credit=OFFSHEET_CREDIT, modifications=KEY_MODS)

SHIHOU_SHACHI = make_series(
    "shihou-sashi-shachi-sen", "Shihou-sashi-shachi-sen", "四方差し車知栓",
    X_BANDS + Z_BANDS,
    note="Four beams frame into one post. The two x tenons stack below the "
         "two z tenons so none share the post's core, and a tapered 車知栓 "
         "through each tenon locks it. 建築用語集 shows the 車知栓 as the red "
         "member in its 四方差し figure, while warning that the through "
         "tenons leave a large lost section in the post.")

JOINTS = [WATARI, SHIHOU_SHACHI]


def main(argv):
    want = set(argv[1:])
    for j in JOINTS:
        if want and j["id"] not in want:
            continue
        path = os.path.join(JP, j["id"] + ".json")
        with open(path, "w") as fh:
            json.dump([j], fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        faces = sum(len(s["faces"]) for p in j["pieces"] for s in p["solids"])
        print("%-30s %2d pieces %4d faces -> %s"
              % (j["id"], len(j["pieces"]), faces, path))


if __name__ == "__main__":
    main(sys.argv)
