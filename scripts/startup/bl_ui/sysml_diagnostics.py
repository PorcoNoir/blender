# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""sml2c diagnostics bridge (BSML4 / SCRUM-662).

Run sml2c over a SysML model and turn its authoritative output into structured
findings. sml2c reports diagnostics as one line per finding on stderr:

    <file>:<line>[:<col>]: <severity>: [<CODE>] <message>

e.g. ``model.sysml:2: error: [E0200] Undefined name 'Missing'.`` (exit 65 when
any error is present). This module parses those into dicts and exposes the model
status; mapping findings onto nodes / the text surface is a later story.

sml2c is located the same way the native bridge does (the ``SML2C`` env var, else
next to the Blender binary); resolution runs against the bundled stdlib when it
is installed alongside. With no sml2c present the functions return no findings,
so callers can soft-skip.
"""

import os
import re
import subprocess
import tempfile

import bpy

# <file>:<line>[:<col>]: <severity>: [<CODE>] <message>
# `file` is non-greedy so a Windows drive prefix ("C:/...") isn't mistaken for
# the line separator (the ":<digits>:" only matches the real line number).
_DIAG_RE = re.compile(
    r"^(?P<file>.*?):(?P<line>\d+)(?::(?P<col>\d+))?:\s*"
    r"(?P<severity>error|warning|note):\s*"
    r"(?:\[(?P<code>\w+)\]\s*)?(?P<message>.*)$"
)


def sml2c_binary_path():
    """Path to the sml2c binary, or None (SML2C env, else next to blender)."""
    env = os.environ.get("SML2C")
    if env and os.path.exists(env):
        return env
    program_dir = os.path.dirname(bpy.app.binary_path or "")
    for name in ("sml2c.exe", "sml2c"):
        candidate = os.path.join(program_dir, name)
        if os.path.exists(candidate):
            return candidate
    return None


def available():
    """True when an sml2c binary can be resolved."""
    return sml2c_binary_path() is not None


def _stdlib_args():
    program_dir = os.path.dirname(bpy.app.binary_path or "")
    stdlib = os.path.join(program_dir, "sysml-stdlib")
    return ["--stdlib-path", stdlib] if os.path.isdir(stdlib) else []


def parse_diagnostics(stderr):
    """Parse sml2c stderr into a list of finding dicts.

    Each finding: {severity, code, line, col, message, file}. Lines that are not
    diagnostics (summaries, blank lines) are ignored. Pure — no sml2c needed.
    """
    findings = []
    for raw in stderr.splitlines():
        match = _DIAG_RE.match(raw.strip())
        if match is None:
            continue
        findings.append({
            "severity": match.group("severity"),
            "code": match.group("code") or "",
            "line": int(match.group("line")),
            "col": int(match.group("col")) if match.group("col") else None,
            "message": match.group("message").strip(),
            "file": match.group("file"),
        })
    return findings


def diagnose_file(path):
    """Findings for a `.sysml` file. Empty list when sml2c is unavailable."""
    sml2c = sml2c_binary_path()
    if sml2c is None:
        return []
    proc = subprocess.run(
        [sml2c, "--emit-json", *_stdlib_args(), path],
        capture_output=True, text=True,
    )
    return parse_diagnostics(proc.stderr)


def diagnose_text(text):
    """Findings for a SysML source string (written to a temp file for sml2c)."""
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "model.sysml")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return diagnose_file(path)


def has_errors(findings):
    """True when any finding is error severity (the model does not resolve)."""
    return any(f["severity"] == "error" for f in findings)
