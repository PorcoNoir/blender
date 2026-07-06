# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Guided rigging/animation methodology (Animation Binding B / SCRUM-654).

One-step actions that each produce valid SysML *and* the matching Blender rig /
animation, in the spirit of Syson's methodology support:

* **add bone chain** — N bone-part nodes chained by containment, with stacked
  rest transforms, then rigged into a parented bone chain;
* **build IK from connection** — stamp an existing bone-part connection as an IK
  joint and re-rig it into a pose-bone IK constraint;
* **keyframe pose** — snapshot each bound bone's current pose at the current
  frame into the graph and re-keyframe (the graph gains an Occurrence snapshot,
  the rig gains a keyframe).

The operators are RNA-visible (searchable) and surfaced in a "SysML Rigging"
menu in the node editor header.
"""

import json

import bpy
from bpy.types import Menu

from bl_ui.sysml_armature import rig_tree, CONSTRAINT_KEY, _find_rig_armature
from bl_ui.sysml_animate import keyframe_tree, SNAPSHOTS_KEY
from bl_ui.sysml_bone_binding import (
    BONE_KEY, BONE_HEAD_KEY, BONE_TAIL_KEY, bound_bones,
)
from bl_ui.sysml_time import TIME_UNIT_KEY, from_frame

_TREE_IDNAME = "SysMLNodeTree"


# --- templates ----------------------------------------------------------------

def add_bone_chain(tree, count=3, length=1.0, prefix="Bone"):
    """Create a containment-chained bone-part run and rig it. Returns the nodes."""
    nodes = []
    for i in range(count):
        node = tree.nodes.new("SysMLNodePartUsage")
        node.element_name = "{}{}".format(prefix, i + 1)
        node[BONE_KEY] = 1
        node[BONE_HEAD_KEY] = (0.0, 0.0, i * length)
        node[BONE_TAIL_KEY] = (0.0, 0.0, (i + 1) * length)
        node.location = (0.0, -160.0 * i)
        nodes.append(node)
    # Each bone is contained by its predecessor -> bone parent/child on rig.
    for i in range(1, count):
        tree.links.new(nodes[i].outputs["Self"], nodes[i - 1].inputs["Members"])
    rig_tree(tree)
    return nodes


def build_ik(tree, connection_node):
    """Turn an existing bone-part connection into an IK joint and re-rig."""
    connection_node[CONSTRAINT_KEY] = "IK"
    rig_tree(tree)
    return connection_node


def keyframe_pose(tree, scene=None):
    """Snapshot every bound bone's current pose at the current frame + re-keyframe.

    Returns the number of bones snapshotted.
    """
    scene = scene or bpy.context.scene
    arm = _find_rig_armature(tree)
    if arm is None:
        return 0
    frame = scene.frame_current
    t = round(from_frame(frame, "s", scene), 6)
    touched = 0
    for _obj, bone, node in bound_bones(tree):
        pbone = arm.pose.bones.get(bone.name)
        if pbone is None:
            continue
        snap = {
            "t": t,
            "loc": [round(v, 6) for v in pbone.location],
            "rot": [round(v, 6) for v in pbone.rotation_quaternion],
        }
        try:
            snaps = json.loads(node.get(SNAPSHOTS_KEY) or "[]")
        except (ValueError, TypeError):
            snaps = []
        snaps = [s for s in snaps if round(float(s.get("t", 0.0)), 6) != t]
        snaps.append(snap)
        snaps.sort(key=lambda s: float(s["t"]))
        node[SNAPSHOTS_KEY] = json.dumps(snaps)
        node[TIME_UNIT_KEY] = "s"
        touched += 1
    keyframe_tree(tree, scene)
    return touched


# --- operators ----------------------------------------------------------------

def _resolve_tree(op, context, create=False):
    if op.tree_name:
        tree = bpy.data.node_groups.get(op.tree_name)
        if tree is not None:
            return tree
    edit = getattr(context.space_data, "edit_tree", None)
    if edit is not None and edit.bl_idname == _TREE_IDNAME:
        return edit
    if create:
        return bpy.data.node_groups.new(op.tree_name or "SysML Rig", _TREE_IDNAME)
    return None


class NODE_OT_sysml_add_bone_chain(bpy.types.Operator):
    """Add a chained run of bone parts and rig it"""
    bl_idname = "node.sysml_add_bone_chain"
    bl_label = "Add Bone Chain"
    bl_options = {'REGISTER', 'UNDO'}

    tree_name: bpy.props.StringProperty(options={'SKIP_SAVE'})
    count: bpy.props.IntProperty(name="Bones", default=3, min=1, max=64)
    length: bpy.props.FloatProperty(name="Bone Length", default=1.0, min=0.001)

    def execute(self, context):
        tree = _resolve_tree(self, context, create=True)
        nodes = add_bone_chain(tree, self.count, self.length)
        self.report({'INFO'}, f"Added {len(nodes)}-bone chain")
        return {'FINISHED'}


class NODE_OT_sysml_build_ik(bpy.types.Operator):
    """Make the named bone-part connection an IK joint and re-rig"""
    bl_idname = "node.sysml_build_ik"
    bl_label = "Build IK from Connection"
    bl_options = {'REGISTER', 'UNDO'}

    tree_name: bpy.props.StringProperty(options={'SKIP_SAVE'})
    connection_name: bpy.props.StringProperty(name="Connection", options={'SKIP_SAVE'})

    def execute(self, context):
        tree = _resolve_tree(self, context)
        if tree is None:
            self.report({'ERROR'}, "No SysML node tree")
            return {'CANCELLED'}
        conn = next((n for n in tree.nodes
                     if n.bl_idname == "SysMLNodeConnectionUsage"
                     and (n.element_name or n.name) == self.connection_name), None)
        if conn is None:
            self.report({'ERROR'}, f"No connection '{self.connection_name}'")
            return {'CANCELLED'}
        build_ik(tree, conn)
        self.report({'INFO'}, "Built IK joint")
        return {'FINISHED'}


class NODE_OT_sysml_keyframe_pose(bpy.types.Operator):
    """Snapshot the current pose into the graph and re-keyframe"""
    bl_idname = "node.sysml_keyframe_pose"
    bl_label = "Keyframe Pose"
    bl_options = {'REGISTER', 'UNDO'}

    tree_name: bpy.props.StringProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        tree = _resolve_tree(self, context)
        if tree is None:
            self.report({'ERROR'}, "No SysML node tree")
            return {'CANCELLED'}
        n = keyframe_pose(tree, context.scene)
        self.report({'INFO'}, f"Keyframed {n} bone{'' if n == 1 else 's'}")
        return {'FINISHED'}


# --- menu ---------------------------------------------------------------------

class NODE_MT_sysml_methodology(Menu):
    bl_idname = "NODE_MT_sysml_methodology"
    bl_label = "SysML Rigging"

    def draw(self, _context):
        layout = self.layout
        layout.operator(NODE_OT_sysml_add_bone_chain.bl_idname)
        layout.operator(NODE_OT_sysml_build_ik.bl_idname)
        layout.operator(NODE_OT_sysml_keyframe_pose.bl_idname)


def _menu_draw(self, context):
    if getattr(context.space_data, "tree_type", "") == _TREE_IDNAME:
        self.layout.menu(NODE_MT_sysml_methodology.bl_idname)


_menu_installed = False


def install_menu():
    global _menu_installed
    menus = getattr(bpy.types, "NODE_MT_editor_menus", None)
    if menus is not None and not _menu_installed:
        try:
            menus.append(_menu_draw)
            _menu_installed = True
        except Exception:  # noqa: BLE001
            pass


def uninstall_menu():
    global _menu_installed
    menus = getattr(bpy.types, "NODE_MT_editor_menus", None)
    if menus is not None and _menu_installed:
        try:
            menus.remove(_menu_draw)
        except Exception:  # noqa: BLE001
            pass
        _menu_installed = False


classes = (
    NODE_OT_sysml_add_bone_chain,
    NODE_OT_sysml_build_ik,
    NODE_OT_sysml_keyframe_pose,
    NODE_MT_sysml_methodology,
)


# Surface the menu once the node-editor menu type exists (after startup).
def _deferred_menu_install():
    install_menu()
    return None


try:
    bpy.app.timers.register(_deferred_menu_install, first_interval=0.0)
except Exception:  # noqa: BLE001 - timers unavailable headless is fine
    pass
