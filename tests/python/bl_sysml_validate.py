# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Diagnostics on nodes — badges + panel + validate operator (BSML4 / SCRUM-664).

Validating marks the offending node and records the finding for the panel; a
clean graph clears both; re-validating is idempotent; the jump-to-node operator
selects the node. Node-attribution is driven by the local structural checks, so
this runs without sml2c. Pure bpy.
"""

import json
import sys
import unittest

import bpy

from bl_ui import sysml_validate

TREE_IDNAME = "SysMLNodeTree"


class SysMLValidateTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.tree = bpy.data.node_groups.new("M", TREE_IDNAME)
        # Abstract PartDef A instantiated by usage b -> a structural error on b.
        self.a = self.tree.nodes.new("SysMLNodePartDef")
        self.a.element_name = "A"
        self.a.is_abstract = True
        self.b = self.tree.nodes.new("SysMLNodePartUsage")
        self.b.element_name = "b"
        self.tree.links.new(self.a.outputs["Self"], self.b.inputs["Type"])

    def _list(self):
        return json.loads(self.tree[sysml_validate.DIAG_LIST_KEY])

    def test_validate_marks_node_and_records_finding(self):
        sysml_validate.validate_tree(self.tree)
        # Offending node badged as an error with a message + custom colour.
        self.assertEqual(self.b[sysml_validate.DIAG_SEVERITY_KEY], "error")
        self.assertIn(sysml_validate.DIAG_MSG_KEY, self.b)
        self.assertTrue(self.b.use_custom_color)
        self.assertGreater(self.b.color[0], self.b.color[1])  # red-dominant
        # The clean node is untouched.
        self.assertNotIn(sysml_validate.DIAG_SEVERITY_KEY, self.a)
        # The finding is recorded on the tree for the panel.
        self.assertTrue(any(f["node"] == self.b.name and f["code"] == "B4001"
                            for f in self._list()))

    def test_fix_then_revalidate_clears(self):
        sysml_validate.validate_tree(self.tree)
        self.assertIn(sysml_validate.DIAG_SEVERITY_KEY, self.b)
        self.a.is_abstract = False  # fix the model
        sysml_validate.validate_tree(self.tree)
        self.assertNotIn(sysml_validate.DIAG_SEVERITY_KEY, self.b)
        self.assertFalse(self.b.use_custom_color)
        self.assertEqual([f for f in self._list() if f["severity"] == "error"], [])

    def test_revalidate_is_idempotent(self):
        sysml_validate.validate_tree(self.tree)
        first = len(self._list())
        sysml_validate.validate_tree(self.tree)
        self.assertEqual(len(self._list()), first)
        self.assertEqual(self.b[sysml_validate.DIAG_SEVERITY_KEY], "error")

    def test_jump_to_node_selects(self):
        sysml_validate.validate_tree(self.tree)
        self.a.select = True
        self.assertEqual(
            bpy.ops.node.sysml_diag_select(tree_name=self.tree.name, node_name=self.b.name),
            {'FINISHED'})
        self.assertTrue(self.b.select)
        self.assertFalse(self.a.select)
        self.assertEqual(self.tree.nodes.active, self.b)

    def test_operator_and_panel_registered(self):
        self.assertEqual(bpy.ops.node.sysml_validate.idname(), "NODE_OT_sysml_validate")
        self.assertEqual(bpy.ops.node.sysml_validate(tree_name=self.tree.name), {'FINISHED'})
        self.assertTrue(hasattr(bpy.types, "NODE_PT_sysml_diagnostics"))


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
