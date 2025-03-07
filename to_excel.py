

import xlwings as xw

def to_excel(df_out, plant_config, df_lcoa):
    ####################################################################################################################
    # Transfer Data to Excel
    ####################################################################################################################

    wb = xw.Book('Output_Data/Output_Visualize.xlsm')

    # Store df_out to Calc_RAW sheet
    sht = wb.sheets['Calc_RAW']
    # sht.clear_contents()
    sht.range("A1").value = df_out

    # Store plant_config to Plant_Config sheet by converting
    sht = wb.sheets['Plant_Config']
    # sht.clear_contents()

    data = [["Category", "Parameter", "Value", "Unit"]]  # Table headers

    for category, params in plant_config.items():
        for param, details in params.items():
            value = details.get('value', 'N/A')  # Get value, default to 'N/A' if missing
            unit = details.get('unit', '')  # Get unit, default to empty string if missing
            data.append([category, param, value, unit])

    sht.range("A1").value = data

    # Store df_lc to Levelized_Cost
    sht = wb.sheets['Levelized_Cost']
    # sht.clear_contents()
    sht.range("A1").value = df_lcoa
