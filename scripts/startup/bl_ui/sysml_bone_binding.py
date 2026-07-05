# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Node <-> armature bone binding for the SysML animation layer (Animation
Binding A / SCRUM-646).

The animation counterpart of the geometry node<->object binding. A bone is not a
datablock, so the binding is split across the two things that *are* reliably
managed:

* the **armature object** holds ``sysml_tree`` — the SysML node tree it rigs (a
  datablock reference Blender keeps valid across save/reload and nulls on delete);
* each **bone** holds ``sysml_node`` — the bound node's name (a string, which
  survives on bone data without the ID-remap concerns of a datablock pointer).

So deleting the armature drops every bone binding, deleting the tree nulls the
tree reference, and .blend save/reload round-trips both. Bone rest data (a
bone-nature marker + head/tail/roll) rides on the node as custom properties, read
by the rig operator (SCRUM-647).
"""

import bpy

ARM_TREE_KEY = "sysml_tree"    # on the armature object -> node group (managed ID)
BONE_NODE_KEY = "sysml_node"   # on the bone -> node.name (string)

# Bone rest data carried on the node (populated/read by rig & capture).
BONE_KEY = "sysml_bone"        # marker: this part is a bone
BONE_HEAD_KEY = "sysml_bone_head"
BONE_TAIL_KEY = "sysml_bone_tail"
BONE_ROLL_KEY = "sysml_bone_roll"


def is_bone_part(node):
    """True when `node` is marked as a bone-nature part."""
    return bool(node.get(BONE_KEY))


def bind_bone(node, armature_obj, bone):
    """Bind SysML `node` to `bone` inside `armature_obj`. Returns `bone`."""
    armature_obj[ARM_TREE_KEY] = node.id_data
    bone[BONE_NODE_KEY] = node.name
    return bone


def unbind_bone(bone):
    """Remove the binding marker from `bone` (leaves the armature's tree ref,
    which other bones may still use)."""
    if BONE_NODE_KEY in bone:
        del bone[BONE_NODE_KEY]


def node_for_bone(armature_obj, bone):
    """The live SysML node bound to `bone`, or None."""
    tree = armature_obj.get(ARM_TREE_KEY)
    if tree is None:
        return None
    return tree.nodes.get(bone.get(BONE_NODE_KEY, ""))


def bone_for_node(node):
    """(armature_obj, bone) bound to `node`, or None (scans armatures)."""
    tree = node.id_data
    name = node.name
    for obj in bpy.data.objects:
        if obj.type != 'ARMATURE' or obj.get(ARM_TREE_KEY) != tree:
            continue
        for bone in obj.data.bones:
            if bone.get(BONE_NODE_KEY) == name:
                return obj, bone
    return None


def is_bone_bound(armature_obj, bone):
    """True when `bone` resolves to a live SysML node."""
    return node_for_bone(armature_obj, bone) is not None


def bound_bones(tree):
    """Yield (armature_obj, bone, node) for every bone bound into `tree`."""
    for obj in bpy.data.objects:
        if obj.type != 'ARMATURE' or obj.get(ARM_TREE_KEY) != tree:
            continue
        for bone in obj.data.bones:
            node = tree.nodes.get(bone.get(BONE_NODE_KEY, ""))
            if node is not None:
                yield obj, bone, node
