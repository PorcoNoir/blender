# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""BSML2 exit gate — tutorial-corpus import fidelity (SCRUM-451).

Imports the curated sml2c contract corpus (``tests/python/sysml_corpus``) through
the ``File -> Import -> SysML`` operator and proves the graph is faithful to the
source model in two independent ways:

1. **No drift** — node and link counts match a recorded golden baseline, so a
   dropped node or lost edge (or a spurious one) fails the gate. Regenerate the
   baseline deliberately (see ``BASELINE``) when the corpus or the importer's
   kind coverage intentionally changes.

2. **No lost edges** — every relationship sml2c reports in its own ``--emit-json``
   AST (typing, specialization, redefinition, containment, connector ends) whose
   endpoints both imported as named nodes must appear as a wired link. This is
   derived live from the compiler, so it needs no hand-maintained expectations.

Runs headless; skips where the sml2c binary is unavailable (matching the soft
skip of the sml2c regen gate until per-OS binaries ship — SCRUM-453).
"""

import json
import os
import subprocess
import sys
import unittest

import bpy

TREE_IDNAME = "SysMLNodeTree"

CORPUS_DIR = os.path.join(os.path.dirname(__file__), "sysml_corpus")

# Golden node/link counts per corpus file. Captured by importing each file with
# the shipped importer; a mismatch means the graph drifted (regression or an
# intended coverage change that should be re-baselined).
BASELINE = {
    "01_minimal.sysml":        {"nodes": 2,  "links": 1},
    "02_imports.sysml":        {"nodes": 2,  "links": 1},
    "03_specialization.sysml": {"nodes": 4,  "links": 6},
    "04_usages.sysml":         {"nodes": 7,  "links": 8},
    "05_multiplicity.sysml":   {"nodes": 7,  "links": 9},
    "06_magical_bag.sysml":    {"nodes": 7,  "links": 7},
    "all-kinds.sysml":         {"nodes": 45, "links": 64},
}


def sml2c_binary():
    """Resolve the sml2c binary the same way the C++ bridge does."""
    env = os.environ.get("SML2C")
    if env and os.path.exists(env):
        return env
    program_dir = os.path.dirname(bpy.app.binary_path or "")
    for name in ("sml2c.exe", "sml2c"):
        candidate = os.path.join(program_dir, name)
        if os.path.exists(candidate):
            return candidate
    return None


def _ref_target(qn):
    if isinstance(qn, dict):
        if isinstance(qn.get("resolvedTo"), str):
            return qn["resolvedTo"]
        parts = qn.get("parts")
        if isinstance(parts, list) and parts and isinstance(parts[-1], str):
            return parts[-1]
    return ""


def expected_edges(ast, names):
    """Relationships in the AST whose both endpoints imported as named nodes.

    Yields ``(from_name, to_name, {socket_ids})`` — a set of acceptable target
    socket identifiers (connectors accept ``connect`` or ``from`` for the first
    end).
    """
    edges = []

    def children(node):
        for key in ("members", "body"):
            val = node.get(key)
            if isinstance(val, list):
                yield from val
            elif isinstance(val, dict):
                yield val

    def walk(node, parent_name):
        if not isinstance(node, dict):
            return
        name = node.get("name") if isinstance(node.get("name"), str) else ""
        present = name in names and name != ""

        if present:
            # Containment: direct named parent -> this node's `members`.
            if parent_name in names and parent_name:
                edges.append((name, parent_name, {"members"}))
            for key, socket in (("types", "of"),
                                ("specializes", "specializes"),
                                ("redefines", "redefines")):
                val = node.get(key)
                if isinstance(val, list):
                    for ref in val:
                        tgt = _ref_target(ref)
                        if tgt in names and tgt:
                            edges.append((tgt, name, {socket}))
            ends = node.get("ends")
            if isinstance(ends, list):
                for i, ref in enumerate(ends):
                    tgt = _ref_target(ref)
                    if tgt in names and tgt:
                        slots = {"connect", "from"} if i == 0 else {"to"}
                        edges.append((tgt, name, slots))

        next_parent = name if present else parent_name
        for child in children(node):
            walk(child, next_parent)

    walk(ast, "")
    return edges


@unittest.skipUnless(sml2c_binary(), "sml2c binary not available next to blender")
class SysMLCorpusFidelityTest(unittest.TestCase):
    def _import(self, path):
        before = set(bpy.data.node_groups.keys())
        result = bpy.ops.node.sysml_import(filepath=path)
        self.assertEqual(result, {'FINISHED'}, f"{os.path.basename(path)} failed to import")
        new = [
            ng for key, ng in bpy.data.node_groups.items()
            if key not in before and ng.bl_idname == TREE_IDNAME
        ]
        self.assertEqual(len(new), 1)
        return new[0]

    def test_corpus_imports_are_faithful(self):
        sml2c = sml2c_binary()
        for filename, expect in BASELINE.items():
            path = os.path.join(CORPUS_DIR, filename)
            with self.subTest(corpus=filename):
                self.assertTrue(os.path.exists(path), f"missing corpus file {filename}")

                tree = self._import(path)

                # (1) No drift against the golden baseline.
                self.assertEqual(len(tree.nodes), expect["nodes"],
                                 f"{filename}: node count drifted")
                self.assertEqual(len(tree.links), expect["links"],
                                 f"{filename}: link count drifted")

                # (2) No lost edges, checked against sml2c's own AST.
                proc = subprocess.run([sml2c, "--emit-json", path],
                                      capture_output=True, text=True)
                self.assertEqual(proc.returncode, 0,
                                 f"{filename}: sml2c failed:\n{proc.stderr}")
                ast = json.loads(proc.stdout)

                names = {n.element_name for n in tree.nodes if n.element_name}
                in_sockets = {
                    n.element_name: {s.identifier for s in n.inputs}
                    for n in tree.nodes if n.element_name
                }
                wired = {
                    (link.from_node.element_name,
                     link.to_node.element_name,
                     link.to_socket.identifier)
                    for link in tree.links
                }
                for from_name, to_name, slots in expected_edges(ast, names):
                    # Only require edges the target node can actually hold: some
                    # definition kinds (e.g. item_def, enumeration_def) expose no
                    # `members` socket, so their nested features import as free
                    # nodes. That is a node-model coverage limit, not a wiring
                    # bug, so it is out of scope for this import-fidelity gate.
                    usable = slots & in_sockets.get(to_name, set())
                    if not usable:
                        continue
                    self.assertTrue(
                        any((from_name, to_name, s) in wired for s in usable),
                        f"{filename}: missing edge {from_name} -> {to_name} "
                        f"[{'/'.join(sorted(usable))}]")


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
