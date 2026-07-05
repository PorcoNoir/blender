# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""SysML time <-> Blender frames (Animation Binding A / SCRUM-645).

Checks the time-unit/frame conversions round-trip losslessly, honour the scene
fps, and place `1 [s]` at 24 fps on frame 24 (from a configurable origin).
Pure bpy (uses light fake scenes for scale/fps).
"""

import sys
import unittest

from bl_ui.sysml_time import to_frame, from_frame


class _Scene:
    def __init__(self, rate, base=1.0, start=0):
        self.render = type("R", (), {"fps": rate, "fps_base": base})()
        self.frame_start = start


class SysMLTimeTest(unittest.TestCase):
    def test_one_second_is_frame_24(self):
        scene = _Scene(24, start=0)
        self.assertAlmostEqual(to_frame(1, "s", scene), 24.0)
        self.assertAlmostEqual(to_frame(500, "ms", scene), 12.0)
        self.assertAlmostEqual(from_frame(24, "s", scene), 1.0)

    def test_roundtrip_lossless(self):
        scene = _Scene(30, start=1)
        for unit in ("s", "ms", "min", "us"):
            for value in (1.0, 0.5, 42.0, 1000.0):
                frame = to_frame(value, unit, scene)
                self.assertAlmostEqual(from_frame(frame, unit, scene), value, places=6,
                                       msg=f"{value} {unit}")

    def test_honours_scene_fps(self):
        self.assertAlmostEqual(to_frame(1, "s", _Scene(60, start=0)), 60.0)
        self.assertAlmostEqual(to_frame(1, "s", _Scene(30, start=0)), 30.0)
        # fps_base is honoured (24/1.001 ~= 23.976 fps).
        self.assertAlmostEqual(to_frame(1, "s", _Scene(24, base=1.001, start=0)),
                               24.0 / 1.001)

    def test_frame_origin(self):
        scene = _Scene(24, start=1)          # scene start frame is the origin
        self.assertAlmostEqual(to_frame(1, "s", scene), 25.0)
        self.assertAlmostEqual(from_frame(25, "s", scene), 1.0)
        # explicit origin overrides
        self.assertAlmostEqual(to_frame(1, "s", scene, origin=0), 24.0)

    def test_default_unit_and_no_scene(self):
        self.assertAlmostEqual(to_frame(2, None), 48.0)   # 2 s at default 24 fps, origin 0


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
