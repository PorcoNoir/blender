# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Animation Binding B exit gate — live-sync round-trip (SCRUM-655).

The phase-B acceptance gate: on a methodology-built rig with sync enabled, an
edit in either view reaches the other through the *full* engine pipeline
(dirty-mark -> debounced flush), the cycle converges (no oscillation), and the
per-tree source of truth structurally blocks the reverse direction (no loops).
Headless bpy; wired into the release workflow. Green here means the whole
Animation Binding feature is complete.
"""

import json
import sys
import unittest

import bpy

from bl_ui import sysml_sync as sync
from bl_ui import sysml_methodology as methodology
from bl_ui.sysml_armature import _find_rig_armature
from bl_ui.sysml_animate import keyframe_tree, SNAPSHOTS_KEY
from bl_ui.sysml_capture import _action_fcurves
from bl_ui.sysml_time import TIME_UNIT_KEY

TREE_IDNAME = "SysMLNodeTree"


def _fcurve(arm, bone, index):
    return next(f for f in _action_fcurves(arm.animation_data.action)
               if f.data_path == 'pose.bones["{}"].location'.format(bone)
               and f.array_index == index)


class AnimationBExitGate(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene = bpy.context.scene
        self.scene.frame_start = 1
        sync._SYNCING = False
        sync._dirty_pull.clear()
        sync._dirty_push.clear()

        # A methodology-built rig (proves methodology + sync compose).
        self.tree = bpy.data.node_groups.new("Rig", TREE_IDNAME)
        self.nodes = methodology.add_bone_chain(self.tree, count=2, length=1.0)
        self.nodes[0][TIME_UNIT_KEY] = "s"
        self.nodes[0][SNAPSHOTS_KEY] = json.dumps(
            [{"t": 0.0, "loc": [0, 0, 0]}, {"t": 1.0, "loc": [0, 0, 1]}])
        keyframe_tree(self.tree, self.scene)
        self.arm = _find_rig_armature(self.tree)

    def _snap_z(self, node):
        return json.loads(node[SNAPSHOTS_KEY])[1]["loc"][2]

    def _move_key(self, bone, frame, z):
        fc = _fcurve(self.arm, bone, 2)
        kp = next(k for k in fc.keyframe_points if round(k.co.x) == frame)
        kp.co.y = z
        fc.update()

    # -- Blender view -> graph, through the full pipeline --------------------

    def test_blender_edit_reaches_graph(self):
        sync.set_sync(self.tree, True, sync.SOURCE_BLENDER)
        self._move_key("Bone1", 25, 3.0)
        sync._note_updated_ids({self.arm})           # depsgraph would mark it
        self.assertIn(self.tree.name, sync._dirty_pull)
        sync._flush_pull()                           # debounced flush
        self.assertAlmostEqual(self._snap_z(self.nodes[0]), 3.0, places=3)
        # No loop kicked off: nothing queued for the reverse direction.
        self.assertEqual(sync._dirty_push, set())
        self.assertFalse(sync._SYNCING)

    # -- graph view -> Blender, through the full pipeline --------------------

    def test_graph_edit_reaches_blender(self):
        sync.set_sync(self.tree, True, sync.SOURCE_GRAPH)
        self.nodes[0][SNAPSHOTS_KEY] = json.dumps(
            [{"t": 0.0, "loc": [0, 0, 0]}, {"t": 1.0, "loc": [0, 0, 5]}])
        sync._note_graph_dirty(self.tree.name)
        sync._flush_push()
        self.assertAlmostEqual(_fcurve(self.arm, "Bone1", 2).evaluate(25), 5.0, places=3)
        self.assertEqual(sync._dirty_pull, set())
        self.assertFalse(sync._SYNCING)

    # -- convergence (no oscillation) ----------------------------------------

    def test_repeated_cycle_converges(self):
        sync.set_sync(self.tree, True, sync.SOURCE_BLENDER)
        self._move_key("Bone1", 25, 4.0)
        sync._note_updated_ids({self.arm})
        sync._flush_pull()
        first = self.nodes[0][SNAPSHOTS_KEY]
        # A second tick with nothing newly changed reproduces the same graph.
        sync._note_updated_ids({self.arm})
        sync._flush_pull()
        self.assertEqual(self.nodes[0][SNAPSHOTS_KEY], first)

    # -- source of truth is a structural loop guard --------------------------

    def test_source_blocks_reverse_direction(self):
        sync.set_sync(self.tree, True, sync.SOURCE_BLENDER)
        before = _fcurve(self.arm, "Bone1", 2).evaluate(25)
        # Even if a push is (wrongly) queued, a blender-source tree is never pushed.
        self.nodes[0][SNAPSHOTS_KEY] = json.dumps(
            [{"t": 0.0, "loc": [0, 0, 0]}, {"t": 1.0, "loc": [0, 0, 9]}])
        sync._note_graph_dirty(self.tree.name)
        sync._flush_push()
        self.assertAlmostEqual(_fcurve(self.arm, "Bone1", 2).evaluate(25), before, places=3)


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
