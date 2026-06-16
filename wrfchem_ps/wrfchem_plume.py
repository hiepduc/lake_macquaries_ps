#!/usr/bin/env python3
"""
WRF-Chem-ready CIT point source injector with:
- Briggs plume rise (simplified but physical)
- vertical redistribution into model layers
- hourly emissions handling
"""

import numpy as np
import xarray as xr
import sys

g = 9.81  # gravity

# -------------------------------------------------
# SPECIES (CBIV)
# -------------------------------------------------
SPECIES = [
    "NO", "NO2", "CO", "SO2", "PM",
    "ALD2", "ETH", "FORM", "ISOP",
    "OLE", "PAR", "TOL", "XYL",
    "ETOH", "MEOH", "UNR", "NH3"
]

NSPEC = len(SPECIES)


# -------------------------------------------------
# CIT PARSER
# -------------------------------------------------

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
            sid = line.split()[0]
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
# PLUME RISE (BRIGGS - simplified)
# -------------------------------------------------

def plume_rise(stack_h, T_stack, T_amb, V, D):
    """
    Simplified Briggs plume rise
    """

    # buoyancy flux
    Fb = (g * V * D**2 * (T_stack - T_amb)) / (4 * T_stack)

    if Fb <= 0:
        return 0.0

    # unstable/neutral approximation
    delta_h = 1.6 * (Fb**(1/3)) * 100  # scaling to meters

    return delta_h


# -------------------------------------------------
# VERTICAL DISTRIBUTION
# -------------------------------------------------

def distribute_vertical(z_levels, effective_height):
    """
    Distribute emissions into WRF vertical layers
    Gaussian weighting around plume center
    """

    sigma = 150.0  # plume spread (m)

    weights = np.exp(-((z_levels - effective_height)**2) / (2 * sigma**2))
    return weights / weights.sum()


# -------------------------------------------------
# MAIN GRID BUILDER
# -------------------------------------------------

def build_wrfchemi(data, nx=210, ny=273, nz=20):

    nt = 24

    emis = np.zeros((nt, NSPEC, nz, ny, nx))

    # WRF vertical grid (simplified heights)
    z_levels = np.linspace(50, 5000, nz)

    for d in data:
        t = d["hour"]
        x = d["x"] - 1
        y = d["y"] - 1

        # -------------------------------------------------
        # STACK PARAMETERS (DEFAULTS if not available)
        # -------------------------------------------------
        stack_h = 120.0
        stack_d = 5.0
        T_stack = 400.0
        T_amb = 290.0
        V = 25.0

        # -------------------------------------------------
        # PLUME RISE
        # -------------------------------------------------
        delta_h = plume_rise(stack_h, T_stack, T_amb, V, stack_d)
        eff_h = stack_h + delta_h

        # -------------------------------------------------
        # VERTICAL WEIGHTING
        # -------------------------------------------------
        vert_w = distribute_vertical(z_levels, eff_h)

        # -------------------------------------------------
        # INJECT EMISSIONS
        # -------------------------------------------------
        if 0 <= x < nx and 0 <= y < ny:

            for k in range(nz):
                emis[t, :, k, y, x] += d["emis"] * vert_w[k]

    return emis


# -------------------------------------------------
# NETCDF OUTPUT
# -------------------------------------------------

def write_netcdf(emis, outfile):

    nt, ns, nz, ny, nx = emis.shape

    ds = xr.Dataset(
        {
            "E_NO":  (["Time","bottom_top","south_north","west_east"], emis[:,0]),
            "E_NO2": (["Time","bottom_top","south_north","west_east"], emis[:,1]),
            "E_CO":  (["Time","bottom_top","south_north","west_east"], emis[:,2]),
            "E_SO2": (["Time","bottom_top","south_north","west_east"], emis[:,3]),
            "E_PM":  (["Time","bottom_top","south_north","west_east"], emis[:,4]),
        },
        coords={
            "Time": np.arange(24),
            "bottom_top": np.arange(nz),
            "south_north": np.arange(ny),
            "west_east": np.arange(nx),
        }
    )

    ds.attrs["title"] = "WRF-Chem point source emissions (plume-rise injected)"
    ds.to_netcdf(outfile)


# -------------------------------------------------
# MAIN
# -------------------------------------------------

if __name__ == "__main__":

    if len(sys.argv) != 3:
        print("Usage: python wrfchem_plume.py input.in output.nc")
        sys.exit(1)

    infile = sys.argv[1]
    outfile = sys.argv[2]

    print("Reading CIT...")
    data = read_cit(infile)

    print("Building WRF-Chem plume-rise emissions...")
    emis = build_wrfchemi(data)

    print("Writing NetCDF...")
    write_netcdf(emis, outfile)

    print("DONE:", outfile)

