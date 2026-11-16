# The house

The open structural frame of the two-storey house in [`house.jpg`](../house.jpg)
and [`house-2.jpg`](../house-2.jpg). It is a **frame**, not a finished building:
there are no walls, floor boards, roof boards or tiles, so every post, beam and
joint stays visible.

- `source.json` — the frame, in the same face schema as the joint sources. One
  list with one level, `house`, and 272 timber pieces. There are no `assemble`
  offsets: the frame is static.
- `house.glb` — one mesh node per timber, flat per-face colours, no animation,
  15,530 triangles, about 2.1 MB.
- `sunset_house.png` — the poster render of the shipped GLB.

## Plan and dimensions

| | |
|---|---|
| plan | 3 bays × 2 bays, one ken (`1.82 m`) each → **5.46 × 3.64 m** |
| grid | four post lines across the long face, three across the short face |
| storeys | two, `2.70 m` floor-to-floor |
| principal members | `120 mm` posts, sills, plates and beams |
| studs, braces | `105 mm` and `90 mm` |
| joists, rafters | `60 mm` and `45 × 90 mm` |
| foundation | `450 mm` strip and pad footings, sill top at `570 mm` |
| roof | hip (`寄棟`), ridge along the long axis, `600 mm` eaves, ridge `1.82 m` long |

The ridge is deliberately only `W - D = 1.82 m` long, as in the reference: the
four hips meet it at the ends.

Coordinates are metres, Y up, in the closed pose. The origin is the centre of
the ground plan at grade. The frame is built in three layers:

- **base** — plinth, strip and pad footings, foundation stones, floor stones;
- **floor** — 床束, 大引 and 根太 on the ground floor, six upper 根太;
- **axis** — sills, posts, studs, 貫, braces, 火打梁, 胴差, 床梁 and 軒桁;
- **roof** — 小屋梁, 小屋束, 真束, 母屋, 棟木, 隅木, 垂木 and the jack rafters.

The colours follow the groups in `house-2.jpg`: axis terracotta, roof olive,
floor slate blue, foundation and stone grey. They are muted to sit with the
paper background. Lighting is the same baked directional term as the joint set
and the GLB is written with `KHR_materials_unlit`, so a viewer should not add
its own lights.

## Joint schedule

| Connection | Joint in the model |
|---|---|
| post ↔ sill | through tenon, protruding below the sill with a wedge |
| post ↔ 胴差 / 軒桁 | housed tenon in the post, 55 mm deep, with a komisen peg through the post |
| beam ↔ post | the post is continuous; each bay's beam has a housed tenon at both ends |
| 貫 ↔ post | 包み込み貫, scaled: a `105 × 120 mm` nuki, a 15 mm housing in the post, and a wedge on the outer face |
| 筋違 ↔ post / sill / beam | brace let into the post faces; its thickness is the housing |
| 火打梁 ↔ 土台 / 胴差 | diagonal corner tie resting on the sill or girder |
| 根太 ↔ 大引 | half-lap notch, 30 mm out of each member |
| 根太 ↔ 土台 | 30 mm housed end |
| 床束 ↔ 大引 | tenon into the sleeper, on a stone |
| 小屋梁 ↔ 軒桁 | housed tenon into the inner face of the plate |
| 小屋束 ↔ 小屋梁 | tenon into the top of the beam |
| 母屋 ↔ 小屋束 | the post runs 40 mm into the purlin; the purlin is notched over it |
| 垂木 ↔ 母屋 / 軒桁 / 棟木 | birdsmouth notch at each crossing |
| 隅木 ↔ 棟木 | the hip butts the ridge end; the ridge is notched for the 真束 |
| 土台 corners | half-lapped, alternating by wall |
| 胴差 / 軒桁 at posts | housed tenon, as at the other beam ends |

The brace, fire-beam, joist and rafter connections do not appear on the joint
reference sheets. They are authored in [`tools/author_house.py`](../tools/author_house.py)
and are **not** part of the 34-joint catalog: the house is one model, not a
joint specimen, and the site's joint counts do not change. If one of these
connections is wanted as a specimen later, its cut geometry can be lifted into
`tools/author_joint.py` and the catalog.

## Building

```sh
python3 tools/author_house.py      # house/source.json
python3 tools/export_house.py      # house/house.glb
python3 tools/preview.py house/source.json --sunset --level house \
    --size 1100 --ss 1 --glbdir house --outdir house \
    --margin 0.92 --bottom 0.01 --sun-yaw 40 --sun-pitch 27
python3 tools/build_site.py        # adds the third tab to docs/
```

`tools/house_geom.py` holds the dimensions, palette and the members built in a
local frame (braces, hips, rafters). The rest is axis-aligned box CSG via
`author_joint.compile_solid`, so the cuts are exact rectangles and the source
stays editable.

## What is left out

- wall and roof finishes, floor and roof boards, tiles and metalwork;
- the second-floor deck boards: the upper 根太 are shown, but the deck is left
  open so the ground-floor frame stays visible;
- door and window openings, stairs, and the interior partitions;
- the exact roof profile at the hips (the hips and jack rafters are cut square,
  not scribed), and the curved or tapered ends some of the reference timbers
  have.

## Attribution

The geometry is original, authored for this project from the two reference
drawings; it is not traced or copied from a third-party model. It is released
CC BY 4.0 under the same terms as the authored joints. The reference drawings
are included for provenance and remain under their own terms; the CC BY 4.0
grant covers the authored model and scripts, not the drawings.
