import pandas as pd
import numpy as np
import xlwings as xw
import modul

def main():
    pd.set_option("expand_frame_repr", False)
    pd.set_option("display.min_rows", 10)

    # Set up Modul Objects with plant parameters

    RES_Asset_Wind = modul.RES_Asset(
        Pnom_MW=100
    )

    RES_Asset_PV = modul.RES_Asset(
        Pnom_MW=50
    )

    BESS = modul.BESS(
        capacity_MWh=50,
        Pnom_MW=30,
        SOC_t0=0.5,
        flex_use=0.5,
        DoD=0.8,
        charge_eff=0.97,
        discharge_eff=0.97
    )

    H2Storage = modul.H2Storage(
        capacity_tH2=4,
        SOC_t0=0.5,
        flex_use=0.5
    )

    Electrolysis = modul.Electrolysis(
        capacity_MW=100,
        specific_el_MWhptH2=55,
        min_Load=0.15
    )

    HaberBosch = modul.HaberBosch(
        capacity_tNH3ph=7.5,
        specific_el_MWhptNH3=0.33,
        specific_H2_tH2ptNH3=0.18,
        min_Load=0.4,
        P_standby_MW=2
    )

    # Read .csv RES Data to pd dataframe
    file_path_Wind = r'RES_Data/20241126_Run_5_Wind_DE-SH_10_years_2010-01-01_2020-12-31/TS_Multiyear_Wind_DE-SH_2010-01-01_2020-12-31.csv'
    df_Wind = pd.read_csv(file_path_Wind, names=['DateTimes','Wind_CF'], header=None, index_col='DateTimes', skiprows=4)

    file_path_PV = r'RES_Data/20241126_Run_6_PV_DE-BY_10_years_2010-01-01_2020-12-31/TS_Multiyear_PV_DE-BY_2010-01-01_2020-12-31.csv'
    df_PV = pd.read_csv(file_path_PV, names=['DateTimes','PV_CF'], header=None, index_col='DateTimes', skiprows=4)

    # Create process state (SOC) and flow (el_in, el_out, etc) variables used for later iterative time series calculation
    # Numpy arrays are initialized with zeros() and set to the length of the read in RES-Data plus 1 to initialize Storage SOCs
    timesteps = len(df_PV) + 1

    p_Wind_CF = np.vstack((np.zeros(1),df_Wind.to_numpy()))
    p_Wind_MW = p_Wind_CF * RES_Asset_Wind.Pnom_MW
    p_PV_CF = np.vstack((np.zeros(1),df_PV.to_numpy()))
    p_PV_MW = p_PV_CF * RES_Asset_PV.Pnom_MW
    p_Total_RES_MW = p_Wind_MW + p_PV_MW
    p_Grid_MW = np.zeros((timesteps,1))
    el_el_in_MW = np.zeros((timesteps,1))
    el_H2_out_tH2 = np.zeros((timesteps,1))
    bess_el_in_MWh = np.zeros((timesteps,1))
    bess_el_charge_MWh = np.zeros((timesteps,1))
    bess_SOC_MWh = np.vstack((np.array(BESS.SOC_t0 * BESS.capacity_eff_MWh), np.zeros((timesteps - 1,1))))
    bess_el_discharge_MWh = np.zeros((timesteps, 1))
    bess_el_out_MWh = np.zeros((timesteps,1))
    bess_el_loss_MWh = np.zeros((timesteps,1))
    ch2_comp_el_in = np.zeros((timesteps,1))
    ch2_in_tH2 = np.zeros((timesteps,1))
    ch2_SOC = np.vstack((np.array(H2Storage.SOC_t0 * H2Storage.capacity_tH2), np.zeros((timesteps - 1,1))))
    ch2_out_tH2 = np.zeros((timesteps,1))
    syn_el_in_MWh = np.zeros((timesteps,1))
    syn_H2_in_tH2 = np.zeros((timesteps,1))
    syn_NH3_out_tNH3 = np.zeros((timesteps,1))

    # Iterative plant calculation

    for i in range(1, timesteps):
        total_pot_power = p_Total_RES_MW[i] + max(0, min(bess_SOC_MWh[i-1] * BESS.discharge_eff, BESS.Pnom_MW / BESS.discharge_eff))
        test = 2


    # SET UP OUTPUT DATAFRAME

    # Collect Column Names
    columns = [
        'p_Wind_CF',
        'p_Wind_MW',
        'p_PV_CF',
        'p_PV_MW',
        'p_Total_RES_MW',
        'p_Grid_MW',
        'el_el_in_MW',
        'el_H2_out_tH2',
        'bess_el_in_MWh',
        'bess_el_charge_MWh',
        'bess_SOC_MW',
        'bess_el_discharge_MWh',
        'bess_el_out_MWh',
        'bess_el_loss_MWh',
        'ch2_comp_el_in',
        'ch2_in_tH2',
        'ch2_SOC',
        'ch2_out_tH2',
        'syn_el_in_MWh',
        'syn_H2_in_tH2',
        'syn_NH3_out_tNH3'
    ]

    # Collect numpy array for calculated outputs in order of column names collected in columns[]
    calc_data = np.hstack((
        p_Wind_CF,
        p_Wind_MW,
        p_PV_CF,
        p_PV_MW,
        p_Total_RES_MW,
        p_Grid_MW,
        el_el_in_MW,
        el_H2_out_tH2,
        bess_el_in_MWh,
        bess_el_charge_MWh,
        bess_SOC_MWh,
        bess_el_discharge_MWh,
        bess_el_out_MWh,
        bess_el_loss_MWh,
        ch2_comp_el_in,
        ch2_in_tH2,
        ch2_SOC,
        ch2_out_tH2,
        syn_el_in_MWh,
        syn_H2_in_tH2,
        syn_NH3_out_tNH3
    ))

    # Initialize Output dataframe with columns-list and add DateTimes index from RES Data
    df_out = pd.DataFrame(calc_data,columns=columns)
    df_out.insert(0, 'DateTimes', [0] + df_Wind.index.tolist())
    print(df_out)

    wb = xw.Book('Output_Visualize.xlsm')
    sht = wb.sheets[0]
    sht.range("A10").value = df_out

if __name__ == '__main__':
    main()