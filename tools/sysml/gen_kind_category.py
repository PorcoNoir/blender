#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Generate the SysML kind -> category table (BSML4 / SCRUM-663).

A pure-Python derivation from the node taxonomy in
``node_add_menu_sysml_generated.py`` (itself generated from the pinned sml2c) —
so it needs no sml2c and stays in sync with the node families. The table
classifies each node kind as definition / usage / package / import / alias /
annotation / other, which the local structural checks (sysml_structure.py) use
to validate reference-socket wiring.

  python tools/sysml/gen_kind_category.py           # regenerate
  python tools/sysml/gen_kind_category.py --check    # fail if stale (CI gate)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "scripts" / "startup" / "bl_ui" / "node_add_menu_sysml_generated.py"
OUT = ROOT / "scripts" / "startup" / "bl_ui" / "sysml_kind_category_generated.py"

_PACKAGE = {"Package", "LibraryPackage"}
_ANNOTATION = {"Comment", "Documentation"}


def load_kinds() -> list[str]:
    ns: dict = {}
    exec(compile(SRC.read_text(encoding="utf-8"), str(SRC), "exec"), ns)  # noqa: S102 - trusted generated data
    kinds = {idname
             for _family, _accent, nodes in ns["SYSML_MENU_FAMILIES"]
             for idname, _label in nodes}
    return sorted(kinds)


def categorize(idname: str) -> str:
    name = idname[len("SysMLNode"):] if idname.startswith("SysMLNode") else idname
    if name in _PACKAGE:
        return "package"
    if name in _ANNOTATION:
        return "annotation"
    if name == "Import":
        return "import"
    if name == "Alias":
        return "alias"
    if name.endswith("Def"):
        return "definition"
    if name.endswith("Usage"):
        return "usage"
    return "other"


def render() -> str:
    lines = [
        "# SPDX-FileCopyrightText: 2026 Blender Authors",
        "#",
        "# SPDX-License-Identifier: GPL-2.0-or-later",
        "#",
        "# AUTO-GENERATED - DO NOT EDIT. Regenerate: python tools/sysml/gen_kind_category.py",
        "#",
        "# SysML node kind -> metamodel category, derived from the node taxonomy.",
        "# Used by sysml_structure.py to validate reference-socket wiring.",
        "",
        "KIND_CATEGORY = {",
    ]
    for kind in load_kinds():
        lines.append('    "{}": "{}",'.format(kind, categorize(kind)))
    lines.append("}")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate the SysML kind->category table.")
    ap.add_argument("--check", action="store_true", help="fail if the generated file is stale")
    args = ap.parse_args()

    content = render()
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != content:
            sys.exit(f"{OUT.name} is stale vs the taxonomy. Run gen_kind_category.py and commit.")
        print(f"{OUT.name} up to date")
        return
    OUT.write_text(content, encoding="utf-8")
    print(f"wrote {OUT.name} ({len(load_kinds())} kinds)")


if __name__ == "__main__":
    main()
