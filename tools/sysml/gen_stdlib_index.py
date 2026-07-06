#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Generate the SysML standard-library index (BSML5 / SCRUM-675).

A catalog of the standard-library packages + types that resolve for Blender-SML
models, from two sources:

* **builtin** — packages the pinned sml2c already resolves out of the box
  (ScalarValues, Quantities, ISQ, SI). These are compiled into sml2c, not files,
  so bundling them would collide (E0203); they are curated here (each entry
  verified to resolve) rather than shipped.
* **bundled** — the domain packages we ship in `extern/sysml-stdlib` (Geometry,
  Time), scanned from the `.sysml` sources.

The index drives the in-editor library browser (SCRUM-676). Pure-Python (scans
text, no sml2c), so it is a token-free regen-diff gate.

  python tools/sysml/gen_stdlib_index.py          # regenerate
  python tools/sysml/gen_stdlib_index.py --check   # fail if stale (CI gate)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STDLIB_DIR = ROOT / "extern" / "sysml-stdlib"
OUT = ROOT / "scripts" / "startup" / "bl_ui" / "sysml_stdlib_index_generated.py"

# Packages sml2c resolves built-in (verified: each type resolves under
# --stdlib-path). Curated because they are compiled into sml2c, not files.
BUILTIN = {
    "ScalarValues": ["Boolean", "Integer", "Natural", "Number", "Real", "String"],
    "Quantities": ["AngleValue", "DurationValue", "LengthValue", "MassValue",
                   "ScalarQuantityValue"],
    "ISQ": ["DurationValue", "ForceValue", "LengthValue", "MassValue",
            "SpeedValue", "TemperatureValue"],
    "SI": ["Unit", "kilogram", "metre", "second"],
}

_PACKAGE_RE = re.compile(r"^\s*(?:standard library\s+)?package\s+(\w+)", re.MULTILINE)
_DEF_RE = re.compile(r"^\s*(?:abstract\s+)?\w+\s+def\s+(\w+)", re.MULTILINE)


def _scan_bundled():
    """{package: [types]} scanned from the shipped `.sysml` sources."""
    packages = {}
    for path in sorted(STDLIB_DIR.rglob("*.sysml")):
        text = path.read_text(encoding="utf-8")
        pkg = _PACKAGE_RE.search(text)
        if not pkg:
            continue
        types = sorted(set(_DEF_RE.findall(text)))
        packages[pkg.group(1)] = types
    return packages


def _entries():
    entries = []
    for pkg, types in sorted(BUILTIN.items()):
        entries.append((pkg, "builtin", sorted(types)))
    for pkg, types in sorted(_scan_bundled().items()):
        entries.append((pkg, "bundled", types))
    return entries


def render():
    lines = [
        "# SPDX-FileCopyrightText: 2026 Blender Authors",
        "#",
        "# SPDX-License-Identifier: GPL-2.0-or-later",
        "#",
        "# AUTO-GENERATED - DO NOT EDIT. Regenerate: python tools/sysml/gen_stdlib_index.py",
        "#",
        "# Catalog of resolvable SysML standard-library packages + types, by source",
        "# (builtin = compiled into sml2c; bundled = shipped in extern/sysml-stdlib).",
        "# Consumed by the in-editor library browser (sysml_library.py).",
        "",
        "STDLIB_INDEX = [",
    ]
    for pkg, source, types in _entries():
        joined = ", ".join('"{}"'.format(t) for t in types)
        lines.append('    {{"package": "{}", "source": "{}", "types": [{}]}},'.format(
            pkg, source, joined))
    lines.append("]")
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description="Generate the SysML stdlib index.")
    ap.add_argument("--check", action="store_true", help="fail if the generated file is stale")
    args = ap.parse_args()

    content = render()
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != content:
            sys.exit(f"{OUT.name} is stale vs the bundle/builtin catalog. "
                     f"Run gen_stdlib_index.py and commit.")
        print(f"{OUT.name} up to date")
        return
    OUT.write_text(content, encoding="utf-8")
    n_pkg = len(_entries())
    print(f"wrote {OUT.name} ({n_pkg} packages)")


if __name__ == "__main__":
    main()
