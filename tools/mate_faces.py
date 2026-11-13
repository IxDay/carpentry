#!/usr/bin/env python3
"""Make a joint's mating faces meet exactly.

Several of the Sketchfab joints have two halves whose slanted faces differ by a
few millimetres, so no offset brings every face into contact. Each preset below
snaps the corners of one timber onto the other's (in the timber's own source
coordinates) and recomputes the normals of the faces that move. A preset is a
no-op once its corners match.

    python3 tools/mate_faces.py hira-isuka-tsugi joints/sources/hira-isuka-tsugi.json
"""
import json
import sys

TOL = 0.0015

# joint -> [(piece, rules)]; a rule is (match {axis: value}, axis, from, to) in
# the piece's source coordinates
PRESETS = {
    # part-b closed at z=0.1966: its beak corners follow part-a's
    "hira-isuka-tsugi": [("part-b", [
        ({"x": -0.06, "y": 0.06}, "z", -0.0386, -0.0346),
        ({"x": -0.06, "y": 0.06}, "z", -0.1626, -0.1576),
        ({"x": -0.06, "y": 0.12}, "z", -0.0386, -0.0346),
        ({"x": 0.06, "y": 0.0}, "z", -0.0386, -0.0346),
        ({"x": 0.06, "y": 0.06}, "z", -0.0386, -0.0346),
        ({"x": 0.06, "y": 0.06}, "z", -0.1626, -0.1576),
        ({"x": -0.06, "y": 0.0}, "z", -0.1626, -0.1576),
        ({"x": 0.06, "y": 0.12}, "z", -0.1626, -0.1576),
    ])],
    # part-b's two slanted end faces take part-a's slope (0.25 / 0.333)
    # shoulders sit 0.3 mm proud of part-a's while the tongue ends coincide
    "meji-tsukikake-awase-tsugi": [("part-b", [
        ({}, "z", -0.2699, -0.2702),
        ({"x": -0.015}, "z", -0.0298, -0.0301),
        ({"x": -0.06}, "z", -0.0298, -0.0301),
        ({"x": 0.015}, "z", -0.0298, -0.0301),
        ({"x": 0.06}, "z", -0.0298, -0.0301),
    ]), ("part-a", [
        # face a1 is tilted 0.3 mm across its width; flatten it
        ({"x": 0.06}, "z", 0.2702, 0.2699),
    ])],
    # tenon step corners were 0.19-0.23 mm off the mortise's (two rules: one
    # rule is applied per corner and run, so run the tool twice on a fresh file)
    "otoshi-ari-hozo-shikuchi": [("part-b", [
        ({}, "y", 0.179965, 0.179771),
        ({}, "x", 0.020084, 0.019854),
    ])],
    # dovetail rim corners moved up to 1.2 mm so all four dovetail faces are
    # planar and parallel to the (1,0,-1) slide; part-b closed at
    # (0.168972, 0, -0.168975). The two halves are corrected symmetrically.
    "shihou-ari-tsugi": [("part-a", [
        ({"y": 0.261412, "x": 0.144997}, "z", -0.062799, -0.061647),
        ({"y": 0.261412, "z": -0.023977}, "x", 0.108464, 0.107327),
        ({"y": 0.261412, "x": 0.023975}, "z", -0.108466, -0.107325),
        ({"y": 0.261412, "z": -0.145}, "x", 0.062797, 0.06165),
        ({"y": 0.261412, "z": -0.023977}, "x", 0.062797, 0.061677),
        ({"y": 0.261412, "x": 0.144997}, "z", -0.108466, -0.107297),
        ({"y": 0.261412, "x": 0.023975}, "z", -0.062799, -0.061675),
        ({"y": 0.261412, "z": -0.145}, "x", 0.108464, 0.1073),
    ]), ("part-b", [
        ({"y": 0.261412, "x": -0.024}, "z", 0.108462, 0.107328),
        ({"y": 0.261412, "z": 0.145}, "x", -0.062797, -0.061645),
        ({"y": 0.261412, "x": -0.145}, "z", 0.062794, 0.06165),
        ({"y": 0.261412, "z": 0.024}, "x", -0.108462, -0.107322),
        ({"y": 0.261412, "z": 0.145}, "x", -0.108462, -0.107295),
        ({"y": 0.261412, "x": -0.024}, "z", 0.062794, 0.061678),
        ({"y": 0.261412, "x": -0.145}, "z", 0.108462, 0.1073),
        ({"y": 0.261412, "z": 0.024}, "x", -0.062797, -0.061672),
    ])],
    # hook step faces were 0.43 mm out and the tongue slopes 0.2 mm; the hard
    # stop (tip/shoulder) is made to touch exactly. `key` is a blade, not a key
    "nimai-kama-tsugi": [("part-b", [
        ({"z": 0.20011, "y": 0.207523}, "y", 0.207523, 0.207718),
        ({"z": 0.20011, "y": 0.192471}, "y", 0.192471, 0.192673),
    ]), ("key", [
        ({"y": 0.222568}, "z", -0.200123, -0.19969),
        ({"y": 0.207523}, "z", -0.200123, -0.19969),
    ])],
    "kakeawase-komisen-tsugi": [("part-b", [
        # exact: both pairs close at z=0.247827 (part-a z - part-b z at y=0.0595)
        ({"y": 0.119}, "z", -0.023, -0.018075),
        ({"y": 0.119}, "z", -0.018, -0.018075),
        ({"y": 0.0}, "z", -0.23, -0.224599),
        ({"y": 0.0}, "z", -0.225, -0.224599),
    ])],
}


def normal(p, ref):
    u = [p[1][i] - p[0][i] for i in range(3)]
    v = [p[2][i] - p[0][i] for i in range(3)]
    n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
    m = sum(c * c for c in n) ** 0.5
    n = [c / m for c in n]
    if sum(a * b for a, b in zip(n, ref)) < 0:
        n = [-c for c in n]
    return [round(c, 9) for c in n]


def main(joint, path):
    data = json.load(open(path))
    ax = {"x": 0, "y": 1, "z": 2}
    moved = 0
    for piece, rules in PRESETS[joint]:
        part = next(p for p in data[0]["pieces"] if p["id"] == piece)
        for f in part["solids"][0]["faces"]:
            changed = False
            for q in f["points"]:
                for match, axis, frm, to in rules:
                    if all(abs(q[ax[k]] - v) < TOL for k, v in match.items()) \
                            and abs(q[ax[axis]] - frm) < TOL:
                        if abs(q[ax[axis]] - to) > 1e-7:
                            q[ax[axis]] = round(to, 6)
                            changed = True
                            moved += 1
                        break
            if changed:
                f["normal"] = normal(f["points"], f["normal"])
    print(joint, "moved", moved, "corners")
    if moved:
        with open(path, "w") as fh:
            json.dump(data, fh, indent=1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
