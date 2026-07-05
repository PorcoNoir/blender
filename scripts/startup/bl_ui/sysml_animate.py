# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Animate the rig from the SysML temporal model (Animation Binding A / SCRUM-649).

The animation counterpart of geometry materialize, for time: each bone-part's
`Occurrence` snapshots become pose keyframes on the bound bone. A snapshot rides
on the node as a JSON `sysml_snapshots` custom property -- a list of

    {"t": <time>, "loc": [x, y, z], "rot": [w, x, y, z]}

where `t` is a clock time in the node's `sysml_time_unit` (SCRUM-645), and loc/rot
are the pose-bone transform at that instant (both optional). The clock time maps
to a frame via the time<->frame bridge; loc/rot are keyframed there. The snapshot
span sets the scene's animation range.

Rigging is a prerequisite: if the tree has no armature yet, it is rigged first.
`animation_data_clear()` runs up front so re-animating replaces the keyframes
rather than stacking them.
"""

import json

import bpy

from bl_ui import sysml_armature
from bl_ui.sysml_bone_binding import bone_for_node, is_bone_part
from bl_ui.sysml_time import TIME_UNIT_KEY, DEFAULT_TIME_UNIT, to_frame

SNAPSHOTS_KEY = "sysml_snapshots"


def _snapshots(node):
    """Parsed snapshot list for `node`, oldest first, or []."""
    raw = node.get(SNAPSHOTS_KEY)
    if not raw:
        return []
    try:
        snaps = json.loads(raw)
    except (ValueError, TypeError):
        return []
    return sorted(snaps, key=lambda s: float(s.get("t", 0.0)))


def keyframe_tree(tree, scene=None):
    """Keyframe the tree's rig from every bone-part's snapshots.

    Returns the number of keyframed instants (snapshots applied to a bone).
    """
    scene = scene or bpy.context.scene

    arm = sysml_armature._find_rig_armature(tree)
    if arm is None:
        sysml_armature.rig_tree(tree)
        arm = sysml_armature._find_rig_armature(tree)
    if arm is None:
        return 0

    arm.animation_data_clear()  # deterministic: replace, never stack

    applied = 0
    frames = []
    for node in tree.nodes:
        if not is_bone_part(node):
            continue
        snaps = _snapshots(node)
        if not snaps:
            continue
        bound = bone_for_node(node)
        if bound is None:
            continue
        pbone = arm.pose.bones.get(bound[1].name)
        if pbone is None:
            continue
        pbone.rotation_mode = 'QUATERNION'
        unit = node.get(TIME_UNIT_KEY, DEFAULT_TIME_UNIT)
        for snap in snaps:
            frame = round(to_frame(snap.get("t", 0.0), unit, scene))
            loc = snap.get("loc")
            rot = snap.get("rot")
            if loc is not None:
                pbone.location = loc
                pbone.keyframe_insert("location", frame=frame)
            if rot is not None:
                pbone.rotation_quaternion = rot
                pbone.keyframe_insert("rotation_quaternion", frame=frame)
            if loc is not None or rot is not None:
                frames.append(frame)
                applied += 1

    if frames:
        scene.frame_start = min(frames)
        scene.frame_end = max(frames)

    return applied


class NODE_OT_sysml_animate(bpy.types.Operator):
    """Keyframe the SysML rig from its Occurrence snapshots"""
    bl_idname = "node.sysml_animate"
    bl_label = "Animate SysML Rig"
    bl_options = {'REGISTER', 'UNDO'}

    tree_name: bpy.props.StringProperty(
        name="Tree",
        description="SysML node tree to animate (defaults to the active editor's tree)",
        options={'SKIP_SAVE'},
    )

    def execute(self, context):
        tree = None
        if self.tree_name:
            tree = bpy.data.node_groups.get(self.tree_name)
        elif getattr(context.space_data, "edit_tree", None):
            tree = context.space_data.edit_tree
        if tree is None or tree.bl_idname != "SysMLNodeTree":
            self.report({'ERROR'}, "No SysML node tree to animate")
            return {'CANCELLED'}

        count = keyframe_tree(tree, context.scene)
        self.report({'INFO'}, f"Keyframed {count} snapshot{'' if count == 1 else 's'}")
        return {'FINISHED'}


classes = (
    NODE_OT_sysml_animate,
)
