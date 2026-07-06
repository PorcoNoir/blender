# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Connections -> bone constraints (Animation Binding A / SCRUM-648).

A SysML ConnectionUsage between two bone-parts becomes a pose-bone constraint:
its connect/from end owns the constraint and its `to` end is the target bone.
Checks the constraint type, target, and subtarget; the fallback to a default
type; and that re-rigging does not stack duplicate constraints. Pure bpy.
"""

import sys
import unittest

import bpy

from bl_ui import sysml_armature
from bl_ui.sysml_bone_binding import BONE_KEY, BONE_HEAD_KEY, BONE_TAIL_KEY

TREE_IDNAME = "SysMLNodeTree"


class SysMLConstraintTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.tree = bpy.data.node_groups.new("Arm", TREE_IDNAME)
        self.fore = self._bone("Forearm", (0, 0, 0), (0, 0, 2))
        self.target = self._bone("IKTarget", (0, 1, 2), (0, 1, 3))

    def _bone(self, name, head, tail):
        node = self.tree.nodes.new("SysMLNodePartUsage")
        node.element_name = name
        node[BONE_KEY] = 1
        node[BONE_HEAD_KEY] = tuple(float(v) for v in head)
        node[BONE_TAIL_KEY] = tuple(float(v) for v in tail)
        return node

    def _connect(self, name, ctype, owner, target):
        conn = self.tree.nodes.new("SysMLNodeConnectionUsage")
        conn.element_name = name
        conn[sysml_armature.CONSTRAINT_KEY] = ctype
        self.tree.links.new(owner.outputs["Self"], conn.inputs["Connect"])
        self.tree.links.new(target.outputs["Self"], conn.inputs["To"])
        return conn

    def _forearm_constraints(self):
        arm = sysml_armature._find_rig_armature(self.tree)
        return arm, list(arm.pose.bones["Forearm"].constraints)

    def test_ik_connection_becomes_ik_constraint(self):
        self._connect("Wrist", "IK", self.fore, self.target)
        sysml_armature.rig_tree(self.tree)

        arm, cons = self._forearm_constraints()
        self.assertEqual(len(cons), 1)
        con = cons[0]
        self.assertEqual(con.type, 'IK')
        self.assertEqual(con.name, "SysML Wrist")
        self.assertEqual(con.target, arm)
        self.assertEqual(con.subtarget, "IKTarget")
        # The target bone itself carries no constraint.
        self.assertEqual(len(arm.pose.bones["IKTarget"].constraints), 0)

    def test_default_type_for_unknown_kind(self):
        self._connect("Joint", "NOT_A_REAL_TYPE", self.fore, self.target)
        sysml_armature.rig_tree(self.tree)
        _, cons = self._forearm_constraints()
        self.assertEqual([c.type for c in cons], [sysml_armature.DEFAULT_CONSTRAINT])

    def test_copy_transforms_connection(self):
        self._connect("Weld", "COPY_TRANSFORMS", self.fore, self.target)
        sysml_armature.rig_tree(self.tree)
        _, cons = self._forearm_constraints()
        self.assertEqual([c.type for c in cons], ['COPY_TRANSFORMS'])

    def test_rerig_does_not_duplicate_constraints(self):
        self._connect("Wrist", "IK", self.fore, self.target)
        sysml_armature.rig_tree(self.tree)
        sysml_armature.rig_tree(self.tree)
        _, cons = self._forearm_constraints()
        self.assertEqual(len(cons), 1)


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
