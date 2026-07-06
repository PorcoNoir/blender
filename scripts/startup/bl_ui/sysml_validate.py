# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Diagnostics on nodes — badges + panel + validate operator (BSML4 / SCRUM-664).

Aggregates the two BSML4 finding sources into one editor experience:

* local structural findings (SCRUM-663) — reliably keyed to a node;
* sml2c findings (SCRUM-662) — line-based on the exported text, best-effort
  matched to a node by the element name quoted in the message.

Validating a tree stamps each offending node with its worst finding (a severity
marker + message custom property, reflected as the node's header colour) and
stores the full findings list on the tree for the diagnostics panel. It is
idempotent: prior marks are cleared before re-marking, so re-validating never
stacks, and fixing a problem clears its badge.
"""

import json
import os
import tempfile

import bpy

from bl_ui import sysml_structure, sysml_diagnostics

DIAG_SEVERITY_KEY = "sysml_diag"        # on a node: "error" / "warning" / "note"
DIAG_MSG_KEY = "sysml_diag_msg"         # on a node: the message
DIAG_LIST_KEY = "sysml_diagnostics"     # on the tree: JSON list of all findings

_SEVERITY_RANK = {"error": 3, "warning": 2, "note": 1}
_COLORS = {
    "error": (0.70, 0.12, 0.12),
    "warning": (0.72, 0.52, 0.12),
    "note": (0.20, 0.35, 0.60),
}
_TREE_IDNAME = "SysMLNodeTree"


# --- aggregation --------------------------------------------------------------

def _match_node(tree, message):
    """A node whose element name is quoted in `message`, or None (best-effort)."""
    for node in tree.nodes:
        name = node.element_name
        if name and "'{}'".format(name) in message:
            return node
    return None


def _sml2c_findings(tree):
    """Line-based sml2c findings for the exported tree (empty if unavailable)."""
    if not sysml_diagnostics.available():
        return []
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "model.sysml")
        try:
            res = bpy.ops.node.sysml_export(filepath=path, tree_name=tree.name)
        except RuntimeError:
            return []
        if 'FINISHED' not in res or not os.path.exists(path):
            return []
        for f in sysml_diagnostics.diagnose_file(path):
            node = _match_node(tree, f["message"])
            out.append({
                "node": node.name if node else None,
                "element": node.element_name if node else "",
                "severity": f["severity"],
                "code": f["code"],
                "message": f["message"],
                "line": f["line"],
                "source": "sml2c",
            })
    return out


def aggregate_findings(tree):
    """All findings for `tree`: local structural + sml2c (normalised shape)."""
    findings = []
    for f in sysml_structure.check_tree(tree):
        findings.append({**f, "line": None, "source": "local"})
    findings.extend(_sml2c_findings(tree))
    return findings


# --- marking ------------------------------------------------------------------

def _clear_marks(tree):
    for node in tree.nodes:
        if DIAG_SEVERITY_KEY in node:
            del node[DIAG_SEVERITY_KEY]
            if DIAG_MSG_KEY in node:
                del node[DIAG_MSG_KEY]
            node.use_custom_color = False


def validate_tree(tree):
    """(Re)compute findings, stamp node badges, store the list. Returns findings."""
    _clear_marks(tree)
    findings = aggregate_findings(tree)

    # Worst finding per node drives its badge.
    worst = {}
    for f in findings:
        name = f.get("node")
        if not name:
            continue
        cur = worst.get(name)
        if cur is None or _SEVERITY_RANK.get(f["severity"], 0) > _SEVERITY_RANK.get(cur["severity"], 0):
            worst[name] = f

    for name, f in worst.items():
        node = tree.nodes.get(name)
        if node is None:
            continue
        node[DIAG_SEVERITY_KEY] = f["severity"]
        node[DIAG_MSG_KEY] = f["message"]
        node.use_custom_color = True
        node.color = _COLORS.get(f["severity"], _COLORS["warning"])

    tree[DIAG_LIST_KEY] = json.dumps(findings)
    return findings


# --- operators ----------------------------------------------------------------

class NODE_OT_sysml_validate(bpy.types.Operator):
    """Validate the SysML graph and mark diagnostics on the nodes"""
    bl_idname = "node.sysml_validate"
    bl_label = "Validate SysML"
    bl_options = {'REGISTER', 'UNDO'}

    tree_name: bpy.props.StringProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        tree = None
        if self.tree_name:
            tree = bpy.data.node_groups.get(self.tree_name)
        elif getattr(context.space_data, "edit_tree", None):
            tree = context.space_data.edit_tree
        if tree is None or tree.bl_idname != _TREE_IDNAME:
            self.report({'ERROR'}, "No SysML node tree to validate")
            return {'CANCELLED'}
        findings = validate_tree(tree)
        errors = sum(1 for f in findings if f["severity"] == "error")
        self.report({'INFO'}, f"{len(findings)} finding(s), {errors} error(s)")
        return {'FINISHED'}


class NODE_OT_sysml_diag_select(bpy.types.Operator):
    """Select the node a diagnostic refers to"""
    bl_idname = "node.sysml_diag_select"
    bl_label = "Go to Node"
    bl_options = {'REGISTER'}

    tree_name: bpy.props.StringProperty(options={'SKIP_SAVE'})
    node_name: bpy.props.StringProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        tree = bpy.data.node_groups.get(self.tree_name)
        node = tree.nodes.get(self.node_name) if tree else None
        if node is None:
            self.report({'ERROR'}, "Node not found")
            return {'CANCELLED'}
        for n in tree.nodes:
            n.select = False
        node.select = True
        tree.nodes.active = node
        return {'FINISHED'}


# --- panel --------------------------------------------------------------------

class NODE_PT_sysml_diagnostics(bpy.types.Panel):
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "SysML"
    bl_label = "Diagnostics"

    @classmethod
    def poll(cls, context):
        tree = getattr(context.space_data, "edit_tree", None)
        return tree is not None and tree.bl_idname == _TREE_IDNAME

    def draw(self, context):
        layout = self.layout
        tree = context.space_data.edit_tree
        layout.operator(NODE_OT_sysml_validate.bl_idname, icon='CHECKMARK').tree_name = tree.name

        raw = tree.get(DIAG_LIST_KEY)
        if not raw:
            layout.label(text="Not validated")
            return
        try:
            findings = json.loads(raw)
        except (ValueError, TypeError):
            findings = []
        if not findings:
            layout.label(text="No issues", icon='CHECKMARK')
            return

        for f in findings:
            row = layout.row(align=True)
            row.label(text="", icon='ERROR' if f["severity"] == "error" else 'INFO')
            code = "[{}] ".format(f["code"]) if f.get("code") else ""
            row.label(text=code + f["message"])
            if f.get("node"):
                op = row.operator(NODE_OT_sysml_diag_select.bl_idname, text="", icon='VIEWZOOM')
                op.tree_name = tree.name
                op.node_name = f["node"]


classes = (
    NODE_OT_sysml_validate,
    NODE_OT_sysml_diag_select,
    NODE_PT_sysml_diagnostics,
)
