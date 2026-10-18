#!/usr/bin/env python3
"""Recover joint designs that were deleted from this repo, as .tsu files.

Usage: uv run recover_examples.py   (needs the full git history)

Writes recovered_joints/:
  tsu_history/   .tsu files that once existed in the repo (each distinct version)
  paper_data/    height fields saved as .npy during the paper work (setup/data/)
  user_study/    designs from the UIST 2020 user study (2-timber joints)

Old files have no sliding axis or timber size. These defaults apply: SAX 2,
square joint (ANG 0), 44 mm timber (38 mm for the user study, as in the
study's main.py). Old .tsu files get the current angle convention: before
commit 7311082, ANG 90 meant square; now ANG 0 means square.
"""
import io
import os
import re
import subprocess
import sys

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "recovered_joints")
DEFAULT_FS = [[[2, 0]], [[2, 1]]]
STUDY_FS_3 = [[[2, 0]], [[1, 0]], [[0, 0]]]
ANGLE_CHANGE = "7311082"  # after this commit ANG is the deviation from 90 degrees (0 = square)
SEEN = set()  # designs already written or still in the repo


def design_key(text):
    """The parts of a .tsu that define the joint shape."""
    keep = ("SAX", "NOT", "RES", "ANG", "FSS")
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    hfs = lines[next((i for i, l in enumerate(lines) if l.startswith("HFS")), len(lines))+1:]
    return tuple(l for l in lines if l.split()[0] in keep)+tuple(hfs)


def emit(path, text):
    key = design_key(text)
    if key in SEEN: return 0
    SEEN.add(key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f: f.write(text)
    return 1


def git(*args):
    return subprocess.run(["git", "-C", ROOT, *args], capture_output=True, check=True).stdout


def versions(path):
    """Distinct (commit, content) of a path over all history, oldest first."""
    seen, result = set(), []
    for commit in reversed(git("log", "--all", "--format=%h", "--", path).decode().split()):
        try: blob = git("show", commit+":"+path)
        except subprocess.CalledProcessError: continue  # deleted in this commit
        if blob and blob not in seen:
            seen.add(blob)
            result.append((commit, blob))
    return result


def paths_ever(pattern):
    names = git("log", "--all", "--format=", "--name-only", "--", pattern).decode().splitlines()
    return sorted(set(n for n in names if n))


def load_npy(blob):
    return np.load(io.BytesIO(blob), allow_pickle=True)


def write_tsu(path, hfs, fs, sax=2, td=44.0, ang=0.0):
    hfs = np.asarray(hfs, dtype=float).astype(int)
    if hfs.ndim == 2: hfs = hfs[None]
    fs_str = ":".join(".".join(str(int(ax))+","+str(int(d)) for ax, d in sides) for sides in fs)
    lines = ["SAX "+str(sax), "NOT "+str(len(fs)), "RES "+str(hfs.shape[1]), "ANG "+str(ang),
             "TDX "+str(td), "TDY "+str(td), "TDZ "+str(td), "FSS "+fs_str, "HFS "]
    lines += [":".join(",".join(str(v) for v in row) for row in hf) for hf in hfs]
    return emit(path, "\n".join(lines))


def before_angle_change(commit):
    # Files committed in ANGLE_CHANGE itself were saved before it, with the old app
    return subprocess.run(["git", "-C", ROOT, "merge-base", "--is-ancestor", commit, ANGLE_CHANGE]).returncode == 0


def normalize_old_tsu(text, old_angle):
    """Map the old TDW/TDD keys to TDX/TDY/TDZ, convert the old angle, drop blank lines (Types.open fails on them)."""
    lines = [l for l in text.splitlines() if l.strip()]
    if old_angle:  # old ANG was the angle between the timbers (90 = square)
        lines = ["ANG "+str(float(l.split()[1])-90) if l.startswith("ANG ") else l for l in lines]
    keys = dict(l.split(None, 1) for l in lines if len(l.split()) == 2)
    if "TDW" in keys and "TDX" not in keys:
        w = keys["TDW"]; d = keys.get("TDD", w)
        lines = [l for l in lines if l.split()[0] not in ("TDW", "TDD")]
        at = next(i for i, l in enumerate(lines) if l.startswith("FSS"))
        lines[at:at] = ["TDX "+w, "TDY "+d, "TDZ "+w]
    return "\n".join(lines)


def safe(name):
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_")


def recover_tsu_history():
    current = set(git("ls-files", "*.tsu").decode().split("\n"))
    count = 0
    for path in paths_ever("*.tsu"):
        vs = versions(path)
        if path in current: vs = vs[:-1]  # the latest version is still in the repo
        base = safe(os.path.splitext(path.replace("setup/", "setup_"))[0])
        for commit, blob in vs:
            name = base+"__"+commit if len(vs) > 1 else base
            count += emit(os.path.join(OUT, "tsu_history", name+".tsu"), normalize_old_tsu(blob.decode(errors="replace"), before_angle_change(commit)))
    return count


def fixed_sides_at(commit, folder, noc):
    try: fs = load_npy(git("show", commit+":"+folder+"/saved_fixed_sides.npy")).tolist()
    except subprocess.CalledProcessError: fs = None
    if fs is not None and len(fs) == noc: return fs
    return DEFAULT_FS if noc == 2 else None


def recover_paper_data():
    count = 0
    for path in paths_ever("setup/*.npy"):
        if "fixed_sides" in path or "voxel_matrix" in path or path.endswith("/.npy"): continue
        folder = os.path.dirname(path)
        for commit, blob in versions(path):
            hfs = load_npy(blob)
            if hfs.ndim == 2: hfs = hfs[None]
            fs = fixed_sides_at(commit, folder, len(hfs)+1)
            if fs is None:
                print("skip "+path+"@"+commit+": no fixed sides for "+str(len(hfs)+1)+" timbers")
                continue
            name = safe(os.path.splitext(path.replace("setup/data/", "").replace("setup/", ""))[0])+"__"+commit
            count += write_tsu(os.path.join(OUT, "paper_data", name+".tsu"), hfs, fs)
    return count


def recover_user_study():
    count = 0
    for path in paths_ever("user_study/*.npy"):
        parts = path.split("/")  # user_study/<condition>/<stage>/<user>/height_fields_<i>.npy
        vs = versions(path)
        for commit, blob in vs:
            name = "_".join(parts[1:4])+"_"+os.path.splitext(parts[4])[0].replace("height_fields_", "")
            if len(vs) > 1: name += "__"+commit
            hfs = load_npy(blob)
            fs = DEFAULT_FS if hfs.ndim == 2 or len(hfs) == 1 else STUDY_FS_3  # main.py --gal3
            count += write_tsu(os.path.join(OUT, "user_study", safe(name)+".tsu"), hfs, fs, td=38.0)
    return count


def main():
    for path in git("ls-files", "*.tsu").decode().split():
        SEEN.add(design_key(open(os.path.join(ROOT, path)).read()))
    print("tsu_history:", recover_tsu_history())
    print("paper_data: ", recover_paper_data())
    print("user_study: ", recover_user_study())


if __name__ == "__main__":
    sys.exit(main())
