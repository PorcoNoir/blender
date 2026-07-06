standard library package Time {
	/*
	 * Blender-SML minimal, parseable subset of the SysML v2 Domain Library
	 * `Time`, for the Animation Binding (SCRUM-644). A Clock provides a
	 * currentTime as a TimeInstant that advances over its lifetime; the
	 * animation binding maps a snapshot's clock time to a Blender frame via the
	 * time↔frame bridge (SCRUM-645). Trimmed to what the binding needs; keep
	 * every definition parseable by the pinned sml2c.
	 */

	/* A point in time (a TimeInstantValue in the full library). */
	attribute def TimeInstant;

	/* Provides a currentTime that advances monotonically. */
	part def Clock {
		attribute currentTime : TimeInstant;
	}
}
