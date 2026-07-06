# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""sml2c diagnostics bridge (BSML4 / SCRUM-662).

The parser is exercised deterministically (no sml2c needed); the live
sml2c-invoking checks soft-skip when the binary is absent, like the other
library-resolution tests.
"""

import sys
import unittest

from bl_ui import sysml_diagnostics


class DiagnosticsParserTest(unittest.TestCase):
    """Pure parser — always runs, even without sml2c."""

    def test_parses_error_with_code_and_position(self):
        line = "C:/x/bad.sysml:2: error: [E0200] Undefined name 'Missing'."
        (f,) = sysml_diagnostics.parse_diagnostics(line)
        self.assertEqual(f["severity"], "error")
        self.assertEqual(f["code"], "E0200")
        self.assertEqual(f["line"], 2)
        self.assertEqual(f["file"], "C:/x/bad.sysml")  # drive colon not eaten
        self.assertIn("Missing", f["message"])

    def test_parses_column_and_warning(self):
        (f,) = sysml_diagnostics.parse_diagnostics("m.sysml:3:5: warning: [W0100] hmm")
        self.assertEqual((f["severity"], f["code"], f["line"], f["col"]), ("warning", "W0100", 3, 5))

    def test_ignores_non_diagnostic_lines(self):
        self.assertEqual(sysml_diagnostics.parse_diagnostics("Resolution failed with 1 error.\n"), [])

    def test_has_errors(self):
        self.assertTrue(sysml_diagnostics.has_errors([{"severity": "error"}]))
        self.assertFalse(sysml_diagnostics.has_errors([{"severity": "warning"}]))


@unittest.skipUnless(sysml_diagnostics.available(), "sml2c binary not available next to blender")
class DiagnosticsSml2cTest(unittest.TestCase):
    """Live sml2c invocation."""

    def test_undefined_reference_is_flagged(self):
        text = "package P {\n  part def A :> Missing;\n}\n"
        findings = sysml_diagnostics.diagnose_text(text)
        errors = [f for f in findings if f["severity"] == "error"]
        self.assertTrue(errors, "expected at least one error")
        self.assertTrue(any(f["code"] == "E0200" and "Missing" in f["message"] for f in errors))
        self.assertTrue(sysml_diagnostics.has_errors(findings))

    def test_clean_model_has_no_errors(self):
        text = "package P {\n  part def A;\n  part def B :> A;\n}\n"
        self.assertFalse(sysml_diagnostics.has_errors(sysml_diagnostics.diagnose_text(text)))


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
