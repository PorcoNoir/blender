# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

set(INC
  .
  ..
  ../intern
  ../../blenlib
  ../../editors/include
  ../../makesrna
  # RNA_prototypes.hh
  ${CMAKE_BINARY_DIR}/source/blender/makesrna
)

set(INC_SYS
)

set(SRC
  node_sysml_register.cc
  node_sysml_socket.cc
  node_sysml_tree.cc
  node_sysml_util.cc

  node_sysml_register.hh
  node_sysml_util.hh
)

set(LIB
  PRIVATE bf::blenkernel
  PRIVATE bf::blenlib
  PRIVATE bf::blentranslation
  PRIVATE bf::dna
  PRIVATE bf::intern::guardedalloc
  bf_nodes
  PRIVATE bf::windowmanager
)

blender_add_lib(bf_nodes_sysml "${SRC}" "${INC}" "${INC_SYS}" "${LIB}")

# RNA_prototypes.hh
add_dependencies(bf_nodes_sysml bf_rna)
