# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""BSML3 exit gate — text ⇄ graph ⇄ .py round-trip (SCRUM-502).

The capstone gate for BSML3: for every corpus model, the graph imported from the
source must survive both export paths unchanged —

    source.sysml --import--> G0
      G0 --export .sysml--> --reimport--> G1     (text round-trip)
      G0 --export .py-----> --exec------> G2     (bpy round-trip)

with G0 == G1 == G2 (same nodes by name+kind, same relationship edges). If all
three agree for every file, text, graph, and the generated bpy builder all
represent the same model — BSML3's definition of done.

The focused per-path gates (bl_sysml_roundtrip, bl_sysml_export_bpy) stay for
diagnostics; this ties them together. Skips where sml2c is unavailable.
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


@unittest.skipUnless(sml2c_available(), "sml2c binary not available next to blender")
class SysMLBsml3ExitGate(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._dir = tempfile.mkdtemp()

    def _new_tree_after(self, before):
        new = [ng for key, ng in bpy.data.node_groups.items()
               if key not in before and ng.bl_idname == TREE_IDNAME]
        self.assertEqual(len(new), 1)
        return new[0]

    def _import(self, filepath):
        before = set(bpy.data.node_groups.keys())
        self.assertEqual(bpy.ops.node.sysml_import(filepath=filepath), {'FINISHED'})
        return self._new_tree_after(before)

    def _reimport_notation(self, tree, filename):
        path = os.path.join(self._dir, "text_" + filename)
        self.assertEqual(bpy.ops.node.sysml_export(filepath=path, tree_name=tree.name),
                         {'FINISHED'})
        return self._import(path)

    def _rebuild_from_bpy(self, tree, filename):
        path = os.path.join(self._dir, "bpy_" + filename + ".py")
        self.assertEqual(bpy.ops.node.sysml_export_bpy(filepath=path, tree_name=tree.name),
                         {'FINISHED'})
        before = set(bpy.data.node_groups.keys())
        with open(path, encoding="utf-8") as f:
            exec(compile(f.read(), path, "exec"), {})
        return self._new_tree_after(before)

    def test_text_graph_bpy_all_agree(self):
        for filename in CORPUS:
            with self.subTest(corpus=filename):
                g0 = self._import(os.path.join(CORPUS_DIR, filename))
                base = snapshot(g0)

                g1 = self._reimport_notation(g0, filename)
                self.assertEqual(snapshot(g1), base,
                                 f"{filename}: text round-trip (graph->.sysml->graph) diverged")

                g2 = self._rebuild_from_bpy(g0, filename)
                self.assertEqual(snapshot(g2), base,
                                 f"{filename}: bpy round-trip (graph->.py->graph) diverged")


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
