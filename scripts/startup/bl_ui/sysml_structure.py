# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Local structural checks for the SysML node graph (BSML4 / SCRUM-663).

Fast, graph-native validation that needs no sml2c — the node-attributable half of
BSML4's diagnostics. Each check returns findings keyed to a node, so they can be
shown as node badges (SCRUM-664):

* **abstract instantiated** — a usage typed (``of``) by an abstract definition;
* **illegal socket target** — a reference socket wired to a kind it can't accept
  (a usage's type must be a definition, a specialization must target a
  definition, a redefinition must target a usage);
* **malformed multiplicity** — a multiplicity string that doesn't parse, or whose
  lower bound exceeds its upper.

Kind categories come from the generated ``sysml_kind_category_generated`` table
(derived from the node taxonomy, so it tracks new kinds automatically).
"""

from bl_ui.sysml_kind_category_generated import KIND_CATEGORY

ABSTRACT_CODE = "B4001"
ILLEGAL_TARGET_CODE = "B4002"
MULTIPLICITY_CODE = "B4003"

# Which target categories each reference socket legally accepts. Sockets not
# listed (e.g. `members`, `connect`, `to`) are intentionally unconstrained here.
SOCKET_RULES = {
    "of": {"definition"},           # a usage's type is a definition
    "specializes": {"definition"},  # a definition specializes a definition
    "redefines": {"usage"},         # a usage redefines a usage
}


def category(node):
    return KIND_CATEGORY.get(node.bl_idname, "other")


def _display(node):
    return node.element_name or node.name


def _finding(node, severity, code, message):
    return {
        "node": node.name,
        "element": _display(node),
        "severity": severity,
        "code": code,
        "message": message,
    }


def _links_into(tree, node, socket_id):
    return [l for l in tree.links
            if l.to_node == node and l.to_socket.identifier == socket_id]


def _multiplicity_ok(text):
    """True if `text` is a well-formed multiplicity ('', 'n', 'n..m', 'n..*')."""
    s = (text or "").strip().strip("[]").strip()
    if not s:
        return True
    if ".." in s:
        lo, _, hi = s.partition("..")
        lo, hi = lo.strip(), hi.strip()
        if not lo.isdigit():
            return False
        if hi == "*":
            return True
        return hi.isdigit() and int(lo) <= int(hi)
    return s == "*" or s.isdigit()


def check_tree(tree):
    """Return the list of local structural findings for `tree`."""
    findings = []

    for node in tree.nodes:
        cat = category(node)

        # Abstract definition instantiated by a usage's type.
        if cat == "usage":
            for link in _links_into(tree, node, "of"):
                src = link.from_node
                if category(src) == "definition" and getattr(src, "is_abstract", False):
                    findings.append(_finding(
                        node, "error", ABSTRACT_CODE,
                        "Usage '{}' instantiates abstract definition '{}'".format(
                            _display(node), _display(src))))

        # Multiplicity well-formedness.
        mult = getattr(node, "multiplicity", "")
        if mult and not _multiplicity_ok(mult):
            findings.append(_finding(
                node, "warning", MULTIPLICITY_CODE,
                "Malformed multiplicity '{}'".format(mult)))

    # Reference sockets wired to a category they can't accept.
    for link in tree.links:
        rule = SOCKET_RULES.get(link.to_socket.identifier)
        if rule is None:
            continue
        src = link.from_node
        if category(src) not in rule:
            findings.append(_finding(
                link.to_node, "error", ILLEGAL_TARGET_CODE,
                "'{}' ({}) is not a valid {} target".format(
                    _display(src), category(src), link.to_socket.identifier)))

    return findings
