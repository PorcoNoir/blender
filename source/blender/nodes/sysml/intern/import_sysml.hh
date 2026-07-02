/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 *
 * Import a validated sml2c AST (`--emit-json`) into SysML nodes
 * (BSML2). Creates one node per element and populates its fields (SCRUM-447),
 * then wires the relationship sockets — `members`/`of`/`specializes`/
 * `redefines`/connector ends (SCRUM-448). Auto-layout follows in SCRUM-449.
 * Port of `astToGraph.ts`.
 */

#pragma once

#include <string>

#include "BLI_string_ref.hh"

struct bContext;
struct bNodeTree;

namespace blender::nodes::sysml {

/**
 * Parse sml2c `--emit-json` text and create one SysML node per element in
 * `tree`, populating name / multiplicity / abstract from the AST. Returns the
 * number of nodes created; appends a line per unmapped element kind to
 * `r_report` (kinds are reported, never silently dropped).
 */
int import_sysml_ast_json(const bContext *C,
                          bNodeTree &tree,
                          StringRefNull json_text,
                          std::string &r_report);

}  // namespace blender::nodes::sysml
