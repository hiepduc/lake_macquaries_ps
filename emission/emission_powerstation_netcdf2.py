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

# Number of time steps
nt = len(df)

# ==========================================================
# CREATE DATASET
# ==========================================================
ds = xr.Dataset(
    coords={
        "Time": df["Time"].values
    }
)

# ==========================================================
# CREATE LAT/LON AS TIME-DEPENDENT VARIABLES
# ==========================================================
ds["lat"] = ("Time", np.full(nt, LAT))
ds["lon"] = ("Time", np.full(nt, LON))

ds["lat"].attrs["units"] = "degrees_north"
ds["lon"].attrs["units"] = "degrees_east"

# ==========================================================
# VARIABLE MAP
# ==========================================================
varmap = {

    "5A_NOx_gs": "NOx_5A_gs",
    "5B_NOx_gs": "NOx_5B_gs",
    "6A_NOx_gs": "NOx_6A_gs",
    "6B_NOx_gs": "NOx_6B_gs",

    "5A_SO2_gs": "SO2_5A_gs",
    "5B_SO2_gs": "SO2_5B_gs",
    "6A_SO2_gs": "SO2_6A_gs",
    "6B_SO2_gs": "SO2_6B_gs",

    "TOTAL_NOx_gs": "TOTAL_NOx_gs",
    "TOTAL_SO2_gs": "TOTAL_SO2_gs"
}

# ==========================================================
# ADD VARIABLES
# ==========================================================
for oldname, newname in varmap.items():

    ds[newname] = ("Time", df[oldname].values)

    ds[newname].attrs["units"] = "g s-1"

# ==========================================================
# STACK PARAMETERS
# ==========================================================
ds["stack_height"] = 178.0
ds["stack_diameter"] = 10.3
ds["exit_velocity"] = 26.0
ds["exit_temperature"] = 369.0

# ==========================================================
# GLOBAL ATTRIBUTES
# ==========================================================
ds.attrs["title"] = "VPPS hourly emissions"
ds.attrs["power_station"] = "Vales Point Power Station"
ds.attrs["latitude"] = LAT
ds.attrs["longitude"] = LON

# ==========================================================
# WRITE NETCDF
# ==========================================================
outfile = "VPPS_hourly_emissions_v2.nc"

ds.to_netcdf(outfile)

print(f"Created: {outfile}")

