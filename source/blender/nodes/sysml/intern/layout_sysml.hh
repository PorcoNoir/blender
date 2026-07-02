/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 *
 * Containment-aware auto-layout for a SysML node tree (BSML2 / SCRUM-449).
 * Port of `layoutGraph.ts`: reconstructs the parent/child hierarchy from the
 * tree's `members` links and places nodes depth-first, top-down, so an imported
 * model is readable without overlaps. Deterministic for a given tree; rewrites
 * only node locations.
 */

#pragma once

namespace blender {
struct bNodeTree;
}

namespace blender::nodes::sysml {

/**
 * Reposition every node in `tree` by its `members` containment hierarchy:
 * roots (nodes with no `members` parent) are stacked top-to-bottom, each child
 * indented one level to the right and placed below its previous sibling. Node
 * ordering follows link/creation order, so the result is deterministic.
 */
void layout_sysml_tree(bNodeTree &tree);

}  // namespace blender::nodes::sysml
