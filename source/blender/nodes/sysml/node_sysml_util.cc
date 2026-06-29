/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

#include "node_sysml_util.hh"

#include "MEM_guardedalloc.h"

#include "BLI_utildefines.hh"

#include "BLT_translation.hh"

#include "DNA_node_types.h"

#include "node_util.hh"

namespace blender::nodes {

bool sysml_node_poll_default(const bke::bNodeType * /*ntype*/,
                             const bNodeTree *ntree,
                             const char **r_disabled_hint)
{
  if (!STREQ(ntree->idname, "SysMLNodeTree")) {
    *r_disabled_hint = RPT_("Not a SysML node tree");
    return false;
  }
  return true;
}

void sysml_node_type_base(bke::bNodeType *ntype,
                          UString idname,
                          const std::optional<int16_t> legacy_type)
{
  bke::node_type_base(*ntype, idname, legacy_type);

  ntype->poll = sysml_node_poll_default;
  ntype->insert_link = node_insert_link_default;
}

void sysml_node_storage_register(bke::bNodeType &ntype)
{
  bke::node_type_storage(
      ntype, "NodeSysMLElement", node_free_standard_storage, node_copy_standard_storage);
}

void sysml_node_storage_init(bNode *node)
{
  node->storage = MEM_new<NodeSysMLElement>(__func__);
}

}  // namespace blender::nodes
