import numpy as np
import json
import matplotlib.pyplot as plt
from scipy.interpolate import griddata


import json
import tkinter as tk
from tkinter import filedialog

def select_and_load_json():
    """Opens a file dialog to select a JSON file and loads its contents into a variable."""
    # Initialize Tkinter (hide main window)
    root = tk.Tk()
    root.withdraw()  # Hide the root window

    # Bring the file dialog to the front
    root.lift()
    root.attributes("-topmost", True)
    root.update()

    # Open file explorer to select a JSON file
    file_path = filedialog.askopenfilename(
        title="Select a JSON file",
        filetypes=[("JSON Files", "*.json")],  # Only allow JSON files
    )

    if not file_path:
        print("No file selected.")
        return None  # Exit function if no file is selected

    # Load the JSON file
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"File loaded successfully: {file_path}")
        return data
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        return None

# Given data

data = select_and_load_json()
print(data)

xy_data = data["xy_input_data"]
plant_config_total = data["plant_config_total"]
KPI_total = data["KPI_total"]
x, y = zip(*xy_data["xy_input"])
x = list(x)
y = list(y)
LCOA = KPI_total["LCOA - monthly (EUR/tNH3)"]

print(x)
print(y)
print(LCOA)

data = [x, y, LCOA]

# Extract x, y, and KPI
x = np.array(data[0])
y = np.array(data[1])
kpi = np.array(data[2])

# Create a grid for interpolation
xi = np.linspace(min(x), max(x), 100)  # Fine grid in x
yi = np.linspace(min(y), max(y), 100)  # Fine grid in y
X, Y = np.meshgrid(xi, yi)

# Interpolate KPI values over the grid
Z = griddata((x, y), kpi, (X, Y), method='cubic')

# Plot the heatmap
plt.figure(figsize=(8, 6))
contour = plt.contourf(X, Y, Z, levels=20, cmap='viridis')  # 'cubic' interpolation
plt.colorbar(contour, label="KPI Value")
plt.scatter(x, y, color='red', marker='o', label="Evaluation Points")  # Mark original points
plt.xlabel("X")
plt.ylabel("Y")
plt.title("Interpolated KPI Heatmap")
plt.legend()
plt.show()