
#################################################################################################################
# plant_calc() calculates the plant operation vor a pre defined plant setup and returns the entire time series in
# the df_out pandas dataframe. The parameter store_to_csv checks whether the results shall be stored to the
# out.csv file and is defaulted as False
#################################################################################################################


import pandas as pd
from datetime import datetime
from calendar import monthrange
from calendar import isleap
import modul

def plant_calc(plant_config):

    # Set up Modul Objects with plant parameters
    RES_Asset_Wind = modul.RES_Asset(
        Pnom_MW=plant_config['RES_Asset_Wind']['Pnom_MW']['value']
    )

    RES_Asset_PV = modul.RES_Asset(
        Pnom_MW=plant_config['RES_Asset_PV']['Pnom_MW']['value']
    )

    Grid = modul.Grid(
        country=plant_config['Grid']['country']['value'],
        ci_gCO2pMJ=plant_config['Grid']['ci_gCO2pMJ']['value'],
        renewable_share=plant_config['Grid']['renewable_share']['value']
    )

    BESS = modul.BESS(
        capacity_MWh=plant_config['BESS']['capacity_MWh']['value'],
        Pnom_MW=plant_config['BESS']['Pnom_MW']['value'],
        SOC_t0=plant_config['BESS']['SOC_t0']['value'],
        min_SOC=plant_config['BESS']['min_SOC']['value'],
        flex_use=plant_config['BESS']['flex_use']['value'],
        charge_eff=plant_config['BESS']['charge_eff']['value'],
        discharge_eff=plant_config['BESS']['discharge_eff']['value'],
        degradation_eff=plant_config['BESS']['degradation_eff']['value'],  # * 100 = % decrease of charge/discharge-eff per year
        degradation_capacity=plant_config['BESS']['degradation_capacity']['value']  # * 100 = % decrease of capacity per year
    )

    H2Storage = modul.H2Storage(
        capacity_tH2=plant_config['H2Storage']['capacity_tH2']['value'],
        SOC_t0=plant_config['H2Storage']['SOC_t0']['value'],
        min_SOC=plant_config['H2Storage']['min_SOC']['value'],
        flex_use=plant_config['H2Storage']['flex_use']['value'],
        ci_max_gCO2pMJ=plant_config['H2Storage']['ci_max_gCO2pMJ']['value']
    )

    Compressor = modul.Compressor(
        specific_el_MWhptH2=plant_config['Compressor']['specific_el_MWhptH2']['value']
    )

    Electrolysis = modul.Electrolysis(
        capacity_MW=plant_config['Electrolysis']['capacity_MW']['value'],
        specific_el_MWhptH2=plant_config['Electrolysis']['specific_el_MWhptH2']['value'],
        min_Load=plant_config['Electrolysis']['min_Load']['value'],
        degradation_specific_el=plant_config['Electrolysis']['degradation_specific_el']['value']
        # * 100 = % increase of specific el consumption per year
    )

    HaberBosch = modul.HaberBosch(
        capacity_tNH3ph=plant_config['HaberBosch']['capacity_tNH3ph']['value'],
        specific_el_MWhptNH3=plant_config['HaberBosch']['specific_el_MWhptNH3']['value'],
        specific_H2_tH2ptNH3=plant_config['HaberBosch']['specific_H2_tH2ptNH3']['value'],
        min_Load=plant_config['HaberBosch']['min_Load']['value'],
        restart_delay_h=plant_config['HaberBosch']['restart_delay_h']['value']
    )

    # Economic & System variables/constants
    ci_max_gCO2pMJ = plant_config['Economic_System']['ci_max_gCO2pMJ']['value']
    ci_others_gCO2pMJ = plant_config['Economic_System']['ci_others_gCO2pMJ']['value']
    ci_budget_gCO2pMJ = ci_max_gCO2pMJ - ci_others_gCO2pMJ
    energy_density_NH3_MJpkgNH3 = plant_config['Economic_System']['energy_density_NH3_MJpkgNH3']['value']
    energy_density_H2_MJpkgH2 = plant_config['Economic_System']['energy_density_H2_MJpkgH2']['value']

    # Read .csv RES Data to pd dataframe
    file_path_Wind = r'RES_Data/20241126_Run_5_Wind_DE-SH_10_years_2010-01-01_2020-12-31/TS_Multiyear_Wind_DE-SH_2010-01-01_2020-12-31.csv'
    df_Wind = pd.read_csv(file_path_Wind, names=['DateTimes', 'Wind_CF'], header=None, index_col='DateTimes',
                          skiprows=4)

    file_path_PV = r'RES_Data/20241126_Run_6_PV_DE-BY_10_years_2010-01-01_2020-12-31/TS_Multiyear_PV_DE-BY_2010-01-01_2020-12-31.csv'
    df_PV = pd.read_csv(file_path_PV, names=['DateTimes', 'PV_CF'], header=None, index_col='DateTimes', skiprows=4)

    # Create process state (SOC) and flow (el_in, el_out, etc) variables used for later iterative time series calculation
    timesteps = len(df_PV) + 1

    DateTimes = [datetime.fromtimestamp(0).strftime('%Y-%m-%d %H:%M')] + df_Wind.index.tolist()
    p_Wind_CF = [0] + df_Wind['Wind_CF'].tolist()
    p_Wind_MW = [value * RES_Asset_Wind.Pnom_MW for value in p_Wind_CF]
    p_PV_CF = [0] + df_PV['PV_CF'].tolist()
    p_PV_MW = [value * RES_Asset_PV.Pnom_MW for value in p_PV_CF]
    p_Total_RES_MW = [p_wind + p_pv for p_wind, p_pv in zip(p_Wind_MW, p_PV_MW)]
    p_Grid_MW = [0] * timesteps
    p_Surplus_RES_MW = [0] * timesteps
    p_Total_consump_MW = [0] * timesteps
    el_el_in_MW = [0] * timesteps
    el_H2_out_tH2 = [0] * timesteps
    bess_el_in_MWh = [0] * timesteps
    bess_el_charge_MWh = [0] * timesteps
    bess_SOC_MWh = [BESS.SOC_t0 * BESS.capacity_MWh] + [0] * (timesteps - 1)
    bess_el_discharge_MWh = [0] * timesteps
    bess_el_out_MWh = [0] * timesteps
    bess_el_loss_MWh = [0] * timesteps
    ch2_comp_el_in_MWh = [0] * timesteps
    ch2_comp_el_in_grid_MWh = [0] * timesteps
    ch2_in_tH2 = [0] * timesteps
    ch2_in_ci_gCO2pMJ = [0] * timesteps
    ch2_SOC = [H2Storage.SOC_t0 * H2Storage.capacity_tH2] + [0] * (timesteps - 1)
    ch2_avg_ci_gCO2pMJ = [H2Storage.ci_max_gCO2pMJ if ch2_SOC[0] > 0 else 0] + [0.] * (timesteps - 1)
    ch2_batches_TS_tH2_ci = [[0, ch2_SOC[0], ch2_avg_ci_gCO2pMJ[0]]]
    ch2_out_tH2 = [0] * timesteps
    ch2_vent_tH2 = [0] * timesteps
    ch2_out_ci_gCO2pMJ = [0] * timesteps
    syn_el_in_MWh = [0] * timesteps
    syn_el_in_grid_MWh = [0] * timesteps
    syn_H2_in_tH2 = [0] * timesteps
    syn_NH3_out_tNH3 = [0] * timesteps
    syn_NH3_out_ci_gCO2pMJ = [0] * timesteps
    operation_mode = [''] * timesteps
    syn_shutdown = [0] * timesteps
    el_shutdown = [0] * timesteps
    bess_discharge_eff = [BESS.discharge_eff] + [0] * (timesteps - 1)
    bess_charge_eff = [BESS.charge_eff] + [0] * (timesteps - 1)
    bess_capacity_MWh = [BESS.capacity_MWh] + [0] * (timesteps - 1)
    el_specific_el_MWhptH2 = [Electrolysis.specific_el_MWhptH2] + [0] * (timesteps - 1)


    # Shut down analysis variable initiation
    syn_SD_t0 = 0
    syn_SD_duration = 0
    el_SD_t0 = 0
    el_SD_duration = 0

    # Degradation tracker variable initiation
    prev_month = (
        datetime.strptime(DateTimes[0], '%Y-%m-%d %H:%M').month,
        datetime.strptime(DateTimes[0], '%Y-%m-%d %H:%M').year
    )

    bess_capacity_t0 = BESS.capacity_MWh
    bess_dischar_eff_t0 = BESS.discharge_eff
    bess_char_eff_t0 = BESS.charge_eff
    el_specific_el_t0 = Electrolysis.specific_el_MWhptH2

    # Syn restart delay tracker variable initiation
    syn_block = False
    syn_delay_counter = 0



    ####################################################################################################################
    # Iterative plant calculation
    ####################################################################################################################

    for i in range(1, timesteps):

        ####################################################################################################################
        # Adjust plant performance according to degradation (BESS capacity, Ely specific el consumption, etc)
        ####################################################################################################################

        current_time = datetime.strptime(DateTimes[i], '%Y-%m-%d %H:%M')
        current_month = current_time.month
        current_year = current_time.year

        # Check whether the first of a new month has been reached to adjust the degradation for the following month
        if prev_month != (current_month, current_year):

            # Determine monthly share of degradation
            days_annual = 366 if isleap(current_year) else 365
            days_month = monthrange(current_year, current_month)[1]
            annual_share = days_month / days_annual

            # Adjust plant properties according to monthly degradation impact
            BESS.capacity_MWh = BESS.capacity_MWh - bess_capacity_t0 * BESS.degradation_capacity * annual_share
            BESS.charge_eff = BESS.charge_eff - BESS.degradation_eff * annual_share
            BESS.discharge_eff = BESS.discharge_eff - BESS.degradation_eff * annual_share
            # BESS.charge_eff = BESS.charge_eff - bess_char_eff_t0 * BESS.degradation_eff * annual_share
            # BESS.discharge_eff = BESS.discharge_eff - bess_dischar_eff_t0 * BESS.degradation_eff * annual_share
            Electrolysis.specific_el_MWhptH2 = Electrolysis.specific_el_MWhptH2 + el_specific_el_t0 * Electrolysis.degradation_specific_el * annual_share

            # Adjust BESS SOC to new max capacity if necessary
            bess_el_loss_MWh[i - 1] += max(0, bess_SOC_MWh[i - 1] - BESS.capacity_MWh)
            bess_SOC_MWh[i - 1] = min(bess_SOC_MWh[i - 1], BESS.capacity_MWh)


        prev_month = (current_month, current_year)

        # Track degradation affected plant properties
        bess_capacity_MWh[i] = BESS.capacity_MWh
        bess_charge_eff[i] = BESS.charge_eff
        bess_discharge_eff[i] = BESS.discharge_eff
        el_specific_el_MWhptH2[i] = Electrolysis.specific_el_MWhptH2

        ####################################################################################################################
        # Synthesis restart delay
        ####################################################################################################################

        # decrement restart delay tracker
        syn_delay_counter = max(0, syn_delay_counter - 1)

        # Check if the Synthesis is currently under restart delay (syn_block = True). If so check whether Delay counter
        # ran out. If so unblock Synthesis (syn_block = False)
        if syn_block:
            syn_block = True if syn_delay_counter > 0 else False


        ####################################################################################################################
        # Calc fix system variables
        ####################################################################################################################

        bess_SOC_min_MWh = BESS.capacity_MWh * BESS.min_SOC
        ch2_SOC_min_tH2 = H2Storage.capacity_tH2 * H2Storage.min_SOC

        # CON 1:
        ####################################################################################################################
        # c01_demand_system_nom: Gives the total power-demand necessary to operate the HaberBosch at nominal load independent of storage --> H2 supply directly from ELY
        c01_demand_system_nom = HaberBosch.capacity_tNH3ph * (
                HaberBosch.specific_H2_tH2ptNH3 * Electrolysis.specific_el_MWhptH2 + HaberBosch.specific_el_MWhptNH3)

        # CON 5:
        ####################################################################################################################
        # c05_system_spec_el_MWhptH2: Gives the specific el. energy demand per tonne H2 produced and compressed to storage
        c05_system_spec_el_MWhptH2 = Electrolysis.specific_el_MWhptH2 + Compressor.specific_el_MWhptH2

        # c05_max_grid_share_ci_limit: The maximum share of electricity that can be taken from the
        # grid and fed to the compressor to uphold the Ci-Threshold set on H2 stored to cH2-Storage
        c05_max_grid_share_ci_limit = min(1.,
                                          min(H2Storage.ci_max_gCO2pMJ,
                                              ci_budget_gCO2pMJ) * energy_density_H2_MJpkgH2 / (
                                                  Grid.ci_gCO2pkWh * c05_system_spec_el_MWhptH2))

        # c05_max_grid_share_comp_limit: The maximum share of electricity that can be taken from the
        # grid and fed to the compressor, to ensure that no grid electricity is consumed in the Ely
        c05_max_grid_share_comp_limit = Compressor.specific_el_MWhptH2 / c05_system_spec_el_MWhptH2

        # c08_max_grid_share: Gives either max grid share based on ci limits or max compressor consumption ensuring 100 % RFNBO
        c05_max_grid_share = min(c05_max_grid_share_comp_limit, c05_max_grid_share_ci_limit)

        # CON 8
        ####################################################################################################################
        # c08_demand_system_min: Gives the total power-demand necessary to operate the HaberBosch
        # at min load independent of storage --> H2 supply directly from ELY
        c08_demand_system_min = c01_demand_system_nom * HaberBosch.min_Load

        # c08_system_spec_el_MWhptNH3: Specific el. energy demand per tonne NH3 including all consumers
        c08_system_spec_el_MWhptNH3 = HaberBosch.specific_el_MWhptNH3 + HaberBosch.specific_H2_tH2ptNH3 * Electrolysis.specific_el_MWhptH2

        # c08_syn_p_total_share & c08_el_p_total_share: share of the total power consumption under normal operation (no storage)
        # in the HaberBosch (syn) and Electrolysis (el) respectively
        c08_syn_p_total_share = HaberBosch.specific_el_MWhptNH3 / c08_system_spec_el_MWhptNH3
        c08_el_p_total_share = HaberBosch.specific_H2_tH2ptNH3 * Electrolysis.specific_el_MWhptH2 / c08_system_spec_el_MWhptNH3

        # c08_max_grid_share_ci_limit: The maximum share of electricity that can be taken from the
        # grid, to uphold the Ci limitations of the produced NH3
        c08_max_grid_share_ci_limit = min(1., ci_budget_gCO2pMJ * energy_density_NH3_MJpkgNH3 / (
                Grid.ci_gCO2pkWh * c08_system_spec_el_MWhptNH3))

        # c08_max_grid_share_syn_limit: The maximum share of electricity that can be taken from the
        # grid under normal operation (no storage), to ensure that no grid electricity is consumed in the Ely
        c08_max_grid_share_syn_limit = HaberBosch.specific_el_MWhptNH3 / c08_system_spec_el_MWhptNH3

        # c08_max_grid_share: Gives either max grid share based on ci limits or max processing consumption ensuring 100 % RFNBO
        c08_max_grid_share = min(c08_max_grid_share_syn_limit, c08_max_grid_share_ci_limit)


        ####################################################################################################################
        # Condition 1:
        # Is there more power from RES, than necessary to supply and operate the Synthesis at nominal load?
        ####################################################################################################################
        if p_Total_RES_MW[i] > c01_demand_system_nom and not syn_block:

            operation_mode[i] = "con_1_T"

            ####################################################################################################################
            # Condition 2:
            # Is the BESS and cH2 below minimum required SOC?
            ####################################################################################################################
            if ch2_SOC[i - 1] < ch2_SOC_min_tH2 or bess_SOC_MWh[i - 1] < bess_SOC_min_MWh:

                operation_mode[i] = operation_mode[i] + '_con_2_T'

                # p_Total_RES_surplus_MW gives the surplus RES potential that is available when running the plant at min load
                p_Total_RES_surplus_MW = p_Total_RES_MW[i] - c08_demand_system_min

                if bess_SOC_MWh[i - 1] < bess_SOC_min_MWh:
                    # bess_el_in_store_SOC_min_MWh gives the RES that can be stored to BESS in order to reach SOC_min
                    bess_el_in_MWh[i] = min(
                        p_Total_RES_surplus_MW,
                        BESS.Pnom_MW,
                        (bess_SOC_min_MWh - bess_SOC_MWh[i - 1]) / BESS.charge_eff
                    )

                    # Adjust p_Total_RES_surplus_MW to the remaining RES after max charging BESS to SOC_min
                    p_Total_RES_surplus_MW -= bess_el_in_MWh[i]

                if ch2_SOC[i - 1] < ch2_SOC_min_tH2 and p_Total_RES_surplus_MW > 0:
                    # el_el_in_H2_stored_max_MWh gives the maximum ELY capacity range that is available to produce H2
                    # to storage when the plant is running at minimum load
                    el_el_in_H2_stored_max_MWh = Electrolysis.capacity_MW - c08_demand_system_min * c08_el_p_total_share

                    ch2_in_tH2[i] = min(
                        p_Total_RES_surplus_MW / c05_system_spec_el_MWhptH2,
                        ch2_SOC_min_tH2 - ch2_SOC[i - 1],
                        el_el_in_H2_stored_max_MWh / Electrolysis.specific_el_MWhptH2
                    )

                    ch2_comp_el_in_MWh[i] = ch2_in_tH2[i] * Compressor.specific_el_MWhptH2

                    # Adjust p_Total_RES_surplus_MW to the remaining RES after max charging cH2-Storage to SOC_min
                    p_Total_RES_surplus_MW -= (ch2_in_tH2[i] * Electrolysis.specific_el_MWhptH2 + ch2_comp_el_in_MWh[i])

                # If, after charging of BESS and cH2-Storage to minimum SOC, while running the plant at minimum load,
                # there is RES available the plant operation will be maximized.

                el_el_in_MW[i] = min(
                    (c08_demand_system_min + p_Total_RES_surplus_MW) * c08_el_p_total_share,
                    Electrolysis.capacity_MW - ch2_in_tH2[i] * Electrolysis.specific_el_MWhptH2,
                    c01_demand_system_nom * c08_el_p_total_share
                ) + ch2_in_tH2[i] * Electrolysis.specific_el_MWhptH2

                el_H2_out_tH2[i] = el_el_in_MW[i] / Electrolysis.specific_el_MWhptH2

                syn_H2_in_tH2[i] = el_H2_out_tH2[i] - ch2_in_tH2[i]
                syn_NH3_out_tNH3[i] = syn_H2_in_tH2[i] / HaberBosch.specific_H2_tH2ptNH3
                syn_el_in_MWh[i] = syn_NH3_out_tNH3[i] * HaberBosch.specific_el_MWhptNH3

                if bess_el_in_MWh[i] != 0:
                    bess_el_charge_MWh[i] = bess_el_in_MWh[i] * BESS.charge_eff
                    bess_el_loss_MWh[i] = bess_el_in_MWh[i] - bess_el_charge_MWh[i]
                    bess_SOC_MWh[i] = bess_SOC_MWh[i - 1] + bess_el_charge_MWh[i]

                if ch2_in_tH2[i] != 0:
                    ch2_batches_TS_tH2_ci.append([i, ch2_in_tH2[i], ch2_in_ci_gCO2pMJ[i]])
                    ch2_SOC[i] = sum(batch[1] for batch in ch2_batches_TS_tH2_ci)
                    ch2_avg_ci_gCO2pMJ[i] = sum(batch[1] * batch[2] for batch in ch2_batches_TS_tH2_ci) / ch2_SOC[i] if \
                    ch2_SOC[i] > 0 else 0

                p_Total_consump_MW[i] = el_el_in_MW[i] + bess_el_in_MWh[i] + ch2_comp_el_in_MWh[i] + syn_el_in_MWh[i]

                p_Surplus_RES_MW[i] = RES_remain = p_Total_RES_MW[i] - p_Total_consump_MW[i]

                # Set storage levels
                bess_SOC_MWh[i] = round(
                    bess_SOC_MWh[i] if (bess_el_in_MWh[i] != 0 or bess_el_out_MWh[i] != 0) else bess_SOC_MWh[i - 1], 10)
                ch2_SOC[i] = round(ch2_SOC[i] if (ch2_in_tH2[i] != 0 or ch2_out_tH2[i] != 0) else ch2_SOC[i - 1], 10)
                ch2_avg_ci_gCO2pMJ[i] = round(
                    ch2_avg_ci_gCO2pMJ[i] if (ch2_in_tH2[i] != 0 or ch2_out_tH2[i] != 0) else ch2_avg_ci_gCO2pMJ[i - 1],
                    10)

                # If, after charging the BESS and cH2-Storage to their minimum SOC and operating the plant at the
                # maximum load possible based on the available component capacity (namely ELY), there is still power
                # remaining, maximize the charge of the cH2-Storage.
                if RES_remain > 0:

                    el_el_in_pot_MW = Electrolysis.capacity_MW - el_el_in_MW[i]

                    ch2_in_extra_tH2 = min(
                        RES_remain / c05_system_spec_el_MWhptH2,
                        el_el_in_pot_MW / Electrolysis.specific_el_MWhptH2,
                        H2Storage.capacity_tH2 - (ch2_SOC[i - 1] + ch2_in_tH2[i])
                    )

                    if ch2_in_tH2[i] != 0:
                        ch2_batches_TS_tH2_ci[-1][1] += ch2_in_extra_tH2
                    else:
                        ch2_batches_TS_tH2_ci.append([i, ch2_in_extra_tH2, ch2_in_ci_gCO2pMJ[i]])

                    ch2_SOC[i] = sum(batch[1] for batch in ch2_batches_TS_tH2_ci)
                    ch2_avg_ci_gCO2pMJ[i] = sum(batch[1] * batch[2] for batch in ch2_batches_TS_tH2_ci) / ch2_SOC[i] if \
                    ch2_SOC[i] > 0 else 0

                    ch2_in_tH2[i] += ch2_in_extra_tH2
                    ch2_comp_el_in_MWh[i] = ch2_in_tH2[i] * Compressor.specific_el_MWhptH2

                    el_el_in_MW[i] += ch2_in_extra_tH2 * Electrolysis.specific_el_MWhptH2
                    el_H2_out_tH2[i] = el_el_in_MW[i] / Electrolysis.specific_el_MWhptH2

                    p_Total_consump_MW[i] = el_el_in_MW[i] + bess_el_in_MWh[i] + ch2_comp_el_in_MWh[i] + syn_el_in_MWh[
                        i]

                    p_Surplus_RES_MW[i] = RES_remain = RES_remain - ch2_in_extra_tH2 * c05_system_spec_el_MWhptH2

                    # If there's still power left after max charging cH2-Storage, then max charge BESS. Any power left
                    # over after that will be put unused surplus
                    if RES_remain > 0:
                        bess_el_in_extra_MWh = min(
                            RES_remain,
                            BESS.Pnom_MW - bess_el_in_MWh[i],
                            (BESS.capacity_MWh - (
                                        bess_SOC_MWh[i - 1] + bess_el_in_MWh[i] / BESS.charge_eff)) / BESS.charge_eff
                        )

                        bess_el_in_MWh[i] += bess_el_in_extra_MWh
                        bess_el_charge_MWh[i] = bess_el_in_MWh[i] * BESS.charge_eff
                        bess_el_loss_MWh[i] = bess_el_in_MWh[i] - bess_el_charge_MWh[i]
                        bess_SOC_MWh[i] = bess_SOC_MWh[i - 1] + bess_el_charge_MWh[i]

                        p_Total_consump_MW[i] = el_el_in_MW[i] + bess_el_in_MWh[i] + ch2_comp_el_in_MWh[i] + \
                                                syn_el_in_MWh[i]
                        p_Surplus_RES_MW[i] -= bess_el_in_extra_MWh

            else:

                operation_mode[i] = operation_mode[i] + '_con_2_F'

                # Operate Syn at nominal load with direct H2-Feed from Ely and determine remaining RES
                syn_el_in_MWh[i] = HaberBosch.capacity_tNH3ph * HaberBosch.specific_el_MWhptNH3
                syn_H2_in_tH2[i] = HaberBosch.capacity_tNH3ph * HaberBosch.specific_H2_tH2ptNH3
                syn_NH3_out_tNH3[i] = HaberBosch.capacity_tNH3ph

                el_H2_out_tH2[i] = syn_H2_in_tH2[i]
                el_el_in_MW[i] = el_H2_out_tH2[i] * Electrolysis.specific_el_MWhptH2

                RES_remain = p_Total_RES_MW[i] - syn_el_in_MWh[i] - el_el_in_MW[i]

                ####################################################################################################################
                # Condition 4:
                # Is there empty cH2 storage capacity?
                ####################################################################################################################
                if ch2_SOC[i - 1] < H2Storage.capacity_tH2:

                    operation_mode[i] = operation_mode[i] + '_con_4_T'

                    ####################################################################################################################
                    # Condition 5:
                    # Would there be RES remaining after max charge cH2 (max Grid use for Comp -> cH2-Ci-Threshold)?
                    ####################################################################################################################
                    if (
                            min(
                                Electrolysis.capacity_MW - el_el_in_MW[i],
                                (H2Storage.capacity_tH2 - ch2_SOC[i - 1]) * Electrolysis.specific_el_MWhptH2
                            )
                            / (Electrolysis.specific_el_MWhptH2 / c05_system_spec_el_MWhptH2)
                            * (1 - c05_max_grid_share)
                            < RES_remain
                    ):

                        ####################################################################################################################
                        # Condition 6: --> Consolidated into one!
                        # Would there be RES remaining after max charge cH2 (max Grid use for Comp -> cH2-Ci-Threshold)
                        # and max charge BESS?
                        ####################################################################################################################

                        operation_mode[i] = operation_mode[i] + '_con_5_T'

                        # Determine increased ELY consumption corresponding to H2 produced to storage
                        el_el_in_stored_H2_MW = min(
                            Electrolysis.capacity_MW - el_el_in_MW[i],
                            (H2Storage.capacity_tH2 - ch2_SOC[i - 1]) * Electrolysis.specific_el_MWhptH2
                        )

                        # Increase ELY consumption by el energy necessary to produce H2 that will be stored and adjust total H2-Output
                        el_el_in_MW[i] += el_el_in_stored_H2_MW
                        el_H2_out_tH2[i] = el_el_in_MW[i] / Electrolysis.specific_el_MWhptH2

                        # Determine H2 volume transferred to storage and set compressor consumption accordingly
                        ch2_in_tH2[i] = el_el_in_stored_H2_MW / Electrolysis.specific_el_MWhptH2
                        ch2_comp_el_in_MWh[i] = ch2_in_tH2[i] * Compressor.specific_el_MWhptH2

                        # Reduce remaining RES by amount consumed in ELY & Compressor for stored H2 production
                        # -> Total_RES(ELY_Consumption)
                        RES_remain -= el_el_in_stored_H2_MW / (
                                    Electrolysis.specific_el_MWhptH2 / c05_system_spec_el_MWhptH2) * (
                                                  1 - c05_max_grid_share)

                        # Determine max charge to BESS from remaining RES considering potential charging-power
                        # limitations due to initial charging to required minimum SOC
                        bess_el_in_extra_MWh = min(
                            RES_remain,
                            min(
                                BESS.Pnom_MW,
                                (BESS.capacity_MWh - bess_SOC_MWh[i - 1]) / BESS.charge_eff
                            )
                            - bess_el_in_MWh[i]
                        )

                        bess_el_in_MWh[i] += bess_el_in_extra_MWh
                        bess_el_loss_MWh[i] = bess_el_in_MWh[i] * (1 - BESS.charge_eff)
                        bess_el_charge_MWh[i] = bess_el_in_MWh[i] - bess_el_loss_MWh[i]
                        bess_SOC_MWh[i] = bess_el_in_extra_MWh * BESS.charge_eff + (
                            bess_SOC_MWh[i] if bess_SOC_MWh[i] != 0 else bess_SOC_MWh[i - 1])

                        # Determine total onsite consumption and derive surplus and additional gird demand depending on
                        # Total RES potential
                        p_Total_consump_MW[i] = el_el_in_MW[i] + syn_el_in_MWh[i] + bess_el_in_MWh[i] + \
                                                ch2_comp_el_in_MWh[i]

                        p_Surplus_RES_MW[i] = max(0, p_Total_RES_MW[i] - p_Total_consump_MW[i])

                        p_Grid_MW[i] = max(0, p_Total_consump_MW[i] - p_Total_RES_MW[i])

                        # Any Grid consumption can only be associated to the compression
                        ch2_comp_el_in_grid_MWh[i] = p_Grid_MW[i]

                        # Determine Ci of H2 transferred to cH2-Storage based on grid consumption which is 100% associated
                        # to Compressor consumption
                        ch2_in_ci_gCO2pMJ[i] = round(ch2_comp_el_in_grid_MWh[i] * 1000 * Grid.ci_gCO2pkWh / (
                                    ch2_in_tH2[i] * 1000 * energy_density_H2_MJpkgH2), 10)

                        # Update cH2-Storage Batch-Overview and adjust cH2-SOC accordingly
                        ch2_batches_TS_tH2_ci.append([i, ch2_in_tH2[i], ch2_in_ci_gCO2pMJ[i]])
                        ch2_SOC[i] = sum(batch[1] for batch in ch2_batches_TS_tH2_ci)
                        ch2_avg_ci_gCO2pMJ[i] = sum(batch[1] * batch[2] for batch in ch2_batches_TS_tH2_ci) / ch2_SOC[
                            i] if ch2_SOC[i] > 0 else 0

                        # Set storage levels
                        bess_SOC_MWh[i] = round(
                            bess_SOC_MWh[i] if (bess_el_in_MWh[i] != 0 or bess_el_out_MWh[i] != 0) else bess_SOC_MWh[
                                i - 1], 10)
                        ch2_SOC[i] = round(
                            ch2_SOC[i] if (ch2_in_tH2[i] != 0 or ch2_out_tH2[i] != 0) else ch2_SOC[i - 1], 10)
                        ch2_avg_ci_gCO2pMJ[i] = round(
                            ch2_avg_ci_gCO2pMJ[i] if (ch2_in_tH2[i] != 0 or ch2_out_tH2[i] != 0) else
                            ch2_avg_ci_gCO2pMJ[i - 1], 10)

                    else:

                        operation_mode[i] = operation_mode[i] + '_con_5_F'

                        # Determine increased ELY consumption corresponding to H2 produced to storage
                        el_el_in_stored_H2_MW = RES_remain * (
                                    Electrolysis.specific_el_MWhptH2 / c05_system_spec_el_MWhptH2) / (
                                                            1 - c05_max_grid_share)

                        # Increase ELY consumption by el energy necessary to produce H2 that will be stored and adjust total H2-Output
                        el_el_in_MW[i] += el_el_in_stored_H2_MW
                        el_H2_out_tH2[i] = el_el_in_MW[i] / Electrolysis.specific_el_MWhptH2

                        # Determine H2 volume transferred to storage and set compressor consumption accordingly
                        ch2_in_tH2[i] = el_el_in_stored_H2_MW / Electrolysis.specific_el_MWhptH2
                        ch2_comp_el_in_MWh[i] = ch2_in_tH2[i] * Compressor.specific_el_MWhptH2

                        # Determine total onsite consumption and derive surplus and additional gird demand depending on
                        # Total RES potential
                        p_Total_consump_MW[i] = el_el_in_MW[i] + syn_el_in_MWh[i] + bess_el_in_MWh[i] + \
                                                ch2_comp_el_in_MWh[i]

                        p_Surplus_RES_MW[i] = max(0, p_Total_RES_MW[i] - p_Total_consump_MW[i])

                        p_Grid_MW[i] = max(0, p_Total_consump_MW[i] - p_Total_RES_MW[i])

                        # Determine Ci of H2 transferred to cH2-Storage based on grid consumption which is 100% associated
                        # to Compressor consumption
                        ch2_in_ci_gCO2pMJ[i] = round(
                            p_Grid_MW[i] * 1000 * Grid.ci_gCO2pkWh / (ch2_in_tH2[i] * 1000 * energy_density_H2_MJpkgH2),
                            10)
                        ch2_comp_el_in_grid_MWh[i] = p_Grid_MW[i]

                        # Update cH2-Storage Batch-Overview and adjust cH2-SOC accordingly
                        ch2_batches_TS_tH2_ci.append([i, ch2_in_tH2[i], ch2_in_ci_gCO2pMJ[i]])
                        ch2_SOC[i] = sum(batch[1] for batch in ch2_batches_TS_tH2_ci)
                        ch2_avg_ci_gCO2pMJ[i] = sum(batch[1] * batch[2] for batch in ch2_batches_TS_tH2_ci) / ch2_SOC[
                            i] if ch2_SOC[i] > 0 else 0

                        # Set storage levels
                        bess_SOC_MWh[i] = round(
                            bess_SOC_MWh[i] if (bess_el_in_MWh[i] != 0 or bess_el_out_MWh[i] != 0) else bess_SOC_MWh[
                                i - 1], 10)
                        ch2_SOC[i] = round(
                            ch2_SOC[i] if (ch2_in_tH2[i] != 0 or ch2_out_tH2[i] != 0) else ch2_SOC[i - 1], 10)
                        ch2_avg_ci_gCO2pMJ[i] = round(
                            ch2_avg_ci_gCO2pMJ[i] if (ch2_in_tH2[i] != 0 or ch2_out_tH2[i] != 0) else
                            ch2_avg_ci_gCO2pMJ[i - 1], 10)

                else:

                    operation_mode[i] = operation_mode[i] + '_con_4_F'

                    # Determine max charge to BESS from remaining RES considering potential charging-power
                    # limitations due to initial charging to required minimum SOC
                    bess_el_in_extra_MWh = min(
                        RES_remain,
                        min(
                            BESS.Pnom_MW,
                            (BESS.capacity_MWh - bess_SOC_MWh[i - 1]) / BESS.charge_eff
                        )
                        - bess_el_in_MWh[i]
                    )

                    bess_el_in_MWh[i] += bess_el_in_extra_MWh
                    bess_el_loss_MWh[i] = bess_el_in_MWh[i] * (1 - BESS.charge_eff)
                    bess_el_charge_MWh[i] = bess_el_in_MWh[i] - bess_el_loss_MWh[i]
                    bess_SOC_MWh[i] = bess_el_in_extra_MWh * BESS.charge_eff + (
                        bess_SOC_MWh[i] if bess_SOC_MWh[i] != 0 else bess_SOC_MWh[i - 1])

                    # Determine remaining RES after max charging BESS
                    RES_remain -= bess_el_in_extra_MWh

                    # Determine the maximum potential H2 produced to storage
                    # a is the potential available energy to the electrolysis from the remaining RES based on a 100% RES supplied ELY and Comp
                    # b is the maximum available ELY-Capacity not yet used
                    # cH2_in_potential_tH2 is the maximum potential H2 produced from RES and unused ELY capacity
                    a = RES_remain * (1 - Compressor.specific_el_MWhptH2 / (
                                Compressor.specific_el_MWhptH2 + Electrolysis.specific_el_MWhptH2))
                    b = Electrolysis.capacity_MW - el_el_in_MW[i]
                    cH2_in_potential_tH2 = min(a, b) / Electrolysis.specific_el_MWhptH2

                    # Determine whether there is Hydrogen in the storage, that could be vented and replaced with lower Ci-H2
                    # batch_TS tracks the batch time stamp that indicates the furthest the cH2 Storage can be depleted
                    # and refilled with lower Ci-H2
                    # trigger keeps track whether a batch with higher Ci-H2 has been identified. If not there is no
                    # H2 to be vented and replaced
                    batch_tH2_total = 0
                    batch_TS = 0
                    trigger = False

                    for batch in ch2_batches_TS_tH2_ci:
                        if batch[2] > 0 and batch_tH2_total < cH2_in_potential_tH2:
                            batch_TS = batch[0]
                            trigger = True
                        batch_tH2_total += batch[1]

                    # Determine the total sum of H2 in the batches that will be fully or partially vented and replaced
                    batch_tH2_total = sum(batch[1] for batch in ch2_batches_TS_tH2_ci if batch[0] <= batch_TS)

                    ####################################################################################################################
                    # Condition 7:
                    # Is there enough unused RES power and unused ELY capacity to produce enough H2 with lower Ci to vent
                    # and replace higher Ci H2 stored in cH2?
                    ####################################################################################################################

                    if RES_remain > 0 and Electrolysis.capacity_MW - el_el_in_MW[i] > 0 and trigger:

                        operation_mode[i] = operation_mode[i] + '_con_7_T'

                        # Check whether the last affected batch (batch_TS) will be fully or partially vented
                        if batch_tH2_total > cH2_in_potential_tH2:

                            # Last affected batch will be vented partially -> Pop batches before and reduce partially vented batch volume
                            # Whole H2-production potential will be used, giving the H2 volume stored to cH2-Storage
                            ch2_in_tH2[i] = cH2_in_potential_tH2
                            ch2_out_tH2[i] = cH2_in_potential_tH2
                            ch2_vent_tH2[i] = cH2_in_potential_tH2

                            # Vent of H2 to the same amount as will be stored (pop batches and adjust last batch's volume)
                            ch2_batches_TS_tH2_ci = [batch for batch in ch2_batches_TS_tH2_ci if batch[0] >= batch_TS]

                            ch2_batches_TS_tH2_ci[0][1] -= ch2_batches_TS_tH2_ci[0][1] - (
                                        batch_tH2_total - cH2_in_potential_tH2)

                        else:

                            # All affected batches will be vented fully and replaced in full
                            ch2_in_tH2[i] = batch_tH2_total
                            ch2_out_tH2[i] = batch_tH2_total
                            ch2_vent_tH2[i] = batch_tH2_total

                            # Vent of H2 to the same amount as will be stored (pop batches and adjust last batch's volume)
                            ch2_batches_TS_tH2_ci = [batch for batch in ch2_batches_TS_tH2_ci if batch[0] > batch_TS]

                        # Determine additional energy input to the ELY necessary to produce stored H2
                        el_el_in_stored_H2_MW = ch2_in_tH2[i] * Electrolysis.specific_el_MWhptH2

                        # Increase ELY consumption by el energy necessary to produce H2 that will be stored and adjust total H2-Output
                        el_el_in_MW[i] += el_el_in_stored_H2_MW
                        el_H2_out_tH2[i] = el_el_in_MW[i] / Electrolysis.specific_el_MWhptH2
                        ch2_comp_el_in_MWh[i] = ch2_in_tH2[i] * Compressor.specific_el_MWhptH2

                        ch2_batches_TS_tH2_ci.append([i, ch2_in_tH2[i], ch2_in_ci_gCO2pMJ[i]])
                        ch2_SOC[i] = sum(batch[1] for batch in ch2_batches_TS_tH2_ci)
                        ch2_avg_ci_gCO2pMJ[i] = sum(batch[1] * batch[2] for batch in ch2_batches_TS_tH2_ci) / ch2_SOC[
                            i] if ch2_SOC[i] > 0 else 0

                        p_Surplus_RES_MW[i] = RES_remain - el_el_in_stored_H2_MW - ch2_comp_el_in_MWh[i]

                    else:

                        operation_mode[i] = operation_mode[i] + '_con_7_F'

                        # Set Surplus to unused remaining RES
                        p_Surplus_RES_MW[i] = RES_remain

                        # Set storage levels
                        bess_SOC_MWh[i] = round(
                            bess_SOC_MWh[i] if (bess_el_in_MWh[i] != 0 or bess_el_out_MWh[i] != 0) else bess_SOC_MWh[
                                i - 1], 10)
                        ch2_SOC[i] = round(
                            ch2_SOC[i] if (ch2_in_tH2[i] != 0 or ch2_out_tH2[i] != 0) else ch2_SOC[i - 1], 10)
                        ch2_avg_ci_gCO2pMJ[i] = round(
                            ch2_avg_ci_gCO2pMJ[i] if (ch2_in_tH2[i] != 0 or ch2_out_tH2[i] != 0) else
                            ch2_avg_ci_gCO2pMJ[i - 1], 10)



        else:

            operation_mode[i] = "con_1_F"

            ####################################################################################################################
            # Condition 8:
            # Is there enough power from RES+Grid_max ALONE to supply and operate the synthesis at or above
            # minimum load AND maintain RFNBO-quality?
            ####################################################################################################################

            # Determine the maximum potential power supply from RES + Grid based on available RES and maximum
            # grid share, that allows for the produced NH3 to be compliant
            p_pot_Total_RES_grid_MW = p_Total_RES_MW[i] / (1 - c08_max_grid_share)

            if p_pot_Total_RES_grid_MW > c08_demand_system_min and not syn_block:

                operation_mode[i] = operation_mode[i] + '_con_8_T'

                ####################################################################################################################
                # Condition 9:
                # Is the BESS & cH2 at or above minimum required SOC?
                ####################################################################################################################
                # If either BESS or cH2-Storage are below minimum required SOC, the plant will be held at minimum
                # operating load, until both storages are filled accordingly to SOC_min.
                if ch2_SOC[i - 1] < ch2_SOC_min_tH2 or bess_SOC_MWh[i - 1] < bess_SOC_min_MWh:

                    operation_mode[i] = operation_mode[i] + '_con_9_T'

                    # p_Total_RES_min_MW gives the minimum required RES that is necessary to operate the plant at minimum load from RES and max_Grid alone.
                    p_Total_RES_min_MW = c08_demand_system_min * (1 - c08_max_grid_share)

                    # p_Total_RES_surplus_MW gives the surplus RES potential that is available when running the plant at min load
                    p_Total_RES_surplus_MW = p_Total_RES_MW[i] - p_Total_RES_min_MW

                    # First BESS will be charged to SOC_min
                    if bess_SOC_MWh[i - 1] < bess_SOC_min_MWh:
                        # Charge BESS to required minimum SOC
                        bess_el_in_MWh[i] = min(p_Total_RES_surplus_MW, BESS.Pnom_MW,
                                                (bess_SOC_min_MWh - bess_SOC_MWh[i - 1]) / BESS.charge_eff)
                        bess_el_charge_MWh[i] = bess_el_in_MWh[i] * BESS.charge_eff
                        bess_el_loss_MWh[i] = bess_el_in_MWh[i] - bess_el_charge_MWh[i]
                        bess_SOC_MWh[i] = bess_SOC_MWh[i - 1] + bess_el_charge_MWh[i]
                        p_Total_RES_surplus_MW -= bess_el_in_MWh[i]

                    # If there is left over surplus RES and cH2 is below SOC_min, then try to charge to SOC_min
                    if ch2_SOC[i - 1] < ch2_SOC_min_tH2 and p_Total_RES_surplus_MW > 0:
                        el_el_in_stored_H2_MW = p_Total_RES_surplus_MW / (1 - c05_max_grid_share) * (
                                    Electrolysis.specific_el_MWhptH2 / c05_system_spec_el_MWhptH2)

                        ch2_in_tH2[i] = min(
                            el_el_in_stored_H2_MW / Electrolysis.specific_el_MWhptH2,
                            ch2_SOC_min_tH2 - ch2_SOC[i - 1]
                        )

                        ch2_comp_el_in_MWh[i] = ch2_in_tH2[i] * Compressor.specific_el_MWhptH2
                        ch2_comp_el_in_grid_MWh[i] = ch2_in_tH2[i] * c05_system_spec_el_MWhptH2 * c05_max_grid_share

                        p_Total_RES_surplus_MW -= ch2_in_tH2[i] * c05_system_spec_el_MWhptH2 * (1 - c05_max_grid_share)

                    # Adjust the available RES and max_grid potential used to set the new operating point of the plant
                    # after charging BESS & cH2.
                    # In Case the available RES-Surplus potential is transferred to storage in full (p_Total_RES_surplus_MW = 0)
                    # the resulting p_pot_Total_RES_grid_MW will set plant operation to minimum load. If it is only partially
                    # used (p_Total_RES_surplus_MW > 0) the plant load will be increased accordingly.

                    p_pot_Total_RES_grid_MW = (p_Total_RES_surplus_MW + p_Total_RES_min_MW) / (1 - c08_max_grid_share)

                else:
                    operation_mode[i] = operation_mode[i] + '_con_9_F'

                ####################################################################################################################
                # Condition 10:
                # Are there Flex-Use capacities left in BESS and/or cH2, that can be used,to increase product output?
                ####################################################################################################################

                # Determine flex-use potentials for BESS & cH2. The flex-use attribute of a storage describes the share
                # of nominal capacity that can be used to maximize output even when there is enough available power
                # to supply the Synthesis above minimum load. Storage_capacity * (1 - flex-use) is the range of storage
                # that is reserved for minimum operation only

                ch2_flex_tH2 = max(0, ch2_SOC[i - 1] - H2Storage.capacity_tH2 * (1 - H2Storage.flex_use))
                bess_flex_MWh = max(0, bess_SOC_MWh[i - 1] - BESS.capacity_MWh * (1 - BESS.flex_use))

                # If
                # - there is flex-use capacity available in either BESS or cH2 and
                # - No charging of either BESS or cH2 has occurred and
                # - the available RES + grid_max are already enough to operate the plant at nominal load
                # then use flex-use capacity to increase product output
                if (
                        (ch2_flex_tH2 > 0 or bess_flex_MWh > 0) and
                        operation_mode[i].endswith('F') and
                        p_pot_Total_RES_grid_MW < c01_demand_system_nom
                ):

                    operation_mode[i] = operation_mode[i] + '_con_10_T'

                    # p_Total_RES_flex_MW = p_Total_RES_MW[i] + ch2_flex_tH2 * Electrolysis.specific_el_MWhptH2 + min(BESS.Pnom_MW, bess_flex_MWh * BESS.discharge_eff)

                    ####################################################################################################################
                    # PLACEHOLDER
                    ####################################################################################################################

                    # There are no flex use potential to be used. The available RES + max_Grid potential is used to set
                    # the operating point of ELY and HB-Syn
                    p_Total_RES_grid_MW = min(c01_demand_system_nom, p_pot_Total_RES_grid_MW)

                    el_el_in_MW[i] = p_Total_RES_grid_MW * c08_el_p_total_share + ch2_in_tH2[
                        i] * Electrolysis.specific_el_MWhptH2
                    el_H2_out_tH2[i] = el_el_in_MW[i] / Electrolysis.specific_el_MWhptH2

                    syn_el_in_MWh[i] = p_Total_RES_grid_MW * c08_syn_p_total_share
                    syn_H2_in_tH2[i] = el_H2_out_tH2[i] - ch2_in_tH2[i]
                    syn_NH3_out_tNH3[i] = syn_el_in_MWh[i] / HaberBosch.specific_el_MWhptNH3

                    p_Total_consump_MW[i] = el_el_in_MW[i] + syn_el_in_MWh[i] + bess_el_in_MWh[i] + ch2_comp_el_in_MWh[
                        i]

                    p_Grid_MW[i] = p_Total_consump_MW[i] - p_Total_RES_MW[i]

                    ch2_comp_el_in_grid_MWh[i] = min(p_Grid_MW[i], ch2_comp_el_in_grid_MWh[i])
                    syn_el_in_grid_MWh[i] = p_Grid_MW[i] - ch2_comp_el_in_grid_MWh[i]

                    if ch2_in_tH2[i] != 0:
                        ch2_in_ci_gCO2pMJ[i] = round(ch2_comp_el_in_grid_MWh[i] * 1000 * Grid.ci_gCO2pkWh / (
                                    ch2_in_tH2[i] * 1000 * energy_density_H2_MJpkgH2), 10)
                        ch2_batches_TS_tH2_ci.append([i, ch2_in_tH2[i], ch2_in_ci_gCO2pMJ[i]])
                        ch2_SOC[i] = sum(batch[1] for batch in ch2_batches_TS_tH2_ci)
                        ch2_avg_ci_gCO2pMJ[i] = sum(batch[1] * batch[2] for batch in ch2_batches_TS_tH2_ci) / ch2_SOC[
                            i] if ch2_SOC[i] > 0 else 0

                    syn_NH3_out_ci_gCO2pMJ[i] = (syn_el_in_grid_MWh[i] * 1000 * Grid.ci_gCO2pkWh) / (
                                syn_NH3_out_tNH3[i] * 1000 * energy_density_NH3_MJpkgNH3)

                    # Set storage levels
                    bess_SOC_MWh[i] = round(
                        bess_SOC_MWh[i] if (bess_el_in_MWh[i] != 0 or bess_el_out_MWh[i] != 0) else bess_SOC_MWh[i - 1],
                        10)
                    ch2_SOC[i] = round(ch2_SOC[i] if (ch2_in_tH2[i] != 0 or ch2_out_tH2[i] != 0) else ch2_SOC[i - 1],
                                       10)
                    ch2_avg_ci_gCO2pMJ[i] = round(
                        ch2_avg_ci_gCO2pMJ[i] if (ch2_in_tH2[i] != 0 or ch2_out_tH2[i] != 0) else ch2_avg_ci_gCO2pMJ[
                            i - 1], 10)

                else:

                    operation_mode[i] = operation_mode[i] + '_con_10_F'

                    # There are no flex use potential to be used. The available RES + max_Grid potential is used to set
                    # the operating point of ELY and HB-Syn
                    p_Total_RES_grid_MW = min(c01_demand_system_nom, p_pot_Total_RES_grid_MW)

                    el_el_in_MW[i] = p_Total_RES_grid_MW * c08_el_p_total_share + ch2_in_tH2[
                        i] * Electrolysis.specific_el_MWhptH2
                    el_H2_out_tH2[i] = el_el_in_MW[i] / Electrolysis.specific_el_MWhptH2

                    syn_el_in_MWh[i] = p_Total_RES_grid_MW * c08_syn_p_total_share
                    syn_H2_in_tH2[i] = el_H2_out_tH2[i] - ch2_in_tH2[i]
                    syn_NH3_out_tNH3[i] = syn_el_in_MWh[i] / HaberBosch.specific_el_MWhptNH3

                    p_Total_consump_MW[i] = el_el_in_MW[i] + syn_el_in_MWh[i] + bess_el_in_MWh[i] + ch2_comp_el_in_MWh[
                        i]

                    p_Grid_MW[i] = p_Total_consump_MW[i] - p_Total_RES_MW[i]

                    ch2_comp_el_in_grid_MWh[i] = min(p_Grid_MW[i], ch2_comp_el_in_grid_MWh[i])
                    syn_el_in_grid_MWh[i] = p_Grid_MW[i] - ch2_comp_el_in_grid_MWh[i]

                    if ch2_in_tH2[i] != 0:
                        ch2_in_ci_gCO2pMJ[i] = round(ch2_comp_el_in_grid_MWh[i] * 1000 * Grid.ci_gCO2pkWh / (
                                    ch2_in_tH2[i] * 1000 * energy_density_H2_MJpkgH2), 10)
                        ch2_batches_TS_tH2_ci.append([i, ch2_in_tH2[i], ch2_in_ci_gCO2pMJ[i]])
                        ch2_SOC[i] = sum(batch[1] for batch in ch2_batches_TS_tH2_ci)
                        ch2_avg_ci_gCO2pMJ[i] = sum(batch[1] * batch[2] for batch in ch2_batches_TS_tH2_ci) / ch2_SOC[
                            i] if ch2_SOC[i] > 0 else 0

                    syn_NH3_out_ci_gCO2pMJ[i] = (syn_el_in_grid_MWh[i] * 1000 * Grid.ci_gCO2pkWh) / (
                                syn_NH3_out_tNH3[i] * 1000 * energy_density_NH3_MJpkgNH3)

                    # Set storage levels
                    bess_SOC_MWh[i] = round(
                        bess_SOC_MWh[i] if (bess_el_in_MWh[i] != 0 or bess_el_out_MWh[i] != 0) else bess_SOC_MWh[i - 1],
                        10)
                    ch2_SOC[i] = round(ch2_SOC[i] if (ch2_in_tH2[i] != 0 or ch2_out_tH2[i] != 0) else ch2_SOC[i - 1],
                                       10)
                    ch2_avg_ci_gCO2pMJ[i] = round(
                        ch2_avg_ci_gCO2pMJ[i] if (ch2_in_tH2[i] != 0 or ch2_out_tH2[i] != 0) else ch2_avg_ci_gCO2pMJ[
                            i - 1], 10)

            else:

                operation_mode[i] = operation_mode[i] + '_con_8_F'

                ####################################################################################################################
                # Condition 11:
                # Is there enough power/H2 stored onsite and from RES to supply and operate
                # the Synthesis at minium load AND maintain RFNBO-quality?
                ####################################################################################################################

                # Condition 11 is divided into 3 sub-conditions. Each sub-condition checks for a partial range of the
                # RES-availability-range, that has been determined to be to low to operate the plant above minimum load
                # without the use of storage capacities onsite. Each sub-condition in turn is further divided into 3-4
                # chronological conditions (if else if). The first chronological condition that yields a potential
                # operating point at minimum plant load will be chosen. If none yield a potential operating point
                # condition 11 will be set to FALSE

                # con_11 tracks if condition 11 can be met
                # mode tracks the chosen operating mode
                # Both are handed down to the Condition 11 Decision-Gate
                con_11 = False
                mode = ''

                # el_el_demand_MWh / syn_el_demand_MWh gives the energy/electricity demand required by the ELY / HB-Syn
                # to support min_load operation of the plant
                el_el_demand_MWh = c08_demand_system_min * c08_el_p_total_share
                syn_el_demand_MWh = c08_demand_system_min * c08_syn_p_total_share

                # el_min_el_demand_MWh gives the energy demand of the ELY at minimum load operation
                el_min_el_demand_MWh = el_el_demand_MWh - Electrolysis.capacity_MW * Electrolysis.min_Load

                # bess_pot_el_out_MWh Gives the maximum potential electricity supply from the BESS
                bess_pot_el_out_MWh = min(BESS.Pnom_MW, bess_SOC_MWh[i - 1] * BESS.discharge_eff)
                ch2_pot_el_equivalent_out_MWh = ch2_SOC[i - 1] * Electrolysis.specific_el_MWhptH2

                # Sub-Condition 1: RES < Syn
                # checks for RES availability that is below even the minimum required electricity input to the HB-Syn
                if p_Total_RES_MW[i] < syn_el_demand_MWh:

                    res_plus_bess = p_Total_RES_MW[i] + bess_pot_el_out_MWh
                    syn_deficit = syn_el_demand_MWh - p_Total_RES_MW[i]

                    # If RES and BESS together cannot supply the minimum required el. energy of the HB-Syn, then there
                    # is no potential operating point for the plant at minimum load -> Condition 11 = FALSE
                    if res_plus_bess > syn_el_demand_MWh:

                        # Is there enough H2 in the cH2-Storage to supply the entire HB-Syn-H2-demand at minload?
                        if ch2_pot_el_equivalent_out_MWh > el_el_demand_MWh:
                            con_11 = True
                            mode = 'con_11_T_subcon_1_mode_1'

                        # Is there enough BESS to supply the HB-Syn deficit along with the minimum required el. energy
                        # demand of the ELY? And is there enough H2 to supply the remaining HB-Syn-H2-demand not covered
                        # by the H2-yield from ELY at min load?
                        elif ch2_pot_el_equivalent_out_MWh > el_el_demand_MWh - el_min_el_demand_MWh and bess_pot_el_out_MWh - syn_deficit > el_min_el_demand_MWh:
                            con_11 = True
                            mode = 'con_11_T_subcon_1_mode_2'

                        # Is there enough BESS potential to supply what cannot be supplied by the cH2?
                        elif min(ch2_pot_el_equivalent_out_MWh, el_el_demand_MWh - el_min_el_demand_MWh) + (
                                bess_pot_el_out_MWh - syn_deficit) > el_el_demand_MWh:
                            con_11 = True

                            if min(ch2_pot_el_equivalent_out_MWh, el_el_demand_MWh - el_min_el_demand_MWh) > 0:
                                mode = 'con_11_T_subcon_1_mode_3'
                            else:
                                mode = 'con_11_T_subcon_1_mode_4'

                        # Is there enough BESS potential to supply the HB-Syn-deficit and the required ELY consumption
                        # to produce the HB-Syn-H2-demand?
                        elif bess_pot_el_out_MWh - syn_deficit > el_el_demand_MWh:
                            con_11 = True
                            mode = 'con_11_T_subcon_1_mode_4'

                        # Under Sub-condition 1 there is no possible plant minimum operating point -> Condition 11 = FALSE
                        else:
                            con_11 = False

                    else:
                        con_11 = False

                # Sub-Condition 2: Syn < RES < Syn + ELY_min
                # checks for RES availability that is above the minimum required electricity input to the HB-Syn
                # BUT below the sum of the minimum required electricity input of the HB-Syn and the minimum
                # required electricity input of the ELY
                if p_Total_RES_MW[i] < syn_el_demand_MWh + el_min_el_demand_MWh and p_Total_RES_MW[
                    i] > syn_el_demand_MWh:

                    # is there enough BESS to supply the missing el. energy necessary to operate the ELY at min load.
                    # And is there enough H2 to supply the then missing H2 to cover the HB-Syn-H2 demand
                    if (bess_pot_el_out_MWh > el_min_el_demand_MWh - (p_Total_RES_MW[i] - syn_el_demand_MWh) and
                            ch2_pot_el_equivalent_out_MWh > (el_el_demand_MWh - el_min_el_demand_MWh)):
                        con_11 = True
                        mode = 'con_11_T_subcon_2_mode_1'

                    # Is there enough H2 to supply the total HB-Syn-H2 demand? unused RES can be charged to BESS for later use
                    elif ch2_pot_el_equivalent_out_MWh > c08_demand_system_min - syn_el_demand_MWh:
                        con_11 = True
                        mode = 'con_11_T_subcon_2_mode_2'

                    # Is there enough BESS potential to supply what cannot be supplied by the cH2?
                    elif min(ch2_pot_el_equivalent_out_MWh,
                             el_el_demand_MWh - el_min_el_demand_MWh) + bess_pot_el_out_MWh > c08_demand_system_min - \
                            p_Total_RES_MW[i]:
                        con_11 = True

                        if min(ch2_pot_el_equivalent_out_MWh, el_el_demand_MWh - el_min_el_demand_MWh) > 0:
                            mode = 'con_11_T_subcon_2_mode_3'
                        else:
                            mode = 'con_11_T_subcon_2_mode_4'

                    # Is there enough BESS potential to the total deficit?
                    elif bess_pot_el_out_MWh > c08_demand_system_min - p_Total_RES_MW[i]:
                        con_11 = True
                        mode = 'con_11_T_subcon_2_mode_4'

                    # Under Sub-condition 2 there is no possible plant minimum operating point -> Condition 11 = FALSE
                    else:
                        con_11 = False

                # Sub-Condition 3: RES > Syn + ELY_min
                # checks for RES availability that is above the sum of the minimum required electricity input to the
                # HB-Syn and the minimum required electricity input of the HB-Syn and the minimum required electricity
                # input of the ELY
                if p_Total_RES_MW[i] > syn_el_demand_MWh + el_min_el_demand_MWh:

                    deficit = c08_demand_system_min - p_Total_RES_MW[i]

                    # Is there enough H2 in storage to cover the deficit of H2 required for the HB-Syn at min load?
                    if ch2_pot_el_equivalent_out_MWh > deficit:
                        con_11 = True
                        mode = 'con_11_T_subcon_3_mode_1'

                    # Is there enough BESS potential to supplement the remaining H2 from storage?
                    elif ch2_pot_el_equivalent_out_MWh + bess_pot_el_out_MWh > deficit:
                        con_11 = True

                        # Is there H2 left in storage or will the deficit be purly supplied by BESS?
                        if ch2_SOC[i - 1] > 0:
                            mode = 'con_11_T_subcon_3_mode_2'
                        else:
                            mode = 'con_11_T_subcon_3_mode_3'

                    else:
                        con_11 = False

                # Run Condition 11
                ####################################################################################################################
                if con_11 and not syn_block:

                    operation_mode[i] = operation_mode[i] + '_' + mode

                    syn_el_in_MWh[i] = syn_el_demand_MWh
                    syn_NH3_out_tNH3[i] = syn_el_in_MWh[i] / HaberBosch.specific_el_MWhptNH3
                    syn_H2_in_tH2[i] = syn_NH3_out_tNH3[i] * HaberBosch.specific_H2_tH2ptNH3

                    # Select mode
                    match mode:

                        case 'con_11_T_subcon_1_mode_1':
                            ch2_out_tH2[i] = el_el_demand_MWh / Electrolysis.specific_el_MWhptH2
                            bess_el_out_MWh[i] = syn_el_demand_MWh - p_Total_RES_MW[i]

                        case 'con_11_T_subcon_1_mode_2':
                            ch2_out_tH2[i] = (
                                                         el_el_demand_MWh - el_min_el_demand_MWh) / Electrolysis.specific_el_MWhptH2
                            bess_el_out_MWh[i] = el_min_el_demand_MWh + (syn_el_demand_MWh - p_Total_RES_MW[i])
                            el_el_in_MW[i] = el_min_el_demand_MWh
                            el_H2_out_tH2[i] = el_el_in_MW[i] / Electrolysis.specific_el_MWhptH2

                        case 'con_11_T_subcon_1_mode_3':
                            ch2_out_tH2[i] = min(ch2_SOC[i - 1], (
                                        el_el_demand_MWh - el_min_el_demand_MWh) / Electrolysis.specific_el_MWhptH2)
                            bess_el_out_MWh[i] = c08_demand_system_min - p_Total_RES_MW[i] - ch2_out_tH2[
                                i] * Electrolysis.specific_el_MWhptH2
                            el_el_in_MW[i] = c08_demand_system_min - syn_el_demand_MWh - ch2_out_tH2[
                                i] * Electrolysis.specific_el_MWhptH2
                            el_H2_out_tH2[i] = el_el_in_MW[i] / Electrolysis.specific_el_MWhptH2

                        case 'con_11_T_subcon_1_mode_4':
                            bess_el_out_MWh[i] = c08_demand_system_min - p_Total_RES_MW[i]
                            el_el_in_MW[i] = el_el_demand_MWh
                            el_H2_out_tH2[i] = el_el_in_MW[i] / Electrolysis.specific_el_MWhptH2

                        case 'con_11_T_subcon_2_mode_1':
                            ch2_out_tH2[i] = (
                                                         el_el_demand_MWh - el_min_el_demand_MWh) / Electrolysis.specific_el_MWhptH2
                            bess_el_out_MWh[i] = el_min_el_demand_MWh + (syn_el_demand_MWh - p_Total_RES_MW[i])
                            el_el_in_MW[i] = el_min_el_demand_MWh
                            el_H2_out_tH2[i] = el_el_in_MW[i] / Electrolysis.specific_el_MWhptH2

                        case 'con_11_T_subcon_2_mode_2':
                            ch2_out_tH2[i] = el_el_demand_MWh / Electrolysis.specific_el_MWhptH2
                            bess_el_in_MWh[i] = min(p_Total_RES_MW[i] - syn_el_demand_MWh, BESS.Pnom_MW,
                                                    (BESS.capacity_MWh - bess_SOC_MWh[i - 1]) / BESS.charge_eff)
                            p_Surplus_RES_MW[i] = p_Total_RES_MW[i] - syn_el_demand_MWh - bess_el_in_MWh[i]

                        case 'con_11_T_subcon_2_mode_3':
                            ch2_out_tH2[i] = min(ch2_SOC[i - 1], (
                                        el_el_demand_MWh - el_min_el_demand_MWh) / Electrolysis.specific_el_MWhptH2)
                            bess_el_out_MWh[i] = c08_demand_system_min - p_Total_RES_MW[i] - ch2_out_tH2[
                                i] * Electrolysis.specific_el_MWhptH2
                            el_el_in_MW[i] = c08_demand_system_min - syn_el_demand_MWh - ch2_out_tH2[
                                i] * Electrolysis.specific_el_MWhptH2
                            el_H2_out_tH2[i] = el_el_in_MW[i] / Electrolysis.specific_el_MWhptH2

                        case 'con_11_T_subcon_2_mode_4':
                            bess_el_out_MWh[i] = c08_demand_system_min - p_Total_RES_MW[i]
                            el_el_in_MW[i] = el_el_demand_MWh
                            el_H2_out_tH2[i] = el_el_in_MW[i] / Electrolysis.specific_el_MWhptH2

                        case 'con_11_T_subcon_3_mode_1':
                            ch2_out_tH2[i] = (c08_demand_system_min - p_Total_RES_MW[
                                i]) / Electrolysis.specific_el_MWhptH2
                            el_el_in_MW[i] = c08_demand_system_min - syn_el_demand_MWh - ch2_out_tH2[
                                i] * Electrolysis.specific_el_MWhptH2
                            el_H2_out_tH2[i] = el_el_in_MW[i] / Electrolysis.specific_el_MWhptH2

                        case 'con_11_T_subcon_3_mode_2':
                            ch2_out_tH2[i] = ch2_SOC[i - 1]
                            bess_el_out_MWh[i] = c08_demand_system_min - p_Total_RES_MW[i] - ch2_out_tH2[
                                i] * Electrolysis.specific_el_MWhptH2
                            el_el_in_MW[i] = c08_demand_system_min - syn_el_demand_MWh - ch2_out_tH2[
                                i] * Electrolysis.specific_el_MWhptH2
                            el_H2_out_tH2[i] = el_el_in_MW[i] / Electrolysis.specific_el_MWhptH2

                        case 'con_11_T_subcon_3_mode_3':
                            bess_el_out_MWh[i] = c08_demand_system_min - p_Total_RES_MW[i]
                            el_el_in_MW[i] = el_el_demand_MWh
                            el_H2_out_tH2[i] = el_el_in_MW[i] / Electrolysis.specific_el_MWhptH2

                        case _:
                            print(f"Error in Iteration {i} - Condition 11")

                    # cH2-discharge
                    if ch2_out_tH2[i] != 0:
                        ch2_discharge = ch2_out_tH2[i]
                        current_sum = 0
                        batch_TS = 0
                        discharge_batches = []

                        if ch2_discharge < 0:
                            raise ValueError(f"Error in Iteration {i} - Condition 11 - cH2-discharge is less 0")

                        elif 0 < ch2_discharge < ch2_SOC[i - 1]:
                            for batch in ch2_batches_TS_tH2_ci:
                                if current_sum + batch[1] > ch2_discharge:
                                    # Calculate the portion to remove
                                    removed_amount = ch2_discharge - current_sum
                                    discharge_batches.append([batch[0], removed_amount, batch[2]])

                                    # Adjust the remaining portion of the current batch
                                    batch[1] -= removed_amount
                                    batch_TS = batch[0]
                                    break
                                else:
                                    # Fully remove the batch
                                    current_sum += batch[1]
                                    discharge_batches.append(batch)

                            ch2_batches_TS_tH2_ci = [batch for batch in ch2_batches_TS_tH2_ci if batch[0] >= batch_TS]

                            ch2_out_batches = discharge_batches
                            ch2_out_ci_gCO2pMJ[i] = sum(
                                batch[1] * batch[2] for batch in ch2_out_batches) / ch2_discharge

                        elif ch2_discharge == ch2_SOC[i - 1]:
                            ch2_batches_TS_tH2_ci = []
                            ch2_out_batches = ch2_batches_TS_tH2_ci
                            ch2_out_ci_gCO2pMJ[i] = sum(
                                batch[1] * batch[2] for batch in ch2_out_batches) / ch2_discharge

                        else:
                            print(f"ch2_SOC[i - 1] - ch2_discharge = {ch2_SOC[i - 1] - ch2_discharge}")
                            raise ValueError(
                                f"Error in Iteration {i} - Condition 11 - cH2-discharge is larger than cH2_SOC")

                        ch2_SOC[i] = sum(batch[1] for batch in ch2_batches_TS_tH2_ci)
                        ch2_avg_ci_gCO2pMJ[i] = sum(batch[1] * batch[2] for batch in ch2_batches_TS_tH2_ci) / ch2_SOC[
                            i] if ch2_SOC[i] > 0 else 0

                    # BESS-charge/discharge
                    if bess_el_out_MWh[i] != 0 or bess_el_in_MWh[i] != 0:
                        if bess_el_out_MWh[i] > 0 and bess_el_in_MWh[i] == 0:
                            bess_el_discharge_MWh[i] = bess_el_out_MWh[i] / BESS.discharge_eff
                            bess_SOC_MWh[i] = bess_SOC_MWh[i - 1] - bess_el_discharge_MWh[i]
                            bess_el_loss_MWh[i] = bess_el_discharge_MWh[i] - bess_el_out_MWh[i]
                        elif bess_el_out_MWh[i] == 0 and bess_el_in_MWh[i] > 0:
                            bess_el_charge_MWh[i] = bess_el_in_MWh[i] * BESS.charge_eff
                            bess_SOC_MWh[i] = bess_SOC_MWh[i - 1] + bess_el_charge_MWh[i]
                            bess_el_loss_MWh[i] = bess_el_in_MWh[i] - bess_el_charge_MWh[i]
                        elif bess_el_out_MWh[i] == 0 and bess_el_in_MWh[i] == 0:
                            break
                        else:
                            raise ValueError(
                                f"Error in Iteration {i} - Condition 11 - invalid BESS charge/discharge demands")

                    # Determine NH3-Out Ci
                    # Total CO2 from H2 discharged from storage (only source of CO2 under Condition 11 = TRUE)
                    co2_total_gCO2 = ch2_out_ci_gCO2pMJ[i] * ch2_out_tH2[i] * 1000 * energy_density_H2_MJpkgH2
                    syn_NH3_out_ci_gCO2pMJ[i] = co2_total_gCO2 / (
                                syn_NH3_out_tNH3[i] * 1000 * energy_density_NH3_MJpkgNH3)

                    # Set storage levels
                    bess_SOC_MWh[i] = round(
                        bess_SOC_MWh[i] if (bess_el_in_MWh[i] != 0 or bess_el_out_MWh[i] != 0) else bess_SOC_MWh[i - 1],
                        10)
                    ch2_SOC[i] = round(ch2_SOC[i] if (ch2_in_tH2[i] != 0 or ch2_out_tH2[i] != 0) else ch2_SOC[i - 1],
                                       10)
                    ch2_avg_ci_gCO2pMJ[i] = round(
                        ch2_avg_ci_gCO2pMJ[i] if (ch2_in_tH2[i] != 0 or ch2_out_tH2[i] != 0) else ch2_avg_ci_gCO2pMJ[
                            i - 1], 10)


                else:
                    ####################################################################################################################
                    # Initialize Synthesis delay counter if Synthesis is not blocked
                    ####################################################################################################################
                    if not syn_block:

                        syn_delay_counter = HaberBosch.restart_delay_h
                        syn_block = True

                        operation_mode[i] = operation_mode[i] + '_con_11_F'
                    else:
                        operation_mode[i] = 'Syn_block'

                    ####################################################################################################################
                    # Condition 13:
                    # Is there enough RES to supply Syn-Standby demand?
                    ####################################################################################################################
                    if p_Total_RES_MW[i] > c08_demand_system_min * c08_syn_p_total_share:

                        operation_mode[i] = operation_mode[i] + '_con_13_T'

                        syn_el_in_MWh[i] = c08_demand_system_min * c08_syn_p_total_share

                        RES_remain = p_Total_RES_MW[i] - syn_el_in_MWh[i]

                        ####################################################################################################################
                        # Condition 14:
                        # Is the BESS at or above minimum required SOC?
                        ####################################################################################################################
                        if bess_SOC_MWh[i - 1] < bess_SOC_min_MWh:

                            operation_mode[i] = operation_mode[i] + '_con_14_T'

                            # bess_el_in_store_SOC_min_MWh gives the RES that can be stored to BESS in order to reach SOC_min
                            bess_el_in_MWh[i] = min(
                                RES_remain,
                                BESS.Pnom_MW,
                                (bess_SOC_min_MWh - bess_SOC_MWh[i - 1]) / BESS.charge_eff
                            )

                            RES_remain -= bess_el_in_MWh[i]

                        else:

                            operation_mode[i] = operation_mode[i] + '_con_14_F'

                        ####################################################################################################################
                        # Condition 15:
                        # Is there enough power from RES and empty storage in cH2 to operate the Electrolysis above
                        # minimum load and provide Syn-Standby demand?
                        ####################################################################################################################
                        # cH2_in_min_tH2 gives the H2 production from ELY at min load
                        cH2_in_min_tH2 = Electrolysis.capacity_MW * Electrolysis.min_Load / c05_system_spec_el_MWhptH2

                        # If the remaining RES allows for ELY operation above min load and there is enough available
                        # capacity in cH2-Storage procure max H2 to cH2-Storage
                        if (RES_remain > cH2_in_min_tH2 * Electrolysis.specific_el_MWhptH2 and
                                H2Storage.capacity_tH2 - ch2_SOC[i - 1] > cH2_in_min_tH2):

                            operation_mode[i] = operation_mode[i] + '_con_15_T'

                            ch2_in_tH2[i] = min(
                                RES_remain / c05_system_spec_el_MWhptH2,
                                H2Storage.capacity_tH2 - ch2_SOC[i - 1],
                                Electrolysis.capacity_MW / Electrolysis.specific_el_MWhptH2
                            )

                            el_el_in_MW[i] = ch2_in_tH2[i] * Electrolysis.specific_el_MWhptH2
                            el_H2_out_tH2[i] = el_el_in_MW[i] / Electrolysis.specific_el_MWhptH2

                            ch2_comp_el_in_MWh[i] = ch2_in_tH2[i] * Compressor.specific_el_MWhptH2
                            ch2_batches_TS_tH2_ci.append([i, ch2_in_tH2[i], ch2_in_ci_gCO2pMJ[i]])
                            ch2_SOC[i] = sum(batch[1] for batch in ch2_batches_TS_tH2_ci)
                            ch2_avg_ci_gCO2pMJ[i] = sum(batch[1] * batch[2] for batch in ch2_batches_TS_tH2_ci) / \
                                                    ch2_SOC[i] if ch2_SOC[i] > 0 else 0

                            RES_remain -= ch2_comp_el_in_MWh[i] + el_el_in_MW[i]

                        else:

                            operation_mode[i] = operation_mode[i] + '_con_15_F'

                        # Store any leftover RES to BESS
                        bess_el_in_extra_MWh = min(
                            RES_remain,
                            BESS.Pnom_MW - bess_el_in_MWh[i],
                            (BESS.capacity_MWh - (
                                        bess_SOC_MWh[i - 1] + bess_el_in_MWh[i] / BESS.charge_eff)) / BESS.charge_eff
                        )

                        bess_el_in_MWh[i] += bess_el_in_extra_MWh
                        bess_el_charge_MWh[i] = bess_el_in_MWh[i] * BESS.charge_eff
                        bess_el_loss_MWh[i] = bess_el_in_MWh[i] - bess_el_charge_MWh[i]
                        bess_SOC_MWh[i] = bess_SOC_MWh[i - 1] + bess_el_charge_MWh[i]

                        RES_remain -= bess_el_in_extra_MWh
                        p_Surplus_RES_MW[i] = RES_remain

                        # Set storage levels
                        bess_SOC_MWh[i] = round(
                            bess_SOC_MWh[i] if (bess_el_in_MWh[i] != 0 or bess_el_out_MWh[i] != 0) else bess_SOC_MWh[
                                i - 1], 10)
                        ch2_SOC[i] = round(
                            ch2_SOC[i] if (ch2_in_tH2[i] != 0 or ch2_out_tH2[i] != 0) else ch2_SOC[i - 1], 10)
                        ch2_avg_ci_gCO2pMJ[i] = round(
                            ch2_avg_ci_gCO2pMJ[i] if (ch2_in_tH2[i] != 0 or ch2_out_tH2[i] != 0) else
                            ch2_avg_ci_gCO2pMJ[i - 1], 10)


                    else:

                        operation_mode[i] = operation_mode[i] + '_con_13_F'

                        ####################################################################################################################
                        # Condition 16:
                        # Is there enough RES and BESS capacity to supply Syn-Standby demand?
                        ####################################################################################################################
                        if p_Total_RES_MW[i] + min(bess_SOC_MWh[i - 1] / BESS.discharge_eff,
                                                   BESS.Pnom_MW) > c08_demand_system_min * c08_syn_p_total_share:

                            # Supply Syn Standby-demand through RES and BESS
                            operation_mode[i] = operation_mode[i] + '_con_16_T'

                            syn_el_in_MWh[i] = c08_demand_system_min * c08_syn_p_total_share

                            bess_el_out_MWh[i] = syn_el_in_MWh[i] - p_Total_RES_MW[i]
                            bess_el_discharge_MWh[i] = bess_el_out_MWh[i] / BESS.discharge_eff
                            bess_el_loss_MWh[i] = bess_el_discharge_MWh[i] - bess_el_out_MWh[i]
                            bess_SOC_MWh[i] = bess_SOC_MWh[i - 1] - bess_el_discharge_MWh[i]

                            # Set storage levels
                            bess_SOC_MWh[i] = round(
                                bess_SOC_MWh[i] if (bess_el_in_MWh[i] != 0 or bess_el_out_MWh[i] != 0) else
                                bess_SOC_MWh[i - 1], 10)
                            ch2_SOC[i] = round(
                                ch2_SOC[i] if (ch2_in_tH2[i] != 0 or ch2_out_tH2[i] != 0) else ch2_SOC[i - 1], 10)
                            ch2_avg_ci_gCO2pMJ[i] = round(
                                ch2_avg_ci_gCO2pMJ[i] if (ch2_in_tH2[i] != 0 or ch2_out_tH2[i] != 0) else
                                ch2_avg_ci_gCO2pMJ[i - 1], 10)

                        else:

                            # Supply Syn Standby-demand through RES, BESS and grid
                            operation_mode[i] = operation_mode[i] + '_con_16_F'

                            syn_el_in_MWh[i] = c08_demand_system_min * c08_syn_p_total_share

                            bess_el_out_MWh[i] = min(bess_SOC_MWh[i - 1] / BESS.discharge_eff, BESS.Pnom_MW)
                            bess_el_discharge_MWh[i] = bess_el_out_MWh[i] / BESS.discharge_eff
                            bess_el_loss_MWh[i] = bess_el_discharge_MWh[i] - bess_el_out_MWh[i]
                            bess_SOC_MWh[i] = bess_SOC_MWh[i - 1] - bess_el_discharge_MWh[i]

                            p_Grid_MW[i] = syn_el_in_MWh[i] - bess_el_out_MWh[i] - p_Total_RES_MW[i]
                            syn_el_in_grid_MWh[i] = p_Grid_MW[i]

                            # Set storage levels
                            bess_SOC_MWh[i] = round(
                                bess_SOC_MWh[i] if (bess_el_in_MWh[i] != 0 or bess_el_out_MWh[i] != 0) else
                                bess_SOC_MWh[i - 1], 10)
                            ch2_SOC[i] = round(
                                ch2_SOC[i] if (ch2_in_tH2[i] != 0 or ch2_out_tH2[i] != 0) else ch2_SOC[i - 1], 10)
                            ch2_avg_ci_gCO2pMJ[i] = round(
                                ch2_avg_ci_gCO2pMJ[i] if (ch2_in_tH2[i] != 0 or ch2_out_tH2[i] != 0) else
                                ch2_avg_ci_gCO2pMJ[i - 1], 10)

        # Set total consumption
        p_Total_consump_MW[i] = el_el_in_MW[i] + syn_el_in_MWh[i] + bess_el_in_MWh[i] + ch2_comp_el_in_MWh[i]

        ####################################################################################################################
        # ELY & Syn Shutdown behavior:
        # Track Electrolysis and Syn-plant Shut down occurrences and durations
        ####################################################################################################################

        # Syn shutdown
        if syn_NH3_out_tNH3[i] > 0 and syn_NH3_out_tNH3[i - 1] > 0:
            pass

        elif syn_NH3_out_tNH3[i] == 0 and syn_NH3_out_tNH3[i - 1] > 0:
            syn_SD_t0 = i
            syn_SD_duration = 1
            syn_shutdown[syn_SD_t0] = syn_SD_duration

        elif syn_NH3_out_tNH3[i] == syn_NH3_out_tNH3[i - 1] == 0:
            syn_SD_duration += 1
            syn_shutdown[syn_SD_t0] = syn_SD_duration

        elif syn_NH3_out_tNH3[i] > 0 and syn_NH3_out_tNH3[i - 1] == 0:
            syn_SD_t0 = 0
            syn_SD_duration = 0

        # Ely shutdown
        if el_H2_out_tH2[i] > 0 and el_H2_out_tH2[i - 1] > 0:
            pass

        elif el_H2_out_tH2[i] == 0 and el_H2_out_tH2[i - 1] > 0:
            el_SD_t0 = i
            el_SD_duration = 1
            el_shutdown[el_SD_t0] = el_SD_duration

        elif el_H2_out_tH2[i] == el_H2_out_tH2[i - 1] == 0:
            el_SD_duration += 1
            el_shutdown[el_SD_t0] = el_SD_duration

        elif el_H2_out_tH2[i] > 0 and el_H2_out_tH2[i - 1] == 0:
            el_SD_t0 = 0
            el_SD_duration = 0

    ####################################################################################################################
    # SET UP OUTPUT DATAFRAME
    ####################################################################################################################

    # Collect Column Names
    columns = [
        'DateTimes',
        'p_Wind_CF',
        'p_Wind_MW',
        'p_PV_CF',
        'p_PV_MW',
        'p_Total_RES_MW',
        'p_Grid_MW',
        'p_Surplus_RES_MW',
        'p_Total_consump_MW',
        'el_el_in_MW',
        'el_H2_out_tH2',
        'bess_el_in_MWh',
        'bess_el_charge_MWh',
        'bess_SOC_MW',
        'bess_el_discharge_MWh',
        'bess_el_out_MWh',
        'bess_el_loss_MWh',
        'ch2_comp_el_in_MWh',
        'ch2_comp_el_in_grid_MWh',
        'ch2_in_tH2',
        'ch2_SOC',
        'ch2_out_tH2',
        'ch2_vent_tH2',
        'ch2_in_ci_gCO2pMJ',
        'ch2_out_ci_gCO2pMJ',
        'ch2_avg_ci_gCO2pMJ',
        'syn_el_in_MWh',
        'syn_el_in_grid_MWh',
        'syn_H2_in_tH2',
        'syn_NH3_out_tNH3',
        'syn_NH3_out_ci_gCO2pMJ',
        'operation_mode',
        'syn_shutdown',
        'el_shutdown',
        'bess_capacity_MWh',
        'bess_charge_eff',
        'bess_discharge_eff',
        'el_specific_el_MWhptH2'
    ]

    # Combine the lists into rows (zip them together)
    calc_data_rows = list(
        zip(
            DateTimes,
            p_Wind_CF,
            p_Wind_MW,
            p_PV_CF,
            p_PV_MW,
            p_Total_RES_MW,
            p_Grid_MW,
            p_Surplus_RES_MW,
            p_Total_consump_MW,
            el_el_in_MW,
            el_H2_out_tH2,
            bess_el_in_MWh,
            bess_el_charge_MWh,
            bess_SOC_MWh,
            bess_el_discharge_MWh,
            bess_el_out_MWh,
            bess_el_loss_MWh,
            ch2_comp_el_in_MWh,
            ch2_comp_el_in_grid_MWh,
            ch2_in_tH2,
            ch2_SOC,
            ch2_out_tH2,
            ch2_vent_tH2,
            ch2_in_ci_gCO2pMJ,
            ch2_out_ci_gCO2pMJ,
            ch2_avg_ci_gCO2pMJ,
            syn_el_in_MWh,
            syn_el_in_grid_MWh,
            syn_H2_in_tH2,
            syn_NH3_out_tNH3,
            syn_NH3_out_ci_gCO2pMJ,
            operation_mode,
            syn_shutdown,
            el_shutdown,
            bess_capacity_MWh,
            bess_charge_eff,
            bess_discharge_eff,
            el_specific_el_MWhptH2
        )
    )

    # Create the DataFrame
    df_out = pd.DataFrame(calc_data_rows, columns=columns)

    # Return output value dataframe df_out
    return df_out