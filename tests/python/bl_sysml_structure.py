# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Local structural checks (BSML4 / SCRUM-663).

Graph-native validation: abstract-instantiation, illegal reference-socket
targets, and malformed multiplicity each produce a node-attributed finding; a
valid graph produces none. Pure bpy (no sml2c).
"""

import sys
import unittest

import bpy

from bl_ui import sysml_structure
from bl_ui.sysml_kind_category_generated import KIND_CATEGORY

TREE_IDNAME = "SysMLNodeTree"


class SysMLStructureTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.tree = bpy.data.node_groups.new("M", TREE_IDNAME)

    def _node(self, idname, name, **props):
        n = self.tree.nodes.new(idname)
        n.element_name = name
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def _codes(self, findings):
        return sorted(f["code"] for f in findings)

    def test_abstract_instantiation_flagged(self):
        a = self._node("SysMLNodePartDef", "A", is_abstract=True)
        b = self._node("SysMLNodePartUsage", "b")
        self.tree.links.new(a.outputs["Self"], b.inputs["Type"])  # b : A  (of)
        findings = sysml_structure.check_tree(self.tree)
        self.assertEqual(self._codes(findings), [sysml_structure.ABSTRACT_CODE])
        self.assertEqual(findings[0]["node"], b.name)

    def test_illegal_of_target_flagged(self):
        pkg = self._node("SysMLNodePackage", "P")
        b = self._node("SysMLNodePartUsage", "b")
        self.tree.links.new(pkg.outputs["Self"], b.inputs["Type"])  # type must be a definition
        findings = sysml_structure.check_tree(self.tree)
        self.assertEqual(self._codes(findings), [sysml_structure.ILLEGAL_TARGET_CODE])
        self.assertEqual(findings[0]["node"], b.name)
        self.assertIn("package", findings[0]["message"])

    def test_valid_graph_is_clean(self):
        a = self._node("SysMLNodePartDef", "A")  # concrete
        b = self._node("SysMLNodePartUsage", "b")
        self.tree.links.new(a.outputs["Self"], b.inputs["Type"])       # b : A
        self.tree.links.new(b.outputs["Self"], a.inputs["Members"])    # containment (unconstrained)
        self.assertEqual(sysml_structure.check_tree(self.tree), [])

    def test_multiplicity_wellformedness(self):
        good = self._node("SysMLNodePartUsage", "g", multiplicity="0..*")
        bad = self._node("SysMLNodePartUsage", "b", multiplicity="2..1")
        findings = sysml_structure.check_tree(self.tree)
        self.assertEqual(self._codes(findings), [sysml_structure.MULTIPLICITY_CODE])
        self.assertEqual(findings[0]["node"], bad.name)

    def test_multiplicity_parser(self):
        ok = sysml_structure._multiplicity_ok
        for good in ("", "1", "0..1", "0..*", "[1..5]", "*"):
            self.assertTrue(ok(good), good)
        for bad in ("2..1", "a..b", "1..x", "1..2..3"):
            self.assertFalse(ok(bad), bad)

    def test_category_table_covers_taxonomy(self):
        # Every generated node kind is classified (no accidental gaps).
        self.assertTrue(all(v in {"definition", "usage", "package", "import",
                                  "alias", "annotation", "other"}
                            for v in KIND_CATEGORY.values()))
        self.assertEqual(KIND_CATEGORY["SysMLNodePartDef"], "definition")
        self.assertEqual(KIND_CATEGORY["SysMLNodePartUsage"], "usage")
        self.assertEqual(KIND_CATEGORY["SysMLNodePackage"], "package")


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
