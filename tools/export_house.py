#!/usr/bin/env python3
"""Write house/source.json as one GLB, one mesh node per timber.

The house is static, so there are no animation tracks.  Colours are baked with
the same directional term as the joint models and then converted to linear, so
the house matches the joint set when both are seen in the same viewer.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from export import piece_mesh, write_glb  # noqa: E402

SRC = os.path.join(ROOT, "house", "source.json")
OUT = os.path.join(ROOT, "house", "house.glb")
CREDIT = ("Open timber frame authored for the Japanese joinery project from "
          "the reference drawings; CC BY 4.0.")


def main():
    levels = json.load(open(SRC))
    pieces = levels[0]["pieces"]
    nodes = []
    tris = 0
    for p in pieces:
        m = piece_mesh(p, linear=True, include_markers=True, shade=True)
        if m.empty():
            print("WARN empty piece", p["id"])
            continue
        nodes.append((p["id"], m))
        tris += len(m.idx) // 3
    write_glb(OUT, nodes, unlit=True, copyright=CREDIT)
    size = os.path.getsize(OUT)
    print("wrote %s: %d members, %d triangles, %.2f MB"
          % (OUT, len(nodes), tris, size / 1e6))


if __name__ == "__main__":
    main()
