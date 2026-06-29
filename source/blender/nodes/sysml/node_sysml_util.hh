/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 *
 * Shared helpers for SysML v2 element nodes. The hand-written nodes
 * (SCRUM-433) and, later, the BSML1 generator both build on
 * `sysml_node_type_base()` so every SysML node is registered the same way.
 */

#pragma once

#include <optional>

#include "BKE_node.hh"
#include "BKE_node_legacy_types.hh"  // IWYU pragma: export

#include "node_sysml_register.hh"  // IWYU pragma: export

namespace blender::nodes {

/**
 * Default poll: a SysML element node may only be added to a SysML node tree.
 * Mirrors `tex_node_poll_default()`.
 */
bool sysml_node_poll_default(const bke::bNodeType *ntype,
                             const bNodeTree *ntree,
                             const char **r_disabled_hint);

/**
 * Initialize a `bNodeType` for a SysML element node: stamps the idname and the
 * legacy enum, pins the node to the SysML tree via the default poll, and wires
 * default link insertion. Callers set `ui_name`, `declare`, storage, etc.
 * afterwards. Mirrors `geo_node_type_base()` / `tex_node_type_base()`.
 */
void sysml_node_type_base(bke::bNodeType *ntype,
                          UString idname,
                          std::optional<int16_t> legacy_type = std::nullopt);

/**
 * Attach the shared `NodeSysMLElement` storage to a node type (SCRUM-434).
 * Uses the standard free/copy; the struct is plain POD so it persists via the
 * generic node-storage serialization.
 */
void sysml_node_storage_register(bke::bNodeType &ntype);

/** Allocate the `NodeSysMLElement` storage on a freshly created node. */
void sysml_node_storage_init(bNode *node);

}  // namespace blender::nodes
