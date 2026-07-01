// Element-kind probe for the SML Graph regen tool (0.24.0+).
//
// The regen tool runs `sml2c --emit-json` on this file and harvests
// the distinct (defKind, kind) pairs sml2c reports. Each pair maps
// to one row in the generated element table.
//
// CONSERVATIVE PROBE: this file deliberately uses only SysML v2
// syntax forms confirmed to parse cleanly under the current
// bundled sml2c. Kinds that need compound keywords sml2c doesn't
// yet accept (`case def`, `analysis case def`, `verification case
// def`, `use case def`) are NOT exercised by this probe — they
// fall back to the regen tool's `PY_CLASS_OVERRIDES` mapping plus
// the editor's hardcoded `fallback.ts`, which keeps them in the
// merged element table even though they're not harvested from
// sml2c output.
//
// As sml2c grows acceptance for more keyword forms, additional
// probes can be added under tools/probes/ — the regen tool reads
// every `.sysml` file in that directory.
//
// Goal for 0.24.0: exercise enough kinds to validate the regen
// pipeline end-to-end. The 32-kind floor in regen-element-table.ts
// is below the count this probe should produce, so a partial probe
// still passes the floor check.

package SamplePackage {

    // ---- Specializable definitions ----
    // Each keyword followed by `def` and a name. `;` terminates
    // an empty body; `{ }` would too. Both forms parse.
    part def SamplePartDef;
    port def SamplePortDef;
    interface def SampleInterfaceDef;
    connection def SampleConnectionDef;
    flow def SampleFlowDef;
    allocation def SampleAllocationDef;
    item def SampleItemDef;
    action def SampleActionDef;
    state def SampleStateDef;
    calc def SampleCalcDef;
    constraint def SampleConstraintDef;
    requirement def SampleRequirementDef;
    concern def SampleConcernDef;
    view def SampleViewDef;
    viewpoint def SampleViewpointDef;
    rendering def SampleRenderingDef;
    metadata def SampleMetadataDef;
    occurrence def SampleOccurrenceDef;

    // ---- Non-specializable definitions ----
    attribute def SampleAttributeDef;
    enum def SampleEnumerationDef {
        UNO; DOS;
    }

    // ---- Usages (single-keyword forms, container by default) ----
    // Wrapped in a part def so they're syntactically valid as members.
    part def WithUsages {
        part         sample_part           : SamplePartDef { part nested_part : SamplePartDef; }
        attribute    sample_attribute      : SampleAttributeDef;
        port         sample_port           : SamplePortDef;
        item         sample_item           : SampleItemDef;
        connection   sample_connection     : SampleConnectionDef;
        interface    sample_interface      : SampleInterfaceDef;
        allocation   sample_allocation     : SampleAllocationDef;
        flow         sample_flow           : SampleFlowDef;
        action       sample_action         : SampleActionDef;
        state        sample_state          : SampleStateDef;
        calc         sample_calc           : SampleCalcDef;
        view         sample_view           : SampleViewDef;
    }

    // ---- Leaf usages (non-container) ----
    part def WithLeafUsages {
        enum            sample_enumeration_usage   : SampleEnumerationDef;
        constraint      sample_constraint_usage    : SampleConstraintDef;
        requirement     sample_requirement_usage   : SampleRequirementDef;
        concern         sample_concern_usage       : SampleConcernDef;
        viewpoint       sample_viewpoint_usage     : SampleViewpointDef;
        rendering       sample_rendering_usage     : SampleRenderingDef;
        metadata        sample_metadata_usage      : SampleMetadataDef;
        occurrence      sample_occurrence_usage    : SampleOccurrenceDef;
    }
}
