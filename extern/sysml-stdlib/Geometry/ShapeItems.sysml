standard library package ShapeItems {
	/*
	 * Blender-SML minimal, parseable subset of the OMG SysML v2 Geometry
	 * Domain Library `ShapeItems`. The full standard-library file uses
	 * connector/constraint syntax the pinned sml2c cannot parse, so this ships
	 * only the solid starter set the geometry binding maps to Blender mesh
	 * primitives (SCRUM-624). Keep every definition parseable by the pinned
	 * sml2c — no `bind`, `assert`, or constraint expressions.
	 */

	abstract item def Shape;

	/* Rectangular box: length x width x height -> Blender cube. */
	item def Cuboid :> Shape {
		attribute length;
		attribute width;
		attribute height;
	}

	item def Box :> Cuboid;
	item def RectangularCuboid :> Cuboid;

	/* Sphere of the given radius -> Blender UV sphere. */
	item def Sphere :> Shape {
		attribute radius;
	}

	/* Right circular cylinder -> Blender cylinder. */
	item def Cylinder :> Shape {
		attribute radius;
		attribute height;
	}

	/* Right circular cone -> Blender cone. */
	item def Cone :> Shape {
		attribute radius;
		attribute height;
	}

	/* Torus of major/minor radius -> Blender torus. */
	item def Torus :> Shape {
		attribute majorRadius;
		attribute minorRadius;
	}
}
