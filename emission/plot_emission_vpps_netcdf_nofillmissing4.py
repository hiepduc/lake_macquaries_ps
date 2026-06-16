#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import xarray as xr
import numpy as np

# ==========================================================
# INPUT
# ==========================================================
excel_file = "noxso2flowrate.xlsx"

LAT = -33.161
LON = 151.541

STACK_HEIGHT = 178.0
STACK_DIAMETER = 10.3
EXIT_VELOCITY = 26.0
EXIT_TEMPERATURE = 369.0

MW_THRESHOLD = 10.0
SHORT_GAP = 3

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

# ==========================================================
# SHORT GAP FILL ONLY (inputs only)
# ==========================================================
input_cols = list(stack_map.values()) + [
    "5A NOx (mg/m3)", "5B NOx (mg/m3)",
    "6A NOx (mg/m3)", "6B NOx (mg/m3)",
    "5A SO2 (mg/m3)", "5B SO2 (mg/m3)",
    "6A SO2 (mg/m3)", "6B SO2 (mg/m3)"
]

for col in input_cols:
    if col in df.columns:
        df[col] = df[col].interpolate(method="time", limit=SHORT_GAP)

# ==========================================================
# EMISSION CALCULATION (CORRECT VERSION)
# ==========================================================
for stack, flow_col in stack_map.items():

    mw_col = mw_map[stack]

    nox = df[f"{stack} NOx (mg/m3)"] / 1000.0
    so2 = df[f"{stack} SO2 (mg/m3)"] / 1000.0
    flow = df[flow_col]

    nox_raw = nox * flow
    so2_raw = so2 * flow

    mw = df[mw_col]

    on_mask = (mw > MW_THRESHOLD) & mw.notna()
    off_mask = ~on_mask

    df[f"NOx_{stack}_gs"] = np.nan
    df[f"SO2_{stack}_gs"] = np.nan

    # OFF → zero emission
    df.loc[off_mask, f"NOx_{stack}_gs"] = 0.0
    df.loc[off_mask, f"SO2_{stack}_gs"] = 0.0

    # ON → real emission
    df.loc[on_mask, f"NOx_{stack}_gs"] = nox_raw.loc[on_mask]
    df.loc[on_mask, f"SO2_{stack}_gs"] = so2_raw.loc[on_mask]

# ==========================================================
# TOTALS
# ==========================================================
df["TOTAL_NOx_gs"] = df[[f"NOx_{s}_gs" for s in stack_map]].sum(axis=1, min_count=1)
df["TOTAL_SO2_gs"] = df[[f"SO2_{s}_gs" for s in stack_map]].sum(axis=1, min_count=1)

# ==========================================================
# CSV OUTPUT
# ==========================================================
csv_out = "VPPS_hourly_emission_rates.csv"
df.to_csv(csv_out)

# ==========================================================
# NETCDF
# ==========================================================
nt = len(df)

ds = xr.Dataset(coords={"Time": df.index.values})
ds["lat"] = ("Time", np.full(nt, LAT))
ds["lon"] = ("Time", np.full(nt, LON))

ds["stack_height"] = STACK_HEIGHT
ds["stack_diameter"] = STACK_DIAMETER
ds["exit_velocity"] = EXIT_VELOCITY
ds["exit_temperature"] = EXIT_TEMPERATURE

for var in [f"NOx_{s}_gs" for s in stack_map] + \
           [f"SO2_{s}_gs" for s in stack_map] + \
           ["TOTAL_NOx_gs", "TOTAL_SO2_gs"]:

    ds[var] = ("Time", df[var].values)
    ds[var].attrs["units"] = "g s-1"

ds.attrs["title"] = "VPPS emissions (correct MW logic)"
ds.attrs["power_station"] = "Vales Point Power Station"

nc_out = "VPPS_hourly_emissions.nc"
ds.to_netcdf(nc_out)

# ==========================================================
# PLOTS
# ==========================================================
plt.figure(figsize=(16,6))
for s in stack_map:
    plt.plot(df.index, df[f"NOx_{s}_gs"], label=s)

plt.plot(df.index, df["TOTAL_NOx_gs"], label="TOTAL", linewidth=2)
plt.legend(); plt.grid(); plt.title("NOx")
plt.tight_layout()
plt.savefig("NOx.png", dpi=300)

plt.figure(figsize=(16,6))
for s in stack_map:
    plt.plot(df.index, df[f"SO2_{s}_gs"], label=s)

plt.plot(df.index, df["TOTAL_SO2_gs"], label="TOTAL", linewidth=2)
plt.legend(); plt.grid(); plt.title("SO2")
plt.tight_layout()
plt.savefig("SO2.png", dpi=300)
plt.show()

print("Done")
print(csv_out)
print(nc_out)

