#!/usr/bin/env python3
"""Generate the static GitHub Pages site for the baked joints.

Reads ``joints/sources/<id>.json`` (title, Japanese name, credit), copies each
``joints/<id>.glb`` and its sunset preview, and writes a single page where
every joint is a section with an anchor (``#<id>``), a <model-viewer> that plays
the ``assemble`` clip, and the Japanese name below the romanised one.

    python3 tools/build_site.py                  # -> docs/
    python3 tools/build_site.py --out public --preview

The output is plain static files; point GitHub Pages at the folder (``/docs`` on
the default branch needs no workflow).
"""
import argparse
import html
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TEMPLATE = os.path.join(HERE, "site_template.html")

TABS = [
    ("sheet", "On the sheets",
     "Every family printed on the two reference sheets."),
    ("extra", "Off the sheets",
     "Joints the reference sheets do not show, authored for this collection."),
]
DEFAULT_TAB = TABS[0][0]

REFERENCES = [
    ("JAANUS, kanawa tsugi 金輪継",
     "https://projects.mcah.columbia.edu/jaanus/node/3413"),
    ("Denmoku database, joint test drawings (金輪継ぎ, nos. 39-47)",
     "http://www.denmoku-db.jp/files/libs/86/201703290450302471.pdf"),
    ("Kyoto Araki Komuten, 金輪継",
     "http://kyoto-araki.jp/kyomachiya/kig%75mi/kanawa.html"),
    ("Uchimill, 継手 (金輪継ぎ)",
     "https://uchimill.com/2019/05/27/makinghouse-tipstsugite-1/"),
    ("Nekodigi, 金輪継ぎを設計して3Dプリントする",
     "https://nekodigi.hatenablog.com/entry/2020/04/04/%E3%80%90Processing%E3%80%91"
     "%E9%87%91%E8%BC%AA%E7%B6%99%E3%81%8E%E3%82%92%E8%A8%AD%E8%A8%88%E3%81%97%E3%81"
     "%A63D%E3%83%97%E3%83%AA%E3%83%B3%E3%83%88%E3%81%99%E3%82%8B"),
    ("Fine Woodworking, 5 spectacular Japanese joints (the Otemon splice)",
     "https://www.finewoodworking.com/2021/09/29/5-spectacular-japanese-joints"),
    ("Core77, Crazy Japanese technique for splicing the bottom of a rotted column",
     "https://www.core77.com/posts/136894/Crazy-Japanese-Technique-for-Splicing-the-Bottom-of-a-Rotted-Column"),
    ("The Carpentry Way, Chasing transcendence (basara-tsugi)",
     "https://thecarpentryway.blog/2012/12/chasing-transcendence/"),
    ("Big's Woodworking, kanawa tsugi joinery models, part 2",
     "https://bigsandwoodworking.com/kanawa-tsugi-joinery-models-part-2"),
]


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def esc(text):
    return html.escape(text, quote=True)


def load_joints(joints_dir):
    src_dir = os.path.join(joints_dir, "sources")
    known = {tid for tid, _, _ in TABS}
    joints = []
    for name in sorted(os.listdir(src_dir)):
        if not name.endswith(".json"):
            continue
        with open(os.path.join(src_dir, name)) as fh:
            lv = json.load(fh)[0]
        slug = lv["id"]
        if slug != slugify(lv["title"]):
            print("note: id %r differs from slugified title %r" % (slug, slugify(lv["title"])),
                  file=sys.stderr)
        glb = os.path.join(joints_dir, slug + ".glb")
        if not os.path.exists(glb):
            print("skipping %s: no GLB" % slug, file=sys.stderr)
            continue
        tab = lv.get("tab", DEFAULT_TAB)
        if tab not in known:
            print("note: %s has unknown tab %r, using %r" % (slug, tab, DEFAULT_TAB),
                  file=sys.stderr)
            tab = DEFAULT_TAB
        joints.append({
            "slug": slug,
            "title": lv["title"],
            "jp": lv["jp"],
            "tab": tab,
            "pieces": len(lv["pieces"]),
            "source": lv["source"],
            "glb": glb,
            "poster": os.path.join(joints_dir, "previews", "sunset_%s.png" % slug),
        })
    order = {tid: i for i, (tid, _, _) in enumerate(TABS)}
    joints.sort(key=lambda j: (order[j["tab"]], j["slug"]))
    return joints


def tab_counts(joints):
    counts = {}
    for j in joints:
        counts[j["tab"]] = counts.get(j["tab"], 0) + 1
    return counts


def nav_item(j, counts):
    hidden = "" if j["tab"] == DEFAULT_TAB else " hidden"
    return ('        <li data-tab="%s"%s><a href="#%s"><span class="name">%s</span>'
            '<span class="jp" lang="ja">%s</span></a></li>'
            % (j["tab"], hidden, j["slug"], esc(j["title"]), esc(j["jp"])))


def tab_bar(joints):
    counts = tab_counts(joints)
    out = []
    first = True
    for tid, label, note in TABS:
        if not counts.get(tid):
            continue
        out.append(
            '        <button type="button" role="tab" id="tab-%s" data-tab="%s"'
            ' data-note="%s" aria-selected="%s" tabindex="%s" aria-controls="joint-list">'
            '%s <span class="count">%d</span></button>'
            % (tid, tid, esc(note), "true" if first else "false",
               "0" if first else "-1", esc(label), counts[tid]))
        first = False
    return "\n".join(out)


def section(j, counts):
    s = j["source"]
    sa = "SA" in s["license"]
    note = " Shared alike under the same license." if sa else ""
    # The authored joints link to the repository, not to a Sketchfab original.
    origin = (' <a href="%s">Original on Sketchfab</a>.' % esc(s["url"])
              if "sketchfab.com" in s["url"] else
              ' <a href="%s">Source in this repository</a>.' % esc(s["url"]))
    hidden = "" if j["tab"] == DEFAULT_TAB else " hidden"
    return """      <section class="joint" id="{slug}" data-tab="{tab}" data-tab-count="{count}"{hidden}>
        <header>
          <h2><a href="#{slug}">{title}<span class="hash" aria-hidden="true">#</span></a></h2>
          <p class="jp" lang="ja">{jp}</p>
        </header>
        <div class="stage">
          <div class="spinner" aria-hidden="true"></div>
          <model-viewer id="viewer-{slug}" data-src="models/{slug}.glb"
              alt="{title} assembling" autoplay animation-name="assemble" camera-controls
              touch-action="pan-y" interaction-prompt="none" shadow-intensity="0"
              camera-orbit="38deg 64deg auto" loading="eager"></model-viewer>
          <button type="button" data-replay="viewer-{slug}">Replay</button>
        </div>
        <p class="meta">{pieces} pieces &middot; model by <a href="{author_url}">{author}</a>,
          <a href="{license_url}">{license}</a>, modified.{note}{origin}</p>
      </section>""".format(
        slug=j["slug"], title=esc(j["title"]), jp=esc(j["jp"]), pieces=j["pieces"],
        tab=j["tab"], count=counts[j["tab"]], hidden=hidden,
        author=esc(s["author"]), author_url=esc(s["authorUrl"]),
        license=esc(s["license"]), license_url=esc(s["licenseUrl"]),
        origin=origin, note=note)


def footer(repo_url, joints=()):
    refs = "\n".join('        <li><a href="%s">%s</a></li>' % (esc(u), esc(t)) for t, u in REFERENCES)
    words = ("zero one two three four five six seven eight nine ten eleven twelve "
             "thirteen fourteen fifteen sixteen seventeen eighteen nineteen").split()

    def number(n):
        return words[n] if n < len(words) else str(n)

    authored = [j for j in joints if "sketchfab.com" not in j["source"]["url"]]
    sheet = [j for j in authored if j.get("tab", DEFAULT_TAB) == DEFAULT_TAB]
    extra = [j for j in authored if j.get("tab", DEFAULT_TAB) != DEFAULT_TAB]
    authored_line = ""
    if sheet:
        authored_line = (
            "      <p>%s joints with no licensed source model &mdash; every "
            "family on the reference sheets, splices included &mdash; are authored "
            "for this collection from 柱（軸組）の納まり and released CC BY "
            "4.0.</p>" % number(len(sheet)).capitalize())
    if extra:
        if repo_url:
            cited = ('<a href="%s/joints/README.md">joints/README.md</a>'
                     % esc(repo_url.rstrip("/")))
        else:
            cited = "joints/README.md"
        authored_line += (
            "\n      <p>%s more, in the <em>Off the sheets</em> tab, go beyond the "
            "sheets: a dovetail splice and a 包み込み貫 tie, authored from the "
            "sources cited in %s.</p>"
            % (number(len(extra)).capitalize(), cited))
    repo = ('\n      <p>Source and tooling: <a href="%s">%s</a>. Per-joint notes '
            'and references: <a href="%s/joints/README.md">joints/README.md</a>.</p>'
            % (esc(repo_url), esc(repo_url), esc(repo_url.rstrip("/")))
            if repo_url else "")
    return """      <h2>About</h2>
      <p>Models by <a href="https://sketchfab.com/thejoinery">thejoinery</a> (CC BY 4.0, one
        CC BY-SA 4.0), read from the public Sketchfab viewer, split into timbers, re-lit with a
        baked paper-sunrise look and given an assembly animation. The animations were checked
        for timbers passing through each other, and some meshes were corrected where the
        author's pose was not the true closed joint.</p>
%s
      <h2>References</h2>
      <ul>
%s
      </ul>%s""" % (authored_line, refs, repo)


def copy_if_changed(src, dst):
    if os.path.exists(dst) and os.path.getsize(dst) == os.path.getsize(src):
        with open(src, "rb") as a, open(dst, "rb") as b:
            if a.read() == b.read():
                return
    shutil.copyfile(src, dst)


def copy_vendor(out):
    """Copy the pinned third-party scripts the page loads (see vendor/README.md)."""
    src = os.path.join(HERE, "vendor")
    dst = os.path.join(out, "vendor")
    os.makedirs(dst, exist_ok=True)
    wanted = {name for name in os.listdir(src)
              if name != "README.md" and os.path.isfile(os.path.join(src, name))}
    for name in sorted(wanted):
        copy_if_changed(os.path.join(src, name), os.path.join(dst, name))
    for name in os.listdir(dst):
        if name not in wanted:
            os.remove(os.path.join(dst, name))


def build(joints_dir, out, repo_url):
    joints = load_joints(joints_dir)
    for sub in ("models", "posters"):
        os.makedirs(os.path.join(out, sub), exist_ok=True)
    copy_vendor(out)
    keep = set()
    for j in joints:
        copy_if_changed(j["glb"], os.path.join(out, "models", j["slug"] + ".glb"))
        keep.add(j["slug"])
        if os.path.exists(j["poster"]):
            copy_if_changed(j["poster"], os.path.join(out, "posters", j["slug"] + ".png"))
    for sub, ext in (("models", ".glb"), ("posters", ".png")):
        for name in os.listdir(os.path.join(out, sub)):
            if name.endswith(ext) and name[:-len(ext)] not in keep:
                os.remove(os.path.join(out, sub, name))

    with open(TEMPLATE) as fh:
        page = fh.read()
    counts = tab_counts(joints)
    page = (page.replace("{{TABS}}", tab_bar(joints))
                .replace("{{NAV}}", "\n".join(nav_item(j, counts) for j in joints))
                .replace("{{SECTIONS}}", "\n".join(section(j, counts) for j in joints))
                .replace("{{FOOTER}}", footer(repo_url, joints))
                .replace("{{COUNT}}", str(len(joints)))
                .replace("{{OG_IMAGE}}", joints[0]["slug"]))
    with open(os.path.join(out, "index.html"), "w") as fh:
        fh.write(page)
    # no Jekyll processing: the site is already static
    open(os.path.join(out, ".nojekyll"), "w").close()
    print("wrote %s: %d joints" % (os.path.join(out, "index.html"), len(joints)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--joints", default=os.path.join(ROOT, "joints"),
                    help="folder with <id>.glb, previews/ and sources/")
    ap.add_argument("--out", default=os.path.join(ROOT, "docs"))
    ap.add_argument("--repo-url", default="",
                    help="link to the source repository in the footer")
    ap.add_argument("--preview", action="store_true",
                    help="serve the result on http://localhost:8000 afterwards")
    args = ap.parse_args()
    build(args.joints, args.out, args.repo_url)
    if args.preview:
        import functools
        import http.server
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=args.out)
        print("serving on http://localhost:8000")
        http.server.ThreadingHTTPServer(("", 8000), handler).serve_forever()


if __name__ == "__main__":
    main()
