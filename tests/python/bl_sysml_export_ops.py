# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""SysML export operators / menu surface (BSML3 / SCRUM-501).

Pins the user-facing entry points: both export operators are registered and
RNA-visible (callable from ``bpy``), both write their file for a given tree, and
both appear under ``File -> Export``. The exporters themselves are covered by the
SCRUM-498/500 gates; this guards the operator + menu wiring.
"""

import inspect
import os
import sys
import tempfile
import unittest

import bpy

TREE_IDNAME = "SysMLNodeTree"
CORPUS_DIR = os.path.join(os.path.dirname(__file__), "sysml_corpus")


def sml2c_available():
    if os.environ.get("SML2C") and os.path.exists(os.environ["SML2C"]):
        return True
    program_dir = os.path.dirname(bpy.app.binary_path or "")
    return any(os.path.exists(os.path.join(program_dir, n)) for n in ("sml2c.exe", "sml2c"))


class SysMLExportOpsTest(unittest.TestCase):
    def test_operators_are_rna_visible(self):
        # idname() raises if the operator is not registered.
        self.assertEqual(bpy.ops.node.sysml_export.idname(), "NODE_OT_sysml_export")
        self.assertEqual(bpy.ops.node.sysml_export_bpy.idname(), "NODE_OT_sysml_export_bpy")
        for op in (bpy.ops.node.sysml_export, bpy.ops.node.sysml_export_bpy):
            props = op.get_rna_type().properties.keys()
            self.assertIn("filepath", props)
            self.assertIn("tree_name", props)

    def test_menu_entries_present(self):
        self.assertTrue(hasattr(bpy.types, "TOPBAR_MT_file_export"))
        # Blender wraps a menu's draw; the real draw functions live in _draw_funcs.
        draw = bpy.types.TOPBAR_MT_file_export.draw
        funcs = getattr(draw, "_draw_funcs", None) or [draw]
        src = "\n".join(inspect.getsource(f) for f in funcs)
        self.assertIn("node.sysml_export", src, "File > Export missing the .sysml entry")
        self.assertIn("node.sysml_export_bpy", src, "File > Export missing the bpy .py entry")

    @unittest.skipUnless(sml2c_available(), "sml2c binary not available next to blender")
    def test_both_operators_write_files(self):
        out = tempfile.mkdtemp()
        before = set(bpy.data.node_groups.keys())
        self.assertEqual(
            bpy.ops.node.sysml_import(filepath=os.path.join(CORPUS_DIR, "04_usages.sysml")),
            {'FINISHED'})
        tree = next(ng for key, ng in bpy.data.node_groups.items()
                    if key not in before and ng.bl_idname == TREE_IDNAME)

        sysml_path = os.path.join(out, "out.sysml")
        py_path = os.path.join(out, "out.py")
        self.assertEqual(bpy.ops.node.sysml_export(filepath=sysml_path, tree_name=tree.name),
                         {'FINISHED'})
        self.assertEqual(bpy.ops.node.sysml_export_bpy(filepath=py_path, tree_name=tree.name),
                         {'FINISHED'})
        for path in (sysml_path, py_path):
            self.assertTrue(os.path.exists(path) and os.path.getsize(path) > 0,
                            f"{path} was not written")

    def test_export_without_tree_is_reported(self):
        # No active SysML editor and no such tree -> a reported error (bpy.ops
        # raises RuntimeError for a cancelled-with-error operator), not a crash.
        with self.assertRaises(RuntimeError):
            bpy.ops.node.sysml_export(filepath=os.path.join(tempfile.mkdtemp(), "x.sysml"),
                                      tree_name="does-not-exist")


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
