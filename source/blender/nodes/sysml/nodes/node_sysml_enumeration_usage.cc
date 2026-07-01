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

static void sysml_enumeration_usage_init(bNodeTree *ntree, bNode *node)
{
  sysml_node_storage_init(node);
  bke::node_add_socket(*ntree, *node, SOCK_OUT, "NodeSocketSysMLElement", "self", "Self");
  bke::node_add_socket(*ntree, *node, SOCK_IN, "NodeSocketSysMLElement", "of", "Type");
  bke::node_add_socket(*ntree, *node, SOCK_IN, "NodeSocketSysMLElement", "redefines", "Redefines");
  node->color[0] = 0.6627f;
  node->color[1] = 0.6157f;
  node->color[2] = 0.8314f;
  node->flag |= NODE_CUSTOM_COLOR;  /* family accent */
}

void register_node_type_sysml_enumeration_usage()
{
  static bke::bNodeType ntype;

  sysml_node_type_base(&ntype, "SysMLNodeEnumerationUsage"_ustr);
  ntype.ui_name = "Enumeration Usage";
  ntype.ui_description = "SysML v2 enumeration usage";
  ntype.nclass = NODE_CLASS_INPUT;
  ntype.initfunc = sysml_enumeration_usage_init;
  sysml_node_storage_register(ntype);

  bke::node_register_type(ntype);
}

}  // namespace blender::nodes
