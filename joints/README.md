# joints

Fifty-three Japanese timber joints (継ぎ手 / 仕口) in a pastel paper-sunrise
style. Seventeen are from the [thejoinery](https://sketchfab.com/thejoinery)
collection on Sketchfab, rebuilt and baked; seventeen more, with no licensed
source model, are authored in this repository with
[`tools/author_joint.py`](../tools/author_joint.py) (fourteen column-and-beam
`shikuchi` joints, three splices — fifteen drawn from the reference sheet
柱（軸組）の納まり and two from published descriptions of joints the sheet does not
show). A further nineteen are authored with
[`tools/author_details.py`](../tools/author_details.py) for the connection
families the house frame uses beyond the sheets. The site keeps the two
off-sheet joints in a second tab, and the house details in a fourth tab after
**The house**. There is **no garden or ground plane**: the timbers float against
the paper backdrop, which keeps the focus on the cut geometry.

## Layout

- `joints/<id>.glb` — the whole joint, with every timber in its own mesh node
- `joints/<id>/<piece>.glb` — the same timbers one by one, baked in world space
- `joints/previews/sunset_<id>.png` — 1100×1100 renders of the shipped GLBs
- `joints/sources/<id>.json` — catalog-shaped source (a one-element list) with
  the attribution and the assembled-pose offsets

Names are romanised; `part-a`/`part-b` are the two main timbers, `key`,
`key-2`, … are the pegs, wedges and keys.

## The set

| Asset | Japanese | License | Pieces |
|---|---|---|---|
| [`daimochi-tsugi`](../tools/author_joint.py) | 台持ち継ぎ | CC BY 4.0 (authored) | 3 |
| [`doutsuki-ari-tsugi`](../tools/author_joint.py) | 胴付き蟻継ぎ | CC BY 4.0 (authored) | 2 |
| [`hako-sen-tsugi`](https://sketchfab.com/3d-models/hako-sen-tsugi-881723f8c6794db5a9dbe9dc2fb3a69b) | 箱栓継ぎ | CC BY 4.0 | 4 |
| [`hira-isuka-tsugi`](https://sketchfab.com/3d-models/hira-isuka-tsugi-bd6b1bea223144868199fee6a28baf5c) | 平居木継ぎ | CC BY 4.0 | 2 |
| [`kakeawase-komisen-tsugi`](https://sketchfab.com/3d-models/kakeawase-komisen-tsugi-ac403983452d4524a7e23350c2ace36c) | 掛け合わせ込み栓継ぎ | CC BY 4.0 | 3 |
| [`kakushi-kanawa-tsugi`](https://sketchfab.com/3d-models/kakushi-kanawa-tsugi-d3dbb63c57554cf1852724d510cb63e2) | 隠し金輪継ぎ | CC BY 4.0 | 4 |
| [`kanawa-tsugi`](https://sketchfab.com/3d-models/kanawa-tsugi-713b9b3a98344094a008535738348791) | 金輪継ぎ | CC BY 4.0 | 3 |
| [`kata-kama-hozo-sashi`](../tools/author_joint.py) | 片鎌ホゾ差し | CC BY 4.0 (authored) | 2 |
| [`katagi-ooire`](../tools/author_joint.py) | 傾ぎ大入れ | CC BY 4.0 (authored) | 2 |
| [`komisen-inro-tsugi`](https://sketchfab.com/3d-models/komisen-inro-tsugi-ee2d1506029e41068772c19fae51df96) | 込み栓入れ枘継ぎ | CC BY 4.0 | 3 |
| [`koshikake-ari-tsugi`](https://sketchfab.com/3d-models/koshikake-ari-tsugi-6a06924b8c5243c0beee65e5535d1820) | 腰掛け蟻継ぎ | CC BY 4.0 | 2 |
| [`meji-tsukikake-awase-tsugi`](https://sketchfab.com/3d-models/meji-tsukikake-awase-tsugi-64cc903d315b40d6a5f8f6086befa1fd) | 目地突掛け合わせ継ぎ | CC BY 4.0 | 2 |
| [`miyajima-tsugi`](https://sketchfab.com/3d-models/miyajima-tsugi-40104d0e736c4bb0b2a75e2c91db0730) | 宮島継ぎ | CC BY 4.0 | 3 |
| [`naga-hozo-sashi-komisen-uchi`](../tools/author_joint.py) | 長ホゾ差し込み栓打ち | CC BY 4.0 (authored) | 3 |
| [`niho-sashi-shikuchi`](../tools/author_joint.py) | 二方差し仕口 | CC BY 4.0 (authored) | 3 |
| [`nimai-kama-tsugi`](https://sketchfab.com/3d-models/nimai-kama-tsugi-5aa7e4181c674070a9d0c291c0f129f9) | 二枚鎌継ぎ | CC BY 4.0 | 5 |
| [`okkake-daisen-tsugi`](https://sketchfab.com/3d-models/okkake-daisen-tsugi-5b161a4a18ae4054a820d32df2b20ca5) | 追掛け大栓継ぎ | CC BY 4.0 | 4 |
| [`okkake-daisen-tsugi-mochidashi`](../tools/author_joint.py) | 追掛け大栓継ぎ（持ち出し継ぎ） | CC BY 4.0 (authored) | 4 |
| [`osaka-jo-otemon-hikae-bashira-tsugi`](https://sketchfab.com/3d-models/osaka-jo-otemon-hikae-bashira-tsugi-a1cf8bd826504ef2acc1b34510a06d27) | 大阪城大手門控え柱継ぎ | CC BY 4.0 | 2 |
| [`otoshi-ari-hozo-shikuchi`](https://sketchfab.com/3d-models/otoshi-ari-hozo-shikuchi-269f0b5a914e437ba10c0aed445711df) | 落し蟻枘仕口 | CC BY 4.0 | 3 |
| [`sage-kama-oire`](../tools/author_joint.py) | 下げ鎌（大入れ） | CC BY 4.0 (authored) | 3 |
| [`sampo-sashi-shikuchi`](../tools/author_joint.py) | 三方差し仕口 | CC BY 4.0 (authored) | 3 |
| [`shihou-ari-tsugi`](https://sketchfab.com/3d-models/shihou-ari-tsugi-c1d6168a3b4e49a983c3ba815e0b4437) | 四方蟻継ぎ | CC BY 4.0 | 2 |
| [`shihou-sashi-shikuchi`](../tools/author_joint.py) | 四方差し | CC BY 4.0 (authored) | 7 |
| [`shitakone-hozo-hana-sen`](../tools/author_joint.py) | 下小根ホゾ鼻栓打ち | CC BY 4.0 (authored) | 3 |
| [`shitakone-hozo-tasuki-gake`](../tools/author_joint.py) | 下小根ホゾ（襷掛付） | CC BY 4.0 (authored) | 2 |
| [`shitakone-hozo-wari-kusabi`](../tools/author_joint.py) | 下小根ホゾ割り楔打ち | CC BY 4.0 (authored) | 4 |
| [`suitsuki-sashi-shikuchi`](https://sketchfab.com/3d-models/suitsuki-sashi-shikuchi-2edef5371cb34374b9b6046e435603b6) | 吸付差し仕口 | CC BY 4.0 | 2 |
| [`tsutsumikomi-nuki`](../tools/author_joint.py) | 包み込み貫 | CC BY 4.0 (authored) | 3 |
| [`uwakone-hozo-uchi-nuki-komisen`](../tools/author_joint.py) | 上小根ホゾ打ち抜き込み栓打ち | CC BY 4.0 (authored) | 3 |
| [`uwakone-hozo-wari-kusabi`](../tools/author_joint.py) | 上小根ホゾ割り楔打ち | CC BY 4.0 (authored) | 4 |
| [`yatoi-hozo-shachi-sen-shiguchi`](https://sketchfab.com/3d-models/yatoi-hozo-shachi-sen-shiguchi-5f3cc05626b641f19bd42d30a976db3d) | 雇い枘車知栓仕口 | **CC BY-SA 4.0** | 5 |
| [`yatoi-hozo-shikuchi`](../tools/author_joint.py) | 雇い枘仕口 | CC BY 4.0 (authored) | 3 |
| [`yose-ari-hozo-shikuchi`](https://sketchfab.com/3d-models/yose-ari-hozo-shikuchi-3e2f52c247a84a7f9a4caaaefefa4744) | 寄せ蟻枘仕口 | CC BY 4.0 | 2 |

The seventeen Sketchfab models are by **thejoinery**
(<https://sketchfab.com/thejoinery>). Every `sources/<id>.json` repeats the
title, author, canonical URL, license and the change list in its `source`
object, and the same credit is embedded in each GLB's `asset.copyright`. The
seventeen authored joints carry the project as author; fifteen credit the
reference sheet they were drawn from, and the two off-sheet joints
(`doutsuki-ari-tsugi`, `tsutsumikomi-nuki`) credit the published descriptions
they were drawn from.

## House details

The house frame has 494 connections in 27 families. Eight of those families
already have a specimen in the set above; the other nineteen got their own at
the house's 120 mm scale so that every house viewer card can link straight to
the joint it names. They are original geometry, authored from the house's joinery
with [`tools/author_details.py`](../tools/author_details.py), and released
**CC BY 4.0** like the rest of the authored joints. Most are box CSG; the sloped
roof members use a local member frame, arbitrary-plane trimming for square-cut
hip and rafter ends, and a profile prism for a birdsmouth with a horizontal seat.

| Asset | Japanese | License | Pieces |
|---|---|---|---|
| [`sill-corner`](../tools/author_details.py) | 土台の留め | CC BY 4.0 (authored) | 2 |
| [`brace-into-post`](../tools/author_details.py) | 筋違 | CC BY 4.0 (authored) | 2 |
| [`fire-beam-tie`](../tools/author_details.py) | 火打梁 | CC BY 4.0 (authored) | 3 |
| [`joist-half-lap`](../tools/author_details.py) | 根太の相欠き | CC BY 4.0 (authored) | 2 |
| [`joist-into-sill`](../tools/author_details.py) | 根太の土台差し | CC BY 4.0 (authored) | 2 |
| [`floor-post-into-sleeper`](../tools/author_details.py) | 床束の大引差し | CC BY 4.0 (authored) | 2 |
| [`floor-post-on-stone`](../tools/author_details.py) | 床束の礎石 | CC BY 4.0 (authored) | 2 |
| [`sleeper-into-sill`](../tools/author_details.py) | 大引の土台差し | CC BY 4.0 (authored) | 2 |
| [`upper-joist-half-lap`](../tools/author_details.py) | 二階根太の相欠き | CC BY 4.0 (authored) | 2 |
| [`upper-joist-into-girder`](../tools/author_details.py) | 二階根太の胴差差し | CC BY 4.0 (authored) | 2 |
| [`purlin-under-hip`](../tools/author_details.py) | 母屋と隅木 | CC BY 4.0 (authored) | 2 |
| [`hip-into-ridge`](../tools/author_details.py) | 隅木と棟木 | CC BY 4.0 (authored) | 2 |
| [`hip-over-plate`](../tools/author_details.py) | 隅木と軒桁 | CC BY 4.0 (authored) | 3 |
| [`rafter-at-ridge`](../tools/author_details.py) | 垂木と棟木 | CC BY 4.0 (authored) | 2 |
| [`rafter-at-hip`](../tools/author_details.py) | 垂木と隅木 | CC BY 4.0 (authored) | 2 |
| [`rafter-over-purlin`](../tools/author_details.py) | 垂木と母屋 | CC BY 4.0 (authored) | 2 |
| [`rafter-over-plate`](../tools/author_details.py) | 垂木と軒桁 | CC BY 4.0 (authored) | 2 |
| [`jack-rafter-at-hip`](../tools/author_details.py) | 短垂木と隅木 | CC BY 4.0 (authored) | 2 |
| [`jack-rafter-over-plate`](../tools/author_details.py) | 短垂木と軒桁 | CC BY 4.0 (authored) | 2 |

## Changes from the source models

The Sketchfab models are authored in millimetres and exploded. For each one:

- read the mesh from the public viewer's WebGL buffers (the download API needs
  an account) and decoded its quantised positions / octahedral normals;
- split the connected components into individual timbers;
- rebuilt flat per-face normals and merged coplanar triangles back into quads
  and simple polygons, falling back to the authored triangles where an outline
  does not trace cleanly;
- scaled from millimetres to metres, centred on x/z, and dropped the lowest
  point to `y = 0`;
- `hira-isuka-tsugi` and `kakeawase-komisen-tsugi`: the generated closing offset
  left the halves apart, and the slanted faces of the two halves differed by
  4-5 mm, so no offset made every face touch. The closed pose is now the real
  contact pose and `tools/mate_faces.py` snaps one timber's mating corners onto
  the other's;
- `meji-tsukikake-awase-tsugi`, `miyajima-tsugi`, `osaka-jo-otemon-hikae-bashira-tsugi`,
  `yose-ari-hozo-shikuchi`, `otoshi-ari-hozo-shikuchi`, `nimai-kama-tsugi`,
  `yatoi-hozo-shachi-sen-shiguchi`: closed poses corrected the same way (found
  by scanning to contact and checking every mating face pair, 0.00-0.05 mm). The
  dovetail joints needed a second stage: `yose-ari-hozo-shikuchi` drops into the
  entry pocket then slides along the dovetail, `otoshi-ari-hozo-shikuchi` drops
  onto the slope before its wedge key goes in, `nimai-kama-tsugi` lifts a blade
  15 mm off its hook step first (both through `approach`). `shihou-ari-tsugi` had
  its dovetail rim corners moved up to 1.2 mm so its faces are parallel to the
  diagonal slide. In `yatoi-hozo-shachi-sen-shiguchi` the loose tenon is moved
  into its seat in the post (it stays there when the beam is withdrawn);
- `suitsuki-sashi-shikuchi`: the generated offset stopped the beam 45 mm above
  the post's shelf, leaving the tenon out of its pocket and no shared vertices.
  The closed pose drops it the full 200 mm, flush with the post top;
- `osaka-jo-otemon-hikae-bashira-tsugi`: the model is authored at 18 mm where the
  others are 120 mm, so the bake looked blurred and the checks were too coarse.
  Enlarged 6.67x (`tools/rescale_joint.py`), and the motion corrected: the splice
  cannot be lifted straight up, it slides out along the slope of its shoulders
  (about 50 degrees from horizontal in the y-z plane, `approach`) and is then
  lifted clear;
- `kanawa-tsugi` only: the author's pose is the loose, mated joint (step walls
  touching). The closed pose shifts `part-b` 17 mm (one key width) along the
  sloping joint line, which opens the gap the komisen fills;
- baked a sunset rig (unlit vertex colours, cast shadows, AO, paper wash, thin
  edge strips) and omitted the ground slab.

The author's exploded arrangement is kept in the static GLB. The `assemble`
offsets in each source close the joint for the animation below.

The seventeen authored joints (`daimochi-tsugi`, `yatoi-hozo-shikuchi`,
`sampo-sashi-shikuchi`, `niho-sashi-shikuchi`,
`naga-hozo-sashi-komisen-uchi`, `kata-kama-hozo-sashi`, `sage-kama-oire`,
`shihou-sashi-shikuchi`, `katagi-ooire`, `okkake-daisen-tsugi-mochidashi`,
`doutsuki-ari-tsugi`, `tsutsumikomi-nuki`, and the five `小根ホゾ` variants)
are different in kind: they are modelled to the reference sheet already
**closed**, then exploded for the animation, rather than captured exploded and
closed in place. `author_joint.py` builds each timber from axis-aligned boxes
minus the mortises and housings, welds the boundary, and records the reverse of
the exploded offsets as `assemble`. Tapered wedges and pegs, which box CSG cannot
express, are lofted between two parallel sections. They share the same timbers,
scale, normals, bake and animation as the imported set, and are checked the same
way (`tools/check_sources.py`: closed pose watertight and manifold, consistent
winding, zero volumetric overlap between timbers, every mating face in contact).
`daimochi-tsugi`, `okkake-daisen-tsugi-mochidashi` and `doutsuki-ari-tsugi`
are splices; the other fourteen are `shikuchi` (loose tenon,
two-/three-/four-way `差し`, the `小根ホゾ` two-tier tenon family, the long
through tenon, the one-sided kama, the 下げ鎌, the slanted housing and the
包み込み貫) and were added because the reference sheet is almost entirely
column-and-beam work while the imported collection is almost entirely splices.

In the `小根ホゾ` family the full-section 大根 sits at the beam's shoulder and,
past the vertical step (腰), the narrower 小根 runs on into the post. The 下
variants keep the small root's nose flush with the tenon underside; the 上
variants put it at the top, so the 腰 sits low. `襷掛付` forks the small root
around a vertical bridge left in the post; the other four are through joints,
locked by a split kerf and two wedges, a tapered nose peg, or a square `込み栓`
driven through the post's cheeks.

`naga-hozo-sashi-komisen-uchi` is the plain long through tenon: full section,
untiered, passing clean through the post and standing 45 mm proud. A tapered
`込み栓` is driven sideways through post and tenon, across the tenon's width, and
cut off flush with both cheeks.

`kata-kama-hozo-sashi` is the one-sided counterpart: the post's tenon carries a
hook along one lower edge only, and the sill's mortise is a slot open at the
sill's end, so the post is slid in along the sill. The hook runs in under the
sill's lip and then cannot be lifted out; its square back bears on the lip
under uplift, while the post's shoulder seats on the sill and the tenon clears
the mortise floor. The hook is kept square (no tightening slope) because the
authoring CSG is axis-aligned.

`shihou-sashi-shikuchi` takes a beam from each of the post's four faces at one
level. Two through-tenons cannot share a core, so the pairs are staggered: the
two x beams' `竿` sit in the lower half of the beam depth, the two z beams' in
the upper half, and each long tenon passes through the post and 30 mm into the
end of the beam opposite, so the four members tie one another. One tapered
plate `込み栓` drops through each pair from the post's top face and stands a
little proud, ready to be trimmed flush.

`katagi-ooire` is the fully housed joint with the seam cut at a slope instead
of square. The beam is let into the post's face at full section, but its end
runs 40 mm deeper at the bottom, into a matching triangular rebate, so the lower
end sits in under the post's overhanging cheek and the upper end is flush. The
whole load bears on the sloped face and the beam cannot be lifted out; it is
withdrawn straight along its own axis, and no key is needed. Both timbers are
constant-section prisms (`loft()` with identical top and bottom sections) whose
outline carries the slope, so nothing had to be cut at an angle.

`okkake-daisen-tsugi-mochidashi` takes the same 追掛け family as the imported
`okkake-daisen-tsugi`, but with the tenons left long: each timber's tenon is
carried out past the other's shoulder, so its nose stands 20 mm proud of the
finished surface and seats in a shallow rebate cut for it. The lap is 280 mm
long and half the section deep, the upper half belonging to one timber and the
lower to the other, so each tenon is trapped by the other timber and the two
halves cannot be lifted apart. Two 50 × 40 `大栓` are driven down through the
lap, each passing through both tenons, with their heads left proud on the top
face. The two timbers are the same part turned half round about the joint's
axis, which is why one nose comes out on top and the other underneath. The
sheet prints both names for this one drawing and shows only the prepared end,
so the closed form here is an interpretation: the projecting tenon is what
`持ち出し` names, and the noses are the visible result.

`doutsuki-ari-tsugi` is the first of the two joints the reference sheets do not
show. It is a dovetail cut in **plan** rather than in elevation: the 120 mm
timber's full depth carries a tenon that is 60 mm wide at the shoulders and
100 mm at the nose, so once the socket timber is lowered over it the two cannot
be pulled apart along their length. The socket is open at the top and bottom, so
the joint closes with a straight vertical drop and the shoulders meet at the
seam. It is the 蟻継ぎ family's plan-cut counterpart to the imported
`koshikake-ari-tsugi` and `shihou-ari-tsugi`, which cut their dovetails in
elevation.

`tsutsumikomi-nuki` is the second. The nuki runs 90 mm into the 120 mm post and
its last 15 mm is rebated 15 mm up from the underside; the post keeps a 15 mm
shelf under that rebate and a 30 mm wall beyond the end, so the end is wrapped
rather than merely housed. Assembly needs three moves: offer the nuki up 15 mm,
run it home over the shelf, then lower it onto the shelf, and drive a wedge into
the 15 mm gap above its back at the mouth. The `approach` path in the source
records those moves, so the animation shows the end being caught rather than
sliding straight in.

## Assemble animation

Each joint GLB carries one glTF animation named `assemble` (24 fps, ~6 s,
looping):

1. the assembled joint holds for 0.9 s;
2. every key/peg withdraws first along its own insertion axis (0.9–1.45 s),
   then moves aside to its exploded pose (1.45–1.85 s);
3. the main timbers separate along the member axis (1.9–3.0 s), holding
   exploded for a moment;
4. the timbers come back together (3.3–4.4 s);
5. the keys move back over their holes (4.45–4.85 s) and are driven home along
   the insertion axis last (4.85–5.5 s);
6. the assembled joint holds to the end.

Withdrawing a key on the straight diagonal to its exploded place would drag it
through the surrounding timber, so the axial slide is a separate step. A source may also carry an `approach`
vector (kanawa-tsugi): that timber is first slid back along the pitch to the
mated pose, then lifted straight up; assembly runs the other way, and the key
is driven in last. The sloping joint line is why the slide is both z and y. A
list of vectors gives a whole path instead (`tsutsumikomi-nuki` is offered up
15 mm, slid home over the post's shelf and lowered onto it). That is
what makes the lock readable: in `kanawa-tsugi` the upper half drops vertically
and only then does the horizontal key enter; in `okkake-daisen-tsugi` both
vertical keys lift/drop clear before the beams slide apart.

It is sampled as node translations with linear interpolation, so any glTF
viewer can play it; model-viewer picks it up with `autoplay` and
`animation-name="assemble"`. The viewer page also has a **Replay assembly**
button.

## Rebuilding

From `tools/`:

```sh
python3 import_joint.py caps/<uid>.json ../joints/sources/<id>.json \
    --id <id> --title <Title> --uid <uid> --url <model-url>
python3 bake.py ../joints/sources/<id>.json ../joints --level <id> \
    --pieces --no-ground --detail 0.02 \
    --edge 0.0015 --edge-lift 0.0004 --ao-dist 0.10
python3 preview.py ../joints/sources/<id>.json --sunset \
    --size 1100 --ss 2 --glbdir ../joints --outdir ../joints/previews --level <id>
```

The capture JSON comes from `tools/sketchfab_capture.mjs`; see
[`tools/README.md`](../tools/README.md). Use `--no-animation` to bake without
the `assemble` clip, or `--fps` to change its sample rate.

The seventeen authored joints have no capture step; regenerate their sources from the
joint definitions, then bake and preview the same way:

```sh
python3 author_joint.py                 # rewrites all seventeen sources
python3 author_joint.py daimochi-tsugi  # or one
python3 author_details.py               # rewrites all nineteen house details
python3 author_details.py sill-corner   # or one
```

The house details use arbitrary-plane trimming and a profile-prism extruder for
the sloped cuts; `author_details.py` rounds every vertex to the 1 µm grid so the
welded solids stay closed. Check them with `python3 check_sources.py <id>` before
baking.

To browse the result:

```sh
python3 tools/viewer.py --open       # same page as the published site
```

## References

Used to correct the assembly animations (what each joint is, how it is put
together, where the key goes):

- JAANUS, *kanawa tsugi 金輪継* —
  <https://projects.mcah.columbia.edu/jaanus/node/3413>: oblique, housed,
  rabbeted, T-shaped, half-blind scarf joint; cannot slide together from the
  side; the komisen is driven through the central opening.
- Denmoku database (伝統木造 joint tests), reference drawing list, nos. 39–47
  (金輪継ぎ) — <http://www.denmoku-db.jp/files/libs/86/201703290450302471.pdf>:
  side elevation with the long sloping joint line and the 15 mm key gap.
- Kyoto Araki Komuten, 金輪継 —
  <http://kyoto-araki.jp/kyomachiya/kig%75mi/kanawa.html>: the T-shaped mechi
  rules out dropping the timber in from above; after mating, shift along the
  axis by the key's amount.
- Uchimill, 継手 (金輪継ぎ) —
  <https://uchimill.com/2019/05/27/makinghouse-tipstsugite-1/>: leave a gap at
  the centre, assemble loosely, then drive the komisen into the gap to draw the
  timbers tight.
- Nekodigi, 金輪継ぎを設計して3Dプリントする —
  <https://nekodigi.hatenablog.com/entry/2020/04/04/%E3%80%90Processing%E3%80%91%E9%87%91%E8%BC%AA%E7%B6%99%E3%81%8E%E3%82%92%E8%A8%AD%E8%A8%88%E3%81%97%E3%81%A63D%E3%83%97%E3%83%AA%E3%83%B3%E3%83%88%E3%81%99%E3%82%8B>:
  a 3D-printed build of the joint with a Fusion 360 assembly animation
  (<https://www.youtube.com/watch?v=rmxwNI-sSm0>).
- Fine Woodworking, *5 spectacular Japanese joints* —
  <https://www.finewoodworking.com/2021/09/29/5-spectacular-japanese-joints>;
  Core77, *Crazy Japanese Technique for Splicing the Bottom of a Rotted Column* —
  <https://www.core77.com/posts/136894/Crazy-Japanese-Technique-for-Splicing-the-Bottom-of-a-Rotted-Column>;
  The Carpentry Way, *Chasing transcendence* —
  <https://thecarpentryway.blog/2012/12/chasing-transcendence/>: the Otemon
  splice (basara-tsugi) of Osaka Castle: two opposing faces are dovetails, two
  are "like a sword tip", and the sloped shoulders let the repair piece slide
  into the upper one; a pin or wedge locks it.
- Big's Woodworking, kanawa tsugi joinery models, part 2 —
  <https://bigsandwoodworking.com/kanawa-tsugi-joinery-models-part-2>: the
  tapered trapezoid wedge and the deliberate gap at the stub tenon.
- Sketchfab model by thejoinery (no animation) —
  <https://sketchfab.com/3d-models/kanawa-tsugi-713b9b3a98344094a008535738348791>.

## Contact / mortise accuracy pass

`tools/check_sources.py` already rejects overlapping or non-manifold solids, but
it allows mating faces to touch, so a joint whose pieces floated 0.4–2.5 mm
apart still passed. `tools/check_contact.py` was added to measure
surface-to-surface distance in the closed pose and report disconnected piece
groups. Nine specimens failed it: `brace-into-post`, `hip-over-plate`,
`jack-rafter-at-hip`, `jack-rafter-over-plate`, `purlin-under-hip`,
`rafter-at-hip`, `rafter-over-plate`, `rafter-over-purlin` and
`shitakone-hozo-hana-sen`. They were rebuilt so every piece now contacts its
neighbour: the brace bears on the bottom of its post housing, the hip/rafter
end cuts meet their neighbours exactly, the birdsmouth seats sit on the purlin
and plate tops, and the nose peg fills its mortise and bears on the post face.
All 53 sources now have one connected piece graph in the closed pose.

Research used for the dimensions and for deciding which connections need a
recess (rather than only a bearing face):

- Flat35 2025 specification sample, §§5.1.2–5.1.3 and 5.9.1–5.9.8 —
  <https://www.inoueshoin.co.jp/e-flat35/sample/sample.html>: 120 mm standard
  sill, 90 mm sleepers, 30×90 mm braces; housed/dovetailed sill corners and
  sleeper joints; joists simply bear at 45–60 mm but use a housing or
  `渡りあご` at 90 mm+; `火打ちばり` uses `かたぎ大入れ`, not face bearing.
- 中央工学校, 火打 — <https://chuoko.ac.jp/2021/01/15/35016/>: the fire beam
  is laid out with a 1:1:√2 triangle and cut with `傾ぎ大入れ` so it carries
  force through a one-sided housing in the sill.
- 下山眞司, 土台・大引・床束 joints —
  <https://ameblo.jp/archi1217ss-7/entry-12926333294.html> and 梁と小梁・根太 —
  <https://ameblo.jp/archi1217ss-7/entry-12926333763.html>: housed sill and
  sleeper joints, the `渡りあご` alternative, and the size rules behind the
  floor-detail sections.
- JAANUS, `taruki` / `munagi` / `moya` / `sumigi` —
  <http://www.aisf.or.jp/~jaanus/deta/t/taruki.htm>,
  <http://www.aisf.or.jp/~jaanus/deta/m/munagi.htm>,
  <http://www.aisf.or.jp/~jaanus/deta/m/moya.htm>,
  <http://www.aisf.or.jp/~jaanus/deta/s/sumigi.htm>: roof-member load paths;
  the hip is larger than a common rafter and receives jack-rafter and purlin
  ends.
- 展開図ラボ, 垂木欠き / 鳥口 — <https://tenkaizulab.com/column/taruki-kaki/>
  and <https://tenkaizulab.com/articles/taruki-nagasa/>: for a 4寸 (0.4) slope
  the rafter's `座` (seat) is about 50 mm for a 20 mm `立水` (plumb cheek), and
  the beam-top notch depth is `(beam width / 2) × slope`. The roof details were
  changed from the earlier 100 mm seat with a 1 mm reveal to a 50 mm seat and
  20 mm cheek, with the seat now flush on the 120 mm purlin/plate top.
- 展開図ラボ, 隅木の計算 — <https://tenkaizulab.com/articles/sumigi-keisan/>
  and 配付垂木 — <https://tenkaizulab.com/articles/haitsuke-taruki/>: hip
  slope is roof slope / √2; jack rafters stop against the hip's side face and
  are cut to that face rather than crossing it.
- thejoinery STEP archive, e.g.
  <https://thejoinery.jp/item.php?id=97749> (kanawa),
  <https://thejoinery.jp/item.php?id=74935> (okkake),
  <https://thejoinery.jp/item.php?id=86159> (koshikake-ari),
  <https://thejoinery.jp/item.php?id=47329> (hira-isuka),
  <https://thejoinery.jp/item.php?id=85252> (shihou-ari): exact dovetail drafts
  (about 1/8), 15 mm jaws, two 17 mm pegs at L/4, and 45° V-scarf geometry.
  The imported specimens are captures of these families; their closed poses
  were already corrected by `mate_faces.py`, and the contact pass confirms the
  corrections still leave every timber joined.

Bearing-only connections that deliberately have **no** mortise are documented
as such in their guidance: `floor-post-on-stone` (post bears on the dressed
stone), `rafter-at-ridge` and `rafter-at-hip` / `jack-rafter-at-hip` (square
plumb or side cuts), and `purlin-under-hip` / `hip-over-plate` (load paths
through bearing surfaces; the exact housing is drawing-specific). The
`fire-beam-tie` no longer belongs to that list: its ends now drop into 30 mm
`大入れ` housings in the two sill tops.

Used to author the seventeen joints with no source model (shapes, proportions, which
face each mortise opens on, where the key goes):

- `joints.jpg`, `joints-2.jpg` — reference sheets of `継ぎ手` and `仕口`
  (column-and-beam `納まり`), included at the repository root. The 追掛け
  detail is labelled `追掛け大栓継ぎ（持ち出し継ぎ）` and drawn as the prepared
  end of a `胴差` with its keys lifted out, so it shows the 持ち出し tenon but
  not the closed joint.
- thejoinery, *追掛け大栓継ぎ* —
  <https://sketchfab.com/3d-models/okkake-daisen-tsugi-5b161a4a18ae4054a820d32df2b20ca5>:
  the licensed model of the same family, used as the reference for the closed
  lap and the two keys.
- JAANUS, *Japanese Architecture and Art Net Users System* —
  <https://www.aisf.or.jp/~jaanus/>: terminology for the `大根` / `小根` tiers,
  the `腰` step and the housed through-tenon.
- 伝統的構法データベース, datasheet 17 下げ鎌（引張） —
  <http://www.denmoku-db.jp/publics/index/46/>: a 120 post with a 15–45 × 120
  `貫`, the kama bearing on the post's far face, and the 15 mm `引っ掛かり`
  that fixes the hook depth.
- Irie & Shimaya, *伝統的木造構法における下げ鎌および包み込み貫の耐力・剛性評価式に関する検討*,
  AIJ Technology Report 20(44), 2014, fig. 1 —
  <https://www.jstage.jst.go.jp/article/aijt/20/44/20_95/_pdf/-char/ja>
  (doi:10.3130/aijt.20.95): a through `貫` with a down-hook at the far end and
  the wedge above the tenon; the 包み込み貫 test series J5-1–J5-7, a 120 post,
  15–60 mm nuki and 90 mm insertion.
- 伝統的構法データベース, datasheet 18 包み込み貫（曲げ） —
  <http://www.denmoku-db.jp/publics/index/46/>: the test drawings and
  load–deformation curves behind the AIJ paper, including the 15 mm rebate on
  the nuki's underside and the 30 mm post wall beyond its end.
- 宮本 慎宏, *伝統的木造建築物の柱貫接合部の構造性能評価に関する研究*,
  平成29年度 建築分野 No.7, 香川大学, fig. 2 — the T-type specimen with a
  105 mm post and nuki, 90 mm insertion, and the (a) 包み込み貫 / (b) 下げ鎌
  elevations used to fix the rebate, shelf and wedge.
- 建築用語.net, *蟻継ぎ* — <https://architectjiten.net/ag14/ag14_061.html>: a
  splice with a dovetail (蟻) cut on one member's end and a matching socket in
  the other; the flared tenon resists being pulled straight apart.
- 建築用語集, *四方差し* — <http://kenchikuyogo.com/?page_id=5746>: members
  tenoned into one post from all four faces; the tenons pass through the post
  to fix the member opposite, and the red member in the figure is the
  `車知栓`.
- 建築用語集, *傾き大入れ* — <http://kenchikuyogo.com/?page_id=3357>: a
  post-and-beam joint that carries the whole load into the post by cutting the
  beam at a slant and hooking its lower part onto the post, rather than relying
  on the tenon's cross-section alone.
- 建築用語.net, *傾ぎ大入れ* — <https://architectjiten.net/ag14/ag14_270.html>:
  a wooden `仕口` between post and 胴差, 窓台 or 敷桁 in which the seam between
  the two members is slanted rather than square.
- 建築用語集, *追(大)入れ* — <http://kenchikuyogo.com/?page_id=1619>: the housed
  joint the slanted form is cut from; the member is sprung into a shallow
  recess and wedged so the joint does not open.
- 福田 敏幸, *柱と梁の組み方で「四方差し」とは* —
  <https://ameblo.jp/kominka-kenhokunagasaki/entry-12313908760.html>: opposite
  members joined with long tenons one above the other and tied with
  `込み栓`; used under floors, in sill beams and in roof framing on a
  through-post.
- thejoinery, <https://thejoinery.jp/> — the source collection the imported
  models come from, and the visual reference for the authored ones.

## Licensing

The CC BY 4.0 assets may be reused with attribution; the `asset.copyright`
string and the `source` block provide it. `yatoi-hozo-shachi-sen-shiguchi` is
**CC BY-SA 4.0**: its baked GLB and its pieces are a derivative and are
distributed under the same license
([CC BY-SA 4.0](http://creativecommons.org/licenses/by-sa/4.0/)); credit
thejoinery and keep the changes above with any redistribution.
