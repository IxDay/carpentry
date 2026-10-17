// An anchor that swaps instead of reloading the document.
//
// Written as a real <a href> and enhanced afterwards. With JavaScript off,
// to a crawler, and on the first load of any page it is a link and the
// browser does what it always did -- which is why `to` is required and why
// there is no version of this that renders a <span> with a click handler.
//
// `to` takes what the route helpers return:
//
//     <Link to={routes::users::id::path(7)}>User 7</Link>
//
// never a string. A route that does not exist is then a compile error
// rather than a 404 somebody finds later.

pub fn Link(to: &str, children: Element) -> Element {
    <a href={to} dp-boost>{children}</a>
}

// A sidebar entry: a `Link` that knows whether it is the page being shown.
//
// `aria-current` rather than a class, so the styling and a screen reader read
// the same fact. The server sets it on a full load; after a swap the viewer
// script moves it, because the sidebar sits outside the swap and is never
// re-sent -- re-sending 184 rows would also reset its scroll position.
pub fn NavLink(to: &str, current: bool, children: Element) -> Element {
    if current {
        <a href={to} dp-boost class="nav-link" aria-current="page">{children}</a>
    } else {
        <a href={to} dp-boost class="nav-link">{children}</a>
    }
}
