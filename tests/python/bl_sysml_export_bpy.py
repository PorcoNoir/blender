# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""SysML bpy graph-builder export test (BSML3 / SCRUM-500).

Drives ``NODE_OT_sysml_export_bpy``: import each corpus model, export the graph
as a bpy graph-builder ``.py``, run that script, and assert the rebuilt tree
reproduces the source graph exactly — nodes, relationship edges, and node
locations. Also checks the emitted script is deterministic.

Importing the corpus needs the sml2c binary, so the cases skip when it is absent
(the bpy export itself has no external dependency).
"""

import os
import sys
import tempfile
import unittest
from collections import Counter

import bpy

TREE_IDNAME = "SysMLNodeTree"
CORPUS_DIR = os.path.join(os.path.dirname(__file__), "sysml_corpus")
CORPUS = [
    "01_minimal.sysml", "02_imports.sysml", "03_specialization.sysml",
    "04_usages.sysml", "05_multiplicity.sysml", "06_magical_bag.sysml",
    "all-kinds.sysml",
]


def sml2c_available():
    if os.environ.get("SML2C") and os.path.exists(os.environ["SML2C"]):
        return True
    program_dir = os.path.dirname(bpy.app.binary_path or "")
    return any(os.path.exists(os.path.join(program_dir, n)) for n in ("sml2c.exe", "sml2c"))


def snapshot(tree):
    nodes = Counter((n.element_name, n.bl_idname) for n in tree.nodes)
    edges = Counter(
        (link.from_node.element_name, link.to_node.element_name, link.to_socket.identifier)
        for link in tree.links
    )
    return nodes, edges


def locations(tree):
    return sorted((n.element_name, n.bl_idname, round(n.location.x, 3), round(n.location.y, 3))
                  for n in tree.nodes)


@unittest.skipUnless(sml2c_available(), "sml2c binary not available next to blender")
class SysMLBpyExportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._dir = tempfile.mkdtemp()

    def _import(self, path):
        before = set(bpy.data.node_groups.keys())
        self.assertEqual(bpy.ops.node.sysml_import(filepath=path), {'FINISHED'})
        new = [ng for key, ng in bpy.data.node_groups.items()
               if key not in before and ng.bl_idname == TREE_IDNAME]
        self.assertEqual(len(new), 1)
        return new[0]

    def _export_bpy(self, tree, filename):
        out_path = os.path.join(self._dir, filename)
        self.assertEqual(
            bpy.ops.node.sysml_export_bpy(filepath=out_path, tree_name=tree.name), {'FINISHED'})
        return out_path

    def _run_script(self, path):
        before = set(bpy.data.node_groups.keys())
        with open(path, encoding="utf-8") as f:
            exec(compile(f.read(), path, "exec"), {})
        new = [ng for key, ng in bpy.data.node_groups.items()
               if key not in before and ng.bl_idname == TREE_IDNAME]
        self.assertEqual(len(new), 1, "the builder script should create one SysML tree")
        return new[0]

    def test_bpy_rebuilds_graph(self):
        for filename in CORPUS:
            with self.subTest(corpus=filename):
                source = self._import(os.path.join(CORPUS_DIR, filename))
                script = self._export_bpy(source, filename + ".py")
                rebuilt = self._run_script(script)

                self.assertEqual(snapshot(rebuilt), snapshot(source),
                                 f"{filename}: rebuilt graph differs from source")
                self.assertEqual(locations(rebuilt), locations(source),
                                 f"{filename}: rebuilt layout differs from source")

    def test_script_is_deterministic(self):
        source = self._import(os.path.join(CORPUS_DIR, "all-kinds.sysml"))
        a = self._export_bpy(source, "det_a.py")
        b = self._export_bpy(source, "det_b.py")
        with open(a, encoding="utf-8") as fa, open(b, encoding="utf-8") as fb:
            self.assertEqual(fa.read(), fb.read(), "bpy export is not deterministic")


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
