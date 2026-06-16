#!/usr/bin/env python3
"""
Convert CIT point source emissions → WRF-Chem point emission NetCDF
"""

import numpy as np
import xarray as xr
import sys

# -----------------------------
# CONFIG (EDIT THIS)
# -----------------------------

SPECIES = [
    "NO", "NO2", "CO", "SO2", "PM",
    "ALD2", "ETH", "FORM", "ISOP",
    "OLE", "PAR", "TOL", "XYL",
    "ETOH", "MEOH", "UNR", "NH3"
]

NSPEC = len(SPECIES)


# -----------------------------
# PARSE CIT FILE
# -----------------------------

def decode_sid(sid):
    sid = sid.strip()
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
        line = lines[i]

        if line.startswith("E") and "999999" not in line:
            parts = line.split()
            sid = parts[0]
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


# -----------------------------
# BUILD WRF-CHEM GRID
# -----------------------------

def build_wrfchemi(cit_data, nx=210, ny=273, nt=24):
    """
    Create 4D emission array:
    Time × Species × Y × X
    """

    emis = np.zeros((nt, NSPEC, ny, nx))

    for item in cit_data:
        t = item["hour"]
        x = item["x"] - 1
        y = item["y"] - 1

        if 0 <= x < nx and 0 <= y < ny:
            emis[t, :, y, x] += item["emis"]

    return emis


# -----------------------------
# WRITE NETCDF
# -----------------------------

def write_netcdf(emis, outfile):
    nt, ns, ny, nx = emis.shape

    ds = xr.Dataset(
        {
            "emissions": (["Time", "Species", "south_north", "west_east"], emis)
        },
        coords={
            "Time": np.arange(nt),
            "Species": SPECIES,
            "south_north": np.arange(ny),
            "west_east": np.arange(nx),
        }
    )

    ds["emissions"].attrs["units"] = "g s-1"
    ds.to_netcdf(outfile)


# -----------------------------
# MAIN
# -----------------------------

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python cit_to_wrfchemi.py input.in output.nc")
        sys.exit(1)

    infile = sys.argv[1]
    outfile = sys.argv[2]

    print("Reading CIT...")
    data = read_cit(infile)

    print("Building WRF-Chem grid...")
    emis = build_wrfchemi(data)

    print("Writing NetCDF...")
    write_netcdf(emis, outfile)

    print("Done:", outfile)

