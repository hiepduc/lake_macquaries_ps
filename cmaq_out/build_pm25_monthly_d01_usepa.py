#!/usr/bin/env python3

import xarray as xr
import numpy as np
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
    "esme_local/cmaq_gmr_2023/run/MCIP/2023-07-02/d01/"
    "GRIDCRO2D_160801_3km.nc"
)

YEAR = 2023
MONTH = 7

OUTFILE = f"PM25_EPA_{YEAR}{MONTH:02d}.nc"

# ==========================================================
# FIND FILES
# ==========================================================

pattern = f"{CTM_DIR}/{YEAR}-{MONTH:02d}-*/d01/CCTM_ACONC_v54_intel_d01_*.nc"
files = sorted(glob.glob(pattern))

print(f"Found {len(files)} files")

if len(files) == 0:
    raise RuntimeError("No CMAQ files found")

# ==========================================================
# GRID
# ==========================================================

grid = xr.open_dataset(GRID_FILE)
lat = grid["LAT"][0, 0, :, :]
lon = grid["LON"][0, 0, :, :]

# ==========================================================
# STORAGE
# ==========================================================

pm25_list = []
so4_list = []
no3_list = []
nh4_list = []
ec_list = []
poa_list = []
soa_list = []

# ==========================================================
# LOOP DAILY FILES
# ==========================================================

for f in files:
    print("Processing:", os.path.basename(f))
    ds = xr.open_dataset(f)

    # -----------------------------
    # Inorganic aerosols (EPA style)
    # -----------------------------
    so4 = ds["ASO4I"][:,0,:,:] + ds["ASO4J"][:,0,:,:] + ds["ASO4K"][:,0,:,:]
    no3 = ds["ANO3I"][:,0,:,:] + ds["ANO3J"][:,0,:,:] + ds["ANO3K"][:,0,:,:]
    nh4 = ds["ANH4I"][:,0,:,:] + ds["ANH4J"][:,0,:,:] + ds["ANH4K"][:,0,:,:]

    # -----------------------------
    # Carbonaceous aerosol
    # -----------------------------
    ec = ds["AECI"][:,0,:,:] + ds["AECJ"][:,0,:,:]

    # Primary organic aerosol
    poa = (
        ds["APOCI"][:,0,:,:] +
        ds["APOCJ"][:,0,:,:] +
        ds["APNCOMI"][:,0,:,:] +
        ds["APNCOMJ"][:,0,:,:]
    )

    # -----------------------------
    # SOA (VBS-consistent CMAQ v5.4)
    # -----------------------------
    soa = (
        ds["AISO1J"][:,0,:,:] +
        ds["AISO2J"][:,0,:,:] +
        ds["AISO3J"][:,0,:,:] +
        ds["ASVPO1J"][:,0,:,:] +
        ds["ASVPO2J"][:,0,:,:] +
        ds["ASVPO3J"][:,0,:,:] +
        ds["AOLGAJ"][:,0,:,:] +
        ds["AOLGBJ"][:,0,:,:] +
        ds["AGLYJ"][:,0,:,:] +
        ds["AORGCJ"][:,0,:,:]
    )

    # -----------------------------
    # Dust + sea salt (fine fraction)
    # -----------------------------
    soil = ds["ASOIL"][:,0,:,:]
    seasalt = ds["ASEACAT"][:,0,:,:]

    # -----------------------------
    # PM2.5 reconstructed (EPA style)
    # -----------------------------
    pm25 = so4 + no3 + nh4 + ec + poa + soa + soil + seasalt

    # store
    pm25_list.append(pm25)
    so4_list.append(so4)
    no3_list.append(no3)
    nh4_list.append(nh4)
    ec_list.append(ec)
    poa_list.append(poa)
    soa_list.append(soa)

# ==========================================================
# CONCAT MONTH
# ==========================================================

PM25 = xr.concat(pm25_list, dim="time")
SO4  = xr.concat(so4_list, dim="time")
NO3  = xr.concat(no3_list, dim="time")
NH4  = xr.concat(nh4_list, dim="time")
EC   = xr.concat(ec_list, dim="time")
POA  = xr.concat(poa_list, dim="time")
SOA  = xr.concat(soa_list, dim="time")

# ==========================================================
# MONTHLY MEAN
# ==========================================================

out = xr.Dataset(
    {
        "PM25": PM25.mean("time"),
        "SO4": SO4.mean("time"),
        "NO3": NO3.mean("time"),
        "NH4": NH4.mean("time"),
        "EC": EC.mean("time"),
        "POA": POA.mean("time"),
        "SOA": SOA.mean("time"),
        "SOIL": (SO4 * 0 + SOA * 0 + POA * 0 + PM25 * 0) + 0,  # placeholder dims
    }
)

# ==========================================================
# COORDINATES
# ==========================================================

out["LAT"] = lat
out["LON"] = lon

# ==========================================================
# ATTRIBUTES
# ==========================================================

for v in out.data_vars:
    out[v].attrs["units"] = "ug m-3"

out["PM25"].attrs["long_name"] = "Reconstructed PM2.5 (EPA CMAQ v5.4 style)"

# ==========================================================
# SAVE
# ==========================================================

out.to_netcdf(OUTFILE)

print("Saved:", OUTFILE)

