import time
import pandas as pd
from plant_calc import *
from plant_init import *
from kpi_calc import *

def runs1(runs):

    for _ in range(runs):
        plant_config = plant_init()
        # df_out = plant_calc(plant_config)
        # KPI_out = kpi_calc(df_out, plant_config)

def runs2(runs):

    for _ in range(runs):
        plant_config = plant_init()
        df_out = plant_calc(plant_config)
        # KPI_out = kpi_calc(df_out, plant_config)

def runs3(runs):

    for _ in range(runs):
        plant_config = plant_init()
        df_out = plant_calc(plant_config)
        KPI_out = kpi_calc(df_out, plant_config)


a = 4

for _ in range(a):
    start_time = time.perf_counter()
    runs1(1)
    end_time = time.perf_counter()

    elapsed_time = end_time - start_time
    print(f"Function runtime: {elapsed_time:.6f} seconds")

for _ in range(a):
    start_time = time.perf_counter()
    runs2(1)
    end_time = time.perf_counter()

    elapsed_time = end_time - start_time
    print(f"Function runtime: {elapsed_time:.6f} seconds")

for _ in range(a):
    start_time = time.perf_counter()
    runs3(1)
    end_time = time.perf_counter()

    elapsed_time = end_time - start_time
    print(f"Function runtime: {elapsed_time:.6f} seconds")