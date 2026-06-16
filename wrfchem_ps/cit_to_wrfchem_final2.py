#!/usr/bin/env python3
"""
CIT → WRF-Chem emissions using WPS namelist grid
HPC-safe version (NO xarray, NO segfaults)
"""

import numpy as np
import re
import sys
import os
from netCDF4 import Dataset
from pyproj import CRS, Transformer

# Prevent HDF5 locking issues on Lustre
os.environ["HDF5_USE_FILE_LOCKING"] = "FALSE"

# -------------------------------------------------
# SPECIES (CB-IV)
# -------------------------------------------------
SPECIES = [
    "NO","NO2","CO","SO2","PM",
    "ALD2","ETH","FORM","ISOP",
    "OLE","PAR","TOL","XYL",
    "ETOH","MEOH","UNR","NH3"
]
NSPEC = len(SPECIES)


# -------------------------------------------------
# READ WPS NAMELIST
# -------------------------------------------------
def read_wps(fname):

    with open(fname, "r") as f:
        txt = f.read()

    def get(key):
        m = re.search(rf"{key}\s*=\s*([^,]+)", txt)
        return m.group(1).strip()

    return {
        "ref_lat": float(get("ref_lat")),
        "ref_lon": float(get("ref_lon")),
        "truelat1": float(get("truelat1")),
        "truelat2": float(get("truelat2")),
        "stand_lon": float(get("stand_lon")),
        "dx": float(get("dx")),
        "dy": float(get("dy")),
        "e_we": int(get("e_we")),
        "e_sn": int(get("e_sn")),
    }


# -------------------------------------------------
# BUILD SYNTHETIC WRF GRID (FROM WPS)
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

    x = np.arange(nx) * wps["dx"]
    y = np.arange(ny) * wps["dy"]

    xx, yy = np.meshgrid(x, y)

    lon, lat = transformer.transform(xx, yy)

    return lat, lon


# -------------------------------------------------
# CIT HEADER (SAFE PARSER)
# -------------------------------------------------
def read_cit_header(fname):

    x_min = x_max = y_min = y_max = None

    with open(fname, "r", encoding="latin-1") as f:
        for line in f:

            if "Grid Easting from" in line:
                nums = re.findall(r"\d+", line)
                x_min, x_max = int(nums[0]), int(nums[1])

            if "Grid Northing from" in line:
                nums = re.findall(r"\d+", line)
                y_min, y_max = int(nums[0]), int(nums[1])

    return x_min, x_max, y_min, y_max


# -------------------------------------------------
# CIT EMISSIONS
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
# PLUME RISE (SIMPLE GAUSSIAN)
# -------------------------------------------------
def plume_height():
    return 300.0


def vertical_profile(nz, h):

    z = np.linspace(50, 4000, nz)
    sigma = 200.0

    w = np.exp(-(z - h)**2 / (2*sigma**2))
    return w / np.sum(w)


# -------------------------------------------------
# FIND GRID CELL
# -------------------------------------------------
def find_cell(lat, lon, LAT, LON):

    dist = (LAT - lat)**2 + (LON - lon)**2
    j, i = np.unravel_index(np.argmin(dist), dist.shape)

    return i, j


# -------------------------------------------------
# EMISSION INJECTION
# -------------------------------------------------
def inject(cit, LAT, LON, nx, ny, nz=20):

    emis = np.zeros((24, NSPEC, nz, ny, nx))

    for d in cit:

        t = d["hour"]

        # fallback placement (domain center)
        lat = np.mean(LAT)
        lon = np.mean(LON)

        i, j = find_cell(lat, lon, LAT, LON)

        w = vertical_profile(nz, plume_height())

        for k in range(nz):
            emis[t, :, k, j, i] += d["emis"] * w[k]

    return emis


# -------------------------------------------------
# WRITE NETCDF (HPC SAFE)
# -------------------------------------------------
def write_nc(emis, LAT, LON, outfile):

    nt, ns, nz, ny, nx = emis.shape

    nc = Dataset(outfile, "w", format="NETCDF4")

    # dimensions
    nc.createDimension("Time", nt)
    nc.createDimension("bottom_top", nz)
    nc.createDimension("south_north", ny)
    nc.createDimension("west_east", nx)

    # coordinates
    latv = nc.createVariable("XLAT", "f4", ("south_north","west_east"))
    lonv = nc.createVariable("XLONG", "f4", ("south_north","west_east"))

    latv[:, :] = LAT
    lonv[:, :] = LON

    # emissions
    for i, s in enumerate(SPECIES):

        v = nc.createVariable(
            f"E_{s}",
            "f4",
            ("Time","bottom_top","south_north","west_east"),
            zlib=True,
            complevel=4
        )

        v[:] = emis[:, i, :, :, :]

    # global metadata
    nc.description = "CIT → WRF-Chem emissions (WPS-based grid)"
    nc.source = "CIT + WPS namelist"

    nc.close()


# -------------------------------------------------
# MAIN
# -------------------------------------------------
if __name__ == "__main__":

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
    emis = inject(cit, LAT, LON, wps["e_we"], wps["e_sn"])

    print("Writing NetCDF (HPC-safe)...")
    write_nc(emis, LAT, LON, out_file)

    print("DONE:", out_file)

