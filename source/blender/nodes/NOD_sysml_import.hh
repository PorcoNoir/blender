/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 *
 * Public entry point for importing a `.sysml` file into a SysML node tree
 * (BSML2 / SCRUM-450). Ties the bundled `sml2c` bridge, AST import, and
 * auto-layout together so the editor operator only has to pick a file and a
 * target tree.
 */

#pragma once

#include <string>

#include "BLI_string_ref.hh"

struct bContext;

namespace blender {
struct bNodeTree;
}

namespace blender::nodes::sysml {

/**
 * Compile `filepath` with `sml2c --emit-json`, import the resulting AST into
 * `tree` (nodes, relationship edges, auto-layout), and return the number of
 * nodes created. Returns -1 if sml2c could not run or the file failed to
 * compile; sml2c diagnostics (and any unresolved/unmapped notes) are appended
 * to `r_report` so the caller can surface them.
 */
int import_sysml_file(const bContext *C,
                      bNodeTree &tree,
                      StringRefNull filepath,
                      std::string &r_report);

}  // namespace blender::nodes::sysml
