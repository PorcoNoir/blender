#!/usr/bin/env python3
"""Blender-SML code generator (BSML1).

SCRUM-438 scope (this file's current stage): probe a *pinned* ``sml2c`` over
``tools/sysml/probes/*.sysml`` and emit
``source/blender/nodes/sysml/sysml_elements.generated.hh`` — the kind table that
drives per-kind node generation in later stories (SCRUM-439/440/441).

This is the Python port of the TS editor's ``tools/regen-element-table.ts`` +
``src/conversion/kindMaps.ts`` (single source of truth for kind mapping).

Usage:
    python tools/sysml/gen_sysml_nodes.py            # uses bundled sml2c
    SML2C=/path/to/sml2c python tools/sysml/gen_sysml_nodes.py
    python tools/sysml/gen_sysml_nodes.py --check    # fail if the .hh is stale (CI regen-diff)

Generated files are checked in but NEVER hand-edited.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROBES_DIR = REPO_ROOT / "tools" / "sysml" / "probes"
OUT_HH = REPO_ROOT / "source" / "blender" / "nodes" / "sysml" / "sysml_elements.generated.hh"
GEN_NODES_DIR = REPO_ROOT / "source" / "blender" / "nodes" / "sysml" / "nodes"
OUT_REGISTER = REPO_ROOT / "source" / "blender" / "nodes" / "sysml" / "sysml_nodes_register.generated.hh"
OUT_SOURCES = REPO_ROOT / "source" / "blender" / "nodes" / "sysml" / "sysml_generated_sources.cmake"
OUT_RNA = REPO_ROOT / "source" / "blender" / "nodes" / "sysml" / "sysml_rna_defs.generated.hh"
OUT_MENU = REPO_ROOT / "scripts" / "startup" / "bl_ui" / "node_add_menu_sysml_generated.py"
OUT_IMPORT_MAP = REPO_ROOT / "source" / "blender" / "nodes" / "sysml" / "sysml_import_kindmap.generated.hh"
OUT_NOTATION = REPO_ROOT / "source" / "blender" / "nodes" / "sysml" / "sysml_notation_keywords.generated.hh"

GEN_BANNER = (
    "/* SPDX-FileCopyrightText: 2026 Blender Authors\n"
    " *\n"
    " * SPDX-License-Identifier: GPL-2.0-or-later */\n"
    "\n"
    "/** \\file\n"
    " * \\ingroup nodes\n"
    " *\n"
    " * AUTO-GENERATED - DO NOT EDIT.\n"
    " * Regenerate: python tools/sysml/gen_sysml_nodes.py\n"
    " */\n"
)

# Floor picked conservatively (mirrors the TS regen tool): abort rather than
# clobber the table with garbage if the probe under-harvests.
KIND_FLOOR = 20

# --- kind maps (ported from src/conversion/kindMaps.ts) --------------------

# sml2c ``defKind`` -> editor-id stem (WITHOUT the _def/_usage suffix).
DEFKIND_TO_STEM = {
    "PartDef": "part",
    "IndividualDef": "part",  # individual def X -> part_def (is_individual flag set on export)
    "AttributeDef": "attribute",
    "PortDef": "port",
    "ItemDef": "item",
    "InterfaceDef": "interface",
    "ConnectionDef": "connection",
    "FlowDef": "flow",
    "AllocationDef": "allocation",
    "SatisfyDef": "satisfy",
    "ActionDef": "action",
    "StateDef": "state",
    "CalcDef": "calc",
    "ConstraintDef": "constraint",
    "RequirementDef": "requirement",
    "ConcernDef": "concern",
    "CaseDef": "case",
    "UseCaseDef": "use_case",
    "ViewDef": "view",
    "ViewpointDef": "viewpoint",
    "RenderingDef": "rendering",
    "MetadataDef": "metadata",
    "OccurrenceDef": "occurrence",
    "EnumDef": "enumeration",
    "DataTypeDef": "data_type",
    "ConjugatedPortDef": "conjugated_port",
    "VerificationCaseDef": "verification_case",
    "AnalysisCaseDef": "analysis_case",
    # Reference usages: sml2c tags a feature end (`end ports : PowerOutPort`) as
    # defKind "End" and an explicit `ref x` as "ReferenceUsage" — both are
    # reference usages. Without these the feature is dropped on import (and the
    # exported `ref x` would not round-trip back to a node).
    "End": "reference",
    "ReferenceUsage": "reference",
}

# Top-level kinds that don't follow Definition/Usage + defKind.
SPECIAL_KIND_TO_EDITOR = {
    "Attribute": "sysml.attribute_usage",
    "Package": "sysml.package",
    "Program": None,        # root envelope — skip
    "QualifiedName": None,  # reference syntax — skip
}

# Editor kinds sml2c doesn't emit as their own AST nodes yet; seeded so they
# appear in the table regardless (containment/flags from overrides below).
NON_ELEMENT_KINDS = [
    "sysml.library_package",
    "sysml.import",
    "sysml.alias",
    "sysml.comment",
    "sysml.documentation",
]

# Capabilities the probe can't exhibit directly (ported from regen-element-table.ts).
# Values: (is_container, can_specialize) — None means "leave to the probe".
CAPABILITY_OVERRIDES = {
    "sysml.attribute_def": (True, False),
    "sysml.enumeration_def": (False, False),
    "sysml.package": (True, False),
    "sysml.library_package": (True, False),
    "sysml.enumeration_usage": (False, None),
    "sysml.binding_usage": (False, None),
    "sysml.succession_usage": (False, None),
    "sysml.constraint_usage": (False, None),
    "sysml.requirement_usage": (False, None),
    "sysml.concern_usage": (False, None),
    "sysml.viewpoint_usage": (False, None),
    "sysml.rendering_usage": (False, None),
    "sysml.metadata_usage": (False, None),
    "sysml.reference_usage": (False, None),
    "sysml.occurrence_usage": (False, None),
    "sysml.comment": (False, False),
    "sysml.documentation": (False, False),
    "sysml.import": (False, False),
    "sysml.alias": (False, False),
}

# Kinds the pinned sml2c cannot emit/parse yet (the compound-keyword case
# family, port conjugation, and defkind-less usages), seeded from the editor
# taxonomy so BSML1 still generates nodes for the full SysML kind set. Flags
# mirror src/sml2/elementTable.generated.ts. (is_container, is_usage, can_specialize)
FALLBACK_KINDS = {
    "sysml.case_def": (True, False, True),
    "sysml.case_usage": (True, True, False),
    "sysml.use_case_def": (True, False, True),
    "sysml.use_case_usage": (True, True, False),
    "sysml.analysis_case_def": (True, False, True),
    "sysml.analysis_case_usage": (True, True, False),
    "sysml.verification_case_def": (True, False, True),
    "sysml.verification_case_usage": (True, True, False),
    "sysml.conjugated_port_def": (True, False, True),
    "sysml.binding_usage": (False, True, False),
    "sysml.succession_usage": (False, True, False),
    "sysml.reference_usage": (False, True, False),
}


def find_sml2c() -> str:
    env = os.environ.get("SML2C")
    if env and Path(env).exists():
        return env
    plat = "windows" if sys.platform.startswith("win") else "macos" if sys.platform == "darwin" else "linux"
    exe = "sml2c.exe" if plat == "windows" else "sml2c"
    cand = REPO_ROOT / "extern" / "sml2c" / "bin" / plat / exe
    if cand.exists():
        return str(cand)
    sys.exit(f"sml2c not found at {cand} (or set $SML2C).")


def harvest(node, found: dict) -> None:
    """Port of regen-element-table.ts harvest(): collect (editor_id -> flags)."""
    if not isinstance(node, dict):
        return
    kind = node.get("kind") if isinstance(node.get("kind"), str) else None
    def_kind = node.get("defKind") if isinstance(node.get("defKind"), str) else None

    editor_id = None
    is_usage = False
    if kind == "Definition" and def_kind:
        stem = DEFKIND_TO_STEM.get(def_kind)
        if stem:
            editor_id = f"sysml.{stem}_def"
    elif kind == "Usage" and def_kind:
        stem = DEFKIND_TO_STEM.get(def_kind)
        if stem:
            editor_id = f"sysml.{stem}_usage"
            is_usage = True
    elif kind and kind in SPECIAL_KIND_TO_EDITOR:
        editor_id = SPECIAL_KIND_TO_EDITOR[kind]
        if kind == "Attribute":
            is_usage = True

    if editor_id:
        has_members = isinstance(node.get("members"), list) and len(node["members"]) > 0
        has_spec = isinstance(node.get("specializes"), list) and len(node["specializes"]) > 0
        e = found.get(editor_id)
        if e:
            e["is_container"] = e["is_container"] or has_members
            e["can_specialize"] = e["can_specialize"] or has_spec
        else:
            found[editor_id] = {
                "is_container": has_members,
                "is_usage": is_usage,
                "can_specialize": has_spec,
                "source": "sml2c",
            }

    for child in node.get("members", []) if isinstance(node.get("members"), list) else []:
        harvest(child, found)
    body = node.get("body")
    if isinstance(body, list):
        for child in body:
            harvest(child, found)
    elif isinstance(body, dict):
        harvest(body, found)


def apply_overrides(found: dict) -> None:
    for eid in NON_ELEMENT_KINDS:
        found.setdefault(
            eid, {"is_container": False, "is_usage": False, "can_specialize": False, "source": "fallback"})
    for eid, (cont, spec) in CAPABILITY_OVERRIDES.items():
        if eid in found:
            if cont is not None:
                found[eid]["is_container"] = cont
            if spec is not None:
                found[eid]["can_specialize"] = spec
    # Seed kinds the pinned sml2c can't produce (harvested entries win).
    for eid, (cont, usage, spec) in FALLBACK_KINDS.items():
        found.setdefault(
            eid, {"is_container": cont, "is_usage": usage, "can_specialize": spec, "source": "fallback"})
    # BSML3 (SCRUM-496): every SysML v2 definition can own nested features (a
    # part def nests parts, an enumeration def its literals, an item def its
    # attributes, ...). Our import wires all containment through the `members`
    # socket, so a def without one drops its nested features on import — and they
    # can't round-trip. Force every `_def` to be a container; this supersedes any
    # override above that marked a definition non-container (e.g. enumeration_def).
    for eid, entry in found.items():
        if eid.endswith("_def"):
            entry["is_container"] = True


def node_idname(editor_id: str) -> str:
    """sysml.part_def -> SysMLNodePartDef ; sysml.package -> SysMLNodePackage."""
    stem = editor_id[len("sysml."):]
    return "SysMLNode" + "".join(w.capitalize() for w in stem.split("_"))


def ui_name(editor_id: str) -> str:
    stem = editor_id[len("sysml."):]
    parts = stem.split("_")
    subst = {"def": "Definition", "usage": "Usage"}
    return " ".join(subst.get(p, p.capitalize()) for p in parts)


# Connector families and their end sockets (ports from nodes/sysml.ts):
CONNECTOR_CONNECT = {"connection", "interface", "allocation"}  # connect ... to
CONNECTOR_FLOW = {"flow"}                                      # from ... to
SUBJECT_KINDS = {"requirement"}                               # `subject` wire
# Definitions are specializable and carry a `specializes` socket, EXCEPT these:
# enum defs aren't specializable; conjugated ports wire an `original` instead.
NO_SPECIALIZE_DEFS = {"enumeration", "conjugated_port"}

# editor-id -> canonical SysML surface keyword, ported from notation.ts
# NOTATION_KEYWORDS (BSML3 / SCRUM-498). Kinds not listed fall back to a keyword
# derived from the stem (see notation_keyword). Used by export_notation.cc.
NOTATION_KEYWORDS = {
    "sysml.package": "package", "sysml.library_package": "library package",
    "sysml.part_def": "part def", "sysml.attribute_def": "attribute def",
    "sysml.enumeration_def": "enum def", "sysml.port_def": "port def",
    "sysml.conjugated_port_def": "port def", "sysml.interface_def": "interface def",
    "sysml.connection_def": "connection def", "sysml.allocation_def": "allocation def",
    "sysml.flow_def": "flow def", "sysml.item_def": "item def",
    "sysml.occurrence_def": "occurrence def", "sysml.constraint_def": "constraint def",
    "sysml.metadata_def": "metadata def", "sysml.requirement_def": "requirement def",
    "sysml.concern_def": "concern def", "sysml.action_def": "action def",
    "sysml.state_def": "state def", "sysml.calc_def": "calc def",
    "sysml.view_def": "view def", "sysml.viewpoint_def": "viewpoint def",
    "sysml.rendering_def": "rendering def", "sysml.case_def": "case def",
    "sysml.analysis_case_def": "analysis case def",
    "sysml.verification_case_def": "verification case def",
    "sysml.use_case_def": "use case def", "sysml.part_usage": "part",
    "sysml.attribute_usage": "attribute", "sysml.enumeration_usage": "enum",
    "sysml.port_usage": "port", "sysml.item_usage": "item",
    "sysml.connection_usage": "connection", "sysml.interface_usage": "interface",
    "sysml.allocation_usage": "allocation", "sysml.satisfy_def": "satisfy",
    "sysml.satisfy_usage": "satisfy", "sysml.flow_usage": "flow",
    "sysml.binding_usage": "bind", "sysml.succession_usage": "succession",
    "sysml.action_usage": "action", "sysml.state_usage": "state",
    "sysml.calc_usage": "calc", "sysml.constraint_usage": "constraint",
    "sysml.requirement_usage": "requirement", "sysml.concern_usage": "concern",
    "sysml.case_usage": "case", "sysml.analysis_case_usage": "analysis case",
    "sysml.verification_case_usage": "verification case",
    "sysml.use_case_usage": "use case", "sysml.view_usage": "view",
    "sysml.viewpoint_usage": "viewpoint", "sysml.rendering_usage": "rendering",
    "sysml.metadata_usage": "metadata", "sysml.reference_usage": "ref",
    "sysml.occurrence_usage": "occurrence",
    "sysml.event_occurrence_usage": "event occurrence",
    "sysml.snapshot_usage": "snapshot", "sysml.timeslice_usage": "timeslice",
    "sysml.import": "import", "sysml.alias": "alias",
    "sysml.comment": "comment", "sysml.documentation": "doc",
}


def notation_keyword(eid: str) -> str:
    if eid in NOTATION_KEYWORDS:
        return NOTATION_KEYWORDS[eid]
    stem = eid[len("sysml."):]
    if stem.endswith("_def"):
        return stem[:-4].replace("_", " ") + " def"
    if stem.endswith("_usage"):
        return stem[:-6].replace("_", " ")
    return stem.replace("_", " ")

# Add-menu families + accent colours (ported from the editor's ACCENT map in
# src/nodes/sysml.ts). Every kind's base stem maps to one family.
FAMILY_ACCENT = {
    "Packages": "#7e9ac0", "Structure": "#a99dd4", "Ports": "#c0a050",
    "Connections": "#c97b5e", "Behavior": "#a76db5", "Requirements": "#b07050",
    "Cases": "#5b8fb9", "Views": "#76b8d9", "Metadata": "#9aa3ad",
}
FAMILY_ORDER = ["Packages", "Structure", "Ports", "Connections", "Behavior",
                "Requirements", "Cases", "Views", "Metadata"]
FAMILY_OF = {
    "package": "Packages", "library_package": "Packages", "import": "Packages", "alias": "Packages",
    "part": "Structure", "item": "Structure", "attribute": "Structure", "occurrence": "Structure",
    "reference": "Structure", "enumeration": "Structure", "data_type": "Structure",
    "port": "Ports", "conjugated_port": "Ports",
    "connection": "Connections", "interface": "Connections", "flow": "Connections",
    "allocation": "Connections", "binding": "Connections", "succession": "Connections",
    "action": "Behavior", "state": "Behavior", "calc": "Behavior",
    "requirement": "Requirements", "constraint": "Requirements", "concern": "Requirements", "satisfy": "Requirements",
    "case": "Cases", "use_case": "Cases", "verification_case": "Cases", "analysis_case": "Cases",
    "view": "Views", "viewpoint": "Views", "rendering": "Views",
    "metadata": "Metadata", "comment": "Metadata", "documentation": "Metadata",
}


def family_of(editor_id: str) -> str:
    return FAMILY_OF.get(kind_base(editor_id), "Metadata")


def accent_rgb(family: str):
    h = FAMILY_ACCENT[family].lstrip("#")
    return tuple(round(int(h[i:i + 2], 16) / 255.0, 4) for i in (0, 2, 4))


def kind_base(editor_id: str) -> str:
    """`sysml.part_def` / `sysml.part_usage` -> `part` (family stem)."""
    stem = editor_id[len("sysml."):]
    for suffix in ("_def", "_usage"):
        if stem.endswith(suffix):
            return stem[: -len(suffix)]
    return stem


def socket_rules(editor_id: str, entry: dict):
    """Relationship input sockets for a kind, from its flags + family. Every
    node also has the `self` identity output (added by the template).

    Ordering is fixed (containment -> typing -> connector ends -> specialization
    -> subject) so the generated PartDef/PartUsage/ConnectionUsage match the
    hand-written BSML0 nodes byte-for-byte in socket order."""
    base = kind_base(editor_id)
    is_connector = base in CONNECTOR_CONNECT or base in CONNECTOR_FLOW
    socks = []
    if entry["is_container"]:
        socks.append(("SOCK_IN", "members", "Members"))
    if entry["is_usage"]:
        socks.append(("SOCK_IN", "of", "Type"))
    if entry["is_usage"] and base in CONNECTOR_CONNECT:
        socks.append(("SOCK_IN", "connect", "Connect"))
        socks.append(("SOCK_IN", "to", "To"))
    elif entry["is_usage"] and base in CONNECTOR_FLOW:
        socks.append(("SOCK_IN", "from", "From"))
        socks.append(("SOCK_IN", "to", "To"))
    if editor_id.endswith("_def") and base not in NO_SPECIALIZE_DEFS:
        socks.append(("SOCK_IN", "specializes", "Specializes"))
    elif editor_id.endswith("_usage") and not is_connector:
        socks.append(("SOCK_IN", "redefines", "Redefines"))
    if base in SUBJECT_KINDS:
        socks.append(("SOCK_IN", "subject", "Subject"))
    return socks


def emit_node_cc(editor_id: str, entry: dict) -> str:
    stem = editor_id[len("sysml."):]
    init = f"sysml_{stem}_init"
    reg = f"register_node_type_sysml_{stem}"
    idname = node_idname(editor_id)
    label = ui_name(editor_id)
    add = 'bke::node_add_socket(*ntree, *node, {}, "NodeSocketSysMLElement", "{}", "{}");'
    lines = [
        GEN_BANNER,
        '#include "BKE_node.hh"',
        "",
        '#include "DNA_node_types.h"',
        "",
        '#include "node_sysml_util.hh"',
        "",
        "namespace blender::nodes {",
        "",
        f"static void {init}(bNodeTree *ntree, bNode *node)",
        "{",
        "  sysml_node_storage_init(node);",
        "  " + add.format("SOCK_OUT", "self", "Self"),
    ]
    for d, ident, name in socket_rules(editor_id, entry):
        lines.append("  " + add.format(d, ident, name))
    r, g, b = accent_rgb(family_of(editor_id))
    lines += [
        f"  node->color[0] = {r}f;",
        f"  node->color[1] = {g}f;",
        f"  node->color[2] = {b}f;",
        "  node->flag |= NODE_CUSTOM_COLOR;  /* family accent */",
    ]
    lines += [
        "}",
        "",
        f"void {reg}()",
        "{",
        "  static bke::bNodeType ntype;",
        "",
        f'  sysml_node_type_base(&ntype, "{idname}"_ustr);',
        f'  ntype.ui_name = "{label}";',
        f'  ntype.ui_description = "SysML v2 {label.lower()}";',
        "  ntype.nclass = NODE_CLASS_INPUT;",
        f"  ntype.initfunc = {init};",
        "  sysml_node_storage_register(ntype);",
        "",
        "  bke::node_register_type(ntype);",
        "}",
        "",
        "}  // namespace blender::nodes",
        "",
    ]
    return "\n".join(lines)


def emit_rna_defs(found: dict) -> str:
    """RNA storage-defs block: applies the shared NodeSysMLElement RNA to every
    element node. #included inside the RNA node-registration block in
    rna_nodetree.cc, where `define` and `def_sysml_element` are in scope."""
    lines = [
        "/* SPDX-FileCopyrightText: 2026 Blender Authors",
        " *",
        " * SPDX-License-Identifier: GPL-2.0-or-later */",
        "",
        "/* AUTO-GENERATED - DO NOT EDIT. Regenerate: python tools/sysml/gen_sysml_nodes.py */",
        "",
    ]
    lines += [f'define("NodeInternal", "{node_idname(eid)}", def_sysml_element);' for eid in sorted(found)]
    lines.append("")
    return "\n".join(lines)


def emit_import_kindmap(found: dict) -> str:
    """sml2c AST (kind, defKind) -> SysML node idname, for the importer
    (SCRUM-447). Only maps kinds that have a registered node."""
    def_rows, usage_rows = [], []
    for defkind, stem in sorted(DEFKIND_TO_STEM.items()):
        if f"sysml.{stem}_def" in found:
            def_rows.append((defkind, node_idname(f"sysml.{stem}_def")))
        if f"sysml.{stem}_usage" in found:
            usage_rows.append((defkind, node_idname(f"sysml.{stem}_usage")))
    lines = [
        GEN_BANNER,
        "#pragma once",
        "",
        "#include <string_view>",
        "",
        "namespace blender::nodes::sysml {",
        "",
        "/* sml2c AST (kind, defKind) -> SysML node idname; empty when unmapped. */",
        "inline const char *sysml_import_idname(std::string_view kind, std::string_view def_kind)",
        "{",
        '  if (kind == "Definition") {',
    ]
    lines += [f'    if (def_kind == "{dk}") return "{idn}";' for dk, idn in def_rows]
    lines += ["  }", '  if (kind == "Usage") {']
    lines += [f'    if (def_kind == "{dk}") return "{idn}";' for dk, idn in usage_rows]
    lines += ["  }"]
    for k, eid in SPECIAL_KIND_TO_EDITOR.items():
        if eid and eid in found:
            lines.append(f'  if (kind == "{k}") return "{node_idname(eid)}";')
    lines += ['  return "";', "}", "", "}  // namespace blender::nodes::sysml", ""]
    return "\n".join(lines)


def emit_notation_keywords(found: dict) -> str:
    """SysML node idname -> canonical notation keyword, for export_notation.cc
    (SCRUM-498). Ports notation.ts's NOTATION_KEYWORDS onto our node idnames."""
    rows = [(node_idname(eid), notation_keyword(eid)) for eid in sorted(found)]
    lines = [
        GEN_BANNER,
        "#pragma once",
        "",
        "#include <string_view>",
        "",
        "namespace blender::nodes::sysml {",
        "",
        "/* SysML node idname -> canonical notation keyword; empty when unknown. */",
        "inline const char *sysml_notation_keyword(std::string_view idname)",
        "{",
    ]
    lines += [f'  if (idname == "{idn}") return "{kw}";' for idn, kw in rows]
    lines += ['  return "";', "}", "", "}  // namespace blender::nodes::sysml", ""]
    return "\n".join(lines)


def emit_menu_module(found: dict) -> str:
    """Add-menu families as Python data for node_add_menu_sysml.py: each family
    lists its (idname, ui_name) with defs before usages."""
    fam: dict = {}
    for eid in sorted(found):
        fam.setdefault(family_of(eid), []).append((node_idname(eid), ui_name(eid), eid))
    lines = [
        "# SPDX-FileCopyrightText: 2026 Blender Authors",
        "#",
        "# SPDX-License-Identifier: GPL-2.0-or-later",
        "#",
        "# AUTO-GENERATED - DO NOT EDIT. Regenerate: python tools/sysml/gen_sysml_nodes.py",
        "#",
        "# SysML add-menu families. Each entry: (family_label, accent_hex,",
        "# [(node_idname, ui_name), ...]). Consumed by node_add_menu_sysml.py.",
        "",
        "SYSML_MENU_FAMILIES = [",
    ]
    for f in FAMILY_ORDER:
        entries = sorted(fam.get(f, []), key=lambda t: (not t[2].endswith("_def"), t[0]))
        if not entries:
            continue
        lines.append(f"    ({f!r}, {FAMILY_ACCENT[f]!r}, [")
        lines += [f"        ({idname!r}, {label!r})," for idname, label, _ in entries]
        lines.append("    ]),")
    lines += ["]", ""]
    return "\n".join(lines)


def emit_sources_cmake(found: dict) -> str:
    lines = [
        "# SPDX-FileCopyrightText: 2026 Blender Authors",
        "#",
        "# SPDX-License-Identifier: GPL-2.0-or-later",
        "#",
        "# AUTO-GENERATED - DO NOT EDIT. Regenerate: python tools/sysml/gen_sysml_nodes.py",
        "",
        "set(SYSML_GENERATED_SRC",
    ]
    lines += [f"  nodes/node_sysml_{eid[len('sysml.'):]}.cc" for eid in sorted(found)]
    lines += ["  sysml_elements.generated.hh", "  sysml_nodes_register.generated.hh", ")", ""]
    return "\n".join(lines)


def emit_register(found: dict) -> str:
    stems = [eid[len("sysml."):] for eid in sorted(found)]
    lines = [GEN_BANNER, "#pragma once", "", "namespace blender::nodes {", ""]
    lines += [f"void register_node_type_sysml_{s}();" for s in stems]
    lines += ["", "inline void register_generated_sysml_nodes()", "{"]
    lines += [f"  register_node_type_sysml_{s}();" for s in stems]
    lines += ["}", "", "}  // namespace blender::nodes", ""]
    return "\n".join(lines)


def sml2c_version(sml2c: str) -> str:
    try:
        return subprocess.run([sml2c, "--version"], capture_output=True, text=True).stdout.strip() or "unknown"
    except OSError:
        return "unknown"


def emit_hh(found: dict, version: str) -> str:
    b = ["true", "false"]
    harvested = sum(1 for e in found.values() if e.get("source") == "sml2c")
    fallback = len(found) - harvested
    lines = [
        "/* SPDX-FileCopyrightText: 2026 Blender Authors",
        " *",
        " * SPDX-License-Identifier: GPL-2.0-or-later */",
        "",
        "/** \\file",
        " * \\ingroup nodes",
        " *",
        " * AUTO-GENERATED - DO NOT EDIT.",
        " * Regenerate: python tools/sysml/gen_sysml_nodes.py",
        f" * sml2c version:  {version}",
        f" * Element kinds:  {len(found)}  ({harvested} harvested from sml2c, {fallback} fallback-seeded)",
        " *",
        " * X-macro table of SysML element kinds driving node registration. Each row:",
        " *   X(editor_id, node_idname, ui_name, is_container, is_usage, can_specialize)",
        " */",
        "",
        "#pragma once",
        "",
        "/* clang-format off */",
        "#define SYSML_ELEMENT_KINDS \\",
    ]
    for eid in sorted(found):
        e = found[eid]
        lines.append(
            f'  X("{eid}", "{node_idname(eid)}", "{ui_name(eid)}", '
            f'{b[not e["is_container"]]}, {b[not e["is_usage"]]}, {b[not e["can_specialize"]]}) \\'
        )
    lines[-1] = lines[-1].rstrip(" \\")  # drop trailing continuation
    lines += ["/* clang-format on */", ""]
    return "\n".join(lines)


def main() -> None:
    check = "--check" in sys.argv
    sml2c = find_sml2c()
    version = sml2c_version(sml2c)
    print(f"sml2c: {sml2c} ({version})", file=sys.stderr)

    probes = sorted(PROBES_DIR.glob("*.sysml"))
    if not probes:
        sys.exit(f"No probes under {PROBES_DIR}.")

    found: dict = {}
    for probe in probes:
        print(f"  -> {probe.name}", file=sys.stderr)
        out = subprocess.run([sml2c, "--emit-json", str(probe)], capture_output=True, text=True)
        if out.returncode != 0:
            print(f"    skipped (sml2c rejected): {out.stderr.splitlines()[:1]}", file=sys.stderr)
            continue
        try:
            harvest(json.loads(out.stdout), found)
        except json.JSONDecodeError as e:
            print(f"    skipped (invalid JSON): {e}", file=sys.stderr)

    apply_overrides(found)
    if len(found) < KIND_FLOOR:
        sys.exit(f"Only {len(found)} kinds harvested (< floor {KIND_FLOOR}); aborting.")

    # Full set of generated outputs (path -> text): the kind table, the
    # per-kind node source, and the registration aggregator.
    outputs = {OUT_HH: emit_hh(found, version), OUT_REGISTER: emit_register(found),
               OUT_SOURCES: emit_sources_cmake(found), OUT_RNA: emit_rna_defs(found),
               OUT_MENU: emit_menu_module(found), OUT_IMPORT_MAP: emit_import_kindmap(found),
               OUT_NOTATION: emit_notation_keywords(found)}
    for eid in sorted(found):
        outputs[GEN_NODES_DIR / f"node_sysml_{eid[len('sysml.'):]}.cc"] = emit_node_cc(eid, found[eid])

    if check:
        stale = [p for p, t in outputs.items()
                 if (p.read_text(encoding="utf-8") if p.exists() else "") != t]
        if stale:
            sys.exit("Stale generated files vs the pinned sml2c: "
                     + ", ".join(p.name for p in stale) + ". Run gen_sysml_nodes.py and commit.")
        print(f"All {len(outputs)} generated files up to date ({len(found)} kinds).", file=sys.stderr)
        return

    GEN_NODES_DIR.mkdir(parents=True, exist_ok=True)
    for p, t in outputs.items():
        p.write_text(t, encoding="utf-8")
    print(f"Wrote {len(outputs)} files: {OUT_HH.name}, {OUT_REGISTER.name}, and "
          f"{len(found)} node_sysml_*.cc.", file=sys.stderr)


if __name__ == "__main__":
    main()
