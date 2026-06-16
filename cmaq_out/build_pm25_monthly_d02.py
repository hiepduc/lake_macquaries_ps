#!/usr/bin/env python3

import xarray as xr
import numpy as np
import pandas as pd
import glob
import os

# ==========================================================
# USER SETTINGS
# ==========================================================

CTM_DIR = (
    "/mnt/scratch_lustre/ar_policy/whe_project/"
    "esme_local/cmaq_gmr_2023/run/CTM"
)

GRID_FILE = (
    "/mnt/scratch_lustre/ar_policy/whe_project/"
    "esme_local/cmaq_gmr_2023/run/MCIP/2023-07-02/d02/"
    "GRIDCRO2D_160801_3km.nc"
)

YEAR = 2023
MONTH = 7

OUTFILE = f"PM25_{YEAR}{MONTH:02d}_d02.nc"

# ==========================================================
# FIND DAILY ACONC FILES
# ==========================================================

pattern = (
    f"{CTM_DIR}/{YEAR}-{MONTH:02d}-*/d02/"
    "CCTM_ACONC_v54_intel_d02_*.nc"
)

files = sorted(glob.glob(pattern))

print(f"\nFound {len(files)} daily CMAQ files\n")

if len(files) == 0:
    raise RuntimeError("No CMAQ files found")

# ==========================================================
# READ GRID
# ==========================================================

grid = xr.open_dataset(GRID_FILE)

lat = grid["LAT"][0, 0, :, :]
lon = grid["LON"][0, 0, :, :]

# ==========================================================
# DETERMINE PM25 SPECIES
# ==========================================================

sample = xr.open_dataset(files[0])

exclude = [
    "AH2OI",
    "AH2OJ",
    "AH2OK",
    "AORGH2OJ",
    "AH3OPI",
    "AH3OPJ",
    "AH3OPK",
]

pm25_species = []

for v in sample.data_vars:

    try:
        units = sample[v].attrs.get("units", "").strip()

        if units == "ug m-3":

            if v not in exclude:
                pm25_species.append(v)

    except Exception:
        pass

print("\nPM25 species:\n")
for v in pm25_species:
    print(v)

print(f"\nNumber of PM species = {len(pm25_species)}")

# ==========================================================
# PROCESS ALL FILES
# ==========================================================

all_pm25 = []
all_so4 = []
all_no3 = []
all_nh4 = []
all_ec = []
all_poa = []

for f in files:

    print(os.path.basename(f))

    ds = xr.open_dataset(f)

    # ------------------------------------------------------
    # total PM2.5
    # ------------------------------------------------------

    pm25 = 0

    for v in pm25_species:
        if v in ds:
            pm25 = pm25 + ds[v][:, 0, :, :]

    # ------------------------------------------------------
    # sulfate
    # ------------------------------------------------------

    sulfate = (
        ds["ASO4I"][:,0,:,:]
        + ds["ASO4J"][:,0,:,:]
        + ds["ASO4K"][:,0,:,:]
    )

    # ------------------------------------------------------
    # nitrate
    # ------------------------------------------------------

    nitrate = (
        ds["ANO3I"][:,0,:,:]
        + ds["ANO3J"][:,0,:,:]
        + ds["ANO3K"][:,0,:,:]
    )

    # ------------------------------------------------------
    # ammonium
    # ------------------------------------------------------

    ammonium = (
        ds["ANH4I"][:,0,:,:]
        + ds["ANH4J"][:,0,:,:]
        + ds["ANH4K"][:,0,:,:]
    )

    # ------------------------------------------------------
    # elemental carbon
    # ------------------------------------------------------

    ec = (
        ds["AECI"][:,0,:,:]
        + ds["AECJ"][:,0,:,:]
    )

    # ------------------------------------------------------
    # primary organic aerosol
    # ------------------------------------------------------

    poa = (
        ds["APOCI"][:,0,:,:]
        + ds["APOCJ"][:,0,:,:]
        + ds["APNCOMI"][:,0,:,:]
        + ds["APNCOMJ"][:,0,:,:]
    )

    # ------------------------------------------------------
    # SOA residual
    # ------------------------------------------------------

    soa = pm25 - sulfate - nitrate - ammonium - ec - poa

    all_pm25.append(pm25)
    all_so4.append(sulfate)
    all_no3.append(nitrate)
    all_nh4.append(ammonium)
    all_ec.append(ec)
    all_poa.append(poa)

# ==========================================================
# CONCATENATE ALL DAYS
# ==========================================================

PM25 = xr.concat(all_pm25, dim="time")
SO4  = xr.concat(all_so4, dim="time")
NO3  = xr.concat(all_no3, dim="time")
NH4  = xr.concat(all_nh4, dim="time")
EC   = xr.concat(all_ec, dim="time")
POA  = xr.concat(all_poa, dim="time")

SOA = PM25 - SO4 - NO3 - NH4 - EC - POA

# ==========================================================
# MONTHLY MEANS
# ==========================================================

PM25_mean = PM25.mean("time")
SO4_mean  = SO4.mean("time")
NO3_mean  = NO3.mean("time")
NH4_mean  = NH4.mean("time")
EC_mean   = EC.mean("time")
POA_mean  = POA.mean("time")
SOA_mean  = SOA.mean("time")

# ==========================================================
# OUTPUT DATASET
# ==========================================================

out = xr.Dataset(
    {
        "PM25": PM25_mean,
        "SO4": SO4_mean,
        "NO3": NO3_mean,
        "NH4": NH4_mean,
        "EC": EC_mean,
        "POA": POA_mean,
        "SOA": SOA_mean,
    }
)

out["LAT"] = lat
out["LON"] = lon

out["PM25"].attrs["units"] = "ug m-3"

out.to_netcdf(OUTFILE)

print("\nSaved:")
print(OUTFILE)

print("\nDone.")

