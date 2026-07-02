// Verifies multiplicity preservation. The converter stores
// multiplicity on the usage's `multiplicity` field as a textual
// form ("0..1", "1..*", "*", "4").
package WithMultiplicity {
    item def Wheel;

    part def Bicycle {
        item wheels : Wheel [2];
    }
    part def Truck {
        item wheels : Wheel [4..18];
        item trailer : Wheel [0..*];
    }
}
