# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# AUTO-GENERATED - DO NOT EDIT. Regenerate: python tools/sysml/gen_sysml_nodes.py
#
# SysML add-menu families. Each entry: (family_label, accent_hex,
# [(node_idname, ui_name), ...]). Consumed by node_add_menu_sysml.py.

SYSML_MENU_FAMILIES = [
    ('Packages', '#7e9ac0', [
        ('SysMLNodeAlias', 'Alias'),
        ('SysMLNodeImport', 'Import'),
        ('SysMLNodeLibraryPackage', 'Library Package'),
        ('SysMLNodePackage', 'Package'),
    ]),
    ('Structure', '#a99dd4', [
        ('SysMLNodeAttributeDef', 'Attribute Definition'),
        ('SysMLNodeEnumerationDef', 'Enumeration Definition'),
        ('SysMLNodeItemDef', 'Item Definition'),
        ('SysMLNodeOccurrenceDef', 'Occurrence Definition'),
        ('SysMLNodePartDef', 'Part Definition'),
        ('SysMLNodeAttributeUsage', 'Attribute Usage'),
        ('SysMLNodeEnumerationUsage', 'Enumeration Usage'),
        ('SysMLNodeItemUsage', 'Item Usage'),
        ('SysMLNodeOccurrenceUsage', 'Occurrence Usage'),
        ('SysMLNodePartUsage', 'Part Usage'),
        ('SysMLNodeReferenceUsage', 'Reference Usage'),
    ]),
    ('Ports', '#c0a050', [
        ('SysMLNodeConjugatedPortDef', 'Conjugated Port Definition'),
        ('SysMLNodePortDef', 'Port Definition'),
        ('SysMLNodePortUsage', 'Port Usage'),
    ]),
    ('Connections', '#c97b5e', [
        ('SysMLNodeAllocationDef', 'Allocation Definition'),
        ('SysMLNodeConnectionDef', 'Connection Definition'),
        ('SysMLNodeFlowDef', 'Flow Definition'),
        ('SysMLNodeInterfaceDef', 'Interface Definition'),
        ('SysMLNodeAllocationUsage', 'Allocation Usage'),
        ('SysMLNodeBindingUsage', 'Binding Usage'),
        ('SysMLNodeConnectionUsage', 'Connection Usage'),
        ('SysMLNodeFlowUsage', 'Flow Usage'),
        ('SysMLNodeInterfaceUsage', 'Interface Usage'),
        ('SysMLNodeSuccessionUsage', 'Succession Usage'),
    ]),
    ('Behavior', '#a76db5', [
        ('SysMLNodeActionDef', 'Action Definition'),
        ('SysMLNodeCalcDef', 'Calc Definition'),
        ('SysMLNodeStateDef', 'State Definition'),
        ('SysMLNodeActionUsage', 'Action Usage'),
        ('SysMLNodeCalcUsage', 'Calc Usage'),
        ('SysMLNodeStateUsage', 'State Usage'),
    ]),
    ('Requirements', '#b07050', [
        ('SysMLNodeConcernDef', 'Concern Definition'),
        ('SysMLNodeConstraintDef', 'Constraint Definition'),
        ('SysMLNodeRequirementDef', 'Requirement Definition'),
        ('SysMLNodeConcernUsage', 'Concern Usage'),
        ('SysMLNodeConstraintUsage', 'Constraint Usage'),
        ('SysMLNodeRequirementUsage', 'Requirement Usage'),
    ]),
    ('Cases', '#5b8fb9', [
        ('SysMLNodeAnalysisCaseDef', 'Analysis Case Definition'),
        ('SysMLNodeCaseDef', 'Case Definition'),
        ('SysMLNodeUseCaseDef', 'Use Case Definition'),
        ('SysMLNodeVerificationCaseDef', 'Verification Case Definition'),
        ('SysMLNodeAnalysisCaseUsage', 'Analysis Case Usage'),
        ('SysMLNodeCaseUsage', 'Case Usage'),
        ('SysMLNodeUseCaseUsage', 'Use Case Usage'),
        ('SysMLNodeVerificationCaseUsage', 'Verification Case Usage'),
    ]),
    ('Views', '#76b8d9', [
        ('SysMLNodeRenderingDef', 'Rendering Definition'),
        ('SysMLNodeViewDef', 'View Definition'),
        ('SysMLNodeViewpointDef', 'Viewpoint Definition'),
        ('SysMLNodeRenderingUsage', 'Rendering Usage'),
        ('SysMLNodeViewUsage', 'View Usage'),
        ('SysMLNodeViewpointUsage', 'Viewpoint Usage'),
    ]),
    ('Metadata', '#9aa3ad', [
        ('SysMLNodeMetadataDef', 'Metadata Definition'),
        ('SysMLNodeComment', 'Comment'),
        ('SysMLNodeDocumentation', 'Documentation'),
        ('SysMLNodeMetadataUsage', 'Metadata Usage'),
    ]),
]
