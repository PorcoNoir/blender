# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Node <-> Blender object binding for the SysML geometry layer (Geometry
Binding A / SCRUM-626).

The binding ties a SysML part node to the Blender object that represents it in
3D. It is stored **on the object** as managed ID custom properties:

* ``sysml_tree`` — the SysML node tree the object belongs to (a datablock
  reference Blender keeps valid across ``.blend`` save/reload and nulls
  automatically when the tree is deleted).
* ``sysml_node`` — the bound node's name within that tree.

Storing it object-side gets the whole data-model contract for free: deleting the
object drops the binding, deleting the tree nulls it, and save/reload round-trips
it — no dangling pointers, no C++ DNA field, no custom ID-remap plumbing.
``object_for_node`` scans objects (fine for the manual materialize/reverse of
Phase A); the live-sync phase can back it with an index.
"""

import bpy

TREE_KEY = "sysml_tree"
NODE_KEY = "sysml_node"


def bind(node, obj):
    """Bind SysML `node` to Blender `obj`. Returns `obj`."""
    obj[TREE_KEY] = node.id_data
    obj[NODE_KEY] = node.name
    return obj


def unbind(obj):
    """Remove any binding markers from `obj`."""
    for key in (TREE_KEY, NODE_KEY):
        if key in obj:
            del obj[key]


def element_for_object(obj):
    """The live SysML node bound to `obj`, or None."""
    tree = obj.get(TREE_KEY)
    if tree is None:
        return None
    return tree.nodes.get(obj.get(NODE_KEY, ""))


def object_for_node(node):
    """The Blender object bound to `node`, or None (scans objects)."""
    tree = node.id_data
    name = node.name
    for obj in bpy.data.objects:
        if obj.get(TREE_KEY) == tree and obj.get(NODE_KEY) == name:
            return obj
    return None


def is_bound(obj):
    """True when `obj` resolves to a live SysML node."""
    return element_for_object(obj) is not None


def bound_objects(tree):
    """Yield (object, node) for every object bound into `tree`."""
    for obj in bpy.data.objects:
        if obj.get(TREE_KEY) == tree:
            node = tree.nodes.get(obj.get(NODE_KEY, ""))
            if node is not None:
                yield obj, node
