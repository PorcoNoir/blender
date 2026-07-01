#!/usr/bin/env python3
"""Fetch the pinned sml2c binary into the (gitignored) extern/sml2c/bin/<os>/.

Pins live in extern/sml2c/sml2c.lock (version + per-platform SHA-256 of the
*binary*). The binaries are never committed to source — this script (run by a
developer, by CI, or by the release-packaging step) populates them on demand.

  python tools/sysml/fetch_sml2c.py                     # download the pinned release + verify
  python tools/sysml/fetch_sml2c.py --from-local PATH   # copy a locally-built sml2c + verify
  python tools/sysml/fetch_sml2c.py --check             # verify the already-present binary

Until the sml2c repo ships release binaries, use --from-local pointing at a
local sml2c build (e.g. M:/sysml-utils/sml2c/bin/sml2c.exe).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCK = REPO_ROOT / "extern" / "sml2c" / "sml2c.lock"


def platform_key() -> str:
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_lock():
    data = json.loads(LOCK.read_text(encoding="utf-8"))
    plat = platform_key()
    entry = data["platforms"].get(plat)
    if not entry:
        sys.exit(f"No sml2c pin for platform '{plat}' in {LOCK.name}.")
    target_dir = REPO_ROOT / "extern" / "sml2c" / "bin" / plat
    target = target_dir / entry["exe"]
    return data, plat, entry, target_dir, target


def verify(target: Path, entry: dict) -> None:
    want = entry.get("sha256", "")
    got = sha256(target)
    if not want:
        print(f"WARNING: no pinned sha256 for this platform; got {got}. "
              f"Record it in {LOCK.name}.", file=sys.stderr)
        return
    if got != want:
        sys.exit(f"sha256 mismatch for {target.name}:\n  want {want}\n  got  {got}")
    print(f"OK: {target} matches pin ({want[:12]}...).")


def main() -> None:
    ap = argparse.ArgumentParser(description="Fetch the pinned sml2c binary.")
    ap.add_argument("--from-local", metavar="PATH",
                    help="copy a locally-built sml2c instead of downloading")
    ap.add_argument("--check", action="store_true",
                    help="verify the already-present binary against the lock")
    args = ap.parse_args()

    data, plat, entry, target_dir, target = load_lock()
    target_dir.mkdir(parents=True, exist_ok=True)

    if args.check:
        if not target.exists():
            sys.exit(f"{target} not present — run fetch_sml2c.py first.")
        verify(target, entry)
        return

    if args.from_local:
        src = Path(args.from_local)
        if not src.exists():
            sys.exit(f"--from-local path not found: {src}")
        shutil.copy2(src, target)
        if plat != "windows":
            os.chmod(target, 0o755)
        verify(target, entry)
        return

    # Default: download the pinned release asset and extract the binary.
    if not entry.get("sha256"):
        sys.exit(f"No published sha256 for '{plat}' yet. Use --from-local PATH until sml2c "
                 f"ships release binaries (see the sml2c release-pipeline task).")
    url = (f"https://github.com/{data['source_repo']}/releases/download/"
           f"{data['release_tag']}/{entry['asset']}")
    print(f"Downloading {url}", file=sys.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        zpath = Path(tmp) / entry["asset"]
        try:
            urllib.request.urlretrieve(url, zpath)
        except Exception as e:  # noqa: BLE001 - surface any download failure clearly
            sys.exit(f"download failed: {e}\n(Has sml2c published {data['release_tag']}? "
                     f"See the sml2c release-pipeline task.)")
        with zipfile.ZipFile(zpath) as z:
            member = next((m for m in z.namelist() if m.endswith(entry["exe"])), None)
            if not member:
                sys.exit(f"{entry['exe']} not found inside {entry['asset']}")
            z.extract(member, tmp)
            shutil.copy2(Path(tmp) / member, target)
    if plat != "windows":
        os.chmod(target, 0o755)
    verify(target, entry)


if __name__ == "__main__":
    main()
