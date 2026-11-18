#!/usr/bin/env python3
"""Author multi-beam connection specimens for the joint catalogue.

This tool adds four specimens that fill gaps the 32-sheet catalogue leaves:

    watari-ago-niju-hozo-shikuchi  渡り顎二重枘仕口  stacked double tenon over a post
    watari-ago-shikuchi            渡り顎仕口        plate and square tenon between ribs
    sampo-sashi-shachi-sen         三方差し車知栓   three beams, paired wedge keys
    shihou-sashi-shachi-sen        四方差し車知栓   four beams, paired wedge keys

Geometry uses the same box-CSG and loft helpers as ``author_joint.py``.  The
post takes one tenon per direction, each at its own level inside the beam depth
so that no two tenons share the post's core.  Paired shachi-sen pass through
each tenon from opposite faces.

    python3 author_multi.py                       # all four
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
# 渡り顎二重枘仕口: a post carries two tenons stacked one above the other. The
# lower one takes the 桁 (girder) that sits directly on the post; the upper one
# runs right through that girder, right through the 梁 (beam) crossing above,
# and is cut off flush with the beam's top face.  Where the two horizontal
# timbers cross the girder's top is housed down over a band 1 sun 3 bu (78 mm)
# wide, and the beam carries a chin of the same width that drops into it - the
# 渡り顎 - so each timber keeps a pair of shoulders either side of the crossing.
#
# The layout follows the carpentry-school build log of the exact joint
# (hainankenchiku.jimdofree.com, mirrored at diyshufu.com/job-training-of-
# carpenter/1754/): "下から柱、真ん中のが桁、一番上を梁", the 峠 set 5 bu above
# the 桁, the 渡り顎 widths taken 1 sun 3 bu from the centre, and the tenon
# holes opened right through ("穴を貫通させるのに手間取っていた").  The
# stacked arrangement is the one shown in @thejoinery_jp's assembly GIF
# (https://twitter.com/i/status/771307153583812610).
W_POST_TOP = 0.42
W_DEPTH = (W_POST_TOP, W_POST_TOP + 0.12)     # 桁: 120 mm deep
W_HALF = P                                    # 120 mm square post, girder and beam
W_AGO = 0.039                                 # 渡り顎 half-width, 1 sun 3 bu from the centre
W_AGO_DROP = 0.018                            # jaw seating depth, 6 bu
W_JAW_FLOOR = W_DEPTH[1] - W_AGO_DROP         # floor of the housing / foot of the chin
W_TENON_LO = 0.040                            # 80 mm lower tenon
W_TENON_HI = 0.020                            # 40 mm upper tenon
W_TENON_MID = W_POST_TOP + 0.06               # step between the two tenons
W_BEAM_BOT = W_DEPTH[1]                       # the 梁 sits on the 桁
W_BEAM_TOP = W_BEAM_BOT + 0.12
W_MODS = ("authored from the carpentry-school account of 渡り顎二重枘仕口 and "
          "@thejoinery_jp's assembly GIF: post with a stacked double tenon, "
          "桁 below, 梁 above, the upper tenon passing through both timbers and "
          "cut flush with the beam's top, a 78 mm 渡り顎 housing in the girder "
          "taking the beam's chin; closed pose, each timber lifted clear of its "
          "mortise before sliding out for the assemble animation, sunset "
          "lighting baked; the baking rig's ground slab is omitted")
W_CREDIT = ("Original geometry authored for this collection from the carpentry "
            "school's 渡り顎・二重ほぞ仕口 build log and @thejoinery_jp's "
            "assembly GIF; CC BY 4.0.")
WATARI = joint(
    "watari-ago-niju-hozo-shikuchi", "Watari-ago-niju-hozo-shikuchi",
    "渡り顎二重枘仕口",
    [
        # The post's top is stepped: a wide lower tenon and a narrow upper one
        # that runs on through the girder and the beam.
        piece("post", "Post", [
            [(-P, P), (0.0, W_POST_TOP), (-P, P)],
            [(-W_TENON_LO, W_TENON_LO), (W_POST_TOP, W_TENON_MID),
             (-W_TENON_LO, W_TENON_LO)],
            [(-W_TENON_HI, W_TENON_HI), (W_TENON_MID, W_BEAM_TOP),
             (-W_TENON_HI, W_TENON_HI)],
        ]),
        # 桁 runs along x: a lower mortise for the post, a through mortise for
        # the upper tenon, and a transverse housing across the top for the 梁's
        # chin.  The two shoulders left either side of the housing are the 顎.
        piece("girder-x", "Girder x",
              [[(-BEAM_OUT, BEAM_OUT), W_DEPTH, (-W_HALF, W_HALF)]],
              [[(-W_TENON_LO, W_TENON_LO), (W_POST_TOP, W_TENON_MID),
                (-W_TENON_LO, W_TENON_LO)],
               [(-W_TENON_HI, W_TENON_HI), (W_TENON_MID, W_DEPTH[1]),
                (-W_TENON_HI, W_TENON_HI)],
               [(-W_AGO, W_AGO), (W_JAW_FLOOR, W_DEPTH[1]),
                (-W_HALF, W_HALF)]]),
        # 梁 runs along z: a full-depth beam whose underside carries a chin that
        # drops into the girder's housing, with the through mortise for the
        # post's upper tenon cut right through chin and beam alike.
        piece("beam-z", "Beam z",
              [[(-W_HALF, W_HALF), (W_BEAM_BOT, W_BEAM_TOP),
                (-BEAM_OUT, BEAM_OUT)],
               [(-W_AGO, W_AGO), (W_JAW_FLOOR, W_BEAM_BOT),
                (-W_HALF, W_HALF)]],
              [[(-W_TENON_HI, W_TENON_HI), (W_JAW_FLOOR, W_BEAM_TOP),
                (-W_TENON_HI, W_TENON_HI)]]),
    ],
    {"girder-x": [-0.34, 0.30, 0.0], "beam-z": [0.0, 0.36, 0.30]},
    "A post carries two stacked tenons: the lower one takes the 桁 girder, the "
    "upper one runs through both the girder and the 梁 beam above and is cut "
    "flush with the beam's top, and a 渡り顎 housing across the girder takes the "
    "beam's chin.  The layout follows the carpentry-school build log "
    "(hainankenchiku.jimdofree.com; diyshufu.com/job-training-of-carpenter/"
    "1754/) and the assembly GIF by @thejoinery_jp (tweet 771307153583812610).",
    tab="extra", credit=W_CREDIT, modifications=W_MODS,
    approach={
        "beam-z": [[0.0, 0.36, 0.0], [0.0, 0.36, 0.30]],
        "girder-x": [[0.0, 0.0, 0.0], [0.0, 0.30, 0.0],
                     [-0.34, 0.30, 0.0]],
    },
    duration=12.0)

# ---------------------------------------------------------------------------
# 渡り顎仕口, as drawn frame by frame in @thejoinery_jp's assembly GIF.  Post,
# 桁 girder and 梁 beam are all 120 mm square (U = 120 mm); the girder runs
# along x and is 3.75 U long, the beam runs along z and is 3.9 U long.  The
# post's stepped tenon is a 0.75 U x 0.25 U plate into a blind mortise from the
# girder's underside, topped by a 0.25 U square that comes up through a square
# hole in the girder, through the beam, and ends flush with the beam's top.  The
# girder's top keeps a raised rib at each x edge of the crossing, 0.78 U wide
# (narrower than the girder, so a shoulder is left either side); the beam's
# underside is notched at both x edges to take them, 0.24 U deep and 0.26 U
# high, leaving a central tab between the ribs that locks the beam against
# twisting and takes load off the tenon.
# A shallow slot open to the girder's +z face sits beside the tenon hole.
U = 0.12
A_Y0 = 0.20                                   # post top, girder underside
A_GIRDER = (A_Y0, A_Y0 + U)
A_BEAM = (A_Y0 + U, A_Y0 + 2 * U)
A_PLATE = (0.375 * U, 0.125 * U)              # tenon plate half x, half z
A_PLATE_TOP = A_Y0 + 0.75 * U
A_SQ = 0.125 * U                              # upper tenon half-section
A_RIB_X = ((-U / 2, -U / 2 + 0.24 * U), (U / 2 - 0.24 * U, U / 2))
A_HOOKS = [(x, (A_BEAM[0], A_BEAM[0] + 0.26 * U), (-0.39 * U, 0.39 * U))
           for x in A_RIB_X]
A_SLOT = ((-0.2 * U, 0.2 * U), (A_BEAM[0] - 0.2 * U, A_BEAM[0]),
          (0.5 * U - 0.23 * U, 0.5 * U))
A_MODS = ("authored from the frames of @thejoinery_jp's assembly GIF: post "
          "with a stepped tenon, 桁 girder with a blind lower mortise, a square "
          "through hole and a rib along each of its x edges, 梁 beam with the matching "
          "notch under each x edge and a flush square mortise; the hook, the "
          "notch and the side slot are read from a single isometric view, so "
          "their depths are approximate; closed pose, each timber lifted "
          "straight off the post for the assemble animation, sunset lighting "
          "baked; the baking rig's ground slab is omitted")
A_CREDIT = ("Original geometry authored for this collection from "
            "@thejoinery_jp's assembly GIF; CC BY 4.0.")
WATARI_AGO = joint(
    "watari-ago-shikuchi", "Watari-ago-shikuchi", "渡り顎仕口",
    [
        piece("post", "Post", [
            [(-U / 2, U / 2), (0.0, A_Y0), (-U / 2, U / 2)],
            [(-A_PLATE[0], A_PLATE[0]), (A_Y0, A_PLATE_TOP),
             (-A_PLATE[1], A_PLATE[1])],
            [(-A_SQ, A_SQ), (A_PLATE_TOP, A_BEAM[1]), (-A_SQ, A_SQ)],
        ]),
        piece("girder-x", "Girder x",
              [[(-1.875 * U, 1.875 * U), A_GIRDER, (-U / 2, U / 2)]] + A_HOOKS,
              [[(-A_PLATE[0], A_PLATE[0]), (A_Y0, A_PLATE_TOP),
                (-A_PLATE[1], A_PLATE[1])],
               [(-A_SQ, A_SQ), (A_PLATE_TOP, A_GIRDER[1]), (-A_SQ, A_SQ)],
               A_SLOT]),
        piece("beam-z", "Beam z",
              [[(-U / 2, U / 2), A_BEAM, (-1.95 * U, 1.95 * U)]],
              [[(-A_SQ, A_SQ), A_BEAM, (-A_SQ, A_SQ)]] + A_HOOKS),
    ],
    {"girder-x": [0.0, 0.30, 0.0], "beam-z": [0.0, 0.62, 0.0]},
    "A post carries a stepped tenon: a flat plate that sits in a blind mortise "
    "under the 桁 girder, and a square tenon above it that rises through the "
    "girder and the 梁 beam and ends flush with the beam's top.  The girder's "
    "top carries a raised rib either side of the tenon, a little narrower than the "
    "girder, and the beam's underside is notched at both edges to take them; the "
    "central tab between the ribs locks the beam against twisting and takes "
    "load off the tenon.  Drawn from "
    "@thejoinery_jp's assembly GIF (tweet 771307153583812610).",
    tab="extra", credit=A_CREDIT, modifications=A_MODS, duration=12.0)

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

JOINTS = [WATARI, WATARI_AGO, SAMPO_SHACHI, SHIHOU_SHACHI]


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
