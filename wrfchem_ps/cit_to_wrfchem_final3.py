#!/usr/bin/env python3
"""
FINAL VERSION: CIT → WRF-Chem emissions (HPC SAFE + SCIENTIFIC)

- No xarray (avoids segfault)
- Lustre-safe NetCDF writing
- Proper WPS grid reconstruction
- Preserves spatial distribution
"""

import numpy as np
import re
import sys
import os
from netCDF4 import Dataset
from pyproj import CRS, Transformer

# -------------------------------------------------
# HPC SAFETY
# -------------------------------------------------
os.environ["HDF5_USE_FILE_LOCKING"] = "FALSE"
os.environ["HDF5_DISABLE_VERSION_CHECK"] = "2"

# -------------------------------------------------
# SPECIES
# -------------------------------------------------
SPECIES = [
    "NO","NO2","CO","SO2","PM",
    "ALD2","ETH","FORM","ISOP",
    "OLE","PAR","TOL","XYL",
    "ETOH","MEOH","UNR","NH3"
]
NSPEC = len(SPECIES)

# -------------------------------------------------
# READ WPS
# -------------------------------------------------
def read_wps(fname):

    with open(fname, "r") as f:
        txt = f.read()

    def get(key):
        m = re.search(rf"{key}\s*=\s*([^,]+)", txt)
        if not m:
            raise ValueError(f"{key} not found")
        return m.group(1).strip()

    return {
        "ref_lat": float(get("ref_lat")),
        "truelat1": float(get("truelat1")),
        "truelat2": float(get("truelat2")),
        "stand_lon": float(get("stand_lon")),
        "dx": float(get("dx")),
        "dy": float(get("dy")),
        "e_we": int(get("e_we")),
        "e_sn": int(get("e_sn")),
    }

# -------------------------------------------------
# BUILD GRID
# -------------------------------------------------
def build_grid(wps):

    nx = wps["e_we"]
    ny = wps["e_sn"]

    proj = CRS.from_proj4(
        f"+proj=lcc +lat_1={wps['truelat1']} "
        f"+lat_2={wps['truelat2']} "
        f"+lat_0={wps['ref_lat']} "
        f"+lon_0={wps['stand_lon']} "
        "+datum=WGS84 +units=m +no_defs"
    )

    transformer = Transformer.from_crs(proj, "EPSG:4326", always_xy=True)

    # cell-centered grid
    x = (np.arange(nx) + 0.5) * wps["dx"]
    y = (np.arange(ny) + 0.5) * wps["dy"]

    xx, yy = np.meshgrid(x, y)
    lon, lat = transformer.transform(xx, yy)

    return lat, lon

# -------------------------------------------------
# READ CIT
# -------------------------------------------------
def decode_sid(sid):
    return {
        "hour": int(sid[1:3]),
        "x": int(sid[3:6]),
        "y": int(sid[6:9]),
    }

def read_cit(fname):

    with open(fname, "r", encoding="latin-1") as f:
        lines = f.readlines()

    data = []
    i = 0

    while i < len(lines):

        if lines[i].startswith("E") and "999999" not in lines[i]:

            sid = lines[i].split()[0]
            meta = decode_sid(sid)

            i += 1
            emis = []

            while len(emis) < NSPEC:
                emis.extend([float(v) for v in lines[i].split()])
                i += 1

            data.append({
                "hour": meta["hour"],
                "x": meta["x"],
                "y": meta["y"],
                "emis": np.array(emis[:NSPEC])
            })

        else:
            i += 1

    return data

# -------------------------------------------------
# PLUME PROFILE
# -------------------------------------------------
def plume_height():
    return 300.0

def vertical_profile(nz, h):

    z = np.linspace(50, 4000, nz)
    sigma = 200.0

    w = np.exp(-(z - h)**2 / (2*sigma**2))
    return w / np.sum(w)

# -------------------------------------------------
# INJECTION
# -------------------------------------------------
def inject(cit, nx, ny, nz=20):

    emis = np.zeros((24, NSPEC, nz, ny, nx))

    # CIT grid size (from your file header)
    CIT_NX = 210
    CIT_NY = 273

    for d in cit:

        t = d["hour"]

        i = int((d["x"] / CIT_NX) * nx)
        j = int((d["y"] / CIT_NY) * ny)

        i = np.clip(i, 0, nx-1)
        j = np.clip(j, 0, ny-1)

        w = vertical_profile(nz, plume_height())

        for k in range(nz):
            emis[t, :, k, j, i] += d["emis"] * w[k]

    return emis

# -------------------------------------------------
# WRITE NETCDF (HPC SAFE)
# -------------------------------------------------
def write_nc(emis, LAT, LON, outfile):

    nt, ns, nz, ny, nx = emis.shape

    # -----------------------
    # CREATE FILE (DEFINE ONLY)
    # -----------------------
    nc = Dataset(outfile, "w", format="NETCDF3_CLASSIC")

    nc.createDimension("Time", nt)
    nc.createDimension("bottom_top", nz)
    nc.createDimension("south_north", ny)
    nc.createDimension("west_east", nx)

    latv = nc.createVariable("XLAT", "f4", ("south_north","west_east"))
    lonv = nc.createVariable("XLONG", "f4", ("south_north","west_east"))

    emis_vars = {}
    for i, s in enumerate(SPECIES):
        emis_vars[s] = nc.createVariable(
            f"E_{s}",
            "f4",
            ("Time","bottom_top","south_north","west_east")
        )

    # -----------------------
    # CLOSE DEFINE MODE SAFELY
    # -----------------------
    nc.close()

    # -----------------------
    # REOPEN IN WRITE MODE (THIS IS THE FIX)
    # -----------------------
    nc = Dataset(outfile, "a")

    latv = nc.variables["XLAT"]
    lonv = nc.variables["XLONG"]

    # write coordinates
    latv[:, :] = LAT
    lonv[:, :] = LON

    # write emissions
    for i, s in enumerate(SPECIES):

        v = nc.variables[f"E_{s}"]

        for t in range(nt):
            for k in range(nz):
                for j in range(ny):
                    v[t, k, j, :] = emis[t, i, k, j, :]

    nc.close()

# -------------------------------------------------
# MAIN
# -------------------------------------------------
if __name__ == "__main__":

    if len(sys.argv) != 4:
        print("Usage: script.py cit.in namelist.wps out.nc")
        sys.exit(1)

    cit_file = sys.argv[1]
    wps_file = sys.argv[2]
    out_file = sys.argv[3]

    print("Reading WPS...")
    wps = read_wps(wps_file)

    print("Building WRF grid...")
    LAT, LON = build_grid(wps)

    print("Reading CIT...")
    cit = read_cit(cit_file)

    print("Injecting emissions...")
    emis = inject(cit, wps["e_we"], wps["e_sn"])

    print("Writing NetCDF (safe)...")
    write_nc(emis, LAT, LON, out_file)

    print("DONE:", out_file)

