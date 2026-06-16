#!/usr/bin/env python3

from netCDF4 import Dataset
from wrf import getvar, ll_to_xy
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ======================================================
# MERRIWA CEILOMETER LOCATION
# ======================================================

LAT_SITE = -32.14
LON_SITE = 150.36

# ======================================================
# FORECAST PBLH FILES
# ======================================================

import glob
import xarray as xr

LAT_SITE = -32.14
LON_SITE = 150.36

files = sorted(
    glob.glob(
#        "/mnt/climate/cas/ar_data/forecast/wrf-cmaq/ens1/2023-07-01T00/cmaq_gmr_2023/gmr/forecast--gmr--*.nc"
#        "/mnt/climate/cas/ar_data/forecast/wrf-cmaq/ens1/2023-06-15T00/cmaq_jul23_gmr_nowhe/gmr/forecast*2023080*.nc"
          "/mnt/climate/cas/ar_data/forecast/wrf-cmaq/ens1/2023-09-10T00/fire54/nsw/forecast*2023091*.nc"
#        "/mnt/climate/cas/ar_data/forecast/wrf-cmaq/ens1/2023-09-10T00/fire54/sydney/forecast*2023091*.nc"
    )
)

print("Number of files =", len(files))

wrf_times = []
wrf_pblh = []

for f in files:

    print("Reading", f)

    ds = xr.open_dataset(f)

    # ----------------------------------------
    # nearest grid point
    # ----------------------------------------

    iy = np.abs(
        ds["lat"].values - LAT_SITE
    ).argmin()

    ix = np.abs(
        ds["lon"].values - LON_SITE
    ).argmin()

    # ----------------------------------------
    # extract time
    # ----------------------------------------

    t = pd.to_datetime(
        ds["time"].values[0]
    )

    # ----------------------------------------
    # extract PBLH
    # ----------------------------------------

    pblh = float(
        ds["PBLH"][0, iy, ix]
    )

    wrf_times.append(t)
    wrf_pblh.append(pblh)

    ds.close()

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

wrf_df = (
    wrf_df
    .sort_values("time")
    .set_index("time")
)
print()
print("WRF records =", len(wrf_df))
print(wrf_df.head())

ds = xr.open_dataset(files[0])
print(ds["time"].values)

# Check
print("\nForecast PBLH statistics")
print(
    "NaN values =",
    wrf_df["PBLH_WRF"].isna().sum()
)
print(
    "Min =",
    wrf_df["PBLH_WRF"].min()
)
print(
    "Max =",
    wrf_df["PBLH_WRF"].max()
)

# ======================================================
# CEILOMETER FILES
# ======================================================

csv_files = [
    "ceilodata/L3_DEFAULT_0_20230910_Merriwa.csv",
    "ceilodata/L3_DEFAULT_0_20230911_Merriwa.csv",
    "ceilodata/L3_DEFAULT_0_20230912_Merriwa.csv",
    "ceilodata/L3_DEFAULT_0_20230914_Merriwa.csv"
]

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

# Check
print("\nCeilometer PBLH statistics")
print(
    "NaN values =",
    ceilo_hourly["bl_height"].isna().sum()
)
print(
    "Min =",
    ceilo_hourly["bl_height"].min()
)
print(
    "Max =",
    ceilo_hourly["bl_height"].max()
)

# ======================================================
# FIND COMMON TIME PERIOD
# ======================================================

print("\nForecast period:")
print(wrf_df.index.min(), "to", wrf_df.index.max())

print("\nCeilometer period:")
print(
    ceilo_hourly.index.min(),
    "to",
    ceilo_hourly.index.max()
)

start_time = max(
    wrf_df.index.min(),
    ceilo_hourly.index.min()
)

end_time = min(
    wrf_df.index.max(),
    ceilo_hourly.index.max()
)

print("\nCommon period:")
print(start_time, "to", end_time)

# Trim both datasets to common period

wrf_df = wrf_df.loc[
    start_time:end_time
]

ceilo_hourly = ceilo_hourly.loc[
    start_time:end_time
]

print("\nRecords after trimming:")
print("Forecast =", len(wrf_df))
print("Ceilometer =", len(ceilo_hourly))

# ======================================================
# MATCH TIMES
# ======================================================

compare = pd.merge(
    wrf_df,
    ceilo_hourly[["bl_height"]],
    left_index=True,
    right_index=True,
    how="inner"
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

# Safety check

if len(compare) == 0:
    raise ValueError(
        "No matching valid PBLH data found "
        "after trimming and merging."
    )

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

print()
print("================================")
print("PBLH MODEL EVALUATION")
print("================================")
print(f"N    = {len(obs)}")
print(f"R    = {r:.3f}")
print(f"MB   = {mb:.1f} m")
print(f"MAE  = {mae:.1f} m")
print(f"RMSE = {rmse:.1f} m")
print(f"NMB  = {nmb:.1f} %")
print("================================")

# ======================================================
# TIME SERIES
# ======================================================

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
    "Merriwa Ceilometer vs WRF-Chem PBLH"
)

plt.grid(True)

plt.legend()

plt.tight_layout()

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
    f"Merriwa PBLH\nR={r:.2f} MB={mb:.0f} m"
)

plt.grid(True)

plt.legend()

plt.tight_layout()

plt.show()

