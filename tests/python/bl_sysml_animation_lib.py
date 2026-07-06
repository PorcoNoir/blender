# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Bundled Occurrences / Time standard library (Animation Binding A / SCRUM-644).

Verifies the minimal temporal library shipped next to the executable
(`sysml-stdlib/Time/{Occurrences,Time}.sysml`) is present, parseable, and
resolves the animation types: a part that specializes `Occurrence` with
`Snapshot` members and a `Clock` compiles with those references resolved when the
bundle is passed to sml2c (and, as a control, they do NOT resolve without it).
Also smoke-tests that such a model imports. Skips where sml2c is unavailable.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

import bpy

TREE_IDNAME = "SysMLNodeTree"

MODEL = """package Anim {
    private import Occurrences::*;
    private import Time::*;
    part def Wheel :> Occurrence {
        item startPose : Snapshot;
        item endPose : Snapshot;
    }
    part clock : Clock;
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
class SysMLAnimationStdlibTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._model = os.path.join(tempfile.mkdtemp(), "anim.sysml")
        with open(cls._model, "w", encoding="utf-8") as f:
            f.write(MODEL)

    def test_bundle_present(self):
        for rel in ("Time/Occurrences.sysml", "Time/Time.sysml"):
            self.assertTrue(os.path.exists(os.path.join(stdlib_dir(), rel)), f"missing {rel}")

    def test_bundle_parses(self):
        sml2c = sml2c_binary()
        for rel in ("Time/Occurrences.sysml", "Time/Time.sysml"):
            proc = subprocess.run([sml2c, "--parse-only", os.path.join(stdlib_dir(), rel)],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, f"{rel} is not parseable:\n{proc.stderr}")

    def test_temporal_types_resolve_with_bundle(self):
        proc = subprocess.run(
            [sml2c_binary(), "--stdlib-path", stdlib_dir(), "--emit-json", self._model],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        ast = json.loads(proc.stdout)
        self.assertIn("Occurrence", resolved(ast, "Wheel", "specializes"))
        self.assertIn("Snapshot", resolved(ast, "startPose", "types"))
        self.assertIn("Clock", resolved(ast, "clock", "types"))

    def test_control_unresolved_without_bundle(self):
        proc = subprocess.run([sml2c_binary(), "--emit-json", self._model],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        ast = json.loads(proc.stdout)
        self.assertNotIn("Snapshot", resolved(ast, "startPose", "types"),
                         "Snapshot should be unresolved without the bundled library")

    def test_temporal_model_imports(self):
        before = set(bpy.data.node_groups.keys())
        self.assertEqual(bpy.ops.node.sysml_import(filepath=self._model), {'FINISHED'})
        new = [ng for key, ng in bpy.data.node_groups.items()
               if key not in before and ng.bl_idname == TREE_IDNAME]
        self.assertEqual(len(new), 1)
        names = {n.element_name for n in new[0].nodes}
        self.assertIn("Wheel", names)
        self.assertIn("clock", names)


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
