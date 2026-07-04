#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later
"""Generate the SysML shape -> Blender primitive resolver (Geometry Binding A /
SCRUM-625).

Reads the bundled Geometry `ShapeItems` library (extern/sysml-stdlib), resolves
every shape `item def` to its base solid via the library's specialization
hierarchy, validates that the mapped attributes exist, and emits a byte-stable
Python resolver consumed by the geometry materialize operator.

Run:  python tools/sysml/gen_geometry_shapes.py [--check]
"""

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SHAPEITEMS = REPO_ROOT / "extern" / "sysml-stdlib" / "Geometry" / "ShapeItems.sysml"
OUT = REPO_ROOT / "scripts" / "startup" / "bl_ui" / "sysml_geometry_shapes_generated.py"

# Curated base-shape -> Blender primitive mapping. `params` bind bpy op kwargs to
# shape attribute names; `dimensions` (or None) names the attributes used to set
# object.dimensions after creating the primitive (for the box family, whose base
# cube is unit-sized). Subtypes inherit their base's entry via specialization.
SHAPE_MAP = {
    "Cuboid": {
        "op": "primitive_cube_add",
        "params": {},
        "dimensions": ["length", "width", "height"],
    },
    "Sphere": {
        "op": "primitive_uv_sphere_add",
        "params": {"radius": "radius"},
        "dimensions": None,
    },
    "Cylinder": {
        "op": "primitive_cylinder_add",
        "params": {"radius": "radius", "depth": "height"},
        "dimensions": None,
    },
    "Cone": {
        "op": "primitive_cone_add",
        "params": {"radius1": "radius", "depth": "height"},
        "dimensions": None,
    },
    "Torus": {
        "op": "primitive_torus_add",
        "params": {"major_radius": "majorRadius", "minor_radius": "minorRadius"},
        "dimensions": None,
    },
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


def harvest(ast) -> dict:
    """name -> {spec: [...], attrs: [...]} for every shape ItemDef."""
    defs: dict = {}

    def walk(node):
        if isinstance(node, dict):
            if node.get("kind") == "Definition" and node.get("defKind") == "ItemDef" and node.get("name"):
                spec = [q.get("resolvedTo") for q in node.get("specializes", []) if q.get("resolvedTo")]
                attrs = [m.get("name") for m in node.get("members", [])
                         if isinstance(m, dict) and m.get("name")]
                defs[node["name"]] = {"spec": spec, "attrs": attrs}
            for key in ("members", "body"):
                val = node.get(key)
                if isinstance(val, list):
                    for child in val:
                        walk(child)
                elif isinstance(val, dict):
                    walk(val)

    walk(ast)
    return defs


def base_of(name, defs):
    """Nearest SHAPE_MAP base reached by walking specialization; None if none."""
    seen, cur = set(), name
    while cur and cur not in seen:
        if cur in SHAPE_MAP:
            return cur
        seen.add(cur)
        spec = defs.get(cur, {}).get("spec", [])
        cur = spec[0] if spec else None
    return None


def attrs_closure(name, defs):
    """All attribute names on `name` including inherited ones."""
    out, seen, cur = [], set(), name
    while cur and cur not in seen:
        seen.add(cur)
        out += defs.get(cur, {}).get("attrs", [])
        spec = defs.get(cur, {}).get("spec", [])
        cur = spec[0] if spec else None
    return out


def build_resolver(defs) -> dict:
    resolver: dict = {}
    for name in sorted(defs):
        base = base_of(name, defs)
        if base is None:
            continue  # abstract Shape or an unmapped kind
        entry = SHAPE_MAP[base]
        have = set(attrs_closure(name, defs))
        needed = set(entry["params"].values()) | set(entry["dimensions"] or [])
        missing = needed - have
        if missing:
            sys.exit(f"shape {name} (base {base}) is missing attributes {sorted(missing)} "
                     f"in the bundled library")
        resolver[name] = {
            "op": entry["op"],
            "params": dict(entry["params"]),
            "dimensions": list(entry["dimensions"]) if entry["dimensions"] else None,
        }
    return resolver


def emit(resolver) -> str:
    lines = [
        "# SPDX-FileCopyrightText: 2026 Blender Authors",
        "#",
        "# SPDX-License-Identifier: GPL-2.0-or-later",
        "#",
        "# AUTO-GENERATED - DO NOT EDIT. Regenerate: python tools/sysml/gen_geometry_shapes.py",
        "#",
        "# SysML v2 Geometry shape (item def name) -> the Blender mesh primitive that",
        "# materializes it (Geometry Binding A / SCRUM-625).",
        "#   op         : bpy.ops.mesh.<op> that creates the primitive",
        "#   params     : {op_kwarg: shape_attribute} feeding the op from shape attributes",
        "#   dimensions : shape attributes used to set object.dimensions afterwards, or None",
        "",
        "SHAPE_RESOLVER = {",
    ]
    for name in sorted(resolver):
        e = resolver[name]
        params = "{" + ", ".join(f"{k!r}: {v!r}" for k, v in e["params"].items()) + "}"
        lines.append(f"    {name!r}: {{")
        lines.append(f"        \"op\": {e['op']!r},")
        lines.append(f"        \"params\": {params},")
        lines.append(f"        \"dimensions\": {e['dimensions']!r},")
        lines.append("    },")
    lines += ["}", ""]
    return "\n".join(lines)


def main() -> None:
    proc = subprocess.run([find_sml2c(), "--emit-json", str(SHAPEITEMS)],
                          capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f"sml2c failed on {SHAPEITEMS}:\n{proc.stderr}")
    resolver = build_resolver(harvest(json.loads(proc.stdout)))
    if not resolver:
        sys.exit("no shapes resolved from the bundled ShapeItems library")
    text = emit(resolver)

    if "--check" in sys.argv:
        current = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if current != text:
            sys.exit(f"{OUT} is stale; run: python tools/sysml/gen_geometry_shapes.py")
        print("geometry shape resolver up to date")
        return

    OUT.write_text(text, encoding="utf-8")
    print(f"Wrote {OUT.name}: {len(resolver)} shapes")


if __name__ == "__main__":
    main()
