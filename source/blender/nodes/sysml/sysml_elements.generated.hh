/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 *
 * AUTO-GENERATED - DO NOT EDIT.
 * Regenerate: python tools/sysml/gen_sysml_nodes.py
 * sml2c version:  sml2c 0.45.4-alpha
 * Element kinds:  58  (41 harvested from sml2c, 17 fallback-seeded)
 *
 * X-macro table of SysML element kinds driving node registration. Each row:
 *   X(editor_id, node_idname, ui_name, is_container, is_usage, can_specialize)
 */

#pragma once

/* clang-format off */
#define SYSML_ELEMENT_KINDS \
  X("sysml.action_def", "SysMLNodeActionDef", "Action Definition", true, false, false) \
  X("sysml.action_usage", "SysMLNodeActionUsage", "Action Usage", false, true, false) \
  X("sysml.alias", "SysMLNodeAlias", "Alias", false, false, false) \
  X("sysml.allocation_def", "SysMLNodeAllocationDef", "Allocation Definition", true, false, false) \
  X("sysml.allocation_usage", "SysMLNodeAllocationUsage", "Allocation Usage", false, true, false) \
  X("sysml.analysis_case_def", "SysMLNodeAnalysisCaseDef", "Analysis Case Definition", true, false, true) \
  X("sysml.analysis_case_usage", "SysMLNodeAnalysisCaseUsage", "Analysis Case Usage", true, true, false) \
  X("sysml.attribute_def", "SysMLNodeAttributeDef", "Attribute Definition", true, false, false) \
  X("sysml.attribute_usage", "SysMLNodeAttributeUsage", "Attribute Usage", false, true, false) \
  X("sysml.binding_usage", "SysMLNodeBindingUsage", "Binding Usage", false, true, false) \
  X("sysml.calc_def", "SysMLNodeCalcDef", "Calc Definition", true, false, false) \
  X("sysml.calc_usage", "SysMLNodeCalcUsage", "Calc Usage", false, true, false) \
  X("sysml.case_def", "SysMLNodeCaseDef", "Case Definition", true, false, true) \
  X("sysml.case_usage", "SysMLNodeCaseUsage", "Case Usage", true, true, false) \
  X("sysml.comment", "SysMLNodeComment", "Comment", false, false, false) \
  X("sysml.concern_def", "SysMLNodeConcernDef", "Concern Definition", true, false, false) \
  X("sysml.concern_usage", "SysMLNodeConcernUsage", "Concern Usage", false, true, false) \
  X("sysml.conjugated_port_def", "SysMLNodeConjugatedPortDef", "Conjugated Port Definition", true, false, true) \
  X("sysml.connection_def", "SysMLNodeConnectionDef", "Connection Definition", true, false, false) \
  X("sysml.connection_usage", "SysMLNodeConnectionUsage", "Connection Usage", false, true, false) \
  X("sysml.constraint_def", "SysMLNodeConstraintDef", "Constraint Definition", true, false, false) \
  X("sysml.constraint_usage", "SysMLNodeConstraintUsage", "Constraint Usage", false, true, false) \
  X("sysml.documentation", "SysMLNodeDocumentation", "Documentation", false, false, false) \
  X("sysml.enumeration_def", "SysMLNodeEnumerationDef", "Enumeration Definition", true, false, false) \
  X("sysml.enumeration_usage", "SysMLNodeEnumerationUsage", "Enumeration Usage", false, true, false) \
  X("sysml.flow_def", "SysMLNodeFlowDef", "Flow Definition", true, false, false) \
  X("sysml.flow_usage", "SysMLNodeFlowUsage", "Flow Usage", false, true, false) \
  X("sysml.import", "SysMLNodeImport", "Import", false, false, false) \
  X("sysml.interface_def", "SysMLNodeInterfaceDef", "Interface Definition", true, false, false) \
  X("sysml.interface_usage", "SysMLNodeInterfaceUsage", "Interface Usage", false, true, false) \
  X("sysml.item_def", "SysMLNodeItemDef", "Item Definition", true, false, false) \
  X("sysml.item_usage", "SysMLNodeItemUsage", "Item Usage", false, true, false) \
  X("sysml.library_package", "SysMLNodeLibraryPackage", "Library Package", true, false, false) \
  X("sysml.metadata_def", "SysMLNodeMetadataDef", "Metadata Definition", true, false, false) \
  X("sysml.metadata_usage", "SysMLNodeMetadataUsage", "Metadata Usage", false, true, false) \
  X("sysml.occurrence_def", "SysMLNodeOccurrenceDef", "Occurrence Definition", true, false, false) \
  X("sysml.occurrence_usage", "SysMLNodeOccurrenceUsage", "Occurrence Usage", false, true, false) \
  X("sysml.package", "SysMLNodePackage", "Package", true, false, false) \
  X("sysml.part_def", "SysMLNodePartDef", "Part Definition", true, false, false) \
  X("sysml.part_usage", "SysMLNodePartUsage", "Part Usage", true, true, false) \
  X("sysml.port_def", "SysMLNodePortDef", "Port Definition", true, false, false) \
  X("sysml.port_usage", "SysMLNodePortUsage", "Port Usage", false, true, false) \
  X("sysml.reference_usage", "SysMLNodeReferenceUsage", "Reference Usage", false, true, false) \
  X("sysml.rendering_def", "SysMLNodeRenderingDef", "Rendering Definition", true, false, false) \
  X("sysml.rendering_usage", "SysMLNodeRenderingUsage", "Rendering Usage", false, true, false) \
  X("sysml.requirement_def", "SysMLNodeRequirementDef", "Requirement Definition", true, false, false) \
  X("sysml.requirement_usage", "SysMLNodeRequirementUsage", "Requirement Usage", false, true, false) \
  X("sysml.state_def", "SysMLNodeStateDef", "State Definition", true, false, false) \
  X("sysml.state_usage", "SysMLNodeStateUsage", "State Usage", false, true, false) \
  X("sysml.succession_usage", "SysMLNodeSuccessionUsage", "Succession Usage", false, true, false) \
  X("sysml.use_case_def", "SysMLNodeUseCaseDef", "Use Case Definition", true, false, true) \
  X("sysml.use_case_usage", "SysMLNodeUseCaseUsage", "Use Case Usage", true, true, false) \
  X("sysml.verification_case_def", "SysMLNodeVerificationCaseDef", "Verification Case Definition", true, false, true) \
  X("sysml.verification_case_usage", "SysMLNodeVerificationCaseUsage", "Verification Case Usage", true, true, false) \
  X("sysml.view_def", "SysMLNodeViewDef", "View Definition", true, false, false) \
  X("sysml.view_usage", "SysMLNodeViewUsage", "View Usage", false, true, false) \
  X("sysml.viewpoint_def", "SysMLNodeViewpointDef", "Viewpoint Definition", true, false, false) \
  X("sysml.viewpoint_usage", "SysMLNodeViewpointUsage", "Viewpoint Usage", false, true, false)
/* clang-format on */
