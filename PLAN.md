# Plan: growing the joint collection

Inventory of the joints, coverage against the reference sheet
[`joints-2.jpg`](joints-2.jpg) (柱（軸組）の納まり), source availability, and the
order in which to add the missing families.

## Inventory

### Splices (`tsugi`, joined end to end along a member)

| Asset | Japanese | Pieces |
|---|---|---|
| `kanawa-tsugi` | 金輪継ぎ | 3 |
| `kakushi-kanawa-tsugi` | 隠し金輪継ぎ | 4 |
| `okkake-daisen-tsugi` | 追掛け大栓継ぎ | 4 |
| `hira-isuka-tsugi` | 平居木継ぎ | 2 |
| `koshikake-ari-tsugi` | 腰掛け蟻継ぎ | 2 |
| `shihou-ari-tsugi` | 四方蟻継ぎ | 2 |
| `nimai-kama-tsugi` | 二枚鎌継ぎ | 5 |
| `hako-sen-tsugi` | 箱栓継ぎ | 4 |
| `komisen-inro-tsugi` | 込み栓入れ枘継ぎ | 3 |
| `kakeawase-komisen-tsugi` | 掛け合わせ込み栓継ぎ | 3 |
| `meji-tsukikake-awase-tsugi` | 目地突掛け合わせ継ぎ | 2 |
| `miyajima-tsugi` | 宮島継ぎ | 3 |
| `osaka-jo-otemon-hikae-bashira-tsugi` | 大阪城大手門控え柱継ぎ | 2 |

### Column/beam joints (`shikuchi`)

| Asset | Japanese | Pieces |
|---|---|---|
| `yatoi-hozo-shachi-sen-shiguchi` | 雇い枘車知栓仕口 | 5 |
| `yose-ari-hozo-shikuchi` | 寄せ蟻枘仕口 | 2 |
| `otoshi-ari-hozo-shikuchi` | 落し蟻枘仕口 | 3 |

The splice set is strong. The `shikuchi` set is thin, while the reference sheet
is almost entirely column-and-beam framing joints — the coverage gap is
systematic.

## Coverage against the reference sheet

| Reference family | Status | Nearest asset we own |
|---|---|---|
| 追掛け大栓継ぎ | have | `okkake-daisen-tsugi` |
| 追掛け大栓継ぎ（持ち出し継ぎ） | missing | variant of the above |
| 台持ち継ぎ（真継ぎ） | **have** | `daimochi-tsugi` |
| 雇いホゾ | **have** | `yatoi-hozo-shikuchi` (plain form) + `yatoi-hozo-shachi-sen-shiguchi` |
| 三方差し（T字） | **have** | `sampo-sashi-shikuchi` |
| 二方差し（L字） | **have** | `niho-sashi-shikuchi` |
| 下小根ホゾ（襷掛付） | **have** | `shitakone-hozo-tasuki-gake` |
| 下小根ホゾ・割り楔打ち | **have** | `shitakone-hozo-wari-kusabi` |
| 下小根ホゾ・鼻栓打ち | **have** | `shitakone-hozo-hana-sen` |
| 上小根ホゾ・割り楔打ち | **have** | `uwakone-hozo-wari-kusabi` |
| 上小根ホゾ・打ち抜き込み栓打ち | **have** | `uwakone-hozo-uchi-nuki-komisen` |
| 長ホゾ差し・込み栓打ち | **have** | `naga-hozo-sashi-komisen-uchi` |
| 片鎌ホゾ差し | **have** | `kata-kama-hozo-sashi` |
| 四方差し | **missing** | `shihou-ari-tsugi` is a splice, different joint |
| 落し鎧 | **missing** | `otoshi-ari-hozo-shikuchi` is 落し蟻, not 鎧 |
| 下げ鎌（大入れ） | **missing** | — |
| 傾ぎ大入れ | **missing** | — |

Counting the five `小根ホゾ` variants separately, the sheet lists fourteen
`shikuchi` entries. The first batch took coverage from one of them (雇いホゾ,
and only in its 車知栓 form) to three: 雇いホゾ (now both forms), 三方差し and
二方差し. It also added the one splice family we were missing. The second batch
covers the whole `小根ホゾ` cluster, taking `shikuchi` coverage to eight of the
fourteen; the third adds the long through tenon and the fourth a one-sided kama,
so ten of the fourteen. Four families remain: `四方差し`, `落し鎧`, `下げ鎌`
and `傾ぎ大入れ`.

## Source availability

- **thejoinery** on Sketchfab: 17 models, all now imported. The last one,
  `Suitsuki-sashi-shikuchi` (吸付差し仕口), uid
  `2edef5371cb34374b9b6046e435603b6`, is **CC BY 4.0** — same author, same
  licence, capture pipeline already proven. Nothing further is available there.
- The other Sketchfab hits cannot be used: `Koshikake kama Tsugi` has no
  licence, `Japanese Wood Joinery` / `…2` are Standard, `221209_Hozo` is
  CC BY-NC-SA.
- The missing families therefore have to be authored in-house from the reference
  sheet (or a model commissioned / permission obtained). Authored joints carry a
  project licence and no third-party attribution.

## Order

1. **`Suitsuki-sashi-shikuchi`** — free and licensed, adds a new `shikuchi`
   family, exercises the angled-seat `approach` path.
2. **台持ち継ぎ（真継ぎ）** — the one splice family on the sheet we lack; the
   plain control next to kanawa and okkake.
3. **雇いホゾ, plain + 三方差し（T字）+ 二方差し（L字）** — one loose-tenon
   family, three configurations; reuses the loose-tenon handling from
   `yatoi-hozo-shachi-sen-shiguchi`.
4. **下小根ホゾ / 上小根ホゾ family** — five labelled variants (差し, 割り楔,
   鼻栓, 打ち抜き込み栓); the densest uncovered cluster. **Done** (second batch).
5. **長ホゾ差し・込み栓打ち**, then **片鎌ホゾ差し** — high-recognition joints,
   cheap to author.
6. **落し鎧, 下げ鎌（大入れ）, 傾ぎ大入れ, 四方差し** — housed/dovetail seats,
   the most `approach` work.

## First batch — done

| Asset | Japanese | Source | Pieces |
|---|---|---|---|
| `suitsuki-sashi-shikuchi` | 吸付差し仕口 | captured, thejoinery, CC BY 4.0 | 2 |
| `daimochi-tsugi` | 台持ち継ぎ | authored, CC BY 4.0 | 3 |
| `yatoi-hozo-shikuchi` | 雇い枘仕口 | authored, CC BY 4.0 | 3 |
| `sampo-sashi-shikuchi` | 三方差し仕口 | authored, CC BY 4.0 | 3 |
| `niho-sashi-shikuchi` | 二方差し仕口 | authored, CC BY 4.0 | 3 |

Five new assets, taking the collection from 16 to **21**. `suitsuki` was captured with
`tools/sketchfab_capture.mjs` and needed its `assemble` offset corrected from
-155 mm to -200 mm: the generated guess left the beam 45 mm above the post's
shelf, so the tenon never entered its pocket.

The other four have no licensed source model and are authored with
[`tools/author_joint.py`](tools/author_joint.py): exact axis-aligned box CSG on a
coordinate-plane grid, boundary quads merged into rectangles, T-junctions welded.
Their sources are generated in the closed pose and exploded for the animation.
All five were checked for a watertight manifold boundary with consistent winding,
coincident mating faces and zero volumetric overlap between timbers, then baked,
previewed, and `tools/validate.py ../joints` passes.

## Second batch — done

| Asset | Japanese | Source | Pieces |
|---|---|---|---|
| `shitakone-hozo-tasuki-gake` | 下小根ホゾ（襷掛付） | authored, CC BY 4.0 | 2 |
| `shitakone-hozo-wari-kusabi` | 下小根ホゾ割り楔打ち | authored, CC BY 4.0 | 4 |
| `shitakone-hozo-hana-sen` | 下小根ホゾ鼻栓打ち | authored, CC BY 4.0 | 3 |
| `uwakone-hozo-wari-kusabi` | 上小根ホゾ割り楔打ち | authored, CC BY 4.0 | 4 |
| `uwakone-hozo-uchi-nuki-komisen` | 上小根ホゾ打ち抜き込み栓打ち | authored, CC BY 4.0 | 3 |

Five more assets, taking the collection from 21 to **26**. The family needed two
additions to `author_joint.py`: a `loft()` primitive for the tapered wedges and
pegs (two parallel sections joined by planar quads), and `mirror_x()`, because
the site camera looks from +x/+z and the `小根ホゾ` tenon has to face it.

The closed pose is verified by the new
[`tools/check_sources.py`](tools/check_sources.py), which checks the source plus
`assemble` (not just the baked GLBs): every edge used twice in opposite
directions, every face wound with its normal, and no volumetric overlap between
timbers. It probes vertices, edge midpoints and triangle centroids, and also
tests coplanar face pairs, so a 10 mm intrusion is caught in any of x, y or z.
All 26 sources pass.

## Third batch — done

| Asset | Japanese | Source | Pieces |
|---|---|---|---|
| `naga-hozo-sashi-komisen-uchi` | 長ホゾ差し込み栓打ち | authored, CC BY 4.0 | 3 |

Taking the collection from 26 to **27**, and `shikuchi` coverage to nine of the
fourteen entries. Pure box work: the untiered tenon runs clean through the post
and stands 45 mm proud, and a tapered `込み栓` pierces post and tenon across the
tenon's width. The closed pose passes `check_sources.py`; bake, preview and
`validate.py` are run with the same flags as the rest of the set.

## Fourth batch — done

| Asset | Japanese | Source | Pieces |
|---|---|---|---|
| `kata-kama-hozo-sashi` | 片鎌ホゾ差し | authored, CC BY 4.0 | 2 |

Taking the collection from 27 to **28** and `shikuchi` coverage to ten of the
fourteen entries. The post's tenon carries a hook on one lower edge only; the
sill's mortise is a slot open at the sill's end, so the post is slid in along
the sill, the hook running in under the sill's lip. The hook is kept square: the
tightening slope of the reference's 鎌 is omitted because the box CSG cannot cut
or add a sloped face, and a staircase would show in the baked edge strips.

## Next

Most of the remaining queue is still axis-aligned box work, but the dovetail
flanks and the sloped seats need `author_joint.py` extended beyond boxes and
lofts (sloped quads) or hand-authored face lists:

1. **落し鎧, 下げ鎌（大入れ）, 傾ぎ大入れ, 四方差し** — housed/dovetail seats,
   the most `approach` work.

For each: author or capture the geometry, verify the closed pose, add `approach`
where a seat is sloped or a dovetail has to drop before sliding, then bake,
preview, validate and rebuild `docs/`.
