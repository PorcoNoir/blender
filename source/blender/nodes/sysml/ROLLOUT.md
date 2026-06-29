# SysML v2 Nodes — Feature Rollout Plan

Fork objective: a native Blender node system whose nodes represent every
OMG **SysML v2** element and relationship, with a textual SysML scripting
surface that round-trips with the graph and exports to runnable **bpy**
code.

Reference assets (do **not** rebuild — reuse / port / generate from):

| Asset | Path | Role |
|---|---|---|
| `sml2c` | `M:\sysml-utils\sml2c` | C11 SysML v2 compiler/validator. `--emit-json` (validated AST), `--emit-sysml` (canonical round-trip). Our parser + validator + formatter. |
| `sml-node-editor` | `M:\sysml-utils\sml-node-editor` | Proven Blender-*style* SysML node editor (TS). Source-of-truth for taxonomy, socket shapes, kind maps, import/codegen logic to port. |

Key files to mine: `sml2/elementTable.generated.ts` (47 kinds, generated from
sml2c), `nodes/sysml.ts` (socket/field shapes), `conversion/kindMaps.ts`,
`conversion/astToGraph.ts`, `conversion/sml2cBridge.ts`, `treeTypes/sysmlV2/{python,notation}.ts`,
`sml2/{validate,allowedChildren,libraries}.ts`.

## Locked decisions

1. **Delivery: native C++ node types.** A new node tree type `NTREE_SYSML`
   (`ntreeType_SysML`, idname `"SysMLNodeTree"`), peer to Geometry/Shader/
   Compositor/Texture. Nodes registered via `NOD_REGISTER_NODE`, sockets via
   `NodeDeclarationBuilder`, DNA storage + RNA wrapping, `space_node` editor
   integration. RNA auto-exposes everything to `bpy` (satisfies "bpy module").
2. **sml2c: prebuilt binary, subprocess.** Per-OS `sml2c` bundled under the
   fork; import/export operators shell out to `--emit-json` / `--emit-sysml`.
   Mirrors `sml2cBridge.ts`. Pinned version; decoupled from Blender's build.
3. **Export target: bpy graph-builder script.** Export emits Python that, run
   in Blender, reconstructs the SysML node graph via the RNA API
   (`node_tree.nodes.new(...)`, set fields, `links.new(...)`).

## Architecture

```
 .sysml text ──sml2c --emit-json──► AST JSON ──import op (C++)──► SysMLNodeTree (native nodes)
      ▲                                                                  │
      │ sml2c --emit-sysml (oracle)            ┌── notation export ──► canonical .sysml
      └──────────── notation export ◄──────────┤
                                               └── bpy export ──────► graph-builder .py
```

The SysML graph is **structural, not evaluated** — there is no
`*_node_execute`. Nodes carry typed fields + relationship sockets; "running"
the graph means *emitting* (SysML text or bpy code), not computing values.

## Target source layout (new)

```
source/blender/nodes/sysml/
  node_sysml_tree.cc            # ntreeType_SysML registration, get_from_context, foreach_nodeclass
  node_sysml_util.{hh,cc}       # sysml_node_type_base(), shared socket/field helpers
  nodes/                        # GENERATED: one node_sysml_<kind>.cc per element kind
  sysml_elements.generated.hh   # GENERATED: 47-kind table (from sml2c probe)
  intern/sml2c_bridge.{hh,cc}   # subprocess wrapper: run_emit_json / run_emit_sysml
  intern/import_sysml.cc        # AST JSON -> nodes (port of astToGraph.ts)
  intern/export_notation.cc     # graph -> canonical .sysml (port of notation.ts)
  intern/export_bpy.cc          # graph -> bpy graph-builder .py (new)
  intern/validate.cc            # in-editor diagnostics (port of validate/allowedChildren)
  CMakeLists.txt
source/blender/makesdna/DNA_node_types.h   # + NTREE_SYSML, NodeSysML* storage structs
source/blender/makesrna/intern/rna_nodetree.cc  # + SysML node/socket RNA
source/blender/editors/space_node/...      # add-menu category, draw, get_from_context
tools/sysml/gen_sysml_nodes.py             # GENERATOR: sml2c element table -> .cc/DNA/RNA stubs
extern/sml2c/bin/{windows,linux,macos}/    # bundled prebuilt sml2c
tests/sysml/                               # golden .sysml <-> graph <-> .py round-trip fixtures
```

## Code-generation strategy (the multiplier)

Hand-writing 47 element kinds × (node .cc + DNA struct + RNA) is the bulk of
the risk. Instead, **generate** them, exactly as the editor generates
`elementTable.generated.ts` from sml2c:

- `tools/sysml/gen_sysml_nodes.py` probes `sml2c` (and ports `kindMaps.ts`)
  to produce `sysml_elements.generated.hh` (kind → pyClass, isContainer,
  isUsage, canSpecialize) plus a `node_sysml_<kind>.cc` per kind from one
  template, and the matching DNA storage + RNA define blocks.
- Generated files are checked in but never hand-edited; regen tracks the
  pinned sml2c. The template encodes the relationship sockets below.

## Element taxonomy & relationship sockets (from the editor)

47 kinds across families: **package** · **definition** (`*_def`) ·
**usage** (`*_usage`) · **port/connection/interface/flow** · **requirement/
constraint/concern** · **behavior** (action/state/calc) · **case** (use/verif/
analysis) · **view/viewpoint/rendering** · **metadata/doc/comment** · special
(`attribute`, `import`, `alias`, `library_package`, `binding`, `succession`,
`reference`, `satisfy`).

Relationship sockets (custom `SocketSysMLElement` ref socket + `members`
containment socket):

| Socket | SysML | Edge meaning |
|---|---|---|
| `members` (in) | containment | `children=[...]` |
| `of` (in) | typing | `: Type` |
| `specializes` (in) | `:>` | supertype |
| `redefines` (in) | `::>`/`:>>` | feature redefinition |
| `connect`/`to`/`from` | connector ends | `connect a to b`, `flow … from … to …` |
| `subject` (in) | requirement subject | `subject …` |
| `self` (out) | identity | wired into others' ref slots |

## Phased rollout

**Phase 0 — Engine spike (1 sprint).** Register `NTREE_SYSML` +
`ntreeType_SysML` + `"SysMLNodeTree"` editor space entry. Hand-write the
custom `SocketSysMLElement` ref socket (DNA+RNA+draw) and **3 nodes**
(`PartDef`, `PartUsage`, `ConnectionUsage`). *Exit: open a SysML node editor,
drop & wire the 3 nodes, save/load a .blend.*

**Phase 1 — Generator + full taxonomy (2 sprints).** Build
`gen_sysml_nodes.py`; generate `sysml_elements.generated.hh` and all 47
`node_sysml_<kind>.cc` + DNA + RNA from the sml2c probe. Categorized add-menu
with the editor's accent groups. *Exit: all 47 kinds instantiable, wireable,
persisted; RNA visible from `bpy`.*

**Phase 2 — Import `.sysml` → graph (1–2 sprints).** `sml2c_bridge`
subprocess + `import_sysml.cc` (port `astToGraph.ts`): JSON AST → nodes +
edges (`members`/`of`/`specializes`/`subject`/connector ends) + auto-layout
(port `layoutGraph.ts`). *Exit: Sensmetry tutorial `.sysml` files import to a
faithful graph.*

**Phase 3 — Export & round-trip (2 sprints).**
- 3a `export_notation.cc` (port `notation.ts`): graph → canonical `.sysml`;
  verify stability with `sml2c --emit-sysml` as oracle.
- 3b `export_bpy.cc`: graph → bpy graph-builder `.py`. *Exit:
  text ⇄ graph ⇄ generated .py all agree on the tutorial corpus.*

**Phase 4 — Validation & native scripting surface (1–2 sprints).** Wire
sml2c diagnostics onto nodes (badges/colors; port `validate.ts` +
`allowedChildren.ts` for fast local checks, sml2c authoritative). In-editor
SysML `Text` datablock that parses-to-nodes on demand — the "native node
scripting" surface.

**Phase 5 — Library, polish, packaging (1 sprint).** Bundle `sysml.library`
refs (port `libraries.ts`), tutorial `.blend`s, manual docs, CI against the
sml2c contract corpus (`tests/sml2c-contract`).

## Cross-cutting

- **Tests:** golden round-trip fixtures reusing `tests/sml2c-contract`; every
  generated kind must import→export→reimport stably.
- **Versioning:** pin one sml2c build; the generated table tracks the binary;
  `.blend` forward-compat handled in DNA `versioning_*.cc`.
- **Non-goals (initial):** node evaluation/simulation, FMU/C emission, live
  multi-user editing.

## Risks

| Risk | Mitigation |
|---|---|
| 47× boilerplate (node+DNA+RNA) | Generator; never hand-edit generated files. |
| DNA storage churn across kinds | One flexible `NodeSysMLElement` storage struct (name/short_name/multiplicity/flags) shared by all kinds; specialize only where needed. |
| sml2c JSON schema drift | Pin version; `kindMaps.ts` port is single source; contract tests. |
| RNA/`bpy` surface stability for export | Generate export against the same RNA the import uses; round-trip test guards it. |
| Round-trip fidelity (text↔graph) | sml2c `--emit-sysml` is the oracle in CI. |
```
