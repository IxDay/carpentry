#!/usr/bin/env python3
"""Enlarge (or shrink) a joint's source geometry about the origin.

Some Sketchfab models are authored at a different scale from the rest: the
Osaka-jo Otemon splice is 18 mm across where the other joints are 120 mm. The
bake settings (edge strips, shading cells, AO distance) are sized for 120 mm
timbers, so a small joint comes out blurred and its checks use thresholds that
are too coarse. This multiplies every face point and every `assemble` /
`approach` offset by a factor and records it, so a second run does nothing.

    python3 tools/rescale_joint.py joints/sources/<id>.json 6.6667
"""
import json
import sys


def main(path, factor):
    data = json.load(open(path))
    lv = data[0]
    if lv.get("rescaled"):
        print("already rescaled by", lv["rescaled"])
        return
    for piece in lv["pieces"]:
        for solid in piece["solids"]:
            for face in solid["faces"]:
                face["points"] = [[round(c * factor, 6) for c in q] for q in face["points"]]
    for key in ("assemble", "approach"):
        for pid, vec in (lv.get(key) or {}).items():
            lv[key][pid] = [round(c * factor, 6) for c in vec]
    lv["rescaled"] = factor
    src = lv["source"]
    note = "enlarged %.2fx to match the other joints" % factor
    src["modifications"] = src["modifications"].replace(
        "scaled from millimetres to metres,", "scaled from millimetres to metres, " + note + ",", 1)
    src["credit"] = src["credit"].replace("scaled from millimetres,", "scaled from millimetres, enlarged %.2fx," % factor, 1)
    with open(path, "w") as fh:
        json.dump(data, fh, indent=1)
    print("rescaled by", factor)


if __name__ == "__main__":
    main(sys.argv[1], float(sys.argv[2]))
