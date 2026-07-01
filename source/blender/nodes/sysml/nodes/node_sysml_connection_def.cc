/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 *
 * AUTO-GENERATED - DO NOT EDIT.
 * Regenerate: python tools/sysml/gen_sysml_nodes.py
 */

#include "BKE_node.hh"

#include "DNA_node_types.h"

#include "node_sysml_util.hh"

namespace blender::nodes {

static void sysml_connection_def_init(bNodeTree *ntree, bNode *node)
{
  sysml_node_storage_init(node);
  bke::node_add_socket(*ntree, *node, SOCK_OUT, "NodeSocketSysMLElement", "self", "Self");
  bke::node_add_socket(*ntree, *node, SOCK_IN, "NodeSocketSysMLElement", "specializes", "Specializes");
}

void register_node_type_sysml_connection_def()
{
  static bke::bNodeType ntype;

  sysml_node_type_base(&ntype, "SysMLNodeConnectionDef"_ustr);
  ntype.ui_name = "Connection Definition";
  ntype.ui_description = "SysML v2 connection definition";
  ntype.nclass = NODE_CLASS_INPUT;
  ntype.initfunc = sysml_connection_def_init;
  sysml_node_storage_register(ntype);

  bke::node_register_type(ntype);
}

}  // namespace blender::nodes
