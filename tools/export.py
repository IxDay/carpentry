import json, struct, math, os, re, sys, argparse

# The app's palette is authored in sRGB and written to a BGRA8Unorm drawable
# (MTLPixelFormatBGRA8Unorm = 80, not _srgb). glTF COLOR_0 is linear, so every
# color must be converted or the result comes out washed-out / too bright.
def srgb_to_linear(c):
    c = max(0.0, min(1.0, float(c)))
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


# The app bakes a single directional Lambert term into the per-face colour on
# the CPU before handing a flat-coloured vertex stream to a pass-through Metal
# shader. Fitted against the App Store screenshots (see README):
#     shade(n) = AMBIENT + DIFFUSE * max(0, n . LIGHT)
# where LIGHT is the unit vector pointing *towards* the light. The result is
# applied in display sRGB and clamped before the sRGB->linear conversion.
AMBIENT = 0.60
DIFFUSE = 0.53
LIGHT = (-0.3948, 0.8745, 0.2818)


def shade_factor(n):
    q = n[0] * LIGHT[0] + n[1] * LIGHT[1] + n[2] * LIGHT[2]
    if q < 0.0:
        q = 0.0
    return AMBIENT + DIFFUSE * q


class Mesh:
    def __init__(self):
        self.pos = []
        self.nrm = []
        self.col = []
        self.idx = []

    def add_tri(self, a, b, c, n, color):
        base = len(self.pos)
        for p in (a, b, c):
            self.pos.append((p[0], p[1], p[2]))
            self.nrm.append((n[0], n[1], n[2]))
            self.col.append((color[0], color[1], color[2]))
        self.idx += [base, base + 1, base + 2]

    def empty(self):
        return not self.idx


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def norm(v):
    l = math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])
    if l < 1e-12:
        return (0.0, 1.0, 0.0)
    return (v[0] / l, v[1] / l, v[2] / l)


def newell(pts):
    nx = ny = nz = 0.0
    for i in range(len(pts)):
        a = pts[i]
        b = pts[(i + 1) % len(pts)]
        nx += (a[1] - b[1]) * (a[2] + b[2])
        ny += (a[2] - b[2]) * (a[0] + b[0])
        nz += (a[0] - b[0]) * (a[1] + b[1])
    return (nx, ny, nz)


def add_face(m, face, linear=True, shade=True):
    pts = [tuple(float(x) for x in p) for p in face["points"]]
    if len(pts) < 3:
        return
    given = tuple(float(x) for x in face["normal"])
    # Faces in the app data are already CCW for the supplied normal, but verify
    # and fix winding so backface culling and lighting agree in any viewer.
    wn = newell(pts)
    if given[0] * wn[0] + given[1] * wn[1] + given[2] * wn[2] < 0:
        pts.reverse()
        wn = (-wn[0], -wn[1], -wn[2])
    n = norm(given) if (given[0] or given[1] or given[2]) else norm(wn)
    c = face["color"]
    if shade:
        k = shade_factor(n)
        c = tuple(max(0.0, min(1.0, float(x) * k)) for x in c)
    color = tuple(srgb_to_linear(x) for x in c) if linear else tuple(c)
    for i in range(1, len(pts) - 1):
        m.add_tri(pts[0], pts[i], pts[i + 1], n, color)


def piece_mesh(piece, linear=True, include_markers=True, shade=True):
    """Use the app's own tessellation: Solid.faces covers every solid, including
    boxes, prisms and the custom roof/awning polyhedra. box/prism are only
    parametric builders and are redundant (and less complete)."""
    m = Mesh()
    for s in piece["solids"]:
        if not include_markers and not s.get("casts"):
            continue
        faces = s.get("faces") or []
        for f in faces:
            add_face(m, f, linear, shade)
    return m


# ---------------- GLB writer ----------------
def write_glb(path, nodes, unlit=False, copyright=None, animations=None):
    nodes = [(n, m) for n, m in nodes if not m.empty()]
    bin_ = bytearray()
    views = []
    accessors = []
    meshes = []
    jnodes = []

    def add_view(data, target=None):
        while len(bin_) % 4:
            bin_.append(0)
        off = len(bin_)
        bin_.extend(data)
        v = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
        if target is not None:
            v["target"] = target
        views.append(v)
        return len(views) - 1

    def add_acc(view, comp, typ, count, mn=None, mx=None):
        a = {"bufferView": view, "componentType": comp, "count": count, "type": typ}
        if mn is not None:
            a["min"] = mn
        if mx is not None:
            a["max"] = mx
        accessors.append(a)
        return len(accessors) - 1

    for name, m in nodes:
        pos = struct.pack("<%df" % (len(m.pos) * 3), *[c for p in m.pos for c in p])
        nrm = struct.pack("<%df" % (len(m.nrm) * 3), *[c for p in m.nrm for c in p])
        col = struct.pack("<%df" % (len(m.col) * 3), *[c for p in m.col for c in p])
        idx = struct.pack("<%dI" % len(m.idx), *m.idx)
        mn = [min(p[i] for p in m.pos) for i in range(3)]
        mx = [max(p[i] for p in m.pos) for i in range(3)]
        a_pos = add_acc(add_view(pos, 34962), 5126, "VEC3", len(m.pos), mn, mx)
        a_nrm = add_acc(add_view(nrm, 34962), 5126, "VEC3", len(m.nrm))
        a_col = add_acc(add_view(col, 34962), 5126, "VEC3", len(m.col))
        a_idx = add_acc(add_view(idx, 34963), 5125, "SCALAR", len(m.idx))
        meshes.append({"name": name, "primitives": [{
            "attributes": {"POSITION": a_pos, "NORMAL": a_nrm, "COLOR_0": a_col},
            "indices": a_idx, "material": 0}]})
        jnodes.append({"name": name, "mesh": len(meshes) - 1})

    anims = []
    for anim in animations or []:
        channels, samplers = [], []
        by_name = {n["name"]: i for i, n in enumerate(jnodes)}
        for name, keys in anim.get("tracks", {}).items():
            if name not in by_name or not keys:
                continue
            times = [round(float(t), 5) for t, _v in keys]
            vals = [float(c) for _t, v in keys for c in v]
            a_t = add_acc(add_view(struct.pack("<%df" % len(times), *times)),
                          5126, "SCALAR", len(times), [min(times)], [max(times)])
            a_v = add_acc(add_view(struct.pack("<%df" % len(vals), *vals)),
                          5126, "VEC3", len(times))
            samplers.append({"input": a_t, "output": a_v,
                             "interpolation": "LINEAR"})
            channels.append({"sampler": len(samplers) - 1,
                             "target": {"node": by_name[name],
                                        "path": "translation"}})
        if channels:
            anims.append({"name": anim.get("name", "animation"),
                          "channels": channels, "samplers": samplers})

    mat = {"name": "Timber",
           "pbrMetallicRoughness": {"baseColorFactor": [1, 1, 1, 1],
                                    "metallicFactor": 0.0,
                                    "roughnessFactor": 1.0},
           "doubleSided": True}
    asset = {"version": "2.0", "generator": "joinery-timber-bake-v1.0"}
    if copyright:
        asset["copyright"] = copyright
    gltf = {
        "asset": asset,
        "scene": 0,
        "scenes": [{"name": "scene", "nodes": list(range(len(jnodes)))}],
        "nodes": jnodes,
        "meshes": meshes,
        "materials": [mat],
        "buffers": [{"byteLength": len(bin_)}],
        "bufferViews": views,
        "accessors": accessors,
    }
    if unlit:
        mat["extensions"] = {"KHR_materials_unlit": {}}
        gltf["extensionsUsed"] = ["KHR_materials_unlit"]
    if anims:
        gltf["animations"] = anims

    js = json.dumps(gltf, separators=(",", ":")).encode()
    while len(js) % 4:
        js += b" "
    while len(bin_) % 4:
        bin_.append(0)
    total = 12 + 8 + len(js) + 8 + len(bin_)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(js), 0x4E4F534A))
        f.write(js)
        f.write(struct.pack("<II", len(bin_), 0x004E4942))
        f.write(bin_)


def safe(s):
    s = re.sub(r"[^A-Za-z0-9._-]+", "_", s)
    return s.strip("._-") or "unnamed"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", default="catalog.json")
    ap.add_argument("out", nargs="?", default="glb")
    ap.add_argument("--unlit", action="store_true",
                    help="write KHR_materials_unlit (flat colors, no viewer lighting)")
    ap.add_argument("--no-linear", action="store_true",
                    help="keep raw sRGB values (normally converted to linear)")
    ap.add_argument("--no-markers", action="store_true",
                    help="omit casts=0 slot/mortise marking faces")
    ap.add_argument("--no-shade", action="store_true",
                    help="keep raw palette colours (skip the app's baked Lambert term)")
    args = ap.parse_args()

    cat = json.load(open(args.src))
    linear = not args.no_linear
    include_markers = not args.no_markers
    shade = not args.no_shade
    os.makedirs(args.out, exist_ok=True)
    files = 0
    tris = 0
    for lv in cat:
        lid = safe(lv["id"])
        ldir = os.path.join(args.out, lid)
        os.makedirs(ldir, exist_ok=True)
        nodes = []
        for p in lv["pieces"]:
            m = piece_mesh(p, linear, include_markers, shade)
            if m.empty():
                print("WARN empty piece", lv["id"], p["id"])
                continue
            write_glb(os.path.join(ldir, safe(p["id"]) + ".glb"), [(p["id"], m)], args.unlit)
            files += 1
            tris += len(m.idx) // 3
            nodes.append((p["id"], m))
        write_glb(os.path.join(args.out, lid + ".glb"), nodes, args.unlit)
        files += 1
        print("%-12s %2d pieces" % (lv["id"], len(nodes)))
    print("wrote %d files, %d triangles -> %s" % (files, tris, args.out))


if __name__ == "__main__":
    main()
