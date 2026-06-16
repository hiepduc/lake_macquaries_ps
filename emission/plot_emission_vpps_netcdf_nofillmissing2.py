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
# COLUMNS
# ==========================================================
stack_map = {
    "5A": "U5 DUCT A Flow (m3/s)",
    "5B": "U5 DUCT B Flow (m3/s)",
    "6A": "U6 DUCT C Flow (m3/s)",
    "6B": "U6 DUCT D Flow (m3/s)"
}


mw_map = {
    "5A": "Unit 5 Load (MW)",
    "5B": "Unit 5 Load (MW)",
    "6A": "Unit 6 Load (MW)",
    "6B": "Unit 6 Load (MW)"
}


MW_THRESHOLD = 10.0

print(df.columns.tolist())

print(
    "Unit 5 load <10 MW:",
    (df["Unit 5 Load (MW)"] < 10).sum()
)

print(
    "Unit 6 load <10 MW:",
    (df["Unit 6 Load (MW)"] < 10).sum()
)

print(
    "Missing Unit 5 load:",
    df["Unit 5 Load (MW)"].isna().sum()
)

print(
    "Missing Unit 6 load:",
    df["Unit 6 Load (MW)"].isna().sum()
)

for col in [
    "5A NOx (mg/m3)",
    "5B NOx (mg/m3)",
    "5A SO2 (mg/m3)",
    "5B SO2 (mg/m3)",
    "6A NOx (mg/m3)",
    "6B NOx (mg/m3)",
]:
    print(col, df[col].isna().sum())

# ==========================================================
# INPUT CLEANING (SAFE ONLY)
# ==========================================================
all_input_cols = list(stack_map.values()) + [
    "5A NOx (mg/m3)", "5B NOx (mg/m3)", "6A NOx (mg/m3)", "6B NOx (mg/m3)",
    "5A SO2 (mg/m3)", "5B SO2 (mg/m3)", "6A SO2 (mg/m3)", "6B SO2 (mg/m3)"
]

#for col in all_input_cols:
#    if col in df.columns:
#        df[col] = df[col].interpolate(method="time")
#        df[col] = df[col].bfill().ffill()

# ==========================================================
# MW CLEANING (CRITICAL FIX)
# ==========================================================
#for col in mw_map.values():
#    if col in df.columns:

        # IMPORTANT: DO NOT ffill large gaps
        # preserve shutdowns
#        df[col] = df[col].interpolate(method="time", limit=1)

# ==========================================================
# OPERATING MASK (ROBUST FIX)
# ==========================================================
operating_mask = pd.DataFrame(index=df.index)

for stack, mw_col in mw_map.items():
    if mw_col in df.columns:

        mw = df[mw_col].copy()

        # raw ON/OFF
        is_on = mw > MW_THRESHOLD

        # smooth single-point noise (optional but important)
        is_on = is_on.rolling(3, center=True, min_periods=1).max()

        operating_mask[stack] = is_on

    else:
        operating_mask[stack] = True

# ==========================================================
# EMISSION CALCULATION (STRICT PHYSICAL LOGIC)
# ==========================================================
for stack, flow_col in stack_map.items():

    nox_gm3 = df[f"{stack} NOx (mg/m3)"] / 1000.0
    so2_gm3 = df[f"{stack} SO2 (mg/m3)"] / 1000.0
    flow = df[flow_col]

    nox_raw = nox_gm3 * flow
    so2_raw = so2_gm3 * flow

    is_running = operating_mask[stack]

    # INIT
    df[f"NOx_{stack}_gs"] = 0.0
    df[f"SO2_{stack}_gs"] = 0.0

    # APPLY ONLY WHEN RUNNING
    df.loc[is_running, f"NOx_{stack}_gs"] = nox_raw[is_running]
    df.loc[is_running, f"SO2_{stack}_gs"] = so2_raw[is_running]

    # OPTIONAL: smooth ONLY within ON periods
    run_blocks = (is_running != is_running.shift()).cumsum()

    for _, block in df[is_running].groupby(run_blocks):
        idx = block.index

        df.loc[idx, f"NOx_{stack}_gs"] = df.loc[idx, f"NOx_{stack}_gs"].interpolate(method="time")
        df.loc[idx, f"SO2_{stack}_gs"] = df.loc[idx, f"SO2_{stack}_gs"].interpolate(method="time")

# ==========================================================
# TOTAL EMISSIONS
# ==========================================================
df["TOTAL_NOx_gs"] = (
    df["NOx_5A_gs"] + df["NOx_5B_gs"] +
    df["NOx_6A_gs"] + df["NOx_6B_gs"]
)

df["TOTAL_SO2_gs"] = (
    df["SO2_5A_gs"] + df["SO2_5B_gs"] +
    df["SO2_6A_gs"] + df["SO2_6B_gs"]
)

# ==========================================================
# DEBUG CHECK (IMPORTANT)
# ==========================================================
for stack, mw_col in mw_map.items():
    if mw_col in df.columns:
        print(f"\n{stack}")
        print("MW min:", df[mw_col].min())
        print("MW max:", df[mw_col].max())
        print("MW < 10 hours:", (df[mw_col] < MW_THRESHOLD).sum())

# ==========================================================
# PLOTS
# ==========================================================
plt.figure(figsize=(16,6))

for stack in stack_map:
    plt.plot(df.index, df[f"NOx_{stack}_gs"], label=f"{stack} NOx", linewidth=0.8)

plt.plot(df.index, df["TOTAL_NOx_gs"], label="TOTAL NOx", linewidth=2)
plt.title("Hourly NOx Emission Rate (Correct ON/OFF)")
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
plt.title("Hourly SO2 Emission Rate (Correct ON/OFF)")
plt.ylabel("g/s")
plt.xlabel("Time")
plt.legend()
plt.grid()
plt.tight_layout()
plt.savefig("SO2_emission_rate.png", dpi=300)

# ==========================================================
# SAVE CSV (THIS WILL NOW CHANGE)
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

vars_to_save = [
    "NOx_5A_gs", "NOx_5B_gs", "NOx_6A_gs", "NOx_6B_gs",
    "SO2_5A_gs", "SO2_5B_gs", "SO2_6A_gs", "SO2_6B_gs",
    "TOTAL_NOx_gs", "TOTAL_SO2_gs"
]

for var in vars_to_save:
    ds[var] = ("Time", df[var].values)
    ds[var].attrs["units"] = "g s-1"

ds.attrs["title"] = "VPPS emissions (correct MW-based ON/OFF)"
ds.attrs["power_station"] = "Vales Point Power Station"
ds.attrs["latitude"] = LAT
ds.attrs["longitude"] = LON

nc_out = "VPPS_hourly_emissions.nc"
ds.to_netcdf(nc_out)

# ==========================================================
# OUTPUT
# ==========================================================
print("\nFinished.")
print(f"CSV: {csv_out}")
print(f"NetCDF: {nc_out}")

plt.show()

