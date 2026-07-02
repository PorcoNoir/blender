/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup spnode
 *
 * File -> Import -> SysML (.sysml) operator (BSML2 / SCRUM-450). Picks a
 * `.sysml` file, runs it through the bundled sml2c bridge, and builds an
 * auto-laid-out SysML node graph. Imports into the active SysML node tree when
 * one is open, otherwise creates a new `SysMLNodeTree` data-block named after
 * the file. Registered as `NODE_OT_sysml_import` so it is scriptable from bpy.
 */

#include <string>

#include "DNA_node_types.h"
#include "DNA_space_types.h"

#include "BLI_path_utils.hh"

#include "BKE_context.hh"
#include "BKE_main.hh"
#include "BKE_node.hh"
#include "BKE_node_tree_update.hh"
#include "BKE_report.hh"

#include "RNA_access.hh"
#include "RNA_define.hh"

#include "WM_api.hh"
#include "WM_types.hh"

#include "NOD_sysml_import.hh"

#include "node_intern.hh" /* own include */

namespace blender::ed::space_node {

static wmOperatorStatus sysml_import_exec(bContext *C, wmOperator *op)
{
  char filepath[FILE_MAX];
  RNA_string_get(op->ptr, "filepath", filepath);
  if (filepath[0] == '\0') {
    BKE_report(op->reports, RPT_ERROR, "No file path given");
    return OPERATOR_CANCELLED;
  }

  Main *bmain = CTX_data_main(C);

  /* Prefer the active SysML tree; otherwise import into a fresh data-block so
   * the operator also works from the File menu with no node editor open. */
  SpaceNode *snode = CTX_wm_space_node(C);
  bNodeTree *tree = (snode && snode->edittree && snode->edittree->type == NTREE_SYSML) ?
                        snode->edittree :
                        nullptr;
  const bool created = tree == nullptr;
  if (created) {
    std::string tree_name = BLI_path_basename(filepath);
    const size_t dot = tree_name.find_last_of('.');
    if (dot != std::string::npos) {
      tree_name.resize(dot);
    }
    if (tree_name.empty()) {
      tree_name = "SysML";
    }
    tree = bke::node_tree_add_tree(bmain, tree_name, "SysMLNodeTree");
  }

  std::string report;
  const int nodes_added = nodes::sysml::import_sysml_file(C, *tree, filepath, report);
  if (nodes_added < 0) {
    BKE_report(op->reports, RPT_ERROR, report.empty() ? "sml2c import failed" : report.c_str());
    return OPERATOR_CANCELLED;
  }

  BKE_ntree_update_tag_all(tree);
  BKE_ntree_update(*bmain);
  WM_event_add_notifier(C, NC_NODE | NA_ADDED, nullptr);
  WM_event_add_notifier(C, NC_SPACE | ND_SPACE_NODE, nullptr);

  BKE_reportf(op->reports,
              RPT_INFO,
              "Imported %d SysML node%s from %s",
              nodes_added,
              nodes_added == 1 ? "" : "s",
              BLI_path_basename(filepath));
  /* Unresolved references / unmapped kinds are non-fatal; report them. */
  if (!report.empty()) {
    BKE_report(op->reports, RPT_WARNING, report.c_str());
  }
  return OPERATOR_FINISHED;
}

static wmOperatorStatus sysml_import_invoke(bContext *C, wmOperator *op, const wmEvent *event)
{
  if (RNA_struct_property_is_set(op->ptr, "filepath")) {
    return sysml_import_exec(C, op);
  }
  return WM_operator_filesel(C, op, event);
}

void NODE_OT_sysml_import(wmOperatorType *ot)
{
  ot->name = "Import SysML";
  ot->description = "Import a SysML v2 (.sysml) model as a node graph";
  ot->idname = "NODE_OT_sysml_import";

  ot->invoke = sysml_import_invoke;
  ot->exec = sysml_import_exec;
  /* No poll: reachable from the File menu without an open node editor. */

  ot->flag = OPTYPE_REGISTER | OPTYPE_UNDO;

  WM_operator_properties_filesel(ot,
                                 FILE_TYPE_FOLDER,
                                 FILE_SPECIAL,
                                 FILE_OPENFILE,
                                 WM_FILESEL_FILEPATH,
                                 FILE_DEFAULTDISPLAY,
                                 FILE_SORT_DEFAULT);
  PropertyRNA *prop = RNA_def_string(ot->srna, "filter_glob", "*.sysml", 0, "", "");
  RNA_def_property_flag(prop, PROP_HIDDEN | PROP_SKIP_SAVE);
}

}  // namespace blender::ed::space_node
