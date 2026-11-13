import json, math, sys, os, argparse, struct, zlib

# Same baked Lambert term as export.py, but previews are written straight to
# display sRGB, so the shade multiplies the sRGB colour and is *not* linearised.
AMBIENT = 0.60
DIFFUSE = 0.53
LIGHT = (-0.3948, 0.8745, 0.2818)


def shade_factor(n):
    q = n[0] * LIGHT[0] + n[1] * LIGHT[1] + n[2] * LIGHT[2]
    if q < 0.0:
        q = 0.0
    return AMBIENT + DIFFUSE * q


def rot(p, yaw, pitch):
    x, y, z = p
    cy, sy = math.cos(yaw), math.sin(yaw)
    x, z = x * cy - z * sy, x * sy + z * cy
    cp, sp = math.cos(pitch), math.sin(pitch)
    y, z = y * cp - z * sp, y * sp + z * cp
    return x, y, z


def collect(level_id):
    lv = [x for x in CAT if x["id"] == level_id][0]
    tris = []
    for p in lv["pieces"]:
        for s in p["solids"]:
            for f in s.get("faces") or []:
                pts = [tuple(float(v) for v in q) for q in f["points"]]
                n = tuple(float(v) for v in f["normal"])
                c = f["color"]
                if len(pts) >= 3:
                    tris.append((pts, n, c))
    return tris


def raster(tri, out_path, project, W, H, bg=(238, 233, 220)):
    zbuf = [-1e30] * (W * H)
    img = bytearray()
    for _ in range(W * H):
        img += bytes(bg)
    for pts, n, col in tri:
        k = shade_factor(n)
        cr = min(255, int(col[0] * k * 255 + 0.5))
        cg = min(255, int(col[1] * k * 255 + 0.5))
        cb = min(255, int(col[2] * k * 255 + 0.5))
        q = [project(p) for p in pts]
        for t in range(1, len(q) - 1):
            A, B, C = q[0], q[t], q[t + 1]
            area = (B[0] - A[0]) * (C[1] - A[1]) - (B[1] - A[1]) * (C[0] - A[0])
            if abs(area) < 1e-9:
                continue
            x0 = max(0, int(min(A[0], B[0], C[0])))
            x1 = min(W - 1, int(max(A[0], B[0], C[0])) + 1)
            y0 = max(0, int(min(A[1], B[1], C[1])))
            y1 = min(H - 1, int(max(A[1], B[1], C[1])) + 1)
            if x1 < x0 or y1 < y0:
                continue
            inv = 1.0 / area
            for y in range(y0, y1 + 1):
                py = y + 0.5
                for x in range(x0, x1 + 1):
                    px = x + 0.5
                    w0 = ((B[0] - px) * (C[1] - py) - (B[1] - py) * (C[0] - px)) * inv
                    w1 = ((C[0] - px) * (A[1] - py) - (C[1] - py) * (A[0] - px)) * inv
                    w2 = 1.0 - w0 - w1
                    if w0 < -1e-6 or w1 < -1e-6 or w2 < -1e-6:
                        continue
                    z = w0 * A[2] + w1 * B[2] + w2 * C[2]
                    i = y * W + x
                    if z <= zbuf[i]:
                        continue
                    zbuf[i] = z
                    o = i * 3
                    img[o:o + 3] = bytes((cr, cg, cb))
    with open(out_path, "wb") as f:
        f.write(b"P6\n%d %d\n255\n" % (W, H))
        f.write(img)
    print("wrote", out_path, "tris", len(tri))


def render_orbit(level_id, out, yaw, pitch, W, H):
    tri = [( [rot(p, yaw, pitch) for p in pts], n, c) for pts, n, c in collect(level_id)]
    xs = [v[0] for pts, n, c in tri for v in pts]
    ys = [v[1] for pts, n, c in tri for v in pts]
    mnx, mxx = min(xs), max(xs)
    mny, mxy = min(ys), max(ys)
    sc = min(W / (mxx - mnx) * 0.88, H / (mxy - mny) * 0.88)
    ox = (W - (mxx - mnx) * sc) / 2 - mnx * sc
    oy = (H - (mxy - mny) * sc) / 2 - mny * sc

    def project(v):
        # screen y grows down
        return (v[0] * sc + ox, H - (v[1] * sc + oy), v[2])

    raster(tri, out, project, W, H)


def render_iso(level_id, out, scale, cx, cy, yaw, sinphi, W, H):
    """Calibrated isometric used to compare against the App Store screenshots.
    X = x cos t - z sin t, Z = x sin t + z cos t
    sx = cx + s X, sy = cy + s (Z sinphi - y cosphi), depth = Z cosphi + y sinphi
    """
    cphi = math.sqrt(max(0.0, 1.0 - sinphi * sinphi))
    ct, st = math.cos(yaw), math.sin(yaw)

    def project(p):
        x, y, z = p
        X = x * ct - z * st
        Z = x * st + z * ct
        return (cx + scale * X, cy + scale * (Z * sinphi - y * cphi),
                Z * cphi + y * sinphi)

    raster(collect(level_id), out, project, W, H)


# ------------------------------------------------------------------- GLB IO --
_COMP = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2),
         5125: ("I", 4), 5126: ("f", 4)}
_NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def _accessor(js, bin_, ai):
    a = js["accessors"][ai]
    bv = js["bufferViews"][a["bufferView"]]
    fmt, size = _COMP[a["componentType"]]
    n = _NCOMP[a["type"]]
    start = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = bv.get("byteStride", size * n)
    return [struct.unpack_from("<%d%s" % (n, fmt), bin_, start + i * stride)
            for i in range(a["count"])]


def load_glb(path):
    """Return [(node_name, positions, colors_linear, indices)] from a GLB."""
    data = open(path, "rb").read()
    magic, ver, total = struct.unpack_from("<III", data, 0)
    assert magic == 0x46546C67 and ver == 2
    off = 12
    js = bin_ = None
    while off < len(data):
        ln, typ = struct.unpack_from("<II", data, off)
        chunk = data[off + 8:off + 8 + ln]
        if typ == 0x4E4F534A:
            js = json.loads(chunk.decode())
        elif typ == 0x004E4942:
            bin_ = chunk
        off += 8 + ln
    out = []
    for node in js["nodes"]:
        mesh = js["meshes"][node["mesh"]]
        prim = mesh["primitives"][0]
        at = prim["attributes"]
        pos = _accessor(js, bin_, at["POSITION"])
        col = _accessor(js, bin_, at["COLOR_0"])
        idx = [i[0] for i in _accessor(js, bin_, prim["indices"])]
        out.append((node.get("name", "mesh"), pos, col, idx))
    return out


def linear_to_srgb(c):
    c = max(0.0, min(1.0, float(c)))
    return 12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055


BACKDROP_TOP = (0.910, 0.831, 0.737)   # warm cream at the top
BACKDROP_MID = (0.953, 0.910, 0.847)   # lighter paper through the middle
BACKDROP_BOT = (0.941, 0.902, 0.843)   # barely cooler at the bottom
CLOUD = BACKDROP_MID                    # clouds are just more paper
CLOUDS = [(0.14, 1.04, 0.088, 0.038, 0.82),
          (0.52, 0.94, 0.128, 0.030, 0.60),
          (0.90, 1.06, 0.200, 0.026, 0.45)]
SUN_DISK = (0.775, 0.376, 0.271)
GRAIN_COARSE = 0.75
GRAIN_FINE = 0.25
GRAIN_SCALE = 15.0


def _span(img, w, y, x0, x1, color):
    x0 = max(0, int(x0))
    x1 = min(w - 1, int(x1))
    if x1 < x0:
        return
    o = (y * w + x0) * 3
    img[o:o + (x1 - x0 + 1) * 3] = bytes(color) * (x1 - x0 + 1)


def _paper_tone(t):
    if t < 0.45:
        u = t / 0.45
        a, b = BACKDROP_TOP, BACKDROP_MID
    else:
        u = (t - 0.45) / 0.55
        a, b = BACKDROP_MID, BACKDROP_BOT
    u = u * u * (3.0 - 2.0 * u)
    return tuple(a[i] + (b[i] - a[i]) * u for i in range(3))


def _soft_bar(img, w, h, ax0, ax1, cy, th, alpha, color):
    """A rounded, feathered bar: the reference clouds are translucent paper,
    so they only read as a pale wash where they cross the sun."""
    r = 0.5 * th
    f = max(1.0, 0.011 * w)
    y0 = max(0, int(cy - r - f - 1))
    y1 = min(h - 1, int(cy + r + f + 1))
    x0 = max(0, int(ax0 - r - f - 1))
    x1 = min(w - 1, int(ax1 + r + f + 1))
    cr, cg, cb = color
    for y in range(y0, y1 + 1):
        py = y + 0.5
        dy = py - cy
        for x in range(x0, x1 + 1):
            px = x + 0.5
            if px < ax0:
                dx = ax0 - px
            elif px > ax1:
                dx = px - ax1
            else:
                dx = 0.0
            d = math.sqrt(dx * dx + dy * dy)
            a = (r + f - d) / f
            if a <= 0.0:
                continue
            if a > 1.0:
                a = 1.0
            a *= alpha
            o = (y * w + x) * 3
            img[o] = int(img[o] + (cr - img[o]) * a + 0.5)
            img[o + 1] = int(img[o + 1] + (cg - img[o + 1]) * a + 0.5)
            img[o + 2] = int(img[o + 2] + (cb - img[o + 2]) * a + 0.5)


def paint_backdrop(img, w, h):
    """Warm-to-cool cream paper, a large red sun disk and soft cloud bars."""
    span = float(max(1, h - 1))
    for y in range(h):
        c = _paper_tone(y / span)
        row = bytes((int(255 * c[0] + 0.5),
                     int(255 * c[1] + 0.5),
                     int(255 * c[2] + 0.5))) * w
        img[y * w * 3:(y + 1) * w * 3] = row

    sun = tuple(int(c * 255) for c in SUN_DISK)
    cx, cy, r = 0.72 * w, 0.27 * h, 0.235 * w
    y0 = max(0, int(cy - r))
    y1 = min(h - 1, int(cy + r))
    for y in range(y0, y1 + 1):
        dy = y - cy
        half = math.sqrt(max(0.0, r * r - dy * dy))
        _span(img, w, y, cx - half, cx + half, sun)

    cloud = tuple(int(c * 255) for c in CLOUD)
    for fx0, fx1, fy, fth, alpha in CLOUDS:
        _soft_bar(img, w, h, fx0 * w, fx1 * w, fy * h, fth * h, alpha, cloud)


def _grain_noise(x, y):
    a = _hash01(x // 3, y // 3, 1)
    b = _hash01(x, y, 2)
    return GRAIN_COARSE * (a - 0.5) + GRAIN_FINE * (b - 0.5)


def _hash01(ix, iy, seed=0):
    h = (ix * 374761393 + iy * 668265263 + seed * 1013904223) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h ^= h >> 16
    return h / 4294967295.0


def apply_grain(img, W, H, mask):
    """Paper tooth. Fine two-octave noise over everything that is not model,
    so the backdrop reads as painted stock rather than flat vector fill."""
    for y in range(H):
        base = y * W
        for x in range(W):
            k = base + x
            if mask[k]:
                continue
            d = int(_grain_noise(x, y) * GRAIN_SCALE)
            o = k * 3
            r = img[o] + d
            g = img[o + 1] + d
            b = img[o + 2] + d
            img[o] = 0 if r < 0 else (255 if r > 255 else r)
            img[o + 1] = 0 if g < 0 else (255 if g > 255 else g)
            img[o + 2] = 0 if b < 0 else (255 if b > 255 else b)


def write_png(path, W, H, img):
    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff))
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += img[y * stride:(y + 1) * stride]
    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 6))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def render_sunset(level_id, out, W, H, yaw, pitch, ss=2, glbdir="../joints"):
    """Render a baked GLB exactly as written (Gouraud + supersampling)."""
    path = os.path.join(glbdir, level_id + ".glb")
    if not os.path.exists(path):
        raise SystemExit("missing %s - run bake.py first" % path)
    tris = []
    for _, pos, col, idx in load_glb(path):
        for t in range(0, len(idx), 3):
            ii = idx[t:t + 3]
            p = [rot(pos[i], yaw, pitch) for i in ii]
            c = [tuple(linear_to_srgb(x) for x in col[i]) for i in ii]
            tris.append((p, c))
    xs = [q[0] for p, c in tris for q in p]
    ys = [q[1] for p, c in tris for q in p]
    mnx, mxx = min(xs), max(xs)
    mny, mxy = min(ys), max(ys)

    w, h = W * ss, H * ss
    sc = min(w / (mxx - mnx) * 1.10, h / (mxy - mny) * 1.10)
    ox = (w - (mxx - mnx) * sc) / 2 - mnx * sc
    oy = (h - (mxy - mny) * sc) / 2 - mny * sc - 0.042 * h

    def project(v):
        return (v[0] * sc + ox, h - (v[1] * sc + oy), v[2])

    img = bytearray(w * h * 3)
    paint_backdrop(img, w, h)

    zbuf = [-1e30] * (w * h)
    for p, c in tris:
        A, B, C = project(p[0]), project(p[1]), project(p[2])
        area = (B[0] - A[0]) * (C[1] - A[1]) - (B[1] - A[1]) * (C[0] - A[0])
        if abs(area) < 1e-9:
            continue
        x0 = max(0, int(min(A[0], B[0], C[0])))
        x1 = min(w - 1, int(max(A[0], B[0], C[0])) + 1)
        y0 = max(0, int(min(A[1], B[1], C[1])))
        y1 = min(h - 1, int(max(A[1], B[1], C[1])) + 1)
        if x1 < x0 or y1 < y0:
            continue
        inv = 1.0 / area
        for y in range(y0, y1 + 1):
            py = y + 0.5
            for x in range(x0, x1 + 1):
                px = x + 0.5
                w0 = ((B[0] - px) * (C[1] - py) - (B[1] - py) * (C[0] - px)) * inv
                w1 = ((C[0] - px) * (A[1] - py) - (C[1] - py) * (A[0] - px)) * inv
                w2 = 1.0 - w0 - w1
                if w0 < -1e-6 or w1 < -1e-6 or w2 < -1e-6:
                    continue
                z = w0 * A[2] + w1 * B[2] + w2 * C[2]
                k = y * w + x
                if z <= zbuf[k]:
                    continue
                zbuf[k] = z
                o = k * 3
                img[o] = int((w0 * c[0][0] + w1 * c[1][0] + w2 * c[2][0]) * 255 + 0.5)
                img[o + 1] = int((w0 * c[0][1] + w1 * c[1][1] + w2 * c[2][1]) * 255 + 0.5)
                img[o + 2] = int((w0 * c[0][2] + w1 * c[1][2] + w2 * c[2][2]) * 255 + 0.5)

    mask = bytearray(W * H)
    if ss > 1:
        out_img = bytearray(W * H * 3)
        n = ss * ss
        for y in range(H):
            sy = y * ss
            for x in range(W):
                sx = x * ss
                r = g = b = 0
                covered = False
                for dy in range(ss):
                    base = ((sy + dy) * w + sx) * 3
                    for dx in range(ss):
                        if zbuf[(sy + dy) * w + sx + dx] > -1e29:
                            covered = True
                        o = base + dx * 3
                        r += img[o]
                        g += img[o + 1]
                        b += img[o + 2]
                o = (y * W + x) * 3
                out_img[o] = r // n
                out_img[o + 1] = g // n
                out_img[o + 2] = b // n
                if covered:
                    mask[y * W + x] = 1
        img = out_img
        w, h = W, H
    else:
        for k in range(W * H):
            if zbuf[k] > -1e29:
                mask[k] = 1
    apply_grain(img, w, h, mask)
    write_png(out, w, h, img)
    print("wrote", out, "%dx%d  tris %d" % (w, h, len(tris)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", default="catalog.json")
    ap.add_argument("--level", action="append", default=[],
                    help="level id to render (repeatable)")
    ap.add_argument("--outdir", default=".")
    ap.add_argument("--size", type=int, default=640)
    ap.add_argument("--iso", action="store_true", help="calibrated isometric camera")
    ap.add_argument("--scale", type=float, default=128.4)
    ap.add_argument("--cx", type=float, default=441.0)
    ap.add_argument("--cy", type=float, default=915.5)
    ap.add_argument("--yaw", type=float, default=45.0)
    ap.add_argument("--sinphi", type=float, default=0.5773502691896258)
    ap.add_argument("--width", type=int, default=884)
    ap.add_argument("--height", type=int, default=1920)
    ap.add_argument("--sunset", action="store_true",
                    help="bake the sunset rig and render its vertex colours (PNG)")
    ap.add_argument("--ss", type=int, default=2,
                    help="supersampling factor for --sunset (default 2)")
    ap.add_argument("--glbdir", default="../joints",
                    help="directory holding baked GLBs for --sunset")
    args = ap.parse_args()

    global CAT
    CAT = json.load(open(args.src))
    levels = args.level or [lv["id"] for lv in CAT]
    for lid in levels:
        if args.sunset:
            out = os.path.join(args.outdir, "sunset_%s.png" % lid)
            render_sunset(lid, out, args.size, args.size,
                          math.radians(35), math.radians(22), args.ss,
                          args.glbdir)
            continue
        out = os.path.join(args.outdir, "prev_%s.ppm" % lid)
        if args.iso:
            render_iso(lid, out, args.scale, args.cx, args.cy,
                       math.radians(args.yaw), args.sinphi,
                       args.width, args.height)
        else:
            render_orbit(lid, out, math.radians(35), math.radians(22),
                         args.size, args.size)


if __name__ == "__main__":
    main()
