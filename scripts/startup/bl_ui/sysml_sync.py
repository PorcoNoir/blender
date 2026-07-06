# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Live sync between a SysML graph and its Blender armature/animation
(Animation Binding B / SCRUM-653).

Makes the graph and the rig two live views of one model. Each tree has a
**source of truth** which makes it *unidirectional*, so loops are impossible by
construction:

* ``source = "blender"`` -> a ``depsgraph_update_post`` handler pulls pose/bone
  and keyframe edits into the graph (bone-part nodes' rest transform + snapshots);
* ``source = "graph"``   -> an ``msgbus`` subscription pushes graph edits into the
  rig (re-rig + re-keyframe).

Propagation is **debounced**: handlers only mark the affected tree dirty, and a
short timer coalesces bursts into one flush. A reentrancy guard (``_SYNCING``)
blocks any handler from firing while a flush is running. Sync is opt-in per tree
(``sysml_sync_enabled``); individual bindings can be made inert with a per-node
``sysml_sync_linked`` flag.

The pull path deliberately reads only data available without an operator
(``head_local`` / ``tail_local`` and action fcurves) — running ``bpy.ops`` /
mode switches inside a depsgraph handler is unsafe. The push path (which re-rigs)
runs from a timer, where operators are allowed.
"""

import contextlib
import json

import bpy
from bpy.app.handlers import persistent

from bl_ui.sysml_armature import rig_tree, _find_rig_armature
from bl_ui.sysml_animate import keyframe_tree, SNAPSHOTS_KEY
from bl_ui.sysml_bone_binding import (
    BONE_HEAD_KEY, BONE_TAIL_KEY, bound_bones,
)
from bl_ui.sysml_capture import _bone_snapshots
from bl_ui.sysml_time import TIME_UNIT_KEY

SYNC_ENABLED_KEY = "sysml_sync_enabled"
SYNC_SOURCE_KEY = "sysml_sync_source"
LINK_KEY = "sysml_sync_linked"   # on a node; missing/1 = linked, 0 = inert

SOURCE_BLENDER = "blender"
SOURCE_GRAPH = "graph"
DEBOUNCE = 0.05

_TREE_IDNAME = "SysMLNodeTree"

# Module state: reentrancy guard + per-direction dirty sets (tree names).
_SYNCING = False
_dirty_pull = set()
_dirty_push = set()


# --- enable / source / link accessors ----------------------------------------

def is_enabled(tree):
    return bool(tree.get(SYNC_ENABLED_KEY))


def source_of_truth(tree):
    return tree.get(SYNC_SOURCE_KEY, SOURCE_BLENDER)


def set_sync(tree, enabled, source=None):
    tree[SYNC_ENABLED_KEY] = 1 if enabled else 0
    if source is not None:
        tree[SYNC_SOURCE_KEY] = source
    if enabled and source_of_truth(tree) == SOURCE_GRAPH:
        _subscribe(tree)
    else:
        _unsubscribe(tree)


def is_linked(node):
    return node.get(LINK_KEY, 1) != 0


def set_linked(node, linked):
    node[LINK_KEY] = 1 if linked else 0


def _enabled_trees(source):
    for tree in bpy.data.node_groups:
        if (tree.bl_idname == _TREE_IDNAME and is_enabled(tree)
                and source_of_truth(tree) == source):
            yield tree


@contextlib.contextmanager
def _guard():
    global _SYNCING
    _SYNCING = True
    try:
        yield
    finally:
        _SYNCING = False


# --- propagation --------------------------------------------------------------

def sync_pull(tree):
    """Blender -> graph: update bound (and linked) nodes from the armature.

    Returns the number of bindings updated. Operator-free (handler-safe).
    """
    arm = _find_rig_armature(tree)
    if arm is None:
        return 0
    scene = bpy.context.scene
    action = arm.animation_data.action if arm.animation_data else None
    updated = 0
    for _obj, bone, node in bound_bones(tree):
        if not is_linked(node):
            continue
        node[BONE_HEAD_KEY] = tuple(bone.head_local)
        node[BONE_TAIL_KEY] = tuple(bone.tail_local)
        if action is not None:
            snaps = _bone_snapshots(action, bone.name, scene)
            if snaps:
                node[SNAPSHOTS_KEY] = json.dumps(snaps)
                node[TIME_UNIT_KEY] = "s"
        updated += 1
    return updated


def sync_push(tree):
    """Graph -> Blender: re-rig + re-keyframe from the graph. Returns 1/0."""
    with _guard():  # rig_tree touches the armature; don't let it bounce back
        rig_tree(tree)
        keyframe_tree(tree, bpy.context.scene)
    return 1


# --- debounced flush ----------------------------------------------------------

def _schedule(fn):
    try:
        if not bpy.app.timers.is_registered(fn):
            bpy.app.timers.register(fn, first_interval=DEBOUNCE)
    except Exception:  # noqa: BLE001 - timers unavailable (e.g. headless) is fine
        pass


def _flush_pull():
    names = list(_dirty_pull)
    _dirty_pull.clear()
    with _guard():
        for name in names:
            tree = bpy.data.node_groups.get(name)
            if tree is not None and is_enabled(tree) and source_of_truth(tree) == SOURCE_BLENDER:
                sync_pull(tree)
    return None


def _flush_push():
    names = list(_dirty_push)
    _dirty_push.clear()
    for name in names:
        tree = bpy.data.node_groups.get(name)
        if tree is not None and is_enabled(tree) and source_of_truth(tree) == SOURCE_GRAPH:
            sync_push(tree)
    return None


def _note_updated_ids(updated_ids):
    """Mark blender-source trees whose armature was in the update set."""
    for tree in _enabled_trees(SOURCE_BLENDER):
        arm = _find_rig_armature(tree)
        if arm is not None and (arm in updated_ids or arm.data in updated_ids):
            _dirty_pull.add(tree.name)
    if _dirty_pull:
        _schedule(_flush_pull)


def _note_graph_dirty(tree_name):
    """Mark a graph-source tree for a push (called from msgbus)."""
    _dirty_push.add(tree_name)
    _schedule(_flush_push)


# --- handlers / msgbus --------------------------------------------------------

@persistent
def _on_depsgraph(_scene, depsgraph):
    if _SYNCING:
        return
    _note_updated_ids({u.id.original for u in depsgraph.updates})


_msgbus_owners = {}


def _subscribe(tree):
    owner = _msgbus_owners.get(tree.name)
    if owner is None:
        owner = object()
        _msgbus_owners[tree.name] = owner
    try:
        bpy.msgbus.clear_by_owner(owner)
        bpy.msgbus.subscribe_rna(
            key=tree.path_resolve("nodes", False),
            owner=owner,
            args=(tree.name,),
            notify=_note_graph_dirty,
        )
    except Exception:  # noqa: BLE001 - msgbus best-effort; explicit push still works
        pass


def _unsubscribe(tree):
    owner = _msgbus_owners.pop(tree.name, None)
    if owner is not None:
        try:
            bpy.msgbus.clear_by_owner(owner)
        except Exception:  # noqa: BLE001
            pass


def install():
    if _on_depsgraph not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(_on_depsgraph)


def uninstall():
    if _on_depsgraph in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(_on_depsgraph)


# --- operators ----------------------------------------------------------------

class NODE_OT_sysml_sync(bpy.types.Operator):
    """Enable or disable live sync for a SysML tree"""
    bl_idname = "node.sysml_sync"
    bl_label = "SysML Live Sync"
    bl_options = {'REGISTER', 'UNDO'}

    enable: bpy.props.BoolProperty(name="Enable", default=True, options={'SKIP_SAVE'})
    source: bpy.props.EnumProperty(
        name="Source of Truth",
        items=[
            (SOURCE_BLENDER, "Blender", "Pose/keyframe edits drive the graph"),
            (SOURCE_GRAPH, "Graph", "Graph edits drive the rig"),
        ],
        default=SOURCE_BLENDER,
        options={'SKIP_SAVE'},
    )
    tree_name: bpy.props.StringProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        tree = None
        if self.tree_name:
            tree = bpy.data.node_groups.get(self.tree_name)
        elif getattr(context.space_data, "edit_tree", None):
            tree = context.space_data.edit_tree
        if tree is None or tree.bl_idname != _TREE_IDNAME:
            self.report({'ERROR'}, "No SysML node tree to sync")
            return {'CANCELLED'}
        set_sync(tree, self.enable, self.source)
        state = "on ({})".format(self.source) if self.enable else "off"
        self.report({'INFO'}, f"Live sync {state}")
        return {'FINISHED'}


classes = (
    NODE_OT_sysml_sync,
)

# Install the depsgraph handler as soon as the module loads (persistent, so it
# survives file loads; deduped so reloads don't stack it).
install()
