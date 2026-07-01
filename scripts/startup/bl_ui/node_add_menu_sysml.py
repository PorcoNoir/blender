# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

# Categorized Add / Swap menus for the SysML v2 node editor (BSML1 / SCRUM-442).
#
# The families and their node lists are generated from the pinned sml2c
# taxonomy — see node_add_menu_sysml_generated.py (regenerate with
# tools/sysml/gen_sysml_nodes.py). This module only builds the menu structure;
# never hand-edit the generated data.

from bpy.types import Menu
from bpy.app.translations import (
    contexts as i18n_contexts,
)
from bl_ui import node_add_menu
from bl_ui.node_add_menu_sysml_generated import SYSML_MENU_FAMILIES


def _family_slug(label):
    return label.lower().replace(" ", "_").replace("&", "and")


def _make_family_draw(nodes):
    def draw(self, _context):
        layout = self.layout
        for idname, _label in nodes:
            self.node_operator(layout, idname)
    return draw


# One base Menu class per family, built from the generated taxonomy. The
# Add/Swap variants (with node_operator) are produced by generate_menus below.
_family_bases = {}
for _family, _accent, _nodes in SYSML_MENU_FAMILIES:
    _family_bases[_family] = type(
        f"NODE_MT_sysml_fam_{_family_slug(_family)}_base",
        (Menu,),
        {"bl_label": _family, "draw": _make_family_draw(_nodes)},
    )


class NODE_MT_sysml_node_all_base(node_add_menu.NodeMenu):
    bl_label = ""
    menu_path = "Root"
    bl_translation_context = i18n_contexts.operator_default

    # Menus are looked up by label, so the Add & Swap roots share this layout
    # while each resolving to its corresponding per-family menu.
    def draw(self, context):
        del context
        layout = self.layout
        for family, _accent, _nodes in SYSML_MENU_FAMILIES:
            self.draw_menu(layout, family)
        layout.separator()
        self.draw_menu(layout, "Group")
        self.draw_menu(layout, "Layout")

        self.draw_root_assets(layout)


def _menu_dict(suffix, all_idname):
    d = {
        f"NODE_MT_category_sysml_{_family_slug(family)}{suffix}": cls
        for family, cls in _family_bases.items()
    }
    d[all_idname] = NODE_MT_sysml_node_all_base
    return d


add_menus = node_add_menu.generate_menus(
    _menu_dict("", "NODE_MT_sysml_node_add_all"),
    template=node_add_menu.AddNodeMenu,
    base_dict=node_add_menu.add_base_pathing_dict,
)


swap_menus = node_add_menu.generate_menus(
    _menu_dict("_swap", "NODE_MT_sysml_node_swap_all"),
    template=node_add_menu.SwapNodeMenu,
    base_dict=node_add_menu.swap_base_pathing_dict,
)


classes = (
    *add_menus,
    *swap_menus,
)


if __name__ == "__main__":  # only for live edit.
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
