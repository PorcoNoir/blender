# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Rig a SysML graph into a Blender armature (Animation Binding A / SCRUM-647).

The animation counterpart of geometry materialize. Walks a SysML node tree and,
for every bone-nature part, creates a bone in a single Armature: the bone's rest
transform (head/tail/roll) comes from the node's bone data, and bones are
parented per the `members` containment links. Re-running rebuilds the bones in
the tree's armature in place, so it never duplicates. Each node is bound to its
bone (SCRUM-646).

Bone data rides on the node as custom properties (`sysml_bone` marker +
`sysml_bone_head` / `_tail` / `_roll`), written by capture (SCRUM-651) / an import
annotation; read here.
"""

import bpy

from bl_ui.sysml_bone_binding import (
    ARM_TREE_KEY, BONE_HEAD_KEY, BONE_TAIL_KEY, BONE_ROLL_KEY,
    bind_bone, is_bone_part,
)

_DEFAULT_HEAD = (0.0, 0.0, 0.0)
_DEFAULT_TAIL = (0.0, 0.0, 1.0)


def _find_rig_armature(tree):
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE' and obj.get(ARM_TREE_KEY) == tree:
            return obj
    return None


def rig_tree(tree):
    """(Re)build the armature for `tree`. Returns the bone count."""
    arm = _find_rig_armature(tree)
    if arm is None:
        arm = bpy.data.objects.new(tree.name, bpy.data.armatures.new(tree.name))
        bpy.context.scene.collection.objects.link(arm)
    arm[ARM_TREE_KEY] = tree

    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    edit_bones = arm.data.edit_bones
    for existing in list(edit_bones):
        edit_bones.remove(existing)  # clean slate -> idempotent rebuild

    node_to_bone = {}
    for node in tree.nodes:
        if not is_bone_part(node):
            continue
        eb = edit_bones.new(node.element_name or node.name)
        eb.head = tuple(node.get(BONE_HEAD_KEY, _DEFAULT_HEAD))
        eb.tail = tuple(node.get(BONE_TAIL_KEY, _DEFAULT_TAIL))
        eb.roll = float(node.get(BONE_ROLL_KEY, 0.0))
        node_to_bone[node.name] = eb.name

    # Parent per containment: a `members` link runs child.self -> parent.members.
    for link in tree.links:
        if link.to_socket.identifier != "members":
            continue
        child = node_to_bone.get(link.from_node.name)
        parent = node_to_bone.get(link.to_node.name)
        if child and parent and child != parent:
            edit_bones[child].parent = edit_bones[parent]

    bpy.ops.object.mode_set(mode='OBJECT')

    # Bind each node to its (now-existing) data bone.
    for node in tree.nodes:
        bone_name = node_to_bone.get(node.name)
        if bone_name and bone_name in arm.data.bones:
            bind_bone(node, arm, arm.data.bones[bone_name])

    return len(node_to_bone)


class NODE_OT_sysml_rig(bpy.types.Operator):
    """Build a Blender armature from the SysML skeleton graph"""
    bl_idname = "node.sysml_rig"
    bl_label = "Rig SysML Skeleton"
    bl_options = {'REGISTER', 'UNDO'}

    tree_name: bpy.props.StringProperty(
        name="Tree",
        description="SysML node tree to rig (defaults to the active editor's tree)",
        options={'SKIP_SAVE'},
    )

    def execute(self, context):
        tree = None
        if self.tree_name:
            tree = bpy.data.node_groups.get(self.tree_name)
        elif getattr(context.space_data, "edit_tree", None):
            tree = context.space_data.edit_tree
        if tree is None or tree.bl_idname != "SysMLNodeTree":
            self.report({'ERROR'}, "No SysML node tree to rig")
            return {'CANCELLED'}

        count = rig_tree(tree)
        self.report({'INFO'}, f"Rigged {count} bone{'' if count == 1 else 's'}")
        return {'FINISHED'}


classes = (
    NODE_OT_sysml_rig,
)
