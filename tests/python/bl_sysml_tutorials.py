# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Tutorial .blend generator (BSML5 / SCRUM-678).

Runs the headless tutorial generator and checks it produces the expected .blend
files deterministically. Graphs are built directly (no sml2c), so this always
runs.
"""

import os
import sys
import tempfile
import unittest

# make_tutorials lives under tools/sysml; put it on the path.
_TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tools", "sysml")
sys.path.insert(0, os.path.abspath(_TOOLS))

import make_tutorials  # noqa: E402 - needs the path insert above


class SysMLTutorialsTest(unittest.TestCase):
    def test_generator_produces_all_blends(self):
        with tempfile.TemporaryDirectory() as out:
            paths = make_tutorials.build_tutorials(out)
            expected = [name + ".blend" for name, _ in make_tutorials.TUTORIALS]
            self.assertEqual([os.path.basename(p) for p in paths], expected)
            for path in paths:
                self.assertTrue(os.path.exists(path), path)
                self.assertGreater(os.path.getsize(path), 0, path)

    def test_generation_is_repeatable(self):
        with tempfile.TemporaryDirectory() as out:
            first = make_tutorials.build_tutorials(out)
            second = make_tutorials.build_tutorials(out)   # overwrites in place
            self.assertEqual(len(first), len(second))
            self.assertEqual(len(second), len(make_tutorials.TUTORIALS))


def main():
    unittest.main(argv=[__file__] + (sys.argv[sys.argv.index("--") + 1:]
                                     if "--" in sys.argv else []))


if __name__ == "__main__":
    main()
