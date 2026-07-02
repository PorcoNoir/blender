/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 *
 * See layout_sysml.hh. Depth-first, subtree-aware placement ported from
 * `layoutGraph.ts`. The editor's LibraryRef "left lane" is intentionally
 * omitted: our `of`/`specializes`/`redefines` edges point at real imported
 * nodes that already have a home in the containment hierarchy, so re-placing
 * them as refs would fight their hierarchy position. Layout is therefore driven
 * purely by the `members` tree.
 */

#include "layout_sysml.hh"

#include <algorithm>
#include <cstring>
#include <unordered_map>
#include <unordered_set>
#include <vector>

#include "DNA_node_types.h"

#include "BLI_listbase.hh"

namespace blender::nodes::sysml {

/* Matches DEFAULT_LAYOUT in astToGraph.ts / layoutGraph.ts. Y grows downward in
 * the layout math; we negate it into Blender's Y-up node space when placing. */
static const float H_GUTTER = 280.0f;      /* horizontal step per nesting level */
static const float V_GUTTER = 90.0f;       /* vertical step between rows */
static const float SUBTREE_GUTTER = 40.0f; /* extra gap between top-level subtrees */
static const float START_X = 60.0f;
static const float START_Y = 40.0f;

using ChildMap = std::unordered_map<const bNode *, std::vector<bNode *>>;

/* Place `node` at (x, y) and its subtree below/right. Returns the deepest Y
 * used by the subtree (same contract as layoutGraph's `place`). */
static float place(bNode &node,
                   const float x,
                   const float y,
                   const ChildMap &children_of,
                   std::unordered_set<const bNode *> &visited)
{
  if (!visited.insert(&node).second) {
    /* Defensive: a well-formed containment graph is a tree, but never recurse
     * twice into the same node if the links happen to be malformed. */
    return y;
  }
  node.location[0] = x;
  node.location[1] = -y;

  float lowest = y;
  float child_y = y;
  const auto it = children_of.find(&node);
  if (it != children_of.end()) {
    for (bNode *child : it->second) {
      const float placed_bottom = place(*child, x + H_GUTTER, child_y, children_of, visited);
      lowest = std::max(lowest, placed_bottom);
      child_y = placed_bottom + V_GUTTER;
    }
  }
  return std::max(y, lowest);
}

void layout_sysml_tree(bNodeTree &tree)
{
  ChildMap children_of;
  std::unordered_set<const bNode *> has_parent;

  for (bNodeLink &link : tree.links) {
    if (link.tonode == nullptr || link.fromnode == nullptr || link.tosock == nullptr) {
      continue;
    }
    /* Containment link: `child.self` -> `parent.members`. */
    if (strcmp(link.tosock->identifier, "members") == 0) {
      children_of[link.tonode].push_back(link.fromnode);
      has_parent.insert(link.fromnode);
    }
  }

  std::unordered_set<const bNode *> visited;
  float root_y = START_Y;
  for (bNode &node : tree.nodes) {
    if (has_parent.find(&node) != has_parent.end()) {
      continue; /* placed as part of its parent's subtree */
    }
    const float placed_bottom = place(node, START_X, root_y, children_of, visited);
    root_y = placed_bottom + V_GUTTER + SUBTREE_GUTTER;
  }
}

}  // namespace blender::nodes::sysml
