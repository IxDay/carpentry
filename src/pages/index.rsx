// The overview. It carries no `data-glb`, so the viewer beside it shows its
// empty state rather than a joint nobody picked.

pub fn Index() -> Element {
    <article class="joint">
        <nav class="crumbs" aria-label="Breadcrumb"><span>Joints</span></nav>
        <h1 class="title">Joint gallery</h1>
        <p class="lede">
            {crate::joints::all().len()} joints designed in Tsugite. Pick one in
            the list to open it in the viewer. Use <kbd>&uarr;</kbd> and <kbd>&darr;</kbd>
            to step through them, and <kbd>/</kbd> to filter.
        </p>
    </article>
}
