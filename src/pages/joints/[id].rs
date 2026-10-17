//! `/joints/{id}` -- one joint, shown in the viewer beside the list.

use crate::joints::Joint;
use crate::pages::{html, views, Ctx, Error, IntoResponse};

pub fn handle(ctx: &mut Ctx) -> Result<impl IntoResponse, Error> {
    // A 404 and not a 400: the segment is well formed, the gallery simply
    // has no joint under that number.
    let joint = Joint::parse(ctx.require("id")?)
        .ok_or_else(|| Error::new(404, "No such joint"))?;
    html!(ctx, views::joints::_id_::JointPage { joint })
}
