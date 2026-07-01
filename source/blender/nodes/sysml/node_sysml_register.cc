/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "NOD_register.hh"

#include "node_sysml_register.hh"

#include "sysml_nodes_register.generated.hh"

namespace blender {

void register_sysml_nodes()
{
  register_node_tree_type_sysml();
  register_node_socket_type_sysml_element();

  /* All generated element nodes (BSML1). */
  nodes::register_generated_sysml_nodes();
}

}  // namespace blender
