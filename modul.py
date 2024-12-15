
class RES_Asset: # wahnsinnsklasse
    def __init__(
            self,
            Pnom_MW
    ):
        self.Pnom_MW = Pnom_MW

class BESS:
    def __init__(
            self,
            capacity_MWh,
            Pnom_MW,
            SOC_t0,
            flex_use,
            DoD,
            charge_eff,
            discharge_eff
    ):
        self.capacity_MWh = capacity_MWh
        self.Pnom_MW = Pnom_MW
        self.SOC_t0 = SOC_t0
        self.flex_use = flex_use
        self.DoD = DoD
        self.charge_eff = charge_eff
        self.discharge_eff = discharge_eff
        self.capacity_eff_MWh = capacity_MWh * DoD

class H2Storage:
    def __init__(
            self,
            capacity_tH2,
            SOC_t0,
            flex_use
    ):
        self.capacity_tH2 = capacity_tH2
        self.SOC_t0 = SOC_t0
        self.flex_use = flex_use

class Electrolysis:
    def __init__(
            self,
            capacity_MW,
            specific_el_MWhptH2,
            min_Load
    ):
        self.capacity_MW = capacity_MW
        self.specific_el_MWhptH2 = specific_el_MWhptH2
        self.min_Load = min_Load

class HaberBosch:
    def __init__(
            self,
            capacity_tNH3ph,
            specific_el_MWhptNH3,
            specific_H2_tH2ptNH3,
            min_Load,
            P_standby_MW
    ):
        self.capacity_tNH3ph = capacity_tNH3ph
        self.specific_el_MWhptNH3 = specific_el_MWhptNH3
        self.specific_H2_tH2ptNH3 = specific_H2_tH2ptNH3
        self.min_Load = min_Load
        self.P_standby_MW = P_standby_MW