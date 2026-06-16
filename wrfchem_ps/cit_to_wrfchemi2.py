#!/usr/bin/env python3
"""
Direct CIT point-source injection into WRF-Chem grid
using XLAT / XLONG nearest-neighbour mapping
"""

import numpy as np
import xarray as xr

# -------------------------------------------------
# CONFIG
# -------------------------------------------------

SPECIES = [
    "NO", "NO2", "CO", "SO2", "PM",
    "ALD2", "ETH", "FORM", "ISOP",
    "OLE", "PAR", "TOL", "XYL",
    "ETOH", "MEOH", "UNR", "NH3"
]

NSPEC = len(SPECIES)


# -------------------------------------------------
# CIT PARSER (simplified)
# -------------------------------------------------

def decode_sid(sid):
    return {
        "hour": int(sid[1:3]),
        "x": int(sid[3:6]),
        "y": int(sid[6:9]),
        "src_id": int(sid[9:]) if sid[9:].isdigit() else None
    }


def read_emis(lines, i):
    emis = []
    while len(emis) < NSPEC:
        emis.extend([float(v) for v in lines[i].split()])
        i += 1
    return np.array(emis[:NSPEC]), i


def read_cit(infile):
    with open(infile, "r", encoding="latin-1") as f:
        lines = f.readlines()

    data = []
    i = 0

    while i < len(lines):
        if lines[i].startswith("E") and "999999" not in lines[i]:
            sid = lines[i].split()[0]
            meta = decode_sid(sid)

            i += 1
            emis, i = read_emis(lines, i)

            data.append({
                "hour": meta["hour"],
                "x": meta["x"],
                "y": meta["y"],
                "emis": emis
            })
        else:
            i += 1

    return data


# -------------------------------------------------
# LOAD WRF GRID
# -------------------------------------------------

def load_wrf_grid(wrf_file):
    ds = xr.open_dataset(wrf_file)

    return ds["XLAT"][0].values, ds["XLONG"][0].values


# -------------------------------------------------
# FIND NEAREST GRID CELL
# -------------------------------------------------

def find_nearest(lat, lon, XLAT, XLONG):
    dist = (XLAT - lat)**2 + (XLONG - lon)**2
    j, i = np.unravel_index(np.argmin(dist), dist.shape)
    return i, j


# -------------------------------------------------
# MAIN INJECTION
# -------------------------------------------------

def inject_to_wrf(cit_data, wrf_file, nx, ny, nz=20):

    XLAT, XLONG = load_wrf_grid(wrf_file)

    nt = 24

    emis = np.zeros((nt, NSPEC, nz, ny, nx))

    # vertical profile (simple plume spread)
    z_levels = np.linspace(50, 4000, nz)
    sigma = 200.0

    for d in cit_data:

        t = d["hour"]

        # -------------------------------------------------
        # convert CIT grid → approximate lat/lon
        # (if you don't have true CRS, use WRF centroid method)
        # -------------------------------------------------
        lat = np.mean(XLAT[d["y"], :])
        lon = np.mean(XLONG[:, d["x"]])

        i, j = find_nearest(lat, lon, XLAT, XLONG)

        # -------------------------------------------------
        # vertical distribution (Gaussian plume)
        # -------------------------------------------------
        stack_h = 120.0
        eff_h = stack_h  # (plug plume rise here if needed)

        vert_w = np.exp(-(z_levels - eff_h)**2 / (2*sigma**2))
        vert_w /= vert_w.sum()

        # -------------------------------------------------
        # inject emissions
        # -------------------------------------------------
        for k in range(nz):
            emis[t, :, k, j, i] += d["emis"] * vert_w[k]

    return emis


# -------------------------------------------------
# WRITE WRF-CHEM NETCDF
# -------------------------------------------------

def write_wrfchemi(emis, wrf_file, outfile):

    ds_ref = xr.open_dataset(wrf_file)

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

    # COPY WRF METADATA (THIS IS CRITICAL)
    ds.attrs = ds_ref.attrs

    # preserve projection metadata automatically
    for v in ["CEN_LAT","CEN_LON","DX","DY","TRUELAT1","TRUELAT2"]:
        if v in ds_ref.attrs:
            ds.attrs[v] = ds_ref.attrs[v]

    ds.to_netcdf(outfile)


# -------------------------------------------------
# MAIN
# -------------------------------------------------

if __name__ == "__main__":

    import sys

    if len(sys.argv) != 4:
        print("Usage: python inject_wrf.py cit.in wrfinput_d01.nc output.nc")
        sys.exit(1)

    cit_file = sys.argv[1]
    wrf_file = sys.argv[2]
    out_file = sys.argv[3]

    print("Reading CIT...")
    data = read_cit(cit_file)

    print("Injecting into WRF grid...")
    emis = inject_to_wrf(data, wrf_file, nx=wrf_file, ny=wrf_file)

    print("Writing WRF-Chem file...")
    write_wrfchemi(emis, wrf_file, out_file)

    print("DONE:", out_file)

