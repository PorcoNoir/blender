# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""End-to-end import test for the SysML node editor (BSML2 / SCRUM-450).

Exercises the full ``File -> Import -> SysML`` path through the ``NODE_OT_sysml_import``
operator: pick a ``.sysml`` file, run the bundled ``sml2c`` bridge, build the node
graph (SCRUM-447), wire the relationship edges (SCRUM-448), and auto-layout
(SCRUM-449). Mirrors Blender's ``tests/python`` conventions.

The test needs the ``sml2c`` binary at runtime (installed next to ``blender``,
or via the ``SML2C`` env var). Where it is absent — e.g. a platform without a
published binary yet (SCRUM-453) — the cases skip rather than fail, matching the
soft-skip policy of the sml2c regen gate.
"""

import os
import sys
import tempfile
import unittest

import bpy

TREE_IDNAME = "SysMLNodeTree"
PART_DEF = "SysMLNodePartDef"
PART_USAGE = "SysMLNodePartUsage"
CONNECTION_USAGE = "SysMLNodeConnectionUsage"

# A model exercising every relationship the importer wires: containment
# (members), typing (of), specialization (specializes), and a connection with
# two ends (connect / to).
MODEL = """package Test {
    part def Engine;
    part def Vehicle :> Engine {
        part eng : Engine;
    }
    connection def Conn;
    part def System {
        part a : Engine;
        part b : Engine;
        connection c : Conn connect a to b;
    }
}
"""


def sml2c_available():
    """True when the bridge can resolve an sml2c binary (see sml2c_binary_path)."""
    if os.environ.get("SML2C") and os.path.exists(os.environ["SML2C"]):
        return True
    program_dir = os.path.dirname(bpy.app.binary_path or "")
    return any(
        os.path.exists(os.path.join(program_dir, name))
        for name in ("sml2c.exe", "sml2c")
    )


@unittest.skipUnless(sml2c_available(), "sml2c binary not available next to blender")
class SysMLImportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._dir = tempfile.mkdtemp()
        cls._path = os.path.join(cls._dir, "model.sysml")
        with open(cls._path, "w", encoding="utf-8") as f:
            f.write(MODEL)

    def _import(self, name=None):
        """Import the fixture into a fresh tree; return that tree."""
        before = set(bpy.data.node_groups.keys())
        result = bpy.ops.node.sysml_import(filepath=self._path)
        self.assertEqual(result, {'FINISHED'})
        new = [
            ng for key, ng in bpy.data.node_groups.items()
            if key not in before and ng.bl_idname == TREE_IDNAME
        ]
        self.assertEqual(len(new), 1, "import should create exactly one SysML tree")
        return new[0]

    @staticmethod
    def _by_name(tree):
        return {n.element_name: n for n in tree.nodes if n.element_name}

    @staticmethod
    def _in_socket(node, identifier):
        for sock in node.inputs:
            if sock.identifier == identifier:
                return sock
        return None

    def _has_edge(self, tree, from_name, to_name, socket_id):
        """Is there a link from `from_name`.self into `to_name`.<socket_id>?"""
        for link in tree.links:
            if (link.from_node.element_name == from_name
                    and link.to_node.element_name == to_name
                    and link.to_socket.identifier == socket_id):
                return True
        return False

    def test_nodes_created_with_kinds(self):
        tree = self._import()
        nodes = self._by_name(tree)
        for name in ("Engine", "Vehicle", "eng", "Conn", "System", "a", "b", "c"):
            self.assertIn(name, nodes, f"missing imported element '{name}'")
        self.assertEqual(nodes["Engine"].bl_idname, PART_DEF)
        self.assertEqual(nodes["eng"].bl_idname, PART_USAGE)
        self.assertEqual(nodes["c"].bl_idname, CONNECTION_USAGE)

    def test_typing_edges(self):
        tree = self._import()
        # eng / a / b are all `: Engine`.
        for usage in ("eng", "a", "b"):
            self.assertTrue(self._has_edge(tree, "Engine", usage, "of"),
                            f"typing edge Engine -> {usage}.of missing")

    def test_specialization_edge(self):
        tree = self._import()
        self.assertTrue(self._has_edge(tree, "Engine", "Vehicle", "specializes"),
                        "specialization edge Engine -> Vehicle.specializes missing")

    def test_containment_edges(self):
        tree = self._import()
        self.assertTrue(self._has_edge(tree, "eng", "Vehicle", "members"),
                        "containment eng in Vehicle missing")
        for child in ("a", "b", "c"):
            self.assertTrue(self._has_edge(tree, child, "System", "members"),
                            f"containment {child} in System missing")

    def test_connection_ends(self):
        tree = self._import()
        self.assertTrue(self._has_edge(tree, "a", "c", "connect"),
                        "connection end a -> c.connect missing")
        self.assertTrue(self._has_edge(tree, "b", "c", "to"),
                        "connection end b -> c.to missing")

    def test_layout_indents_children_and_is_deterministic(self):
        tree_a = self._import()
        pos_a = {n.element_name: tuple(n.location) for n in tree_a.nodes}

        # Children are placed to the right of (indented from) their parent.
        for child, parent in (("eng", "Vehicle"), ("a", "System"), ("b", "System")):
            self.assertGreater(pos_a[child][0], pos_a[parent][0],
                               f"{child} should be indented right of {parent}")

        # No two nodes land on the exact same point.
        points = list(pos_a.values())
        self.assertEqual(len(points), len(set(points)), "nodes overlap exactly")

        # Deterministic: a second import of the same file matches positions.
        tree_b = self._import()
        pos_b = {n.element_name: tuple(n.location) for n in tree_b.nodes}
        self.assertEqual(pos_a, pos_b, "layout is not deterministic")


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
