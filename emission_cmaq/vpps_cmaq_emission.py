#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import xarray as xr
import numpy as np

# ==========================================================
# INPUT EXCEL FILE
# ==========================================================
excel_file = "noxso2flowrate.xlsx"

# ==========================================================
# POWER STATION INFORMATION
# ==========================================================
LAT = -33.161
LON = 151.541

STACK_HEIGHT = 178.0       # m
STACK_DIAMETER = 10.3      # m
EXIT_VELOCITY = 26.0       # m/s
EXIT_TEMPERATURE = 369.0   # K

# ==========================================================
# READ EXCEL
# ==========================================================
df = pd.read_excel(excel_file, engine="openpyxl")

# Rename first column to Time
df.rename(columns={df.columns[0]: "Time"}, inplace=True)

# Convert datetime
df["Time"] = pd.to_datetime(df["Time"], dayfirst=True)

# Set datetime index
df.set_index("Time", inplace=True)

# ==========================================================
# EMISSION COLUMNS
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

# ==========================================================
# FLOW RATE COLUMNS
# ==========================================================
stack_map = {
    "5A": "U5 DUCT A Flow (m3/s)",
    "5B": "U5 DUCT B Flow (m3/s)",
    "6A": "U6 DUCT C Flow (m3/s)",
    "6B": "U6 DUCT D Flow (m3/s)"
}

# ==========================================================
# FILL MISSING INPUT DATA
# ==========================================================
print("\nChecking missing input data...\n")

all_input_cols = nox_cols + so2_cols + list(stack_map.values())

for col in all_input_cols:

    n_missing_before = df[col].isna().sum()

    if n_missing_before > 0:
        print(f"{col}: {n_missing_before} missing values")

    # Interpolate time series
    df[col] = df[col].interpolate(method="time")

    # Fill edge NaNs
    df[col] = df[col].bfill()
    df[col] = df[col].ffill()

# ==========================================================
# CHECK REMAINING MISSING INPUTS
# ==========================================================
print("\nRemaining missing values after filling:\n")
print(df[all_input_cols].isna().sum())

# ==========================================================
# CALCULATE EMISSION RATES (g/s)
# ==========================================================
for stack, flow_col in stack_map.items():

    # Convert concentration mg/m3 -> g/m3
    nox_gm3 = df[f"{stack} NOx (mg/m3)"] / 1000.0
    so2_gm3 = df[f"{stack} SO2 (mg/m3)"] / 1000.0

    # Flow rate
    flow = df[flow_col]

    # Emission rate
    df[f"NOx_{stack}_gs"] = nox_gm3 * flow
    df[f"SO2_{stack}_gs"] = so2_gm3 * flow

# ==========================================================
# FILL MISSING EMISSION RATES
# ==========================================================
emission_vars = [

    "NOx_5A_gs",
    "NOx_5B_gs",
    "NOx_6A_gs",
    "NOx_6B_gs",

    "SO2_5A_gs",
    "SO2_5B_gs",
    "SO2_6A_gs",
    "SO2_6B_gs"
]

for var in emission_vars:

    # Interpolate
    df[var] = df[var].interpolate(method="time")

    # Fill remaining edge NaNs
    df[var] = df[var].bfill()
    df[var] = df[var].ffill()

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
# PLOT NOx EMISSIONS
# ==========================================================
plt.figure(figsize=(16,6))

for stack in stack_map:

    plt.plot(
        df.index,
        df[f"NOx_{stack}_gs"],
        label=f"{stack} NOx",
        linewidth=0.8
    )

plt.plot(
    df.index,
    df["TOTAL_NOx_gs"],
    label="TOTAL NOx",
    linewidth=2
)

plt.title("Hourly NOx Emission Rate")
plt.ylabel("Emission Rate (g/s)")
plt.xlabel("Date")
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.savefig("NOx_emission_rate.png", dpi=300)

# ==========================================================
# PLOT SO2 EMISSIONS
# ==========================================================
plt.figure(figsize=(16,6))

for stack in stack_map:

    plt.plot(
        df.index,
        df[f"SO2_{stack}_gs"],
        label=f"{stack} SO2",
        linewidth=0.8
    )

plt.plot(
    df.index,
    df["TOTAL_SO2_gs"],
    label="TOTAL SO2",
    linewidth=2
)

plt.title("Hourly SO2 Emission Rate")
plt.ylabel("Emission Rate (g/s)")
plt.xlabel("Date")
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.savefig("SO2_emission_rate.png", dpi=300)

# ==========================================================
# DAILY AVERAGES
# ==========================================================
daily = df.resample("D").mean()

# ==========================================================
# DAILY TOTAL NOx
# ==========================================================
plt.figure(figsize=(16,6))

plt.plot(
    daily.index,
    daily["TOTAL_NOx_gs"],
    linewidth=1.5
)

plt.title("Daily Mean Total NOx Emission")
plt.ylabel("g/s")
plt.xlabel("Date")
plt.grid(True)

plt.tight_layout()
plt.savefig("Daily_TOTAL_NOx.png", dpi=300)

# ==========================================================
# SAVE CSV
# ==========================================================
csv_out = "VPPS_hourly_emission_rates.csv"

df.to_csv(csv_out)

# ==========================================================
# CREATE NETCDF
# ==========================================================
nt = len(df)

ds = xr.Dataset(
    coords={
        "Time": df.index.values
    }
)

# ==========================================================
# LAT/LON
# ==========================================================
ds["lat"] = ("Time", np.full(nt, LAT))
ds["lon"] = ("Time", np.full(nt, LON))

ds["lat"].attrs["units"] = "degrees_north"
ds["lon"].attrs["units"] = "degrees_east"

# ==========================================================
# STACK PARAMETERS
# ==========================================================
ds["stack_height"] = STACK_HEIGHT
ds["stack_diameter"] = STACK_DIAMETER
ds["exit_velocity"] = EXIT_VELOCITY
ds["exit_temperature"] = EXIT_TEMPERATURE

# ==========================================================
# SAVE EMISSION VARIABLES
# ==========================================================
vars_to_save = [

    "NOx_5A_gs",
    "NOx_5B_gs",
    "NOx_6A_gs",
    "NOx_6B_gs",

    "SO2_5A_gs",
    "SO2_5B_gs",
    "SO2_6A_gs",
    "SO2_6B_gs",

    "TOTAL_NOx_gs",
    "TOTAL_SO2_gs"
]

for var in vars_to_save:

    ds[var] = ("Time", df[var].values)

    ds[var].attrs["units"] = "g s-1"

# ==========================================================
# GLOBAL ATTRIBUTES
# ==========================================================
ds.attrs["title"] = "VPPS hourly stack emissions"
ds.attrs["power_station"] = "Vales Point Power Station"
ds.attrs["latitude"] = LAT
ds.attrs["longitude"] = LON

# ==========================================================
# WRITE NETCDF
# ==========================================================
nc_out = "VPPS_hourly_emissions.nc"

ds.to_netcdf(nc_out)

# ==========================================================
# PRINT OUTPUTS
# ==========================================================
print("\nFinished.")
print("\nCreated files:")
print(f"  {csv_out}")
print(f"  {nc_out}")
print("  NOx_emission_rate.png")
print("  SO2_emission_rate.png")
print("  Daily_TOTAL_NOx.png")

# ==========================================================
# SHOW FIGURES
# ==========================================================
plt.show()

import xarray as xr
import numpy as np

# ----------------------------------------------------------
# Generate daily CMAQ elevated files
# ----------------------------------------------------------

stacks = ["5A", "5B", "6A", "6B"]

for day, day_df in df.groupby(df.index.date):

    datestr = pd.Timestamp(day).strftime("%Y%m%d")

    # ======================================================
    # EMISSION FILE
    # ======================================================

    emis_ds = xr.Dataset()

    emis_ds.coords["TSTEP"] = np.arange(len(day_df))
    emis_ds.coords["NSTK"] = np.arange(4)

    NO = np.zeros((len(day_df),4))
    NO2 = np.zeros((len(day_df),4))
    SO2 = np.zeros((len(day_df),4))

    for i, stack in enumerate(stacks):

        nox = day_df[f"NOx_{stack}_gs"].values

        NO[:,i]  = 0.95 * nox
        NO2[:,i] = 0.05 * nox
        SO2[:,i] = day_df[f"SO2_{stack}_gs"].values

    emis_ds["NO"] = (("TSTEP","NSTK"), NO)
    emis_ds["NO2"] = (("TSTEP","NSTK"), NO2)
    emis_ds["SO2"] = (("TSTEP","NSTK"), SO2)

    emis_ds["NO"].attrs["units"] = "g s-1"
    emis_ds["NO2"].attrs["units"] = "g s-1"
    emis_ds["SO2"].attrs["units"] = "g s-1"

    emis_ds.to_netcdf(
        f"VPPS_EMIS_{datestr}.nc"
    )

    # ======================================================
    # STACK FILE
    # ======================================================

    stk_ds = xr.Dataset()

    stk_ds.coords["NSTK"] = np.arange(4)

    stk_ds["LAT"] = (
        ("NSTK"),
        np.full(4,-33.161)
    )

    stk_ds["LON"] = (
        ("NSTK"),
        np.full(4,151.541)
    )

    stk_ds["STKHT"] = (
        ("NSTK"),
        np.full(4,178.0)
    )

    stk_ds["STKDM"] = (
        ("NSTK"),
        np.full(4,10.3)
    )

    stk_ds["STKVE"] = (
        ("NSTK"),
        np.full(4,26.0)
    )

    stk_ds["STKTK"] = (
        ("NSTK"),
        np.full(4,369.0)
    )

    stk_ds.to_netcdf(
        f"VPPS_STACK_{datestr}.nc"
    )

    print(f"Created {datestr}")

