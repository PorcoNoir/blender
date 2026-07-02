/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 *
 * Public entry points for exporting a SysML node tree back to text
 * (BSML3 / SCRUM-498). Canonical `.sysml` notation now; a bpy graph-builder
 * `.py` follows in SCRUM-500.
 */

#pragma once

#include <string>

#include "BLI_string_ref.hh"

namespace blender {
struct bNodeTree;
}

namespace blender::nodes::sysml {

/** Emit `tree` as canonical SysML v2 notation text (port of `notation.ts`). */
std::string export_sysml_notation(const bNodeTree &tree);

/**
 * Emit `tree` to `filepath` as canonical `.sysml`. Returns the number of
 * top-level elements written, or -1 on a write error (message in `r_report`).
 */
int export_sysml_notation_file(const bNodeTree &tree,
                               StringRefNull filepath,
                               std::string &r_report);

}  // namespace blender::nodes::sysml
