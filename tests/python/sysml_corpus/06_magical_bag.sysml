// The "MagicalBag" example — exercises the broad surface: package,
// imports, definitions, usages, specialization, redefinition,
// short names, long names, multiplicity, nested elements.
package MagicalBag {
    private import BaseComponents::*;

    part def CargoBay :> BaseComponents::CargoBay {
        item payload [0..1] : BottomlessGiftBag;
    }

    item def BottomlessGiftBag {
        attribute capacity;
    }

    interface def BatteryConnection {
        end ports : PowerOutPort [1];
    }

    port def PowerOutPort;
}
