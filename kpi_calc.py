#################################################################################################################
# kpi_calc() returns LCOA on a monthly resolution and a list of commercial, technical and regulatory
# KPIs. As an input the function requires
# - a plant configuration as is returned by plant_init() and
# - a plant calculation as is returned by plant_cals()
#################################################################################################################

import pandas as pd

def kpi_calc(df_out, plant_config):

    # Plant calculation output data handling/aggregation
    ###################################################################################################################
    # Adjust output dataframe
    df_out['DateTimes'] = pd.to_datetime(df_out['DateTimes'], format='%Y-%m-%d %H:%M')
    df_out = df_out.drop(columns=['operation_mode'])
    df_out = df_out.drop([0])
    df_out.set_index('DateTimes', inplace=True)

    # Create aggregated data description on daily, monthly and annual basis
    df_out_month = df_out.resample('ME').agg(['count', 'sum', 'mean', 'max', 'min'])
    df_out_year = df_out.resample('YE').agg(['count', 'sum', 'mean', 'max', 'min'])
    df_out_total = df_out.agg(['count', 'sum', 'mean', 'max', 'min'])

    # Define Calc variables
    ###################################################################################################################
    # Project specifications
    WACC = plant_config['Economic_System']['WACC']['value']
    construction_phase_a = plant_config['Economic_System']['construction_phase_a']['value']
    CPI = plant_config['Economic_System']['CPI']['value']

    # Specific cost of functioning units
    sc_HaberBosch_EURptNH3ph = plant_config['HaberBosch']['specific_cost_EURptNH3ph']['value']
    sc_BESS_EURpMWh = plant_config['BESS']['specific_cost_EURpMWh']['value']
    sc_Ely_EURpMW = plant_config['Electrolysis']['specific_cost_EURpMW']['value']
    sc_cH2_EURptH2 = plant_config['H2Storage']['specific_cost_EURptH2']['value']

    # Functioning unit capacity
    HaberBosch_capacity_tNH3ph = plant_config['HaberBosch']['capacity_tNH3ph']['value']
    BESS_capacity_MWh = plant_config['BESS']['capacity_MWh']['value']
    Electrolysis_capacity_MW = plant_config['Electrolysis']['capacity_MW']['value']
    H2Storage_capacity_tH2 = plant_config['H2Storage']['capacity_tH2']['value']
    RES_Wind_Pnom_MW = plant_config['RES_Asset_Wind']['Pnom_MW']['value']
    RES_PV_Pnom_MW = plant_config['RES_Asset_PV']['Pnom_MW']['value']

    # Total CapEx based on plant_config
    CapEx_HaberBosch = sc_HaberBosch_EURptNH3ph * HaberBosch_capacity_tNH3ph
    CapEx_BESS = sc_BESS_EURpMWh * BESS_capacity_MWh
    CapEx_Ely = sc_Ely_EURpMW * Electrolysis_capacity_MW
    CapEx_cH2 = sc_cH2_EURptH2 * H2Storage_capacity_tH2

    CapEx_Total = sum([
        CapEx_HaberBosch,
        CapEx_BESS,
        CapEx_Ely,
        CapEx_cH2
    ])

    # Operational cost
    transport_logistics_EURptNH3 = 0
    O_M_CapEx_share = plant_config['Economic_System']['O_M_CapEx_share']['value'] # Annual O&M cost as percentage of initial CapEx
    O_M_cost = O_M_CapEx_share * CapEx_Total

    # Electricity cost
    RES_Wind_PPA_price_EURpMWh = plant_config['RES_Asset_Wind']['PPA_price_EURpMWh']['value'] # (fixed price longterm PPA)
    RES_PV_PPA_price_EURpMWh = plant_config['RES_Asset_PV']['PPA_price_EURpMWh']['value'] # (fixed price longterm PPA)
    Grid_price_EURpMWh = plant_config['Economic_System']['grid_el_price_EURpMWh']['value']
    RES_Surplus_sales_price_EURpMWh = plant_config['Economic_System']['RES_surplus_sales_price']['value']


    # Set up indexations for orientation
    ###################################################################################################################
    index_year = [0]
    index_month = [0]

    for year in range(1, construction_phase_a + len(df_out_year.index) + 1):
        for month in range(1, 13):
            index_year.append(year)
            index_month.append(month)

    index_operational = [1 if i > construction_phase_a else 0 for i in index_year]

    discount_factor = [1 / pow(1 + WACC, i / 12) for i in range(len(index_year))]

    CPI_factor = [pow(1 + CPI, i / 12) for i in range(len(index_year))]

    # Cost serieses
    ###################################################################################################################
    # Component & Total CapEx
    # c_CapEx_EUR = c_CapEx_HaberBosch = c_CapEx_BESS = c_CapEx_Ely = c_CapEx_cH2 = [0] * len(index_year)

    c_CapEx_HaberBosch = [CapEx_HaberBosch] + [0] * (len(index_year) - 1)
    c_CapEx_BESS = [CapEx_BESS] + [0] * (len(index_year) - 1)
    c_CapEx_Ely = [CapEx_Ely] + [0] * (len(index_year) - 1)
    c_CapEx_cH2 = [CapEx_cH2] + [0] * (len(index_year) - 1)
    c_CapEx_EUR = [CapEx_Total] + [0] * (len(index_year) - 1)

    # OpEx
    c_OpEx_EUR = [i_op * i_cpi * O_M_cost / 12 for i_op, i_cpi in zip(index_operational, CPI_factor)]

    # Electricity bought from RES and Grid
    # Wind PPA
    el_RES_wind_MWh = [0] + [0] * 12 * construction_phase_a + df_out_month.p_Wind_MW["sum"].tolist()
    c_RES_wind_EUR = [RES_Wind_PPA_price_EURpMWh * i for i in el_RES_wind_MWh]

    # PV PPA
    el_RES_pv_MWh = [0] + [0] * 12 * construction_phase_a + df_out_month.p_PV_MW["sum"].tolist()
    c_RES_pv_EUR = [RES_PV_PPA_price_EURpMWh * i for i in el_RES_pv_MWh]

    # RES total
    el_RES_MWh = [a + b for a,b in zip(el_RES_wind_MWh,el_RES_pv_MWh)]
    c_RES_EUR = [a + b for a,b in zip(c_RES_wind_EUR,c_RES_pv_EUR)]
    sc_RES_PPA_EURpMWh = [a / b if b != 0 else 0 for a,b in zip(c_RES_EUR,el_RES_MWh)]

    # RES surplus & used
    el_RES_surplus_MWh = [0] + [0] * 12 * construction_phase_a + df_out_month.p_Surplus_RES_MW["sum"].tolist()
    el_RES_used_MWh = [a - b for a,b in zip(el_RES_MWh,el_RES_surplus_MWh)]
    sc_RES_used_EURpMWh = [a / b if b != 0 else 0 for a,b in zip(c_RES_EUR,el_RES_used_MWh)]

    # Grid
    el_grid_MWh = [0] + [0] * 12 * construction_phase_a + df_out_month.p_Grid_MW["sum"].tolist()
    c_grid_EUR = [Grid_price_EURpMWh * i for i in el_grid_MWh]

    # RES + Grid Total
    el_RES_grid_MWh = [a + b for a,b in zip(el_RES_MWh,el_grid_MWh)]
    c_RES_grid_EUR = [a + b for a,b in zip(c_RES_EUR,c_grid_EUR)]
    sc_RES_grid_EURpMWh = [a / b if b != 0 else 0 for a,b in zip(c_RES_grid_EUR,el_RES_grid_MWh)]

    # Surplus sales
    r_RES_surplus_sales_EURpMWh = [- RES_Surplus_sales_price_EURpMWh * i for i in el_RES_surplus_MWh]

    # Total cost
    c_Total_EUR = [sum(i) for i in zip(c_CapEx_EUR, c_OpEx_EUR, c_RES_grid_EUR, r_RES_surplus_sales_EURpMWh)]
    c_Total_discounted_EUR = [a * b for a,b in zip(c_Total_EUR, discount_factor)]

    # Total ammonia production
    NH3_out_tNH3 = [0] + [0] * 12 * construction_phase_a + df_out_month.syn_NH3_out_tNH3["sum"].tolist()
    NH3_out_discounted = [a * b for a,b in zip(NH3_out_tNH3, discount_factor)]

    # Levelized Cost of Ammonia
    LCOA = sum(c_Total_discounted_EUR) / sum(NH3_out_discounted) if sum(NH3_out_discounted) > 0 else 0


    # Set up output dataframe for levelized cost calculation
    ###################################################################################################################
    # Define multi index
    multi_index = pd.MultiIndex.from_arrays([index_year, index_month], names=["Year", "Month"])

    # Create DataFrame
    df_lcoa = pd.DataFrame({
        "Operational": index_operational,
        "Discount Factor": discount_factor,
        "CPI factor": CPI_factor,
        "CapEx Haber Bosch unit": c_CapEx_HaberBosch,
        "CapEx Electrolyzer unit": c_CapEx_Ely,
        "CapEx BESS": c_CapEx_BESS,
        "CapEx cH2-Storage unit": c_CapEx_cH2,
        "Total CapEx @ Entry": c_CapEx_EUR,
        "OpEx": c_OpEx_EUR,
        "Total RES from PPA": el_RES_MWh,
        "Cost RES from PPA": c_RES_EUR,
        "Specific cost of total RES": sc_RES_PPA_EURpMWh,
        "Surplus RES": el_RES_surplus_MWh,
        "Used RES": el_RES_used_MWh,
        "Specific cost of used RES": sc_RES_used_EURpMWh,
        "Grid": el_grid_MWh,
        "Cost grid": c_grid_EUR,
        "Revenues from surplus sales": r_RES_surplus_sales_EURpMWh,
        "Total cost": c_Total_EUR,
        "Total NH3 out": NH3_out_tNH3,
        "Total discounted cost":c_Total_discounted_EUR,
        "Total discounted NH3 out": NH3_out_discounted

    }, index=multi_index)

    df_lcoa_T = df_lcoa.T

    # KPIs
    ###################################################################################################################
    # LCOA - monthly (EUR/tNH3)
    # Total CapEx (EUR)
    # Average annual NH3 production (tNH3)
    # Average annual NH3 CI (gCO2/MJ)
    # Average annual Haber-Bosch FLH (FLH)
    # Average annual Electrolysis FLH (FLH)
    # Average annual RES FLH (FLH)
    # Average annual RES production (MWh)
    # Average annual RES consumed (MWh)
    # Average annual RES surplus (MWh)
    # Curtailment (%)
    # Average annual Grid consumption (MWh)
    # Specific cost of produced RES (EUR/MWh)
    # Specific cost of consumed RES (EUR/MWh)
    # Specific cost of consumed RES + Grid (EUR/MWh)
    # Average annual Nr of Electrolysis Shutdowns
    # Average annual Electrolysis Shutdown Duration (hours)
    # Average annual Nr of Haber-Bosch Shutdowns
    # Average annual Haber-Bosch Shutdown Duration (hours)
    ###################################################################################################################

    # Average annual NH3 production (tNH3)
    avg_NH3_out_tNH3 = df_out_total.loc['sum', 'syn_NH3_out_tNH3'] / len(df_out_year)

    # Average NH3 CI (gCO2/MJ)
    avg_NH3_out_CI_gCO2pMJ = df_out_total.loc['mean', 'syn_NH3_out_ci_gCO2pMJ']

    # Average annual Haber-Bosch FLH (FLH)
    avg_HB_FLH = sum([i / HaberBosch_capacity_tNH3ph for i in df_out_year.syn_NH3_out_tNH3['sum'].tolist()]) / len(df_out_year)

    # Average annual Electrolysis FLH (FLH)
    avg_Ely_FLH = sum([i / Electrolysis_capacity_MW for i in df_out_year.el_el_in_MW['sum'].tolist()]) / len(df_out_year)

    # Average annual RES FLH (FLH)
    avg_RES_FLH = sum([i / (RES_Wind_Pnom_MW + RES_PV_Pnom_MW) for i in df_out_year.p_Total_RES_MW['sum'].tolist()]) / len(df_out_year)

    # Average annual RES production (MWh)
    avg_Total_RES_MWh = df_out_total.loc['sum', 'p_Total_RES_MW'] / len(df_out_year)

    # Average annual RES consumed (MWh)
    avg_RES_consumed_MWh = (df_out_total.loc['sum', 'p_Total_RES_MW'] - df_out_total.loc['sum', 'p_Surplus_RES_MW']) / len(df_out_year)

    # Average annual RES surplus (MWh)
    avg_RES_surplus_MWh = df_out_total.loc['sum', 'p_Surplus_RES_MW'] / len(df_out_year)

    # Curtailment (%)
    curtailment = df_out_total.loc['sum', 'p_Surplus_RES_MW'] / df_out_total.loc['sum', 'p_Total_RES_MW']

    # Average annual Grid consumption (MWh)
    avg_Grid_MWh = df_out_total.loc['sum', 'p_Grid_MW'] / len(df_out_year)

    # Specific cost of produced RES (EUR/MWh)
    sc_RES_out_EURpMWh = (df_out_total.loc['sum', 'p_Wind_MW'] * RES_Wind_PPA_price_EURpMWh + df_out_total.loc['sum', 'p_PV_MW'] * RES_PV_PPA_price_EURpMWh) / df_out_total.loc['sum', 'p_Total_RES_MW']

    # Specific cost of consumed RES (EUR/MWh)
    sc_RES_consumed_EURpMWh = sc_RES_out_EURpMWh * df_out_total.loc['sum', 'p_Total_RES_MW'] / (df_out_total.loc['sum', 'p_Total_RES_MW'] - df_out_total.loc['sum', 'p_Surplus_RES_MW'])

    # Specific cost of consumed RES + Grid (EUR/MWh)
    sc_RES_consumed_Grid_EURpMWh = (sc_RES_out_EURpMWh * df_out_total.loc['sum', 'p_Total_RES_MW'] + df_out_total.loc['sum', 'p_Grid_MW'] * Grid_price_EURpMWh) / (df_out_total.loc['sum', 'p_Total_RES_MW'] - df_out_total.loc['sum', 'p_Surplus_RES_MW'] + df_out_total.loc['sum', 'p_Grid_MW'])

    # Average annual Nr of Electrolysis Shutdowns
    el_SD = df_out.el_shutdown
    el_SD = el_SD[el_SD > 0]
    el_SD_agg = el_SD.agg(['count', 'sum', 'mean', 'max', 'min'])

    avg_Ely_SD_count = el_SD_agg['count'] / len(df_out_year)

    # Average Electrolysis Shutdown Duration (hours)
    avg_Ely_SD_duration = el_SD_agg['mean']

    # Average annual Electrolysis downtime (hours)
    avg_Ely_downtime = el_SD_agg['sum'] / len(df_out_year)

    # Average annual Nr of Haber-Bosch Shutdowns
    syn_SD = df_out.syn_shutdown
    syn_SD = syn_SD[syn_SD > 0]
    syn_SD_agg = syn_SD.agg(['count', 'sum', 'mean', 'max', 'min'])

    avg_HB_SD_count = syn_SD_agg['count'] / len(df_out_year)

    # Average Haber-Bosch Shutdown Duration (hours)
    avg_HB_SD_duration = syn_SD_agg['mean']

    # Average annual Haber-Bosch downtime (hours)
    avg_HB_downtime = syn_SD_agg['sum'] / len(df_out_year)

    # Set up KPI output Dataframe
    ###################################################################################################################

    dict_KPI = {
        'LCOA - monthly (EUR/tNH3)': LCOA,
        'Total CapEx (EUR)': CapEx_Total,
        'Average annual NH3 production (tNH3)': avg_NH3_out_tNH3,
        'Average annual NH3 CI (gCO2/MJ)': avg_NH3_out_CI_gCO2pMJ,
        'Average annual Haber-Bosch FLH (FLH)': avg_HB_FLH,
        'Average annual Electrolysis FLH (FLH)': avg_Ely_FLH,
        'Average annual RES FLH (FLH)': avg_RES_FLH,
        'Average annual RES production(MWh)': avg_Total_RES_MWh,
        'Average annual RES consumed (MWh)': avg_RES_consumed_MWh,
        'Average annual RES surplus (MWh)': avg_RES_surplus_MWh,
        'Curtailment (%)': curtailment,
        'Average annual Grid consumption (MWh)': avg_Grid_MWh,
        'Specific cost of produced RES (EUR/MWh)': sc_RES_out_EURpMWh,
        'Specific cost of consumed RES (EUR/MWh)': sc_RES_consumed_EURpMWh,
        'Specific cost of consumed RES + Grid (EUR/MWh)': sc_RES_consumed_Grid_EURpMWh,
        'Average annual Nr of Electrolysis Shutdowns': avg_Ely_SD_count,
        'Average Electrolysis Shutdown Duration (hours)': avg_Ely_SD_duration,
        'Average annual Electrolysis downtime (hours)': avg_Ely_downtime,
        'Average annual Nr of Haber-Bosch Shutdowns': avg_HB_SD_count,
        'Average Haber-Bosch Shutdown Duration (hours)': avg_HB_SD_duration,
        'Average annual Haber-Bosch downtime (hours)': avg_HB_downtime
    }

    dict_KPI = {key: float(value) for key, value in dict_KPI.items()}

    return df_lcoa_T, dict_KPI