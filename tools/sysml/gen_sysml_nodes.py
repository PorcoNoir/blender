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

    text = emit_hh(found, version)
    if check:
        current = OUT_HH.read_text(encoding="utf-8") if OUT_HH.exists() else ""
        if current != text:
            sys.exit(f"{OUT_HH.name} is stale vs the pinned sml2c. Run gen_sysml_nodes.py and commit.")
        print(f"{OUT_HH.name} is up to date ({len(found)} kinds).", file=sys.stderr)
        return
    OUT_HH.write_text(text, encoding="utf-8")
    print(f"Wrote {OUT_HH.relative_to(REPO_ROOT)} ({len(found)} kinds).", file=sys.stderr)


if __name__ == "__main__":
    main()
