# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

# Add / Swap menus for the SysML v2 node editor (BSML0 / SCRUM-431).
#
# The category structure mirrors the SysML element families. The first three
# element nodes (PartDef / PartUsage / ConnectionUsage) land in SCRUM-433; the
# full taxonomy is generated in BSML1. Menu draw is lazy, so referencing those
# node idnames here is forward-compatible — entries become live once the node
# types register.

from bpy.types import Menu
from bpy.app.translations import (
    contexts as i18n_contexts,
)
from bl_ui import node_add_menu


class NODE_MT_sysml_node_definition_base(Menu):
    bl_label = "Definition"

    def draw(self, _context):
        layout = self.layout
        self.node_operator(layout, "SysMLNodePartDef")


class NODE_MT_sysml_node_usage_base(Menu):
    bl_label = "Usage"

    def draw(self, _context):
        layout = self.layout
        self.node_operator(layout, "SysMLNodePartUsage")


class NODE_MT_sysml_node_connection_base(Menu):
    bl_label = "Connection"

    def draw(self, _context):
        layout = self.layout
        self.node_operator(layout, "SysMLNodeConnectionUsage")


class NODE_MT_sysml_node_all_base(node_add_menu.NodeMenu):
    bl_label = ""
    menu_path = "Root"
    bl_translation_context = i18n_contexts.operator_default

    # NOTE: Menus are looked up via their label, so that both the Add & Swap
    # menus can share the same layout while each using their corresponding menus.
    def draw(self, context):
        del context
        layout = self.layout
        self.draw_menu(layout, "Definition")
        self.draw_menu(layout, "Usage")
        self.draw_menu(layout, "Connection")
        layout.separator()
        self.draw_menu(layout, "Group")
        self.draw_menu(layout, "Layout")

        self.draw_root_assets(layout)


add_menus = {
    # menu `bl_idname`: base-class.
    "NODE_MT_category_sysml_definition": NODE_MT_sysml_node_definition_base,
    "NODE_MT_category_sysml_usage": NODE_MT_sysml_node_usage_base,
    "NODE_MT_category_sysml_connection": NODE_MT_sysml_node_connection_base,
    "NODE_MT_sysml_node_add_all": NODE_MT_sysml_node_all_base,
}
add_menus = node_add_menu.generate_menus(
    add_menus,
    template=node_add_menu.AddNodeMenu,
    base_dict=node_add_menu.add_base_pathing_dict
)


swap_menus = {
    # menu `bl_idname`: base-class.
    "NODE_MT_sysml_node_definition_swap": NODE_MT_sysml_node_definition_base,
    "NODE_MT_sysml_node_usage_swap": NODE_MT_sysml_node_usage_base,
    "NODE_MT_sysml_node_connection_swap": NODE_MT_sysml_node_connection_base,
    "NODE_MT_sysml_node_swap_all": NODE_MT_sysml_node_all_base,
}
swap_menus = node_add_menu.generate_menus(
    swap_menus,
    template=node_add_menu.SwapNodeMenu,
    base_dict=node_add_menu.swap_base_pathing_dict
)


classes = (
    *add_menus,
    *swap_menus,
)


if __name__ == "__main__":  # only for live edit.
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
