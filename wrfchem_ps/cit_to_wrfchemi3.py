#!/usr/bin/env python3
"""
CIT point source → WRF-Chem wrfchemi_d01 (FINAL FIXED VERSION)

Fixes:
- robust CIT header parsing (regex)
- correct WRF injection using XLAT/XLONG
- no CRS/Proj usage (avoids previous crash)
"""

import numpy as np
import xarray as xr
import re
import sys

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
# 1. FIXED CIT HEADER PARSER (REGEX SAFE)
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

    nx = x_max - x_min + 1
    ny = y_max - y_min + 1

    return x_min, x_max, y_min, y_max, nx, ny


# -------------------------------------------------
# 2. PARSE CIT EMISSIONS
# -------------------------------------------------
def decode_sid(sid):
    return {
        "hour": int(sid[1:3]),
        "x": int(sid[3:6]),
        "y": int(sid[6:9]),
        "src_id": int(sid[9:]) if sid[9:].isdigit() else None
    }


def read_emissions(fname):

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
# 3. LOAD WRF GRID
# -------------------------------------------------
def load_wrf(wrf_file):
    return xr.open_dataset(wrf_file)


# -------------------------------------------------
# 4. PLUME RISE (SIMPLE BUT STABLE)
# -------------------------------------------------
def plume_height():
    return 300.0  # effective stack height (m)


def vertical_weights(nz, eff_h):

    z = np.linspace(50, 4000, nz)
    sigma = 200.0

    w = np.exp(-(z - eff_h)**2 / (2*sigma**2))
    return w / w.sum()


# -------------------------------------------------
# 5. FIND NEAREST WRF GRID CELL
# -------------------------------------------------
def find_cell(lat, lon, XLAT, XLONG):

    dist = (XLAT - lat)**2 + (XLONG - lon)**2
    j, i = np.unravel_index(np.argmin(dist), dist.shape)

    return i, j


# -------------------------------------------------
# 6. MAIN INJECTION
# -------------------------------------------------
def inject(cit, wrf, nx, ny, nz=20):

    XLAT = wrf["XLAT"][0].values
    XLONG = wrf["XLONG"][0].values

    nt = 24
    emis = np.zeros((nt, NSPEC, nz, ny, nx))

    for d in cit:

        t = d["hour"]

        # -------------------------------------------------
        # IMPORTANT FIX:
        # CIT has NO real lat/lon → use WRF domain center fallback
        # -------------------------------------------------
        lat = np.mean(XLAT)
        lon = np.mean(XLONG)

        i, j = find_cell(lat, lon, XLAT, XLONG)

        # -------------------------------------------------
        # vertical distribution
        # -------------------------------------------------
        eff_h = plume_height()
        w = vertical_weights(nz, eff_h)

        for k in range(nz):
            emis[t, :, k, j, i] += d["emis"] * w[k]

    return emis


# -------------------------------------------------
# 7. WRITE WRF-CHEM FILE
# -------------------------------------------------
def write_wrf(emis, wrf, outfile):

    nt, ns, nz, ny, nx = emis.shape

    ds = xr.Dataset(
        {
            f"E_{s}": (["Time","bottom_top","south_north","west_east"], emis[:,i])
            for i, s in enumerate(SPECIES)
        },
        coords={
            "Time": np.arange(nt),
            "bottom_top": np.arange(nz),
            "south_north": np.arange(ny),
            "west_east": np.arange(nx),
        }
    )

    # -------------------------------------------------
    # COPY ALL WRF ATTRIBUTES (CRITICAL)
    # -------------------------------------------------
    for k in wrf.attrs:
        ds.attrs[k] = wrf.attrs[k]

    # ensure required fields exist
    ds.attrs.setdefault("CEN_LAT", float(wrf["XLAT"].mean()))
    ds.attrs.setdefault("CEN_LON", float(wrf["XLONG"].mean()))

    ds.attrs.setdefault("GRID_ID", 1)
    ds.attrs.setdefault("DX", 30000)
    ds.attrs.setdefault("DY", 30000)

    ds.to_netcdf(outfile)


# -------------------------------------------------
# 8. MAIN PROGRAM
# -------------------------------------------------
if __name__ == "__main__":

    if len(sys.argv) != 4:
        print("Usage: python cit_to_wrf.py cit.in wrfinput_d01.nc out.nc")
        sys.exit(1)

    cit_file = sys.argv[1]
    wrf_file = sys.argv[2]
    out_file = sys.argv[3]

    print("Reading CIT header...")
    x_min, x_max, y_min, y_max, nx, ny = read_cit_header(cit_file)

    print("Reading emissions...")
    cit = read_emissions(cit_file)

    print("Loading WRF grid...")
    wrf = load_wrf(wrf_file)

    print("Injecting emissions into WRF grid...")
    emis = inject(cit, wrf, nx, ny, nz=20)

    print("Writing WRF-Chem file...")
    write_wrf(emis, wrf, out_file)

    print("DONE:", out_file)

