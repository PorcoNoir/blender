# SysML node generator (BSML1)

Generates the Blender SysML node family from a **pinned** `sml2c`, so the ~58
element kinds aren't hand-written. Ports the TS editor's
`tools/regen-element-table.ts` + `src/conversion/kindMaps.ts`.

## Pipeline
```
extern/sml2c/bin/<os>/sml2c  --emit-json  tools/sysml/probes/*.sysml
        │                                          │
        └── pinned (extern/sml2c/sml2c.lock)       └── harvest kinds + flags
                                                   ▼
             source/blender/nodes/sysml/sysml_elements.generated.hh   (X-macro table)
```

## Usage
```bash
# 1. Get the pinned sml2c (binaries are gitignored, never committed):
python tools/sysml/fetch_sml2c.py                    # download the pinned release + verify sha256
python tools/sysml/fetch_sml2c.py --from-local PATH  # or copy a local build (for an unreleased sml2c)

# sml2c is a private repo, so the download authenticates: `gh` (if signed in) is
# tried first, else GH_TOKEN / GITHUB_TOKEN from the environment.

# 2. Regenerate the table:
python tools/sysml/gen_sysml_nodes.py

# CI regen-diff gate (SCRUM-444): fail if the checked-in file is stale.
python tools/sysml/gen_sysml_nodes.py --check
```

Generated files are **checked in but never hand-edited**.

## Kind-count reconciliation (SCRUM-438)
Pinned **sml2c 0.45.4-alpha** (vs the v0.31.2 the editor table originally claimed
47 kinds from; the taxonomy has since grown to **58**).

| Bucket | Count | Notes |
|---|---|---|
| Harvested from sml2c | 41 | `--emit-json` on `probes/all-kinds.sysml` |
| Fallback — non-element | 5 | `library_package`, `import`, `alias`, `comment`, `documentation` (sml2c doesn't emit as own AST nodes) |
| Fallback — unparseable | 12 | `case`/`use_case`/`analysis_case`/`verification_case` (def+usage), `conjugated_port_def`, `binding`/`succession`/`reference` usages |
| **Total** | **58** | exact parity with the editor's `elementTable.generated.ts` |

**Why 12 are fallback-seeded:** sml2c 0.45.4 still rejects the compound-keyword
case family (`case def`, `use case def`, … → *"Expected declaration"*), port
conjugation isn't directly declarable, and `binding`/`succession`/`reference`
are usages without a `defKind`. They're seeded from the editor taxonomy (flags
mirror `elementTable.generated.ts`) so BSML1 still produces nodes for every
kind. When sml2c grows acceptance, extend `probes/` and they harvest instead.
