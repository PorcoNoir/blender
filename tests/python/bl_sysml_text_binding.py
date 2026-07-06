# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Text <-> tree binding + on-demand round-trip (BSML4 / SCRUM-667).

Binding links a Text datablock and its node tree both ways; syncing to text
updates the bound datablock, syncing from text re-parses into the bound tree, and
the binding survives .blend save/reload. The sync-from-text direction needs
sml2c (import), so it soft-skips; the rest run without it.
"""

import os
import sys
import tempfile
import unittest

import bpy

from bl_ui import sysml_text
from bl_ui import sysml_diagnostics

TREE_IDNAME = "SysMLNodeTree"


def _build_tree(name="Widget"):
    tree = bpy.data.node_groups.new(name, TREE_IDNAME)
    eng = tree.nodes.new("SysMLNodePartDef"); eng.element_name = "Engine"
    car = tree.nodes.new("SysMLNodePartDef"); car.element_name = "Car"
    e = tree.nodes.new("SysMLNodePartUsage"); e.element_name = "e"
    tree.links.new(eng.outputs["Self"], e.inputs["Type"])
    tree.links.new(e.outputs["Self"], car.inputs["Members"])
    return tree


class SysMLTextBindingTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.tree = _build_tree()

    def test_bind_links_both_ways(self):
        text = bpy.data.texts.new("Widget.sysml")
        sysml_text.bind_text(self.tree, text)
        self.assertEqual(sysml_text.bound_text(self.tree), text)
        self.assertEqual(sysml_text.bound_tree(text), self.tree)

    def test_unbind_clears(self):
        text = bpy.data.texts.new("Widget.sysml")
        sysml_text.bind_text(self.tree, text)
        sysml_text.unbind_text(self.tree)
        self.assertIsNone(sysml_text.bound_text(self.tree))
        self.assertIsNone(sysml_text.bound_tree(text))

    def test_sync_to_text_updates_bound_datablock(self):
        text = bpy.data.texts.new("Widget.sysml")
        sysml_text.bind_text(self.tree, text)
        sysml_text.sync_to_text(self.tree)
        self.assertIn("Engine", text.as_string())
        # A graph edit reflected on the next sync (same datablock).
        w = self.tree.nodes.new("SysMLNodePartDef"); w.element_name = "Wheel"
        sysml_text.sync_to_text(self.tree)
        self.assertIn("Wheel", text.as_string())
        self.assertEqual(len([t for t in bpy.data.texts if t.name == "Widget.sysml"]), 1)

    def test_bind_operator_serializes_when_no_text(self):
        self.assertEqual(bpy.ops.node.sysml_bind_text(tree_name="Widget"), {'FINISHED'})
        text = sysml_text.bound_text(self.tree)
        self.assertIsNotNone(text)
        self.assertEqual(text.name, "Widget.sysml")

    def test_binding_survives_save_reload(self):
        text = bpy.data.texts.new("Widget.sysml")
        sysml_text.bind_text(self.tree, text)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "bind.blend")
            bpy.ops.wm.save_as_mainfile(filepath=path)
            bpy.ops.wm.open_mainfile(filepath=path)
        tree = bpy.data.node_groups.get("Widget")
        text = bpy.data.texts.get("Widget.sysml")
        self.assertIsNotNone(sysml_text.bound_text(tree))
        self.assertEqual(sysml_text.bound_tree(text), tree)

    @unittest.skipUnless(sysml_diagnostics.available(), "sml2c binary not available next to blender")
    def test_sync_from_text_updates_bound_tree(self):
        text = bpy.data.texts.new("Widget.sysml")
        text.write("package Demo {\n    part def Engine;\n    part def Truck;\n}\n")
        sysml_text.bind_text(self.tree, text)
        new_tree = sysml_text.sync_from_text(text)
        # Content came from the text; name + binding preserved.
        self.assertEqual(new_tree.name, "Widget")
        self.assertEqual(sysml_text.bound_tree(text), new_tree)
        names = {n.element_name for n in new_tree.nodes if n.element_name}
        self.assertIn("Truck", names)
        # Idempotent: syncing again keeps one "Widget" tree.
        sysml_text.sync_from_text(text)
        self.assertEqual(len([t for t in bpy.data.node_groups
                              if t.name == "Widget" and t.bl_idname == TREE_IDNAME]), 1)


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
