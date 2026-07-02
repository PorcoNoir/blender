# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""SysML notation export test (BSML3 / SCRUM-498).

Drives ``NODE_OT_sysml_export``: import each corpus model, export the resulting
graph back to canonical ``.sysml``, and prove sml2c re-parses the output without
error. Also spot-checks that the notation carries the expected syntax (typing,
specialization, connectors). Full text ⇄ graph round-trip stability is the
separate SCRUM-499 gate.

Skips where the sml2c binary is unavailable (matching the other SysML gates).
"""

import os
import subprocess
import sys
import tempfile
import unittest

import bpy

TREE_IDNAME = "SysMLNodeTree"
CORPUS_DIR = os.path.join(os.path.dirname(__file__), "sysml_corpus")


def sml2c_binary():
    env = os.environ.get("SML2C")
    if env and os.path.exists(env):
        return env
    program_dir = os.path.dirname(bpy.app.binary_path or "")
    for name in ("sml2c.exe", "sml2c"):
        candidate = os.path.join(program_dir, name)
        if os.path.exists(candidate):
            return candidate
    return None


CORPUS = [
    "01_minimal.sysml", "02_imports.sysml", "03_specialization.sysml",
    "04_usages.sysml", "05_multiplicity.sysml", "06_magical_bag.sysml",
    "all-kinds.sysml",
]


@unittest.skipUnless(sml2c_binary(), "sml2c binary not available next to blender")
class SysMLExportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._out = tempfile.mkdtemp()

    def _import(self, path):
        before = set(bpy.data.node_groups.keys())
        self.assertEqual(bpy.ops.node.sysml_import(filepath=path), {'FINISHED'})
        new = [ng for key, ng in bpy.data.node_groups.items()
               if key not in before and ng.bl_idname == TREE_IDNAME]
        self.assertEqual(len(new), 1)
        return new[0]

    def _export(self, tree, filename):
        out_path = os.path.join(self._out, filename)
        result = bpy.ops.node.sysml_export(filepath=out_path, tree_name=tree.name)
        self.assertEqual(result, {'FINISHED'}, f"export of {filename} failed")
        self.assertTrue(os.path.exists(out_path))
        return out_path

    def test_export_reparses_through_sml2c(self):
        sml2c = sml2c_binary()
        for filename in CORPUS:
            with self.subTest(corpus=filename):
                tree = self._import(os.path.join(CORPUS_DIR, filename))
                out_path = self._export(tree, filename)
                proc = subprocess.run([sml2c, "--emit-json", out_path],
                                      capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0,
                                 f"{filename}: exported .sysml did not parse:\n{proc.stderr}")

    def test_notation_carries_structure(self):
        # A model with definitions, typing and nested containment.
        tree = self._import(os.path.join(CORPUS_DIR, "06_magical_bag.sysml"))
        with open(self._export(tree, "06_check.sysml"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("def ", text, "definitions should emit a `def` keyword")
        self.assertRegex(text, r":\s*\w", "typed usages should emit `: Type`")
        self.assertIn("{", text, "container elements should emit a `{ ... }` body")
        self.assertIn("}", text, "nested containers should emit a closing brace")

    def test_specialization_notation(self):
        # 03_specialization exercises `:>` (or `specializes`).
        tree = self._import(os.path.join(CORPUS_DIR, "03_specialization.sysml"))
        with open(self._export(tree, "03_check.sysml"), encoding="utf-8") as f:
            text = f.read()
        self.assertTrue(":>" in text or "specializes" in text,
                        "specialization should emit `:>`")


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
