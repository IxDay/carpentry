//! Every command in this project.
//!
//! The `mod` lines are the whole of it. A command registers itself through a
//! link-time slice, so adding one is a file and a `mod`, and there is no list
//! to keep in step.
//!
//! `serve` arrived with the scaffold and is ordinary code here: rename it,
//! give it flags, or delete it. The framework does not own this command line.

pub mod serve;
