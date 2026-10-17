//! `/` -- the gallery with nothing selected yet.

use crate::pages::{html, views, Ctx, Error, IntoResponse};

pub fn handle(ctx: &mut Ctx) -> Result<impl IntoResponse, Error> {
    html!(ctx, views::index::Index {})
}
