//! The joint catalogue: every `.tsu` joint in the tsugite repository,
//! exported one `.glb` per joint by `export_examples_glb.py`.
//!
//! The files are `public/joints/<group>/<name>.glb`. They sit in `public/`
//! and not `assets/` because the viewer fetches them by a name a visitor can
//! bookmark and share; a fingerprint would change that name on every rebuild
//! for files that never change.
//!
//! Nothing here lists the joints by hand. The catalogue is read off what
//! `assets!` embedded, so adding a file is the whole of adding a joint (after
//! `touch src/assets.rs`). A folder that is not a [`Group`] fails a test
//! rather than vanishing from the sidebar.

use std::sync::OnceLock;

use crate::assets::{Asset, ASSETS};

/// Where a joint came from: one subfolder of `examples_glb/` upstream.
///
/// The order of the variants is the order of the sidebar.
#[derive(Clone, Copy, Debug, PartialEq, Eq, PartialOrd, Ord)]
pub enum Group {
    Repo,
    Setup,
    PaperData,
    UserStudy,
    TsuHistory,
}

impl Group {
    pub const ALL: [Group; 5] = [
        Group::Repo,
        Group::Setup,
        Group::PaperData,
        Group::UserStudy,
        Group::TsuHistory,
    ];

    /// The folder name, which is also the URL segment.
    pub fn slug(self) -> &'static str {
        match self {
            Group::Repo => "repo",
            Group::Setup => "setup",
            Group::PaperData => "paper_data",
            Group::UserStudy => "user_study",
            Group::TsuHistory => "tsu_history",
        }
    }

    pub fn title(self) -> &'static str {
        match self {
            Group::Repo => "Repository examples",
            Group::Setup => "Setup",
            Group::PaperData => "Paper data",
            Group::UserStudy => "User study",
            Group::TsuHistory => "Earlier versions",
        }
    }

    pub fn from_slug(slug: &str) -> Option<Self> {
        Self::ALL.into_iter().find(|group| group.slug() == slug)
    }
}

/// One joint. Only [`all`] and [`find`] hand one out, and both read it off
/// an embedded file, so a `Joint` always names a model that is served.
#[derive(Clone, Copy)]
pub struct Joint {
    pub group: Group,
    /// The file stem, which is also the URL segment.
    pub name: &'static str,
    asset: &'static Asset,
}

impl Joint {
    /// The name the sidebar and the heading show: the file stem with its
    /// underscores read as spaces.
    pub fn title(self) -> String {
        let words: Vec<&str> = self.name.split('_').filter(|w| !w.is_empty()).collect();
        let mut title = words.join(" ");
        if let Some(first) = title.get(..1) {
            title.replace_range(..1, &first.to_uppercase());
        }
        title
    }

    pub fn file_name(self) -> &'static str {
        self.asset.logical.rsplit('/').next().unwrap_or(self.name)
    }

    pub fn path(self) -> String {
        crate::pages::routes::joints::group::name::path(self.group.slug(), self.name)
    }

    /// The URL of the model, as `public/` publishes it.
    pub fn glb(self) -> &'static str {
        self.asset.published
    }

    /// How many timbers the joint has, read from the model's node names.
    /// `None` for a file that is not the binary glTF the exporter writes.
    pub fn timbers(self) -> Option<usize> {
        #[derive(serde::Deserialize)]
        struct Gltf {
            nodes: Vec<Node>,
        }
        #[derive(serde::Deserialize)]
        struct Node {
            #[serde(default)]
            name: String,
        }

        // A .glb is a 12-byte header, then chunks; the first is the JSON.
        let body = self.asset.body;
        let length = u32::from_le_bytes(body.get(12..16)?.try_into().ok()?) as usize;
        let json = body.get(20..20 + length)?;
        let gltf: Gltf = serde_json::from_slice(json).ok()?;
        Some(
            gltf.nodes
                .iter()
                .filter(|n| n.name.starts_with("timber_"))
                .count(),
        )
    }

    pub fn previous(self) -> Option<Joint> {
        let at = self.index();
        at.checked_sub(1).map(|i| all()[i])
    }

    pub fn next(self) -> Option<Joint> {
        all().get(self.index() + 1).copied()
    }

    fn index(self) -> usize {
        all()
            .iter()
            .position(|joint| joint.asset.logical == self.asset.logical)
            .expect("a Joint comes out of the catalogue")
    }
}

/// Every joint, in sidebar order: by group, then by name.
pub fn all() -> &'static [Joint] {
    static CATALOGUE: OnceLock<Vec<Joint>> = OnceLock::new();
    CATALOGUE.get_or_init(|| {
        let mut joints: Vec<Joint> = ASSETS.iter().filter_map(parse).collect();
        // Case-blind, so `Untitled` does not sort ahead of `science_agora_…`.
        joints.sort_by_key(|joint| (joint.group, joint.name.to_lowercase()));
        joints
    })
}

/// The joints of one group, in sidebar order.
pub fn in_group(group: Group) -> impl Iterator<Item = Joint> {
    all()
        .iter()
        .copied()
        .filter(move |joint| joint.group == group)
}

/// The joint a URL names, or `None`.
pub fn find(group: &str, name: &str) -> Option<Joint> {
    let group = Group::from_slug(group)?;
    in_group(group).find(|joint| joint.name == name)
}

/// `joints/<group>/<name>.glb` to a joint; anything else is not one.
fn parse(asset: &'static Asset) -> Option<Joint> {
    let rest = asset.logical.strip_prefix("joints/")?;
    let (group, file) = rest.split_once('/')?;
    let name = file.strip_suffix(".glb")?;
    Some(Joint {
        group: Group::from_slug(group)?,
        name,
        asset,
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn every_model_under_joints_belongs_to_a_group() {
        let models = ASSETS
            .iter()
            .filter(|a| a.logical.starts_with("joints/"))
            .count();
        assert_eq!(
            all().len(),
            models,
            "a folder under public/joints is not a Group"
        );
        assert!(models > 0);
    }

    #[test]
    fn every_group_has_joints() {
        for group in Group::ALL {
            assert!(in_group(group).next().is_some(), "{group:?} is empty");
        }
    }

    #[test]
    fn every_model_has_its_timbers() {
        for joint in all() {
            let timbers = joint.timbers();
            assert!(
                matches!(timbers, Some(2..)),
                "{} has {timbers:?} timbers",
                joint.file_name()
            );
        }
    }

    #[test]
    fn a_joint_is_found_by_the_url_it_links_to() {
        for joint in all() {
            let found = find(joint.group.slug(), joint.name).map(|j| j.glb());
            assert_eq!(found, Some(joint.glb()));
        }
        assert!(find("repo", "no_such_joint").is_none());
        assert!(find("no_such_group", "3_1").is_none());
    }

    #[test]
    fn the_ends_of_the_catalogue_have_no_neighbour_beyond_them() {
        assert!(all()[0].previous().is_none());
        assert!(all()[all().len() - 1].next().is_none());
    }

    #[test]
    fn a_title_reads_underscores_as_spaces() {
        let joint = find("tsu_history", "setup_joint_-_Copy_3").expect("the file exists");
        assert_eq!(joint.title(), "Setup joint - Copy 3");
    }
}
