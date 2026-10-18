#!/usr/bin/env python3
"""Export every .tsu joint in the repo to animated .glb files.

Usage: uv run export_examples_glb.py [output_dir]   (default: examples_glb/)

Sources, and the output subfolder for each:
  *.tsu                 -> repo/
  setup/*.tsu           -> setup/
  recovered_joints/<x>/ -> <x>/   (made by recover_examples.py)

Same geometry, materials and "assemble" animation as export_gallery_glb.py.
"""
import glob
import os
import sys
import traceback

sys.dont_write_bytecode = True  # upstream tracks setup/__pycache__ in git
from export_gallery_glb import ROOT, Types, _Parent, export_joint

SOURCES = [("repo", "*.tsu"), ("setup", "setup/*.tsu")]
SOURCES += [(os.path.basename(d), os.path.relpath(d, ROOT)+"/*.tsu")
            for d in sorted(glob.glob(os.path.join(ROOT, "recovered_joints", "*"))) if os.path.isdir(d)]


def main():
    out_dir = os.path.abspath(os.path.join(ROOT, sys.argv[1] if len(sys.argv) > 1 else "examples_glb"))
    type = Types(_Parent(), fs=[[[2, 0]], [[2, 1]]], sax=2, dim=3)
    total, failed = 0, []
    for sub, pattern in SOURCES:
        files = sorted(glob.glob(os.path.join(ROOT, pattern)))
        os.makedirs(os.path.join(out_dir, sub), exist_ok=True)
        for path in files:
            name = os.path.splitext(os.path.basename(path))[0]
            try:
                type.open(path)
                export_joint(type, type.mesh.height_fields, os.path.join(out_dir, sub, name+".glb"))
                total += 1
            except Exception as e:
                failed.append((os.path.relpath(path, ROOT), repr(e)))
                traceback.print_exc(limit=1)
        print("%-12s %d files" % (sub, len(files)))
    print("Exported %d joints to %s" % (total, out_dir))
    for path, err in failed: print("FAILED "+path+": "+err)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
