<!--
SPDX-FileCopyrightText: 2026 Blender Authors
SPDX-License-Identifier: GPL-2.0-or-later
-->

# Blender-SML — License Review Checklist (SCRUM-679)

> **Owner-completed.** This document records the checklist and the *factual*
> context gathered by engineering. The **Determination** column is a legal call
> and is intentionally left open — it is filled in by the project owner before an
> MVP release tag. Nothing here is legal advice.

**Status legend:** ☐ open · ☑ resolved
**Owner:** project owner (legal sign-off) unless noted.

---

## 1. Blender fork (GPL)

| Item | Facts gathered | Determination |
|---|---|---|
| Base license | Blender ships under **GNU GPL v2-or-later** (`COPYING` at repo root). | ☐ |
| Fork additions | All Blender-SML source carries `SPDX-License-Identifier: GPL-2.0-or-later` headers (C++ nodes, Python `bl_ui/sysml_*`, tools, tests). | ☐ |
| Distribution of binaries | Releasing a built `blender.exe` triggers GPL source-availability obligations for the whole work. Confirm the release provides/points to complete corresponding source. | ☐ |

## 2. sml2c (the SysML compiler)

| Item | Facts gathered | Determination |
|---|---|---|
| License terms | sml2c lives in the **private** repo `PorcoNoir/sml2c`. Its license is **not yet recorded here** — capture it (add `extern/sml2c/LICENSE` or a note). | ☐ |
| Bundled vs fetched | The binary is **never committed** to this repo. It is fetched at build time by `tools/sysml/fetch_sml2c.py`, pinned by version + SHA-256 in `extern/sml2c/sml2c.lock` (currently `v0.46.0-alpha`). Runtime dep installed next to `blender.exe`. | ☐ |
| GPL interaction | Determine whether sml2c is (a) an at-arm's-length tool invoked as a subprocess (the bridge shells out to it), or (b) a derivative/combined work, and whether its license is GPL-compatible for redistribution alongside a GPL binary. Note: the current build **invokes sml2c as a separate process**, it is not linked. | ☐ |
| Redistribution | If releases ship the sml2c binary next to `blender.exe`, confirm sml2c's license permits that redistribution + whether its source must accompany it. | ☐ |

## 3. Bundled standard library (`extern/sysml-stdlib/`)

| Item | Facts gathered | Determination |
|---|---|---|
| Provenance | `extern/sysml-stdlib/` (VERSION 0.3.0) is a **hand-authored minimal, parseable subset** derived from the OMG SysML v2 standard library, trimmed to what the pinned sml2c parses (Geometry, Time). Foundational packages (ScalarValues/Quantities/ISQ/SI) are **not shipped** — they are built into sml2c. | ☐ |
| OMG licensing | Determine the OMG SysML v2 standard-library license and whether the derived subset may be redistributed under this repo's terms; add attribution if required. | ☐ |

## 4. Generated & tutorial artifacts

| Item | Facts gathered | Determination |
|---|---|---|
| Generated code | Generated files (`*_generated.py/.hh`) carry GPL SPDX headers and are produced from the pinned sml2c taxonomy by `tools/sysml/gen_*.py`. | ☐ |
| Tutorial `.blend`s | Produced by `tools/sysml/make_tutorials.py`; contain only project-authored content. Confirm no third-party assets embedded. | ☐ |
| Corpus | `tests/python/sysml_corpus/*.sysml` are project-authored test models. Confirm provenance of any externally-derived corpus files. | ☐ |

## 5. Release gating

| Item | Facts gathered | Determination |
|---|---|---|
| Pre-tag sign-off | Every item above is resolved (☑) before cutting an MVP release tag (`blender-sml-vX.Y.Z`). | ☐ |

---

*Update this file as items are resolved; the BSML5 exit gate only checks that the
checklist is present, not that it is completed — completion is the owner's call.*
