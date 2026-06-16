#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import xarray as xr
import numpy as np

# ==========================================================
# INPUT FILE
# ==========================================================
excel_file = "Eraringnoxso2Emission.xlsx"

# ==========================================================
# POWER STATION INFO
# ==========================================================
LAT = -33.083
LON = 151.513

STACK_HEIGHT = 314.4
STACK_DIAMETER = 10.54
EXIT_VELOCITY = 28.0
EXIT_TEMPERATURE = 370.0

# ==========================================================
# READ DATA
# ==========================================================
#df = pd.read_excel(excel_file, engine="openpyxl")
df = pd.read_excel(
    excel_file,
    sheet_name="Unit Emissions Data",
    engine="openpyxl"
)

df.rename(columns={df.columns[0]: "Time"}, inplace=True)
df["Time"] = pd.to_datetime(df["Time"], dayfirst=True)
df.set_index("Time", inplace=True)

# ==========================================================
# UNIT MAP (Eraring 4 units)
# ==========================================================
units = ["U1", "U2", "U3", "U4"]

# column naming pattern from your data
def col(unit, var):
    return f"{unit}{var}"

# ==========================================================
# COLUMN DEFINITIONS
# ==========================================================
load_col = "LoadMW"
flow_col = "FlowRate"
nox_col = "NOxConc"
so2_col = "SO2Conc"

temp_col = "Temp"
vel_col = "Velocity"

# ==========================================================
# CLEAN / FILL DATA
# ==========================================================
all_cols = []

for u in units:
    all_cols += [
        col(u, load_col),
        col(u, flow_col),
        col(u, nox_col),
        col(u, so2_col),
        col(u, temp_col),
        col(u, vel_col),
    ]

print("\nChecking missing values...\n")

for c in all_cols:
    if c in df.columns:
        nmiss = df[c].isna().sum()
        if nmiss > 0:
            print(f"{c}: {nmiss} missing")

        df[c] = df[c].interpolate(method="time").bfill().ffill()

# ==========================================================
# EMISSION CALCULATION (g/s)
# ==========================================================
for u in units:

    flow = df[col(u, flow_col)]          # m3/s
    nox = df[col(u, nox_col)] / 1000.0   # mg/m3 -> g/m3
    so2 = df[col(u, so2_col)] / 1000.0

    # OFFLINE handling: zero load = zero emission
    load = df[col(u, load_col)]

    df[f"NOx_{u}_gs"] = nox * flow * (load > 0)
    df[f"SO2_{u}_gs"] = so2 * flow * (load > 0)

# ==========================================================
# TOTAL EMISSIONS
# ==========================================================
df["TOTAL_NOx_gs"] = sum(df[f"NOx_{u}_gs"] for u in units)
df["TOTAL_SO2_gs"] = sum(df[f"SO2_{u}_gs"] for u in units)

# ==========================================================
# PLOT HOURLY NOx
# ==========================================================
plt.figure(figsize=(16,6))

for u in units:
    plt.plot(df.index, df[f"NOx_{u}_gs"], label=f"{u} NOx", linewidth=0.8)

plt.plot(df.index, df["TOTAL_NOx_gs"], label="TOTAL NOx", linewidth=2)

plt.title("Eraring – Hourly NOx Emission Rate")
plt.ylabel("g/s")
plt.xlabel("Time")
plt.legend()
plt.grid()

plt.tight_layout()
plt.savefig("Eraring_NOx_hourly.png", dpi=300)

# ==========================================================
# PLOT HOURLY SO2
# ==========================================================
plt.figure(figsize=(16,6))

for u in units:
    plt.plot(df.index, df[f"SO2_{u}_gs"], label=f"{u} SO2", linewidth=0.8)

plt.plot(df.index, df["TOTAL_SO2_gs"], label="TOTAL SO2", linewidth=2)

plt.title("Eraring – Hourly SO2 Emission Rate")
plt.ylabel("g/s")
plt.xlabel("Time")
plt.legend()
plt.grid()

plt.tight_layout()
plt.savefig("Eraring_SO2_hourly.png", dpi=300)

# ==========================================================
# DAILY STATISTICS
# ==========================================================
daily = df.resample("D").mean()

plt.figure(figsize=(16,6))
plt.plot(daily.index, daily["TOTAL_NOx_gs"])
plt.title("Eraring – Daily Mean NOx Emission")
plt.ylabel("g/s")
plt.grid()

plt.tight_layout()
plt.savefig("Eraring_NOx_daily.png", dpi=300)

plt.show()

# ==========================================================
# SUMMARY STATISTICS
# ==========================================================
summary = pd.DataFrame({
    "Mean_NOx_gs": df[[f"NOx_{u}_gs" for u in units]].mean(),
    "Max_NOx_gs": df[[f"NOx_{u}_gs" for u in units]].max(),
    "Mean_SO2_gs": df[[f"SO2_{u}_gs" for u in units]].mean(),
    "Max_SO2_gs": df[[f"SO2_{u}_gs" for u in units]].max(),
})

summary.loc["TOTAL"] = [
    df["TOTAL_NOx_gs"].mean(),
    df["TOTAL_NOx_gs"].max(),
    df["TOTAL_SO2_gs"].mean(),
    df["TOTAL_SO2_gs"].max()
]

summary.to_csv("Eraring_summary_statistics.csv")

# ==========================================================
# SAVE HOURLY CSV
# ==========================================================
df.to_csv("Eraring_hourly_emissions.csv")

# ==========================================================
# CREATE NETCDF
# ==========================================================
ds = xr.Dataset(coords={"Time": df.index.values})

nt = len(df)

ds["lat"] = ("Time", np.full(nt, LAT))
ds["lon"] = ("Time", np.full(nt, LON))

for u in units:
    ds[f"NOx_{u}_gs"] = ("Time", df[f"NOx_{u}_gs"].values)
    ds[f"SO2_{u}_gs"] = ("Time", df[f"SO2_{u}_gs"].values)

ds["TOTAL_NOx_gs"] = ("Time", df["TOTAL_NOx_gs"].values)
ds["TOTAL_SO2_gs"] = ("Time", df["TOTAL_SO2_gs"].values)

ds.attrs["title"] = "Eraring Power Station Emissions"
ds.attrs["latitude"] = LAT
ds.attrs["longitude"] = LON

ds.to_netcdf("Eraring_emissions.nc")

# ==========================================================
# DONE
# ==========================================================
print("\nDONE")
print("Outputs:")
print(" - Eraring_NOx_hourly.png")
print(" - Eraring_SO2_hourly.png")
print(" - Eraring_NOx_daily.png")
print(" - Eraring_summary_statistics.csv")
print(" - Eraring_hourly_emissions.csv")
print(" - Eraring_emissions.nc")

