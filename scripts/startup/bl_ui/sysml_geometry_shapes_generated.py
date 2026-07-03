# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# AUTO-GENERATED - DO NOT EDIT. Regenerate: python tools/sysml/gen_geometry_shapes.py
#
# SysML v2 Geometry shape (item def name) -> the Blender mesh primitive that
# materializes it (Geometry Binding A / SCRUM-625).
#   op         : bpy.ops.mesh.<op> that creates the primitive
#   params     : {op_kwarg: shape_attribute} feeding the op from shape attributes
#   dimensions : shape attributes used to set object.dimensions afterwards, or None

SHAPE_RESOLVER = {
    'Box': {
        "op": 'primitive_cube_add',
        "params": {},
        "dimensions": ['length', 'width', 'height'],
    },
    'Cone': {
        "op": 'primitive_cone_add',
        "params": {'radius1': 'radius', 'depth': 'height'},
        "dimensions": None,
    },
    'Cuboid': {
        "op": 'primitive_cube_add',
        "params": {},
        "dimensions": ['length', 'width', 'height'],
    },
    'Cylinder': {
        "op": 'primitive_cylinder_add',
        "params": {'radius': 'radius', 'depth': 'height'},
        "dimensions": None,
    },
    'RectangularCuboid': {
        "op": 'primitive_cube_add',
        "params": {},
        "dimensions": ['length', 'width', 'height'],
    },
    'Sphere': {
        "op": 'primitive_uv_sphere_add',
        "params": {'radius': 'radius'},
        "dimensions": None,
    },
    'Torus': {
        "op": 'primitive_torus_add',
        "params": {'major_radius': 'majorRadius', 'minor_radius': 'minorRadius'},
        "dimensions": None,
    },
}
