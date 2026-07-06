# SPDX-FileCopyrightText: 2026 Blender Authors
#
# SPDX-License-Identifier: GPL-2.0-or-later
#
# AUTO-GENERATED - DO NOT EDIT. Regenerate: python tools/sysml/gen_stdlib_index.py
#
# Catalog of resolvable SysML standard-library packages + types, by source
# (builtin = compiled into sml2c; bundled = shipped in extern/sysml-stdlib).
# Consumed by the in-editor library browser (sysml_library.py).

STDLIB_INDEX = [
    {"package": "ISQ", "source": "builtin", "types": ["DurationValue", "ForceValue", "LengthValue", "MassValue", "SpeedValue", "TemperatureValue"]},
    {"package": "Quantities", "source": "builtin", "types": ["AngleValue", "DurationValue", "LengthValue", "MassValue", "ScalarQuantityValue"]},
    {"package": "SI", "source": "builtin", "types": ["Unit", "kilogram", "metre", "second"]},
    {"package": "ScalarValues", "source": "builtin", "types": ["Boolean", "Integer", "Natural", "Number", "Real", "String"]},
    {"package": "Occurrences", "source": "bundled", "types": ["Occurrence", "Snapshot", "TimeSlice"]},
    {"package": "ShapeItems", "source": "bundled", "types": ["Box", "Cone", "Cuboid", "Cylinder", "RectangularCuboid", "Shape", "Sphere", "Torus"]},
    {"package": "SpatialItems", "source": "bundled", "types": ["SpatialItem"]},
    {"package": "Time", "source": "bundled", "types": ["Clock", "TimeInstant"]},
]
