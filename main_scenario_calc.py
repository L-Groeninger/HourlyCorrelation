
#################################################################################################################
# main_scenario_calc evaluates a specific plant configuration. Calculation data, plant configuration and LCOA
# calculation can be stored to csv format and/or transferred to excel for further assessment
#################################################################################################################

from plant_calc import *
from plant_init import *
from to_excel import *
from visualize import *
from kpi_calc import *
import json

def main():
    pd.set_option("expand_frame_repr", False)
    pd.set_option("display.min_rows", 10)


    # 1. Define plant configuration
    ##########################################
    # Use plant_init() key-value pairings i.e. 'BESS_capacity_MWh': xy
    plant_spec = {}
    ##########################################
    plant_config = plant_init(**plant_spec)
    print(json.dumps(plant_config, indent=4))


    # 2. Run plant calculation
    ##########################################
    df_out = plant_calc(plant_config=plant_config)
    print(df_out)


    # 3. KPI + LCOA calculation
    ##########################################
    KPI_calc_out = kpi_calc(df_out=df_out, plant_config=plant_config)

    df_lcoa = KPI_calc_out[0]
    print(df_lcoa)

    dict_KPI = KPI_calc_out[1]
    for key,value in dict_KPI.items():
        print(f"{key} : {round(value, 2)}")


    # 4. Transfer to Excel
    ##########################################
    transfer_to_excel = False
    ##########################################
    if transfer_to_excel:
        to_excel(df_out=df_out, plant_config=plant_config, df_lcoa=df_lcoa)


    # 5. Store df_out to out.csv
    ##########################################
    store_to_csv = False
    filepath = 'Output_Data/df_out_csv/'
    csv_name = ''
    ##########################################

    if store_to_csv:
        df_out.to_csv(filepath + csv_name, index=False)
        print(f"df_out stored to {filepath + csv_name}")


    # 6. Visualize KPI-Analysis
    ##########################################
    fig_name = ''
    ##########################################

    visualize(df_out, plant_config, fig_name=fig_name)


if __name__ == '__main__':
    main()