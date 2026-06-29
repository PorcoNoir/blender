/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "NOD_register.hh"

#include "node_sysml_register.hh"

namespace blender {

void register_sysml_nodes()
{
  register_node_tree_type_sysml();
  register_node_socket_type_sysml_element();

  /* Element nodes (PartDef, PartUsage, ConnectionUsage, …) are registered
   * here once SCRUM-433 lands. */
}

}  // namespace blender
