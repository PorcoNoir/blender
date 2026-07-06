# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Rig SysML graph -> Blender armature (Animation Binding A / SCRUM-647).

Builds a small bone hierarchy (an upper-arm bone with a forearm child) from a
SysML graph, rigs it, and checks the armature has the bones with the right rest
transforms and parenting, each bound to its node, and that re-running does not
duplicate. Pure bpy.
"""

import sys
import unittest

import bpy

from bl_ui import sysml_armature
from bl_ui.sysml_bone_binding import (
    BONE_KEY, BONE_HEAD_KEY, BONE_TAIL_KEY, node_for_bone, bone_for_node,
)

TREE_IDNAME = "SysMLNodeTree"


class SysMLRigTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.tree = bpy.data.node_groups.new("Arm", TREE_IDNAME)
        self.upper = self._bone("UpperArm", (0, 0, 0), (0, 0, 2), node_type="SysMLNodePartDef")
        self.fore = self._bone("Forearm", (0, 0, 2), (0, 0, 4))
        # Forearm is contained by UpperArm -> bone parent.
        self.tree.links.new(self.fore.outputs["Self"], self.upper.inputs["Members"])

    def _bone(self, name, head, tail, node_type="SysMLNodePartUsage"):
        node = self.tree.nodes.new(node_type)
        node.element_name = name
        node[BONE_KEY] = 1
        node[BONE_HEAD_KEY] = tuple(float(v) for v in head)
        node[BONE_TAIL_KEY] = tuple(float(v) for v in tail)
        return node

    def test_rig_bones_transforms_parenting_binding(self):
        count = sysml_armature.rig_tree(self.tree)
        self.assertEqual(count, 2)

        arm = sysml_armature._find_rig_armature(self.tree)
        self.assertIsNotNone(arm)
        self.assertEqual(arm.type, "ARMATURE")
        self.assertEqual({b.name for b in arm.data.bones}, {"UpperArm", "Forearm"})

        upper_bone = arm.data.bones["UpperArm"]
        fore_bone = arm.data.bones["Forearm"]
        # Rest transforms.
        self.assertEqual(tuple(round(v, 3) for v in upper_bone.tail_local), (0.0, 0.0, 2.0))
        self.assertEqual(tuple(round(v, 3) for v in fore_bone.head_local), (0.0, 0.0, 2.0))
        # Parenting from containment.
        self.assertEqual(fore_bone.parent, upper_bone)
        # Bindings both ways.
        self.assertEqual(node_for_bone(arm, upper_bone), self.upper)
        self.assertEqual(bone_for_node(self.fore), (arm, fore_bone))

    def test_rerun_is_idempotent(self):
        sysml_armature.rig_tree(self.tree)
        n_arms = len([o for o in bpy.data.objects if o.type == 'ARMATURE'])
        sysml_armature.rig_tree(self.tree)
        self.assertEqual(len([o for o in bpy.data.objects if o.type == 'ARMATURE']), n_arms)
        arm = sysml_armature._find_rig_armature(self.tree)
        self.assertEqual(len(arm.data.bones), 2)

    def test_operator_is_rna_visible(self):
        self.assertEqual(bpy.ops.node.sysml_rig.idname(), "NODE_OT_sysml_rig")
        self.assertEqual(bpy.ops.node.sysml_rig(tree_name=self.tree.name), {'FINISHED'})
        self.assertIsNotNone(sysml_armature._find_rig_armature(self.tree))


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
