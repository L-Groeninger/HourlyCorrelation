#################################################################################################################
# plant_init() takes in **kwargs for all technical, economic and regulatory plant variables that describe a plant
# configuration and returns them in a dictionary.
# plant_init() also stores default values for each variable in case no **kwargs are called/defined.
#################################################################################################################

def plant_init(
        # RES Assets
        RES_Asset_Wind_Pnom_MW=150,
        RES_Asset_Wind_PPA_price_EURpMWh = 75,
        RES_Asset_PV_Pnom_MW=50,
        RES_Asset_PV_PPA_price_EURpMWh = 55,

        # Grid
        Grid_country="XX",
        Grid_ci_gCO2pMJ=114,
        Grid_renewable_share=0.55,

        # Battery Energy Storage System (BESS)
        BESS_capacity_MWh=0,
        BESS_Pnom_MW=30,
        BESS_SOC_t0=0,
        BESS_min_SOC=0.5,
        BESS_flex_use=0.3,
        BESS_charge_eff=0.97,
        BESS_discharge_eff=0.97,
        BESS_degradation_eff=0.01,
        BESS_degradation_capacity=0.01,
        BESS_specific_cost_EURpMWh = 350000,
        BESS_specific_replacement_cost_EURpMWh=150000,

        # H2 Storage
        H2Storage_capacity_tH2=0,
        H2Storage_SOC_t0=0,
        H2Storage_min_SOC=0.3,
        H2Storage_flex_use=0.2,
        H2Storage_ci_max_gCO2pMJ=5,
        H2Storage_specific_cost_EURptH2=2000000,

        # Compressor
        Compressor_specific_el_MWhptH2=2,

        # Electrolysis
        Electrolysis_capacity_MW=100,
        Electrolysis_specific_el_MWhptH2=55,
        Electrolysis_min_Load=0.10,
        Electrolysis_degradation_specific_el=0.01,
        Electrolysis_specific_cost_EURpMW=2000000,
        Electrolysis_specific_replacement_cost_EURpMW=1000000,

        # Haber-Bosch
        HaberBosch_capacity_tNH3ph=7.5,
        HaberBosch_specific_el_MWhptNH3=0.33,
        HaberBosch_specific_H2_tH2ptNH3=0.18,
        HaberBosch_min_Load=0.4,
        HaberBosch_restart_delay_h=10,
        HaberBosch_specific_cost_EURptNH3ph=10000000,

        # Economic & System variables/constants
        ci_max_gCO2pMJ=28.2,
        ci_others_gCO2pMJ=6.0,
        energy_density_NH3_MJpkgNH3=18.8,
        energy_density_H2_MJpkgH2=120,
        WACC=0.08,
        CPI=0.02,
        construction_phase_a=2,
        grid_el_price_EURpMWh=150,
        RES_Surplus_sales_price_EURpMWh=0,
        O_M_CapEx_share=0.02

):
    plant_config = {
        'RES_Asset_Wind': {
            'Pnom_MW': {
                'value': RES_Asset_Wind_Pnom_MW,
                'unit': 'MW'
            },
            'PPA_price_EURpMWh': {
                'value': RES_Asset_Wind_PPA_price_EURpMWh,
                'unit': 'EUR/MWh'
            }
        },
        'RES_Asset_PV': {
            'Pnom_MW': {
                'value': RES_Asset_PV_Pnom_MW,
                'unit': 'MW'
            },
            'PPA_price_EURpMWh': {
                'value': RES_Asset_PV_PPA_price_EURpMWh,
                'unit': 'EUR/MWh'
            }
        },
        'Grid': {
            'country': {
                'value': Grid_country,
                'unit': ''
            },
            'ci_gCO2pMJ': {
                'value': Grid_ci_gCO2pMJ,
                'unit': 'gCO2/MJ'
            },
            'renewable_share': {
                'value': Grid_renewable_share,
                'unit': '* 100 = %'
            }
        },
        'BESS': {
            'capacity_MWh': {
                'value': BESS_capacity_MWh,
                'unit': 'MWh'
            },
            'Pnom_MW': {
                'value': BESS_Pnom_MW,
                'unit': 'MW'
            },
            'SOC_t0': {
                'value': BESS_SOC_t0,
                'unit': '* 100 = %'
            },
            'min_SOC': {
                'value': BESS_min_SOC,
                'unit': '* 100 = %'
            },
            'flex_use': {
                'value': BESS_flex_use,
                'unit': '* 100 = %'
            },
            'charge_eff': {
                'value': BESS_charge_eff,
                'unit': '* 100 = %'
            },
            'discharge_eff': {
                'value': BESS_discharge_eff,
                'unit': '* 100 = %'
            },
            'degradation_eff': {
                'value': BESS_degradation_eff,
                'unit': '* 100 = % per year'
            },
            'degradation_capacity': {
                'value': BESS_degradation_capacity,
                'unit': '* 100 = % per year'
            },
            'specific_cost_EURpMWh': {
                'value': BESS_specific_cost_EURpMWh,
                'unit': 'EUR/MWh'
            },
            'specific_replacement_cost_EURpMWh': {
                'value': BESS_specific_replacement_cost_EURpMWh,
                'unit': 'EUR/MWh'
            }
        },
        'H2Storage': {
            'capacity_tH2': {
                'value': H2Storage_capacity_tH2,
                'unit': 'tH2'
            },
            'SOC_t0': {
                'value': H2Storage_SOC_t0,
                'unit': '* 100 = %'
            },
            'min_SOC': {
                'value': H2Storage_min_SOC,
                'unit': '* 100 = %'
            },
            'flex_use': {
                'value': H2Storage_flex_use,
                'unit': '* 100 = %'
            },
            'ci_max_gCO2pMJ': {
                'value': H2Storage_ci_max_gCO2pMJ,
                'unit': 'gCO2/MJ'
            },
            'specific_cost_EURptH2': {
                'value': H2Storage_specific_cost_EURptH2,
                'unit': 'EUR/tH2'
            },
        },
        'Compressor': {
            'specific_el_MWhptH2': {
                'value': Compressor_specific_el_MWhptH2,
                'unit': 'MWh/tH2'
            }
        },
        'Electrolysis': {
            'capacity_MW': {
                'value': Electrolysis_capacity_MW,
                'unit': 'MW'
            },
            'specific_el_MWhptH2': {
                'value': Electrolysis_specific_el_MWhptH2,
                'unit': 'MWh/tH2'
            },
            'min_Load': {
                'value': Electrolysis_min_Load,
                'unit': '* 100 = %'
            },
            'degradation_specific_el': {
                'value': Electrolysis_degradation_specific_el,
                'unit': '* 100 = % per year'
            },
            'specific_cost_EURpMW': {
                'value': Electrolysis_specific_cost_EURpMW,
                'unit': 'EUR/MW'
            },
            'specific_replacement_cost_EURpMW': {
                'value': Electrolysis_specific_replacement_cost_EURpMW,
                'unit': 'EUR/MW'
            }
        },
        'HaberBosch': {
            'capacity_tNH3ph': {
                'value': HaberBosch_capacity_tNH3ph,
                'unit': 'tNH3/h'
            },
            'specific_el_MWhptNH3': {
                'value': HaberBosch_specific_el_MWhptNH3,
                'unit': 'MWh/tNH3'
            },
            'specific_H2_tH2ptNH3': {
                'value': HaberBosch_specific_H2_tH2ptNH3,
                'unit': 'tH2/tNH3'
            },
            'min_Load': {
                'value': HaberBosch_min_Load,
                'unit': '* 100 = %'
            },
            'restart_delay_h': {
                'value': HaberBosch_restart_delay_h,
                'unit': 'h'
            },
            'specific_cost_EURptNH3ph': {
                'value': HaberBosch_specific_cost_EURptNH3ph,
                'unit': 'EUR/(tNH3/h)'
            }
        },
        'Economic_System': {
            'ci_max_gCO2pMJ': {
                'value': ci_max_gCO2pMJ,
                'unit': 'gCO2/MJ'
            },
            'ci_others_gCO2pMJ': {
                'value': ci_others_gCO2pMJ,
                'unit': 'gCO2/MJ'
            },
            'energy_density_NH3_MJpkgNH3': {
                'value': energy_density_NH3_MJpkgNH3,
                'unit': 'MJ/kgNH3'
            },
            'energy_density_H2_MJpkgH2': {
                'value': energy_density_H2_MJpkgH2,
                'unit': 'MJ/kgH2'
            },
            'WACC': {
                'value': WACC,
                'unit': '* 100 = %'
            },
            'CPI': {
                'value': CPI,
                'unit': '* 100 = %'
            },
            'construction_phase_a': {
                'value': construction_phase_a,
                'unit': 'years'
            },
            'grid_el_price_EURpMWh': {
                'value': grid_el_price_EURpMWh,
                'unit': 'EUR/MWh'
            },
            'RES_surplus_sales_price': {
                'value': RES_Surplus_sales_price_EURpMWh,
                'unit': 'EUR/MWh'
            },
            'O_M_CapEx_share': {
                'value': O_M_CapEx_share,
                'unit': '* 100 = % of total CapEx'
            }
        }
    }

    return plant_config