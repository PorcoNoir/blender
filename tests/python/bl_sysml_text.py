# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""SysML Text datablock -> nodes (BSML4 / SCRUM-665).

A valid Text datablock parses to the expected tree (named after the datablock);
an invalid one reports the sml2c diagnostic and creates no tree. Import needs
sml2c, so the suite soft-skips when it is unavailable.
"""

import sys
import unittest

import bpy

from bl_ui import sysml_text
from bl_ui import sysml_diagnostics

TREE_IDNAME = "SysMLNodeTree"

VALID = """package Demo {
    part def Engine;
    part def Car {
        part e : Engine;
    }
}
"""

INVALID = """package Bad {
    part def A :> Missing;
}
"""


@unittest.skipUnless(sysml_diagnostics.available(), "sml2c binary not available next to blender")
class SysMLTextTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def _text(self, name, body):
        t = bpy.data.texts.new(name)
        t.write(body)
        return t

    def _names(self, tree):
        return {n.element_name for n in tree.nodes if n.element_name}

    def test_valid_text_parses_to_named_tree(self):
        text = self._text("Widget", VALID)
        tree = sysml_text.text_to_nodes(text)
        self.assertEqual(tree.bl_idname, TREE_IDNAME)
        self.assertEqual(tree.name, "Widget")               # named after the datablock
        self.assertLessEqual({"Engine", "Car", "e"}, self._names(tree))

    def test_invalid_text_raises_and_creates_no_tree(self):
        text = self._text("Broken", INVALID)
        before = len(bpy.data.node_groups)
        with self.assertRaises(sysml_text.SysMLParseError) as ctx:
            sysml_text.text_to_nodes(text)
        self.assertIn("Missing", str(ctx.exception))
        self.assertEqual(len(bpy.data.node_groups), before)  # nothing created

    def test_operator_valid(self):
        self._text("Op", VALID)
        self.assertEqual(bpy.ops.node.sysml_text_to_nodes(text_name="Op"), {'FINISHED'})
        self.assertIsNotNone(bpy.data.node_groups.get("Op"))

    def test_operator_invalid_cancels(self):
        # Reporting {'ERROR'} makes bpy.ops raise in script context; no tree is made.
        self._text("OpBad", INVALID)
        before = len(bpy.data.node_groups)
        with self.assertRaises(RuntimeError) as ctx:
            bpy.ops.node.sysml_text_to_nodes(text_name="OpBad")
        self.assertIn("Missing", str(ctx.exception))
        self.assertEqual(len(bpy.data.node_groups), before)


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
