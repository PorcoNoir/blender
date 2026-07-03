/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup spnode
 *
 * File -> Export -> SysML operators (BSML3 / SCRUM-498, SCRUM-500). Write a
 * SysML node tree back out as canonical `.sysml` notation (`NODE_OT_sysml_export`)
 * or as a bpy graph-builder `.py` (`NODE_OT_sysml_export_bpy`). Both export the
 * active SysML editor's tree, or the tree named by the `tree_name` property (so
 * they are scriptable / testable headless).
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

/* The tree to export: an explicit `tree_name` (scripting / tests) wins,
 * otherwise the active SysML editor's tree. Reports and returns null on miss. */
static bNodeTree *resolve_export_tree(bContext *C, wmOperator *op)
{
  Main *bmain = CTX_data_main(C);
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
    return nullptr;
  }
  return tree;
}

static bool export_filepath(wmOperator *op, char r_filepath[FILE_MAX])
{
  RNA_string_get(op->ptr, "filepath", r_filepath);
  if (r_filepath[0] == '\0') {
    BKE_report(op->reports, RPT_ERROR, "No file path given");
    return false;
  }
  return true;
}

static wmOperatorStatus export_invoke(bContext *C, wmOperator *op, const wmEvent *event)
{
  /* WM_operator_filesel runs exec directly when a filepath is already set. */
  return WM_operator_filesel(C, op, event);
}

static void export_filesel_props(wmOperatorType *ot, const char *glob)
{
  WM_operator_properties_filesel(ot,
                                 FILE_TYPE_FOLDER,
                                 FILE_SPECIAL,
                                 FILE_SAVE,
                                 WM_FILESEL_FILEPATH,
                                 FILE_DEFAULTDISPLAY,
                                 FILE_SORT_DEFAULT);
  PropertyRNA *prop = RNA_def_string(ot->srna, "filter_glob", glob, 0, "", "");
  RNA_def_property_flag(prop, PROP_HIDDEN | PROP_SKIP_SAVE);
  prop = RNA_def_string(ot->srna,
                        "tree_name",
                        nullptr,
                        MAX_ID_NAME - 2,
                        "Tree",
                        "SysML node tree to export (defaults to the active editor's tree)");
  RNA_def_property_flag(prop, PROP_SKIP_SAVE);
}

/* -------------------------------------------------------------------------- */
/* Notation (.sysml) */

static wmOperatorStatus sysml_export_exec(bContext *C, wmOperator *op)
{
  char filepath[FILE_MAX];
  if (!export_filepath(op, filepath)) {
    return OPERATOR_CANCELLED;
  }
  bNodeTree *tree = resolve_export_tree(C, op);
  if (tree == nullptr) {
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

void NODE_OT_sysml_export(wmOperatorType *ot)
{
  ot->name = "Export SysML";
  ot->description = "Export the SysML node graph as canonical .sysml text";
  ot->idname = "NODE_OT_sysml_export";

  ot->invoke = export_invoke;
  ot->exec = sysml_export_exec;
  ot->flag = OPTYPE_REGISTER;

  export_filesel_props(ot, "*.sysml");
}

/* -------------------------------------------------------------------------- */
/* bpy graph-builder (.py) */

static wmOperatorStatus sysml_export_bpy_exec(bContext *C, wmOperator *op)
{
  char filepath[FILE_MAX];
  if (!export_filepath(op, filepath)) {
    return OPERATOR_CANCELLED;
  }
  bNodeTree *tree = resolve_export_tree(C, op);
  if (tree == nullptr) {
    return OPERATOR_CANCELLED;
  }

  std::string report;
  const int count = nodes::sysml::export_sysml_bpy_file(*tree, filepath, report);
  if (count < 0) {
    BKE_report(op->reports, RPT_ERROR, report.empty() ? "SysML bpy export failed" : report.c_str());
    return OPERATOR_CANCELLED;
  }
  BKE_reportf(op->reports,
              RPT_INFO,
              "Exported a bpy builder for %d SysML node%s to %s",
              count,
              count == 1 ? "" : "s",
              BLI_path_basename(filepath));
  return OPERATOR_FINISHED;
}

void NODE_OT_sysml_export_bpy(wmOperatorType *ot)
{
  ot->name = "Export SysML as bpy";
  ot->description = "Export the SysML node graph as a bpy graph-builder Python script";
  ot->idname = "NODE_OT_sysml_export_bpy";

  ot->invoke = export_invoke;
  ot->exec = sysml_export_bpy_exec;
  ot->flag = OPTYPE_REGISTER;

  export_filesel_props(ot, "*.py");
}

}  // namespace blender::ed::space_node
