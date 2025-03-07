import matplotlib.pyplot as plt
import numpy as np
import json
import tkinter as tk
from tkinter import filedialog
import pandas as pd

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

def randrange(n, vmin, vmax):
    """
    Helper function to make an array of random numbers having shape (n, )
    with each number distributed Uniform(vmin, vmax).
    """
    return (vmax - vmin)*np.random.rand(n) + vmin

fig = plt.figure()
ax = fig.add_subplot(projection='3d')

data = select_and_load_json()

xy_data = data["xy_input_data"]
plant_config_total = data["plant_config_total"]
KPI_total = data["KPI_total"]
print(KPI_total.keys())

x, y = zip(*xy_data["xy_input"])
x = list(x)
y = list(y)
LCOA = KPI_total["LCOA - monthly (EUR/tNH3)"]

data = pd.DataFrame({"x": x, "y": y, "KPI": LCOA})
data_filtered = data[data.KPI < 3000]

x = data_filtered.x.tolist()
y = data_filtered.y.tolist()
KPI = data_filtered.KPI.tolist()


ax.scatter(x, y, KPI, marker='o')

ax.set_xlabel('X Label')
ax.set_ylabel('Y Label')
ax.set_zlabel('Z Label')

plt.show()