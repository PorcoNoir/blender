/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 *
 * The `NodeSocketSysMLElement` reference socket (BSML0 / SCRUM-432).
 *
 * Every SysML element node exposes a `self` identity output of this type and
 * the relationship inputs (`members`, `of`, `specializes`, `redefines`, and
 * the connector ends) accept it. The socket carries no data value of its own —
 * it is pure wiring/identity — so it is modeled on Blender's virtual socket
 * (`SOCK_CUSTOM`) rather than on a typed value socket. Edge *semantics*
 * (containment, typing, specialization) are interpreted by the later codegen
 * passes; here we only define the socket type, its RNA, and its colour.
 */

#include "MEM_guardedalloc.h"

#include "BLI_assert.hh"

#include "BKE_node.hh"

#include "DNA_node_types.h"

#include "RNA_access.hh"

#include "ED_node_c.hh"

#include "node_sysml_register.hh"

namespace blender {

static bke::bNodeSocketType *make_socket_type_sysml_element()
{
  const char *socket_idname = "NodeSocketSysMLElement";

  bke::bNodeSocketType *stype = MEM_new<bke::bNodeSocketType>(__func__);
  stype->free_self = [](bke::bNodeSocketType *type) { MEM_delete(type); };
  stype->idname = UString(socket_idname);

  /* RNA type uses the exact same identifier as the socket idname. */
  StructRNA *srna = stype->ext_socket.srna = RNA_struct_find(socket_idname);
  BLI_assert(srna != nullptr);
  RNA_struct_blender_type_set(srna, stype);

  stype->type = SOCK_CUSTOM;

  /* Editor-side draw + colour. Bad-level call (resolved at the final
   * executable link), mirroring how the virtual socket is initialised. */
  ED_init_node_socket_type_sysml_element(stype);

  /* `self` fans out to many ref inputs; ref inputs themselves may accept
   * several incoming wires (e.g. `members`, multiple `redefines`). Individual
   * sockets can tighten this via their own link limit where needed. */
  stype->use_link_limits_of_type = true;
  stype->input_link_limit = 0xFFF;
  stype->output_link_limit = 0xFFF;

  return stype;
}

void register_node_socket_type_sysml_element()
{
  bke::node_register_socket_type(*make_socket_type_sysml_element());
}

}  // namespace blender
