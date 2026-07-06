#!/usr/bin/env python3
"""Fetch the pinned sml2c binary into the (gitignored) extern/sml2c/bin/<os>/.

Pins live in extern/sml2c/sml2c.lock (version + per-platform SHA-256 of the
*binary*). The binaries are never committed to source — this script (run by a
developer, by CI, or by the release-packaging step) populates them on demand
from the sml2c GitHub release assets.

  python tools/sysml/fetch_sml2c.py                     # download the pinned release + verify
  python tools/sysml/fetch_sml2c.py --from-local PATH   # copy a locally-built sml2c + verify
  python tools/sysml/fetch_sml2c.py --check             # verify the already-present binary

Windows assets are .zip, linux/macos are .tar.gz; each archive holds the full
sml2c toolchain, and only the sml2c/sml2c.exe binary is extracted. Use
--from-local (pointing at a local sml2c build) only when working against an
unreleased build.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tarfile
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


def _download_asset(data: dict, entry: dict, dest_dir: Path) -> Path:
    """Fetch the release asset into `dest_dir`, returning its path.

    sml2c may be a private repo, so try the authenticated `gh` CLI first, then a
    token from the environment (GH_TOKEN / GITHUB_TOKEN), then an anonymous
    download (which works for a public repo).
    """
    asset, tag, repo = entry["asset"], data["release_tag"], data["source_repo"]
    out = dest_dir / asset

    if shutil.which("gh"):
        try:
            subprocess.run(
                ["gh", "release", "download", tag, "--repo", repo,
                 "--pattern", asset, "--dir", str(dest_dir), "--clobber"],
                check=True, capture_output=True, text=True)
            if out.exists():
                return out
        except subprocess.CalledProcessError:
            pass  # fall through to token / anonymous

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if token:
        rel = _api_json(
            f"https://api.github.com/repos/{repo}/releases/tags/{tag}", token)
        asset_id = next((a["id"] for a in (rel or {}).get("assets", [])
                         if a["name"] == asset), None)
        if asset_id is not None:
            req = urllib.request.Request(
                f"https://api.github.com/repos/{repo}/releases/assets/{asset_id}",
                headers={"Authorization": f"Bearer {token}",
                         "Accept": "application/octet-stream"})
            with urllib.request.urlopen(req) as resp, open(out, "wb") as fh:
                shutil.copyfileobj(resp, fh)
            return out

    url = f"https://github.com/{repo}/releases/download/{tag}/{asset}"
    urllib.request.urlretrieve(url, out)
    return out


def _api_json(url: str, token: str):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def _extract_binary(archive: Path, exe: str) -> bytes | None:
    """Read `exe` out of a .zip or .tar.gz archive by basename. None if absent."""
    name = archive.name.lower()
    if name.endswith((".tar.gz", ".tgz", ".tar")):
        with tarfile.open(archive) as tf:
            for member in tf.getmembers():
                if member.isfile() and member.name.rsplit("/", 1)[-1] == exe:
                    extracted = tf.extractfile(member)
                    if extracted is not None:
                        return extracted.read()
    else:
        with zipfile.ZipFile(archive) as z:
            for member in z.namelist():
                if member.rsplit("/", 1)[-1] == exe:
                    return z.read(member)
    return None


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
        sys.exit(f"No pinned sha256 for '{plat}' in {LOCK.name}. Record it, or use "
                 f"--from-local PATH against a local build.")
    print(f"Fetching {entry['asset']} from {data['source_repo']} "
          f"{data['release_tag']}", file=sys.stderr)
    with tempfile.TemporaryDirectory() as tmp:
        try:
            apath = _download_asset(data, entry, Path(tmp))
        except Exception as e:  # noqa: BLE001 - surface any download failure clearly
            sys.exit(f"download failed: {e}\n(Is {data['source_repo']} "
                     f"{data['release_tag']} accessible? For a private repo, "
                     f"authenticate `gh` or set GH_TOKEN.)")
        payload = _extract_binary(apath, entry["exe"])
        if payload is None:
            sys.exit(f"{entry['exe']} not found inside {entry['asset']}")
        target.write_bytes(payload)
    if plat != "windows":
        os.chmod(target, 0o755)
    verify(target, entry)


if __name__ == "__main__":
    main()
