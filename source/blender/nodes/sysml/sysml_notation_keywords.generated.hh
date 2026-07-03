/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 *
 * AUTO-GENERATED - DO NOT EDIT.
 * Regenerate: python tools/sysml/gen_sysml_nodes.py
 */

#pragma once

#include <string_view>

namespace blender::nodes::sysml {

/* SysML node idname -> canonical notation keyword; empty when unknown. */
inline const char *sysml_notation_keyword(std::string_view idname)
{
  if (idname == "SysMLNodeActionDef") return "action def";
  if (idname == "SysMLNodeActionUsage") return "action";
  if (idname == "SysMLNodeAlias") return "alias";
  if (idname == "SysMLNodeAllocationDef") return "allocation def";
  if (idname == "SysMLNodeAllocationUsage") return "allocation";
  if (idname == "SysMLNodeAnalysisCaseDef") return "analysis case def";
  if (idname == "SysMLNodeAnalysisCaseUsage") return "analysis case";
  if (idname == "SysMLNodeAttributeDef") return "attribute def";
  if (idname == "SysMLNodeAttributeUsage") return "attribute";
  if (idname == "SysMLNodeBindingUsage") return "bind";
  if (idname == "SysMLNodeCalcDef") return "calc def";
  if (idname == "SysMLNodeCalcUsage") return "calc";
  if (idname == "SysMLNodeCaseDef") return "case def";
  if (idname == "SysMLNodeCaseUsage") return "case";
  if (idname == "SysMLNodeComment") return "comment";
  if (idname == "SysMLNodeConcernDef") return "concern def";
  if (idname == "SysMLNodeConcernUsage") return "concern";
  if (idname == "SysMLNodeConjugatedPortDef") return "port def";
  if (idname == "SysMLNodeConnectionDef") return "connection def";
  if (idname == "SysMLNodeConnectionUsage") return "connection";
  if (idname == "SysMLNodeConstraintDef") return "constraint def";
  if (idname == "SysMLNodeConstraintUsage") return "constraint";
  if (idname == "SysMLNodeDocumentation") return "doc";
  if (idname == "SysMLNodeEnumerationDef") return "enum def";
  if (idname == "SysMLNodeEnumerationUsage") return "enum";
  if (idname == "SysMLNodeFlowDef") return "flow def";
  if (idname == "SysMLNodeFlowUsage") return "flow";
  if (idname == "SysMLNodeImport") return "import";
  if (idname == "SysMLNodeInterfaceDef") return "interface def";
  if (idname == "SysMLNodeInterfaceUsage") return "interface";
  if (idname == "SysMLNodeItemDef") return "item def";
  if (idname == "SysMLNodeItemUsage") return "item";
  if (idname == "SysMLNodeLibraryPackage") return "library package";
  if (idname == "SysMLNodeMetadataDef") return "metadata def";
  if (idname == "SysMLNodeMetadataUsage") return "metadata";
  if (idname == "SysMLNodeOccurrenceDef") return "occurrence def";
  if (idname == "SysMLNodeOccurrenceUsage") return "occurrence";
  if (idname == "SysMLNodePackage") return "package";
  if (idname == "SysMLNodePartDef") return "part def";
  if (idname == "SysMLNodePartUsage") return "part";
  if (idname == "SysMLNodePortDef") return "port def";
  if (idname == "SysMLNodePortUsage") return "port";
  if (idname == "SysMLNodeReferenceUsage") return "ref";
  if (idname == "SysMLNodeRenderingDef") return "rendering def";
  if (idname == "SysMLNodeRenderingUsage") return "rendering";
  if (idname == "SysMLNodeRequirementDef") return "requirement def";
  if (idname == "SysMLNodeRequirementUsage") return "requirement";
  if (idname == "SysMLNodeStateDef") return "state def";
  if (idname == "SysMLNodeStateUsage") return "state";
  if (idname == "SysMLNodeSuccessionUsage") return "succession";
  if (idname == "SysMLNodeUseCaseDef") return "use case def";
  if (idname == "SysMLNodeUseCaseUsage") return "use case";
  if (idname == "SysMLNodeVerificationCaseDef") return "verification case def";
  if (idname == "SysMLNodeVerificationCaseUsage") return "verification case";
  if (idname == "SysMLNodeViewDef") return "view def";
  if (idname == "SysMLNodeViewUsage") return "view";
  if (idname == "SysMLNodeViewpointDef") return "viewpoint def";
  if (idname == "SysMLNodeViewpointUsage") return "viewpoint";
  return "";
}

}  // namespace blender::nodes::sysml
