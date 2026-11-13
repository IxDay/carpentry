# tools

Capture, import, bake, check and publish tools for the Japanese joint models.

Everything is Python 3.9+ with the standard library only, except the optional
Sketchfab capture (Node 22+ and Google Chrome, no extra npm packages) and the
search library the generated page loads, which is pinned and vendored under
`vendor/`.

## Source format

A joint is described by `joints/sources/<id>.json`, a one-element list:

| Field | Meaning |
|---|---|
| `id`, `title`, `jp` | slug, romanised name, Japanese name |
| `pieces[].solids[].faces[]` | each face: `points`, `normal`, `color`, optional `grid` (forces its barycentric resolution so ear-clipped triangles of one concave face share edge samples). Coordinates are the **author's exploded pose**, in metres |
| `assemble` | `{piece: [x, y, z]}`, the translation that takes each timber from the exploded pose to the **closed** joint |
| `approach` | optional `{piece: [x, y, z]}`, a waiting stage: that timber first slides to `closed + approach` before leaving along the straight line (kanawa's slide along the pitch, a dovetail's slide along its groove) |
| `rescaled` | the factor `rescale_joint.py` applied, if any |
| `source` | author, URL, license, change list and credit text embedded in each GLB |

The generated `assemble` offsets are only a first guess; the real closed pose is
found by scanning to contact and checking that every pair of mating faces
coincides. Several joints also needed a key-width shift along the member (the
author's pose is the *mated* joint, the key slot only opens once the timbers are
drawn apart by the key's width) or small corner snaps (`mate_faces.py`).

## Scripts

### `sketchfab_capture.mjs` — record a Sketchfab model in the browser

```sh
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
    --headless=new --remote-debugging-port=9231 about:blank &
node sketchfab_capture.mjs caps 713b9b3a98344094a008535738348791
```

The download API requires an account, so the script attaches to a headless
Chrome over CDP and opens the public `/models/<uid>/embed` page. A hook records
every `bufferData` / `bufferSubData`, `vertexAttribPointer`, shader source,
linked program and `drawElements` call, plus the values of `uQVS` and `uQVT`.
The result is a JSON blob in `caps/`; the uid is the last segment of the model
URL.

### `import_joint.py` — decode a capture into a source

```sh
python3 import_joint.py caps/<uid>.json ../joints/sources/<id>.json \
    --id <id> --title <Title> --uid <uid> --url <model-url>
```

Rebuilds the mesh from the capture:

- positions are four `uint16` values, decoded as
  `p = ((v.xyz + v.w) * uQVS <op> vec3(c).perm + uQVT)` where the shader
  permutation, the operator (`*` or `/`) and the constant are read from the
  captured GLSL; normals are octahedral `int16` pairs;
- welds identical positions, drops degenerate triangles and re-orients each
  triangle to agree with the authored normals;
- splits the mesh into connected components (the individual timbers);
- merges coplanar triangles into quads and simple polygons (ear-clipped for
  bigger outlines), falling back to the authored triangles when the outline does
  not trace cleanly or overlaps itself;
- scales millimetres to metres, centres x/z, puts the lowest point at `y = 0`,
  names the two largest timbers `part-a` / `part-b` and the rest `key`, `key-2`,
  …;
- writes a first-guess `assemble`.

Attribution and licensing are in [`../joints/README.md`](../joints/README.md).

### `bake.py` — bake a sunset rig into unlit GLBs

```sh
python3 bake.py ../joints/sources/<id>.json ../joints --level <id> --pieces \
    --no-ground --detail 0.02 --edge 0.0015 --edge-lift 0.0004 --ao-dist 0.10
```

Writes `KHR_materials_unlit` GLBs whose vertex colours already contain the
lighting: a bright cream sky fill, a soft warm high sun, a light paper grade,
ray-traced cast shadows and hemisphere ambient occlusion. The rig is evaluated in
display sRGB, graded towards a cream paper tone, and linearised for `COLOR_0`:

```
color = grade(base · (ambient(n) · ao + sun · max(0, n·L) · visibility))
grade(c) = desaturate(c) then mix towards PAPER by HAZE
```

`visibility` samples points across the sun's disk (not just its rim), so the
penumbra is a proper convolution ramp. The disc is deliberately small and the
residual penumbra is snapped to 0/1, so the shadow reads as a hard cut instead of
a smudge. Every face is subdivided before baking so shadow edges and AO gradients
have vertices to land on: quads become rectangular grids (a thin plank keeps its
resolution along both axes), other faces a barycentric grid per fan triangle.

Two details are painted rather than lit, both baked into `COLOR_0`: a thin
constant-colour border strip on every crease and silhouette edge (coplanar
internal seams are skipped, otherwise flat faces get a double outline), and a
little procedural mottling so surfaces read as painted paper.

The light rig is at the top of the file:

| Constant | Value | Meaning |
|---|---|---|
| `AZ`, `EL` | 144.5°, 48° | sun azimuth/elevation (high, front-left) |
| `SUN_RGB`, `SUN_I` | `(1.00, 0.96, 0.90)`, 0.30 | pale warm direct light |
| `SKY_RGB`, `BOUNCE_RGB` | `(0.88, 0.85, 0.80)`, `(0.60, 0.60, 0.58)` | cream sky / neutral side fill |
| `AMB_I`, `AO_MIN` | 0.88, 0.80 | ambient scale; floor of the AO term |
| `SUN_RAYS`, `SUN_RADIUS` | 24, 0.004 | sun-disk samples and penumbra width |
| `AO_RAYS`, `AO_DIST` | 8, 0.55 | hemisphere AO samples and ray length |
| `PAPER`, `HAZE`, `DESAT` | `(0.945, 0.905, 0.835)`, 0.03, 0.07 | paper-wash grade |
| `PIECE_DESAT` | 0.40 | pull timber colours towards their luma (taupe wood) |
| `EDGE_STRIP_W`, `EDGE_STRIP_DARK` | 0.007, 0.22 | painted border width and strength |

Flags: `--level` (repeatable; default all sources given), `--detail` (grid size,
default 0.06; joints use 0.02), `--pieces` (also write one baked GLB per timber),
`--no-ground` (omit the ground slab; the joints always use it), `--no-ao`,
`--ao-dist` (AO ray length), `--edge` / `--edge-lift` (painted border width and
lift), `--no-animation` (omit the assemble clip) and `--fps` (animation sample
rate, default 24).

When a source has an `assemble` map, the GLB also gets a looping glTF animation
named `assemble`: closed → exploded → closed, sampled as node translations with
linear interpolation. Keys and pegs (pieces much smaller than the main timber)
are first withdrawn along their own long axis and only then moved aside; the
timbers move after the keys are clear, and assembly runs the reverse order. A
timber with an `approach` first slides to its waiting pose before leaving. This
keeps the keys out of the surrounding timber and makes the locking action
legible. The GLB writer is `export.py`.

### `preview.py` — software renders

```sh
python3 preview.py ../joints/sources/<id>.json --sunset --size 1100 --ss 2 \
    --glbdir ../joints --outdir ../joints/previews --level <id>
```

`--sunset` does **not** re-bake: it loads the GLB from `--glbdir`, decodes
`COLOR_0`, and renders it with Gouraud interpolation and `--ss`× supersampling,
so the preview verifies the shipped artifact, shadow edges included. The backdrop
is paper stock: a warm-to-cool cream gradient, a large red sun disk, three
translucent feathered cloud bars and a fine grain applied only to pixels the
model did not cover. It is drawn by `preview.py` and is not part of the GLB. The
render shows the static (exploded) pose.

### `validate.py` — check the output tree

```sh
python3 validate.py ../joints
```

Verifies GLB magic/version/chunk lengths, accessor bounds against the `BIN`
chunk, unit face normals, `COLOR_0` in `[0, 1]`, index range, and that every node
has a mesh.

### `check_sources.py` — check the closed pose before baking

```sh
python3 check_sources.py                 # every joints/sources/*.json
python3 check_sources.py daimochi-tsugi  # by id or path
```

`validate.py` checks the baked GLBs; this checks the geometry they came from.
Each source stores its pieces in the exploded pose, so the tool shifts them by
`assemble` and then verifies, for every piece:

- every edge is used by exactly two faces, in opposite directions (closed, and
  consistently wound), with T-junctions split first so an imported capture's
  extra vertices do not read as holes;
- every face's stored normal agrees with its point order;
- no two timbers share volume. Probing uses vertices, edge midpoints and
  triangle centroids; points that lie on the other piece's surface are ignored,
  so mating faces may touch. A second test looks for two faces in the same plane
  whose footprints overlap with one piece's interior on the wrong side, which
  catches interpenetration whose vertices all sit on the other surface. Samples
  within 2 mm of a face edge are skipped and patches thinner than 0.5 mm are
  ignored, so capture noise and a knife-edge contact do not fail.

### `mate_faces.py` — make mating faces meet exactly

```sh
python3 mate_faces.py <id> ../joints/sources/<id>.json
```

Several joints have two halves whose slanted faces differ by a fraction of a
millimetre up to a few millimetres, so no offset brings every face into contact.
Each per-joint preset snaps the corners of one or both timbers (in source
coordinates) and recomputes the normals of the faces that move. A preset does
nothing once its corners match.

### `open_pockets.py` — open capped key pockets

```sh
python3 open_pockets.py --dry-run ../joints/sources/*.json
python3 open_pockets.py ../joints/sources/<id>.json
```

In some models a mortise is drawn with its walls but its mouth is closed by a cap
polygon in the same plane as the timber's big outer face, so a withdrawn key
leaves no visible hole. This drops each cap and cuts its footprint out of the
rectangle it sits in.

### `rescale_joint.py` — enlarge a joint authored at the wrong scale

```sh
python3 rescale_joint.py ../joints/sources/<id>.json 6.6667
```

Multiplies every face point and every `assemble` / `approach` offset by a factor
and records it in the source (`rescaled`), so a second run does nothing. The bake
settings are sized for 120 mm timbers; the Osaka-jo Otemon splice was 18 mm
across, which blurred its bake and made collision checks far too coarse to see
the timbers passing through each other.

### `author_joint.py` — model joints that have no source

```sh
python3 author_joint.py                 # rewrite every authored source
python3 author_joint.py daimochi-tsugi  # just one, by id
```

The Sketchfab collection is all splices; the column-and-beam (`shikuchi`)
families on the reference sheet have no licensed model, so ten joints are built
here (nine `shikuchi` plus one splice). Each joint is defined in the closed pose
as a list of axis-aligned
boxes to add minus a list of boxes to cut — that is enough for square tenons,
mortises, housings, corner notches and round pegs. The boundary is extracted on
the exact box grid (no voxels) by grouping boundary cells per (axis, plane,
direction), greedily merging them into rectangles, and then splitting every edge
at any vertex that lies on it so the shared edges match exactly. The result is
the same welded, flat-normal, per-face polygon form `import_joint.py` produces.

Box CSG cannot taper, so driven wedges and pegs are built with `loft()` instead:
two parallel cross-sections (the same point count, counter-clockwise seen from
+axis) joined by planar side quads. `mirror_x()` flips a whole joint through
x = 0, reversing each face and flipping the normals and `assemble` x; the `小根
ホゾ` family is modelled on the readable side and mirrored so its mortise mouth
faces the site camera at `38deg 64deg`.

Each joint passes an explode map giving, per piece, the vector it is drawn away
from the closed joint by; the script stores the moved geometry and the opposite
translation as `assemble`. Keys get an axial clearance plus a lateral offset so `bake.py` can
withdraw them along their own axis and then move them aside without cutting
through the timber. Coordinates are metres, on the same 120 mm timber scale as
the imported models, so the standard bake flags apply.

`compile_solid` only handles boxes, and `loft()` only straight tapers, so sloped
and curved faces (the `kama` and dovetail families) still have to be authored by
hand or added as face lists. The geometry is original, not derived from a
Sketchfab model; the sources credit the project and the reference sheet, and are
released CC BY 4.0. After regenerating, run `check_sources.py` before baking.

### `build_site.py` — the GitHub Pages site

```sh
python3 build_site.py                       # ../docs, from ../joints
python3 build_site.py --repo-url https://github.com/<you>/<repo>
python3 build_site.py --preview             # also serve it on :8000
```

Reads `joints/sources/*.json` (title, Japanese name, credit), copies every
`joints/<id>.glb` and its sunset preview, and writes `docs/index.html` from
`site_template.html`: one section per joint with a `#<id>` anchor, smooth
scrolling, a `<model-viewer>` that plays the `assemble` clip and the Japanese
name in light gray under the romanised one. Up / Down arrow keys step through the
joints. Below 56 rem the index becomes a slide-in menu (button at the top left)
and every joint is a full-screen page: swipe up / down for the next / previous
joint (scroll snapping), drag sideways to rotate, with an `n / <count>` counter and
the credits along the bottom. Models load only near the viewport and only once
scrolling has settled (never mid-swipe): each stage is an empty box of its final
size with a spinner, the adjacent models are fetched at rest, and a model fades
in when it is ready.

The top of the index (and so the top of the phone menu) has a full-text search
box. It searches each joint's romanised name, Japanese name and id with
[`@leeoniya/ufuzzy`](https://github.com/leeoniya/uFuzzy) (MIT, vendored under
`vendor/` and copied into `docs/`): the query is filtered against one haystack
string per joint, ranked, and the list reordered to the ranking. The library's
`unicode: true` regexps are switched on so `金輪` and `腰掛け` match as well as
`kanawa`. Typing a single error still matches (`sanpo` finds Sampo, `kama` finds
Nimai-kama), no match shows a live-region message, Enter follows the first hit,
Escape clears the query, and `/` focuses the box from anywhere.

Plain static files, stdlib only. Regenerate and commit `docs/` after changing a
joint; publish with Pages set to the default branch, `/docs` folder.

### `viewer.py` — the same page, locally

```sh
python3 viewer.py --open       # builds the site into a temp folder and serves it
python3 viewer.py --port 9000
```

## Legal / scope

The models are reproduced under their own Creative Commons licenses (CC BY 4.0,
except `yatoi-hozo-shachi-sen-shiguchi`, which is CC BY-SA 4.0). The ten
authored joints (listed in [`../joints/README.md`](../joints/README.md)) are
original geometry released CC BY 4.0. The site's
search box uses MIT-licensed `@leeoniya/uFuzzy`, copied unmodified from npm; its
notice is in `vendor/ufuzzy.LICENSE`. See
[`../joints/README.md`](../joints/README.md) for the per-model credit.
