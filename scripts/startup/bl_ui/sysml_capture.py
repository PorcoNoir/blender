# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Capture a Blender Armature + animation back into a SysML graph
(Animation Binding A / SCRUM-651).

The reverse of rig (647) / animate (649) / behavior (650): read an existing
armature and its animation into a SysML node tree, mirroring each mapping the
other way --

* bones            -> bone-nature part nodes (rest transform -> head/tail/roll);
* bone parenting   -> `members` containment links;
* pose constraints -> connection nodes (`sysml_constraint` = constraint type);
* pose keyframes   -> Occurrence snapshots (frame -> clock time via the bridge);
* NLA strips       -> state nodes with pose clips, chained by successions.

It establishes the node<->bone binding, and is deterministic: existing bound
nodes are reused and updated in place rather than duplicated.
"""

import json

import bpy

from bl_ui import sysml_armature
from bl_ui.sysml_armature import CONSTRAINT_KEY, _CONSTRAINT_PREFIX
from bl_ui.sysml_animate import SNAPSHOTS_KEY
from bl_ui.sysml_behavior import (
    POSES_KEY, SUCC_FROM_KEY, SUCC_TO_KEY, NLA_TRACK_NAME, ACTION_PREFIX,
)
from bl_ui.sysml_bone_binding import (
    BONE_KEY, BONE_HEAD_KEY, BONE_TAIL_KEY, BONE_ROLL_KEY,
    bind_bone, is_bone_part, node_for_bone,
)
from bl_ui.sysml_time import TIME_UNIT_KEY, from_frame

_PART_IDNAME = "SysMLNodePartUsage"
_CONN_IDNAME = "SysMLNodeConnectionUsage"
_STATE_IDNAME = "SysMLNodeStateUsage"
_SUCC_IDNAME = "SysMLNodeSuccessionUsage"


# --- small helpers -----------------------------------------------------------

def _action_fcurves(action):
    """Fcurves of `action`, across the Blender 5.x slotted layers."""
    if action is None:
        return []
    if hasattr(action, "fcurves"):
        return list(action.fcurves)
    out = []
    for layer in action.layers:
        for strip in layer.strips:
            for cbag in strip.channelbags:
                out.extend(cbag.fcurves)
    return out


def _input_by_id(node, identifier):
    for sock in node.inputs:
        if sock.identifier == identifier:
            return sock
    return None


def _relink(tree, node, identifier, src_node):
    """Make `src_node`.self the sole link into `node`'s `identifier` input."""
    sock = _input_by_id(node, identifier)
    if sock is None:
        return
    for link in [l for l in tree.links if l.to_socket == sock]:
        tree.links.remove(link)
    tree.links.new(src_node.outputs["Self"], sock)


def _find_by_element(tree, idname, name):
    for node in tree.nodes:
        if node.bl_idname == idname and (node.element_name or node.name) == name:
            return node
    return None


def _read_rolls(arm):
    """Rest-bone roll per bone name (only edit bones expose roll)."""
    rolls = {}
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode='EDIT')
    for eb in arm.data.edit_bones:
        rolls[eb.name] = eb.roll
    bpy.ops.object.mode_set(mode='OBJECT')
    return rolls


def _bone_snapshots(action, bone_name, scene):
    """Occurrence snapshots for `bone_name` sampled from `action`'s keyframes."""
    base = 'pose.bones["{}"]'.format(bone_name)
    loc, rot = {}, {}
    for fc in _action_fcurves(action):
        if fc.data_path == base + ".location":
            loc[fc.array_index] = fc
        elif fc.data_path == base + ".rotation_quaternion":
            rot[fc.array_index] = fc
    if not loc and not rot:
        return []
    frames = sorted({round(kp.co.x)
                     for fc in list(loc.values()) + list(rot.values())
                     for kp in fc.keyframe_points})
    snaps = []
    for f in frames:
        snap = {"t": round(from_frame(f, "s", scene), 6)}
        if loc:
            snap["loc"] = [round(loc[i].evaluate(f), 6) if i in loc else 0.0
                           for i in range(3)]
        if rot:
            snap["rot"] = [round(rot[i].evaluate(f), 6) if i in rot
                           else (1.0 if i == 0 else 0.0) for i in range(4)]
        snaps.append(snap)
    return snaps


# --- capture stages ----------------------------------------------------------

def _bone_node(tree, arm, bone):
    existing = node_for_bone(arm, bone)
    if existing is not None and existing.id_data == tree:
        return existing
    for node in tree.nodes:  # fall back to a same-named bone part
        if is_bone_part(node) and (node.element_name or node.name) == bone.name:
            return node
    return tree.nodes.new(_PART_IDNAME)


def _capture_bones(tree, arm, rolls):
    bone_node = {}
    for bone in arm.data.bones:
        node = _bone_node(tree, arm, bone)
        node.element_name = bone.name
        node[BONE_KEY] = 1
        node[BONE_HEAD_KEY] = tuple(bone.head_local)
        node[BONE_TAIL_KEY] = tuple(bone.tail_local)
        node[BONE_ROLL_KEY] = float(rolls.get(bone.name, 0.0))
        bind_bone(node, arm, bone)
        bone_node[bone.name] = node
    return bone_node


def _capture_containment(tree, arm, bone_node):
    ours = set(bone_node.values())
    for link in list(tree.links):  # clear our members links, then rebuild
        if (link.to_socket.identifier == "members"
                and link.to_node in ours and link.from_node in ours):
            tree.links.remove(link)
    for bone in arm.data.bones:
        if bone.parent and bone.parent.name in bone_node:
            _relink_member(tree, bone_node[bone.name], bone_node[bone.parent.name])


def _relink_member(tree, child, parent):
    tree.links.new(child.outputs["Self"], _input_by_id(parent, "members"))


def _capture_constraints(tree, arm, bone_node):
    made = 0
    for pbone in arm.pose.bones:
        owner = bone_node.get(pbone.name)
        if owner is None:
            continue
        for con in pbone.constraints:
            target = bone_node.get(getattr(con, "subtarget", ""))
            if target is None:
                continue
            name = (con.name[len(_CONSTRAINT_PREFIX):]
                    if con.name.startswith(_CONSTRAINT_PREFIX) else con.name)
            conn = (_find_by_element(tree, _CONN_IDNAME, name)
                    or tree.nodes.new(_CONN_IDNAME))
            conn.element_name = name
            conn[CONSTRAINT_KEY] = con.type
            _relink(tree, conn, "connect", owner)
            _relink(tree, conn, "to", target)
            made += 1
    return made


def _capture_keyframes(tree, arm, bone_node, scene):
    ad = arm.animation_data
    action = ad.action if ad else None
    if action is None:
        return 0
    made = 0
    for name, node in bone_node.items():
        snaps = _bone_snapshots(action, name, scene)
        if snaps:
            node[SNAPSHOTS_KEY] = json.dumps(snaps)
            node[TIME_UNIT_KEY] = "s"
            made += 1
    return made


def _capture_states(tree, arm, bone_node, scene):
    ad = arm.animation_data
    if ad is None:
        return 0
    track = next((t for t in ad.nla_tracks if t.name == NLA_TRACK_NAME), None)
    if track is None:
        return 0
    states = []
    for strip in sorted(track.strips, key=lambda s: s.frame_start):
        act = strip.action
        if act is None:
            continue
        name = (act.name[len(ACTION_PREFIX):]
                if act.name.startswith(ACTION_PREFIX) else act.name)
        node = _find_by_element(tree, _STATE_IDNAME, name) or tree.nodes.new(_STATE_IDNAME)
        node.element_name = name
        poses = {bname: snaps for bname in bone_node
                 for snaps in (_bone_snapshots(act, bname, scene),) if snaps}
        node[POSES_KEY] = json.dumps(poses)
        node[TIME_UNIT_KEY] = "s"
        states.append(node)
    for src, dst in zip(states, states[1:]):
        succ = _find_succession(tree, src, dst) or tree.nodes.new(_SUCC_IDNAME)
        succ.element_name = "{}_to_{}".format(src.element_name, dst.element_name)
        succ[SUCC_FROM_KEY] = src.element_name
        succ[SUCC_TO_KEY] = dst.element_name
    return len(states)


def _find_succession(tree, src, dst):
    for node in tree.nodes:
        if (node.bl_idname == _SUCC_IDNAME
                and node.get(SUCC_FROM_KEY) == src.element_name
                and node.get(SUCC_TO_KEY) == dst.element_name):
            return node
    return None


def capture_armature(arm, tree, scene=None):
    """Read `arm` + its animation into `tree`. Returns the captured bone count."""
    scene = scene or bpy.context.scene
    rolls = _read_rolls(arm)
    bone_node = _capture_bones(tree, arm, rolls)
    _capture_containment(tree, arm, bone_node)
    _capture_constraints(tree, arm, bone_node)
    _capture_keyframes(tree, arm, bone_node, scene)
    _capture_states(tree, arm, bone_node, scene)
    return len(bone_node)


class NODE_OT_sysml_capture(bpy.types.Operator):
    """Capture an Armature + its animation into a SysML graph"""
    bl_idname = "node.sysml_capture"
    bl_label = "Capture Armature to SysML"
    bl_options = {'REGISTER', 'UNDO'}

    armature_name: bpy.props.StringProperty(
        name="Armature",
        description="Armature to capture (defaults to the active object)",
        options={'SKIP_SAVE'},
    )
    tree_name: bpy.props.StringProperty(
        name="Tree",
        description="Target SysML node tree (created if it does not exist)",
        options={'SKIP_SAVE'},
    )

    def execute(self, context):
        arm = bpy.data.objects.get(self.armature_name) if self.armature_name else context.active_object
        if arm is None or arm.type != 'ARMATURE':
            self.report({'ERROR'}, "No armature to capture")
            return {'CANCELLED'}
        tree = bpy.data.node_groups.get(self.tree_name) if self.tree_name else None
        if tree is None:
            tree = bpy.data.node_groups.new(self.tree_name or arm.name, "SysMLNodeTree")
        count = capture_armature(arm, tree, context.scene)
        self.report({'INFO'}, f"Captured {count} bone{'' if count == 1 else 's'}")
        return {'FINISHED'}


classes = (
    NODE_OT_sysml_capture,
)
