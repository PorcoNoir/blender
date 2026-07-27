# Publishing `bpy` to Artifactory for Databricks

This fork's Blender can be consumed from Databricks notebooks as the
`bpy` Python module (Blender-as-a-library, headless). The pipeline is the
same as the other SML utilities — build a wheel, push it to the Artifactory
PyPI repository, let the Databricks Asset Bundle (sml2c repo, `databricks/`)
install it on job clusters.

## 1. Build the module

```sh
make bpy            # or: make bpy release
```

This configures with `build_files/cmake/config/bpy_module.cmake` into a
separate `../build_<platform>_bpy` tree and produces the importable `bpy/`
package in its `bin/` directory.

**Match the target Python.** The bpy extension links against a specific
CPython minor version. Databricks Runtime 15.4 LTS runs Python 3.11,
DBR 16.x runs 3.12 — build with the same interpreter as the DBR you deploy
to (the bundle's `spark_version` variable), and rebuild when it bumps.
Build on a glibc no newer than the runtime's (recent Ubuntu LTS is safe).

## 2. Package + upload

```sh
ARTIFACTORY_URL=https://mycompany.jfrog.io/artifactory \
ARTIFACTORY_PYPI_REPO=sml-pypi-local \
ARTIFACTORY_USER=me ARTIFACTORY_TOKEN=... \
build_files/utils/publish_bpy_artifactory.sh ../build_linux_bpy/bin
```

The script wraps the standard `build_files/utils/make_bpy_wheel.py`
packaging and uploads with twine. Expect a large wheel (hundreds of MB);
Artifactory handles it, but first installs on a cluster take a while —
prefer job clusters with the library pinned over ad-hoc `%pip install`.

## 3. Use from a notebook

```python
import bpy

bpy.ops.wm.read_factory_settings(use_empty=True)
# ... import geometry, run modifiers/exporters, emit rows for Spark ...
print(bpy.app.version_string)
```

`bpy` runs headless (no GPU/display needed) on standard CPU nodes. The
sample notebook and the job wiring — including how pip authenticates to
Artifactory via a secret scope + cluster init script — live in the sml2c
repo under `databricks/` (see its README).
