//! Carpentry -- a brocanth application.
//!
//! This binary is the project's command line. `serve` is the one command the
//! scaffold wrote; the rest are yours. A struct with `#[cmd]` under
//! `src/commands/` is a subcommand, registered at link time, with no list to
//! add it to.
//!
//! The wiring lives in `src/app.rs`, so `serve` and anything else that needs
//! the router read the same thing.

mod app;
mod assets;
mod commands;
mod joints;
mod pages;
mod plugins;

fn main() -> brocanth_command::anyhow::Result<()> {
    brocanth_command::main(brocanth_command::Context::boot()?)
}
