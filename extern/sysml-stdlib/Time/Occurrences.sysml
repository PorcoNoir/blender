standard library package Occurrences {
	/*
	 * Blender-SML minimal, parseable subset of the SysML v2 Kernel Semantic
	 * Library `Occurrences`, for the Animation Binding (SCRUM-644). An
	 * Occurrence is something that happens over space and time; its `snapshots`
	 * are instantaneous states and its `timeSlices` are portions over an
	 * interval. The full library uses `portion` / `inverse` / constraint syntax
	 * the pinned sml2c cannot parse, so this ships only what the animation
	 * binding needs (snapshots -> keyframes, timeSlices -> action ranges). Keep
	 * every definition parseable: no `portion`, `inverse`, `bind`, or `assert`.
	 */

	abstract item def Occurrence {
		/* Instantaneous states of this occurrence -> keyframes. */
		item snapshots : Occurrence [0..*];
		/* Portions of this occurrence over an interval -> action / NLA ranges. */
		item timeSlices : Occurrence [0..*];
	}

	/* An occurrence at a single time instant. */
	item def Snapshot :> Occurrence;

	/* A portion of an occurrence over a time interval. */
	item def TimeSlice :> Occurrence;
}
