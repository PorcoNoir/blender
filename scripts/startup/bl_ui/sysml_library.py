# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""In-editor SysML standard-library browser (BSML5 / SCRUM-676).

Surfaces the standard-library catalog (SCRUM-675) in the node editor so users
author against standard types: pick a `Package::Type` and insert an attribute
usage typed by it, in one step.

A library type (e.g. `ISQ::LengthValue`) is *external* to the graph — it is a
built-in or bundled standard-library element, not a user element in the tree — so
it is recorded as a qualified-name custom property (`sysml_lib_type`) on the
inserted usage rather than wired to a stub node (which would misrepresent the
model and clutter the graph). The `of` socket stays free for typing against
in-model definitions. `library_snippet()` renders the resolvable SysML the usage
represents, for validation.
"""

import bpy

from bl_ui.sysml_stdlib_index_generated import STDLIB_INDEX

LIB_TYPE_KEY = "sysml_lib_type"   # on a usage node: qualified library type name
_TREE_IDNAME = "SysMLNodeTree"


def _default_name(type_name):
    return (type_name[0].lower() + type_name[1:]) if type_name else "value"


def insert_library_element(tree, package, type_name, element_name=None):
    """Add an attribute usage typed by `package::type_name`. Returns the node."""
    node = tree.nodes.new("SysMLNodeAttributeUsage")
    node.element_name = element_name or _default_name(type_name)
    node[LIB_TYPE_KEY] = "{}::{}".format(package, type_name)
    return node


def library_type(node):
    """The qualified library type recorded on `node`, or ''."""
    return node.get(LIB_TYPE_KEY, "")


def library_snippet(node):
    """Resolvable SysML for the library-typed usage on `node`."""
    return "package M {{\n\tattribute {} : {};\n}}\n".format(
        node.element_name or "value", library_type(node))


# Cached so the dynamic EnumProperty items aren't garbage-collected mid-use.
_enum_cache = []


def _library_enum_items(_self, _context):
    _enum_cache.clear()
    for entry in STDLIB_INDEX:
        for type_name in entry["types"]:
            qualified = "{}::{}".format(entry["package"], type_name)
            _enum_cache.append((qualified, qualified, entry["source"]))
    return _enum_cache


class NODE_OT_sysml_insert_library_type(bpy.types.Operator):
    """Insert an attribute usage typed by a standard-library type"""
    bl_idname = "node.sysml_insert_library_type"
    bl_label = "Insert Library Type"
    bl_property = "lib_entry"
    bl_options = {'REGISTER', 'UNDO'}

    tree_name: bpy.props.StringProperty(options={'SKIP_SAVE'})
    lib_entry: bpy.props.EnumProperty(items=_library_enum_items, options={'SKIP_SAVE'})
    element_name: bpy.props.StringProperty(options={'SKIP_SAVE'})

    def execute(self, context):
        tree = None
        if self.tree_name:
            tree = bpy.data.node_groups.get(self.tree_name)
        elif getattr(context.space_data, "edit_tree", None):
            tree = context.space_data.edit_tree
        if tree is None or tree.bl_idname != _TREE_IDNAME:
            self.report({'ERROR'}, "No SysML node tree")
            return {'CANCELLED'}
        package, _, type_name = self.lib_entry.partition("::")
        node = insert_library_element(tree, package, type_name, self.element_name or None)
        self.report({'INFO'}, f"Inserted '{node.element_name} : {self.lib_entry}'")
        return {'FINISHED'}

    def invoke(self, context, _event):
        context.window_manager.invoke_search_popup(self)
        return {'RUNNING_MODAL'}


class NODE_PT_sysml_library(bpy.types.Panel):
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "SysML"
    bl_label = "Library"

    @classmethod
    def poll(cls, context):
        tree = getattr(context.space_data, "edit_tree", None)
        return tree is not None and tree.bl_idname == _TREE_IDNAME

    def draw(self, context):
        layout = self.layout
        tree = context.space_data.edit_tree
        layout.operator(NODE_OT_sysml_insert_library_type.bl_idname, icon='ADD').tree_name = tree.name
        col = layout.column(align=True)
        for entry in STDLIB_INDEX:
            col.label(text="{} · {} ({} types)".format(
                entry["package"], entry["source"], len(entry["types"])))


classes = (
    NODE_OT_sysml_insert_library_type,
    NODE_PT_sysml_library,
)
