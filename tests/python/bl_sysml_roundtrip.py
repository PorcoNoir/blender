# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""SysML notation round-trip fidelity (BSML3 / SCRUM-499).

Proves text ⇄ graph stability over the corpus, two ways:

1. **Graph round-trip is stable** — ``import → export → reimport`` yields the
   identical graph (same nodes by name+kind, same relationship edges). Nothing
   the graph models is lost or invented crossing text on the way back.

2. **Export is faithful to the source AST** — the exported ``.sysml``, recompiled
   by sml2c, carries the same element set the source model does (named elements
   the importer maps to nodes). Any divergence is asserted, never silent.

Uses the compiler as the oracle. Skips where the sml2c binary is unavailable.
"""

import json
import os
import subprocess
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
    "07_library_types.sysml", "all-kinds.sysml",
]


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


def snapshot(tree):
    """Structural fingerprint of a graph: node and edge multisets, name-based."""
    nodes = Counter((n.element_name, n.bl_idname) for n in tree.nodes)
    edges = Counter(
        (link.from_node.element_name, link.to_node.element_name, link.to_socket.identifier)
        for link in tree.links
    )
    return nodes, edges


def ast_element_names(ast):
    """Every named element sml2c parsed (kinds the importer represents)."""
    names = set()

    def walk(node):
        if not isinstance(node, dict):
            return
        kind = node.get("kind")
        name = node.get("name")
        if isinstance(name, str) and name and kind not in (None, "QualifiedName", "Program"):
            names.add(name)
        for key in ("members", "body"):
            val = node.get(key)
            if isinstance(val, list):
                for child in val:
                    walk(child)
            elif isinstance(val, dict):
                walk(val)

    walk(ast)
    return names


class SysMLRoundTripTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Soft-skip without sml2c for dev; hard failure when the release gate
        # sets SYSML_REQUIRE_SML2C (the binary is installed next to blender there).
        if sml2c_binary() is None:
            if os.environ.get("SYSML_REQUIRE_SML2C"):
                raise AssertionError("SYSML_REQUIRE_SML2C set but sml2c binary not found")
            raise unittest.SkipTest("sml2c binary not available next to blender")
        cls._dir = tempfile.mkdtemp()

    def _import(self, filepath):
        before = set(bpy.data.node_groups.keys())
        self.assertEqual(bpy.ops.node.sysml_import(filepath=filepath), {'FINISHED'})
        new = [ng for key, ng in bpy.data.node_groups.items()
               if key not in before and ng.bl_idname == TREE_IDNAME]
        self.assertEqual(len(new), 1)
        return new[0]

    def _export(self, tree, filename):
        out_path = os.path.join(self._dir, filename)
        self.assertEqual(bpy.ops.node.sysml_export(filepath=out_path, tree_name=tree.name),
                         {'FINISHED'})
        return out_path

    def test_graph_roundtrip_is_stable(self):
        for filename in CORPUS:
            with self.subTest(corpus=filename):
                first = self._import(os.path.join(CORPUS_DIR, filename))
                nodes_a, edges_a = snapshot(first)

                exported = self._export(first, "rt_" + filename)
                second = self._import(exported)
                nodes_b, edges_b = snapshot(second)

                self.assertEqual(nodes_a, nodes_b,
                                 f"{filename}: node set changed on import->export->reimport")
                self.assertEqual(edges_a, edges_b,
                                 f"{filename}: edge set changed on import->export->reimport")

    def test_export_matches_source_ast(self):
        sml2c = sml2c_binary()
        for filename in CORPUS:
            with self.subTest(corpus=filename):
                source = os.path.join(CORPUS_DIR, filename)
                tree = self._import(source)
                exported = self._export(tree, "ast_" + filename)

                src = subprocess.run([sml2c, "--emit-json", source],
                                     capture_output=True, text=True)
                exp = subprocess.run([sml2c, "--emit-json", exported],
                                     capture_output=True, text=True)
                self.assertEqual(src.returncode, 0, f"{filename}: source did not compile")
                self.assertEqual(exp.returncode, 0,
                                 f"{filename}: exported .sysml did not compile:\n{exp.stderr}")

                src_names = ast_element_names(json.loads(src.stdout))
                exp_names = ast_element_names(json.loads(exp.stdout))
                self.assertEqual(
                    src_names, exp_names,
                    f"{filename}: element set diverged on export "
                    f"(missing={sorted(src_names - exp_names)}, "
                    f"added={sorted(exp_names - src_names)})")


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
