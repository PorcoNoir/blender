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

/* sml2c AST (kind, defKind) -> SysML node idname; empty when unmapped. */
inline const char *sysml_import_idname(std::string_view kind, std::string_view def_kind)
{
  if (kind == "Definition") {
    if (def_kind == "ActionDef") return "SysMLNodeActionDef";
    if (def_kind == "AllocationDef") return "SysMLNodeAllocationDef";
    if (def_kind == "AnalysisCaseDef") return "SysMLNodeAnalysisCaseDef";
    if (def_kind == "AttributeDef") return "SysMLNodeAttributeDef";
    if (def_kind == "CalcDef") return "SysMLNodeCalcDef";
    if (def_kind == "CaseDef") return "SysMLNodeCaseDef";
    if (def_kind == "ConcernDef") return "SysMLNodeConcernDef";
    if (def_kind == "ConjugatedPortDef") return "SysMLNodeConjugatedPortDef";
    if (def_kind == "ConnectionDef") return "SysMLNodeConnectionDef";
    if (def_kind == "ConstraintDef") return "SysMLNodeConstraintDef";
    if (def_kind == "EnumDef") return "SysMLNodeEnumerationDef";
    if (def_kind == "FlowDef") return "SysMLNodeFlowDef";
    if (def_kind == "IndividualDef") return "SysMLNodePartDef";
    if (def_kind == "InterfaceDef") return "SysMLNodeInterfaceDef";
    if (def_kind == "ItemDef") return "SysMLNodeItemDef";
    if (def_kind == "MetadataDef") return "SysMLNodeMetadataDef";
    if (def_kind == "OccurrenceDef") return "SysMLNodeOccurrenceDef";
    if (def_kind == "PartDef") return "SysMLNodePartDef";
    if (def_kind == "PortDef") return "SysMLNodePortDef";
    if (def_kind == "RenderingDef") return "SysMLNodeRenderingDef";
    if (def_kind == "RequirementDef") return "SysMLNodeRequirementDef";
    if (def_kind == "StateDef") return "SysMLNodeStateDef";
    if (def_kind == "UseCaseDef") return "SysMLNodeUseCaseDef";
    if (def_kind == "VerificationCaseDef") return "SysMLNodeVerificationCaseDef";
    if (def_kind == "ViewDef") return "SysMLNodeViewDef";
    if (def_kind == "ViewpointDef") return "SysMLNodeViewpointDef";
  }
  if (kind == "Usage") {
    if (def_kind == "ActionDef") return "SysMLNodeActionUsage";
    if (def_kind == "AllocationDef") return "SysMLNodeAllocationUsage";
    if (def_kind == "AnalysisCaseDef") return "SysMLNodeAnalysisCaseUsage";
    if (def_kind == "AttributeDef") return "SysMLNodeAttributeUsage";
    if (def_kind == "CalcDef") return "SysMLNodeCalcUsage";
    if (def_kind == "CaseDef") return "SysMLNodeCaseUsage";
    if (def_kind == "ConcernDef") return "SysMLNodeConcernUsage";
    if (def_kind == "ConnectionDef") return "SysMLNodeConnectionUsage";
    if (def_kind == "ConstraintDef") return "SysMLNodeConstraintUsage";
    if (def_kind == "End") return "SysMLNodeReferenceUsage";
    if (def_kind == "EnumDef") return "SysMLNodeEnumerationUsage";
    if (def_kind == "FlowDef") return "SysMLNodeFlowUsage";
    if (def_kind == "IndividualDef") return "SysMLNodePartUsage";
    if (def_kind == "InterfaceDef") return "SysMLNodeInterfaceUsage";
    if (def_kind == "ItemDef") return "SysMLNodeItemUsage";
    if (def_kind == "MetadataDef") return "SysMLNodeMetadataUsage";
    if (def_kind == "OccurrenceDef") return "SysMLNodeOccurrenceUsage";
    if (def_kind == "PartDef") return "SysMLNodePartUsage";
    if (def_kind == "PortDef") return "SysMLNodePortUsage";
    if (def_kind == "ReferenceUsage") return "SysMLNodeReferenceUsage";
    if (def_kind == "RenderingDef") return "SysMLNodeRenderingUsage";
    if (def_kind == "RequirementDef") return "SysMLNodeRequirementUsage";
    if (def_kind == "StateDef") return "SysMLNodeStateUsage";
    if (def_kind == "UseCaseDef") return "SysMLNodeUseCaseUsage";
    if (def_kind == "VerificationCaseDef") return "SysMLNodeVerificationCaseUsage";
    if (def_kind == "ViewDef") return "SysMLNodeViewUsage";
    if (def_kind == "ViewpointDef") return "SysMLNodeViewpointUsage";
  }
  if (kind == "Attribute") return "SysMLNodeAttributeUsage";
  if (kind == "Package") return "SysMLNodePackage";
  return "";
}

}  // namespace blender::nodes::sysml
