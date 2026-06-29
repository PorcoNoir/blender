/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 *
 * Registration of the SysML v2 node tree type (`NTREE_SYSML`,
 * idname `"SysMLNodeTree"`). BSML0 / SCRUM-430.
 */

#include "MEM_guardedalloc.h"

#include "NOD_sysml.hh"

#include "BKE_node.hh"

#include "DNA_node_types.h"

#include "RNA_prototypes.hh"

#include "UI_resources.hh"

#include "BLT_translation.hh"

#include "node_common.h"

namespace blender {

bke::bNodeTreeType *ntreeType_SysML;

/**
 * Resolve the active SysML tree from context. The standalone SysML node
 * editor drives the active tree from its header selector / pin, so there is
 * no datablock-derived context to resolve yet. SCRUM-431 (editor + add-menu)
 * fleshes this out; for now it is a valid no-op.
 */
static void sysml_node_tree_get_from_context(const bContext * /*C*/,
                                             bke::bNodeTreeType * /*treetype*/,
                                             bNodeTree ** /*r_ntree*/,
                                             ID ** /*r_id*/,
                                             ID ** /*r_from*/)
{
}

static void sysml_node_tree_update(bNodeTree *ntree)
{
  /* Keep reroute socket types consistent, mirroring the other trees. */
  ntree_update_reroute_nodes(ntree);
}

/**
 * Add-menu top-level categories. The full SysML category set (package /
 * definition / usage / port / connection / requirement / behavior / case /
 * view / metadata / doc) lands with the node stories (SCRUM-431/433); these
 * generic classes are enough for the tree to register and draw.
 */
static void foreach_nodeclass(void *calldata, bke::bNodeClassCallback func)
{
  func(calldata, NODE_CLASS_INPUT, N_("Input"));
  func(calldata, NODE_CLASS_LAYOUT, N_("Layout"));
}

void register_node_tree_type_sysml()
{
  bke::bNodeTreeType *tt = ntreeType_SysML = MEM_new<bke::bNodeTreeType>(__func__);

  tt->type = NTREE_SYSML;
  tt->idname = "SysMLNodeTree"_ustr;
  tt->group_idname = "SysMLNodeGroup"_ustr;
  tt->ui_name = N_("SysML Node Editor");
  tt->ui_icon = ICON_NODETREE; /* Dedicated icon comes with the editor story. */
  tt->ui_description = N_("Model OMG SysML v2 elements and relationships using nodes");

  tt->get_from_context = sysml_node_tree_get_from_context;
  tt->update = sysml_node_tree_update;
  tt->foreach_nodeclass = foreach_nodeclass;

  tt->rna_ext.srna = RNA_SysMLNodeTree;

  bke::node_tree_type_add(*tt);
}

}  // namespace blender
