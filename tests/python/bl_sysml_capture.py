# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Capture an Armature + animation into a SysML graph (Animation Binding A /
SCRUM-651).

Builds a hand rig (bones + parenting + an IK constraint + a keyframed action) the
way a user would, captures it into an empty tree, and checks the reverse mapping:
bone-part nodes with rest transforms, containment links, a connection carrying the
constraint, and Occurrence snapshots from the keyframes. Re-running updates in
place. Pure bpy.
"""

import json
import sys
import unittest

import bpy

from bl_ui import sysml_capture
from bl_ui.sysml_armature import CONSTRAINT_KEY
from bl_ui.sysml_animate import SNAPSHOTS_KEY
from bl_ui.sysml_bone_binding import (
    BONE_KEY, BONE_HEAD_KEY, BONE_TAIL_KEY, node_for_bone,
)

TREE_IDNAME = "SysMLNodeTree"


def _build_hand_rig(scene):
    arm_data = bpy.data.armatures.new("Rig")
    arm = bpy.data.objects.new("Rig", arm_data)
    scene.collection.objects.link(arm)
    bpy.context.view_layer.objects.active = arm

    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm_data.edit_bones
    u = eb.new("UpperArm"); u.head = (0, 0, 0); u.tail = (0, 0, 2)
    f = eb.new("Forearm"); f.head = (0, 0, 2); f.tail = (0, 0, 4); f.parent = u
    t = eb.new("IKTarget"); t.head = (0, 1, 4); t.tail = (0, 1, 5)
    bpy.ops.object.mode_set(mode='OBJECT')

    con = arm.pose.bones["Forearm"].constraints.new('IK')
    con.name = "SysML Wrist"
    con.target = arm
    con.subtarget = "IKTarget"

    arm.animation_data_create()
    arm.animation_data.action = bpy.data.actions.new("RigAction")
    ub = arm.pose.bones["UpperArm"]
    ub.rotation_mode = 'QUATERNION'
    ub.location = (0, 0, 0); ub.keyframe_insert("location", frame=1)
    ub.location = (0, 0, 1); ub.keyframe_insert("location", frame=25)
    return arm


class SysMLCaptureTest(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene = bpy.context.scene
        self.scene.frame_start = 1
        self.arm = _build_hand_rig(self.scene)
        self.tree = bpy.data.node_groups.new("Captured", TREE_IDNAME)

    def _node(self, name):
        for n in self.tree.nodes:
            if n.element_name == name:
                return n
        return None

    def test_bones_become_parts_with_rest_transforms(self):
        count = sysml_capture.capture_armature(self.arm, self.tree, self.scene)
        self.assertEqual(count, 3)
        upper = self._node("UpperArm")
        self.assertIsNotNone(upper)
        self.assertTrue(upper[BONE_KEY])
        self.assertEqual(tuple(round(v, 3) for v in upper[BONE_TAIL_KEY]), (0.0, 0.0, 2.0))
        fore = self._node("Forearm")
        self.assertEqual(tuple(round(v, 3) for v in fore[BONE_HEAD_KEY]), (0.0, 0.0, 2.0))
        # Binding established.
        self.assertEqual(node_for_bone(self.arm, self.arm.data.bones["UpperArm"]), upper)

    def test_parenting_becomes_containment(self):
        sysml_capture.capture_armature(self.arm, self.tree, self.scene)
        upper, fore = self._node("UpperArm"), self._node("Forearm")
        members = [l for l in self.tree.links
                   if l.to_node == upper and l.to_socket.identifier == "members"]
        self.assertEqual(len(members), 1)
        self.assertEqual(members[0].from_node, fore)

    def test_constraint_becomes_connection(self):
        sysml_capture.capture_armature(self.arm, self.tree, self.scene)
        conn = self._node("Wrist")
        self.assertIsNotNone(conn)
        self.assertEqual(conn.bl_idname, "SysMLNodeConnectionUsage")
        self.assertEqual(conn[CONSTRAINT_KEY], "IK")
        connect = [l for l in self.tree.links
                   if l.to_node == conn and l.to_socket.identifier == "connect"]
        to = [l for l in self.tree.links
              if l.to_node == conn and l.to_socket.identifier == "to"]
        self.assertEqual(connect[0].from_node, self._node("Forearm"))
        self.assertEqual(to[0].from_node, self._node("IKTarget"))

    def test_keyframes_become_snapshots(self):
        sysml_capture.capture_armature(self.arm, self.tree, self.scene)
        snaps = json.loads(self._node("UpperArm")[SNAPSHOTS_KEY])
        self.assertEqual([round(s["t"], 3) for s in snaps], [0.0, 1.0])  # frames 1,25 @ 24 fps
        self.assertAlmostEqual(snaps[1]["loc"][2], 1.0, places=3)

    def test_recapture_updates_not_duplicates(self):
        sysml_capture.capture_armature(self.arm, self.tree, self.scene)
        sysml_capture.capture_armature(self.arm, self.tree, self.scene)
        parts = [n for n in self.tree.nodes if n.bl_idname == "SysMLNodePartUsage"]
        conns = [n for n in self.tree.nodes if n.bl_idname == "SysMLNodeConnectionUsage"]
        self.assertEqual(len(parts), 3)
        self.assertEqual(len(conns), 1)
        upper = self._node("UpperArm")
        members = [l for l in self.tree.links
                   if l.to_node == upper and l.to_socket.identifier == "members"]
        self.assertEqual(len(members), 1)

    def test_operator_creates_tree_and_captures(self):
        self.assertEqual(
            bpy.ops.node.sysml_capture(armature_name="Rig", tree_name="OpTree"),
            {'FINISHED'})
        tree = bpy.data.node_groups.get("OpTree")
        self.assertIsNotNone(tree)
        self.assertEqual(len([n for n in tree.nodes if n.bl_idname == "SysMLNodePartUsage"]), 3)


class SysMLCaptureStatesTest(unittest.TestCase):
    """NLA strips (built by behavior) capture back to states + successions."""

    def setUp(self):
        from bl_ui import sysml_behavior
        from bl_ui.sysml_bone_binding import BONE_HEAD_KEY, BONE_TAIL_KEY
        from bl_ui.sysml_time import TIME_UNIT_KEY
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene = bpy.context.scene
        self.scene.frame_start = 1
        self.behavior = sysml_behavior

        src = bpy.data.node_groups.new("Src", TREE_IDNAME)
        root = src.nodes.new("SysMLNodePartUsage")
        root.element_name = "Root"
        root[BONE_KEY] = 1
        root[BONE_HEAD_KEY] = (0.0, 0.0, 0.0)
        root[BONE_TAIL_KEY] = (0.0, 0.0, 1.0)
        for name, snaps in (("Idle", [{"t": 0.0, "loc": [0, 0, 0]}, {"t": 0.5, "loc": [0, 0, 0]}]),
                            ("Wave", [{"t": 0.0, "loc": [0, 0, 0]}, {"t": 0.5, "loc": [0, 0, 1]}])):
            st = src.nodes.new("SysMLNodeStateUsage")
            st.element_name = name
            st[TIME_UNIT_KEY] = "s"
            st[sysml_behavior.POSES_KEY] = json.dumps({"Root": snaps})
        succ = src.nodes.new("SysMLNodeSuccessionUsage")
        succ[sysml_behavior.SUCC_FROM_KEY] = "Idle"
        succ[sysml_behavior.SUCC_TO_KEY] = "Wave"
        sysml_behavior.build_behavior(src, self.scene)  # -> armature + NLA
        self.arm = sysml_behavior.sysml_armature._find_rig_armature(src)

    def test_nla_strips_become_states_and_successions(self):
        tree = bpy.data.node_groups.new("Captured", TREE_IDNAME)
        sysml_capture.capture_armature(self.arm, tree, self.scene)
        states = {n.element_name for n in tree.nodes if n.bl_idname == "SysMLNodeStateUsage"}
        self.assertEqual(states, {"Idle", "Wave"})
        succ = [n for n in tree.nodes if n.bl_idname == "SysMLNodeSuccessionUsage"]
        self.assertEqual(len(succ), 1)
        self.assertEqual(succ[0][self.behavior.SUCC_FROM_KEY], "Idle")
        self.assertEqual(succ[0][self.behavior.SUCC_TO_KEY], "Wave")


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
