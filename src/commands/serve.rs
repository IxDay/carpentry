//! `serve` -- the one command the scaffold wrote.
//!
//! It is ordinary project code: rename it, give it more flags, or delete it.
//! The framework does not own this command line.

use brocanth_command::{anyhow, clap, cmd, Command, Context};

/// Serve the application over HTTP.
#[cmd]
#[derive(clap::Args)]
pub struct Serve {
    /// Address to bind.
    #[arg(long, default_value = "127.0.0.1:3000")]
    pub addr: String,
}

impl Command for Serve {
    fn run(self, _ctx: &mut Context) -> anyhow::Result<()> {
        crate::app::serve(&self.addr).map_err(anyhow::Error::msg)
    }
}
