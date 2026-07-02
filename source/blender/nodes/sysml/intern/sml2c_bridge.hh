/* SPDX-FileCopyrightText: 2026 Blender Authors
 *
 * SPDX-License-Identifier: GPL-2.0-or-later */

/** \file
 * \ingroup nodes
 *
 * Bridge to the bundled `sml2c` SysML v2 compiler (BSML2 / SCRUM-446).
 *
 * Import (and later export round-trip) shell out to the pinned `sml2c` binary,
 * mirroring the editor's `sml2cBridge.ts`. This wrapper resolves the binary,
 * runs it with an `--emit-*` flag over a `.sysml` file, and captures stdout,
 * stderr, and the exit code so diagnostics are surfaced rather than swallowed.
 */

#pragma once

#include <string>

#include "BLI_string_ref.hh"

namespace blender::nodes::sysml {

/** Outcome of an `sml2c` invocation. */
struct Sml2cResult {
  /** True when sml2c ran and exited 0. */
  bool ok = false;
  /** Captured stdout: the emitted artifact (JSON for `--emit-json`, canonical
   * `.sysml` for `--emit-sysml`). */
  std::string output;
  /** Captured stderr: sml2c's diagnostics/warnings (surfaced even on success). */
  std::string diagnostics;
  /** Process exit code, or -1 if the process could not be launched. */
  int exit_code = -1;
  /** Bridge-level error (binary not found, launch failure, …); empty when the
   * binary ran, even if it exited non-zero. */
  std::string error;
};

/**
 * Resolve the bundled `sml2c` binary. Lookup order:
 *   1. the `SML2C` environment variable (absolute path), then
 *   2. `<blender program dir>/sml2c[.exe]` — where the build's install step
 *      copies it, mirroring how Blender ships runtime library dependencies
 *      next to the executable (build-time it lives under `extern/sml2c/`, the
 *      pinned/fetched analog of Blender's `lib/<platform>` LIBDIR).
 * Returns an empty string if none exists (the caller reports the tried paths).
 */
std::string sml2c_binary_path();

/**
 * Run `sml2c <emit_flag> <sysml_path>`, capturing stdout, stderr, and exit code.
 * `emit_flag` is the literal CLI flag, e.g. "--emit-json".
 */
Sml2cResult sml2c_run(StringRefNull emit_flag, StringRefNull sysml_path);

/** `sml2c --emit-json <path>` — validated AST JSON on `output`. */
inline Sml2cResult run_emit_json(StringRefNull sysml_path)
{
  return sml2c_run("--emit-json", sysml_path);
}

/** `sml2c --emit-sysml <path>` — canonical round-trip `.sysml` on `output`. */
inline Sml2cResult run_emit_sysml(StringRefNull sysml_path)
{
  return sml2c_run("--emit-sysml", sysml_path);
}

}  // namespace blender::nodes::sysml
