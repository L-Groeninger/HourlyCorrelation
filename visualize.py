
####################################################################################################################
# visualize() performs output KPI analysis and visualizes them in a sorted plot.
# - Plant production shutdowns
# - Curtailment
# - Storage performance
# - Capacity factors Electrolysis & Haber-Bosch
# As an input the function requires
# - a plant configuration as is returned by plant_init() and
# - a plant calculation as is returned by plant_cals()
####################################################################################################################

import pandas as pd
import matplotlib.pyplot as plt

def visualize(df_out, plant_config, fig_name='EL_xxMW_RES_yyMW_BESS_zzMWh_cH2_vvt'):

    # Adjust output dataframe
    df_out['DateTimes'] = pd.to_datetime(df_out['DateTimes'], format='%Y-%m-%d %H:%M')
    df_out = df_out.drop(columns=['operation_mode'])
    df_out = df_out.drop([0])
    df_out.set_index('DateTimes', inplace=True)

    # print(df_out)

    # Data aggregation used for further KPI analysis
    ####################################################################################################################
    # Create aggregated data description on daily, monthly and annual basis
    df_out_day = df_out.resample('D').agg(['count', 'sum', 'mean', 'max', 'min'])
    df_out_month = df_out.resample('ME').agg(['count', 'sum', 'mean', 'max', 'min'])
    df_out_year = df_out.resample('YE').agg(['count', 'sum', 'mean', 'max', 'min'])
    df_out_total = df_out.agg(['count', 'sum', 'mean', 'max', 'min'])

    # print(df_out_day)
    # print(df_out_month)
    # print(df_out_year)
    # print(df_out_total)

    # Curtailment calculation
    ####################################################################################################################

    # Curtailment Berechnungen auf Tages, Monats, Jahres, Gesamtbasis
    curtailment_day = df_out_day.p_Surplus_RES_MW['sum'] / df_out_day.p_Total_RES_MW['sum'] * 100
    curtailment_month = df_out_month.p_Surplus_RES_MW['sum'] / df_out_month.p_Total_RES_MW['sum'] * 100
    curtailment_year = df_out_year.p_Surplus_RES_MW['sum'] / df_out_year.p_Total_RES_MW['sum'] * 100
    curtailment_total = df_out_total.loc['sum', 'p_Surplus_RES_MW'] / df_out_total.loc['sum', 'p_Total_RES_MW'] * 100

    curtailment_day.name = 'curtailment_day'
    curtailment_month.name = 'curtailment_month'
    curtailment_year.name = 'curtailment_year'

    # print(curtailment_day)
    # print(curtailment_month)
    # print(curtailment_year)
    # print(curtailment_total)

    df_curtailment = pd.concat([curtailment_month, curtailment_year], axis=1).sort_index(ascending=False).ffill().sort_index()
    df_curtailment['curtailment_total'] = curtailment_total

    # Plant utilization (capacity factors / FLH) Electrolyzer & Haber-Bosch
    ####################################################################################################################

    syn_NH3_out_tNH3_nom = plant_config['HaberBosch']['capacity_tNH3ph']['value']
    cf_syn_day = df_out_day.syn_NH3_out_tNH3['sum'] / (df_out_day.syn_NH3_out_tNH3['count'] * syn_NH3_out_tNH3_nom) * 100
    cf_syn_month = df_out_month.syn_NH3_out_tNH3['sum'] / (df_out_month.syn_NH3_out_tNH3['count'] * syn_NH3_out_tNH3_nom) * 100
    cf_syn_year = df_out_year.syn_NH3_out_tNH3['sum'] / (df_out_year.syn_NH3_out_tNH3['count'] * syn_NH3_out_tNH3_nom) * 100
    cf_syn_total = df_out_total.loc['sum', 'syn_NH3_out_tNH3'] / (df_out_total.loc['count', 'syn_NH3_out_tNH3'] * syn_NH3_out_tNH3_nom) * 100

    el_el_in_MW_nom = plant_config['Electrolysis']['capacity_MW']['value']
    cf_el_day = df_out_day.el_el_in_MW['sum'] / (df_out_day.el_el_in_MW['count'] * el_el_in_MW_nom) * 100
    cf_el_month = df_out_month.el_el_in_MW['sum'] / (df_out_month.el_el_in_MW['count'] * el_el_in_MW_nom) * 100
    cf_el_year = df_out_year.el_el_in_MW['sum'] / (df_out_year.el_el_in_MW['count'] * el_el_in_MW_nom) * 100
    cf_el_total = df_out_total.loc['sum', 'el_el_in_MW'] / (df_out_total.loc['count', 'el_el_in_MW'] * el_el_in_MW_nom) * 100

    cf_syn_day.name = 'cf_syn_day'
    cf_syn_month.name = 'cf_syn_month'
    cf_syn_year.name = 'cf_syn_year'
    cf_el_day.name = 'cf_el_day'
    cf_el_month.name = 'cf_el_month'
    cf_el_year.name = 'cf_el_year'

    df_cf = pd.concat([cf_syn_month, cf_syn_year, cf_el_month, cf_el_year], axis=1).sort_index(ascending=False).ffill().sort_index()
    df_cf['cf_syn_total'] = cf_syn_total
    df_cf['cf_el_total'] = cf_el_total



    # Shut down Analysis
    ####################################################################################################################

    all_years = pd.date_range(start=df_out.index.min(), end=df_out.index.max(), freq='YE')
    # print(all_years)

    syn_SD = df_out.syn_shutdown
    syn_SD = syn_SD[syn_SD > 0]
    syn_SD_agg = syn_SD.resample('YE').agg(['count', 'sum', 'mean', 'max', 'min'])
    syn_SD_agg = syn_SD_agg.reindex(all_years, fill_value=0)

    el_SD = df_out.el_shutdown
    el_SD = el_SD[el_SD > 0]
    el_SD_agg = el_SD.resample('YE').agg(['count', 'sum', 'mean', 'max', 'min'])
    el_SD_agg = el_SD_agg.reindex(all_years, fill_value=0)

    all_years = pd.date_range(start=df_out.index.min(), end=df_out.index.max(), freq='YE').year
    # print(all_years)

    syn_SD_plot_Data = [[0] for _ in all_years]
    el_SD_plot_Data = [[0] for _ in all_years]

    # Iterate over grouped data and replace the [0] only if there are values
    for year, group in syn_SD.groupby(syn_SD.index.year):
        if not group.empty:  # Ensure the group is not empty
            year_index = all_years.get_loc(year)  # Get index of the year
            syn_SD_plot_Data[year_index] = group.tolist()  # Replace with actual values

    for year, group in el_SD.groupby(el_SD.index.year):
        if not group.empty:  # Ensure the group is not empty
            year_index = all_years.get_loc(year)  # Get index of the year
            el_SD_plot_Data[year_index] = group.tolist()  # Replace with actual values

    # print(f"syn_SD: {syn_SD}")
    # print(f"syn_SD_agg: {syn_SD_agg}")
    # print(f"syn_SD_plot_Data: {syn_SD_plot_Data}")

    # print(f"el_SD: {el_SD}")
    # print(f"el_SD_agg: {el_SD_agg}")
    # print(f"el_SD_plot_Data: {el_SD_plot_Data}")

    # Data for step plots
    shutdown_counts_el = el_SD_agg['count'].tolist()  # Number of shutdowns per year
    shutdown_counts_syn = syn_SD_agg['count'].tolist()

    total_downtime_el = el_SD_agg['sum'].tolist()  # Total downtime per year
    total_downtime_syn = syn_SD_agg['sum'].tolist()


    ####################################################################################################################
    # Visualize
    ####################################################################################################################

    # Set up Figure
    fig, axs = plt.subplots(nrows=2, ncols=2, figsize=(18, 9))  # 1 row, 2 columns
    fig_name = 'EL_xxMW_RES_yyMW_BESS_zzMWh_cH2_vvt'
    fig.suptitle(fig_name)

    # Shutdown violin plots
    ####################################################################################################################
    x = list(range(1, len(el_SD_plot_Data) + 1))  # X-axis for years
    tick_label = all_years.tolist()

    # --- First Violin Plot with Step Overlay ---
    ax1 = axs[0, 0]
    ax1.violinplot(el_SD_plot_Data, showmeans=True, showmedians=True)
    ax1.set_title("Electrolysis Shut-Down analysis")

    # Secondary Y-axis for step plot
    ax1_sec = ax1.twinx()
    ax1_sec.step(x, shutdown_counts_el, where="mid", color="black", linestyle="--", label="Shutdown Count")
    ax1_sec.step(x, total_downtime_el, where="mid", color="red", linestyle="-", label="Total Downtime")
    ax1_sec.set_ylim(ymin=0)
    ax1_sec.set_ylabel("Annual Nr of shutdowns / annual total Downtime")
    ax1_sec.legend(loc="upper right")

    # --- Second Violin Plot with Step Overlay ---
    ax2 = axs[0, 1]
    ax2.violinplot(syn_SD_plot_Data, showmeans=True, showmedians=True)
    ax2.set_title("Haber-Bosch Shut-Down analysis")

    # Secondary Y-axis for step plot
    ax2_sec = ax2.twinx()
    ax2_sec.step(x, shutdown_counts_syn, where="mid", color="black", linestyle="--", label="Shutdown Count")
    ax2_sec.step(x, total_downtime_syn, where="mid", color="red", linestyle="-", label="Total Downtime")
    ax2_sec.set_ylim(ymin=0)
    ax2_sec.set_ylabel("Annual Nr of shutdowns / annual total Downtime")
    ax2_sec.legend(loc="upper right")

    # Adding horizontal grid lines
    for ax in axs[0]:
        ax.yaxis.grid(True)
        ax.set_xticks(x, labels=tick_label)
        ax.set_ylim(ymin=1)
        ax.set_ylabel("Shutdown duration")


    # Curtailment step plot
    ####################################################################################################################

    x = df_curtailment.index.tolist()
    ax3 = axs[1, 0]
    ax3.step(x, df_curtailment.curtailment_month, where='mid', label="curtailment_month")
    ax3.step(x, df_curtailment.curtailment_year, where='mid', label="curtailment_year")
    ax3.step(x, df_curtailment.curtailment_total, where='mid', label="curtailment_total")
    ax3.set_xlim(xmin=min(x), xmax=max(x))
    ax3.legend(loc="upper right")
    ax3.set_ylabel("Curtailment in %")
    ax3.set_title("Curtailment analysis")
    ax3.yaxis.grid(True)
    ax3.xaxis.grid(True)


    # Plant utilization - Electrolyzer & Haber-Bosch
    ####################################################################################################################

    x = df_cf.index.tolist()
    ax4 = axs[1, 1]
    ax4.step(x, df_cf.cf_syn_month, where='mid', label="cf_syn_month", linestyle='-', color='blue', alpha=0.4)
    ax4.step(x, df_cf.cf_syn_year, where='mid', label="cf_syn_year", linestyle='--', color='blue', alpha=0.7)
    ax4.step(x, df_cf.cf_syn_total, where='mid', label="cf_syn_total", linestyle='-.', color='blue', alpha=1.0)
    ax4.step(x, df_cf.cf_el_month, where='mid', label="cf_el_month", linestyle='-', color='orange', alpha=0.4)
    ax4.step(x, df_cf.cf_el_year, where='mid', label="cf_el_year", linestyle='--', color='orange', alpha=0.7)
    ax4.step(x, df_cf.cf_el_total, where='mid', label="cf_el_total", linestyle='-.', color='orange', alpha=1.0)
    ax4.set_xlim(xmin=min(x), xmax=max(x))
    ax4.legend(loc="upper right")
    ax4.set_ylabel("Capacity factor in %")
    ax4.set_title("Utilization analysis of Electrolyzer & Haber-Bosch-Syn")
    ax4.yaxis.grid(True)
    ax4.xaxis.grid(True)

    def cf_to_flh(y):
        return y / 100 * 8760

    def flh_to_cf(y):
        return y / 100 / 8760

    ax4_sec = ax4.secondary_yaxis(
        'right', functions=(cf_to_flh, flh_to_cf))
    ax4_sec.set_ylabel("Plant Full-Load-Hours")

    # Show plots
    ####################################################################################################################
    plt.tight_layout()
    plt.show()