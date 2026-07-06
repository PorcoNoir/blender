# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""In-editor library browser (BSML5 / SCRUM-676).

Inserting a library type adds an attribute usage tagged with the qualified type
in one step; the operator + panel are registered; and the SysML the usage
represents resolves against the standard library. Resolution soft-skips without
sml2c.
"""

import sys
import unittest

import bpy

from bl_ui import sysml_library
from bl_ui import sysml_diagnostics

TREE_IDNAME = "SysMLNodeTree"


class SysMLLibraryTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.tree = bpy.data.node_groups.new("M", TREE_IDNAME)

    def test_insert_creates_typed_attribute(self):
        node = sysml_library.insert_library_element(self.tree, "ISQ", "LengthValue", "length")
        self.assertEqual(node.bl_idname, "SysMLNodeAttributeUsage")
        self.assertEqual(node.element_name, "length")
        self.assertEqual(node[sysml_library.LIB_TYPE_KEY], "ISQ::LengthValue")

    def test_default_element_name(self):
        node = sysml_library.insert_library_element(self.tree, "ScalarValues", "Real")
        self.assertEqual(node.element_name, "real")

    def test_operator_inserts(self):
        self.assertEqual(
            bpy.ops.node.sysml_insert_library_type(tree_name="M", lib_entry="ScalarValues::Real"),
            {'FINISHED'})
        typed = [n for n in self.tree.nodes
                 if n.get(sysml_library.LIB_TYPE_KEY) == "ScalarValues::Real"]
        self.assertEqual(len(typed), 1)

    def test_operator_and_panel_registered(self):
        self.assertEqual(bpy.ops.node.sysml_insert_library_type.idname(),
                         "NODE_OT_sysml_insert_library_type")
        self.assertTrue(hasattr(bpy.types, "NODE_PT_sysml_library"))

    @unittest.skipUnless(sysml_diagnostics.available(), "sml2c binary not available next to blender")
    def test_inserted_type_resolves(self):
        for pkg, typ in (("ISQ", "LengthValue"), ("ScalarValues", "Real"),
                         ("ShapeItems", "Cuboid")):
            node = sysml_library.insert_library_element(self.tree, pkg, typ)
            findings = sysml_diagnostics.diagnose_text(sysml_library.library_snippet(node))
            self.assertFalse(sysml_diagnostics.has_errors(findings), (pkg, typ, findings))


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
