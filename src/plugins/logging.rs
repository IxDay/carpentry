//! Request logging.
//!
//! The core assumes no log layer at all -- not `log`, not `tracing`, not a
//! trait with a no-op default. This file is the whole of logging in this
//! binary: delete the registration in `main` and nothing logs, delete this file
//! and nothing about logging is compiled.

use brocanth::plugin_api::{Lifecycle, MiddlewareCatalog, Plugin, PluginError};
use brocanth::plugin_context::NoContext;
use brocanth::routing::Next;

use crate::pages::{Ctx, Response};

/// What this plugin is built from.
///
/// It derives `Deserialize` because this application reads it from
/// `[logging]` in a TOML file. Drop the config plugin and the derive goes
/// with it: `Plugin::Config` carries no bounds the core imposes.
#[derive(Debug, serde::Deserialize)]
#[serde(default, deny_unknown_fields)]
pub struct Settings {
    /// `error`, `warn`, `info` or `debug`.
    pub level: String,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            level: "info".to_string(),
        }
    }
}

pub struct Logging {
    level: String,
}

impl Plugin for Logging {
    type Config = Settings;
    /// Nothing on the context: a logger writes, it does not hand values out.
    type Provides = NoContext;
    const NAME: &'static str = "logging";

    fn new(config: Settings) -> Self {
        Self {
            level: config.level,
        }
    }

    fn configure_router(&mut self, catalog: &mut MiddlewareCatalog<'_>) -> Result<(), PluginError> {
        // Offered, not mounted. Where it runs is the application's call, made
        // in `main`, at a pattern this file never sees.
        catalog.offer("request_log", "one line per request: verb, path, status");
        Ok(())
    }

    fn before_start(&mut self, lc: &mut Lifecycle<'_>) -> Result<(), PluginError> {
        eprintln!("[{}] level {}", lc.instance(), self.level);
        Ok(())
    }
}

/// The layer `request_log` mounts.
///
/// A plain function is a layer: `Layer` is implemented for anything callable
/// with a context and the rest of the chain. Not calling `next.run` is how a
/// layer short-circuits, and dropping it is all that takes.
pub fn layer(ctx: &mut Ctx, next: Next<'_, Ctx, Response>) -> Response {
    let verb = ctx.verb;
    let path = ctx.path.clone();
    let response = next.run(ctx);
    eprintln!("{verb} {path} -> {}", response.status);
    response
}
