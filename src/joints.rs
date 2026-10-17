//! The joint catalogue: the tsugite gallery, exported one `.glb` per joint.
//!
//! The files are `public/joints/joint_000.glb` to `joint_183.glb`. They sit in
//! `public/` and not `assets/` because the viewer fetches them by a name a
//! visitor can bookmark and share; a fingerprint would change that name on
//! every rebuild for files that never change.
//!
//! Every joint in the gallery is the same kind: three timbers meeting in a
//! 3x3x3 voxel grid (`search_results/noc_3/dim_3` upstream). Each file holds
//! one node per timber and an `assemble` animation that slides them together.

/// How many joints the gallery holds. A test below holds this to the files
/// in `public/joints`, so a file added or removed there fails the build's
/// tests rather than a link in the sidebar.
pub const COUNT: u16 = 184;

/// One joint, by its gallery number.
///
/// Only [`Joint::parse`] and [`all`] build one, and both check the range, so
/// a `Joint` always names a file that exists.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Joint(u16);

impl Joint {
    /// The joint a URL segment names, or `None` for anything outside the
    /// gallery. `"042"` and `"42"` are the same joint.
    pub fn parse(segment: &str) -> Option<Self> {
        let number: u16 = segment.parse().ok()?;
        (number < COUNT).then_some(Self(number))
    }

    pub fn number(self) -> u16 {
        self.0
    }

    /// The name the sidebar and the heading show.
    pub fn name(self) -> String {
        format!("Joint {:03}", self.0)
    }

    /// The URL of the model, as `public/` publishes it.
    pub fn glb(self) -> &'static str {
        crate::assets::url(&format!("joints/joint_{:03}.glb", self.0))
    }

    pub fn previous(self) -> Option<Self> {
        self.0.checked_sub(1).map(Self)
    }

    pub fn next(self) -> Option<Self> {
        (self.0 + 1 < COUNT).then_some(Self(self.0 + 1))
    }
}

/// Every joint, in gallery order.
pub fn all() -> impl Iterator<Item = Joint> {
    (0..COUNT).map(Joint)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn every_joint_names_a_published_model() {
        for joint in all() {
            assert!(
                crate::assets::lookup(joint.glb()).is_some(),
                "{} has no model",
                joint.name()
            );
        }
    }

    #[test]
    fn no_published_model_is_missing_from_the_catalogue() {
        let beyond = format!("/joints/joint_{COUNT:03}.glb");
        assert!(crate::assets::lookup(&beyond).is_none());
    }

    #[test]
    fn a_number_outside_the_gallery_is_not_a_joint() {
        assert_eq!(Joint::parse("42").map(Joint::number), Some(42));
        assert_eq!(Joint::parse("042").map(Joint::number), Some(42));
        assert_eq!(Joint::parse(&COUNT.to_string()), None);
        assert_eq!(Joint::parse("-1"), None);
        assert_eq!(Joint::parse("x"), None);
    }

    #[test]
    fn the_ends_of_the_gallery_have_no_neighbour_beyond_them() {
        assert_eq!(Joint::parse("0").and_then(Joint::previous), None);
        let last = (COUNT - 1).to_string();
        assert_eq!(Joint::parse(&last).and_then(Joint::next), None);
    }
}
