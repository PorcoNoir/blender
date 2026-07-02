/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup spnode
 *
 * File -> Export -> SysML (.sysml) operator (BSML3 / SCRUM-498). Writes a
 * SysML node tree back out as canonical `.sysml` notation. Exports the active
 * SysML editor's tree, or the tree named by the `tree_name` property (so it is
 * scriptable / testable headless). Registered as `NODE_OT_sysml_export`.
 */

#include <string>

#include "DNA_ID.h"
#include "DNA_node_types.h"
#include "DNA_space_types.h"

#include "BLI_path_utils.hh"

#include "BKE_context.hh"
#include "BKE_lib_id.hh"
#include "BKE_main.hh"
#include "BKE_report.hh"

#include "RNA_access.hh"
#include "RNA_define.hh"

#include "WM_api.hh"
#include "WM_types.hh"

#include "NOD_sysml_export.hh"

#include "node_intern.hh" /* own include */

namespace blender::ed::space_node {

static wmOperatorStatus sysml_export_exec(bContext *C, wmOperator *op)
{
  char filepath[FILE_MAX];
  RNA_string_get(op->ptr, "filepath", filepath);
  if (filepath[0] == '\0') {
    BKE_report(op->reports, RPT_ERROR, "No file path given");
    return OPERATOR_CANCELLED;
  }

  Main *bmain = CTX_data_main(C);

  /* An explicit tree name wins (scripting / tests); otherwise the active
   * SysML editor's tree. */
  bNodeTree *tree = nullptr;
  char tree_name[MAX_ID_NAME - 2];
  RNA_string_get(op->ptr, "tree_name", tree_name);
  if (tree_name[0] != '\0') {
    tree = reinterpret_cast<bNodeTree *>(BKE_libblock_find_name(bmain, ID_NT, tree_name));
  }
  else if (SpaceNode *snode = CTX_wm_space_node(C)) {
    tree = snode->edittree;
  }
  if (tree == nullptr || tree->type != NTREE_SYSML) {
    BKE_report(op->reports, RPT_ERROR, "No SysML node tree to export");
    return OPERATOR_CANCELLED;
  }

  std::string report;
  const int elements = nodes::sysml::export_sysml_notation_file(*tree, filepath, report);
  if (elements < 0) {
    BKE_report(op->reports, RPT_ERROR, report.empty() ? "SysML export failed" : report.c_str());
    return OPERATOR_CANCELLED;
  }

  BKE_reportf(op->reports,
              RPT_INFO,
              "Exported %d SysML element%s to %s",
              elements,
              elements == 1 ? "" : "s",
              BLI_path_basename(filepath));
  return OPERATOR_FINISHED;
}

static wmOperatorStatus sysml_export_invoke(bContext *C, wmOperator *op, const wmEvent *event)
{
  if (RNA_struct_property_is_set(op->ptr, "filepath")) {
    return sysml_export_exec(C, op);
  }
  return WM_operator_filesel(C, op, event);
}

void NODE_OT_sysml_export(wmOperatorType *ot)
{
  ot->name = "Export SysML";
  ot->description = "Export the SysML node graph as canonical .sysml text";
  ot->idname = "NODE_OT_sysml_export";

  ot->invoke = sysml_export_invoke;
  ot->exec = sysml_export_exec;

  ot->flag = OPTYPE_REGISTER;

  WM_operator_properties_filesel(ot,
                                 FILE_TYPE_FOLDER,
                                 FILE_SPECIAL,
                                 FILE_SAVE,
                                 WM_FILESEL_FILEPATH,
                                 FILE_DEFAULTDISPLAY,
                                 FILE_SORT_DEFAULT);
  PropertyRNA *prop = RNA_def_string(ot->srna, "filter_glob", "*.sysml", 0, "", "");
  RNA_def_property_flag(prop, PROP_HIDDEN | PROP_SKIP_SAVE);
  prop = RNA_def_string(ot->srna,
                        "tree_name",
                        nullptr,
                        MAX_ID_NAME - 2,
                        "Tree",
                        "SysML node tree to export (defaults to the active editor's tree)");
  RNA_def_property_flag(prop, PROP_SKIP_SAVE);
}

}  // namespace blender::ed::space_node
