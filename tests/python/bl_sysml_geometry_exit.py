# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Geometry Binding A exit gate — graph <-> 3D <-> graph round-trip (SCRUM-631).

The capstone for Phase A: a representative geometry graph (an Engine — a Cuboid
block with a Cylinder cut out via CSG difference, plus a nested Sphere part, in
millimetres) is materialized to Blender objects and then reversed back into a
fresh graph. The reversed graph must reproduce the source geometry — shapes,
dimensions (through the unit bridge), containment, and the boolean-difference.
If it does, the bidirectional SysML <-> Blender binding is faithful end to end.

Pure bpy; no sml2c (the graph is the source of truth for geometry). Skips if the
SysML geometry modules are unavailable.
"""

import sys
import unittest

import bpy

from bl_ui import sysml_geometry
from bl_ui.sysml_binding import object_for_node
from bl_ui.sysml_geometry import (SHAPE_KEY, UNIT_KEY, DIM_PREFIX, CSG_KEY, CSG_OPERANDS_KEY)

TREE_IDNAME = "SysMLNodeTree"


def geo_snapshot(tree):
    """A shape-only structural fingerprint: element -> shape/dims/unit/csg/parent."""
    parent_of = {}
    for link in tree.links:
        if link.to_socket.identifier == "members":
            parent_of[link.from_node.element_name] = link.to_node.element_name

    snap = {}
    for node in tree.nodes:
        if node.get(SHAPE_KEY) not in sysml_geometry.SHAPE_RESOLVER:
            continue
        dims = {k[len(DIM_PREFIX):]: round(float(node[k]), 3)
                for k in node.keys() if k.startswith(DIM_PREFIX)}
        snap[node.element_name] = {
            "shape": node[SHAPE_KEY],
            "unit": node.get(UNIT_KEY, "m"),
            "dims": dims,
            "csg": node.get(CSG_KEY, ""),
            "operands": node.get(CSG_OPERANDS_KEY, ""),
            "parent": parent_of.get(node.element_name, ""),
        }
    return snap


class SysMLGeometryExitGate(unittest.TestCase):
    def _build_source(self):
        tree = bpy.data.node_groups.new("Engine", TREE_IDNAME)

        engine = tree.nodes.new("SysMLNodePartDef")
        engine.element_name = "Engine"
        engine[SHAPE_KEY] = "Cuboid"
        engine[UNIT_KEY] = "mm"
        engine[DIM_PREFIX + "length"] = 300.0
        engine[DIM_PREFIX + "width"] = 190.0
        engine[DIM_PREFIX + "height"] = 330.0
        engine[CSG_KEY] = "difference"
        engine[CSG_OPERANDS_KEY] = "Cut"

        cut = tree.nodes.new("SysMLNodePartUsage")
        cut.element_name = "Cut"
        cut[SHAPE_KEY] = "Cylinder"
        cut[UNIT_KEY] = "mm"
        cut[DIM_PREFIX + "radius"] = 55.0
        cut[DIM_PREFIX + "height"] = 350.0

        ball = tree.nodes.new("SysMLNodePartUsage")
        ball.element_name = "Ball"
        ball[SHAPE_KEY] = "Sphere"
        ball[UNIT_KEY] = "mm"
        ball[DIM_PREFIX + "radius"] = 40.0

        tree.links.new(cut.outputs["Self"], engine.inputs["Members"])
        tree.links.new(ball.outputs["Self"], engine.inputs["Members"])
        return tree

    def test_graph_3d_graph_roundtrip(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        source = self._build_source()
        src_snap = geo_snapshot(source)
        # Sanity: the source really exercises shapes, nesting, units and CSG.
        self.assertEqual(set(src_snap), {"Engine", "Cut", "Ball"})
        self.assertEqual(src_snap["Engine"]["csg"], "difference")
        self.assertEqual(src_snap["Ball"]["parent"], "Engine")

        # graph -> 3D
        node_count = sysml_geometry.materialize_tree(source)
        self.assertEqual(node_count, 3)
        engine_obj = object_for_node(next(n for n in source.nodes if n.element_name == "Engine"))
        self.assertTrue(any(m.type == 'BOOLEAN' for m in engine_obj.modifiers),
                        "materialized Engine should have a boolean modifier")
        # Real-world size through the unit bridge: 300 mm -> 0.3 m.
        self.assertAlmostEqual(engine_obj.dimensions.x, 0.3, places=4)

        # 3D -> graph (into a fresh tree). Drop the source binding first so the
        # reverse builds new nodes rather than updating the source.
        objs = [object_for_node(n) for n in source.nodes if object_for_node(n)]
        for o in objs:
            del o["sysml_tree"]
        dest = bpy.data.node_groups.new("EngineRT", TREE_IDNAME)
        sysml_geometry.reverse_objects(objs, dest)

        self.assertEqual(geo_snapshot(dest), src_snap,
                         "graph -> 3D -> graph did not round-trip faithfully")


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
