# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Materialize a SysML graph into Blender objects (Geometry Binding A / SCRUM-627).

Walks a SysML node tree and, for every part node that carries geometry data,
creates a bound Blender object whose mesh is the primitive the shape resolves to
(SCRUM-625), sized from the shape's dimensions, and parented per the `members`
containment links. Re-running rebuilds the tree's objects in place — the graph is
the source of truth — so it never duplicates.

Geometry data lives on the node as custom properties (the graph carrying the
shape, since the node storage itself is name/multiplicity/flag): `sysml_shape`
names the resolved shape (e.g. "Cuboid"); `sysml_dim_<attr>` gives each dimension
(e.g. `sysml_dim_length`). These are written by the import annotation / reverse
(SCRUM-630) and read here.

Transforms from coordinate frames are not yet modeled (the bundled SpatialItems
subset has no frame), so materialized objects sit at the origin for now.
"""

import bpy

from bl_ui.sysml_binding import TREE_KEY, bind, object_for_node
from bl_ui.sysml_geometry_shapes_generated import SHAPE_RESOLVER

SHAPE_KEY = "sysml_shape"
DIM_PREFIX = "sysml_dim_"

# CSG: a shape-bearing node combines its own primitive (the base) with operand
# objects (referenced by SysML element name) via Boolean modifiers. Mirrors the
# standard library's differencesOf / unionsOf / intersectionsOf.
CSG_KEY = "sysml_csg"
CSG_OPERANDS_KEY = "sysml_csg_operands"
CSG_OP = {"difference": 'DIFFERENCE', "union": 'UNION', "intersect": 'INTERSECT'}


def shape_of(node):
    """The resolved shape name carried by `node`, or None."""
    shape = node.get(SHAPE_KEY)
    return shape if shape in SHAPE_RESOLVER else None


def _dims(node):
    return {key[len(DIM_PREFIX):]: float(node[key])
            for key in node.keys() if key.startswith(DIM_PREFIX)}


def _make_object(node):
    """Create a bound mesh object for `node`'s shape; None if it has no shape."""
    shape = shape_of(node)
    if shape is None:
        return None
    entry = SHAPE_RESOLVER[shape]
    dims = _dims(node)

    kwargs = {kw: dims[attr] for kw, attr in entry["params"].items() if attr in dims}
    getattr(bpy.ops.mesh, entry["op"])(**kwargs)
    obj = bpy.context.active_object
    obj.name = node.element_name or node.name

    if entry["dimensions"]:
        target = tuple(dims.get(attr, 1.0) for attr in entry["dimensions"])
        obj.dimensions = target
        bpy.context.view_layer.update()

    bind(node, obj)
    return obj


def materialize_tree(tree):
    """(Re)build the Blender objects for `tree`. Returns the object count."""
    # Clean slate: drop anything previously materialized from this tree so the
    # rebuild is idempotent (no duplicates).
    for obj in [o for o in bpy.data.objects if o.get(TREE_KEY) == tree]:
        bpy.data.objects.remove(obj)

    node_to_obj = {}
    by_element = {}
    for node in tree.nodes:
        obj = _make_object(node)
        if obj is not None:
            node_to_obj[node.name] = obj
            if node.element_name:
                by_element[node.element_name] = obj

    # Parent per containment: a `members` link runs child.self -> parent.members.
    for link in tree.links:
        if link.to_socket.identifier != "members":
            continue
        child = node_to_obj.get(link.from_node.name)
        parent = node_to_obj.get(link.to_node.name)
        if child and parent and child is not parent:
            child.parent = parent
            child.matrix_parent_inverse = parent.matrix_world.inverted()

    _apply_csg(tree, node_to_obj, by_element)
    return len(node_to_obj)


def _apply_csg(tree, node_to_obj, by_element):
    """Add Boolean modifiers to CSG-carrier objects; hide the operand cutters."""
    for node in tree.nodes:
        op = node.get(CSG_KEY)
        if op not in CSG_OP:
            continue
        result = node_to_obj.get(node.name)
        if result is None:
            continue
        for operand_name in (n.strip() for n in node.get(CSG_OPERANDS_KEY, "").split(",")):
            target = by_element.get(operand_name)
            if target is None or target is result:
                continue
            modifier = result.modifiers.new(name=f"SysML CSG {operand_name}", type='BOOLEAN')
            modifier.operation = CSG_OP[op]
            modifier.object = target
            # The cutter is consumed by the boolean: hide it and group it under
            # the result so it travels with it.
            target.hide_viewport = True
            target.hide_render = True
            if target.parent is None:
                target.parent = result
                target.matrix_parent_inverse = result.matrix_world.inverted()


class NODE_OT_sysml_materialize(bpy.types.Operator):
    """Build Blender objects from the SysML geometry graph"""
    bl_idname = "node.sysml_materialize"
    bl_label = "Materialize SysML Geometry"
    bl_options = {'REGISTER', 'UNDO'}

    tree_name: bpy.props.StringProperty(
        name="Tree",
        description="SysML node tree to materialize (defaults to the active editor's tree)",
        options={'SKIP_SAVE'},
    )

    def execute(self, context):
        tree = None
        if self.tree_name:
            tree = bpy.data.node_groups.get(self.tree_name)
        elif getattr(context.space_data, "edit_tree", None):
            tree = context.space_data.edit_tree
        if tree is None or tree.bl_idname != "SysMLNodeTree":
            self.report({'ERROR'}, "No SysML node tree to materialize")
            return {'CANCELLED'}

        count = materialize_tree(tree)
        self.report({'INFO'}, f"Materialized {count} SysML object{'' if count == 1 else 's'}")
        return {'FINISHED'}


classes = (
    NODE_OT_sysml_materialize,
)
