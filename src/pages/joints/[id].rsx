// The part of the page that changes with the joint. The canvas is in the
// root layout, outside the swap, so moving between joints reuses one WebGL
// context; `data-glb` below is what tells it which model to load.

use crate::joints::Joint;
use crate::pages::routes;
use crate::pages::views::link::Link;

pub fn JointPage(joint: Joint) -> Element {
    <article data-joint={joint.number()} data-glb={joint.glb()} data-title={joint.name()} class="joint">
        <nav class="crumbs" aria-label="Breadcrumb">
            <Link to="/">Joints</Link>
            <span aria-hidden="true">/</span>
            <span>{joint.name()}</span>
        </nav>
        <div class="flex items-start justify-between gap-6">
            <div>
                <h1 class="title">{joint.name()}</h1>
                <p class="lede">
                    Three timbers, interlocking in a 3&times;3&times;3 voxel grid.
                    The animation slides them apart along the assembly axis and back.
                </p>
            </div>
            <div class="pager">
                if let Some(previous) = joint.previous() {
                    <Link to={&routes::joints::id::path(previous.number())}>&larr; Previous</Link>
                }
                if let Some(next) = joint.next() {
                    <Link to={&routes::joints::id::path(next.number())}>Next &rarr;</Link>
                }
            </div>
        </div>
        <div class="flex flex-wrap gap-2 mt-4">
            <span class="badge">3 timbers</span>
            <span class="badge">3&times;3&times;3 voxels</span>
            <a class="badge badge-link" href={joint.glb()} download>Download .glb</a>
        </div>
    </article>
}
