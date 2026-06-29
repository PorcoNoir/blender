/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 *
 * SysML v2 `connection` usage element node (BSML0 / SCRUM-433).
 *
 * A connector usage linking two endpoints: wire each end's `self` output into
 * `connect` and `to` (e.g. two part usages). Optionally typed by a
 * ConnectionDef through `of`.
 */

#include "BKE_node.hh"

#include "DNA_node_types.h"

#include "node_sysml_util.hh"

namespace blender::nodes {

static void sysml_connection_usage_init(bNodeTree *ntree, bNode *node)
{
  sysml_node_storage_init(node);
  bke::node_add_socket(*ntree, *node, SOCK_OUT, "NodeSocketSysMLElement", "self", "Self");
  bke::node_add_socket(*ntree, *node, SOCK_IN, "NodeSocketSysMLElement", "of", "Type");
  bke::node_add_socket(*ntree, *node, SOCK_IN, "NodeSocketSysMLElement", "connect", "Connect");
  bke::node_add_socket(*ntree, *node, SOCK_IN, "NodeSocketSysMLElement", "to", "To");
}

void register_node_type_sysml_connection_usage()
{
  static bke::bNodeType ntype;

  sysml_node_type_base(&ntype, "SysMLNodeConnectionUsage"_ustr);
  ntype.ui_name = "Connection Usage";
  ntype.ui_description = "SysML v2 connection usage (connect ... to ...)";
  ntype.nclass = NODE_CLASS_INPUT;
  ntype.initfunc = sysml_connection_usage_init;
  sysml_node_storage_register(ntype);

  bke::node_register_type(ntype);
}

}  // namespace blender::nodes
