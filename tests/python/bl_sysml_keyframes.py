# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Occurrence snapshots -> bone pose keyframes (Animation Binding A / SCRUM-649).

A bone-part with snapshots at t0/t1 keyframes its bound pose bone at the frames
those clock times map to (via the time bridge), with the snapshot transforms.
Checks the frames, the keyframed values, the animation range, and that
re-animating replaces rather than stacks the keyframes. Pure bpy.
"""

import json
import sys
import unittest

import bpy

from bl_ui import sysml_animate
from bl_ui.sysml_bone_binding import BONE_KEY, BONE_HEAD_KEY, BONE_TAIL_KEY
from bl_ui.sysml_time import TIME_UNIT_KEY

TREE_IDNAME = "SysMLNodeTree"


class SysMLKeyframeTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene = bpy.context.scene
        self.scene.frame_start = 1  # time 0 -> frame 1 (origin); 24 fps
        self.tree = bpy.data.node_groups.new("Arm", TREE_IDNAME)
        self.root = self.tree.nodes.new("SysMLNodePartUsage")
        self.root.element_name = "Root"
        self.root[BONE_KEY] = 1
        self.root[BONE_HEAD_KEY] = (0.0, 0.0, 0.0)
        self.root[BONE_TAIL_KEY] = (0.0, 0.0, 1.0)
        self.root[TIME_UNIT_KEY] = "s"
        self.root[sysml_animate.SNAPSHOTS_KEY] = json.dumps([
            {"t": 0.0, "loc": [0.0, 0.0, 0.0], "rot": [1.0, 0.0, 0.0, 0.0]},
            {"t": 1.0, "loc": [0.0, 0.0, 1.0], "rot": [1.0, 0.0, 0.0, 0.0]},
        ])

    def _action(self):
        arm = sysml_animate.sysml_armature._find_rig_armature(self.tree)
        self.assertIsNotNone(arm.animation_data)
        return arm, arm.animation_data.action

    @staticmethod
    def _fcurves(action):
        # Blender 5.x slotted actions keep fcurves under layers/strips/channelbags.
        if hasattr(action, "fcurves"):
            return list(action.fcurves)
        out = []
        for layer in action.layers:
            for strip in layer.strips:
                for cbag in strip.channelbags:
                    out.extend(cbag.fcurves)
        return out

    def _fcurve(self, action, path, index):
        for fc in self._fcurves(action):
            if fc.data_path == path and fc.array_index == index:
                return fc
        return None

    def test_snapshots_become_keyframes(self):
        applied = sysml_animate.keyframe_tree(self.tree, self.scene)
        self.assertEqual(applied, 2)

        _, action = self._action()
        loc_z = self._fcurve(action, 'pose.bones["Root"].location', 2)
        self.assertIsNotNone(loc_z)
        frames = sorted(round(kp.co.x) for kp in loc_z.keyframe_points)
        self.assertEqual(frames, [1, 25])  # t=0 -> 1, t=1 s * 24 fps -> 25
        # Value at the later frame is the snapshot's z translation.
        at_25 = next(kp for kp in loc_z.keyframe_points if round(kp.co.x) == 25)
        self.assertAlmostEqual(at_25.co.y, 1.0, places=4)
        # Rotation was keyframed too.
        self.assertIsNotNone(self._fcurve(action, 'pose.bones["Root"].rotation_quaternion', 0))

    def test_snapshot_span_sets_range(self):
        sysml_animate.keyframe_tree(self.tree, self.scene)
        self.assertEqual(self.scene.frame_start, 1)
        self.assertEqual(self.scene.frame_end, 25)

    def test_reanimate_replaces_not_stacks(self):
        sysml_animate.keyframe_tree(self.tree, self.scene)
        _, action = self._action()
        first = sum(len(fc.keyframe_points) for fc in self._fcurves(action))
        sysml_animate.keyframe_tree(self.tree, self.scene)
        _, action = self._action()
        again = sum(len(fc.keyframe_points) for fc in self._fcurves(action))
        self.assertEqual(again, first)

    def test_operator_rigs_and_animates(self):
        self.assertEqual(bpy.ops.node.sysml_animate(tree_name=self.tree.name), {'FINISHED'})
        arm = sysml_animate.sysml_armature._find_rig_armature(self.tree)
        self.assertIsNotNone(arm)
        self.assertIn("Root", arm.pose.bones)
        self.assertIsNotNone(arm.animation_data.action)


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
