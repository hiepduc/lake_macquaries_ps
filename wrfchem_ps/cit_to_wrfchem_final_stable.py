#!/usr/bin/env python3
import numpy as np
import re
import sys
from netCDF4 import Dataset
from pyproj import CRS, Transformer

# -----------------------------
# SPECIES
# -----------------------------
SPECIES = [
    "NO","NO2","CO","SO2","PM",
    "ALD2","ETH","FORM","ISOP",
    "OLE","PAR","TOL","XYL",
    "ETOH","MEOH","UNR","NH3"
]

NSPEC = len(SPECIES)

# -----------------------------
# SAFE WPS PARSER (FIXED)
# -----------------------------
# READ WPS
# -------------------------------------------------
def read_wps(fname):

    import re

    # safer reading (WPS often has non-UTF8 chars)
    with open(fname, "r", encoding="latin-1", errors="ignore") as f:
        txt = f.read()

    def get(key):

        # match: key = value , safely ignoring spaces and commas
        pattern = rf"{key}\s*=\s*([-+0-9\.eEdD]+)"

        m = re.search(pattern, txt)

        if not m:
            raise ValueError(f"Cannot find {key} in namelist.wps")

        return float(m.group(1).replace("D", "E").replace("d", "e"))

    return {
        "ref_lat": get("ref_lat"),
        "ref_lon": get("ref_lon"),
        "truelat1": get("truelat1"),
        "truelat2": get("truelat2"),
        "stand_lon": get("stand_lon"),
        "dx": get("dx"),
        "dy": get("dy"),
        "e_we": int(get("e_we")),
        "e_sn": int(get("e_sn")),
    }

# -----------------------------
# GRID
# -----------------------------
def build_grid(wps):

    nx, ny = wps["e_we"], wps["e_sn"]

    proj = CRS.from_proj4(
        f"+proj=lcc +lat_1={wps['truelat1']} "
        f"+lat_2={wps['truelat2']} "
        f"+lat_0={wps['ref_lat']} "
        f"+lon_0={wps['stand_lon']} "
        "+datum=WGS84 +units=m +no_defs"
    )

    tf = Transformer.from_crs(proj, "EPSG:4326", always_xy=True)

    x = (np.arange(nx) + 0.5) * wps["dx"]
    y = (np.arange(ny) + 0.5) * wps["dy"]

    xx, yy = np.meshgrid(x, y)

    lon, lat = tf.transform(xx, yy)

    return lat.astype(np.float32), lon.astype(np.float32)

# -----------------------------
# CIT READER (SAFE)
# -----------------------------
def read_cit(fname):

    data = []
    NSPEC = len(SPECIES)

    with open(fname, encoding="latin-1", errors="ignore") as f:
        lines = f.readlines()

    i = 0

    while i < len(lines):

        if lines[i].startswith("E") and "999999" not in lines[i]:

            sid = lines[i].split()[0]

            hour = int(sid[1:3])
            x = int(sid[3:6])
            y = int(sid[6:9])

            i += 1
            vals = []

            while len(vals) < NSPEC:
                vals += [float(v) for v in lines[i].split()]
                i += 1

            data.append((hour, x, y, np.array(vals[:NSPEC])))

        else:
            i += 1

    return data

# -----------------------------
# VERTICAL DISTRIBUTION
# -----------------------------
def vertical_profile(nz, h=300):

    z = np.linspace(50, 4000, nz)
    sigma = 250

    w = np.exp(-(z - h)**2 / (2*sigma**2))
    return w / w.sum()

# -----------------------------
# INJECTION
# -----------------------------
def inject(cit, nx, ny, nz=20):

    emis = np.zeros((24, NSPEC, nz, ny, nx), dtype=np.float32)

    CIT_NX, CIT_NY = 210, 273
    wv = vertical_profile(nz)

    for hour, x, y, val in cit:

        i = int(x / CIT_NX * nx)
        j = int(y / CIT_NY * ny)

        i = np.clip(i, 0, nx-1)
        j = np.clip(j, 0, ny-1)

        emis[hour, :, :, j, i] += val[:, None] * wv[None, :]

    return emis

# -----------------------------
# SAFE NETCDF WRITE (FIXED)
# -----------------------------
def write_nc(emis, LAT, LON, wps, out):

    nt, ns, nz, ny, nx = emis.shape

    nc = Dataset(out, "w", format="NETCDF4")

    # dimensions
    nc.createDimension("Time", nt)
    nc.createDimension("DateStrLen", 19)
    nc.createDimension("bottom_top", nz)
    nc.createDimension("south_north", ny)
    nc.createDimension("west_east", nx)

    # grid
    lat = nc.createVariable("XLAT", "f4", ("south_north","west_east"))
    lon = nc.createVariable("XLONG", "f4", ("south_north","west_east"))

    lat[:] = LAT
    lon[:] = LON

    # WRF-Chem metadata
    nc.CEN_LAT = wps["ref_lat"]
    nc.CEN_LON = wps["ref_lon"]
    nc.STAND_LON = wps["stand_lon"]

    # Times (WRF-safe)
    times = nc.createVariable("Times", "S1", ("Time","DateStrLen"))

    for t in range(nt):
        ts = f"2023-12-19_{t:02d}:00:00"
        times[t, :] = np.array(list(ts.ljust(19)))

    # emissions
    for s, name in enumerate(SPECIES):

        v = nc.createVariable(
            f"E_{name}",
            "f4",
            ("Time","bottom_top","south_north","west_east"),
            zlib=True
        )

        v[:] = emis[:, s, :, :, :]

    nc.description = "CIT → WRF-Chem emissions FINAL STABLE"
    nc.close()

# -----------------------------
# MAIN
# -----------------------------
if __name__ == "__main__":

    cit_file = sys.argv[1]
    wps_file = sys.argv[2]
    out_file = sys.argv[3]

    print("Reading WPS...")
    wps = read_wps(wps_file)

    print("Building grid...")
    LAT, LON = build_grid(wps)

    print("Reading CIT...")
    cit = read_cit(cit_file)

    print("Injecting emissions...")
    emis = inject(cit, wps["e_we"], wps["e_sn"])

    print("Writing NetCDF...")
    write_nc(emis, LAT, LON, wps, out_file)

    print("DONE:", out_file)

