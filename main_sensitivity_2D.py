
#################################################################################################################
# main_sensitivity_2D iterates through two input parameters and returns a result dictionary of plant configurations and
#################################################################################################################

from plant_calc import *
from plant_init import *
from kpi_calc import *
import json
import time
import os
import tkinter as tk
from tkinter import filedialog

def generate_xy_inputs(x, y, x0, y0, dx, dy, x_steps, y_steps):
    xy_input = []
    for i in range(x_steps + 1):
        for j in range(y_steps + 1):
            x_j = x0 + i * dx
            y_j = y0 + j * dy
            xy_input.append((x_j, y_j))
    xy_input_data = {"x": x, "y": y, "xy_input": xy_input}
    return xy_input_data

def calc_2D(xy_input_data):
    x = xy_input_data["x"]
    y = xy_input_data["y"]
    xy_input = xy_input_data["xy_input"]

    # Initialize dictionaries to store results
    plant_config_total = {}
    KPI_total = {}

    total_steps = len(xy_input)

    for step, (i_x, i_y) in enumerate(xy_input, start=1):
        # Compute percentage progress
        percent = (step / total_steps) * 100

        # Print progress message
        print(f"Progress: {percent:.2f}% (step {step} of {total_steps})")

        # Create input dictionary for initialization
        plant_init_input = {x: i_x, y: i_y}

        # Initialize plant configuration
        plant_config = plant_init(**plant_init_input)

        # Perform calculations
        df_out = plant_calc(plant_config=plant_config)
        KPI_calc_out = kpi_calc(df_out=df_out, plant_config=plant_config)

        # Extract KPI dictionary
        dict_KPI = KPI_calc_out[1]

        # Function to recursively extract 'value' fields from plant_config
        def extract_values(nested_dict, parent_key=""):
            for key, sub_dict in nested_dict.items():
                if isinstance(sub_dict, dict) and 'value' in sub_dict:
                    full_key = f"{parent_key}.{key}" if parent_key else key
                    if full_key not in plant_config_total:
                        plant_config_total[full_key] = []
                    plant_config_total[full_key].append(sub_dict['value'])
                elif isinstance(sub_dict, dict):  # Recursively go deeper
                    extract_values(sub_dict, parent_key=f"{parent_key}.{key}" if parent_key else key)

        # Extract and store plant_config values
        extract_values(plant_config)

        # Store dict_KPI values iteratively
        for key, value in dict_KPI.items():
            if key not in KPI_total:
                KPI_total[key] = []
            KPI_total[key].append(value)

    return plant_config_total, KPI_total

def store_results(x, y, data):
    """Stores the given dictionary (consisting of KPI and plant_config data) into JSON files."""
    # Initialize Tkinter (hide main window)
    root = tk.Tk()
    root.withdraw()

    # Bring the window to the foreground
    root.lift()  # Lift the window to the front
    root.attributes("-topmost", True)  # Make sure the window stays on top
    root.update()  # Ensure the update is applied before opening the file dialog

    # Select save location (where JSON file will be stored)
    save_directory = filedialog.askdirectory(title="Select Directory to Save JSON File")
    if not save_directory:
        print("No save directory selected. Files not saved.")
        return  # Exit function

    # Ask for base filename
    filename = input("Enter the filename (without extension): ")

    # Construct file paths
    file = os.path.join(save_directory, f"{filename}_x_{x}_y_{y}.json")

    # Store data in JSON format
    with open(file, "w") as f:
        json.dump(data, f, indent=4)

    print(f"File saved at: - {file}")


def main():
    pd.set_option("expand_frame_repr", False)
    pd.set_option("display.min_rows", 10)

    # 1. Define sensitive parameters
    # Choose x and y according to plant_init() keys
    ##########################################
    x = 'RES_Asset_Wind_Pnom_MW'
    x0 = 50
    dx = 5
    x_steps = 40

    y = 'RES_Asset_PV_Pnom_MW'
    y0 = 50
    dy = 5
    y_steps = 10
    ##########################################
    xy_input_data = generate_xy_inputs(x, y, x0, y0, dx, dy, x_steps, y_steps)
    print(xy_input_data)


    # 2. Iterative calculation of input configurations input(x,y)
    ##########################################
    calc_2D_out = calc_2D(xy_input_data)

    plant_config_total = calc_2D_out[0]
    KPI_total = calc_2D_out[1]

    print('KPI_total')
    for key,value in KPI_total.items():
        print(f"{key} : {value}")

    print('plant_config_total')
    for key,value in plant_config_total.items():
        print(f"{key} : {value}")


    # 3. Request input whether results shall be stored or not
    ##########################################
    results_store = ""

    while results_store not in ("Y", "N"):
        results_store = input("Shall results be stored? Input Y/N: ").capitalize()
        if results_store not in ("Y", "N"): print("Invalid entry!")

    if results_store == "Y":
        data = {"xy_input_data": xy_input_data, "plant_config_total": plant_config_total, "KPI_total": KPI_total}
        store_results(x, y, data)
    else:
        print("Results will not be stored.")


if __name__ == '__main__':
    start_time = time.perf_counter()
    main()
    end_time = time.perf_counter()

    elapsed_time = end_time - start_time
    print(f"Function runtime: {elapsed_time:.6f} seconds")