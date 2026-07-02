/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 *
 * sml2c AST (`--emit-json`) -> SysML node graph. Port of `astToGraph.ts`:
 *   Pass 1 (SCRUM-447) walks the containment tree and creates one node per
 *   element, populating its stored fields.
 *   Pass 2 (SCRUM-448) wires the relationship sockets — containment (`members`),
 *   typing (`of`), `specializes`, `redefines`, and connector ends
 *   (`connect`/`to`, or `from`/`to` for flows) — resolving each reference (via
 *   sml2c's `resolvedTo`) to the target node.
 */

#include "import_sysml.hh"
#include "layout_sysml.hh"
#include "sml2c_bridge.hh"

#include "NOD_sysml_import.hh"

#include <cstring>
#include <unordered_map>
#include <vector>

#include "json.hpp"

#include "BKE_node.hh"

#include "DNA_node_types.h"

#include "sysml_import_kindmap.generated.hh"

namespace blender::nodes::sysml {

using json = nlohmann::json;

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

/* Element created during pass 1, remembered for edge wiring in pass 2. */
struct Created {
  bNode *node;
  const json *element;
  bNode *parent;  /* enclosing node, or null at the root */
};

/* Resolved target name of a QualifiedName reference (sml2c pre-resolves it). */
static std::string ref_target(const json &qn)
{
  if (qn.contains("resolvedTo") && qn["resolvedTo"].is_string()) {
    return qn["resolvedTo"].get<std::string>();
  }
  if (qn.contains("parts") && qn["parts"].is_array() && !qn["parts"].empty() &&
      qn["parts"].back().is_string())
  {
    return qn["parts"].back().get<std::string>();
  }
  return "";
}

/* Link `from`'s `self` output into `to`'s `socket_id` input. Returns false when
 * either socket is absent (e.g. the target kind has no such slot). */
static bool wire(bNodeTree &tree, bNode &from, bNode &to, const char *socket_id)
{
  bNodeSocket *self = bke::node_find_socket(from, SOCK_OUT, UString("self"));
  bNodeSocket *slot = bke::node_find_socket(to, SOCK_IN, UString(socket_id));
  if (self == nullptr || slot == nullptr) {
    return false;
  }
  bke::node_add_link(tree, from, *self, to, *slot);
  return true;
}

static void create_pass(const bContext *C,
                        bNodeTree &tree,
                        const json &element,
                        bNode *parent,
                        std::vector<Created> &records,
                        std::unordered_map<std::string, bNode *> &by_name,
                        int &count,
                        std::string &r_report)
{
  if (!element.is_object()) {
    return;
  }
  const std::string kind = element.value("kind", std::string());
  const std::string def_kind = element.value("defKind", std::string());

  bNode *created = nullptr;
  const char *idname = sysml_import_idname(kind, def_kind);
  if (idname[0] != '\0') {
    created = bke::node_add_node(C, tree, UString(idname));
    populate_fields(created, element);
    count++;
    records.push_back({created, &element, parent});
    if (element.contains("name") && element["name"].is_string()) {
      by_name[element["name"].get<std::string>()] = created;
    }
  }
  else if (!kind.empty() && kind != "Program" && kind != "QualifiedName") {
    r_report += "unmapped SysML kind: " + kind +
                (def_kind.empty() ? std::string() : "/" + def_kind) + "\n";
  }

  bNode *child_parent = (created != nullptr) ? created : parent;
  if (element.contains("members") && element["members"].is_array()) {
    for (const json &child : element["members"]) {
      create_pass(C, tree, child, child_parent, records, by_name, count, r_report);
    }
  }
  if (element.contains("body")) {
    const json &body = element["body"];
    if (body.is_array()) {
      for (const json &child : body) {
        create_pass(C, tree, child, child_parent, records, by_name, count, r_report);
      }
    }
    else if (body.is_object()) {
      create_pass(C, tree, body, child_parent, records, by_name, count, r_report);
    }
  }
}

static void wire_refs(bNodeTree &tree,
                      bNode &node,
                      const json &element,
                      const char *key,
                      const char *socket_id,
                      const std::unordered_map<std::string, bNode *> &by_name,
                      std::string &r_report)
{
  if (!element.contains(key) || !element[key].is_array()) {
    return;
  }
  for (const json &ref : element[key]) {
    const std::string target = ref_target(ref);
    const auto it = by_name.find(target);
    if (it == by_name.end()) {
      r_report += std::string("unresolved ") + key + " reference: " + target + "\n";
      continue;
    }
    /* target's identity feeds this node's relationship slot. */
    wire(tree, *it->second, node, socket_id);
  }
}

static void wire_pass(bNodeTree &tree,
                      const std::vector<Created> &records,
                      const std::unordered_map<std::string, bNode *> &by_name,
                      std::string &r_report)
{
  for (const Created &rec : records) {
    bNode &node = *rec.node;
    const json &element = *rec.element;

    /* Containment: this element sits inside its parent's `members`. */
    if (rec.parent != nullptr) {
      wire(tree, node, *rec.parent, "members");
    }

    wire_refs(tree, node, element, "types", "of", by_name, r_report);
    wire_refs(tree, node, element, "specializes", "specializes", by_name, r_report);
    wire_refs(tree, node, element, "redefines", "redefines", by_name, r_report);

    /* Connector ends: first -> connect (or from for flows), second -> to. */
    if (element.contains("ends") && element["ends"].is_array()) {
      const bool has_connect = bke::node_find_socket(node, SOCK_IN, UString("connect")) != nullptr;
      const char *first_slot = has_connect ? "connect" : "from";
      const json &ends = element["ends"];
      for (size_t i = 0; i < ends.size(); i++) {
        const std::string target = ref_target(ends[i]);
        const auto it = by_name.find(target);
        if (it == by_name.end()) {
          r_report += "unresolved connector end: " + target + "\n";
          continue;
        }
        wire(tree, *it->second, node, (i == 0) ? first_slot : "to");
      }
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
  std::vector<Created> records;
  std::unordered_map<std::string, bNode *> by_name;
  int count = 0;
  create_pass(C, tree, ast, nullptr, records, by_name, count, r_report);
  wire_pass(tree, records, by_name, r_report);
  layout_sysml_tree(tree);
  return count;
}

int import_sysml_file(const bContext *C,
                      bNodeTree &tree,
                      StringRefNull filepath,
                      std::string &r_report)
{
  const Sml2cResult res = run_emit_json(filepath);
  if (!res.ok) {
    if (!res.error.empty()) {
      r_report += res.error;
      r_report += "\n";
    }
    if (!res.diagnostics.empty()) {
      r_report += res.diagnostics;
    }
    if (res.error.empty() && res.diagnostics.empty()) {
      r_report += "sml2c failed (exit " + std::to_string(res.exit_code) + ")\n";
    }
    return -1;
  }
  /* Surface warnings even on a successful compile. */
  if (!res.diagnostics.empty()) {
    r_report += res.diagnostics;
  }
  return import_sysml_ast_json(C, tree, res.output, r_report);
}

}  // namespace blender::nodes::sysml
