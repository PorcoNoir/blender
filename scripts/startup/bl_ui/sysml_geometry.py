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

from bl_ui.sysml_binding import TREE_KEY, bind, element_for_object, object_for_node
from bl_ui.sysml_geometry_shapes_generated import SHAPE_RESOLVER
from bl_ui.sysml_units import UNIT_KEY, DEFAULT_UNIT, to_blender_length, from_blender_length

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
    """Dimension attribute -> length in Blender units (unit-converted)."""
    unit = node.get(UNIT_KEY, DEFAULT_UNIT)
    scene = bpy.context.scene
    return {key[len(DIM_PREFIX):]: to_blender_length(node[key], unit, scene)
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
    # Stamp the shape identity on the object so reverse recovers it exactly
    # (a mesh alone can't be told apart as sphere vs cylinder vs ...).
    obj[SHAPE_KEY] = shape
    obj[UNIT_KEY] = node.get(UNIT_KEY, DEFAULT_UNIT)
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


# -------------------------------------------------------------------------- #
# Reverse: Blender objects -> SysML part nodes (SCRUM-630)                    #
# -------------------------------------------------------------------------- #

_CSG_FROM_BLENDER = {'DIFFERENCE': "difference", 'UNION': "union", 'INTERSECT': "intersect"}


def _infer_shape(obj):
    """The SysML shape for `obj`: its stamped shape, else a box guess, else None."""
    stamped = obj.get(SHAPE_KEY)
    if stamped in SHAPE_RESOLVER:
        return stamped
    if obj.type == "MESH" and len(obj.data.vertices) == 8:
        return "Cuboid"
    return None


def _extract_dims(shape, size):
    """Blender-unit object dimensions (x, y, z) -> shape attribute -> length,
    the inverse of the resolver's forward mapping."""
    x, y, z = size
    if shape in ("Cuboid", "Box", "RectangularCuboid"):
        return {"length": x, "width": y, "height": z}
    if shape == "Sphere":
        return {"radius": x / 2.0}
    if shape in ("Cylinder", "Cone"):
        return {"radius": x / 2.0, "height": z}
    if shape == "Torus":
        minor = z / 2.0
        return {"majorRadius": x / 2.0 - minor, "minorRadius": minor}
    return {}


def _ensure_members_link(tree, child, parent):
    self_out = child.outputs.get("Self")
    members_in = parent.inputs.get("Members")
    if self_out is None or members_in is None:
        return
    for link in tree.links:
        if (link.from_node == child and link.to_node == parent
                and link.to_socket.identifier == "members"):
            return
    tree.links.new(self_out, members_in)


def reverse_objects(objects, tree):
    """Read `objects` into `tree` as SysML part nodes. Idempotent: bound objects
    update their node; unbound objects get a new node. Returns the node count."""
    scene = bpy.context.scene
    obj_to_node = {}
    for obj in sorted(objects, key=lambda o: o.name):
        node = element_for_object(obj)
        if node is None:
            node = tree.nodes.new("SysMLNodePartUsage")
            node.element_name = obj.name
            bind(node, obj)
        shape = _infer_shape(obj)
        if shape is not None:
            unit = obj.get(UNIT_KEY, DEFAULT_UNIT)
            node[SHAPE_KEY] = shape
            node[UNIT_KEY] = unit
            for key in [k for k in node.keys() if k.startswith(DIM_PREFIX)]:
                del node[key]
            for attr, bu in _extract_dims(shape, tuple(obj.dimensions)).items():
                node[DIM_PREFIX + attr] = from_blender_length(bu, unit, scene)
        obj_to_node[obj] = node

    for obj, node in obj_to_node.items():
        if obj.parent in obj_to_node:
            _ensure_members_link(tree, node, obj_to_node[obj.parent])
        booleans = [m for m in obj.modifiers
                    if m.type == 'BOOLEAN' and m.object in obj_to_node]
        if booleans:
            node[CSG_KEY] = _CSG_FROM_BLENDER[booleans[0].operation]
            node[CSG_OPERANDS_KEY] = ",".join(
                obj_to_node[m.object].element_name for m in booleans)

    return len(obj_to_node)


class NODE_OT_sysml_reverse(bpy.types.Operator):
    """Read the selected Blender objects into the SysML geometry graph"""
    bl_idname = "node.sysml_reverse"
    bl_label = "Reverse SysML Geometry"
    bl_options = {'REGISTER', 'UNDO'}

    tree_name: bpy.props.StringProperty(
        name="Tree",
        description="SysML node tree to reverse into (defaults to the active editor's tree)",
        options={'SKIP_SAVE'},
    )

    def execute(self, context):
        tree = None
        if self.tree_name:
            tree = bpy.data.node_groups.get(self.tree_name)
        elif getattr(context.space_data, "edit_tree", None):
            tree = context.space_data.edit_tree
        if tree is None or tree.bl_idname != "SysMLNodeTree":
            self.report({'ERROR'}, "No SysML node tree to reverse into")
            return {'CANCELLED'}

        objects = context.selected_objects or bpy.context.scene.objects
        count = reverse_objects(list(objects), tree)
        self.report({'INFO'}, f"Reversed {count} object{'' if count == 1 else 's'} into the graph")
        return {'FINISHED'}


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
    NODE_OT_sysml_reverse,
)
