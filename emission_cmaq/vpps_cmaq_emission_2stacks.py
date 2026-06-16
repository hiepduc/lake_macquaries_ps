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

import os

outdir = "cmaq_daily"

os.makedirs(outdir, exist_ok=True)

for day, day_df in df.groupby(df.index.date):

    datestr = pd.Timestamp(day).strftime("%Y%m%d")

    # ======================================================
    # COMBINE DUCTS INTO PHYSICAL STACKS
    # ======================================================

    # ------------------------
    # UNIT 5 STACK
    # ------------------------
    nox_5 = (
        day_df["NOx_5A_gs"].values +
        day_df["NOx_5B_gs"].values
    )

    so2_5 = (
        day_df["SO2_5A_gs"].values +
        day_df["SO2_5B_gs"].values
    )

    flow_5 = (
        day_df["U5 DUCT A Flow (m3/s)"].values +
        day_df["U5 DUCT B Flow (m3/s)"].values
    )

    # ------------------------
    # UNIT 6 STACK
    # ------------------------
    nox_6 = (
        day_df["NOx_6A_gs"].values +
        day_df["NOx_6B_gs"].values
    )

    so2_6 = (
        day_df["SO2_6A_gs"].values +
        day_df["SO2_6B_gs"].values
    )

    flow_6 = (
        day_df["U6 DUCT C Flow (m3/s)"].values +
        day_df["U6 DUCT D Flow (m3/s)"].values
    )

    # ======================================================
    # CREATE ARRAYS
    # ======================================================

    NO = np.column_stack([
        0.95 * nox_5,
        0.95 * nox_6
    ])

    NO2 = np.column_stack([
        0.05 * nox_5,
        0.05 * nox_6
    ])

    SO2 = np.column_stack([
        so2_5,
        so2_6
    ])

    FLOW = np.column_stack([
        flow_5,
        flow_6
    ])

    # ======================================================
    # EMISSION FILE
    # ======================================================

    emis_ds = xr.Dataset(
        coords={
            "TSTEP": np.arange(len(day_df)),
            "NSTK": np.arange(2)
        }
    )

    emis_ds["NO"] = (
        ("TSTEP", "NSTK"),
        NO
    )

    emis_ds["NO2"] = (
        ("TSTEP", "NSTK"),
        NO2
    )

    emis_ds["SO2"] = (
        ("TSTEP", "NSTK"),
        SO2
    )

    emis_ds["FLOW"] = (
        ("TSTEP", "NSTK"),
        FLOW
    )

    emis_ds["NO"].attrs["units"] = "g s-1"
    emis_ds["NO2"].attrs["units"] = "g s-1"
    emis_ds["SO2"].attrs["units"] = "g s-1"
    emis_ds["FLOW"].attrs["units"] = "m3 s-1"

    emis_ds.attrs["title"] = \
        "VPPS elevated emissions"

    emis_ds.attrs["date"] = datestr

    emis_ds.to_netcdf(
        f"{outdir}/VPPS_EMIS_{datestr}.nc"
    )

    # ======================================================
    # STACK FILE
    # ======================================================

    stack_ds = xr.Dataset(
        coords={
            "NSTK": np.arange(2)
        }
    )

    stack_ds["LAT"] = (
        ("NSTK"),
        [-33.161, -33.161]
    )

    stack_ds["LON"] = (
        ("NSTK"),
        [151.541, 151.541]
    )

    stack_ds["STKHT"] = (
        ("NSTK"),
        [178.0, 178.0]
    )

    stack_ds["STKDM"] = (
        ("NSTK"),
        [10.3, 10.3]
    )

    stack_ds["STKTK"] = (
        ("NSTK"),
        [369.0, 369.0]
    )

    stack_ds["STKVE_DESIGN"] = (
        ("NSTK"),
        [26.0, 26.0]
    )

    stack_ds["STACK_ID"] = (
        ("NSTK"),
        ["U5", "U6"]
    )

    stack_ds.attrs["title"] = \
        "VPPS stack parameters"

    stack_ds.to_netcdf(
        f"{outdir}/VPPS_STACK_{datestr}.nc"
    )

    print(
        f"Created {datestr}"
    )

print("\nFinished creating daily CMAQ files.")

