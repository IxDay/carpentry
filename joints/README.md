# joints

Twenty-one Japanese timber joints (継ぎ手 / 仕口) in a pastel paper-sunrise
style. Seventeen are from the [thejoinery](https://sketchfab.com/thejoinery)
collection on Sketchfab, rebuilt and baked; four column-and-beam (`shikuchi`)
joints with no licensed source model are authored in this repository from the
reference sheet 柱（軸組）の納まり, with
[`tools/author_joint.py`](../tools/author_joint.py). There is **no garden or
ground plane**: the timbers float against the paper backdrop, which keeps the
focus on the cut geometry.

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
| [`hako-sen-tsugi`](https://sketchfab.com/3d-models/hako-sen-tsugi-881723f8c6794db5a9dbe9dc2fb3a69b) | 箱栓継ぎ | CC BY 4.0 | 4 |
| [`hira-isuka-tsugi`](https://sketchfab.com/3d-models/hira-isuka-tsugi-bd6b1bea223144868199fee6a28baf5c) | 平居木継ぎ | CC BY 4.0 | 2 |
| [`kakeawase-komisen-tsugi`](https://sketchfab.com/3d-models/kakeawase-komisen-tsugi-ac403983452d4524a7e23350c2ace36c) | 掛け合わせ込み栓継ぎ | CC BY 4.0 | 3 |
| [`kakushi-kanawa-tsugi`](https://sketchfab.com/3d-models/kakushi-kanawa-tsugi-d3dbb63c57554cf1852724d510cb63e2) | 隠し金輪継ぎ | CC BY 4.0 | 4 |
| [`kanawa-tsugi`](https://sketchfab.com/3d-models/kanawa-tsugi-713b9b3a98344094a008535738348791) | 金輪継ぎ | CC BY 4.0 | 3 |
| [`komisen-inro-tsugi`](https://sketchfab.com/3d-models/komisen-inro-tsugi-ee2d1506029e41068772c19fae51df96) | 込み栓入れ枘継ぎ | CC BY 4.0 | 3 |
| [`koshikake-ari-tsugi`](https://sketchfab.com/3d-models/koshikake-ari-tsugi-6a06924b8c5243c0beee65e5535d1820) | 腰掛け蟻継ぎ | CC BY 4.0 | 2 |
| [`meji-tsukikake-awase-tsugi`](https://sketchfab.com/3d-models/meji-tsukikake-awase-tsugi-64cc903d315b40d6a5f8f6086befa1fd) | 目地突掛け合わせ継ぎ | CC BY 4.0 | 2 |
| [`miyajima-tsugi`](https://sketchfab.com/3d-models/miyajima-tsugi-40104d0e736c4bb0b2a75e2c91db0730) | 宮島継ぎ | CC BY 4.0 | 3 |
| [`niho-sashi-shikuchi`](../tools/author_joint.py) | 二方差し仕口 | CC BY 4.0 (authored) | 3 |
| [`nimai-kama-tsugi`](https://sketchfab.com/3d-models/nimai-kama-tsugi-5aa7e4181c674070a9d0c291c0f129f9) | 二枚鎌継ぎ | CC BY 4.0 | 5 |
| [`okkake-daisen-tsugi`](https://sketchfab.com/3d-models/okkake-daisen-tsugi-5b161a4a18ae4054a820d32df2b20ca5) | 追掛け大栓継ぎ | CC BY 4.0 | 4 |
| [`osaka-jo-otemon-hikae-bashira-tsugi`](https://sketchfab.com/3d-models/osaka-jo-otemon-hikae-bashira-tsugi-a1cf8bd826504ef2acc1b34510a06d27) | 大阪城大手門控え柱継ぎ | CC BY 4.0 | 2 |
| [`otoshi-ari-hozo-shikuchi`](https://sketchfab.com/3d-models/otoshi-ari-hozo-shikuchi-269f0b5a914e437ba10c0aed445711df) | 落し蟻枘仕口 | CC BY 4.0 | 3 |
| [`sampo-sashi-shikuchi`](../tools/author_joint.py) | 三方差し仕口 | CC BY 4.0 (authored) | 3 |
| [`shihou-ari-tsugi`](https://sketchfab.com/3d-models/shihou-ari-tsugi-c1d6168a3b4e49a983c3ba815e0b4437) | 四方蟻継ぎ | CC BY 4.0 | 2 |
| [`suitsuki-sashi-shikuchi`](https://sketchfab.com/3d-models/suitsuki-sashi-shikuchi-2edef5371cb34374b9b6046e435603b6) | 吸付差し仕口 | CC BY 4.0 | 2 |
| [`yatoi-hozo-shachi-sen-shiguchi`](https://sketchfab.com/3d-models/yatoi-hozo-shachi-sen-shiguchi-5f3cc05626b641f19bd42d30a976db3d) | 雇い枘車知栓仕口 | **CC BY-SA 4.0** | 5 |
| [`yatoi-hozo-shikuchi`](../tools/author_joint.py) | 雇い枘仕口 | CC BY 4.0 (authored) | 3 |
| [`yose-ari-hozo-shikuchi`](https://sketchfab.com/3d-models/yose-ari-hozo-shikuchi-3e2f52c247a84a7f9a4caaaefefa4744) | 寄せ蟻枘仕口 | CC BY 4.0 | 2 |

The seventeen Sketchfab models are by **thejoinery**
(<https://sketchfab.com/thejoinery>). Every `sources/<id>.json` repeats the
title, author, canonical URL, license and the change list in its `source`
object, and the same credit is embedded in each GLB's `asset.copyright`. The
four authored joints carry the project as author and credit the reference sheet
they were drawn from.

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

The four authored joints (`daimochi-tsugi`, `yatoi-hozo-shikuchi`,
`sampo-sashi-shikuchi`, `niho-sashi-shikuchi`) are different in kind: they are
modelled to the reference sheet already **closed**, then exploded for the
animation, rather than captured exploded and closed in place. `author_joint.py`
builds each timber from axis-aligned boxes minus the mortises and housings, welds
the boundary, and records the reverse of the exploded offsets as `assemble`. They
share the same timbers, scale, normals, bake and animation as the imported set,
and are checked the same way (closed pose watertight and manifold, zero volumetric
overlap between timbers, every mating face in contact). `daimochi-tsugi` is a
splice; the other three are `shikuchi` (loose-tenon, three-face and two-face
`差し`) and were added because the reference sheet is almost entirely
column-and-beam work while the imported collection is almost entirely splices.

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
is driven in last. The sloping joint line is why the slide is both z and y.
That is
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

The four authored joints have no capture step; regenerate their sources from the
joint definitions, then bake and preview the same way:

```sh
python3 author_joint.py                 # rewrites all four sources
python3 author_joint.py daimochi-tsugi  # or one
```

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

Used to author the four joints with no source model (shapes, proportions, which
face each mortise opens on, where the key goes):

- `joints.jpg`, `joints-2.jpg` — reference sheets of `継ぎ手` and `仕口`
  (column-and-beam `納まり`), included at the repository root.
- thejoinery, <https://thejoinery.jp/> — the source collection the imported
  models come from, and the visual reference for the authored ones.

## Licensing

The CC BY 4.0 assets may be reused with attribution; the `asset.copyright`
string and the `source` block provide it. `yatoi-hozo-shachi-sen-shiguchi` is
**CC BY-SA 4.0**: its baked GLB and its pieces are a derivative and are
distributed under the same license
([CC BY-SA 4.0](http://creativecommons.org/licenses/by-sa/4.0/)); credit
thejoinery and keep the changes above with any redistribution.
