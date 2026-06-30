/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 *
 * SysML v2 `part` usage element node (BSML0 / SCRUM-433).
 *
 * A Usage: typed by a Definition through `of` (e.g. `part p : PartDef`), may
 * contain members and redefine an inherited feature. Wire a `PartDef`'s `self`
 * output into `of` to express the typing.
 */

#include "BKE_node.hh"

#include "DNA_node_types.h"

#include "node_sysml_util.hh"

namespace blender::nodes {

static void sysml_part_usage_init(bNodeTree *ntree, bNode *node)
{
  sysml_node_storage_init(node);
  bke::node_add_socket(*ntree, *node, SOCK_OUT, "NodeSocketSysMLElement", "self", "Self");
  bke::node_add_socket(*ntree, *node, SOCK_IN, "NodeSocketSysMLElement", "members", "Members");
  bke::node_add_socket(*ntree, *node, SOCK_IN, "NodeSocketSysMLElement", "of", "Type");
  bke::node_add_socket(
      *ntree, *node, SOCK_IN, "NodeSocketSysMLElement", "redefines", "Redefines");
}

void register_node_type_sysml_part_usage()
{
  static bke::bNodeType ntype;

  sysml_node_type_base(&ntype, "SysMLNodePartUsage"_ustr);
  ntype.ui_name = "Part Usage";
  ntype.ui_description = "SysML v2 part usage (typed by a part def via 'Type')";
  ntype.nclass = NODE_CLASS_INPUT;
  ntype.initfunc = sysml_part_usage_init;
  sysml_node_storage_register(ntype);

  bke::node_register_type(ntype);
}

}  // namespace blender::nodes
