/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 *
 * Public interface for the SysML v2 node tree (BSML0 / SCRUM-430).
 *
 * The SysML tree is a structural graph: its nodes represent OMG SysML v2
 * elements and relationships. Unlike the geometry/shader trees it is not
 * evaluated — "running" it means emitting canonical `.sysml` text or a bpy
 * graph-builder script (later BSML phases).
 */

#pragma once

#include "BKE_node.hh"

namespace blender {

extern bke::bNodeTreeType *ntreeType_SysML;

void register_node_tree_type_sysml();

}  // namespace blender
