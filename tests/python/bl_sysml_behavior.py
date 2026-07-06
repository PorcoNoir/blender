# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""SysML behavior -> Actions / NLA strips (Animation Binding A / SCRUM-650).

Two states chained by a succession produce two Blender Actions, laid as ordered,
non-overlapping NLA strips on one track. Checks the Actions, the strip order, and
that re-running updates rather than duplicating. Pure bpy.
"""

import json
import sys
import unittest

import bpy

from bl_ui import sysml_behavior
from bl_ui.sysml_bone_binding import BONE_KEY, BONE_HEAD_KEY, BONE_TAIL_KEY
from bl_ui.sysml_time import TIME_UNIT_KEY

TREE_IDNAME = "SysMLNodeTree"


class SysMLBehaviorTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene = bpy.context.scene
        self.scene.frame_start = 1
        self.tree = bpy.data.node_groups.new("Arm", TREE_IDNAME)

        root = self.tree.nodes.new("SysMLNodePartUsage")
        root.element_name = "Root"
        root[BONE_KEY] = 1
        root[BONE_HEAD_KEY] = (0.0, 0.0, 0.0)
        root[BONE_TAIL_KEY] = (0.0, 0.0, 1.0)

        self._state("Idle", [{"t": 0.0, "loc": [0, 0, 0]}, {"t": 0.5, "loc": [0, 0, 0]}])
        self._state("Wave", [{"t": 0.0, "loc": [0, 0, 0]}, {"t": 0.5, "loc": [0, 0, 1]}])
        self._succession("Idle", "Wave")

    def _state(self, name, root_snaps):
        node = self.tree.nodes.new("SysMLNodeStateUsage")
        node.element_name = name
        node[TIME_UNIT_KEY] = "s"
        node[sysml_behavior.POSES_KEY] = json.dumps({"Root": root_snaps})
        return node

    def _succession(self, src, dst):
        node = self.tree.nodes.new("SysMLNodeSuccessionUsage")
        node.element_name = f"{src}_to_{dst}"
        node[sysml_behavior.SUCC_FROM_KEY] = src
        node[sysml_behavior.SUCC_TO_KEY] = dst
        return node

    def _track(self):
        arm = sysml_behavior.sysml_armature._find_rig_armature(self.tree)
        for t in arm.animation_data.nla_tracks:
            if t.name == sysml_behavior.NLA_TRACK_NAME:
                return t
        return None

    def test_two_states_two_actions(self):
        sysml_behavior.build_behavior(self.tree, self.scene)
        names = {a.name for a in bpy.data.actions}
        self.assertIn("SysML State: Idle", names)
        self.assertIn("SysML State: Wave", names)

    def test_ordered_nonoverlapping_strips(self):
        count = sysml_behavior.build_behavior(self.tree, self.scene)
        self.assertEqual(count, 2)
        track = self._track()
        self.assertIsNotNone(track)
        strips = list(track.strips)
        self.assertEqual([s.action.name for s in strips],
                         ["SysML State: Idle", "SysML State: Wave"])
        # Idle precedes Wave and they do not overlap.
        self.assertLessEqual(strips[0].frame_end, strips[1].frame_start)
        self.assertEqual(int(strips[0].frame_start), 1)

    def test_rebuild_updates_not_duplicates(self):
        sysml_behavior.build_behavior(self.tree, self.scene)
        sysml_behavior.build_behavior(self.tree, self.scene)
        self.assertEqual(len(list(self._track().strips)), 2)
        n_state_actions = len([a for a in bpy.data.actions
                               if a.name.startswith(sysml_behavior.ACTION_PREFIX)])
        self.assertEqual(n_state_actions, 2)

    def test_operator_is_rna_visible(self):
        self.assertEqual(bpy.ops.node.sysml_behavior.idname(), "NODE_OT_sysml_behavior")
        self.assertEqual(bpy.ops.node.sysml_behavior(tree_name=self.tree.name), {'FINISHED'})
        self.assertIsNotNone(self._track())


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
