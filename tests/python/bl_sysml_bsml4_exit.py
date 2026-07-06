# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""BSML4 exit gate — Text round-trip + live diagnostics (SCRUM-668).

The phase-4 acceptance gate proves the BSML4 definition of done:

* a SysML `Text` datablock round-trips text -> nodes -> text -> nodes through the
  bound pair with structure (elements, typing, containment) preserved;
* a model with a seeded defect surfaces the expected diagnostic on the offending
  node and in the diagnostics list.

The round-trip needs sml2c (import) and soft-skips without it; the diagnostics
half is structural and always runs. Headless bpy; wired into the release
workflow. Green here means Phase 4 is complete and BSML5 is unblocked.
"""

import json
import sys
import unittest

import bpy

from bl_ui import sysml_text, sysml_validate, sysml_diagnostics

TREE_IDNAME = "SysMLNodeTree"

MODEL = """package Demo {
    part def Wheel;
    part def Engine;
    part def Car {
        part e : Engine;
        part w : Wheel;
    }
}
"""


def _names(tree):
    return {n.element_name for n in tree.nodes if n.element_name}


def _typed_of(tree, usage_name):
    """The element name typing `usage_name` via its `of` socket, or None."""
    node = next((n for n in tree.nodes if n.element_name == usage_name), None)
    if node is None:
        return None
    for link in tree.links:
        if link.to_node == node and link.to_socket.identifier == "of":
            return link.from_node.element_name
    return None


class BSML4ExitGate(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)

    @unittest.skipUnless(sysml_diagnostics.available(), "sml2c binary not available next to blender")
    def test_text_graph_roundtrip_preserves_structure(self):
        text = bpy.data.texts.new("Demo.sysml")
        text.write(MODEL)

        tree = sysml_text.text_to_nodes(text)          # text -> nodes
        sysml_text.bind_text(tree, text)
        before = _names(tree)
        self.assertLessEqual({"Wheel", "Engine", "Car", "e", "w"}, before)
        self.assertEqual(_typed_of(tree, "e"), "Engine")

        sysml_text.sync_to_text(tree)                  # nodes -> text
        tree2 = sysml_text.sync_from_text(text)        # text -> nodes (bound)

        self.assertEqual(_names(tree2), before)        # element set preserved
        self.assertEqual(_typed_of(tree2, "e"), "Engine")   # typing preserved
        self.assertEqual(_typed_of(tree2, "w"), "Wheel")
        # Containment preserved: Car still owns e and w.
        car = next(n for n in tree2.nodes if n.element_name == "Car")
        members = {l.from_node.element_name for l in tree2.links
                   if l.to_node == car and l.to_socket.identifier == "members"}
        self.assertLessEqual({"e", "w"}, members)

    def test_seeded_defect_surfaces_on_node_and_in_list(self):
        tree = bpy.data.node_groups.new("M", TREE_IDNAME)
        a = tree.nodes.new("SysMLNodePartDef"); a.element_name = "A"; a.is_abstract = True
        b = tree.nodes.new("SysMLNodePartUsage"); b.element_name = "b"
        tree.links.new(a.outputs["Self"], b.inputs["Type"])  # b : A  (A abstract)

        sysml_validate.validate_tree(tree)

        # Live diagnostic on the offending node.
        self.assertEqual(b[sysml_validate.DIAG_SEVERITY_KEY], "error")
        self.assertTrue(b.use_custom_color)
        # ...and in the panel's list.
        findings = json.loads(tree[sysml_validate.DIAG_LIST_KEY])
        self.assertTrue(any(f["node"] == b.name and f["code"] == "B4001" for f in findings))

        # Fixing the model clears the badge on re-validate.
        a.is_abstract = False
        sysml_validate.validate_tree(tree)
        self.assertNotIn(sysml_validate.DIAG_SEVERITY_KEY, b)


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
