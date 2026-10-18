# Carpentry

A web gallery of wood joints. The list of joints is on the left. A three.js
viewer is on the right. Click a joint to see it in 3D, with an animation that
slides the timbers apart and back together.

The site is a brocanth application. The pages are
`.rsx` templates, compiled into the binary. The look follows
[docs.stripe.com](https://docs.stripe.com/). The layout takes its idea from
[wow-converter](https://github.com/IxDay/wow-converter).

## Run it

```
npm install        # once, for the Tailwind CLI
mise run css       # build assets/css/site.css
mise run run       # serve on http://127.0.0.1:3000
```

Run these checks after each change:

```
cargo test
cargo clippy --all-targets -- -D warnings
cargo fmt --check
```

## Where the joints come from

The joints are designs made in [Tsugite](https://github.com/marialarsson/tsugite),
the joint design tool from the UIST 2020 paper *Tsugite: Interactive Design
and Fabrication of Wood Joints*.

- The `tsugite` branch of this repository holds the full upstream history,
  unchanged, up to commit `8e17e06` (2024-11-29). It shares no history with
  `main`.
- The `tsugite-export` branch is `tsugite` plus 2 commits. They add the
  scripts that made the `.glb` files in `public/joints/`:
  - `recover_examples.py` gets back joints that were deleted from the
    upstream repository, as `.tsu` files in `recovered_joints/`.
  - `export_examples_glb.py` exports each `.tsu` file to
    `examples_glb/<group>/<name>.glb`.
  - `export_gallery_glb.py` holds the shared exporter: one node per timber,
    and an `assemble` animation.
- The scripts first ran in a local clone at
  `/Users/max/Documents/Dev/misc/tmp/carpentry.Qvg/tsugite`. The
  `tsugite-export` branch holds the same files.

To make the models again, check out `tsugite-export`, run this, then copy `examples_glb/*`
into `public/joints/`:

```
uv run recover_examples.py
uv run export_examples_glb.py
```

Each subfolder of `public/joints/` is one group in the sidebar
(`src/joints.rs`, `Group`). A new subfolder must have a `Group` variant. If it
does not, a test fails.

## License

Tsugite is free for personal use and for non-commercial research. The models
in `public/joints/` come from Tsugite, so the same terms apply to them. See the
`LICENSE` file on the `tsugite` branch.
