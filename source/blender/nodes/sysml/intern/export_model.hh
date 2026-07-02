/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 *
 * Shared graph → element model for the SysML exporters (BSML3 / SCRUM-497).
 *
 * The reverse of BSML2 import: read a `SysMLNodeTree` back into an ordered,
 * in-memory element tree that both `export_notation.cc` (→ `.sysml`) and
 * `export_bpy.cc` (→ bpy graph-builder `.py`) consume, so neither exporter has
 * to re-derive containment and relationships from raw links. Ports the
 * graph-reading half of `notation.ts`.
 */

#pragma once

#include <memory>
#include <string>
#include <vector>

namespace blender {
struct bNode;
struct bNodeTree;
}  // namespace blender

namespace blender::nodes::sysml {

/**
 * One SysML element read back from a node. Relationship vectors hold non-owning
 * pointers into the same #ExportModel (the referenced elements are owned by
 * #ExportModel::elements). `members` is the ordered containment (top-down);
 * the rest mirror the relationship input sockets.
 */
struct ExportElement {
  const bNode *node = nullptr;
  std::string idname; /* node type, e.g. "SysMLNodePartDef" */
  std::string name;
  std::string multiplicity;
  bool is_abstract = false;
  int order = 0; /* creation index in the tree; deterministic tie-break */

  std::vector<ExportElement *> members; /* ordered children (containment) */
  std::vector<ExportElement *> of;          /* typing */
  std::vector<ExportElement *> specializes; /* generalization */
  std::vector<ExportElement *> redefines;
  std::vector<ExportElement *> subject;
  std::vector<ExportElement *> connect; /* connector first end (connections) */
  std::vector<ExportElement *> from;    /* connector first end (flows) */
  std::vector<ExportElement *> to;      /* connector second end */
};

/** The whole tree as an ordered element forest. Owns every #ExportElement. */
struct ExportModel {
  std::vector<std::unique_ptr<ExportElement>> elements;
  std::vector<ExportElement *> roots; /* top-level, ordered top-down */
};

/**
 * Read `tree` into `r_model`: one element per node, containment reconstructed
 * from `members` links, relationships from the typing/specialization/connector
 * sockets. Ordering (roots and each element's children) is top-down by canvas
 * position with a stable tie-break, so the result is deterministic for a given
 * tree.
 */
void build_export_model(const bNodeTree &tree, ExportModel &r_model);

}  // namespace blender::nodes::sysml
