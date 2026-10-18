//! `/joints/{group}/{name}` -- one joint, shown in the viewer beside the list.

use crate::joints;
use crate::pages::{html, views, Ctx, Error, IntoResponse};

pub fn handle(ctx: &mut Ctx) -> Result<impl IntoResponse, Error> {
    // A 404 and not a 400: the segments are well formed, the catalogue
    // simply has no joint under that name.
    let joint = joints::find(ctx.require("group")?, ctx.require("name")?)
        .ok_or_else(|| Error::new(404, "No such joint"))?;
    html!(ctx, views::joints::_group_::_name_::JointPage { joint })
}
