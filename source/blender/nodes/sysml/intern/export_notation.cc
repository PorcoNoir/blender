/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 *
 * Element model → canonical SysML v2 notation (BSML3 / SCRUM-498). Port of the
 * emission half of `notation.ts`, over the shared #ExportModel (SCRUM-497):
 * each element becomes `<keyword> <name>[ : Type][ :> Super][ ::> Redef]` with a
 * `{ … }` body for its members, and connectors get the `connect a to b` /
 * `flow … from a to b` forms. Keyword per kind comes from the generated
 * `sysml_notation_keyword()` table.
 */

#include "NOD_sysml_export.hh"

#include "export_model.hh"

#include <fstream>
#include <string>
#include <vector>

#include "DNA_node_types.h"

#include "sysml_notation_keywords.generated.hh"

namespace blender::nodes::sysml {

static bool ends_with(const std::string &s, const char *suffix)
{
  const std::string suf = suffix;
  return s.size() >= suf.size() && s.compare(s.size() - suf.size(), suf.size(), suf) == 0;
}

static std::string join_tokens(const std::vector<std::string> &tokens)
{
  std::string s;
  for (size_t i = 0; i < tokens.size(); i++) {
    if (i != 0 && !tokens[i].empty()) {
      s += ' ';
    }
    s += tokens[i];
  }
  return s;
}

static std::string join_names(const std::vector<ExportElement *> &targets)
{
  std::string s;
  for (size_t i = 0; i < targets.size(); i++) {
    if (i != 0) {
      s += ", ";
    }
    s += targets[i]->name;
  }
  return s;
}

/* Wrap in `[...]` unless the stored multiplicity already carries brackets. */
static std::string format_multiplicity(const std::string &mult)
{
  if (mult.empty() || mult.front() == '[') {
    return mult;
  }
  return "[" + mult + "]";
}

static std::vector<std::string> emit_element(const ExportElement &e);

static std::vector<std::string> emit_children(const ExportElement &e)
{
  std::vector<std::string> body;
  for (const ExportElement *child : e.members) {
    const std::vector<std::string> lines = emit_element(*child);
    body.insert(body.end(), lines.begin(), lines.end());
  }
  return body;
}

/* `header;` when the body is empty, else `header { <indented body> }`. */
static std::vector<std::string> as_block(const std::string &header,
                                         const std::vector<std::string> &body)
{
  if (body.empty()) {
    return {header + ";"};
  }
  std::vector<std::string> out;
  out.push_back(header + " {");
  for (const std::string &line : body) {
    out.push_back("    " + line);
  }
  out.push_back("}");
  return out;
}

/* connection/interface/allocation (`connect a to b`) and flow
 * (`flow … from a to b`). Anonymous connectors drop the keyword/name. */
static std::vector<std::string> emit_connector(const ExportElement &e,
                                               const std::string &keyword,
                                               const bool is_flow)
{
  const std::vector<ExportElement *> &first = is_flow ? e.from : e.connect;
  const bool is_allocation = e.idname == "SysMLNodeAllocationUsage";
  const bool anonymous = e.name.empty();

  std::vector<std::string> h;
  if (is_flow) {
    h.push_back("flow");
    if (!e.name.empty()) {
      h.push_back(e.name);
    }
    if (!e.of.empty()) {
      h.push_back("of");
      h.push_back(join_names(e.of));
    }
  }
  else if (!anonymous) {
    h.push_back(keyword);
    h.push_back(e.name);
    if (!e.of.empty()) {
      h.push_back(":");
      h.push_back(join_names(e.of));
    }
  }

  const char *first_kw = is_flow ? "from" : (is_allocation ? "allocate" : "connect");
  if (!first.empty()) {
    h.push_back(first_kw);
    h.push_back(first.front()->name);
  }
  if (!e.to.empty()) {
    h.push_back("to");
    h.push_back(e.to.front()->name);
  }

  return as_block(join_tokens(h), emit_children(e));
}

static std::vector<std::string> emit_element(const ExportElement &e)
{
  const std::string keyword = sysml_notation_keyword(e.idname);
  const bool is_usage = ends_with(e.idname, "Usage");
  const bool is_def = !is_usage; /* definitions + package */

  if (e.idname == "SysMLNodeConnectionUsage" || e.idname == "SysMLNodeInterfaceUsage" ||
      e.idname == "SysMLNodeAllocationUsage")
  {
    return emit_connector(e, keyword, /*is_flow*/ false);
  }
  if (e.idname == "SysMLNodeFlowUsage") {
    return emit_connector(e, keyword, /*is_flow*/ true);
  }

  std::vector<std::string> h;
  if (is_def && e.is_abstract) {
    h.push_back("abstract");
  }
  h.push_back(keyword);
  if (!e.name.empty()) {
    h.push_back(e.name);
  }
  /* Usage: multiplicity precedes the type clause (`part wheels [4] : Wheel`). */
  if (is_usage && !e.multiplicity.empty()) {
    h.push_back(format_multiplicity(e.multiplicity));
  }
  if (is_usage && !e.of.empty()) {
    h.push_back(":");
    h.push_back(join_names(e.of));
  }
  /* Definition: multiplicity trails the name (`part def Wheel [4]`). */
  if (is_def && !e.multiplicity.empty()) {
    h.push_back(format_multiplicity(e.multiplicity));
  }
  if (!e.specializes.empty()) {
    h.push_back(":>");
    h.push_back(join_names(e.specializes));
  }
  if (!e.redefines.empty()) {
    h.push_back("::>");
    h.push_back(join_names(e.redefines));
  }

  std::vector<std::string> body;
  if (e.idname == "SysMLNodeEnumerationDef") {
    /* An enum def's members are value literals — `enum UNO;`, not the generic
     * `attribute UNO : …` usage form. */
    for (const ExportElement *literal : e.members) {
      body.push_back("enum " + literal->name + ";");
    }
  }
  else {
    for (const ExportElement *s : e.subject) {
      body.push_back("subject " + s->name + ";");
    }
    const std::vector<std::string> children = emit_children(e);
    body.insert(body.end(), children.begin(), children.end());
  }

  return as_block(join_tokens(h), body);
}

std::string export_sysml_notation(const bNodeTree &tree)
{
  ExportModel model;
  build_export_model(tree, model);

  std::string out;
  for (const ExportElement *root : model.roots) {
    for (const std::string &line : emit_element(*root)) {
      out += line;
      out += '\n';
    }
    out += '\n';
  }
  return out;
}

int export_sysml_notation_file(const bNodeTree &tree,
                               StringRefNull filepath,
                               std::string &r_report)
{
  ExportModel model;
  build_export_model(tree, model);

  std::string out;
  for (const ExportElement *root : model.roots) {
    for (const std::string &line : emit_element(*root)) {
      out += line;
      out += '\n';
    }
    out += '\n';
  }

  std::ofstream file(filepath.c_str(), std::ios::binary);
  if (!file) {
    r_report += "could not open file for writing: " + std::string(filepath.c_str()) + "\n";
    return -1;
  }
  file << out;
  if (!file) {
    r_report += "write error\n";
    return -1;
  }
  return int(model.roots.size());
}

}  // namespace blender::nodes::sysml
