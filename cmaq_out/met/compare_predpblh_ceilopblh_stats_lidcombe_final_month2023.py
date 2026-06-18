#!/usr/bin/env python3
import glob
from netCDF4 import Dataset
from wrf import getvar, ll_to_xy
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ======================================================
# Lidcombe CEILOMETER LOCATION
# ======================================================

LAT_SITE = -33.89
LON_SITE = 151.05

# ======================================================
# WRF FILES
# ======================================================

wrf_files = sorted(
    glob.glob("/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02*")
)

#wrf_files = [
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-01_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-02_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-03_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-04_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-05_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-06_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-07_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-08_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-09_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-10_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-11_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-12_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-13_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-14_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-15_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-16_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-17_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-18_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-19_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-20_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-21_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-22_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-23_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-24_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-25_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-26_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-27_00:00:00",
#    "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-02-28_00:00:00"
#]

wrf_times = []
wrf_pblh = []

for wrf_file in wrf_files:

    print("Reading", wrf_file)

    nc = Dataset(wrf_file)

    xy = ll_to_xy(
        nc,
        LAT_SITE,
        LON_SITE
    )

    ix = int(xy[0])
    iy = int(xy[1])

    pblh = getvar(nc, "PBLH", timeidx=None)
    times = getvar(nc, "times", timeidx=None)

    print("PBLH shape =", pblh.shape)

    # --------------------------------------------------
    # Multiple time records
    # --------------------------------------------------
    if pblh.ndim == 3:

        nt = pblh.shape[0]

        for t in range(nt):

            wrf_times.append(
                pd.to_datetime(times.values[t])
            )

            wrf_pblh.append(
                float(pblh[t, iy, ix])
            )

    # --------------------------------------------------
    # Single time record
    # --------------------------------------------------
    elif pblh.ndim == 2:

        wrf_times.append(
            pd.to_datetime(times.values[0])
        )

        wrf_pblh.append(
            float(pblh[iy, ix])
        )

    else:

        raise ValueError(
            f"Unexpected PBLH dimensions: {pblh.shape}"
        )

# ======================================================
# UTC -> AEST
# ======================================================

wrf_times = (
    pd.to_datetime(wrf_times)
    + pd.Timedelta(hours=10)
)

wrf_df = pd.DataFrame({
    "time": wrf_times,
    "PBLH_WRF": wrf_pblh
})

wrf_df = wrf_df.set_index("time")

print()
print("WRF records =", len(wrf_df))

# ======================================================
# CEILOMETER FILES
# ======================================================

csv_files = sorted(
    glob.glob("ceilodata/L3_DEFAULT__202302*_Lidcombe.csv")
)

#csv_files = [
#    "ceilo_data/L3_DEFAULT_0_20231206_Lidcombe.csv",
#    "ceilo_data/L3_DEFAULT_0_20231207_Lidcombe.csv",
#    "ceilo_data/L3_DEFAULT_0_20231208_Lidcombe.csv",
#    "ceilo_data/L3_DEFAULT_0_20231209_Lidcombe.csv",
#    "ceilo_data/L3_DEFAULT_0_20231210_Lidcombe.csv",
#    "ceilo_data/L3_DEFAULT_0_20231211_Lidcombe.csv",
#    "ceilo_data/L3_DEFAULT_0_20231212_Lidcombe.csv",
#    "ceilo_data/L3_DEFAULT_0_20231213_Lidcombe.csv",
#    "ceilo_data/L3_DEFAULT_0_20231214_Lidcombe.csv",
#    "ceilo_data/L3_DEFAULT_0_20231215_Lidcombe.csv",
#    "ceilo_data/L3_DEFAULT_0_20231216_Lidcombe.csv",
#    "ceilo_data/L3_DEFAULT_0_20231217_Lidcombe.csv",
#    "ceilo_data/L3_DEFAULT_0_20231218_Lidcombe.csv",
#    "ceilo_data/L3_DEFAULT_0_20231219_Lidcombe.csv"
#    "ceilo_data/L3_DEFAULT_0_20231220_Lidcombe.csv"
#]

dfs = []

for f in csv_files:

    print("Reading", f)

    df = pd.read_csv(f)

    df["Time"] = pd.to_datetime(
        df["# Time"],
        dayfirst=True
    )

    df["bl_height"] = pd.to_numeric(
        df["bl_height"],
        errors="coerce"
    )

    # remove invalid values
    df.loc[
        df["bl_height"] < 0,
        "bl_height"
    ] = np.nan

    dfs.append(df)

ceilo = pd.concat(
    dfs,
    ignore_index=True
)

ceilo = ceilo.sort_values(
    "Time"
)

# ======================================================
# HOURLY CEILOMETER PBLH
# ======================================================

ceilo_hourly = (
    ceilo
    .set_index("Time")
    .resample("1H")
    .median(numeric_only=True)
)

print("Ceilometer hourly records =", len(ceilo_hourly))

# ======================================================
# MATCH TIMES
# ======================================================

compare = pd.concat(
    [
        wrf_df["PBLH_WRF"],
        ceilo_hourly["bl_height"]
    ],
    axis=1
)

compare.columns = [
    "WRF_PBLH",
    "CEILO_PBLH"
]

compare = compare.dropna()

print()
print(compare.head())
print()
print("Matched hours =", len(compare))

# ======================================================
# STATISTICS
# ======================================================

wrf = compare["WRF_PBLH"].values
obs = compare["CEILO_PBLH"].values

r = np.corrcoef(
    obs,
    wrf
)[0,1]

mb = np.mean(
    wrf - obs
)

mae = np.mean(
    np.abs(wrf - obs)
)

rmse = np.sqrt(
    np.mean(
        (wrf - obs)**2
    )
)

nmb = (
    100.0 *
    np.sum(wrf - obs)
    /
    np.sum(obs)
)

stats_text = (
    "\n"
    "================================\n"
    "PBLH MODEL EVALUATION\n"
    "================================\n"
    f"N    = {len(obs)}\n"
    f"R    = {r:.3f}\n"
    f"MB   = {mb:.1f} m\n"
    f"MAE  = {mae:.1f} m\n"
    f"RMSE = {rmse:.1f} m\n"
    f"NMB  = {nmb:.1f} %\n"
    "================================\n"
)

print()
print(stats_text)

with open("PBLH_statistics.txt", "w") as f:
    f.write(stats_text)

print("Saved: PBLH_statistics.txt")

# ======================================================
# TIME SERIES
# ======================================================
outfile = "PBLH_WRF_CEILO.png"

plt.figure(
    figsize=(15,6)
)

plt.scatter(
    ceilo["Time"],
    ceilo["bl_height"],
    s=1,
    alpha=0.15,
    label="Ceilometer Raw"
)

plt.plot(
    ceilo_hourly.index,
    ceilo_hourly["bl_height"],
    linewidth=2,
    label="Ceilometer Hourly"
)

plt.plot(
    wrf_df.index,
    wrf_df["PBLH_WRF"],
    "-o",
    markersize=4,
    linewidth=2,
    label="WRF-Chem"
)

stats_text = (
    f"R = {r:.2f}\n"
    f"MB = {mb:.0f} m\n"
    f"RMSE = {rmse:.0f} m"
)

plt.text(
    0.02,
    0.98,
    stats_text,
    transform=plt.gca().transAxes,
    va="top",
    bbox=dict(facecolor="white")
)

plt.ylabel(
    "PBL Height (m)"
)

plt.xlabel(
    "Date / Time (AEST)"
)

plt.title(
    "Lidcombe Ceilometer vs WRF-Chem PBLH"
)

plt.grid(True)

plt.legend()

plt.tight_layout()

plt.savefig(outfile, dpi=300)
print("Saved:", outfile)

plt.show()

# ======================================================
# SCATTER PLOT
# ======================================================

plt.figure(
    figsize=(7,7)
)

plt.scatter(
    obs,
    wrf,
    alpha=0.6
)

mx = max(
    obs.max(),
    wrf.max()
)

plt.plot(
    [0,mx],
    [0,mx],
    'k--',
    linewidth=2,
    label="1:1"
)

# regression line
m, b = np.polyfit(
    obs,
    wrf,
    1
)

x = np.linspace(
    0,
    mx,
    100
)

plt.plot(
    x,
    m*x+b,
    'r-',
    linewidth=2,
    label=f"y={m:.2f}x+{b:.0f}"
)

plt.xlabel(
    "Ceilometer PBLH (m)"
)

plt.ylabel(
    "WRF-Chem PBLH (m)"
)

plt.title(
    f"Lidcombe PBLH\nR={r:.2f} MB={mb:.0f} m"
)

plt.grid(True)

plt.legend()

plt.tight_layout()

plt.show()

