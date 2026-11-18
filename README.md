# Japanese joinery

Fifty-eight Japanese timber joints (継ぎ手 and 仕口) as interactive 3D models that
assemble and come apart, each tagged with its beam count, use, strengths and
weaknesses, with the tools that rebuild them and the site that shows them:
**<https://ixday.github.io/carpentry/>**. The open frame of a two-storey house
is kept in `house/` but is not published to the site.

Seventeen models are by [thejoinery](https://sketchfab.com/thejoinery) on
Sketchfab (CC BY 4.0, one CC BY-SA 4.0). They were read from the public viewer,
split into timbers, re-lit with a baked paper-sunrise look, given an `assemble`
animation, and corrected where the author's pose was not the true closed joint.
Seventeen joints with no licensed source model (fourteen column-and-beam
`shikuchi`, three splices) are authored in this repository, using
`tools/author_joint.py`: fifteen from the reference sheet and two from published
descriptions of joints the sheet does not show. A further nineteen specimens,
authored with `tools/author_details.py`, cover every connection family the house
frame makes beyond the sheets: halved sills and joists, a brace in a post, floor
posts, and the hip, purlin and rafter cuts of the roof. Five more, authored with
`tools/author_multi.py`, extend the direction series to connections of three,
four, five and six beams. Every source is tagged with `beams`, `usage`,
`strengths` and `weaknesses` in `tools/joint_meta.py`. Per-model links,
attribution, the change list and the references used are in
[`joints/README.md`](joints/README.md).

## Layout

- `joints/<id>.glb` — the whole joint, every timber its own mesh node, with the
  `assemble` animation
- `joints/<id>/<piece>.glb` — the same timbers one by one, in world space
- `joints/previews/sunset_<id>.png` — 1100×1100 renders of the shipped GLBs
- `joints/sources/<id>.json` — the source: faces of every timber (in the
  exploded pose), the closed-pose offsets (`assemble`), an optional `approach`
  stage, and the attribution
- `house/` — the open frame of the house in `house.jpg`: `source.json`,
  `house.glb` with its unbuild/rebuild clip, `connections.json` with every joint
  instance, a poster and notes; see [`house/README.md`](house/README.md)
- `docs/` — the generated GitHub Pages site (`tools/build_site.py`)
- `tools/` — capture, import, bake, check and site tools; see
  [`tools/README.md`](tools/README.md)
- `joints.jpg`, `joints-2.jpg` — the reference sheets the authored joints were
  drawn from
- `PLAN.md` — inventory, coverage against the reference sheet, and the queue of
  joints still to add

Every joint GLB is Y-up and right-handed, with flat per-face normals and an
indexed `COLOR_0`. The material is `KHR_materials_unlit`: the lighting, cast shadows and
ambient occlusion are baked into the vertex colours, so the look is static and
viewer-independent. A viewer should not add its own lights, and tone mapping
(ACES, Filmic) shifts the colours; compare with a Standard/sRGB view transform.
The house GLB uses the same unlit material and baked colours, and its rest pose
is the assembled frame. Its one clip, `assemble`, unbuilds the house from the
ridge down and rebuilds it from the foundation up, one timber at a time, in
27 seconds. Its faces are not subdivided or ambient-occluded: the point is the
frame at architectural scale, not a close-up specimen.

## Browsing

```sh
python3 tools/viewer.py --open
```

Serves the same page that is published on GitHub Pages: a single **Joints** view
with one anchored section per joint and no tabs. Each section shows the assembly
animation, a beam-count badge, a short usage note and lists of strengths and
things to watch for; the scroll wheel zooms the model and Up / Down step between
joints. On a phone the index becomes a slide-in menu with one joint per screen.
A **Filter by beams** menu narrows the 58 joints by how many beams meet at them
(1–6; the post, pegs, wedges and keys are not counted). The index has a search
box at the top (`/` focuses it): it matches romanised and Japanese names and
the metadata prose, ranks the hits, and on a phone it filters the same
slide-in menu. The house frame and its viewer remain in `house/` and
`tools/house_viewer.js` for local use but are not built into the published site.

## The baked look

A high-key paper-sunrise rig is evaluated in display sRGB and baked into
`COLOR_0`:

- a bright, near-white sky fill from the front and above, so the visible faces
  read as front-lit;
- a soft warm sun about 48° up from the back-left, adding top light and short
  shadows that run towards the front-right;
- a light paper wash (slight desaturation and a cream haze) to keep the result
  pastel and low-contrast;
- cast shadows that read as a hard cut: every vertex samples the sun's whole
  disk, but the disk is tiny and the residual penumbra is snapped, so a shadow
  edge lands as a crisp line instead of a gradient;
- a thin constant-colour border strip on every crease and silhouette, so corners
  stay sharply drawn instead of fading across a subdivided triangle.

The flat red disk in the previews is a backdrop graphic, not the light
direction. Every face is subdivided before baking so shadow boundaries and
occlusion gradients have vertices to land on. The rig constants and flags are in
[`tools/README.md`](tools/README.md).

## Rebuilding

```sh
cd tools
python3 author_joint.py                      # regenerate the authored sources
python3 author_details.py                    # the 19 house-detail specimens
python3 author_multi.py                      # the 5 joints with 3-6 beams
python3 joint_meta.py                        # re-stamp joint metadata
for f in ../joints/sources/*.json; do
    id=$(basename "$f" .json)
    python3 bake.py "$f" ../joints --level "$id" --pieces --no-ground \
        --detail 0.02 --edge 0.0015 --edge-lift 0.0004 --ao-dist 0.10
    python3 preview.py "$f" --sunset --size 1100 --ss 2 \
        --glbdir ../joints --outdir ../joints/previews --level "$id"
done
python3 validate.py ../joints
python3 author_house.py                      # the house frame
python3 export_house.py
python3 house_links.py                       # house/connections.json
python3 build_site.py --repo-url https://github.com/IxDay/carpentry
```

The `author_joint.py` line only touches the seventeen authored sources and
`author_details.py` only the nineteen house details; the rest come from captures.
The bake/preview loop processes every source, so all 58 specimens are kept in
step. `--no-animation` drops the `assemble` clip. Importing a new Sketchfab model
and checking an animation for timbers passing through each other are described
in [`tools/README.md`](tools/README.md).

## Licensing

The CC BY 4.0 models may be reused with attribution; each GLB's
`asset.copyright` and `joints/sources/<id>.json` carry it. `yatoi-hozo-shachi-sen-shiguchi`
is CC BY-SA 4.0: its baked GLB and pieces are a derivative and are distributed
under the same license. The seventeen authored joints (three splices and fourteen
column-and-beam `shikuchi`), the nineteen house details and the five multi-beam
specimens, all listed in [`joints/README.md`](joints/README.md), are original
geometry released CC BY 4.0. The house frame in `house/` is likewise original
geometry, released CC BY 4.0; the reference drawings remain under their own
terms. The house viewer source uses three.js r160 (MIT), vendored unmodified
with its notice under `tools/vendor/three/`, but is no longer part of the
published site.
