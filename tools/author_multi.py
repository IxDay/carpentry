#!/usr/bin/env python3
"""Author multi-beam connection specimens for the joint catalogue.

This tool adds three specimens that fill gaps the 32-sheet catalogue leaves:

    watari-ago-niju-hozo-shikuchi  渡り顎二重枘仕口  stacked double tenon over a post
    sampo-sashi-shachi-sen         三方差し車知栓   three beams, paired wedge keys
    shihou-sashi-shachi-sen        四方差し車知栓   four beams, paired wedge keys

Geometry uses the same box-CSG and loft helpers as ``author_joint.py``.  The
post takes one tenon per direction, each at its own level inside the beam depth
so that no two tenons share the post's core.  Paired shachi-sen pass through
each tenon from opposite faces.

    python3 author_multi.py                       # all three
    python3 author_multi.py watari-ago-niju-hozo-shikuchi  # one

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
# 渡り顎二重枘仕口: a post carries two tenons stacked one above the other. The
# lower one takes the 桁 (girder) that sits directly on the post; the upper one
# passes through that girder into the 梁 (beam) crossing above it. A carved
# 渡り顎 jaw at the crossing stops the two horizontal timbers wandering.
#
# The layout follows the carpentry-school build log of the exact joint
# (hainankenchiku.jimdofree.com, mirrored at diyshufu.com/job-training-of-
# carpenter/1754/): "下から柱、真ん中のが桁、一番上を梁", a post with tenons
# worked on top, and mortises opened in both the 桁 and the 梁. The stacked
# arrangement is the one shown in @thejoinery_jp's assembly GIF
# (https://twitter.com/i/status/771307153583812610).
W_POST_TOP = 0.42
W_DEPTH = (W_POST_TOP, W_POST_TOP + 0.12)     # 桁: 120 mm deep
W_HALF = 0.045                                # 90 mm wide timbers
W_CROSS = 0.045                               # 渡り顎 jaw half-width, 1.3 sun
W_TENON_LO = 0.030                            # 60 mm lower tenon
W_TENON_HI = 0.020                            # 40 mm upper tenon
W_TENON_MID = W_POST_TOP + 0.06               # step between the two tenons
W_BEAM_BOT = W_DEPTH[1]                       # the 梁 sits on the 桁
W_BEAM_TOP = W_BEAM_BOT + 0.12
W_MODS = ("authored from the carpentry-school account of 渡り顎二重枘仕口 and "
          "@thejoinery_jp's assembly GIF: post with a stacked double tenon, "
          "桁 below, 梁 above, 渡り顎 jaw at the cross; closed pose, exploded "
          "for the assemble animation, sunset lighting baked; the baking "
          "rig's ground slab is omitted")
W_CREDIT = ("Original geometry authored for this collection from the carpentry "
            "school's 渡り顎・二重ほぞ仕口 build log and @thejoinery_jp's "
            "assembly GIF; CC BY 4.0.")
WATARI = joint(
    "watari-ago-niju-hozo-shikuchi", "Watari-ago-niju-hozo-shikuchi",
    "渡り顎二重枘仕口",
    [
        # The post's top is stepped: a wide lower tenon and a narrow upper one
        # that runs on through the girder into the beam.
        piece("post", "Post", [
            [(-P, P), (0.0, W_POST_TOP), (-P, P)],
            [(-W_TENON_LO, W_TENON_LO), (W_POST_TOP, W_TENON_MID),
             (-W_TENON_LO, W_TENON_LO)],
            [(-W_TENON_HI, W_TENON_HI), (W_TENON_MID, W_BEAM_BOT + 0.06),
             (-W_TENON_HI, W_TENON_HI)],
        ]),
        # 桁 runs along x: a lower mortise for the post and a top notch that
        # receives the 梁's downward jaw.
        piece("girder-x", "Girder x",
              [[(-BEAM_OUT, BEAM_OUT), W_DEPTH, (-W_HALF, W_HALF)]],
              [[(-W_TENON_LO, W_TENON_LO), (W_POST_TOP, W_TENON_MID),
                (-W_TENON_LO, W_TENON_LO)],
               [(-W_CROSS, W_CROSS), (W_TENON_MID, W_DEPTH[1]),
                (-W_HALF, W_HALF)]]),
        # 梁 runs along z: a full-depth beam with a downward jaw at the cross,
        # mortised to take the post's upper tenon.
        piece("beam-z", "Beam z",
              [[(-W_HALF, W_HALF), (W_BEAM_BOT, W_BEAM_TOP),
                (-BEAM_OUT, BEAM_OUT)],
               [(-W_CROSS, W_CROSS), (W_TENON_MID, W_BEAM_BOT),
                (-W_CROSS, W_CROSS)]],
              [[(-W_TENON_HI, W_TENON_HI), (W_TENON_MID, W_BEAM_BOT + 0.06),
                (-W_TENON_HI, W_TENON_HI)]]),
    ],
    {"girder-x": [-0.34, 0.0, 0.0], "beam-z": [0.0, 0.24, 0.30]},
    "A post carries two stacked tenons: the lower one takes the 桁 girder, "
    "the upper passes through it into the 梁 beam above, and a carved 渡り顎 "
    "jaw locks the crossing.  The layout follows the carpentry-school build "
    "log (hainankenchiku.jimdofree.com; diyshufu.com/job-training-of-carpenter/"
    "1754/) and the assembly GIF by @thejoinery_jp (tweet 771307153583812610).",
    tab="extra", credit=W_CREDIT, modifications=W_MODS)

SAMPO_SHACHI = make_series(
    "sampo-sashi-shachi-sen", "Sampo-sashi-shachi-sen", "三方差し車知栓",
    X_BANDS[:1] + Z_BANDS,
    note="Three beams meet one post at a T-junction. Each tenon sits at its "
         "own level, runs 100 mm into the post and is locked by a tapered "
         "車知栓 driven through it from the beam's side; the pair of keys on "
         "opposite faces draws the arrivals tight.")

SHIHOU_SHACHI = make_series(
    "shihou-sashi-shachi-sen", "Shihou-sashi-shachi-sen", "四方差し車知栓",
    X_BANDS + Z_BANDS,
    note="Four beams frame into one post. The two x tenons stack below the "
         "two z tenons so none share the post's core, and a tapered 車知栓 "
         "through each tenon locks it. 建築用語集 shows the 車知栓 as the red "
         "member in its 四方差し figure, while warning that the through "
         "tenons leave a large lost section in the post.")

JOINTS = [WATARI, SAMPO_SHACHI, SHIHOU_SHACHI]


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
