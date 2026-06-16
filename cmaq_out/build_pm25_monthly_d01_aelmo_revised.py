#!/usr/bin/env python3

import xarray as xr
import glob
import os

# ==================================================
# INPUT
# ==================================================

AELMO_DIR = (
    "/mnt/scratch_lustre/ar_policy/"
    "whe_project/esme_local/cmaq_gmr_2023/run/CTM"
)

GRID_FILE = (
    "/mnt/scratch_lustre/ar_policy/"
    "whe_project/esme_local/cmaq_gmr_2023/run/MCIP/"
    "2023-07-02/d01/GRIDCRO2D_160801_3km.nc"
)

files = sorted(glob.glob(
    f"{AELMO_DIR}/2023-07-*/d01/"
    "CCTM_AELMO_v54_intel_d01_*.nc"
))

print("Found", len(files), "files")

# ==================================================
# GRID
# ==================================================

grid = xr.open_dataset(GRID_FILE)

lat = grid["LAT"][0, 0, :, :]
lon = grid["LON"][0, 0, :, :]

# ==================================================
# LOOP DAILY FILES
# ==================================================

all_ds = []

for f in files:

    print(os.path.basename(f))

    ds = xr.open_dataset(f)

    out = xr.Dataset()

    # --------------------------------------------------
    # bulk PM
    # --------------------------------------------------

    out["PM25"] = ds["PM25"][:, 0, :, :]

    # --------------------------------------------------
    # inorganic secondary aerosol
    # --------------------------------------------------

    out["SO4"] = ds["PM25_SO4"][:, 0, :, :]
    out["NO3"] = ds["PM25_NO3"][:, 0, :, :]
    out["NH4"] = ds["PM25_NH4"][:, 0, :, :]

    # --------------------------------------------------
    # carbonaceous
    # --------------------------------------------------

    out["EC"] = ds["PM25_EC"][:, 0, :, :]
    out["OA"] = ds["PM25_OA"][:, 0, :, :]

    out["POA"] = ds["PMF_POA"][:, 0, :, :]
    out["SOA"] = ds["PMF_SOA"][:, 0, :, :]

    # --------------------------------------------------
    # crustal / soil
    # --------------------------------------------------

    out["SOIL"] = ds["PM25_SOIL"][:, 0, :, :]

    # --------------------------------------------------
    # sea salt components (KEEP SEPARATE — NO RECONSTRUCTION)
    # --------------------------------------------------

    out["NA"] = ds["PM25_NA"][:, 0, :, :]
    out["CL"] = ds["PM25_CL"][:, 0, :, :]
    out["MG"] = ds["PM25_MG"][:, 0, :, :]

    # optional but useful
    if "PM25_K" in ds:
        out["K"] = ds["PM25_K"][:, 0, :, :]

    # --------------------------------------------------
    # residual / unexplained
    # --------------------------------------------------

    out["OTHER"] = ds["PM25_OTHER"][:, 0, :, :]

    all_ds.append(out)

# ==================================================
# MERGE MONTH
# ==================================================

result = xr.concat(all_ds, dim="TSTEP")

result["LAT"] = lat
result["LON"] = lon

# ==================================================
# SAVE
# ==================================================

result.to_netcdf("PM25_EPA_AELMO_202307.nc")

print("Saved PM25_EPA_AELMO_202307.nc")

