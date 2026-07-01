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
    outputs = {OUT_HH: emit_hh(found, version), OUT_REGISTER: emit_register(found)}
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
