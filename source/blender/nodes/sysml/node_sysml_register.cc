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

  /* Element nodes (SCRUM-433). */
  nodes::register_node_type_sysml_part_def();
  nodes::register_node_type_sysml_part_usage();
  nodes::register_node_type_sysml_connection_usage();
}

}  // namespace blender
