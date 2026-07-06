# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Live sync engine: graph <-> armature/animation (Animation Binding B /
SCRUM-653).

Drives the sync engine's logic directly (depsgraph/msgbus don't fire reliably
headless): a keyframe move or a rest edit pulls into the graph; a graph edit
pushes into the rig; the per-tree enable, per-binding link flag, reentrancy
guard, and dirty/flush cycle all gate correctly. Pure bpy.
"""

import json
import sys
import unittest

import bpy

from bl_ui import sysml_sync
from bl_ui.sysml_armature import rig_tree, _find_rig_armature
from bl_ui.sysml_animate import keyframe_tree, SNAPSHOTS_KEY
from bl_ui.sysml_capture import _action_fcurves
from bl_ui.sysml_bone_binding import BONE_KEY, BONE_HEAD_KEY, BONE_TAIL_KEY
from bl_ui.sysml_time import TIME_UNIT_KEY

TREE_IDNAME = "SysMLNodeTree"


def _bone_node(tree, name, tail_z, snap_z):
    node = tree.nodes.new("SysMLNodePartUsage")
    node.element_name = name
    node[BONE_KEY] = 1
    node[BONE_HEAD_KEY] = (0.0, 0.0, 0.0)
    node[BONE_TAIL_KEY] = (0.0, 0.0, float(tail_z))
    node[TIME_UNIT_KEY] = "s"
    node[SNAPSHOTS_KEY] = json.dumps(
        [{"t": 0.0, "loc": [0, 0, 0]}, {"t": 1.0, "loc": [0, 0, snap_z]}])
    return node


def _move_key(arm, bone_name, frame, new_z):
    fc = next(f for f in _action_fcurves(arm.animation_data.action)
              if f.data_path == 'pose.bones["{}"].location'.format(bone_name)
              and f.array_index == 2)
    kp = next(k for k in fc.keyframe_points if round(k.co.x) == frame)
    kp.co.y = new_z
    fc.update()


class SysMLSyncTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene = bpy.context.scene
        self.scene.frame_start = 1
        # Reset engine module state between tests.
        sysml_sync._SYNCING = False
        sysml_sync._dirty_pull.clear()
        sysml_sync._dirty_push.clear()

        self.tree = bpy.data.node_groups.new("Arm", TREE_IDNAME)
        self.upper = _bone_node(self.tree, "UpperArm", 2, 1)
        self.fore = _bone_node(self.tree, "Forearm", 4, 1)
        rig_tree(self.tree)
        keyframe_tree(self.tree, self.scene)
        self.arm = _find_rig_armature(self.tree)

    def _snap_z(self, node):
        return json.loads(node[SNAPSHOTS_KEY])[1]["loc"][2]

    # -- pull (blender -> graph) --------------------------------------------

    def test_pull_reflects_keyframe_move(self):
        _move_key(self.arm, "UpperArm", 25, 2.0)
        n = sysml_sync.sync_pull(self.tree)
        self.assertEqual(n, 2)
        self.assertAlmostEqual(self._snap_z(self.upper), 2.0, places=3)

    def test_pull_reflects_rest_edit(self):
        bpy.context.view_layer.objects.active = self.arm
        bpy.ops.object.mode_set(mode='EDIT')
        self.arm.data.edit_bones["UpperArm"].tail = (0.0, 0.0, 5.0)
        bpy.ops.object.mode_set(mode='OBJECT')
        sysml_sync.sync_pull(self.tree)
        self.assertAlmostEqual(self.upper[BONE_TAIL_KEY][2], 5.0, places=3)

    def test_unlinked_binding_inert(self):
        before = dict(json.loads(self.upper[SNAPSHOTS_KEY])[1])
        sysml_sync.set_linked(self.upper, False)
        _move_key(self.arm, "UpperArm", 25, 3.0)
        _move_key(self.arm, "Forearm", 25, 3.0)
        sysml_sync.sync_pull(self.tree)
        # Unlinked node untouched; linked node updated.
        self.assertEqual(json.loads(self.upper[SNAPSHOTS_KEY])[1]["loc"][2], before["loc"][2])
        self.assertAlmostEqual(self._snap_z(self.fore), 3.0, places=3)

    # -- push (graph -> blender) --------------------------------------------

    def test_push_updates_rig(self):
        self.upper[SNAPSHOTS_KEY] = json.dumps(
            [{"t": 0.0, "loc": [0, 0, 0]}, {"t": 1.0, "loc": [0, 0, 4]}])
        sysml_sync.sync_push(self.tree)
        fc = next(f for f in _action_fcurves(self.arm.animation_data.action)
                  if f.data_path == 'pose.bones["UpperArm"].location' and f.array_index == 2)
        self.assertAlmostEqual(fc.evaluate(25), 4.0, places=3)

    # -- gating: enable / guard / dirty-flush -------------------------------

    def test_disabled_tree_not_marked(self):
        sysml_sync.set_sync(self.tree, False)
        sysml_sync._note_updated_ids({self.arm})
        self.assertNotIn(self.tree.name, sysml_sync._dirty_pull)

    def test_enabled_tree_marked_and_flushed(self):
        sysml_sync.set_sync(self.tree, True, sysml_sync.SOURCE_BLENDER)
        _move_key(self.arm, "UpperArm", 25, 2.5)
        sysml_sync._note_updated_ids({self.arm})
        self.assertIn(self.tree.name, sysml_sync._dirty_pull)
        sysml_sync._flush_pull()
        self.assertEqual(sysml_sync._dirty_pull, set())
        self.assertAlmostEqual(self._snap_z(self.upper), 2.5, places=3)

    def test_guard_blocks_handler(self):
        # While a flush is in progress, the depsgraph handler must no-op before
        # ever touching the (here deliberately invalid) depsgraph argument.
        with sysml_sync._guard():
            sysml_sync._on_depsgraph(None, None)  # must not raise
        self.assertEqual(sysml_sync._dirty_pull, set())

    def test_graph_source_marks_push(self):
        sysml_sync.set_sync(self.tree, True, sysml_sync.SOURCE_GRAPH)
        sysml_sync._note_graph_dirty(self.tree.name)
        self.assertIn(self.tree.name, sysml_sync._dirty_push)
        self.upper[SNAPSHOTS_KEY] = json.dumps(
            [{"t": 0.0, "loc": [0, 0, 0]}, {"t": 1.0, "loc": [0, 0, 6]}])
        sysml_sync._flush_push()
        fc = next(f for f in _action_fcurves(self.arm.animation_data.action)
                  if f.data_path == 'pose.bones["UpperArm"].location' and f.array_index == 2)
        self.assertAlmostEqual(fc.evaluate(25), 6.0, places=3)

    # -- install / operator --------------------------------------------------

    def test_install_is_idempotent(self):
        sysml_sync.install()
        sysml_sync.install()
        handlers = bpy.app.handlers.depsgraph_update_post
        self.assertEqual(sum(1 for h in handlers if h is sysml_sync._on_depsgraph), 1)

    def test_operator_toggles_enable(self):
        self.assertEqual(
            bpy.ops.node.sysml_sync(enable=True, source=sysml_sync.SOURCE_GRAPH,
                                    tree_name=self.tree.name),
            {'FINISHED'})
        self.assertTrue(sysml_sync.is_enabled(self.tree))
        self.assertEqual(sysml_sync.source_of_truth(self.tree), sysml_sync.SOURCE_GRAPH)
        bpy.ops.node.sysml_sync(enable=False, tree_name=self.tree.name)
        self.assertFalse(sysml_sync.is_enabled(self.tree))


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
