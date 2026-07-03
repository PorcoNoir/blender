/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 *
 * See export_model.hh. Two passes over the tree: create one #ExportElement per
 * node (reading its stored fields), then route each link by its target socket
 * identifier into containment (`members`) or a relationship vector. Ordering is
 * top-down by canvas Y (nodes sit at `location[1] = -y`, so larger is higher)
 * with the creation index as a stable tie-break.
 */

#include "export_model.hh"

#include <algorithm>
#include <cstring>
#include <unordered_map>

#include "DNA_node_types.h"

#include "BLI_listbase.hh"

namespace blender::nodes::sysml {

/* Relationship input sockets → the ExportElement vector they populate. */
static std::vector<ExportElement *> *relation_slot(ExportElement &e, const char *socket_id)
{
  if (strcmp(socket_id, "of") == 0) {
    return &e.of;
  }
  if (strcmp(socket_id, "specializes") == 0) {
    return &e.specializes;
  }
  if (strcmp(socket_id, "redefines") == 0) {
    return &e.redefines;
  }
  if (strcmp(socket_id, "subject") == 0) {
    return &e.subject;
  }
  if (strcmp(socket_id, "connect") == 0) {
    return &e.connect;
  }
  if (strcmp(socket_id, "from") == 0) {
    return &e.from;
  }
  if (strcmp(socket_id, "to") == 0) {
    return &e.to;
  }
  return nullptr;
}

void build_export_model(const bNodeTree &tree, ExportModel &r_model)
{
  std::unordered_map<const bNode *, ExportElement *> by_node;

  /* Pass 1: one element per node, with its stored fields. */
  int index = 0;
  for (const bNode &node : tree.nodes) {
    auto element = std::make_unique<ExportElement>();
    ExportElement &e = *element;
    e.node = &node;
    e.idname = node.idname;
    e.order = index++;
    if (node.storage != nullptr) {
      const NodeSysMLElement &storage = *static_cast<const NodeSysMLElement *>(node.storage);
      e.name = storage.name;
      e.multiplicity = storage.multiplicity;
      e.is_abstract = (storage.flag & SYSML_ELEMENT_ABSTRACT) != 0;
    }
    by_node.emplace(&node, &e);
    r_model.elements.push_back(std::move(element));
  }

  /* Pass 2: route links. A `members` link is containment (from = child, to =
   * parent); everything else feeds the target node's relationship vector. */
  std::unordered_map<const ExportElement *, bool> has_parent;
  for (const bNodeLink &link : tree.links) {
    if (link.fromnode == nullptr || link.tonode == nullptr || link.tosock == nullptr) {
      continue;
    }
    const auto from_it = by_node.find(link.fromnode);
    const auto to_it = by_node.find(link.tonode);
    if (from_it == by_node.end() || to_it == by_node.end()) {
      continue;
    }
    ExportElement &from = *from_it->second;
    ExportElement &to = *to_it->second;
    const char *socket_id = link.tosock->identifier;

    if (strcmp(socket_id, "members") == 0) {
      to.members.push_back(&from);
      has_parent[&from] = true;
      continue;
    }
    if (std::vector<ExportElement *> *slot = relation_slot(to, socket_id)) {
      slot->push_back(&from);
    }
  }

  /* Deterministic top-down ordering: canvas Y descending (Y-up space), then
   * creation index. Applied to roots and every element's children. */
  const auto by_layout = [](const ExportElement *a, const ExportElement *b) {
    const float ya = a->node->location[1];
    const float yb = b->node->location[1];
    if (ya != yb) {
      return ya > yb;
    }
    return a->order < b->order;
  };
  const auto by_order = [](const ExportElement *a, const ExportElement *b) {
    return a->order < b->order;
  };

  for (std::unique_ptr<ExportElement> &element : r_model.elements) {
    ExportElement &e = *element;
    std::sort(e.members.begin(), e.members.end(), by_layout);
    /* Relationship targets have no meaningful spatial order; keep them stable
     * by creation index. */
    for (std::vector<ExportElement *> *slot :
         {&e.of, &e.specializes, &e.redefines, &e.subject, &e.connect, &e.from, &e.to})
    {
      std::sort(slot->begin(), slot->end(), by_order);
    }
    if (has_parent.find(&e) == has_parent.end()) {
      r_model.roots.push_back(&e);
    }
  }
  std::sort(r_model.roots.begin(), r_model.roots.end(), by_layout);
}

}  // namespace blender::nodes::sysml
