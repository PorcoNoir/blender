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

/* Element-node register functions are declared here as the node stories land,
 * e.g. void register_node_type_sysml_part_def(); */

}  // namespace blender
