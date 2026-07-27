#!/usr/bin/env bash
# Package the already-built bpy module as a wheel and upload it to an
# Artifactory PyPI repository via twine.
#
# Prerequisite: a completed `make bpy` (or `make bpy release`) build; pass
# its install dir (the directory that contains the `bpy/` package,
# e.g. ../build_linux_bpy/bin) as $1.
#
#   ARTIFACTORY_URL=https://mycompany.jfrog.io/artifactory \
#   ARTIFACTORY_PYPI_REPO=sml-pypi-local \
#   ARTIFACTORY_USER=me ARTIFACTORY_TOKEN=... \
#   build_files/utils/publish_bpy_artifactory.sh ../build_linux_bpy/bin
#
# NOTE: unlike rsml2py (abi3), the bpy wheel is CPython-version-specific —
# build with the same Python minor version as the target Databricks
# Runtime (DBR 15.4 = 3.11, DBR 16.x = 3.12) and republish on DBR bumps.
set -euo pipefail

INSTALL_DIR="${1:?usage: publish_bpy_artifactory.sh <bpy-install-dir>}"

: "${ARTIFACTORY_URL:?base URL, e.g. https://mycompany.jfrog.io/artifactory}"
: "${ARTIFACTORY_PYPI_REPO:?PyPI repository key, e.g. sml-pypi-local}"
: "${ARTIFACTORY_USER:?Artifactory user name}"
: "${ARTIFACTORY_TOKEN:?identity token (or API key)}"

SELF_DIR="$(cd "$(dirname "$0")" && pwd)"
WHEEL_DIR="$(mktemp -d)"
trap 'rm -rf "$WHEEL_DIR"' EXIT

python3 -m pip install --quiet twine
python3 "$SELF_DIR/make_bpy_wheel.py" "$INSTALL_DIR" --output-dir "$WHEEL_DIR"

python3 -m twine upload \
    --repository-url "$ARTIFACTORY_URL/api/pypi/$ARTIFACTORY_PYPI_REPO" \
    -u "$ARTIFACTORY_USER" -p "$ARTIFACTORY_TOKEN" \
    "$WHEEL_DIR"/bpy-*.whl
