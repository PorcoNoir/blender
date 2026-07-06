# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Nodes -> SysML Text datablock (BSML4 / SCRUM-666).

Serializing a tree yields a Text datablock named after it; re-running updates the
same datablock. Native export needs no sml2c, so the serialize checks always run;
the full text -> nodes -> text round-trip soft-skips without sml2c.
"""

import sys
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
    tree.links.new(eng.outputs["Self"], e.inputs["Type"])       # e : Engine
    tree.links.new(e.outputs["Self"], car.inputs["Members"])    # Car contains e
    return tree


class SysMLNodesToTextTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.tree = _build_tree()

    def test_serialize_creates_named_text(self):
        text = sysml_text.nodes_to_text(self.tree)
        self.assertEqual(text.name, "Widget.sysml")
        body = text.as_string()
        self.assertIn("Engine", body)
        self.assertIn("Car", body)

    def test_reserialize_updates_same_text(self):
        first = sysml_text.nodes_to_text(self.tree)
        count = len(bpy.data.texts)
        body1 = first.as_string()
        second = sysml_text.nodes_to_text(self.tree)
        self.assertIs(second, first)                      # same datablock
        self.assertEqual(len(bpy.data.texts), count)      # not duplicated
        self.assertEqual(second.as_string(), body1)       # deterministic

    def test_operator(self):
        self.assertEqual(bpy.ops.node.sysml_nodes_to_text(tree_name="Widget"), {'FINISHED'})
        self.assertIsNotNone(bpy.data.texts.get("Widget.sysml"))

    @unittest.skipUnless(sysml_diagnostics.available(), "sml2c binary not available next to blender")
    def test_roundtrip_text_reimports(self):
        text = sysml_text.nodes_to_text(self.tree)
        tree2 = sysml_text.text_to_nodes(text)            # re-parse the serialized text
        names = {n.element_name for n in tree2.nodes if n.element_name}
        self.assertLessEqual({"Engine", "Car", "e"}, names)


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
