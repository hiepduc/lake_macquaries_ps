#!/usr/bin/env python3

import xarray as xr
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import glob

# ======================================================
# MERRIWA CEILOMETER LOCATION
# ======================================================

LAT_SITE = -32.14
LON_SITE = 150.36

# ======================================================
# FORECAST NETCDF FILES
# ======================================================

forecast_dir = (
    "/mnt/climate/cas/ar_data/forecast/"
    "wrf-cmaq/ens1/2023-06-15T00/"
    "cmaq_jul23_gmr_nowhe//gmr/"
)

files = sorted(
    glob.glob(
        forecast_dir +
        "forecast--gmr--2023080*.nc"
    )
)

print()
print("Number of forecast files =", len(files))

# ======================================================
# READ ALL FORECAST FILES
# ======================================================

ds = xr.open_mfdataset(
    files,
    combine="by_coords"
)

print(ds)

# ======================================================
# FIND NEAREST GRID CELL
# ======================================================

latvals = ds["lat"].values
lonvals = ds["lon"].values

iy = np.abs(
    latvals - LAT_SITE
).argmin()

ix = np.abs(
    lonvals - LON_SITE
).argmin()

print()
print("Nearest grid point")
print("Latitude  =", latvals[iy])
print("Longitude =", lonvals[ix])
print("iy =", iy)
print("ix =", ix)

# ======================================================
# EXTRACT PBLH
# ======================================================

wrf_df = pd.DataFrame({
    "PBLH_WRF":
        ds["PBLH"][:, iy, ix].values
},
index=pd.to_datetime(
    ds["time"].values
))

wrf_df.index.name = "time"

# ======================================================
# CHECK TIME ZONE
# ======================================================
#
# Uncomment ONLY if time is UTC
#
# wrf_df.index = (
#     wrf_df.index
#     + pd.Timedelta(hours=10)
# )

print()
print("Forecast records =", len(wrf_df))
print()
print(wrf_df.head())

# ======================================================
# CEILOMETER FILES
# ======================================================

csv_files = [
    "L3_DEFAULT_0_20230801_Merriwa.csv",
    "L3_DEFAULT_0_20230802_Merriwa.csv",
    "L3_DEFAULT_0_20230803_Merriwa.csv",
    "L3_DEFAULT_0_20230804_Merriwa.csv",
    "L3_DEFAULT_0_20230805_Merriwa.csv",
    "L3_DEFAULT_0_20230806_Merriwa.csv",
    "L3_DEFAULT_0_20230807_Merriwa.csv",
    "L3_DEFAULT_0_20230808_Merriwa.csv",
    "L3_DEFAULT_0_20230809_Merriwa.csv"
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

print()
print(
    "Ceilometer hourly records =",
    len(ceilo_hourly)
)

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
)[0, 1]

mb = np.mean(
    wrf - obs
)

mae = np.mean(
    np.abs(wrf - obs)
)

rmse = np.sqrt(
    np.mean(
        (wrf - obs) ** 2
    )
)

nmb = (
    100.0 *
    np.sum(wrf - obs)
    /
    np.sum(obs)
)

fb = (
    100.0 *
    (
        wrf.mean() -
        obs.mean()
    )
    /
    (
        0.5 *
        (
            wrf.mean() +
            obs.mean()
        )
    )
)

print()
print("================================")
print("PBLH MODEL EVALUATION")
print("================================")
print(f"N    = {len(obs)}")
print(f"R    = {r:.3f}")
print(f"R²   = {r**2:.3f}")
print(f"MB   = {mb:.1f} m")
print(f"MAE  = {mae:.1f} m")
print(f"RMSE = {rmse:.1f} m")
print(f"NMB  = {nmb:.1f} %")
print(f"FB   = {fb:.1f} %")
print("================================")

# ======================================================
# TIME SERIES
# ======================================================

plt.figure(
    figsize=(15, 6)
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
    label="Forecast PBLH"
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
    "Date / Time"
)

plt.title(
    "Merriwa Ceilometer vs Forecast PBLH"
)

plt.grid(True)

plt.legend()

plt.tight_layout()

plt.show()

# ======================================================
# SCATTER PLOT
# ======================================================

plt.figure(
    figsize=(7, 7)
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
    [0, mx],
    [0, mx],
    "k--",
    linewidth=2,
    label="1:1"
)

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
    m * x + b,
    "r-",
    linewidth=2,
    label=f"y={m:.2f}x+{b:.0f}"
)

plt.xlabel(
    "Ceilometer PBLH (m)"
)

plt.ylabel(
    "Forecast PBLH (m)"
)

plt.title(
    f"PBLH Comparison\nR={r:.2f}  RMSE={rmse:.0f} m"
)

plt.grid(True)

plt.legend()

plt.tight_layout()

plt.show()

# ======================================================
# DIURNAL CYCLE
# ======================================================

diurnal = compare.copy()

diurnal["hour"] = diurnal.index.hour

hourly_mean = (
    diurnal
    .groupby("hour")
    .mean()
)

plt.figure(
    figsize=(10, 5)
)

plt.plot(
    hourly_mean.index,
    hourly_mean["CEILO_PBLH"],
    "-o",
    linewidth=2,
    label="Ceilometer"
)

plt.plot(
    hourly_mean.index,
    hourly_mean["WRF_PBLH"],
    "-o",
    linewidth=2,
    label="Forecast"
)

plt.xlabel("Hour")
plt.ylabel("PBLH (m)")
plt.title("Mean Diurnal PBLH")
plt.grid(True)
plt.legend()
plt.tight_layout()
plt.show()

