# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""SysML standard-library index (BSML5 / SCRUM-675).

The index catalogs the resolvable standard library — built-in packages (compiled
into sml2c) and the domain packages bundled in extern/sysml-stdlib. The catalog
shape is checked deterministically; a representative type from each source is
verified to resolve through the diagnostics bridge (soft-skips without sml2c).
"""

import sys
import unittest

from bl_ui.sysml_stdlib_index_generated import STDLIB_INDEX
from bl_ui import sysml_diagnostics


class StdlibIndexShapeTest(unittest.TestCase):
    """Pure — always runs."""

    def setUp(self):
        self.by_pkg = {e["package"]: e for e in STDLIB_INDEX}

    def test_builtin_and_bundled_packages_present(self):
        for pkg in ("ScalarValues", "Quantities", "ISQ", "SI"):
            self.assertEqual(self.by_pkg[pkg]["source"], "builtin", pkg)
        for pkg in ("ShapeItems", "SpatialItems", "Time", "Occurrences"):
            self.assertEqual(self.by_pkg[pkg]["source"], "bundled", pkg)

    def test_representative_types_catalogued(self):
        self.assertIn("Real", self.by_pkg["ScalarValues"]["types"])
        self.assertIn("LengthValue", self.by_pkg["ISQ"]["types"])
        self.assertIn("Cuboid", self.by_pkg["ShapeItems"]["types"])
        self.assertIn("TimeInstant", self.by_pkg["Time"]["types"])

    def test_every_entry_wellformed(self):
        for entry in STDLIB_INDEX:
            self.assertIn(entry["source"], {"builtin", "bundled"})
            self.assertTrue(entry["types"], entry["package"])
            self.assertEqual(entry["types"], sorted(entry["types"]))


@unittest.skipUnless(sysml_diagnostics.available(), "sml2c binary not available next to blender")
class StdlibResolveTest(unittest.TestCase):
    """Every catalogued type must actually resolve."""

    def test_representative_type_per_source_resolves(self):
        for qualified in ("ScalarValues::Real", "ISQ::LengthValue",
                          "ShapeItems::Cuboid", "Time::TimeInstant"):
            model = "package M {{\n\tattribute a : {};\n}}\n".format(qualified)
            findings = sysml_diagnostics.diagnose_text(model)
            self.assertFalse(sysml_diagnostics.has_errors(findings),
                             (qualified, findings))


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
