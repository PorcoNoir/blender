# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Node <-> Blender object binding (Geometry Binding A / SCRUM-626).

Exercises the binding data-model contract: bind a SysML part node to an object,
look it up both ways, round-trip it through a .blend save/reload, and confirm
deleting either side clears the binding with no dangling reference. Pure bpy —
no sml2c needed.
"""

import os
import sys
import tempfile
import unittest

import bpy

from bl_ui import sysml_binding

TREE_IDNAME = "SysMLNodeTree"


class SysMLBindingTest(unittest.TestCase):
    def setUp(self):
        # Fresh file per test so datablocks/objects don't leak between cases.
        bpy.ops.wm.read_factory_settings(use_empty=True)

    def _make(self, obj_name="Widget", node_name="Widget"):
        obj = bpy.data.objects.new(obj_name, None)
        bpy.context.scene.collection.objects.link(obj)
        tree = bpy.data.node_groups.new("Tree", TREE_IDNAME)
        node = tree.nodes.new("SysMLNodePartDef")
        node.element_name = node_name
        return obj, tree, node

    def test_bind_and_lookup_both_ways(self):
        obj, tree, node = self._make()
        sysml_binding.bind(node, obj)
        self.assertTrue(sysml_binding.is_bound(obj))
        self.assertEqual(sysml_binding.element_for_object(obj), node)
        self.assertEqual(sysml_binding.object_for_node(node), obj)
        self.assertEqual([o.name for o, n in sysml_binding.bound_objects(tree)], [obj.name])

    def test_unbind(self):
        obj, tree, node = self._make()
        sysml_binding.bind(node, obj)
        sysml_binding.unbind(obj)
        self.assertFalse(sysml_binding.is_bound(obj))
        self.assertIsNone(sysml_binding.element_for_object(obj))
        self.assertIsNone(sysml_binding.object_for_node(node))

    def test_survives_save_reload(self):
        obj, tree, node = self._make()
        sysml_binding.bind(node, obj)
        blend = os.path.join(tempfile.mkdtemp(), "binding.blend")
        bpy.ops.wm.save_as_mainfile(filepath=blend)
        bpy.ops.wm.open_mainfile(filepath=blend)

        obj = bpy.data.objects["Widget"]
        self.assertTrue(sysml_binding.is_bound(obj))
        node = sysml_binding.element_for_object(obj)
        self.assertIsNotNone(node)
        self.assertEqual(node.element_name, "Widget")

    def test_object_delete_clears(self):
        obj, tree, node = self._make()
        sysml_binding.bind(node, obj)
        bpy.data.objects.remove(obj)
        # The object is gone, so nothing binds to the node any more.
        self.assertIsNone(sysml_binding.object_for_node(node))
        self.assertEqual(list(sysml_binding.bound_objects(tree)), [])

    def test_tree_delete_clears(self):
        obj, tree, node = self._make()
        sysml_binding.bind(node, obj)
        bpy.data.node_groups.remove(tree)
        # Blender nulls the managed datablock reference; no dangling pointer.
        self.assertIsNone(obj.get(sysml_binding.TREE_KEY))
        self.assertFalse(sysml_binding.is_bound(obj))
        self.assertIsNone(sysml_binding.element_for_object(obj))


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
