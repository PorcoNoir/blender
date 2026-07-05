# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""SysML behavior -> Blender Actions / NLA strips (Animation Binding A / SCRUM-650).

Where keyframing (SCRUM-649) writes one live animation, behavior maps named
SysML states onto Blender's reusable clip layer:

* a **State** node (``SysMLNodeStateUsage`` / ``StateDef``) carrying a
  ``sysml_poses`` JSON map ``{bone_name: [{t, loc, rot}, ...]}`` becomes a Blender
  **Action** ("SysML State: <name>") holding that clip's keyframes;
* **Succession** nodes (``SysMLNodeSuccessionUsage``) carry the transition
  endpoints as ``sysml_from`` / ``sysml_to`` element names (the node's element
  sockets don't model source/target), ordering the states into a chain;
* the ordered clips are laid end-to-end as **NLA strips** on one track
  ("SysML States").

Deterministic: the track and our prior state Actions are removed and rebuilt, so
re-running updates rather than duplicating.
"""

import json

import bpy

from bl_ui import sysml_armature
from bl_ui.sysml_time import TIME_UNIT_KEY, DEFAULT_TIME_UNIT, to_frame

POSES_KEY = "sysml_poses"
SUCC_FROM_KEY = "sysml_from"
SUCC_TO_KEY = "sysml_to"

STATE_IDNAMES = {"SysMLNodeStateUsage", "SysMLNodeStateDef"}
SUCC_IDNAME = "SysMLNodeSuccessionUsage"
NLA_TRACK_NAME = "SysML States"
ACTION_PREFIX = "SysML State: "


def _ordered_states(tree):
    """State nodes with poses, chained by successions (start -> ... -> end)."""
    states = [n for n in tree.nodes if n.bl_idname in STATE_IDNAMES and POSES_KEY in n]
    by_key = {n.name: n for n in states}
    by_element = {(n.element_name or n.name): n for n in states}

    nexts = {}
    indeg = {n.name: 0 for n in states}
    for node in tree.nodes:
        if node.bl_idname != SUCC_IDNAME:
            continue
        src = by_element.get(node.get(SUCC_FROM_KEY))
        dst = by_element.get(node.get(SUCC_TO_KEY))
        if src is not None and dst is not None and src is not dst:
            nexts[src.name] = dst.name
            indeg[dst.name] += 1

    order, visited = [], set()
    # Follow each chain from a state with no predecessor (stable by node order).
    for start in ([n for n in states if indeg[n.name] == 0] or states):
        cur = start.name
        while cur and cur not in visited:
            visited.add(cur)
            order.append(by_key[cur])
            cur = nexts.get(cur)
    for n in states:  # any leftover (cycles) in stable order
        if n.name not in visited:
            visited.add(n.name)
            order.append(n)
    return order


def _build_state_action(arm, ad, state, scene):
    """A fresh Action holding `state`'s pose clip. Returns (action, length)."""
    action = bpy.data.actions.new(ACTION_PREFIX + (state.element_name or state.name))
    ad.action = action

    poses = {}
    try:
        poses = json.loads(state.get(POSES_KEY) or "{}")
    except (ValueError, TypeError):
        poses = {}
    unit = state.get(TIME_UNIT_KEY, DEFAULT_TIME_UNIT)

    first = last = None
    for bone_name, snaps in poses.items():
        pbone = arm.pose.bones.get(bone_name)
        if pbone is None:
            continue
        pbone.rotation_mode = 'QUATERNION'
        for snap in sorted(snaps, key=lambda s: float(s.get("t", 0.0))):
            frame = round(to_frame(snap.get("t", 0.0), unit, scene))
            loc, rot = snap.get("loc"), snap.get("rot")
            if loc is not None:
                pbone.location = loc
                pbone.keyframe_insert("location", frame=frame)
            if rot is not None:
                pbone.rotation_quaternion = rot
                pbone.keyframe_insert("rotation_quaternion", frame=frame)
            if loc is not None or rot is not None:
                first = frame if first is None else min(first, frame)
                last = frame if last is None else max(last, frame)

    length = 0 if first is None else (last - first)
    return action, length


def build_behavior(tree, scene=None):
    """Realise states as Actions sequenced as NLA strips. Returns strip count."""
    scene = scene or bpy.context.scene

    arm = sysml_armature._find_rig_armature(tree)
    if arm is None:
        sysml_armature.rig_tree(tree)
        arm = sysml_armature._find_rig_armature(tree)
    if arm is None:
        return 0

    ad = arm.animation_data_create()

    # Clean slate: drop our NLA track, then the now-unreferenced state Actions.
    for track in [t for t in ad.nla_tracks if t.name == NLA_TRACK_NAME]:
        ad.nla_tracks.remove(track)
    ad.action = None
    for action in [a for a in bpy.data.actions if a.name.startswith(ACTION_PREFIX)]:
        if action.users == 0:
            bpy.data.actions.remove(action)

    states = _ordered_states(tree)
    if not states:
        return 0

    track = ad.nla_tracks.new()
    track.name = NLA_TRACK_NAME

    start = int(scene.frame_start)
    count = 0
    for state in states:
        action, length = _build_state_action(arm, ad, state, scene)
        ad.action = None  # detach so the strip owns the action
        strip = track.strips.new(action.name, start, action)
        strip.frame_end = start + max(length, 1)
        start = int(strip.frame_end)
        count += 1

    ad.action = None  # NLA drives; no live action
    return count


class NODE_OT_sysml_behavior(bpy.types.Operator):
    """Build Blender Actions + NLA strips from the SysML state behavior"""
    bl_idname = "node.sysml_behavior"
    bl_label = "Build SysML Behavior"
    bl_options = {'REGISTER', 'UNDO'}

    tree_name: bpy.props.StringProperty(
        name="Tree",
        description="SysML node tree to build behavior for (defaults to the active editor's tree)",
        options={'SKIP_SAVE'},
    )

    def execute(self, context):
        tree = None
        if self.tree_name:
            tree = bpy.data.node_groups.get(self.tree_name)
        elif getattr(context.space_data, "edit_tree", None):
            tree = context.space_data.edit_tree
        if tree is None or tree.bl_idname != "SysMLNodeTree":
            self.report({'ERROR'}, "No SysML node tree for behavior")
            return {'CANCELLED'}

        count = build_behavior(tree, context.scene)
        self.report({'INFO'}, f"Built {count} state strip{'' if count == 1 else 's'}")
        return {'FINISHED'}


classes = (
    NODE_OT_sysml_behavior,
)
