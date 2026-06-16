#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import xarray as xr
import numpy as np

# ==========================================================
# INPUT FILE
# ==========================================================
excel_file = "noxso2flowrate.xlsx"

# ==========================================================
# POWER STATION INFO
# ==========================================================
LAT = -33.161
LON = 151.541

STACK_HEIGHT = 178.0
STACK_DIAMETER = 10.3
EXIT_VELOCITY = 26.0
EXIT_TEMPERATURE = 369.0

# ==========================================================
# READ DATA
# ==========================================================
df = pd.read_excel(excel_file, engine="openpyxl")

df.rename(columns={df.columns[0]: "Time"}, inplace=True)
df["Time"] = pd.to_datetime(df["Time"], dayfirst=True)
df.set_index("Time", inplace=True)

# ==========================================================
# EMISSION & FLOW COLUMNS
# ==========================================================
nox_cols = [
    "5A NOx (mg/m3)",
    "5B NOx (mg/m3)",
    "6A NOx (mg/m3)",
    "6B NOx (mg/m3)"
]

so2_cols = [
    "5A SO2 (mg/m3)",
    "5B SO2 (mg/m3)",
    "6A SO2 (mg/m3)",
    "6B SO2 (mg/m3)"
]

stack_map = {
    "5A": "U5 DUCT A Flow (m3/s)",
    "5B": "U5 DUCT B Flow (m3/s)",
    "6A": "U6 DUCT C Flow (m3/s)",
    "6B": "U6 DUCT D Flow (m3/s)"
}

# ==========================================================
# MW (GENERATION) COLUMNS  <<< IMPORTANT
# ==========================================================
mw_map = {
    "5A": "U5A MW",
    "5B": "U5B MW",
    "6A": "U6A MW",
    "6B": "U6B MW"
}

MW_THRESHOLD = 10.0  # MW cutoff for ON/OFF

# ==========================================================
# FILL INPUT DATA (conservative interpolation)
# ==========================================================
print("\nChecking missing input data...\n")

all_input_cols = nox_cols + so2_cols + list(stack_map.values())

for col in all_input_cols:
    if col in df.columns:
        n_missing = df[col].isna().sum()
        if n_missing > 0:
            print(f"{col}: {n_missing} missing values")

        df[col] = df[col].interpolate(method="time")
        df[col] = df[col].bfill().ffill()

# ==========================================================
# CLEAN MW DATA
# ==========================================================
mw_cols = list(mw_map.values())

for col in mw_cols:
    if col in df.columns:
        df[col] = df[col].interpolate(method="time")
        df[col] = df[col].bfill().ffill()

# ==========================================================
# OPERATING MASK (REAL PHYSICAL LOGIC)
# ==========================================================
operating_mask = pd.DataFrame(index=df.index)

for stack, mw_col in mw_map.items():
    if mw_col in df.columns:
        operating_mask[stack] = df[mw_col] > MW_THRESHOLD
    else:
        operating_mask[stack] = True  # fallback if MW missing

# ==========================================================
# EMISSION CALCULATION (g/s WITH ON/OFF CONTROL)
# ==========================================================
for stack, flow_col in stack_map.items():

    nox_gm3 = df[f"{stack} NOx (mg/m3)"] / 1000.0
    so2_gm3 = df[f"{stack} SO2 (mg/m3)"] / 1000.0
    flow = df[flow_col]

    nox_raw = nox_gm3 * flow
    so2_raw = so2_gm3 * flow

    is_running = operating_mask[stack]

    df[f"NOx_{stack}_gs"] = np.where(is_running, nox_raw, 0.0)
    df[f"SO2_{stack}_gs"] = np.where(is_running, so2_raw, 0.0)

# ==========================================================
# OPTIONAL: INTERPOLATION ONLY WHEN UNIT IS ON
# ==========================================================
emission_vars = [
    "NOx_5A_gs", "NOx_5B_gs", "NOx_6A_gs", "NOx_6B_gs",
    "SO2_5A_gs", "SO2_5B_gs", "SO2_6A_gs", "SO2_6B_gs"
]

for var in emission_vars:
    stack = var.split("_")[1]  # 5A, 5B, etc.
    mask = operating_mask[stack]

    # interpolate only during operation
    df.loc[mask, var] = df.loc[mask, var].interpolate(method="time")

    # enforce zero during OFF periods
    df.loc[~mask, var] = 0.0

# ==========================================================
# TOTAL EMISSIONS
# ==========================================================
df["TOTAL_NOx_gs"] = (
    df["NOx_5A_gs"] +
    df["NOx_5B_gs"] +
    df["NOx_6A_gs"] +
    df["NOx_6B_gs"]
)

df["TOTAL_SO2_gs"] = (
    df["SO2_5A_gs"] +
    df["SO2_5B_gs"] +
    df["SO2_6A_gs"] +
    df["SO2_6B_gs"]
)

# ==========================================================
# PLOTS
# ==========================================================
plt.figure(figsize=(16,6))

for stack in stack_map:
    plt.plot(df.index, df[f"NOx_{stack}_gs"], label=f"{stack} NOx", linewidth=0.8)

plt.plot(df.index, df["TOTAL_NOx_gs"], label="TOTAL NOx", linewidth=2)
plt.title("Hourly NOx Emission Rate")
plt.ylabel("g/s")
plt.xlabel("Time")
plt.legend()
plt.grid()
plt.tight_layout()
plt.savefig("NOx_emission_rate.png", dpi=300)

plt.figure(figsize=(16,6))

for stack in stack_map:
    plt.plot(df.index, df[f"SO2_{stack}_gs"], label=f"{stack} SO2", linewidth=0.8)

plt.plot(df.index, df["TOTAL_SO2_gs"], label="TOTAL SO2", linewidth=2)
plt.title("Hourly SO2 Emission Rate")
plt.ylabel("g/s")
plt.xlabel("Time")
plt.legend()
plt.grid()
plt.tight_layout()
plt.savefig("SO2_emission_rate.png", dpi=300)

# ==========================================================
# DAILY MEAN
# ==========================================================
daily = df.resample("D").mean()

# ==========================================================
# SAVE FILES
# ==========================================================
csv_out = "VPPS_hourly_emission_rates.csv"
df.to_csv(csv_out)

# ==========================================================
# NETCDF OUTPUT
# ==========================================================
nt = len(df)

ds = xr.Dataset(coords={"Time": df.index.values})

ds["lat"] = ("Time", np.full(nt, LAT))
ds["lon"] = ("Time", np.full(nt, LON))

ds["stack_height"] = STACK_HEIGHT
ds["stack_diameter"] = STACK_DIAMETER
ds["exit_velocity"] = EXIT_VELOCITY
ds["exit_temperature"] = EXIT_TEMPERATURE

vars_to_save = emission_vars + ["TOTAL_NOx_gs", "TOTAL_SO2_gs"]

for var in vars_to_save:
    ds[var] = ("Time", df[var].values)
    ds[var].attrs["units"] = "g s-1"

ds.attrs["title"] = "VPPS hourly stack emissions"
ds.attrs["power_station"] = "Vales Point Power Station"
ds.attrs["latitude"] = LAT
ds.attrs["longitude"] = LON

nc_out = "VPPS_hourly_emissions.nc"
ds.to_netcdf(nc_out)

# ==========================================================
# FINAL OUTPUT
# ==========================================================
print("\nFinished.")
print("\nCreated files:")
print(f"  {csv_out}")
print(f"  {nc_out}")
print("  NOx_emission_rate.png")
print("  SO2_emission_rate.png")

plt.show()

