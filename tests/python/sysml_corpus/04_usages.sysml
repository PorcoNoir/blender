// Verifies usages and their typing relationship (`:`). Each usage
// should appear as a child of its enclosing definition with a
// `type` field naming the typing target.
package WithUsages {
    item def Wheel;
    item def Engine;

    part def Car {
        item wheels : Wheel;
        item engine : Engine;
        attribute mass;
    }
}
