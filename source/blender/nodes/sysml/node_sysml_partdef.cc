/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 *
 * SysML v2 `part def` element node (BSML0 / SCRUM-433).
 *
 * A Definition: it can contain members and specialize a supertype. Hand-written
 * to validate the node shape the BSML1 generator will later template. Custom
 * fields (short name, multiplicity) arrive with the `NodeSysMLElement` storage
 * struct in SCRUM-434; here the node carries its sockets and the standard name.
 */

#include "BKE_node.hh"

#include "DNA_node_types.h"

#include "node_sysml_util.hh"

namespace blender::nodes {

static void sysml_part_def_init(bNodeTree *ntree, bNode *node)
{
  bke::node_add_socket(*ntree, *node, SOCK_OUT, "NodeSocketSysMLElement", "self", "Self");
  bke::node_add_socket(*ntree, *node, SOCK_IN, "NodeSocketSysMLElement", "members", "Members");
  bke::node_add_socket(
      *ntree, *node, SOCK_IN, "NodeSocketSysMLElement", "specializes", "Specializes");
}

void register_node_type_sysml_part_def()
{
  static bke::bNodeType ntype;

  sysml_node_type_base(&ntype, "SysMLNodePartDef"_ustr);
  ntype.ui_name = "Part Definition";
  ntype.ui_description = "SysML v2 part definition (part def)";
  ntype.nclass = NODE_CLASS_INPUT;
  ntype.initfunc = sysml_part_def_init;

  bke::node_register_type(ntype);
}

}  // namespace blender::nodes
