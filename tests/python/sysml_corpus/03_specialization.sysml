// Verifies `:>` (specialization) is captured on definitions. The
// converter generates one LibraryRef node per qualified-name target
// and wires it into the `specializes` slot.
package WithSpecialization {
    part def Vehicle;
    part def Car :> Vehicle;
    // Multiple supertypes
    part def Sedan :> Car, Vehicle;
}
