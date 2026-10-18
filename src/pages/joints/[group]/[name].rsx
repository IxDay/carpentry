// The part of the page that changes with the joint. The canvas is in the
// root layout, outside the swap, so moving between joints reuses one WebGL
// context; `data-glb` below is what tells it which model to load.

use crate::joints::Joint;
use crate::pages::views::link::Link;

pub fn JointPage(joint: Joint) -> Element {
    <article data-glb={joint.glb()} class="joint">
        <nav class="crumbs" aria-label="Breadcrumb">
            <Link to="/">Joints</Link>
            <span aria-hidden="true">/</span>
            <span>{joint.group.title()}</span>
        </nav>
        <div class="flex items-start justify-between gap-6">
            <div>
                <h1 class="title">{joint.title()}</h1>
                <p class="lede">
                    The animation slides the timbers apart along the assembly axis and back.
                </p>
            </div>
            <div class="pager">
                if let Some(previous) = joint.previous() {
                    <Link to={&previous.path()}>&larr; Previous</Link>
                }
                if let Some(next) = joint.next() {
                    <Link to={&next.path()}>Next &rarr;</Link>
                }
            </div>
        </div>
        <div class="flex flex-wrap gap-2 mt-4">
            if let Some(timbers) = joint.timbers() {
                <span class="badge">{timbers} timbers</span>
            }
            <span class="badge">{joint.group.title()}</span>
            <a class="badge badge-link" href={joint.glb()} download>{joint.file_name()}</a>
        </div>
    </article>
}
