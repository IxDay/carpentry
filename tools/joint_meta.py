#!/usr/bin/env python3
"""Structured catalogue metadata for every joint specimen.

Each entry is keyed by the source id and holds four fields:

* ``beams``     - number of timber pieces meeting at the joint: the receiving
                  post plus each beam/nuki/girder/joist/rafter/brace.  Pegs,
                  wedges, keys, dowels and a separate loose tenon are *not*
                  counted.  For a same-axis splice both timbers are counted (2).
* ``usage``     - the structural situation the joint is chosen for.
* ``strengths`` - what the joint does well (bearing, tension, assembly, looks).
* ``weaknesses``- what to watch for (lost section, loosening, difficult cut).

The prose is compiled from the naming guide supplied with this project, the
reference sheets (joints.jpg / joints-2.jpg), the repository's own joints/README
and house/README, and the web sources listed in SOURCE_NOTES below.  Where a
joint is an extrapolation from the naming convention rather than a documented
named joint, the usage text says so.

``apply(level)`` stamps the fields onto a decoded source record; ``build_site``
also falls back to this table for sources that predate the fields.
"""
import copy
import json


SOURCE_NOTES = {
    "jaanus_kanawa": (
        "JAANUS, kanawa tsugi 金輪継 — https://projects.mcah.columbia.edu/jaanus/node/3413 "
        "(oblique housed rabbeted T-shaped half-blind tenoned scarf; cannot be slipped "
        "together from the side; komisen driven through the central opening, sometimes "
        "two shachi keys instead; used in dodai, daiwa, shikigeta, dashigeta)"),
    "kenchikuyogo_shihou": (
        "建築用語集, 四方差し — http://kenchikuyogo.com/?page_id=5746 "
        "(tenons driven in from four faces pass through the post, so the post's lost "
        "section is large; neat in appearance but not necessarily strong; metal "
        "reinforcement may be better; the red member in the figure is a 車知栓)"),
    "shimoyama_sill": (
        "下山眞司, 土台の継手、土台と大引の納め — "
        "https://ameblo.jp/archi1217ss-7/entry-12926333294.html "
        "(koshikake-ari has no 竿 so the two timbers are hard to keep straight; plain ari "
        "is weak; full-depth ari can leave the timbers uneven; 布/金輪/追掛け大栓 are "
        "きわめて堅固; wooden pegs and wedges rarely loosen thanks to elasticity and "
        "friction, but nuki/post wedges often loosen under vibration)"),
    "shimoyama_beam": (
        "下山眞司, 梁と小梁・根太 — https://ameblo.jp/archi1217ss-7/entry-12926333763.html "
        "(ooire-ari is stronger in bending than plain ooire; watari-ago fixes a joist "
        "over a beam without damaging the beam; a joist in a plain ooire behaves as a "
        "simple beam and can loosen; koshikake-kama alone cannot tie a frame together; "
        "shachi/komisen tenons and okkake-daisen are the recommended robust choices)"),
    "flat35": (
        "Flat35 2025 specification sample — https://www.inoueshoin.co.jp/e-flat35/sample/sample.html "
        "(120 mm sill, 90 mm sleepers, 30x90 mm braces; 渡りあご where a joist is 90 mm+; "
        "火打ちばり uses 傾ぎ大入れ)"),
}


def m(beams, usage, strengths, weaknesses):
    return {"beams": beams, "usage": usage,
            "strengths": list(strengths), "weaknesses": list(weaknesses)}


META = {
    # ---------------------------------------------------------------- splices
    "daimochi-tsugi": m(2,
        "Sill, purlin (keta) or beam lengthened directly over a post, where the "
        "load arrives in bearing and shear and the splice needs no tension capacity.",
        ["A 50 mm shelf carries the upper timber in bearing on the mortise floor.",
         "The housed tenon keeps the two axes aligned without a long scarf."],
        ["Very little pull-out or bending resistance: rely on the support below.",
         "The deep housing removes material from the mortised half."]),
    "doutsuki-ari-tsugi": m(2,
        "Simple dovetail splice cut in plan for a sill or beam that must not pull "
        "apart along its length, where a full-depth socket can be cut.",
        ["Flared tenon resists axial withdrawal; the shoulders carry compression.",
         "The socket is open top and bottom, so it closes with a straight drop."],
        ["The full-depth socket weakens the receiving member at the seam.",
         "The narrow dovetail neck can shear if the joint is driven hard."]),
    "hako-sen-tsugi": m(2,
        "Low-stakes, short splice in a sill or light beam where only mild "
        "pull-resistance is needed and cutting speed matters.",
        ["Box shoulders are quick to cut and give positive alignment.",
         "The driven key adds mild resistance to withdrawal."],
        ["Little bending or tension capacity; not for a structural span.",
         "A loose key or shrink-fit can let the halves open."]),
    "hira-isuka-tsugi": m(2,
        "Beveled (scissor) scarf placed directly over a post or support, used "
        "only for alignment and compression.",
        ["Fastest of the scarves: two matching bevels and no key.",
         "Bearing on the support keeps the bevel faces closed."],
        ["No meaningful tension resistance: the bevels can slide apart.",
         "Only valid while the splice stays directly over its support."]),
    "kakeawase-komisen-tsugi": m(2,
        "General sill or beam splice needing some shear lock plus some "
        "pull-resistance, short of a full kanawa-class scarf.",
        ["The hooked shoulder resists shear across the joint.",
         "The driven komisen resists lengthwise withdrawal."],
        ["Moderate capacity only: the hook can split a narrow timber.",
         "Pin hole and hook reduce the effective section at the seam."]),
    "kakushi-kanawa-tsugi": m(2,
        "The kanawa structural case - seismic sill or important beam - on a "
        "visible face where the wedge pattern must not show.",
        ["Keeps the kanawa-family tension and bending resistance.",
         "Locking detail is concealed, so the show face stays clean."],
        ["Concealment makes the lock hard to inspect or re-tighten.",
         "At least as complex to cut as the open kanawa."]),
    "kanawa-tsugi": m(2,
        "Benchmark strong scarf for seismic sills, foundation footings, wall "
        "plates and important beams where real tension and bending resistance "
        "are required (JAANUS).",
        ["Oblique housed rabbeted T-shaped tenon plus draw pin resists both "
         "tension and bending; two shachi keys may be used instead of the pin.",
         "The pin is driven through the central opening to draw the halves tight."],
        ["JAANUS: because tenon and mortise are blind it cannot be slipped "
         "together from the side - it must be inserted lengthwise.",
         "Complex cut; the key gap and the mortised section must be accurate."]),
    "komisen-inro-tsugi": m(2,
        "General-purpose moderate-load splice in a beam or purlin, where no "
        "special assembly direction is available.",
        ["Stepped scarf and tenon give moderate pull resistance.",
         "The komisen is accessible for replacement."],
        ["Not suitable for high bending or seismic tension.",
         "The pin hole weakens the tenon where it crosses."]),
    "koshikake-ari-tsugi": m(2,
        "The classic sill splice: dovetail resists lengthwise pull, the seat "
        "takes vertical load, and the joint drops straight down as sills are "
        "laid in sequence.",
        ["Dovetail resists pull; the koshikake seat takes vertical load.",
         "Drops straight down, so sills can be laid one after another."],
        ["下山: without a 竿 the two timbers are hard to keep in a straight "
         "line; a 目違い (mechigai) is added when that matters.",
         "Plain ari is a weak joint; an over-tight dovetail neck can break."]),
    "meji-tsukikake-awase-tsugi": m(2,
        "Exposed splice on a reveal or joint line where a clean sight-line "
        "matters as much as the mechanics.",
        ["Hooked shoulder gives some shear lock across the butt.",
         "Keeps a clean continuous groove on the show face."],
        ["Appearance-led: low structural capacity compared with kanawa.",
         "The reveal line can open if the timber shrinks."]),
    "miyajima-tsugi": m(2,
        "Named regional scarf variant used like the kanawa family, often by "
        "school or local convention rather than a different structural need.",
        ["Good tension and bending resistance in its tradition.",
         "Interlocking steps give a large bearing area."],
        ["Geometry is school-specific, so drawings do not generalise.",
         "Complex to lay out and cut by hand."]),
    "nimai-kama-tsugi": m(2,
        "Heavier beam or more critical span than a single kama can serve.",
        ["Two goosenecks share the tensile load.",
         "Better bending capacity than the single-kama family."],
        ["Needs a deeper section to fit two hooks.",
         "One blade must lift clear of the other during assembly."]),
    "okkake-daisen-tsugi": m(2,
        "Strong splice that assembles by sliding horizontally - ridge beams "
        "already seated on posts, or anywhere a beam cannot be lifted in.",
        ["下山 calls 追掛け大栓継ぎ きわめて堅固 (extremely firm).",
         "Large driven keys give high capacity; slide-in needs no lifting."],
        ["Needs a long lap (8 sun to 1 shaku) and accurate key slots.",
         "Requires lateral clearance to slide the lap together."]),
    "okkake-daisen-tsugi-mochidashi": m(2,
        "The same high-capacity slide-in splice where the joint must project "
        "past its bearing point, for example continuing a beam out over an eave.",
        ["Keeps the okkake-daisen capacity while cantilevering past support.",
         "Noses seat in shallow rebates, so the proud ends are controlled."],
        ["Projecting noses need extra rebates and careful setting out.",
         "The closed form is an interpretation: the sheet shows only the "
         "prepared end, not the assembled joint."]),
    "osaka-jo-otemon-hikae-bashira-tsugi": m(2,
        "Showcase/high-status splice on oversized gate brace posts where "
        "maximum splice strength and a large section are available.",
        ["Two dovetail faces and two 'sword tip' shoulders with sloping "
         "shoulders that let the repair piece slide in; a pin or wedge locks it.",
         "Uses the full section of a very large timber."],
        ["Only meaningful at oversized section: wasteful at normal scale.",
         "Very complex; historically a status display as much as a need."]),
    "shihou-ari-tsugi": m(2,
        "Four-way dovetail interlock for a junction where all four directions "
        "need pull-out resistance, not just friction or a pin.",
        ["Dovetail geometry resists withdrawal on every face.",
         "No separate keys are needed to hold the four directions."],
        ["Four-way dovetails are intricate and the rims are fragile.",
         "Only two crossing timbers are modelled here: the four-way cut is in "
         "the interlocking faces, not four separate beams."]),

    # --------------------------------------------------- post / beam (shikuchi)
    "kata-kama-hozo-sashi": m(2,
        "Corner post foot with a one-sided hook, slid along the sill into a "
        "slot open at the sill's end; resists uplift in one direction.",
        ["The square back of the hook bears on the sill lip under uplift.",
         "Slides in along the sill, so no overhead access is needed."],
        ["Only one direction of pull-out is resisted.",
         "The hook needs a slot open at the sill end and sound grain."]),
    "katagi-ooire": m(2,
        "Sloped member - brace or hip rafter - seating into a post or beam at "
        "an angle rather than square.",
        ["The whole load bears on the sloped face and the beam cannot lift out.",
         "No key is needed; withdrawn straight along its own axis."],
        ["The sloped rebate removes a large part of the post's section.",
         "One-directional and hard to adjust once seated."]),
    "naga-hozo-sashi-komisen-uchi": m(2,
        "Baseline post-to-sill or post-to-beam connection, and the recommended "
        "upper-storey post foot where a through tenon can be used.",
        ["Through tenon and side komisen give a reliable, inspectable lock.",
         "下山 recommends a long tenon with a driven pin for post ends."],
        ["The mortise removes a large part of the post's core.",
         "The pin hole can split the tenon; the proud nose can catch."]),
    "niho-sashi-shikuchi": m(2,
        "Corner post receiving beams or nuki from two adjoining faces.",
        ["Simple two-face corner notch; the vertical komisen locks the tongue.",
         "Easy to set out at an ordinary building corner."],
        ["The corner notch reduces the post's effective section.",
         "The driven pin is visible on the show face."]),
    "otoshi-ari-hozo-shikuchi": m(2,
        "Joist-to-beam where the beam is fixed and the joist must be lowered "
        "into place but still resist pull-out.",
        ["Dovetail tenon resists withdrawal after the vertical drop.",
         "Closes with a straight lowering motion."],
        ["下山 warns that a dovetail neck can shear (蟻首がとぶ).",
         "Needs clearance above the beam to drop the joist in."]),
    "sage-kama-oire": m(2,
        "A secondary beam or nuki hung off a primary post: offered up raised, "
        "run home, then dropped so the hook bears behind the far face.",
        ["Hook bears on the post's far face and resists pull-out.",
         "A wedge over the nose seats it on the mortise floor."],
        ["下山: wedges in nuki/post joints often loosen under vibration "
         "(Kiyomizu-dera's underfloor is inspected for this).",
         "The through mortise and hook are awkward to cut."]),
    "sampo-sashi-shikuchi": m(2,
        "Post at a T-junction, for example an interior wall meeting an "
        "exterior wall line, with beams arriving from three directions.",
        ["Mortise opens on three faces, so the beam tenon drops straight in.",
         "A vertical komisen through beam, tenon and post locks the lot."],
        ["The open-top housing weakens the post head.",
         "Only moderate pull resistance; the pin must be driven down."]),
    "shihou-sashi-shikuchi": m(5,
        "Free-standing interior post or central column with beams or nuki "
        "converging from all four sides at one level.",
        ["Opposite tenons pass through the post and 30 mm into the beam "
         "opposite, so the four beams tie one another.",
         "Tenons are stacked at different levels instead of sharing one core."],
        ["建築用語集: tenons through the post leave a large lost section; "
         "neat in appearance but not necessarily strong - consider metal "
         "reinforcement.",
         "Two plate komisen must be dropped accurately and trimmed flush."]),
    "shitakone-hozo-hana-sen": m(2,
        "Lower-tier through tenon locked by a nose peg where the pin must be "
        "visible and accessible from the outside face.",
        ["Tapered nose peg behind the post blocks withdrawal.",
         "The full 大根 bears at the shoulder, the 小根 runs through."],
        ["The through mortise removes a large part of the post.",
         "The peg stands proud and can be knocked or withdrawn."]),
    "shitakone-hozo-tasuki-gake": m(2,
        "Blind lower-tier tenon at a corner where a vertical 襷 bridge in the "
        "post must also tie the arriving beams together.",
        ["Forked small root straddles the 襷 bridge, resisting sideways pull.",
         "Blind mortise leaves the post's far face clean."],
        ["The bridge and twin pockets are intricate to lay out.",
         "Less accessible for repair than a through joint."]),
    "shitakone-hozo-wari-kusabi": m(2,
        "Lower-tier through tenon where the show face must stay clean and the "
        "lock is driven from inside the mortise.",
        ["Two wedges spread the split tenon and lift it against the 腰.",
         "No visible pin on the show face."],
        ["The through mortise reduces the post's section.",
         "Wedges in post joints can loosen under vibration."]),
    "suitsuki-sashi-shikuchi": m(2,
        "Sliding dovetail cleat or batten fixed across a wide board or sill so "
        "it cannot warp away while the wood still moves seasonally.",
        ["Cross-grain dovetail holds the cleat down across the board.",
         "The sliding fit allows seasonal movement across the grain."],
        ["The long sliding fit must be cut accurately.",
         "An over-tight fit can split the board."]),
    "tsutsumikomi-nuki": m(2,
        "Nuki wrapped by the post: a shelf under its rebated end and a wall "
        "beyond it, used where a nuki must not pull out.",
        ["The end is caught between shelf and wall rather than merely housed.",
         "A wedge in the mouth gap holds it down."],
        ["Three-stage assembly (raise, slide, lower) needs access.",
         "A 90 mm insertion removes much of the post's section."]),
    "uwakone-hozo-uchi-nuki-komisen": m(2,
        "Upper-tier through tenon where the member above the post needs the "
        "fuller bearing shoulder and the pin passes through both cheeks.",
        ["Square komisen through post and big root is easy to inspect.",
         "The 腰 sits low so the upper shoulder carries bearing."],
        ["The through mortise and pin hole weaken the post.",
         "Cut flush on both faces, so re-pinning needs re-cutting."]),
    "uwakone-hozo-wari-kusabi": m(2,
        "Upper-tier through tenon with a concealed split-wedge lock.",
        ["Two wedges spread the nose and lock the tenon at the 腰.",
         "No visible pin on the show face."],
        ["The through mortise reduces the post's section.",
         "Wedge lock is sensitive to vibration and shrink/swell."]),
    "yatoi-hozo-shachi-sen-shiguchi": m(2,
        "Repair or retrofit where both receiving timbers are already fixed "
        "and the connection is structurally critical.",
        ["Separate tenon plus paired wedge keys gives a strong, adjustable lock.",
         "Neither existing member has to supply the tenon."],
        ["Loose tenon and two keys need very accurate matching mortises.",
         "Keys can loosen; access to both faces is needed."]),
    "yatoi-hozo-shikuchi": m(2,
        "Light-duty connection where both receiving members are already fixed "
        "in place and neither can supply a tenon.",
        ["A separate loose tenon seats in the post and the beam slides over it.",
         "The tenon can be replaced without disturbing either timber."],
        ["Not cut from either member, so capacity is lower than an integral tenon.",
         "Blind mortises must line up exactly."]),
    "yose-ari-hozo-shikuchi": m(2,
        "Mid-span joist connection assembled by sliding horizontally, where "
        "the dovetail draws the joint snug as it is driven.",
        ["The sloping dovetail pulls the members tight on entry.",
         "Good where a drop-in joint is not possible."],
        ["The dovetail neck can shear if overdriven (蟻首がとぶ).",
         "Needs clear access along the slide direction."]),

    # ------------------------------------------------------------ house details
    "brace-into-post": m(1,
        "筋違 brace let into the face of a post or sill to triangulate a bay.",
        ["The housing carries both compression and tension along the brace.",
         "Thickness of the housing sets the brace flush with the post face."],
        ["The housing removes post section at an already busy corner.",
         "Works in one diagonal only unless a paired brace is fitted."]),
    "fire-beam-tie": m(1,
        "火打梁 diagonal corner tie housed into a sill or girder to brace the "
        "floor plane.",
        ["Triangulates the corner; the 傾ぎ大入れ housing stops it lifting out.",
         "Flat35 and 中央工学校 specify 傾ぎ大入れ rather than a face bearing."],
        ["Only braces one diagonal of the bay.",
         "The sloped housing removes material from the sill top."]),
    "floor-post-into-sleeper": m(1,
        "床束 floor post carried by a 大引 sleeper on the ground floor.",
        ["The tenon locates the post on the sleeper and resists sliding.",
         "The post can be trimmed to height from above."],
        ["No uplift resistance unless a pin is added.",
         "Relies on the sleeper's bending capacity between floor stones."]),
    "floor-post-on-stone": m(1,
        "Floor post bearing on a dressed stone or 礎石, isolated from the soil.",
        ["Stone keeps the timber off damp ground and spreads the load.",
         "Wedges can shim the post to level the floor."],
        ["Bearing only: no positive lateral fix or uplift resistance.",
         "Shim wedges can loosen and need periodic checking."]),
    "hip-into-ridge": m(1,
        "Hip rafter (隅木) butting into the end of the ridge (棟木), with the "
        "ridge notched over the king post.",
        ["Square plumb cut gives a clean bearing transfer into the ridge.",
         "The ridge end is kept short so four hips meet it symmetrically."],
        ["Bearing-only cut: no mechanical lock against separation.",
         "The notch over the king post removes ridge section."]),
    "hip-over-plate": m(1,
        "Hip rafter crossing the wall plate (軒桁) at the eave.",
        ["Birdsmouth-type seat bears on the plate and sets the eave line.",
         "The side cut of the jack rafters registers against the hip."],
        ["The seat removes depth from the hip at a highly loaded point.",
         "The exact housing is drawing-specific."]),
    "jack-rafter-at-hip": m(1,
        "Short jack rafter (短垂木) stopping against the side face of a hip.",
        ["A square cut to the hip's side face gives a clean, close fit.",
         "Keeps the rafter spacing regular across the hip."],
        ["Bearing-only: no tenon to hold the jack against the hip.",
         "Cut angle must follow the hip's slope, not the common rafter's."]),
    "jack-rafter-over-plate": m(1,
        "Short jack rafter bearing on the wall plate at the eave.",
        ["A birdsmouth seats the rafter and fixes its overhang.",
         "Repeats the common rafter detail at the hip end."],
        ["The seat reduces the rafter depth at the bearing.",
         "Relies on fixing against uplift."]),
    "joist-half-lap": m(1,
        "根太 joist halved and lapped to another joist or to a girder at the "
        "same top level.",
        ["Half-lap keeps the top faces flush for the floor finish.",
         "Simple to cut and quick to lay."],
        ["Removes half the depth of each member at the lap.",
         "No positive lock against pulling apart."]),
    "joist-into-sill": m(1,
        "Joist end housed 30 mm into the sill (土台) for a flush top.",
        ["The housing locates the joist and keeps the floor flat.",
         "Small cut for a light, short-span member."],
        ["下山: a joist in a plain ooire acts as a simple beam and can loosen "
         "under load; use a dovetail (蟻掛け) for larger joists.",
         "Housing depth is limited by the sill section."]),
    "purlin-under-hip": m(1,
        "母屋 purlin meeting a hip rafter (隅木) under the roof slope.",
        ["The hip receives the purlin end, continuing the load path to the plate.",
         "Square-cut end keeps the joint readable in the open frame."],
        ["Bearing surface only; the exact housing is drawing-specific.",
         "The hip is the larger member and its section governs the cut."]),
    "rafter-at-hip": m(1,
        "Common rafter (垂木) meeting the side of a hip rafter.",
        ["Square plumb or side cut closes neatly against the hip.",
         "Regular rafter layout can run right up to the hip."],
        ["Bearing-only, with no mortise or key.",
         "Needs an accurate cut to the hip's face."]),
    "rafter-at-ridge": m(1,
        "Common rafter meeting the ridge (棟木) at the roof apex.",
        ["Square plumb cut seats the rafter against the ridge.",
         "Symmetric about the ridge line."],
        ["Bearing-only: no lock against sliding down the slope.",
         "Relies on the birdsmouth lower down for location."]),
    "rafter-over-plate": m(1,
        "Common rafter bearing on the wall plate (軒桁) at the eave.",
        ["Birdsmouth seat carries the rafter load onto the plate.",
         "The seat sets both the overhang and the roof plane."],
        ["The seat cuts into the rafter's depth at the bearing.",
         "Uplift needs separate fixing."]),
    "rafter-over-purlin": m(1,
        "Common rafter bearing on an intermediate purlin (母屋).",
        ["Birdsmouth seat spreads the roof load into the purlin.",
         "Repeatable cut for the whole roof field."],
        ["The seat reduces the rafter depth.",
         "Bearing-only; no resistance to uplift or creep."]),
    "sill-corner": m(1,
        "土台 sill corner, half-lapped and alternating by wall.",
        ["Half-lap keeps the two sills at the same level at the corner.",
         "Alternating which sill is upper avoids a weak pattern at every corner."],
        ["Half the depth is removed from each sill at the lap.",
         "Needs a pin or bolt to stop the lap opening."]),
    "sleeper-into-sill": m(1,
        "大引 sleeper housed into the sill (土台), often with 腰掛け蟻掛け.",
        ["The housed dovetail stops the sleeper pulling out and adds bending "
         "resistance over a plain housing (下山).",
         "Keeps sleeper and sill tops flush."],
        ["A plain ooire can come apart on shrinkage (下山).",
         "The small step at a 120 mm sill / 90 mm sleeper limits the cut."]),
    "upper-joist-half-lap": m(1,
        "二階根太 upper-floor joist halved and lapped at a girder.",
        ["Flush top for the upper floor finish.",
         "Fast, repeatable cut at every joist."],
        ["Halves the member depth at the lap.",
         "Stagger laps on a girder to avoid a line of weakness."]),
    "upper-joist-into-girder": m(1,
        "二階根太 upper-floor joist housed into a 胴差 girder.",
        ["The housing locates the joist and keeps the floor flat.",
         "Works with the upper storey's flush-top layout."],
        ["A joist in a plain ooire behaves as a simple beam and can loosen.",
         "Deep housings into the girder reduce its section."]),

    # ------------------------------------------------------------- new specimens
    "watari-ago-niju-hozo-shikuchi": m(3,
        "Double-tenon crossing over a post: a 桁 girder sits on the post's lower "
        "tenon, a 梁 beam crosses above it and is locked by the post's upper "
        "tenon passing through the girder, and a carved 渡り顎 jaw joins the "
        "crossing timbers.",
        ["The lower tenon fixes the girder on the post without hollowing the "
         "post's core.",
         "The upper tenon runs through the girder into the beam, so the joint "
         "resists uplift as well as side slip.",
         "The 渡り顎 jaw bears on the girder and stops the beam shifting along "
         "the crossing."],
        ["The girder loses half its depth where the jaw is cut.",
         "The through tenon and the jaw must be set out together; the "
         "carpentry-school build log records over two hours of scribing."]),
    "sampo-sashi-shachi-sen": m(4,
        "Three-direction T-junction post with beams arriving from three "
        "directions, each locked by a tapered 車知栓 - built like the 四方差し "
        "figure in 建築用語集 but with one arrival omitted.",
        ["A shachi-sen through each tenon resists withdrawal on all three "
         "arrivals without a separate key per face.",
         "Tenons sit at stacked levels, so none share the post's core."],
        ["Through tenons leave a large lost section in the post (the same "
         "warning 建築用語集 gives 四方差し).",
         "Interpreted from the 四方差し figure with one arrival removed; it is "
         "not a separately sourced named specimen."]),
    "shihou-sashi-shachi-sen": m(5,
        "Four-way post connection locked with paired 車知栓 wedge keys - the "
        "configuration shown in 建築用語集's 四方差し figure, where the red "
        "member is the shachi-sen.",
        ["Paired wedge keys draw all four tenons tight and resist withdrawal.",
         "Opposite tenons pass through the post and tie one another."],
        ["Same warning as 四方差し: passing tenons leave a large lost post "
         "section; metal reinforcement may be needed.",
         "Four tenons and two keys must be set out at distinct levels."]),
}


def apply(level):
    """Return a copy of a decoded source record with the metadata stamped on."""
    out = copy.deepcopy(level)
    entry = META.get(out.get("id"))
    if entry:
        for key in ("beams", "usage", "strengths", "weaknesses"):
            out[key] = copy.deepcopy(entry[key])
    return out


def write_sources(src_dir, only=None):
    """Stamp every source JSON in ``src_dir`` (used once when adding the fields)."""
    import glob
    import os
    paths = sorted(glob.glob(os.path.join(src_dir, "*.json")))
    changed = []
    for path in paths:
        with open(path) as fh:
            data = json.load(fh)
        lv = data[0] if isinstance(data, list) else data
        if only and lv["id"] not in only:
            continue
        if lv["id"] not in META:
            print("no metadata for %s" % lv["id"])
            continue
        updated = apply(lv)
        with open(path, "w") as fh:
            json.dump([updated], fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        changed.append(lv["id"])
    return changed


if __name__ == "__main__":
    import os
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "joints", "sources")
    ids = write_sources(src, set(sys.argv[2:]) or None)
    print("tagged %d sources" % len(ids))
