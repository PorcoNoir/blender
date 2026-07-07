# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Corpus coverage guard (BSML5 / SCRUM-677).

Kills silent omission: proves the on-disk contract corpus, the manifest, and the
two corpus gates all cover exactly the same set of files. Adding or removing a
corpus `.sysml` therefore *must* update the manifest and both gates, or this
fails — so no corpus model is ever silently ungated. Pure (needs no sml2c), so
it always runs.

The gates it ties together:
* `bl_sysml_corpus.BASELINE` — import-fidelity golden counts (BSML2 / 451);
* `bl_sysml_roundtrip.CORPUS` — import->export->reimport stability (BSML3 / 499).
"""

import os
import sys
import unittest

# The sibling gate modules live alongside this file; make them importable when
# run via `blender --python` (their dir isn't on sys.path by default).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bl_sysml_corpus import BASELINE  # noqa: E402 - needs the path insert above
from bl_sysml_roundtrip import CORPUS  # noqa: E402

CORPUS_DIR = os.path.join(os.path.dirname(__file__), "sysml_corpus")

# Single source of truth for the curated corpus. Update deliberately when adding
# or removing a model — the tests below enforce every other list agrees.
CORPUS_MANIFEST = [
    "01_minimal.sysml",
    "02_imports.sysml",
    "03_specialization.sysml",
    "04_usages.sysml",
    "05_multiplicity.sysml",
    "06_magical_bag.sysml",
    "07_library_types.sysml",
    "all-kinds.sysml",
]


class CorpusCoverageTest(unittest.TestCase):
    def test_manifest_matches_directory(self):
        on_disk = sorted(f for f in os.listdir(CORPUS_DIR) if f.endswith(".sysml"))
        self.assertEqual(on_disk, sorted(CORPUS_MANIFEST),
                         "corpus dir vs manifest drift — update CORPUS_MANIFEST")

    def test_import_fidelity_gate_covers_manifest(self):
        self.assertEqual(sorted(BASELINE), sorted(CORPUS_MANIFEST),
                         "bl_sysml_corpus.BASELINE must cover every corpus model")

    def test_roundtrip_gate_covers_manifest(self):
        self.assertEqual(sorted(CORPUS), sorted(CORPUS_MANIFEST),
                         "bl_sysml_roundtrip.CORPUS must cover every corpus model")

    def test_manifest_has_no_duplicates(self):
        self.assertEqual(len(CORPUS_MANIFEST), len(set(CORPUS_MANIFEST)))


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
