#!/usr/bin/env python3

import xarray as xr
import glob
import os

# ==================================================
# INPUT DIRECTORIES
# ==================================================

BASE_DIR = (
"/mnt/scratch_lustre/ar_policy/shipping_runs/"
"esme_local/cmaq_23_baseshp_nensw/run/CTM"
)

NOSHIP_DIR = (
"/mnt/scratch_lustre/ar_policy/shipping_runs/"
"esme_local/cmaq_23_noshp_nensw/run/CTM"
)

GRID_FILE = (
"/mnt/scratch_lustre/ar_policy/shipping_runs/"
"esme_local/cmaq_23_noshp_nensw/run/MCIP/"
"2022-12-27/d01/GRIDCRO2D_160801_3km.nc"
)

# ==================================================
# FILE LISTS
# ==================================================

base_files = sorted(glob.glob(
    f"{BASE_DIR}/2023-07-*/d01/"
    "CCTM_AELMO_v54_intel_d01_*.nc"
))

noship_files = sorted(glob.glob(
    f"{NOSHIP_DIR}/2023-07-*/d01/"
    "CCTM_AELMO_v54_intel_d01_*.nc"
))

print("BASE files   :", len(base_files))
print("NOSHIP files :", len(noship_files))

if len(base_files) != len(noship_files):

    raise RuntimeError(
        "Different number of BASE and NOSHIP files"
    )

# ==================================================
# GRID
# ==================================================

grid = xr.open_dataset(GRID_FILE)

lat = grid["LAT"][0,0,:,:]
lon = grid["LON"][0,0,:,:]

# ==================================================
# PROCESS FILES
# ==================================================

all_ds = []

for fb, fn in zip(base_files, noship_files):

    print(
        "Processing:",
        os.path.basename(fb)
    )

    ds_base = xr.open_dataset(fb)
    ds_nosh = xr.open_dataset(fn)

    out = xr.Dataset()

    # ------------------------------------------------
    # TOTAL PM2.5
    # ------------------------------------------------

    out["PM25"] = (
        ds_base["PM25"][:,0,:,:]
        -
        ds_nosh["PM25"][:,0,:,:]
    )

    # ------------------------------------------------
    # EPA COMPONENTS
    # ------------------------------------------------

    out["SO4"] = (
        ds_base["PM25_SO4"][:,0,:,:]
        -
        ds_nosh["PM25_SO4"][:,0,:,:]
    )

    out["NO3"] = (
        ds_base["PM25_NO3"][:,0,:,:]
        -
        ds_nosh["PM25_NO3"][:,0,:,:]
    )

    out["NH4"] = (
        ds_base["PM25_NH4"][:,0,:,:]
        -
        ds_nosh["PM25_NH4"][:,0,:,:]
    )

    out["EC"] = (
        ds_base["PM25_EC"][:,0,:,:]
        -
        ds_nosh["PM25_EC"][:,0,:,:]
    )

    out["OA"] = (
        ds_base["PM25_OA"][:,0,:,:]
        -
        ds_nosh["PM25_OA"][:,0,:,:]
    )

    out["POA"] = (
        ds_base["PMF_POA"][:,0,:,:]
        -
        ds_nosh["PMF_POA"][:,0,:,:]
    )

    out["SOA"] = (
        ds_base["PMF_SOA"][:,0,:,:]
        -
        ds_nosh["PMF_SOA"][:,0,:,:]
    )

    out["SOIL"] = (
        ds_base["PM25_SOIL"][:,0,:,:]
        -
        ds_nosh["PM25_SOIL"][:,0,:,:]
    )

    # ------------------------------------------------
    # SEASALT
    # ------------------------------------------------

    seasalt_base = (
        ds_base["PM25_NA"][:,0,:,:]
        +
        ds_base["PM25_CL"][:,0,:,:]
        +
        ds_base["PM25_MG"][:,0,:,:]
    )

    seasalt_nosh = (
        ds_nosh["PM25_NA"][:,0,:,:]
        +
        ds_nosh["PM25_CL"][:,0,:,:]
        +
        ds_nosh["PM25_MG"][:,0,:,:]
    )

    out["SEASALT"] = (
        seasalt_base
        -
        seasalt_nosh
    )

    # ------------------------------------------------
    # INDIVIDUAL SEA SALT SPECIES
    # ------------------------------------------------

    out["NA"] = (
        ds_base["PM25_NA"][:,0,:,:]
        -
        ds_nosh["PM25_NA"][:,0,:,:]
    )

    out["CL"] = (
        ds_base["PM25_CL"][:,0,:,:]
        -
        ds_nosh["PM25_CL"][:,0,:,:]
    )

    out["MG"] = (
        ds_base["PM25_MG"][:,0,:,:]
        -
        ds_nosh["PM25_MG"][:,0,:,:]
    )

    # ------------------------------------------------
    # OTHER
    # ------------------------------------------------

    out["OTHER"] = (
        ds_base["PM25_OTHER"][:,0,:,:]
        -
        ds_nosh["PM25_OTHER"][:,0,:,:]
    )

    all_ds.append(out)

# ==================================================
# COMBINE ALL HOURS
# ==================================================

result = xr.concat(
    all_ds,
    dim="TSTEP"
)

# ==================================================
# ADD LAT/LON
# ==================================================

result["LAT"] = lat
result["LON"] = lon

# ==================================================
# ATTRIBUTES
# ==================================================

result.attrs["title"] = (
    "Power Station Impact on PM2.5 "
    "(BASESHIP - NOSHIP)"
)

result.attrs["scenario"] = (
    "BASESHIP minus NOSHIP"
)

result.attrs["units"] = "ug m-3"

# ==================================================
# SAVE HOURLY FILE
# ==================================================

outfile = (
    "PM25_EPA_AELMO_POWERSTATION_202307.nc"
)

result.to_netcdf(outfile)

print()
print("Saved:", outfile)

# ==================================================
# MONTHLY MEAN
# ==================================================

monthly = result.mean("TSTEP")

monthly_file = (
    "PM25_EPA_AELMO_POWERSTATION_MONTHLYMEAN_202307.nc"
)

monthly.to_netcdf(monthly_file)

print("Saved:", monthly_file)

