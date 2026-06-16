#!/usr/bin/env python3

import pandas as pd
import xarray as xr
import numpy as np

# ==========================================================
# INPUT CSV
# ==========================================================
csv_file = "VPPS_hourly_emission_rates.csv"

# ==========================================================
# POWER STATION LOCATION
# ==========================================================
LAT = -33.161
LON = 151.541

# ==========================================================
# READ CSV
# ==========================================================
df = pd.read_csv(csv_file)

# Convert time
df["Time"] = pd.to_datetime(df["Time"])

# ==========================================================
# CREATE XARRAY DATASET
# ==========================================================
ds = xr.Dataset(

    coords={
        "Time": df["Time"].values
    }
)

# ==========================================================
# ADD LOCATION VARIABLES
# ==========================================================
ds["lat"] = LAT
ds["lon"] = LON

# ==========================================================
# ADD EMISSION VARIABLES
# ==========================================================
vars_to_save = [

    "5A_NOx_gs",
    "5B_NOx_gs",
    "6A_NOx_gs",
    "6B_NOx_gs",

    "5A_SO2_gs",
    "5B_SO2_gs",
    "6A_SO2_gs",
    "6B_SO2_gs",

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
ds.attrs["source"] = "Calculated from stack concentration and flow data"
ds.attrs["power_station"] = "VPPS"

# ==========================================================
# SAVE NETCDF
# ==========================================================
outfile = "VPPS_hourly_emissions.nc"

ds.to_netcdf(outfile)

print(f"Created: {outfile}")

