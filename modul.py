
class RES_Asset:
    def __init__(
            self,
            Pnom_MW
    ):
        self.Pnom_MW = Pnom_MW

class Grid:
    def __init__(
            self,
            country,
            ci_gCO2pMJ,
            renewable_share
    ):
        self.country = country
        self.ci_gCO2pMJ = ci_gCO2pMJ
        self.ci_gCO2pkWh = ci_gCO2pMJ * 3.6
        self.renewable_share = renewable_share

class BESS:
    def __init__(
            self,
            capacity_MWh,
            Pnom_MW,
            SOC_t0,
            min_SOC,
            flex_use,
            charge_eff,
            discharge_eff,
            degradation_eff,
            degradation_capacity

    ):
        self.capacity_MWh = capacity_MWh
        self.Pnom_MW = Pnom_MW
        self.SOC_t0 = SOC_t0
        self.min_SOC = min_SOC
        self.flex_use = flex_use
        self.charge_eff = charge_eff
        self.discharge_eff = discharge_eff
        self.degradation_eff = degradation_eff
        self.degradation_capacity = degradation_capacity

class H2Storage:
    def __init__(
            self,
            capacity_tH2,
            SOC_t0,
            min_SOC,
            flex_use,
            ci_max_gCO2pMJ
    ):
        self.capacity_tH2 = capacity_tH2
        self.SOC_t0 = SOC_t0
        self.min_SOC = min_SOC
        self.flex_use = flex_use
        self.ci_max_gCO2pMJ = ci_max_gCO2pMJ

class Electrolysis:
    def __init__(
            self,
            capacity_MW,
            specific_el_MWhptH2,
            min_Load,
            degradation_specific_el
    ):
        self.capacity_MW = capacity_MW
        self.specific_el_MWhptH2 = specific_el_MWhptH2
        self.min_Load = min_Load
        self.degradation_specific_el = degradation_specific_el

class HaberBosch:
    def __init__(
            self,
            capacity_tNH3ph,
            specific_el_MWhptNH3,
            specific_H2_tH2ptNH3,
            min_Load,
            restart_delay_h
    ):
        self.capacity_tNH3ph = capacity_tNH3ph
        self.specific_el_MWhptNH3 = specific_el_MWhptNH3
        self.specific_H2_tH2ptNH3 = specific_H2_tH2ptNH3
        self.min_Load = min_Load
        self.restart_delay_h = restart_delay_h

class Compressor:
    def __init__(
            self,
            specific_el_MWhptH2
    ):
        self.specific_el_MWhptH2 = specific_el_MWhptH2