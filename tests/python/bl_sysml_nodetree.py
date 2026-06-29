# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Tests for the SysML v2 node tree type (BSML0).

Intentionally red/green for the BSML0 rollout:
  * test_tree_type_registered  — PASSES with SCRUM-430 (tree scaffold).
  * test_part_def_node_addable — FAILS until SCRUM-433 (the first element
                                 nodes) lands; encodes the next gate.

Run head-less:
    blender --background --factory-startup \\
        --python tests/python/bl_sysml_nodetree.py
"""

import sys
import unittest

import bpy

TREE_IDNAME = "SysMLNodeTree"


class TestSysMLNodeTree(unittest.TestCase):
    def setUp(self):
        self._groups = []

    def tearDown(self):
        for ng in self._groups:
            try:
                bpy.data.node_groups.remove(ng)
            except Exception:
                pass

    def _new_tree(self, name):
        ng = bpy.data.node_groups.new(name, TREE_IDNAME)
        self._groups.append(ng)
        return ng

    # --- minimal passing test (SCRUM-430) ---
    def test_tree_type_registered(self):
        """The SysML node tree type registers and is creatable via bpy."""
        self.assertTrue(hasattr(bpy.types, TREE_IDNAME),
                        "SysMLNodeTree RNA struct is not registered")
        ng = self._new_tree("sysml_test")
        self.assertEqual(ng.bl_idname, TREE_IDNAME)

    # --- failing test (red until SCRUM-433 adds the first element nodes) ---
    def test_part_def_node_addable(self):
        """A PartDef element node can be added to a SysML tree.

        Expected to FAIL until SCRUM-433 registers the hand-written nodes.
        """
        ng = self._new_tree("sysml_partdef_test")
        node = ng.nodes.new("SysMLNodePartDef")
        self.assertEqual(node.bl_idname, "SysMLNodePartDef")


def main():
    # Drop Blender's own argv so unittest only sees args after "--".
    argv = [sys.argv[0]]
    if "--" in sys.argv:
        argv += sys.argv[sys.argv.index("--") + 1:]
    unittest.main(argv=argv)


if __name__ == "__main__":
    main()
