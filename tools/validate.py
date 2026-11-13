"""Structural + numeric validation of the exported GLB tree."""
import json, struct, math, sys, os, glob

COMP = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2),
        5125: ("I", 4), 5126: ("f", 4)}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def load(path):
    with open(path, "rb") as f:
        data = f.read()
    magic, ver, total = struct.unpack_from("<III", data, 0)
    assert magic == 0x46546C67, "bad magic"
    assert ver == 2, "bad version"
    assert total == len(data), "length mismatch %d/%d" % (total, len(data))
    off = 12
    js = bin_ = None
    while off < len(data):
        ln, typ = struct.unpack_from("<II", data, off)
        chunk = data[off + 8:off + 8 + ln]
        assert len(chunk) == ln, "truncated chunk"
        if typ == 0x4E4F534A:
            js = json.loads(chunk.decode())
        elif typ == 0x004E4942:
            bin_ = chunk
        off += 8 + ln
    assert js is not None and bin_ is not None, "missing chunk"
    return js, bin_


def accessor(js, bin_, ai):
    a = js["accessors"][ai]
    bv = js["bufferViews"][a["bufferView"]]
    fmt, size = COMP[a["componentType"]]
    n = NCOMP[a["type"]]
    start = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = bv.get("byteStride", size * n)
    out = []
    for i in range(a["count"]):
        off = start + i * stride
        vals = struct.unpack_from("<%d%s" % (n, fmt), bin_, off)
        out.append(vals)
    return a, out


def check(path):
    js, bin_ = load(path)
    assert js["asset"]["version"] == "2.0"
    assert js["buffers"][0]["byteLength"] <= len(bin_)
    tris = 0
    for mi, mesh in enumerate(js["meshes"]):
        for prim in mesh["primitives"]:
            at = prim["attributes"]
            pa, pos = accessor(js, bin_, at["POSITION"])
            na, nrm = accessor(js, bin_, at["NORMAL"])
            ca, col = accessor(js, bin_, at["COLOR_0"])
            ia, idx = accessor(js, bin_, prim["indices"])
            assert len(pos) == len(nrm) == len(col)
            assert all(abs(math.sqrt(sum(c * c for c in v)) - 1.0) < 1e-4
                       for v in nrm), "non-unit normal in %s" % mesh["name"]
            assert all(0.0 <= c <= 1.0 for v in col for c in v), \
                "colour out of range in %s" % mesh["name"]
            assert all(0 <= i[0] < len(pos) for i in idx), "index OOB"
            assert len(idx) % 3 == 0
            mn = [min(v[k] for v in pos) for k in range(3)]
            mx = [max(v[k] for v in pos) for k in range(3)]
            assert all(abs(mn[k] - pa["min"][k]) < 1e-5 for k in range(3))
            assert all(abs(mx[k] - pa["max"][k]) < 1e-5 for k in range(3))
            tris += len(idx) // 3
    assert len(js["nodes"]) == len(js["meshes"])
    return len(js["meshes"]), tris


def main():
    root = sys.argv[1]
    files = sorted(glob.glob(os.path.join(root, "**", "*.glb"), recursive=True))
    assert files, "no GLBs under " + root
    nf = nt = 0
    for f in files:
        try:
            n, t = check(f)
        except Exception as e:
            print("FAIL", f, e)
            raise
        nf += n
        nt += t
    print("%-8s %3d files, %3d meshes, %6d triangles OK" % (root, len(files), nf, nt))


if __name__ == "__main__":
    main()
