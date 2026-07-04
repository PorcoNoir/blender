# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Reverse Blender objects -> SysML part nodes (Geometry Binding A / SCRUM-630).

Reads a hand-built object hierarchy back into a SysML graph (shape, dimensions,
units, containment, CSG), and closes the loop: a graph that is materialized and
then reversed reproduces the same geometry. Idempotent on re-run. Pure bpy.
"""

import sys
import unittest

import bpy

from bl_ui import sysml_geometry
from bl_ui.sysml_binding import element_for_object, object_for_node
from bl_ui.sysml_geometry import SHAPE_KEY, DIM_PREFIX, CSG_KEY, CSG_OPERANDS_KEY

TREE_IDNAME = "SysMLNodeTree"


def _cube(name, dims):
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.active_object
    obj.name = name
    obj.dimensions = dims
    bpy.context.view_layer.update()
    return obj


def _sphere(name, radius):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius)
    obj = bpy.context.active_object
    obj.name = name
    obj[SHAPE_KEY] = "Sphere"
    return obj


class SysMLReverseTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.tree = bpy.data.node_groups.new("Rev", TREE_IDNAME)

    def test_reverse_hand_built_hierarchy(self):
        frame = _cube("Frame", (4.0, 2.0, 1.0))     # 8 verts -> inferred Cuboid
        ball = _sphere("Ball", 1.0)                   # stamped Sphere
        ball.parent = frame

        n = sysml_geometry.reverse_objects([frame, ball], self.tree)
        self.assertEqual(n, 2)

        frame_node = element_for_object(frame)
        ball_node = element_for_object(ball)
        self.assertIsNotNone(frame_node)
        self.assertIsNotNone(ball_node)

        self.assertEqual(frame_node[SHAPE_KEY], "Cuboid")
        self.assertAlmostEqual(frame_node[DIM_PREFIX + "length"], 4.0, places=4)
        self.assertAlmostEqual(frame_node[DIM_PREFIX + "width"], 2.0, places=4)
        self.assertAlmostEqual(frame_node[DIM_PREFIX + "height"], 1.0, places=4)

        self.assertEqual(ball_node[SHAPE_KEY], "Sphere")
        self.assertAlmostEqual(ball_node[DIM_PREFIX + "radius"], 1.0, places=4)

        # Containment: Ball wired into Frame's members.
        self.assertTrue(any(
            l.from_node == ball_node and l.to_node == frame_node
            and l.to_socket.identifier == "members" for l in self.tree.links))

    def test_reverse_csg(self):
        block = _cube("Block", (4.0, 4.0, 4.0))
        bpy.ops.mesh.primitive_cylinder_add(radius=1.0, depth=6.0)
        cutter = bpy.context.active_object
        cutter.name = "Cutter"
        cutter[SHAPE_KEY] = "Cylinder"
        mod = block.modifiers.new(name="cut", type='BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.object = cutter

        sysml_geometry.reverse_objects([block, cutter], self.tree)
        block_node = element_for_object(block)
        self.assertEqual(block_node[CSG_KEY], "difference")
        self.assertIn("Cutter", block_node[CSG_OPERANDS_KEY])

    def test_idempotent(self):
        frame = _cube("Frame", (2.0, 2.0, 2.0))
        ball = _sphere("Ball", 1.0)
        ball.parent = frame
        sysml_geometry.reverse_objects([frame, ball], self.tree)
        nodes_after_first = len(self.tree.nodes)
        links_after_first = len(self.tree.links)
        sysml_geometry.reverse_objects([frame, ball], self.tree)
        self.assertEqual(len(self.tree.nodes), nodes_after_first)
        self.assertEqual(len(self.tree.links), links_after_first)

    def test_materialize_reverse_roundtrip(self):
        # Build a graph in mm, materialize, then reverse into a new tree.
        src = self.tree
        frame = src.nodes.new("SysMLNodePartDef")
        frame.element_name = "Frame"
        frame["sysml_shape"] = "Cuboid"
        frame["sysml_unit"] = "mm"
        frame["sysml_dim_length"] = 4800.0
        frame["sysml_dim_width"] = 1840.0
        frame["sysml_dim_height"] = 1350.0
        ball = src.nodes.new("SysMLNodePartUsage")
        ball.element_name = "Ball"
        ball["sysml_shape"] = "Sphere"
        ball["sysml_unit"] = "mm"
        ball["sysml_dim_radius"] = 500.0
        src.links.new(ball.outputs["Self"], frame.inputs["Members"])

        sysml_geometry.materialize_tree(src)
        objs = [object_for_node(frame), object_for_node(ball)]

        dst = bpy.data.node_groups.new("Roundtrip", TREE_IDNAME)
        # Rebind the objects to the destination tree before reversing.
        for o in objs:
            del o["sysml_tree"]  # drop old binding so reverse creates fresh nodes
        sysml_geometry.reverse_objects(objs, dst)

        rn = {n.element_name: n for n in dst.nodes}
        self.assertEqual(rn["Frame"]["sysml_shape"], "Cuboid")
        self.assertAlmostEqual(rn["Frame"][DIM_PREFIX + "length"], 4800.0, places=2)
        self.assertAlmostEqual(rn["Frame"][DIM_PREFIX + "width"], 1840.0, places=2)
        self.assertEqual(rn["Ball"]["sysml_shape"], "Sphere")
        self.assertAlmostEqual(rn["Ball"][DIM_PREFIX + "radius"], 500.0, places=2)


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
