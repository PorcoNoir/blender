# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Bundled Geometry standard library (Geometry Binding A / SCRUM-624).

Verifies that the minimal SysML standard library shipped next to the executable
(`sysml-stdlib/Geometry/{ShapeItems,SpatialItems}.sysml`) is present, parseable,
and actually resolves geometry types: a part that specializes `SpatialItem` and
types its `shape` as a `Cuboid` compiles with those references resolved when the
bundle is passed to sml2c as `--stdlib-path` (and, as a control, `Cuboid` does
NOT resolve without it). Also smoke-tests that such a model imports.

Skips where the sml2c binary is unavailable.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

import bpy

TREE_IDNAME = "SysMLNodeTree"

MODEL = """package GeoTest {
    private import ShapeItems::*;
    private import SpatialItems::*;
    part def Widget :> SpatialItem {
        item :>> shape : Cuboid {
            :>> length = 10;
            :>> width = 20;
            :>> height = 30;
        }
    }
}
"""


def sml2c_binary():
    env = os.environ.get("SML2C")
    if env and os.path.exists(env):
        return env
    program_dir = os.path.dirname(bpy.app.binary_path or "")
    for name in ("sml2c.exe", "sml2c"):
        candidate = os.path.join(program_dir, name)
        if os.path.exists(candidate):
            return candidate
    return None


def stdlib_dir():
    env = os.environ.get("SML2C_STDLIB")
    if env and os.path.isdir(env):
        return env
    return os.path.join(os.path.dirname(bpy.app.binary_path or ""), "sysml-stdlib")


def resolved(ast, name, key):
    """resolvedTo values of `key` (specializes/types) on the element `name`."""
    found = []

    def walk(node):
        if isinstance(node, dict):
            if node.get("name") == name:
                found.extend(q.get("resolvedTo") for q in node.get(key, []))
            for k in ("members", "body"):
                v = node.get(k)
                if isinstance(v, list):
                    for c in v:
                        walk(c)
                elif isinstance(v, dict):
                    walk(v)

    walk(ast)
    return found


@unittest.skipUnless(sml2c_binary(), "sml2c binary not available next to blender")
class SysMLGeometryStdlibTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._dir = tempfile.mkdtemp()
        cls._model = os.path.join(cls._dir, "geo.sysml")
        with open(cls._model, "w", encoding="utf-8") as f:
            f.write(MODEL)

    def test_bundle_present(self):
        d = stdlib_dir()
        self.assertTrue(os.path.isdir(d), f"bundled stdlib dir missing: {d}")
        for rel in ("Geometry/ShapeItems.sysml", "Geometry/SpatialItems.sysml"):
            self.assertTrue(os.path.exists(os.path.join(d, rel)), f"missing {rel}")

    def test_bundle_parses(self):
        sml2c = sml2c_binary()
        for rel in ("Geometry/ShapeItems.sysml", "Geometry/SpatialItems.sysml"):
            path = os.path.join(stdlib_dir(), rel)
            proc = subprocess.run([sml2c, "--parse-only", path],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0,
                             f"{rel} is not parseable by the pinned sml2c:\n{proc.stderr}")

    def test_geometry_types_resolve_with_bundle(self):
        sml2c = sml2c_binary()
        with_lib = subprocess.run(
            [sml2c, "--stdlib-path", stdlib_dir(), "--emit-json", self._model],
            capture_output=True, text=True)
        self.assertEqual(with_lib.returncode, 0, with_lib.stderr)
        ast = json.loads(with_lib.stdout)
        self.assertIn("SpatialItem", resolved(ast, "Widget", "specializes"),
                      "Widget :> SpatialItem did not resolve against the bundle")
        self.assertIn("Cuboid", resolved(ast, "shape", "types"),
                      "shape : Cuboid did not resolve against the bundle")

    def test_control_types_unresolved_without_bundle(self):
        # Without the bundle, the shape type does not resolve — proving the
        # bundle (not something else) is what resolves it.
        sml2c = sml2c_binary()
        without = subprocess.run([sml2c, "--emit-json", self._model],
                                 capture_output=True, text=True)
        self.assertEqual(without.returncode, 0)
        ast = json.loads(without.stdout)
        self.assertNotIn("Cuboid", resolved(ast, "shape", "types"),
                         "Cuboid should be unresolved without the bundled library")

    def test_geometry_model_imports(self):
        before = set(bpy.data.node_groups.keys())
        self.assertEqual(bpy.ops.node.sysml_import(filepath=self._model), {'FINISHED'})
        new = [ng for key, ng in bpy.data.node_groups.items()
               if key not in before and ng.bl_idname == TREE_IDNAME]
        self.assertEqual(len(new), 1)
        names = {n.element_name: n.bl_idname for n in new[0].nodes}
        self.assertEqual(names.get("Widget"), "SysMLNodePartDef")
        self.assertIn("shape", names)


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
