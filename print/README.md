# Printable Watari joint

`watari-ago-niju-hozo-shikuchi.3mf` holds the three timbers of the
渡り顎二重枠仕口 as separate, named objects in millimetres, already sitting on
the build plate and separated by 12 mm. Open it once in Ultimaker Cura (or any
slicer that reads 3MF) and each timber appears as its own model.

The per-piece `*_<piece>.stl` files carry the same geometry at the same bed
positions, for slicers or CAD tools that prefer STL.

| piece | id | size (mm) | notes |
| --- | --- | --- | --- |
| post | `post` | 12 × 12 × 66 | stands upright, 80 mm tenon at the foot, 40 mm tenon at the top |
| girder | `girder-x` | 80 × 12 × 12 | 渡り顎 housing on top, post socket underneath |
| beam | `beam-z` | 12 × 80 × 13.8 | 18 mm chin, prints chin-up on its flat face |

**Scale: 1:10.** The 120 mm timbers print 12 mm square, the 80 mm tenons 8 mm,
the beams are 80 mm long. Regenerate at another scale with:

```sh
cd ../tools
python3 export_print.py ../joints/sources/watari-ago-niju-hozo-shikuchi.json \
    --outdir ../print --scale 0.05     # 1:20, 6 mm sections
```

`--scale 1` is full size (120 mm sections, 800 mm beams, too big for a 220 mm
bed). At 1:10 the whole row is 128 mm wide, so it fits any common plate.

## Printing

No supports are needed. The post stands 66 mm tall on a 12 × 12 foot; the girder
and beam lie flat. The girder's post socket leaves a 48 mm² ceiling 6 mm above
the plate, which bridges without help — expect a slightly rough underside
inside the socket, out of sight once assembled.

A 0.4 mm nozzle at 1:10 gives roughly 30 lines across a timber. The 4 × 4 mm
tenons are the delicate part: print slowly, or go to 1:5 (`--scale 0.2`, 24 mm
sections, 160 mm beams) if the parts are to be handled a lot. The assembled
joint is 80 × 80 mm in plan and 66 mm tall at 1:10 — a desk model rather than a
load-bearing one.

Assembly is the animation's reverse: the girder drops over the post's 40 mm
tenon, then the beam drops through the girder and over the same tenon, its chin
seating in the girder's transverse housing. The tenon is cut flush with the
beam's top face, so nothing should protrude when the joint is closed.
