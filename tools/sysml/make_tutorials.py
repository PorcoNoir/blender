# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""Generate Blender-SML tutorial .blend files (BSML5 / SCRUM-678).

Headless generator — run inside Blender:

    blender --background --factory-startup --python tools/sysml/make_tutorials.py -- <out_dir>

Each tutorial builds a small SysML node graph and applies one part of the
pipeline, then saves a .blend the user can open and explore. Graphs are built
directly (no sml2c), so generation is deterministic and needs no binary:

    01_model       a structural model (parts, typing, containment)
    02_validation  a seeded defect, validated -> node diagnostics
    03_geometry    a shape part, materialised to a mesh object
    04_animation   a bone chain, rigged into an armature
    05_library     an attribute typed from the standard-library browser

The companion user guide is docs/BLENDER_SML_GUIDE.md.
"""

import os
import sys

import bpy

from bl_ui import sysml_validate, sysml_library, sysml_geometry, sysml_methodology
from bl_ui.sysml_geometry import SHAPE_KEY, DIM_PREFIX
from bl_ui.sysml_units import UNIT_KEY

TREE_IDNAME = "SysMLNodeTree"


def _tree(name):
    return bpy.data.node_groups.new(name, TREE_IDNAME)


def _t_model():
    tree = _tree("Car")
    car = tree.nodes.new("SysMLNodePartDef"); car.element_name = "Car"
    engine_def = tree.nodes.new("SysMLNodePartDef"); engine_def.element_name = "Engine"
    engine = tree.nodes.new("SysMLNodePartUsage"); engine.element_name = "engine"
    tree.links.new(engine_def.outputs["Self"], engine.inputs["Type"])   # engine : Engine
    tree.links.new(engine.outputs["Self"], car.inputs["Members"])       # Car owns engine


def _t_validation():
    tree = _tree("Validation")
    base = tree.nodes.new("SysMLNodePartDef")
    base.element_name = "AbstractBase"
    base.is_abstract = True
    usage = tree.nodes.new("SysMLNodePartUsage")
    usage.element_name = "usage"
    tree.links.new(base.outputs["Self"], usage.inputs["Type"])  # instantiates abstract -> B4001
    sysml_validate.validate_tree(tree)


def _t_geometry():
    tree = _tree("Geometry")
    body = tree.nodes.new("SysMLNodePartUsage")
    body.element_name = "Body"
    body[SHAPE_KEY] = "Cuboid"
    body[UNIT_KEY] = "mm"
    body[DIM_PREFIX + "length"] = 4800.0
    body[DIM_PREFIX + "width"] = 1840.0
    body[DIM_PREFIX + "height"] = 1350.0
    sysml_geometry.materialize_tree(tree)


def _t_animation():
    tree = _tree("Skeleton")
    sysml_methodology.add_bone_chain(tree, count=3, length=1.0)


def _t_library():
    tree = _tree("Library")
    sysml_library.insert_library_element(tree, "ISQ", "LengthValue", "length")


TUTORIALS = [
    ("01_model", _t_model),
    ("02_validation", _t_validation),
    ("03_geometry", _t_geometry),
    ("04_animation", _t_animation),
    ("05_library", _t_library),
]


def build_tutorials(out_dir):
    """Build every tutorial .blend into `out_dir`. Returns the list of paths."""
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for name, build in TUTORIALS:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        build()
        path = os.path.join(out_dir, name + ".blend")
        bpy.ops.wm.save_as_mainfile(filepath=path)
        paths.append(path)
    return paths


def _out_dir():
    if "--" in sys.argv:
        rest = sys.argv[sys.argv.index("--") + 1:]
        if rest:
            return rest[0]
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "tutorials")


if __name__ == "__main__":
    out = _out_dir()
    written = build_tutorials(out)
    print("wrote {} tutorial .blend files to {}".format(len(written), out))
