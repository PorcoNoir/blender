# Blender-SML v0.1.0

**First tagged release of the Blender-SML fork — the BSML0 engine spike.**
Native SysML v2 node-tree foundation in Blender, hand-written to prove the
approach before the generator (BSML1).

- **Base:** Blender 5.3.0 Alpha · **Platform:** Windows x64
- **Semver:** `0.1.0` (pre-1.0 — experimental; format and API may change)
- **Phase:** BSML0 (Jira epic SCRUM-429) · Exit-gate decision: **GO**

---

## Highlights
- New **`SysMLNodeTree`** node tree type (`NTREE_SYSML`), peer to
  Geometry/Shader/Compositor — open it from the editor-type selector as the
  **SysML Node Editor**.
- **`NodeSocketSysMLElement`** reference socket — the `self` ↔ ref-input wiring
  primitive every SysML node reuses.
- Three element nodes: **Part Definition**, **Part Usage**, **Connection Usage**,
  with their typed reference sockets (`members` / `of` / `specializes` /
  `redefines` / `connect` / `to`).
- Per-element data (`NodeSysMLElement`: name, short name, multiplicity, abstract
  flag) stored in DNA and **persisted across `.blend` save/load**.

## What's included (BSML0 stories)
| Story | Delivered |
|---|---|
| SCRUM-430 | `nodes/sysml/` scaffold + `NTREE_SYSML` tree type registration |
| SCRUM-431 | Node-editor integration, add-menu, and header tree activation |
| SCRUM-432 | `NodeSocketSysMLElement` reference socket (DNA + RNA + draw) |
| SCRUM-433 | PartDef / PartUsage / ConnectionUsage element nodes |
| SCRUM-434 | `NodeSysMLElement` DNA storage + RNA, generic save/load |
| SCRUM-435 | Drop/wire/save-reload verification + go/no-go (GO) |

## Verification
- **14 automated tests** in `tests/python/bl_sysml_nodetree.py` (tree type,
  socket, node socket shapes, storage props, wiring, add-menu, and a `.blend`
  save→reload round-trip) — all green and gating this release in CI.

## Build / compatibility notes
- Requires **MSVC ≥ 19.44.35216 (VS 2022 17.14.14)**. That compiler ICEs on a
  new core header; this fork carries a behavior-preserving fix in
  `BLI_normalized_int_types.hh` (split bit-field storage). Identical layout.
- Built with **USD/Hydra OFF** (matches the spike configuration).
- The header fix touches an upstream Blender file — reconcile on any rebase
  onto upstream.

## Known limitations
- **No node grouping** ("Make Group" raises `KeyError: 'SysMLNodeTree'`) — needs
  a `SysMLNodeGroup` node + `node_tree_group_type` mapping. Deferred to a later
  story.
- Hand-written nodes only — the full ~47-kind SysML taxonomy and the
  `sml2c`-driven generator land in **BSML1**.
- The SysML graph is **structural, not evaluated**; emit/codegen arrives in
  later phases (BSML3+).

## Next
**BSML1 — Generator + full taxonomy** is unblocked by this release's GO decision.
