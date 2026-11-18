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
| `approach` | optional `{piece: [x, y, z]}` waiting stage: that timber first slides to `closed + approach` before leaving along the straight line (kanawa's slide along the pitch, a dovetail's slide along its groove). A list of vectors is a path instead, visited in order (`tsutsumikomi-nuki`: raised, slid home, lowered) |
| `rescaled` | the factor `rescale_joint.py` applied, if any |
| `source` | author, URL, license, change list and credit text embedded in each GLB |
| `tab` | original provenance group (`sheet`, `extra`, `house-details`); `house-details` sources are kept in the repo but skipped by `build_site.py`, the others are all published in one view |
| `beams`, `usage`, `strengths`, `weaknesses` | catalogue metadata: how many timber pieces meet at the joint (the post counts; pegs, wedges, keys and dowels excluded), its use, and what is good / risky about it. Authored in `joint_meta.py` and stamped onto every source |

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
timber with an `approach` first slides to its waiting pose before leaving; a
list of poses is walked in order, so a firmly wrapped joint is offered up,
slid home and lowered. This
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

### `check_contact.py` — check that pieces actually join

```sh
python3 check_contact.py                 # every joints/sources/*.json
python3 check_contact.py daimochi-tsugi  # by id or path
python3 check_contact.py --json          # machine-readable report
```

`check_sources.py` proves the solids are manifold and do not overlap, but an
"exactly touching" allowance means a joint whose pieces float a millimetre
apart still passes. This tool measures surface-to-surface distance between
every pair of pieces in the closed pose (a vectorised closest-point-on-triangle
kernel over vertices, edge midpoints and centroids), builds the piece adjacency
graph and reports any disconnected groups. It also prints how much of one
piece's surface sits inside the other's bounding box, a cheap interlock/mortise
proxy: a pair with contact but no bounding-box interlock is a bearing contact,
not a housed joint.

A pair is *contact* at 0.1 mm, *near* up to 2 mm and a *gap* beyond that. The
script uses NumPy (already needed by the bake tools) and needs SciPy or trimesh
neither. Run it alongside `check_sources.py` after any geometry edit; a joint
with no disconnected pieces is the minimum bar, not proof that every intended
mortise is present.

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
families on the reference sheet have no licensed model, so seventeen joints are
built here: fifteen from the sheet (thirteen `shikuchi` plus two splices) and
two off-sheet joints from published descriptions (the plan-cut `胴付き蟻継ぎ`
and the wrapped-nuki `包み込み貫`). Each joint is defined in the
closed pose as a list of axis-aligned boxes to add minus a list of boxes to
cut — that is enough for square tenons, mortises, housings, corner notches and
round pegs. The boundary is extracted on the exact box grid (no voxels) by
grouping boundary cells per (axis, plane, direction), greedily merging them into
rectangles, and then splitting every edge
at any vertex that lies on it so the shared edges match exactly. The result is
the same welded, flat-normal, per-face polygon form `import_joint.py` produces.

Box CSG cannot taper, so driven wedges and pegs are built with `loft()` instead:
two parallel cross-sections (the same point count, counter-clockwise seen from
+axis) joined by planar side quads. Two identical sections give a constant
prism, which is how a rebate or an end face can be cut at a slope without any
polygon clipping: the slanted outline lives in the section (`katagi-ooire` is a
post and a beam shaped that way). `mirror_x()` flips a whole joint through
x = 0, reversing each face and flipping the normals and `assemble` x; the `小根
ホゾ` family is modelled on the readable side and mirrored so its mortise mouth
faces the site camera at `38deg 64deg`.

Each joint passes an explode map giving, per piece, the vector it is drawn away
from the closed joint by; the script stores the moved geometry and the opposite
translation as `assemble`. Keys get an axial clearance plus a lateral offset so `bake.py` can
withdraw them along their own axis and then move them aside without cutting
through the timber. Coordinates are metres, on the same 120 mm timber scale as
the imported models, so the standard bake flags apply.

`compile_solid` only handles boxes, and `loft()` joins two straight sections,
so a face that twists (a compound slope) still has to be approximated by hand or
added as a face list; the `片鎌` hook is kept square so it stays box work. The
geometry is original, not derived from a
Sketchfab model; the sources credit the project and the reference sheet, and are
released CC BY 4.0. The two off-sheet joints instead credit "published
descriptions of the joint", carry `tab: "extra"` for provenance (the published
site is a single view), and may give `approach` as a whole path
(`tsutsumikomi-nuki`). After regenerating, run `check_sources.py` before baking.

### `author_multi.py` — off-sheet specimens

```sh
python3 author_multi.py                     # rewrite all three sources
python3 author_multi.py watari-ago-niju-hozo-shikuchi  # just one, by id
```

Three specimens fill gaps the reference sheets leave, each with written or
diagrammatic backing. `watari-ago-niju-hozo-shikuchi` is the stacked double
tenon of the GIF by @thejoinery_jp and the carpentry-school build log: a post's
lower tenon takes the 桁, its upper tenon passes through into the 梁 above, and
a 渡り顎 jaw locks the crossing. `sampo-sashi-shachi-sen` and
`shihou-sashi-shachi-sen` adapt the 建築用語集 四方差し figure for three- and
four-way posts, with one tenon per direction at its own level, each locked by a
tapered 車知栓 driven crosswise through the tenon. Geometry uses the same box CSG and
`loft()` helpers as `author_joint.py`; the sources are written with their
catalogue metadata already stamped on. Original geometry, CC BY 4.0. Regenerate,
then run `check_sources.py`, `check_contact.py`, `bake.py` and `preview.py`.

### `joint_meta.py` — catalogue metadata

```sh
python3 joint_meta.py                       # re-stamp every joints/sources/*.json
python3 joint_meta.py ../joints/sources kanawa-tsugi  # just one id
```

The canonical table of `beams`, `usage`, `strengths` and `weaknesses` for all 56
specimens, with `SOURCE_NOTES` collecting the web references behind the prose.
`apply(level)` stamps a decoded source (a fallback used by `build_site.py`), and
`write_sources(src_dir, only)` rewrites source files in place. The `beams` count
is the number of timber pieces meeting at the joint: the post plus the beams,
girders, joists, rafters or braces; pegs, wedges, keys, dowels and loose tenons
are not counted. Usage and strength notes come from the supplied naming guide,
the reference sheets, the repository READMEs and the cited web pages; only
specimens with direct written, photographic or schematic backing are published.

### `author_details.py` — house-only joint specimens

```sh
python3 author_details.py                  # rewrite all nineteen sources
python3 author_details.py sill-corner      # just one, by id
```

The house has 494 connections in 27 families. Eight families already had a
catalog specimen; the other nineteen (sill and joist half-laps, a brace in a
post, fire-beam ties, floor posts on sleepers and stones, upper-floor framing,
and the purlin, hip, ridge and rafter cuts) had only a line in the house joint
schedule. This tool authors one 120 mm specimen for each, using the same
`joint()` source shape, `house_geom` colours and bake flags as the rest of the
catalog, with `tab: "house-details"`.

Most pieces are box CSG, but the roof needs two extras in this file: `trim()`
clips a convex prism with an arbitrary plane and stitches the cut cap, for the
square ends of hips and rafters; `profile_piece()` extrudes a 2D side profile
across the member width, so a rafter's 鳥口 birdsmouth has a horizontal seat
rather than a notch parallel to its own underside. Most details are yawed about
y in `yaw_detail()` so the fixed site camera sees the cut; geometry and explode
vectors turn together. `round_points()` puts every vertex on the 1 µm grid the
welding and topology checks use — without it an irrational sloped frame leaves
near-duplicate points a fraction of a micron apart. Original geometry, CC BY
4.0. Regenerate, then run `check_sources.py`, `bake.py` and `preview.py` as for
any other specimen.

### `author_house.py` + `house_geom.py` + `house_anim.py` — the house frame

```sh
python3 author_house.py      # ../house/source.json
python3 export_house.py      # ../house/house.glb, with the clip
```

The house is not a joint specimen: it is a 3 × 2 ken, two-storey frame with a
hip roof, built from full-length members and cut only where they meet.
`house_geom.py` holds the plan dimensions, the group palette and the members
that need their own local frame (braces, hips, common and jack rafters);
`author_house.py` builds the rest with axis-aligned box CSG from
`author_joint.compile_solid`, so the source remains plain faces and the GLB
writer can emit one node per timber. Joints are cut as housings, mortises,
half-laps and birdsmouths; wedges and pegs are extra faces in the wedge colour.

`house_anim.py` adds the `assemble` clip. It is a construction sequence, not a
single exploded pose: each timber withdraws along the extraction direction of
the joint that holds it, then parks clear of the frame; the house comes apart
from the ridge down and goes back together from the foundation up in twelve
stages. The rest pose stays assembled. The GLB is unlit, unsubdivided and
un-occluded on purpose: it stays around 2.25 MB and reads at house scale. The
34 original catalog specimens are untouched; the 19 house-only specimens come
from `author_details.py`, and the full connection schedule is in
[`../house/README.md`](../house/README.md).

### `house_links.py` — connection metadata for the viewer

```sh
python3 house_links.py       # ../house/connections.json
```

The GLB is one mesh per timber, so a joint has no mesh of its own. This tool
records every connection as an explicit instance: the member IDs it joins, a
point at the joint in the assembled pose, and the member a marker should follow
while the clip moves. It walks the same loops as `author_house.py` — sills,
posts, beams, 貫, braces, floor framing, roof beams, posts, purlins, rafters —
and asserts each ID against the authored frame, so a renamed or removed timber
fails instead of producing a marker in mid-air. Nothing is inferred from
bounding-box proximity.

The result is 272 pieces and 494 connections in 27 families, every one with a
catalog link: exact matches to a sheet specimen (`貫 ↔ post` → `tsutsumikomi-nuki`)
or to one of the 19 House details (`brace ↔ post` → `brace-into-post`,
`垂木 ↔ 母屋` → `rafter-over-purlin`), and related specimens for the remaining
families (`post ↔ sill` → `shitakone-hozo-wari-kusabi`, roof tenons →
`yatoi-hozo-shikuchi`, beam tenons → `naga-hozo-sashi-komisen-uchi`). The 29
foundation and ground pieces have no connection and are recorded as such.

### `house_viewer.js` — the interactive house

This is the custom element the old house tab loaded. It is kept in the
repository and served by `viewer.py`, but `build_site.py` no longer publishes it
(a stale `docs/house-viewer.js` is removed on rebuild). It reads
the GLB and `connections.json`, raycasts the timbers, and draws screen-space
marker sprites at the connection points. Hovering a timber outlines it and marks
its joints; hovering a marker ghosts every other timber and shows the joint's
name, description and a link straight to the matching catalog specimen. A click
or tap pins it, and the accessible **Browse** panel indexes all 494 connections
by family with a filter.
Focusing a joint writes a `#house/<id>?…` anchor with the connection id, camera
position and target, peel stop and paused clip time; the page script selects the
house tab for that prefix and `restoreFromHash()` rebuilds the exact view, so
Back after following a catalog link (or a reload) lands where the reader left.
The four peel stops ghost the roof, the upper storey or the masonry. Play/Pause,
replay, `currentTime`, Space, R and Escape are wired to the same clip as the
`<model-viewer>` specimens, and a WebGL or fetch failure falls back to the
poster and a GLB download.

### `build_site.py` — the GitHub Pages site

```sh
python3 build_site.py                       # ../docs, from ../joints
python3 build_site.py --repo-url https://github.com/<you>/<repo>
python3 build_site.py --preview             # also serve it on :8000
```

Reads `joints/sources/*.json` (title, Japanese name, credit, metadata), skipping
the 19 with `tab: "house-details"` — those are kept in the repository but
withheld from the site until corrected — copies the remaining 37
`joints/<id>.glb` files and their sunset previews, and writes `docs/index.html`
from `site_template.html`: a single **Joints** view, one section per joint with a
`#<id>` anchor, a `<model-viewer>` that plays the `assemble` clip, the Japanese
name in light gray under the romanised one, a beam-count badge, the usage note
and the strengths / weaknesses lists. The published site has no tabs: the
source `tab` values are kept for provenance only. The house frame, its
`connections.json` and `house-viewer.js` are not loaded, and stale copies are
removed from `docs/` on rebuild. Up / Down arrow keys step through the joints in
view order. Below 56 rem the index becomes a slide-in menu (button at the top
left) and every joint is a full-screen page: swipe up / down for the next /
previous joint (scroll snapping), drag sideways to rotate, with an `n / <count>`
counter and the credits along the bottom. Models load only near the viewport and
only once scrolling has settled (never mid-swipe): each stage is an empty box of
its final size with a spinner, the adjacent models are fetched at rest, and a
model fades in when it is ready.

The top of the index (and so the top of the phone menu) has a **Filter by beams**
menu and a full-text search box. The filter narrows the list to a beam count
(with per-count totals; the post counts, loose hardware does not). The
search covers each joint's romanised name, Japanese name, id and its metadata
prose with [`@leeoniya/ufuzzy`](https://github.com/leeoniya/uFuzzy) (MIT,
vendored under `vendor/` and copied into `docs/`): the query is filtered against
one haystack string per joint, ranked, and the list reordered to the ranking.
The library's `unicode: true` regexps are switched on so `金輪` and `腰掛け`
match as well as `kanawa`. Typing a single error still matches (`sanpo` finds
Sampo, `kama` finds Nimai-kama), no match shows a live-region message, Enter
follows the first hit, Escape clears the query, and `/` focuses the box from
anywhere. The search pool and the arrow-key order are the joints left after the
beam filter.

Plain static files, stdlib only. Regenerate and commit `docs/` after changing a
joint; publish with Pages set to the default branch, `/docs` folder.

### `viewer.py` — the same page, locally

```sh
python3 viewer.py --open       # builds the site into a temp folder and serves it
python3 viewer.py --port 9000
```

## Legal / scope

The models are reproduced under their own Creative Commons licenses (CC BY 4.0,
except `yatoi-hozo-shachi-sen-shiguchi`, which is CC BY-SA 4.0). The seventeen
authored joints, the nineteen house details and the three multi-beam specimens
(listed in [`../joints/README.md`](../joints/README.md)) are original geometry
released CC BY 4.0. The site's
search box uses MIT-licensed `@leeoniya/uFuzzy`, copied unmodified from npm; its
notice is in `vendor/ufuzzy.LICENSE`. The (unpublished) house viewer uses
MIT-licensed three.js r160, likewise copied unmodified; its notice is in
`vendor/three/LICENSE` and the vendored files and checksums are listed in
[`vendor/README.md`](vendor/README.md). See
[`../joints/README.md`](../joints/README.md) for the per-model credit.
