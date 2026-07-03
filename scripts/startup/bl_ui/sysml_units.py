# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later

"""ISQ length units <-> Blender scene units (Geometry Binding A / SCRUM-629).

SysML quantity values carry a unit (`4800 [mm]`); Blender lengths are in Blender
units, which map to metres scaled by ``scene.unit_settings.scale_length``. This
module converts between the two on materialize (SysML -> Blender) and reverse
(Blender -> SysML), so a `4800 [mm]` part is a real 4.8 m object and comes back
as 4800 mm.

The unit a shape's dimensions are expressed in is carried on the node as the
`sysml_unit` custom property (defaults to metres when absent).
"""

UNIT_KEY = "sysml_unit"
DEFAULT_UNIT = "m"

# Length unit -> metres.
UNIT_TO_METRES = {
    "m": 1.0,
    "mm": 0.001,
    "cm": 0.01,
    "dm": 0.1,
    "km": 1000.0,
    "um": 1e-6,
    "µm": 1e-6,
    "nm": 1e-9,
    "in": 0.0254,
    "ft": 0.3048,
    "yd": 0.9144,
    "mi": 1609.344,
}


def unit_factor(unit):
    """Metres per one `unit` (unknown units are treated as metres)."""
    return UNIT_TO_METRES.get((unit or DEFAULT_UNIT).strip(), 1.0)


def scale_length(scene):
    """Metres per Blender unit for `scene` (1.0 when unavailable)."""
    try:
        return scene.unit_settings.scale_length or 1.0
    except AttributeError:
        return 1.0


def to_blender_length(value, unit, scene=None):
    """A SysML length `value` in `unit` -> Blender units for `scene`."""
    metres = float(value) * unit_factor(unit)
    return metres / scale_length(scene) if scene is not None else metres


def from_blender_length(blender_units, unit, scene=None):
    """A Blender-unit length -> a SysML length value expressed in `unit`."""
    metres = float(blender_units) * (scale_length(scene) if scene is not None else 1.0)
    return metres / unit_factor(unit)
