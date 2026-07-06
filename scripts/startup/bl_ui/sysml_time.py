# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""SysML time <-> Blender frames (Animation Binding A / SCRUM-645).

The temporal sibling of the units bridge. A SysML `Occurrence` snapshot carries a
clock time (`1 [s]`); Blender animation is indexed by frame. This maps between
them using the scene's effective fps and a frame origin (the frame that
corresponds to time 0):

    frame  = origin + time_seconds * fps
    time_s = (frame - origin) / fps

The unit a time value is expressed in is carried on the node as the
`sysml_time_unit` custom property (defaults to seconds).
"""

TIME_UNIT_KEY = "sysml_time_unit"
DEFAULT_TIME_UNIT = "s"

# Time unit -> seconds.
TIME_TO_SECONDS = {
    "s": 1.0,
    "ms": 1e-3,
    "us": 1e-6,
    "µs": 1e-6,
    "ns": 1e-9,
    "ks": 1e3,
    "min": 60.0,
    "h": 3600.0,
    "day": 86400.0,
}


def time_unit_factor(unit):
    """Seconds per one `unit` (unknown units are treated as seconds)."""
    return TIME_TO_SECONDS.get((unit or DEFAULT_TIME_UNIT).strip(), 1.0)


def fps(scene):
    """Effective frames per second for `scene` (24.0 when unavailable)."""
    try:
        return scene.render.fps / scene.render.fps_base
    except AttributeError:
        return 24.0


def frame_origin(scene, origin=None):
    """The frame at time 0: explicit `origin`, else the scene start, else 0."""
    if origin is not None:
        return origin
    try:
        return scene.frame_start
    except AttributeError:
        return 0


def to_frame(value, unit, scene=None, origin=None):
    """A SysML time `value` in `unit` -> a Blender frame number."""
    seconds = float(value) * time_unit_factor(unit)
    rate = fps(scene) if scene is not None else 24.0
    return frame_origin(scene, origin) + seconds * rate


def from_frame(frame, unit, scene=None, origin=None):
    """A Blender frame number -> a SysML time value expressed in `unit`."""
    rate = fps(scene) if scene is not None else 24.0
    seconds = (float(frame) - frame_origin(scene, origin)) / rate
    return seconds / time_unit_factor(unit)
