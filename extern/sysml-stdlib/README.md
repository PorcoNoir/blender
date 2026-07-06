# Bundled SysML standard library (minimal)

A **minimal, parseable** subset of the OMG SysML v2 Geometry Domain Library,
shipped with Blender-SML and passed to `sml2c` as `--stdlib-path` by the import
bridge so that parts which specialize `SpatialItem` or type a `shape` resolve
against real library definitions (SCRUM-624).

## Why a subset?

The pinned `sml2c` (0.45.4-alpha) cannot parse the full standard-library
`Geometry/ShapeItems.sysml` — it uses `bind` connectors, `assert` constraints,
and expression syntax the compiler does not yet accept. So this bundle carries a
hand-trimmed, parseable version limited to the **solid starter set** the geometry
binding maps to Blender mesh primitives:

| Shape | Blender primitive |
| --- | --- |
| `Cuboid` / `Box` / `RectangularCuboid` | cube |
| `Sphere` | UV sphere |
| `Cylinder` | cylinder |
| `Cone` | cone |
| `Torus` | torus |

`SpatialItems` carries only `SpatialItem { item shape : Shape; }`. Both grow as
later geometry-binding stories need more (coordinate frames, CSG, etc.).

`Time/` adds the temporal subset the **animation binding** needs (SCRUM-644): a
parseable `Occurrences` (`Occurrence` with `snapshots` / `timeSlices`, `Snapshot`,
`TimeSlice`) and `Time` (`Clock` with `currentTime : TimeInstant`). The full
`Occurrences.kerml` uses `portion`/`inverse`/constraint syntax the pinned sml2c
cannot parse. Snapshots map to Blender keyframes; timeSlices to action/NLA ranges.

## Layout & install

```
extern/sysml-stdlib/
  Geometry/ShapeItems.sysml
  Geometry/SpatialItems.sysml
  VERSION
```

Installed next to the Blender executable as `sysml-stdlib/` (mirroring how the
`sml2c` binary is installed). The bridge resolves it via `$SML2C_STDLIB`, then
`<program dir>/sysml-stdlib`.

Keep every definition parseable by the pinned `sml2c`: no `bind`, `assert`, or
constraint expressions.
