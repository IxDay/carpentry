#!/usr/bin/env python3
"""Staged unbuild/rebuild animation for the house frame.

The joint models animate between an authored exploded pose and the closed
joint.  The house has no single exploded pose: 272 timbers, each held by a
different connection.  So every track is derived from the joint that holds the
timber.  A member first withdraws along that joint's extraction direction - a
post lifts off its sill tenon, a nuki slides out of its through mortise, a
rafter lifts out of its birdsmouth - and only then travels to a parked pose
clear of the frame.  The schedule is a construction sequence: the house comes
apart from the ridge down, waits as an empty foundation, and goes back
together from the foundation up.

The rest pose in the GLB stays assembled, so the poster and the opening frame
are the finished house; the clip moves the nodes out and back.  Key times are
per member (there is no global frame grid), and each move is sampled with a
smoothstep so the LINEAR glTF interpolation still eases.
"""

import math

MAX_STAGE = 11
LEAD = 0.8          # assembled hold before the first timber leaves
STEP = 0.9          # spacing between stages
CLEAR_T = 0.35      # short joint withdrawal
TRAVEL_T = 1.5      # flight to the parked pose
MOVE = CLEAR_T + TRAVEL_T
HOLD = 1.0          # the empty foundation pause
END = 27.0          # a little over the last rebuild plus a settle

REBUILD_START = LEAD + MAX_STAGE * STEP + MOVE + HOLD   # 13.55

ZERO = [0.0, 0.0, 0.0]
UP = [0.0, 1.0, 0.0]


# ---------------------------------------------------------------------------
# piece properties
def bbox(piece):
    pts = [q for s in piece["solids"] for f in s["faces"] for q in f["points"]]
    if not pts:
        return None, None
    mn = [min(q[i] for q in pts) for i in range(3)]
    mx = [max(q[i] for q in pts) for i in range(3)]
    return ([mn[i] / 2 + mx[i] / 2 for i in range(3)],
            [mx[i] - mn[i] for i in range(3)])


def radial(c):
    """Horizontal direction away from the plan centre, with a diagonal fallback
    for compact members (posts) so the corners open outwards."""
    x, z = c[0], c[2]
    if abs(x) < 0.05 and abs(z) < 0.05:
        return [1.0, 0.0, 0.0]
    d = math.sqrt(x * x + z * z)
    return [x / d, 0.0, z / d]


def outward(c, size):
    """The direction a wall layer peels away from the frame.

    Long members leave square to their wall: a member spanning x parks on the
    +-z side and vice versa.  Compact members (posts) move diagonally out from
    the plan centre.
    """
    if size[0] > 1.0 and size[0] >= size[2]:
        return [0.0, 0.0, 1.0 if c[2] >= 0 else -1.0]
    if size[2] > 1.0 and size[2] > size[0]:
        return [1.0 if c[0] >= 0 else -1.0, 0.0, 0.0]
    return radial(c)


# ---------------------------------------------------------------------------
# construction order: 0 goes down first and comes back first
def stage_of(pid, name, c):
    if name in ("Plinth", "Strip footing", "Pad footing", "Foundation stone",
                "Floor stone"):
        return None                      # the ground is not a timber
    if name in ("Sill", "Centre sill", "Floor post", "Sleeper", "Joist"):
        return 0
    if name in ("Post", "Stud"):
        return 4 if pid.endswith("-up") else 1
    if name in ("Brace", "Fire beam", "Nuki"):
        return 2 if c[1] < 3.27 else 4
    if name in ("Gird", "Floor beam", "Upper joist"):
        return 3
    if name == "Plate":
        return 5
    if name == "Roof beam":
        return 6
    if name in ("King post", "Roof strut"):
        return 7
    if name == "Purlin":
        return 8
    if name == "Ridge":
        return 9
    if name == "Hip rafter":
        return 10
    if name in ("Rafter", "Jack rafter"):
        return 11
    raise KeyError("no construction stage for %s (%s)" % (pid, name))


# ---------------------------------------------------------------------------
# joint-derived extraction and the parked pose
CLEAR = {
    "Sill": 0.22, "Centre sill": 0.18, "Floor post": 0.20, "Sleeper": 0.10,
    "Joist": 0.10, "Upper joist": 0.12, "Post": 0.28, "Stud": 0.20,
    "Gird": 0.20, "Floor beam": 0.20, "Plate": 0.20, "Roof beam": 0.20,
    "King post": 0.30, "Roof strut": 0.20, "Purlin": 0.18, "Ridge": 0.18,
}


PARK_Y = 12.0       # clear of the top of the framed view


def park_dist(size):
    """A little fan outwards, so a wall does not rise as one rigid sheet."""
    return 4.0 + 0.30 * max(size)


def motion_for(pid, name, c, size, stage):
    """Return (extraction axis, clear distance, parked offset).

    Every timber parks outside the camera frame, so the unbuilt house reads as
    a bare foundation; the pieces fly back in during the rebuild.
    """
    d = park_dist(size)
    if name == "Nuki":
        # 貫 passes through the posts: it slides out along its own length.
        k = 0 if size[0] >= size[2] else 2
        s = 1.0 if c[k] >= 0 else -1.0
        ax = [0.0, 0.0, 0.0]
        ax[k] = s
        return ax, 0.18, [ax[0] * d, PARK_Y + 0.2 * stage,
                          ax[2] * d]
    if name == "Brace":
        # let into the post and beam faces: it withdraws square to the wall.
        k = 0 if pid.startswith("brace-end") else 2
        s = 1.0 if c[k] >= 0 else -1.0
        ax = [0.0, 0.0, 0.0]
        ax[k] = s
        return ax, 0.16, [ax[0] * d, PARK_Y + 0.2 * stage, ax[2] * d]
    if name == "Fire beam":
        r = radial(c)
        return UP, 0.14, [r[0] * d, PARK_Y + 0.2 * stage, r[2] * d]
    if name in ("Rafter", "Jack rafter"):
        # lifts out of the birdsmouths, then slides out over the eave.
        if name == "Rafter":
            o = [0.0, 0.0, 1.0 if pid.endswith("-f") else -1.0]
        else:
            o = [1.0 if pid.endswith("-r") else -1.0, 0.0, 0.0]
        return UP, 0.12, [o[0] * d, PARK_Y + 0.2 * stage, o[2] * d]
    if name == "Hip rafter":
        sx = 1.0 if c[0] >= 0 else -1.0
        sz = 1.0 if c[2] >= 0 else -1.0
        return UP, 0.14, [sx * d, PARK_Y + 0.2 * stage, sz * d]
    # everything else lifts along its tenon, then withdraws on its wall normal.
    o = outward(c, size)
    return UP, CLEAR[name], [o[0] * d, PARK_Y + 0.2 * stage, o[2] * d]


# ---------------------------------------------------------------------------
def jitter(pid):
    """A small deterministic stagger inside a stage, so a wall does not leave
    in one rigid piece.  Repeatable across rebuilds, which keeps the two
    halves of the cycle symmetrical."""
    h = 0
    for i, ch in enumerate(pid):
        h = (h * 131 + ord(ch) * (i + 7)) & 0xFFFF
    return (h % 97) / 97.0 * 0.35


def _segment(keys, t0, t1, a, b, n=6):
    for k in range(1, n + 1):
        u = k / float(n)
        e = u * u * (3.0 - 2.0 * u)
        keys.append((round(t0 + (t1 - t0) * u, 3),
                     [a[i] + (b[i] - a[i]) * e for i in range(3)]))


def track_for(pid, stage, name, c, size):
    ax, clear, park = motion_for(pid, name, c, size, stage)
    clear_vec = [ax[i] * clear for i in range(3)]
    j = jitter(pid)
    t_out = LEAD + (MAX_STAGE - stage) * STEP + j
    t_in = REBUILD_START + stage * STEP + j
    keys = [(0.0, list(ZERO)), (round(t_out, 3), list(ZERO))]
    _segment(keys, t_out, t_out + CLEAR_T, ZERO, clear_vec)
    _segment(keys, t_out + CLEAR_T, t_out + MOVE, clear_vec, park)
    keys.append((round(t_in, 3), list(park)))
    _segment(keys, t_in, t_in + TRAVEL_T, park, clear_vec)
    _segment(keys, t_in + TRAVEL_T, t_in + MOVE, clear_vec, ZERO)
    keys.append((END, list(ZERO)))
    return keys


def assemble_animation(pieces):
    """One glTF animation track per timber; the ground stays put."""
    tracks = {}
    stages = {}
    for p in pieces:
        c, size = bbox(p)
        if c is None:
            continue
        stage = stage_of(p["id"], p["name"], c)
        if stage is None:
            continue
        tracks[p["id"]] = track_for(p["id"], stage, p["name"], c, size)
        stages[p["id"]] = stage
    return {"name": "assemble", "tracks": tracks,
            "stages": stages, "duration": END}
