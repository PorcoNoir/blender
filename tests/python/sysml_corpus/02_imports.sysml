// Verifies imports — both wildcard and specific, with and without
// visibility modifiers.
package WithImports {
    public import KerML::Element;
    private import ScalarValues::*;
    import OuterPackage::Inner;
    part def Stub;
}
