# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Materialize SysML graph -> Blender objects (Geometry Binding A / SCRUM-627).

Builds a small nested geometry graph (a Cuboid frame containing a Sphere),
materializes it, and checks each part became a correctly shaped, sized, parented
and bound Blender object, and that re-running does not duplicate. Pure bpy — the
geometry data is set on the nodes directly (as the import annotation / reverse
will). No sml2c needed.
"""

import sys
import unittest

import bpy

from bl_ui import sysml_geometry
from bl_ui.sysml_binding import TREE_KEY, object_for_node, element_for_object

TREE_IDNAME = "SysMLNodeTree"


def _dims(obj):
    return tuple(round(v, 3) for v in obj.dimensions)


class SysMLMaterializeTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.tree = bpy.data.node_groups.new("Geo", TREE_IDNAME)
        # Frame (Cuboid 4x2x1) containing Ball (Sphere r=1).
        self.frame = self.tree.nodes.new("SysMLNodePartDef")
        self.frame.element_name = "Frame"
        self.frame["sysml_shape"] = "Cuboid"
        self.frame["sysml_dim_length"] = 4.0
        self.frame["sysml_dim_width"] = 2.0
        self.frame["sysml_dim_height"] = 1.0
        self.ball = self.tree.nodes.new("SysMLNodePartUsage")
        self.ball.element_name = "Ball"
        self.ball["sysml_shape"] = "Sphere"
        self.ball["sysml_dim_radius"] = 1.0
        self.tree.links.new(self.ball.outputs["Self"], self.frame.inputs["Members"])

    def _bound_count(self):
        return sum(1 for o in bpy.data.objects if o.get(TREE_KEY) == self.tree)

    def test_shapes_dimensions_parenting_binding(self):
        count = sysml_geometry.materialize_tree(self.tree)
        self.assertEqual(count, 2)

        frame_obj = object_for_node(self.frame)
        ball_obj = object_for_node(self.ball)
        self.assertIsNotNone(frame_obj)
        self.assertIsNotNone(ball_obj)

        # Correct shapes: a cube (8 verts) and a sphere (many verts).
        self.assertEqual(frame_obj.type, "MESH")
        self.assertEqual(len(frame_obj.data.vertices), 8)
        self.assertGreater(len(ball_obj.data.vertices), 8)

        # Sized from the shape dimensions.
        self.assertEqual(_dims(frame_obj), (4.0, 2.0, 1.0))
        self.assertEqual(_dims(ball_obj), (2.0, 2.0, 2.0))  # radius 1 -> 2x2x2

        # Containment -> parenting; both bound back to their nodes.
        self.assertEqual(ball_obj.parent, frame_obj)
        self.assertEqual(element_for_object(frame_obj), self.frame)
        self.assertEqual(element_for_object(ball_obj), self.ball)

    def test_rerun_is_idempotent(self):
        sysml_geometry.materialize_tree(self.tree)
        first = self._bound_count()
        sysml_geometry.materialize_tree(self.tree)
        self.assertEqual(self._bound_count(), first, "materialize duplicated objects on re-run")
        self.assertEqual(first, 2)

    def test_operator_is_rna_visible(self):
        self.assertEqual(bpy.ops.node.sysml_materialize.idname(), "NODE_OT_sysml_materialize")
        self.assertEqual(bpy.ops.node.sysml_materialize(tree_name=self.tree.name), {'FINISHED'})
        self.assertEqual(self._bound_count(), 2)


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
