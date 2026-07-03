# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Generated SysML shape -> Blender primitive resolver (Geometry Binding A / SCRUM-625).

Validates the generated `SHAPE_RESOLVER` (produced by
tools/sysml/gen_geometry_shapes.py from the bundled Geometry library): every
starter shape maps to the expected Blender primitive with its attributes bound
to the op's parameters, subtypes inherit their base, and every op is a real
`bpy.ops.mesh` primitive. Byte-stable regeneration is enforced separately by the
SysML regen-diff CI gate.
"""

import sys
import unittest

import bpy

from bl_ui.sysml_geometry_shapes_generated import SHAPE_RESOLVER


class SysMLShapeResolverTest(unittest.TestCase):
    def test_starter_set_present(self):
        for shape in ("Cuboid", "Box", "RectangularCuboid", "Sphere",
                      "Cylinder", "Cone", "Torus"):
            self.assertIn(shape, SHAPE_RESOLVER, f"resolver missing shape {shape}")

    def test_expected_primitive_mappings(self):
        expect = {
            "Cuboid": ("primitive_cube_add", {}, ["length", "width", "height"]),
            "Sphere": ("primitive_uv_sphere_add", {"radius": "radius"}, None),
            "Cylinder": ("primitive_cylinder_add", {"radius": "radius", "depth": "height"}, None),
            "Cone": ("primitive_cone_add", {"radius1": "radius", "depth": "height"}, None),
            "Torus": ("primitive_torus_add",
                      {"major_radius": "majorRadius", "minor_radius": "minorRadius"}, None),
        }
        for shape, (op, params, dims) in expect.items():
            entry = SHAPE_RESOLVER[shape]
            self.assertEqual(entry["op"], op, shape)
            self.assertEqual(entry["params"], params, shape)
            self.assertEqual(entry["dimensions"], dims, shape)

    def test_subtypes_inherit_base(self):
        for sub in ("Box", "RectangularCuboid"):
            self.assertEqual(SHAPE_RESOLVER[sub]["op"], SHAPE_RESOLVER["Cuboid"]["op"])
            self.assertEqual(SHAPE_RESOLVER[sub]["dimensions"],
                             SHAPE_RESOLVER["Cuboid"]["dimensions"])

    def test_ops_are_real_blender_primitives(self):
        for shape, entry in SHAPE_RESOLVER.items():
            self.assertTrue(hasattr(bpy.ops.mesh, entry["op"]),
                            f"{shape}: bpy.ops.mesh.{entry['op']} does not exist")

    def test_entry_shape_is_wellformed(self):
        for shape, entry in SHAPE_RESOLVER.items():
            self.assertEqual(set(entry), {"op", "params", "dimensions"}, shape)
            self.assertIsInstance(entry["params"], dict, shape)
            self.assertTrue(entry["dimensions"] is None or isinstance(entry["dimensions"], list),
                            shape)


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
