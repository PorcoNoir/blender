# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""SysML Text datablock -> nodes (BSML4 / SCRUM-665).

Author SysML as text in Blender's Text editor and parse it into a node graph on
demand. The Text datablock's contents are written to a temp `.sysml` (named after
the datablock, so the resulting tree is named sensibly) and handed to the native
import path.

The model is pre-validated through the sml2c diagnostics bridge (SCRUM-662): if
it has errors, the operator reports the first diagnostic and creates no tree,
rather than importing a partial graph. With no sml2c available the pre-check is
skipped and native import runs directly.
"""

import os
import tempfile

import bpy

from bl_ui import sysml_diagnostics

_TREE_IDNAME = "SysMLNodeTree"


class SysMLParseError(ValueError):
    """A SysML source string did not resolve cleanly."""


def _basename(text):
    name = text.name
    if name.lower().endswith(".sysml"):
        name = name[:-len(".sysml")]
    return name or "SysMLText"


def text_to_nodes(text):
    """Parse a SysML `Text` datablock into a new node tree.

    Returns the created tree. Raises SysMLParseError (with the first error
    message) if the model has diagnostics errors — no tree is created.
    """
    content = text.as_string()

    errors = [f for f in sysml_diagnostics.diagnose_text(content)
              if f["severity"] == "error"]
    if errors:
        raise SysMLParseError(errors[0]["message"])

    before = set(bpy.data.node_groups.keys())
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, _basename(text) + ".sysml")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        result = bpy.ops.node.sysml_import(filepath=path)
    if 'FINISHED' not in result:
        raise SysMLParseError("import failed")

    new = [ng for key, ng in bpy.data.node_groups.items()
           if key not in before and ng.bl_idname == _TREE_IDNAME]
    if not new:
        raise SysMLParseError("no tree produced")
    return new[0]


def nodes_to_text(tree, text_name=None):
    """Serialize `tree` to canonical SysML in a Text datablock.

    The datablock is named after the tree (``<tree>.sysml``) unless `text_name`
    is given, and is reused/updated in place on re-run rather than duplicated.
    Returns the Text datablock.
    """
    name = text_name or (tree.name + ".sysml")
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "model.sysml")
        result = bpy.ops.node.sysml_export(filepath=path, tree_name=tree.name)
        if 'FINISHED' not in result or not os.path.exists(path):
            raise SysMLParseError("export failed")
        with open(path, encoding="utf-8") as fh:
            content = fh.read()

    text = bpy.data.texts.get(name)
    if text is None:
        text = bpy.data.texts.new(name)
    text.clear()
    text.write(content)
    return text


class NODE_OT_sysml_text_to_nodes(bpy.types.Operator):
    """Parse a SysML Text datablock into a node graph"""
    bl_idname = "node.sysml_text_to_nodes"
    bl_label = "SysML Text to Nodes"
    bl_options = {'REGISTER', 'UNDO'}

    text_name: bpy.props.StringProperty(
        name="Text",
        description="SysML Text datablock to parse (defaults to the active text)",
        options={'SKIP_SAVE'},
    )

    def execute(self, context):
        text = None
        if self.text_name:
            text = bpy.data.texts.get(self.text_name)
        elif getattr(context.space_data, "text", None):
            text = context.space_data.text
        if text is None:
            self.report({'ERROR'}, "No SysML text to parse")
            return {'CANCELLED'}
        try:
            tree = text_to_nodes(text)
        except SysMLParseError as exc:
            self.report({'ERROR'}, f"SysML parse error: {exc}")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Parsed '{text.name}' -> {len(tree.nodes)} nodes")
        return {'FINISHED'}


class NODE_OT_sysml_nodes_to_text(bpy.types.Operator):
    """Serialize the SysML graph into a Text datablock"""
    bl_idname = "node.sysml_nodes_to_text"
    bl_label = "SysML Nodes to Text"
    bl_options = {'REGISTER', 'UNDO'}

    tree_name: bpy.props.StringProperty(options={'SKIP_SAVE'})
    text_name: bpy.props.StringProperty(
        name="Text",
        description="Target Text datablock (defaults to <tree>.sysml)",
        options={'SKIP_SAVE'},
    )

    def execute(self, context):
        tree = None
        if self.tree_name:
            tree = bpy.data.node_groups.get(self.tree_name)
        elif getattr(context.space_data, "edit_tree", None):
            tree = context.space_data.edit_tree
        if tree is None or tree.bl_idname != _TREE_IDNAME:
            self.report({'ERROR'}, "No SysML node tree to serialize")
            return {'CANCELLED'}
        try:
            text = nodes_to_text(tree, self.text_name or None)
        except SysMLParseError as exc:
            self.report({'ERROR'}, f"SysML export error: {exc}")
            return {'CANCELLED'}
        self.report({'INFO'}, f"Wrote '{text.name}'")
        return {'FINISHED'}


classes = (
    NODE_OT_sysml_text_to_nodes,
    NODE_OT_sysml_nodes_to_text,
)
