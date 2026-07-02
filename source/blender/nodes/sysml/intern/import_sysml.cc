/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 *
 * sml2c AST (`--emit-json`) -> SysML nodes (BSML2 / SCRUM-447). Node-creation
 * half of the import: walk the containment tree, create one node per element
 * (kind-mapped via the generated table), and populate its stored fields.
 */

#include "import_sysml.hh"

#include <cstring>

#include "json.hpp"

#include "BKE_node.hh"

#include "DNA_node_types.h"

#include "sysml_import_kindmap.generated.hh"

namespace blender::nodes::sysml {

using json = nlohmann::json;

/* Copy a UTF-8 string into a fixed DNA char buffer, always null-terminated. */
template<size_t N> static void copy_field(char (&dst)[N], const std::string &src)
{
  const size_t n = std::min(src.size(), N - 1);
  std::memcpy(dst, src.data(), n);
  dst[n] = '\0';
}

static void populate_fields(bNode *node, const json &element)
{
  if (node == nullptr || node->storage == nullptr) {
    return;
  }
  NodeSysMLElement &storage = *static_cast<NodeSysMLElement *>(node->storage);

  if (element.contains("name") && element["name"].is_string()) {
    copy_field(storage.name, element["name"].get<std::string>());
  }
  if (element.contains("multiplicity") && element["multiplicity"].is_string()) {
    copy_field(storage.multiplicity, element["multiplicity"].get<std::string>());
  }
  if (element.value("isAbstract", false)) {
    storage.flag |= SYSML_ELEMENT_ABSTRACT;
  }
}

/* Recurse the containment tree (`members`/`body`), creating a node per element. */
static void walk(const bContext *C,
                 bNodeTree &tree,
                 const json &element,
                 int &count,
                 std::string &r_report)
{
  if (!element.is_object()) {
    return;
  }
  const std::string kind = element.value("kind", std::string());
  const std::string def_kind = element.value("defKind", std::string());

  const char *idname = sysml_import_idname(kind, def_kind);
  if (idname[0] != '\0') {
    bNode *node = bke::node_add_node(C, tree, UString(idname));
    populate_fields(node, element);
    count++;
  }
  else if (!kind.empty() && kind != "Program" && kind != "QualifiedName") {
    r_report += "unmapped SysML kind: " + kind +
                (def_kind.empty() ? std::string() : "/" + def_kind) + "\n";
  }

  if (element.contains("members") && element["members"].is_array()) {
    for (const json &child : element["members"]) {
      walk(C, tree, child, count, r_report);
    }
  }
  if (element.contains("body")) {
    const json &body = element["body"];
    if (body.is_array()) {
      for (const json &child : body) {
        walk(C, tree, child, count, r_report);
      }
    }
    else if (body.is_object()) {
      walk(C, tree, body, count, r_report);
    }
  }
}

int import_sysml_ast_json(const bContext *C,
                          bNodeTree &tree,
                          StringRefNull json_text,
                          std::string &r_report)
{
  const json ast = json::parse(json_text.c_str(), nullptr, /*allow_exceptions*/ false);
  if (ast.is_discarded()) {
    r_report += "sml2c output is not valid JSON\n";
    return 0;
  }
  int count = 0;
  walk(C, tree, ast, count, r_report);
  return count;
}

}  // namespace blender::nodes::sysml
