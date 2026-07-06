# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Node <-> armature bone binding (Animation Binding A / SCRUM-646).

Bind a SysML part node to a bone, look it up both ways, round-trip through a
.blend save/reload, and confirm deleting the armature or the tree clears the
binding with no dangling reference. Pure bpy.
"""

import os
import sys
import tempfile
import unittest

import bpy

from bl_ui import sysml_bone_binding as bb

TREE_IDNAME = "SysMLNodeTree"


def _armature_with_bone(name="Rig", bone_name="Bone"):
    arm_data = bpy.data.armatures.new(name)
    arm = bpy.data.objects.new(name, arm_data)
    bpy.context.scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm_data.edit_bones.new(bone_name)
    eb.head = (0.0, 0.0, 0.0)
    eb.tail = (0.0, 0.0, 1.0)
    bpy.ops.object.mode_set(mode='OBJECT')
    return arm, arm_data.bones[bone_name]


class SysMLBoneBindingTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.tree = bpy.data.node_groups.new("Rig", TREE_IDNAME)
        self.node = self.tree.nodes.new("SysMLNodePartUsage")
        self.node.element_name = "UpperArm"

    def test_bind_and_lookup_both_ways(self):
        arm, bone = _armature_with_bone()
        bb.bind_bone(self.node, arm, bone)
        self.assertTrue(bb.is_bone_bound(arm, bone))
        self.assertEqual(bb.node_for_bone(arm, bone), self.node)
        self.assertEqual(bb.bone_for_node(self.node), (arm, bone))
        self.assertEqual([n.name for _, _, n in bb.bound_bones(self.tree)], [self.node.name])

    def test_survives_save_reload(self):
        arm, bone = _armature_with_bone()
        bb.bind_bone(self.node, arm, bone)
        blend = os.path.join(tempfile.mkdtemp(), "rig.blend")
        bpy.ops.wm.save_as_mainfile(filepath=blend)
        bpy.ops.wm.open_mainfile(filepath=blend)

        arm = bpy.data.objects["Rig"]
        bone = arm.data.bones["Bone"]
        node = bb.node_for_bone(arm, bone)
        self.assertIsNotNone(node)
        self.assertEqual(node.element_name, "UpperArm")

    def test_armature_delete_clears(self):
        arm, bone = _armature_with_bone()
        bb.bind_bone(self.node, arm, bone)
        bpy.data.objects.remove(arm)
        self.assertIsNone(bb.bone_for_node(self.node))
        self.assertEqual(list(bb.bound_bones(self.tree)), [])

    def test_tree_delete_clears(self):
        arm, bone = _armature_with_bone()
        bb.bind_bone(self.node, arm, bone)
        bpy.data.node_groups.remove(self.tree)
        self.assertIsNone(arm.get(bb.ARM_TREE_KEY))
        self.assertIsNone(bb.node_for_bone(arm, bone))

    def test_bone_marker_on_node(self):
        self.node[bb.BONE_KEY] = 1
        self.node[bb.BONE_HEAD_KEY] = (0.0, 0.0, 0.0)
        self.node[bb.BONE_TAIL_KEY] = (0.0, 0.0, 1.0)
        self.assertTrue(bb.is_bone_part(self.node))
        self.assertEqual(tuple(self.node[bb.BONE_TAIL_KEY]), (0.0, 0.0, 1.0))


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
