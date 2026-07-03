# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""ISQ units <-> Blender scene units (Geometry Binding A / SCRUM-629).

Checks the length-unit conversions round-trip losslessly, honour the scene unit
scale, and that a `4800 [mm]` shape materializes to a real 4.8 m object. Pure bpy.
"""

import sys
import unittest

import bpy

from bl_ui import sysml_geometry
from bl_ui.sysml_binding import object_for_node
from bl_ui.sysml_units import to_blender_length, from_blender_length

TREE_IDNAME = "SysMLNodeTree"


def _dims(obj):
    return tuple(round(v, 4) for v in obj.dimensions)


class SysMLUnitsTest(unittest.TestCase):
    def test_conversion_values(self):
        self.assertAlmostEqual(to_blender_length(4800, "mm"), 4.8)
        self.assertAlmostEqual(to_blender_length(2, "m"), 2.0)
        self.assertAlmostEqual(to_blender_length(1, "in"), 0.0254)
        self.assertAlmostEqual(from_blender_length(4.8, "mm"), 4800.0)

    def test_roundtrip_lossless(self):
        for unit in ("mm", "cm", "m", "km", "in", "ft"):
            for value in (1.0, 4800.0, 0.5, 1350.0):
                bu = to_blender_length(value, unit)
                self.assertAlmostEqual(from_blender_length(bu, unit), value, places=6,
                                       msg=f"{value} {unit}")

    def test_scene_scale_honoured(self):
        class Scene:
            class unit_settings:
                scale_length = 0.01  # 1 BU = 1 cm
        # 1 m at scale 0.01 -> 100 BU; and back.
        self.assertAlmostEqual(to_blender_length(1, "m", Scene), 100.0)
        self.assertAlmostEqual(from_blender_length(100.0, "m", Scene), 1.0)

    def test_default_unit_is_metres(self):
        # Absent unit -> raw values unchanged (backward compatible).
        self.assertAlmostEqual(to_blender_length(10, None), 10.0)

    def test_materialize_millimetres(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        tree = bpy.data.node_groups.new("Car", TREE_IDNAME)
        car = tree.nodes.new("SysMLNodePartDef")
        car.element_name = "Car"
        car["sysml_shape"] = "Cuboid"
        car["sysml_unit"] = "mm"
        car["sysml_dim_length"] = 4800.0
        car["sysml_dim_width"] = 1840.0
        car["sysml_dim_height"] = 1350.0

        sysml_geometry.materialize_tree(tree)
        obj = object_for_node(car)
        self.assertEqual(_dims(obj), (4.8, 1.84, 1.35))


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
