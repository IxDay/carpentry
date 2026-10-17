// The document: a top bar, the joint list on the left third and the viewer on
// the right two thirds. The look follows docs.stripe.com -- a white page,
// hairline borders, a quiet grey sidebar with the current entry in the accent
// colour.
//
// Only the `dp-layout` element is swapped when a link is followed. The list
// and the canvas sit outside it on purpose: the list keeps its scroll
// position and the viewer keeps its WebGL context between joints.
//
// three.js comes from jsdelivr through an import map, because its addons
// import the bare name `three` and only a map resolves that in a browser.

use crate::joints;
use crate::pages::routes;
use crate::pages::views::link::{Link, NavLink};
use crate::pages::TITLE;

pub fn Layout(layout: &str, path: &str, children: Element) -> Element {
    <!DOCTYPE html>
    <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>{TITLE}</title>
            <link rel="stylesheet" href={crate::assets::url("css/site.css")}>
            <script type="importmap">
                {"imports": {
                    "three": "https://cdn.jsdelivr.net/npm/three@0.170.0/build/three.module.js",
                    "three/addons/": "https://cdn.jsdelivr.net/npm/three@0.170.0/examples/jsm/"
                }}
            </script>
            <script src={crate::assets::url("dpswap.min.js")} defer></script>
            <script type="module" src={crate::assets::url("js/viewer.js")}></script>
        </head>
        <body class="h-screen flex flex-col bg-white text-body antialiased">
            <header class="topbar">
                <Link to="/">
                    <span class="brand">{TITLE}</span>
                </Link>
                <span class="brand-divider" aria-hidden="true"></span>
                <span class="brand-sub">Joinery</span>
                <span class="flex-1"></span>
                <a class="topbar-link" href="https://github.com/marialarsson/tsugite">Tsugite</a>
            </header>
            <div class="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-3">
                <aside class="sidebar">
                    <div class="sidebar-search">
                        <input id="joint-filter" type="search" placeholder="Filter joints" autocomplete="off" aria-label="Filter joints">
                        <kbd class="search-key">/</kbd>
                    </div>
                    <nav id="joint-nav" class="sidebar-nav" aria-label="Joints">
                        <ul>
                            <li><NavLink to="/" current={path == "/"}>Overview</NavLink></li>
                        </ul>
                        <h2 class="nav-heading">Three-timber joints</h2>
                        <ul>
                            for joint in joints::all() {
                                let to = routes::joints::id::path(joint.number());
                                <li>
                                    <NavLink to={&to} current={path == to}>{joint.name()}</NavLink>
                                </li>
                            }
                        </ul>
                        <p id="joint-empty" class="nav-empty" hidden>No joint matches.</p>
                    </nav>
                </aside>
                <main class="lg:col-span-2 min-h-0 flex flex-col">
                    <div id="outlet" dp-layout={layout} class="outlet">{children}</div>
                    <section id="viewer" class="viewer" data-state="empty">
                        <canvas id="viewer-canvas"></canvas>
                        <div class="viewer-overlay" data-show="empty">
                            <p>Select a joint to view it in 3D.</p>
                        </div>
                        <div class="viewer-overlay" data-show="loading">
                            <span class="spinner" aria-hidden="true"></span>
                            <p>Loading model&hellip;</p>
                        </div>
                        <div class="viewer-overlay" data-show="error">
                            <p class="text-red-600">The model failed to load.</p>
                        </div>
                        <div class="viewer-toolbar" role="toolbar" aria-label="Viewer">
                            <button type="button" id="viewer-play" class="tool" aria-pressed="true">Animate</button>
                            <button type="button" id="viewer-rotate" class="tool" aria-pressed="false">Rotate</button>
                            <button type="button" id="viewer-reset" class="tool">Reset view</button>
                        </div>
                    </section>
                </main>
            </div>
        </body>
    </html>
}
