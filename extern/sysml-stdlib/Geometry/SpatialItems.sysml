standard library package SpatialItems {
	/*
	 * Blender-SML minimal, parseable subset of the OMG SysML v2 Geometry
	 * Domain Library `SpatialItems`. A SpatialItem is a part with a spatial
	 * extent (a `shape`); the geometry binding materializes each SpatialItem as
	 * a Blender object (SCRUM-624). The full standard-library file pulls in the
	 * measurement / coordinate-frame machinery the pinned sml2c cannot parse;
	 * this keeps just what parts specialize.
	 */

	private import ShapeItems::Shape;

	item def SpatialItem {
		/* The geometric shape of this item; empty for a shapeless grouping. */
		item shape : Shape [0..1];
	}
}
