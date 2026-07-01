# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""
Test coverage for the SysML v2 native node tree (BSML0).

Mirrors Blender's ``tests/python`` conventions: unittest test cases run head-less
and registered through ``add_blender_test`` in ``tests/python/CMakeLists.txt``.

Coverage map (extend this as SysML functionality grows):
  * TestSysMLNodeTree       — NTREE_SYSML tree type registration (SCRUM-430).
  * TestSysMLElementSocket  — NodeSocketSysMLElement reference socket (SCRUM-432).
  * TestSysMLElementNodes   — PartDef / PartUsage / ConnectionUsage and their
                              socket shape (SCRUM-433).
  * TestSysMLElementStorage — NodeSysMLElement DNA storage / RNA props (SCRUM-434).
  * TestSysMLWiring         — element-reference links (`of` typing, a connection).
  * TestSysMLAddMenu        — node-editor add-menu registration (SCRUM-431).
  * TestSysMLSaveReload     — save a model to a .blend and reload it (SCRUM-435).

Run head-less:
    blender --background --factory-startup \\
        --python tests/python/bl_sysml_nodetree.py
"""

import os
import sys
import tempfile
import unittest

import bpy

TREE_IDNAME = "SysMLNodeTree"
SOCKET_IDNAME = "NodeSocketSysMLElement"

PART_DEF = "SysMLNodePartDef"
PART_USAGE = "SysMLNodePartUsage"
CONNECTION_USAGE = "SysMLNodeConnectionUsage"

# Expected socket identifiers per node type: (outputs, inputs).
NODE_SOCKETS = {
    PART_DEF: (["self"], ["members", "specializes"]),
    PART_USAGE: (["self"], ["members", "of", "redefines"]),
    CONNECTION_USAGE: (["self"], ["of", "connect", "to"]),
}


class SysMLTestCase(unittest.TestCase):
    """Base case that tracks created trees and removes them on teardown."""

    def setUp(self):
        self._groups = []

    def tearDown(self):
        for ng in self._groups:
            try:
                bpy.data.node_groups.remove(ng)
            except (ReferenceError, RuntimeError):
                # The datablock may be gone after an open_mainfile().
                pass

    def new_tree(self, name=TREE_IDNAME):
        ng = bpy.data.node_groups.new(name, TREE_IDNAME)
        self._groups.append(ng)
        return ng

    @staticmethod
    def socket_identifiers(sockets):
        return [s.identifier for s in sockets]


class TestSysMLNodeTree(SysMLTestCase):
    def test_tree_type_registered(self):
        """The SysML node tree type registers and is creatable via bpy."""
        self.assertTrue(hasattr(bpy.types, TREE_IDNAME),
                        "SysMLNodeTree RNA struct is not registered")
        ng = self.new_tree("sysml_tree")
        self.assertEqual(ng.bl_idname, TREE_IDNAME)

    def test_tree_is_distinct_type(self):
        """A SysML tree is not confused with the other built-in tree types."""
        ng = self.new_tree("sysml_distinct")
        self.assertNotIn(ng.bl_idname,
                         {"ShaderNodeTree", "GeometryNodeTree",
                          "CompositorNodeTree", "TextureNodeTree"})


class TestSysMLElementSocket(SysMLTestCase):
    def test_socket_type_registered(self):
        """The element-reference socket type is registered."""
        self.assertTrue(hasattr(bpy.types, SOCKET_IDNAME),
                        "NodeSocketSysMLElement is not registered")

    def test_self_output_uses_element_socket(self):
        """Every element node's `self` output is a SysML element socket."""
        ng = self.new_tree()
        for idname in NODE_SOCKETS:
            node = ng.nodes.new(idname)
            self.assertEqual(node.outputs["Self"].bl_idname, SOCKET_IDNAME)


class TestSysMLElementNodes(SysMLTestCase):
    def test_nodes_addable(self):
        """All three BSML0 element nodes can be created in a SysML tree."""
        ng = self.new_tree()
        for idname in NODE_SOCKETS:
            node = ng.nodes.new(idname)
            self.assertEqual(node.bl_idname, idname)

    def test_node_socket_shape(self):
        """Each node exposes exactly its specified input/output sockets."""
        ng = self.new_tree()
        for idname, (out_ids, in_ids) in NODE_SOCKETS.items():
            node = ng.nodes.new(idname)
            self.assertEqual(self.socket_identifiers(node.outputs), out_ids,
                             f"{idname} outputs mismatch")
            self.assertEqual(self.socket_identifiers(node.inputs), in_ids,
                             f"{idname} inputs mismatch")

    def test_all_sockets_are_element_sockets(self):
        """Every SysML node socket is the element-reference type."""
        ng = self.new_tree()
        for idname in NODE_SOCKETS:
            node = ng.nodes.new(idname)
            for sock in list(node.inputs) + list(node.outputs):
                self.assertEqual(sock.bl_idname, SOCKET_IDNAME)


class TestSysMLElementStorage(SysMLTestCase):
    STORAGE_PROPS = ("element_name", "short_name", "multiplicity")

    def test_storage_string_props_present(self):
        """The NodeSysMLElement storage exposes its RNA string properties."""
        ng = self.new_tree()
        node = ng.nodes.new(PART_DEF)
        for prop in self.STORAGE_PROPS:
            self.assertTrue(hasattr(node, prop),
                            f"{PART_DEF} missing storage prop '{prop}'")

    def test_storage_roundtrip_in_memory(self):
        """Storage values written via RNA read back unchanged."""
        ng = self.new_tree()
        node = ng.nodes.new(PART_DEF)
        node.element_name = "Vehicle"
        node.short_name = "veh"
        node.multiplicity = "[0..*]"
        node.is_abstract = True
        self.assertEqual(node.element_name, "Vehicle")
        self.assertEqual(node.short_name, "veh")
        self.assertEqual(node.multiplicity, "[0..*]")
        self.assertTrue(node.is_abstract)

    def test_is_abstract_default_false(self):
        ng = self.new_tree()
        node = ng.nodes.new(PART_DEF)
        self.assertFalse(node.is_abstract)


class TestSysMLWiring(SysMLTestCase):
    def test_typing_link(self):
        """A PartUsage can be typed by a PartDef via `self` -> `of`."""
        ng = self.new_tree()
        part_def = ng.nodes.new(PART_DEF)
        part_usage = ng.nodes.new(PART_USAGE)
        link = ng.links.new(part_def.outputs["Self"], part_usage.inputs["Type"])
        self.assertIn(link, list(ng.links))
        # bpy structs compare by underlying data pointer with ==, not identity.
        self.assertEqual(link.from_node, part_def)
        self.assertEqual(link.to_node, part_usage)
        self.assertEqual(link.from_socket.identifier, "self")
        self.assertEqual(link.to_socket.identifier, "of")

    def test_connection_links(self):
        """A ConnectionUsage wires two usages through `connect` and `to`."""
        ng = self.new_tree()
        a = ng.nodes.new(PART_USAGE)
        b = ng.nodes.new(PART_USAGE)
        conn = ng.nodes.new(CONNECTION_USAGE)
        ng.links.new(a.outputs["Self"], conn.inputs["Connect"])
        ng.links.new(b.outputs["Self"], conn.inputs["To"])
        self.assertEqual(len(ng.links), 2)


class TestSysMLAddMenu(SysMLTestCase):
    def test_add_menu_registered(self):
        """The SysML node add-menu is registered (SCRUM-431)."""
        self.assertTrue(hasattr(bpy.types, "NODE_MT_sysml_node_add_all"),
                        "SysML add-menu is not registered")

    def test_family_submenus_registered(self):
        """The categorized add-menu exposes family submenus (SCRUM-442)."""
        for slug in ("packages", "structure", "connections", "requirements", "behavior"):
            self.assertTrue(hasattr(bpy.types, f"NODE_MT_category_sysml_{slug}"),
                            f"missing family submenu '{slug}'")


class TestSysMLSaveReload(SysMLTestCase):
    """The SCRUM-435 gate: a model survives a .blend save/reload round-trip."""

    def _build_model(self, tree_name):
        ng = bpy.data.node_groups.new(tree_name, TREE_IDNAME)
        # Persist even with no other users so it is written to the file.
        ng.use_fake_user = True
        part_def = ng.nodes.new(PART_DEF)
        part_def.element_name = "Vehicle"
        part_def.is_abstract = True
        part_usage = ng.nodes.new(PART_USAGE)
        part_usage.element_name = "myCar"
        ng.links.new(part_def.outputs["Self"], part_usage.inputs["Type"])
        return ng

    def test_save_and_reload(self):
        tree_name = "sysml_saveload_model"
        self._build_model(tree_name)

        tmpdir = tempfile.mkdtemp(prefix="sysml_test_")
        path = os.path.join(tmpdir, "sysml_model.blend").replace("\\", "/")
        try:
            bpy.ops.wm.save_as_mainfile(filepath=path)
            bpy.ops.wm.open_mainfile(filepath=path)

            ng = bpy.data.node_groups.get(tree_name)
            self.assertIsNotNone(ng, "SysML tree did not survive save/reload")
            self.assertEqual(ng.bl_idname, TREE_IDNAME)

            names = {n.bl_idname for n in ng.nodes}
            self.assertIn(PART_DEF, names)
            self.assertIn(PART_USAGE, names)
            self.assertEqual(len(ng.links), 1, "typing link did not persist")

            part_def = next(n for n in ng.nodes if n.bl_idname == PART_DEF)
            self.assertEqual(part_def.element_name, "Vehicle")
            self.assertTrue(part_def.is_abstract)
        finally:
            try:
                os.remove(path)
                os.rmdir(tmpdir)
            except OSError:
                pass


class TestSysMLGeneratedTaxonomy(SysMLTestCase):
    """The full generated taxonomy (BSML1): every kind registers, instantiates,
    exposes storage RNA, and a family sampling round-trips through a .blend."""

    def _idnames(self):
        return sorted(t for t in dir(bpy.types)
                      if t.startswith("SysMLNode") and t not in ("SysMLNodeTree", "SysMLNodeGroup"))

    def test_full_taxonomy_registered(self):
        self.assertGreaterEqual(len(self._idnames()), 55,
                                "expected the full generated SysML taxonomy (~58 kinds)")

    def test_all_kinds_addable_and_rna_visible(self):
        ng = self.new_tree()
        for idname in self._idnames():
            node = ng.nodes.new(idname)
            self.assertEqual(node.bl_idname, idname)
            self.assertTrue(hasattr(node, "element_name"), f"{idname} missing storage RNA")
            self.assertEqual(node.outputs["Self"].bl_idname, SOCKET_IDNAME)

    def test_nodes_carry_family_accent_color(self):
        """Generated nodes get their family accent as a custom header colour (SCRUM-442)."""
        ng = self.new_tree()
        node = ng.nodes.new("SysMLNodePartDef")
        self.assertTrue(node.use_custom_color, "node missing custom accent colour")
        self.assertGreater(sum(node.color), 0.0)

    def test_family_sampling_roundtrip(self):
        sample = ["SysMLNodePartDef", "SysMLNodeRequirementUsage", "SysMLNodeActionDef",
                  "SysMLNodeStateUsage", "SysMLNodeFlowUsage", "SysMLNodeInterfaceUsage",
                  "SysMLNodePackage", "SysMLNodeViewDef", "SysMLNodeCalcUsage"]
        ng = bpy.data.node_groups.new("sysml_family_mix", TREE_IDNAME)
        ng.use_fake_user = True
        for idname in sample:
            ng.nodes.new(idname).element_name = idname

        tmpdir = tempfile.mkdtemp(prefix="sysml_fam_")
        path = os.path.join(tmpdir, "fam.blend").replace("\\", "/")
        try:
            bpy.ops.wm.save_as_mainfile(filepath=path)
            bpy.ops.wm.open_mainfile(filepath=path)
            ng2 = bpy.data.node_groups.get("sysml_family_mix")
            self.assertIsNotNone(ng2, "family-mix tree did not survive save/reload")
            got = {n.bl_idname for n in ng2.nodes}
            for idname in sample:
                self.assertIn(idname, got, f"{idname} lost across save/reload")
        finally:
            try:
                os.remove(path)
                os.rmdir(tmpdir)
            except OSError:
                pass


class TestSysMLForwardCompat(SysMLTestCase):
    """SCRUM-443: the single shared NodeSysMLElement storage backs every kind,
    and a mixed model (storage values + links) survives a .blend round-trip."""

    def test_shared_storage_on_all_kinds(self):
        ng = self.new_tree()
        idnames = [t for t in dir(bpy.types)
                   if t.startswith("SysMLNode") and t not in ("SysMLNodeTree", "SysMLNodeGroup")]
        for idname in sorted(idnames):
            node = ng.nodes.new(idname)
            for prop in ("element_name", "short_name", "multiplicity", "is_abstract"):
                self.assertTrue(hasattr(node, prop), f"{idname} missing storage prop '{prop}'")

    def test_values_and_links_survive_roundtrip(self):
        ng = bpy.data.node_groups.new("sysml_fc_model", TREE_IDNAME)
        ng.use_fake_user = True
        pdef = ng.nodes.new("SysMLNodePartDef")
        pdef.element_name = "Vehicle"
        pdef.short_name = "veh"
        pdef.multiplicity = "[1]"
        pdef.is_abstract = True
        pusage = ng.nodes.new("SysMLNodePartUsage")
        pusage.element_name = "myCar"
        conn = ng.nodes.new("SysMLNodeConnectionUsage")
        ng.links.new(pdef.outputs["Self"], pusage.inputs["Type"])
        ng.links.new(pusage.outputs["Self"], conn.inputs["Connect"])

        tmpdir = tempfile.mkdtemp(prefix="sysml_fc_")
        path = os.path.join(tmpdir, "fc.blend").replace("\\", "/")
        try:
            bpy.ops.wm.save_as_mainfile(filepath=path)
            bpy.ops.wm.open_mainfile(filepath=path)
            ng2 = bpy.data.node_groups.get("sysml_fc_model")
            self.assertIsNotNone(ng2, "model did not survive save/reload")
            pdef2 = next(n for n in ng2.nodes if n.bl_idname == "SysMLNodePartDef")
            self.assertEqual(pdef2.element_name, "Vehicle")
            self.assertEqual(pdef2.short_name, "veh")
            self.assertEqual(pdef2.multiplicity, "[1]")
            self.assertTrue(pdef2.is_abstract)
            self.assertEqual(len(ng2.links), 2, "links did not survive reload")
        finally:
            try:
                os.remove(path)
                os.rmdir(tmpdir)
            except OSError:
                pass

    def test_subset_file_loads(self):
        """A file saved with only a subset of kinds still loads (forward-compat)."""
        ng = bpy.data.node_groups.new("sysml_subset", TREE_IDNAME)
        ng.use_fake_user = True
        ng.nodes.new("SysMLNodePartDef")
        tmpdir = tempfile.mkdtemp(prefix="sysml_sub_")
        path = os.path.join(tmpdir, "sub.blend").replace("\\", "/")
        try:
            bpy.ops.wm.save_as_mainfile(filepath=path)
            bpy.ops.wm.open_mainfile(filepath=path)
            self.assertIsNotNone(bpy.data.node_groups.get("sysml_subset"))
        finally:
            try:
                os.remove(path)
                os.rmdir(tmpdir)
            except OSError:
                pass


def main():
    # Drop Blender's own argv so unittest only sees args after "--".
    argv = [sys.argv[0]]
    if "--" in sys.argv:
        argv += sys.argv[sys.argv.index("--") + 1:]
    unittest.main(argv=argv)


if __name__ == "__main__":
    main()
