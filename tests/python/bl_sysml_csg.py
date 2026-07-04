# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""CSG -> Boolean modifiers (Geometry Binding A / SCRUM-628).

Materializes the engine-block case from the standard library's CSG example — a
Cuboid block with two Cylinder holes (difference) — and checks the block object
gets a Boolean-DIFFERENCE modifier per cutter, the cutters are hidden and grouped
under the result, and re-running does not stack duplicate modifiers. Also checks
the union/intersect operation mapping. Pure bpy — no sml2c needed.
"""

import sys
import unittest

import bpy

from bl_ui import sysml_geometry
from bl_ui.sysml_binding import object_for_node

TREE_IDNAME = "SysMLNodeTree"


class SysMLCsgTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.tree = bpy.data.node_groups.new("Engine", TREE_IDNAME)

    def _shape(self, kind, name, node_type="SysMLNodePartUsage", **dims):
        node = self.tree.nodes.new(node_type)
        node.element_name = name
        node["sysml_shape"] = kind
        for attr, value in dims.items():
            node["sysml_dim_" + attr] = float(value)
        return node

    def _engine(self, op="difference"):
        block = self._shape("Cuboid", "Block", node_type="SysMLNodePartDef",
                            length=4, width=4, height=4)
        block["sysml_csg"] = op
        block["sysml_csg_operands"] = "Cut1,Cut2"
        for name in ("Cut1", "Cut2"):
            cut = self._shape("Cylinder", name, radius=1, height=6)
            self.tree.links.new(cut.outputs["Self"], block.inputs["Members"])
        return block

    def test_difference_makes_two_holes(self):
        block = self._engine("difference")
        sysml_geometry.materialize_tree(self.tree)

        obj = object_for_node(block)
        booleans = [m for m in obj.modifiers if m.type == 'BOOLEAN']
        self.assertEqual(len(booleans), 2, "expected one boolean per cutter")
        for mod in booleans:
            self.assertEqual(mod.operation, 'DIFFERENCE')
            self.assertIsNotNone(mod.object)
        targets = {m.object.name for m in booleans}
        for name in ("Cut1", "Cut2"):
            cut = object_for_node(next(n for n in self.tree.nodes if n.element_name == name))
            self.assertIn(cut.name, targets)
            self.assertTrue(cut.hide_viewport and cut.hide_render, f"{name} should be hidden")
            self.assertEqual(cut.parent, obj, f"{name} should be grouped under the result")

    def test_rerun_does_not_stack_modifiers(self):
        self._engine("difference")
        sysml_geometry.materialize_tree(self.tree)
        sysml_geometry.materialize_tree(self.tree)
        obj = object_for_node(next(n for n in self.tree.nodes if n.element_name == "Block"))
        self.assertEqual(len([m for m in obj.modifiers if m.type == 'BOOLEAN']), 2)

    def test_operation_mapping(self):
        for op, expect in (("union", 'UNION'), ("intersect", 'INTERSECT')):
            with self.subTest(op=op):
                bpy.ops.wm.read_factory_settings(use_empty=True)
                self.tree = bpy.data.node_groups.new("E", TREE_IDNAME)
                block = self._engine(op)
                sysml_geometry.materialize_tree(self.tree)
                obj = object_for_node(block)
                ops = {m.operation for m in obj.modifiers if m.type == 'BOOLEAN'}
                self.assertEqual(ops, {expect})


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
