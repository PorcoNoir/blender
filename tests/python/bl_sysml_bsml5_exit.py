# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""BSML5 exit gate — Blender-SML MVP complete (SCRUM-680).

The final acceptance gate: demonstrates every BSML5 pillar end-to-end, so a green
run here means BSML1-5 are shipped and the Blender-SML MVP is complete.

* **Library** — the standard-library catalog carries built-in + bundled packages,
  and the browser inserts a library-typed element whose SysML resolves.
* **Tutorials** — the generator produces the tutorial .blend set.
* **Corpus** — the manifest, on-disk corpus, and both fidelity/round-trip gates
  cover exactly the same models (no silent omission).
* **Docs & license** — the user guide and the license-review checklist ship.

Library resolution needs sml2c and soft-skips without it; everything else runs.
"""

import os
import sys
import tempfile
import unittest

import bpy

from bl_ui import sysml_library, sysml_diagnostics
from bl_ui.sysml_stdlib_index_generated import STDLIB_INDEX

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.abspath(os.path.join(_HERE, "..", "..", "tools", "sysml")))

import make_tutorials  # noqa: E402
from bl_sysml_corpus_coverage import CORPUS_MANIFEST, CORPUS_DIR  # noqa: E402
from bl_sysml_corpus import BASELINE  # noqa: E402
from bl_sysml_roundtrip import CORPUS  # noqa: E402

_DOCS = os.path.abspath(os.path.join(_HERE, "..", "..", "docs"))


class BSML5ExitGate(unittest.TestCase):
    # -- library pillar ------------------------------------------------------

    def test_library_catalog_and_insert(self):
        sources = {e["source"] for e in STDLIB_INDEX}
        self.assertLessEqual({"builtin", "bundled"}, sources)
        bpy.ops.wm.read_factory_settings(use_empty=True)
        tree = bpy.data.node_groups.new("M", "SysMLNodeTree")
        node = sysml_library.insert_library_element(tree, "ISQ", "LengthValue", "length")
        self.assertEqual(node[sysml_library.LIB_TYPE_KEY], "ISQ::LengthValue")

    @unittest.skipUnless(sysml_diagnostics.available(), "sml2c binary not available next to blender")
    def test_library_type_resolves(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        tree = bpy.data.node_groups.new("M", "SysMLNodeTree")
        node = sysml_library.insert_library_element(tree, "ISQ", "MassValue")
        findings = sysml_diagnostics.diagnose_text(sysml_library.library_snippet(node))
        self.assertFalse(sysml_diagnostics.has_errors(findings), findings)

    # -- tutorials pillar ----------------------------------------------------

    def test_tutorials_generate(self):
        with tempfile.TemporaryDirectory() as out:
            paths = make_tutorials.build_tutorials(out)
            self.assertEqual(len(paths), len(make_tutorials.TUTORIALS))
            self.assertTrue(all(os.path.getsize(p) > 0 for p in paths))

    # -- corpus pillar -------------------------------------------------------

    def test_corpus_gates_are_consistent(self):
        on_disk = sorted(f for f in os.listdir(CORPUS_DIR) if f.endswith(".sysml"))
        self.assertEqual(on_disk, sorted(CORPUS_MANIFEST))
        self.assertEqual(sorted(BASELINE), sorted(CORPUS_MANIFEST))
        self.assertEqual(sorted(CORPUS), sorted(CORPUS_MANIFEST))

    # -- docs & license pillar ----------------------------------------------

    def test_docs_and_license_present(self):
        self.assertTrue(os.path.exists(os.path.join(_DOCS, "BLENDER_SML_GUIDE.md")))
        self.assertTrue(os.path.exists(os.path.join(_DOCS, "LICENSE_REVIEW.md")))


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
