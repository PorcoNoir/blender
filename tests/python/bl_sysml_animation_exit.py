# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Animation Binding A exit gate — graph <-> armature/animation round-trip
(SCRUM-652).

The phase-A acceptance gate: a reference rig graph (a nested bone chain with a
joint constraint, plus snapshot keyframes across a couple of states) is
materialised (rig + behavior / keyframes) and then captured back, and the
captured graph is asserted faithful to the source — bones, hierarchy,
constraints, states, and keyframe/frame times. Headless bpy; wired into the
release workflow. Green here means Animation Binding A is complete and B is
unblocked.

Two round-trips are checked separately because the live-keyframe path
(keyframe_tree, which clears animation data) and the behavior/NLA path
(build_behavior, which detaches the live action) do not co-exist on one armature:

* the **state** round-trip carries its keyframes inside per-state clips (NLA);
* the **live-keyframe** round-trip carries them in the object's action.
"""

import json
import sys
import unittest

import bpy

from bl_ui.sysml_armature import rig_tree, CONSTRAINT_KEY, _find_rig_armature
from bl_ui.sysml_animate import keyframe_tree, SNAPSHOTS_KEY
from bl_ui.sysml_behavior import (
    build_behavior, POSES_KEY, SUCC_FROM_KEY, SUCC_TO_KEY,
)
from bl_ui.sysml_capture import capture_armature
from bl_ui.sysml_bone_binding import (
    BONE_KEY, BONE_HEAD_KEY, BONE_TAIL_KEY,
)
from bl_ui.sysml_time import TIME_UNIT_KEY

TREE_IDNAME = "SysMLNodeTree"

BONES = {
    "UpperArm": ((0, 0, 0), (0, 0, 2)),
    "Forearm": ((0, 0, 2), (0, 0, 4)),
    "IKTarget": ((0, 1, 4), (0, 1, 5)),
}


def _bone(tree, name):
    head, tail = BONES[name]
    node = tree.nodes.new("SysMLNodePartUsage")
    node.element_name = name
    node[BONE_KEY] = 1
    node[BONE_HEAD_KEY] = tuple(float(v) for v in head)
    node[BONE_TAIL_KEY] = tuple(float(v) for v in tail)
    return node


def _build_base(tree):
    """Bones + Forearm-in-UpperArm containment + an IK Forearm->IKTarget joint."""
    nodes = {n: _bone(tree, n) for n in BONES}
    tree.links.new(nodes["Forearm"].outputs["Self"], nodes["UpperArm"].inputs["Members"])
    conn = tree.nodes.new("SysMLNodeConnectionUsage")
    conn.element_name = "Wrist"
    conn[CONSTRAINT_KEY] = "IK"
    tree.links.new(nodes["Forearm"].outputs["Self"], conn.inputs["Connect"])
    tree.links.new(nodes["IKTarget"].outputs["Self"], conn.inputs["To"])
    return nodes


class AnimationExitGate(unittest.TestCase):
    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene = bpy.context.scene
        self.scene.frame_start = 1

    # -- shared assertions ---------------------------------------------------

    def _node(self, tree, name):
        return next((n for n in tree.nodes if n.element_name == name), None)

    def _assert_skeleton(self, cap):
        parts = {n.element_name for n in cap.nodes
                 if n.bl_idname == "SysMLNodePartUsage" and n.get(BONE_KEY)}
        self.assertEqual(parts, set(BONES))
        # Rest transforms survive.
        upper = self._node(cap, "UpperArm")
        self.assertEqual(tuple(round(v, 3) for v in upper[BONE_TAIL_KEY]), (0.0, 0.0, 2.0))
        # Containment: Forearm inside UpperArm.
        members = [l for l in cap.links
                   if l.to_node == upper and l.to_socket.identifier == "members"]
        self.assertEqual([l.from_node for l in members], [self._node(cap, "Forearm")])
        # The IK joint round-trips wired to the right bones.
        conn = next(n for n in cap.nodes if n.bl_idname == "SysMLNodeConnectionUsage")
        self.assertEqual(conn[CONSTRAINT_KEY], "IK")
        connect = next(l for l in cap.links
                       if l.to_node == conn and l.to_socket.identifier == "connect")
        to = next(l for l in cap.links
                  if l.to_node == conn and l.to_socket.identifier == "to")
        self.assertEqual(connect.from_node, self._node(cap, "Forearm"))
        self.assertEqual(to.from_node, self._node(cap, "IKTarget"))

    # -- round-trips ---------------------------------------------------------

    def test_state_roundtrip(self):
        src = bpy.data.node_groups.new("Src", TREE_IDNAME)
        _build_base(src)
        for name, z1 in (("Idle", 0), ("Wave", 1)):
            st = src.nodes.new("SysMLNodeStateUsage")
            st.element_name = name
            st[TIME_UNIT_KEY] = "s"
            st[POSES_KEY] = json.dumps(
                {"UpperArm": [{"t": 0.0, "loc": [0, 0, 0]}, {"t": 0.5, "loc": [0, 0, z1]}]})
        succ = src.nodes.new("SysMLNodeSuccessionUsage")
        succ[SUCC_FROM_KEY] = "Idle"
        succ[SUCC_TO_KEY] = "Wave"

        rig_tree(src)
        build_behavior(src, self.scene)

        cap = bpy.data.node_groups.new("Cap", TREE_IDNAME)
        capture_armature(_find_rig_armature(src), cap, self.scene)

        self._assert_skeleton(cap)
        states = {n.element_name for n in cap.nodes if n.bl_idname == "SysMLNodeStateUsage"}
        self.assertEqual(states, {"Idle", "Wave"})
        succ_cap = next(n for n in cap.nodes if n.bl_idname == "SysMLNodeSuccessionUsage")
        self.assertEqual((succ_cap[SUCC_FROM_KEY], succ_cap[SUCC_TO_KEY]), ("Idle", "Wave"))
        # The Wave clip's keyframe/frame time round-trips (t=0.5 -> z=1).
        wave = json.loads(self._node(cap, "Wave")[POSES_KEY])["UpperArm"]
        late = next(s for s in wave if round(s["t"], 3) == 0.5)
        self.assertAlmostEqual(late["loc"][2], 1.0, places=3)

    def test_keyframe_roundtrip(self):
        src = bpy.data.node_groups.new("Src", TREE_IDNAME)
        nodes = _build_base(src)
        nodes["UpperArm"][TIME_UNIT_KEY] = "s"
        nodes["UpperArm"][SNAPSHOTS_KEY] = json.dumps(
            [{"t": 0.0, "loc": [0, 0, 0]}, {"t": 1.0, "loc": [0, 0, 1]}])

        rig_tree(src)
        keyframe_tree(src, self.scene)

        cap = bpy.data.node_groups.new("Cap", TREE_IDNAME)
        capture_armature(_find_rig_armature(src), cap, self.scene)

        self._assert_skeleton(cap)
        # Live keyframes round-trip as snapshots at the same clock times.
        snaps = json.loads(self._node(cap, "UpperArm")[SNAPSHOTS_KEY])
        self.assertEqual([round(s["t"], 3) for s in snaps], [0.0, 1.0])
        self.assertAlmostEqual(snaps[1]["loc"][2], 1.0, places=3)


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
