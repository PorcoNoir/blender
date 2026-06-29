/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 *
 * Internal registration entry points for the SysML node family. The public
 * tree handle lives in `NOD_sysml.hh`; individual element-node register
 * functions (SCRUM-433 onward) are declared here as they are added.
 */

#pragma once

#include "NOD_sysml.hh"

namespace blender {

/* The shared SysML element reference socket (SCRUM-432). */
void register_node_socket_type_sysml_element();

/* Element-node register functions (SCRUM-433+). */
namespace nodes {
void register_node_type_sysml_part_def();
void register_node_type_sysml_part_usage();
void register_node_type_sysml_connection_usage();
}  // namespace nodes

}  // namespace blender
