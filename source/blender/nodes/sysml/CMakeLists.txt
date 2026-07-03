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
  ${CMAKE_SOURCE_DIR}/extern/json/include
  # RNA_prototypes.hh
  ${CMAKE_BINARY_DIR}/source/blender/makesrna
)

set(INC_SYS
)

# Generated per-kind element nodes (BSML1). Regenerate with
# tools/sysml/gen_sysml_nodes.py; never hand-edit the generated files.
include(${CMAKE_CURRENT_SOURCE_DIR}/sysml_generated_sources.cmake)

set(SRC
  intern/export_bpy.cc
  intern/export_model.cc
  intern/export_notation.cc
  intern/import_sysml.cc
  intern/layout_sysml.cc
  intern/sml2c_bridge.cc
  node_sysml_register.cc
  node_sysml_socket.cc
  node_sysml_tree.cc
  node_sysml_util.cc

  ${SYSML_GENERATED_SRC}

  intern/export_model.hh
  intern/import_sysml.hh
  intern/layout_sysml.hh
  intern/sml2c_bridge.hh
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

# Ship the pinned sml2c next to the Blender executable at runtime, mirroring how
# Blender installs its runtime library dependencies. Build-time the binary lives
# under the fetched/pinned extern/sml2c/ (populate via tools/sysml/fetch_sml2c.py);
# the bridge (intern/sml2c_bridge.cc) then resolves it relative to the program dir.
if(WIN32)
  set(_SML2C_RUNTIME ${CMAKE_SOURCE_DIR}/extern/sml2c/bin/windows/sml2c.exe)
elseif(APPLE)
  set(_SML2C_RUNTIME ${CMAKE_SOURCE_DIR}/extern/sml2c/bin/macos/sml2c)
else()
  set(_SML2C_RUNTIME ${CMAKE_SOURCE_DIR}/extern/sml2c/bin/linux/sml2c)
endif()
if(EXISTS ${_SML2C_RUNTIME})
  install(PROGRAMS ${_SML2C_RUNTIME} DESTINATION "." COMPONENT Libraries)
endif()
unset(_SML2C_RUNTIME)

# Ship the bundled minimal SysML standard library (Geometry ShapeItems /
# SpatialItems) next to the executable as `sysml-stdlib/`, so the bridge can
# pass it to sml2c via --stdlib-path and parts resolve against real library
# types (SCRUM-624). Committed source, unlike the sml2c binary.
if(EXISTS ${CMAKE_SOURCE_DIR}/extern/sysml-stdlib)
  install(DIRECTORY ${CMAKE_SOURCE_DIR}/extern/sysml-stdlib DESTINATION "." COMPONENT Libraries)
endif()
