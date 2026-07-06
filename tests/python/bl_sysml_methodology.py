# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Guided rigging/animation methodology (Animation Binding B / SCRUM-654).

Each methodology action produces valid SysML *and* the matching Blender rig /
animation in one step: an add-bone-chain template, build-IK-from-connection, and
keyframe-pose. Operators are RNA-visible and the menu is registered. Pure bpy.
"""

import json
import sys
import unittest

import bpy

from bl_ui import sysml_methodology
from bl_ui.sysml_armature import rig_tree, CONSTRAINT_KEY, _find_rig_armature
from bl_ui.sysml_animate import keyframe_tree, SNAPSHOTS_KEY
from bl_ui.sysml_bone_binding import (
    BONE_KEY, BONE_HEAD_KEY, BONE_TAIL_KEY,
)
from bl_ui.sysml_time import TIME_UNIT_KEY

TREE_IDNAME = "SysMLNodeTree"


class SysMLMethodologyTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene = bpy.context.scene
        self.scene.frame_start = 1
        self.tree = bpy.data.node_groups.new("Rig", TREE_IDNAME)

    def _node(self, name):
        return next((n for n in self.tree.nodes if n.element_name == name), None)

    # -- add bone chain ------------------------------------------------------

    def test_add_bone_chain_builds_graph_and_rig(self):
        nodes = sysml_methodology.add_bone_chain(self.tree, count=3, length=1.0)
        self.assertEqual([n.element_name for n in nodes], ["Bone1", "Bone2", "Bone3"])
        # Containment chain in the graph.
        b1, b2 = self._node("Bone1"), self._node("Bone2")
        members = [l for l in self.tree.links
                   if l.to_node == b1 and l.to_socket.identifier == "members"]
        self.assertEqual([l.from_node for l in members], [b2])
        # Parented bone chain in the armature with stacked rest transforms.
        arm = _find_rig_armature(self.tree)
        self.assertEqual({b.name for b in arm.data.bones}, {"Bone1", "Bone2", "Bone3"})
        self.assertEqual(arm.data.bones["Bone2"].parent, arm.data.bones["Bone1"])
        self.assertEqual(arm.data.bones["Bone3"].parent, arm.data.bones["Bone2"])
        self.assertEqual(tuple(round(v, 3) for v in arm.data.bones["Bone2"].head_local),
                         (0.0, 0.0, 1.0))

    def test_add_bone_chain_operator(self):
        self.assertEqual(
            bpy.ops.node.sysml_add_bone_chain(tree_name=self.tree.name, count=2),
            {'FINISHED'})
        self.assertEqual(len([n for n in self.tree.nodes if n.get(BONE_KEY)]), 2)
        self.assertEqual(len(_find_rig_armature(self.tree).data.bones), 2)

    # -- build IK ------------------------------------------------------------

    def test_build_ik_from_connection(self):
        for name, head, tail in (("A", (0, 0, 0), (0, 0, 1)), ("B", (0, 1, 1), (0, 1, 2))):
            n = self.tree.nodes.new("SysMLNodePartUsage")
            n.element_name = name
            n[BONE_KEY] = 1
            n[BONE_HEAD_KEY] = tuple(float(v) for v in head)
            n[BONE_TAIL_KEY] = tuple(float(v) for v in tail)
        conn = self.tree.nodes.new("SysMLNodeConnectionUsage")
        conn.element_name = "Joint"
        self.tree.links.new(self._node("A").outputs["Self"], conn.inputs["Connect"])
        self.tree.links.new(self._node("B").outputs["Self"], conn.inputs["To"])

        sysml_methodology.build_ik(self.tree, conn)
        self.assertEqual(conn[CONSTRAINT_KEY], "IK")
        arm = _find_rig_armature(self.tree)
        cons = arm.pose.bones["A"].constraints
        self.assertEqual([c.type for c in cons], ['IK'])
        self.assertEqual(cons[0].subtarget, "B")

    # -- keyframe pose -------------------------------------------------------

    def test_keyframe_pose_snapshots_and_keys(self):
        root = self.tree.nodes.new("SysMLNodePartUsage")
        root.element_name = "Root"
        root[BONE_KEY] = 1
        root[BONE_HEAD_KEY] = (0.0, 0.0, 0.0)
        root[BONE_TAIL_KEY] = (0.0, 0.0, 1.0)
        root[TIME_UNIT_KEY] = "s"
        root[SNAPSHOTS_KEY] = json.dumps([{"t": 0.0, "loc": [0, 0, 0]}])
        rig_tree(self.tree)
        keyframe_tree(self.tree, self.scene)

        self.scene.frame_current = 13  # -> t = 0.5 s at 24 fps
        arm = _find_rig_armature(self.tree)
        arm.pose.bones["Root"].location = (0.0, 0.0, 2.0)
        n = sysml_methodology.keyframe_pose(self.tree, self.scene)
        self.assertEqual(n, 1)

        snaps = json.loads(self._node("Root")[SNAPSHOTS_KEY])
        late = next(s for s in snaps if round(s["t"], 3) == 0.5)
        self.assertAlmostEqual(late["loc"][2], 2.0, places=3)
        # And the rig gained the matching keyframe.
        from bl_ui.sysml_capture import _action_fcurves
        fc = next(f for f in _action_fcurves(arm.animation_data.action)
                  if f.data_path == 'pose.bones["Root"].location' and f.array_index == 2)
        self.assertAlmostEqual(fc.evaluate(13), 2.0, places=3)

    # -- discoverability -----------------------------------------------------

    def test_operators_and_menu_registered(self):
        self.assertEqual(bpy.ops.node.sysml_add_bone_chain.idname(), "NODE_OT_sysml_add_bone_chain")
        self.assertEqual(bpy.ops.node.sysml_build_ik.idname(), "NODE_OT_sysml_build_ik")
        self.assertEqual(bpy.ops.node.sysml_keyframe_pose.idname(), "NODE_OT_sysml_keyframe_pose")
        self.assertTrue(hasattr(bpy.types, "NODE_MT_sysml_methodology"))


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
