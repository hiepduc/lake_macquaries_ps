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
# READ WPS (ROBUST)
# -----------------------------
def read_wps(fname):

    with open(fname, "r", encoding="latin-1", errors="ignore") as f:
        txt = f.read()

    def get(key):
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
# BUILD WRF GRID
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
# READ CIT FILE
# -----------------------------
def read_cit(fname):

    data = []

    with open(fname, encoding="latin-1", errors="ignore") as f:
        lines = f.readlines()

    i = 0

    while i < len(lines):

        if lines[i].startswith("E") and "999999" not in lines[i]:

            sid = lines[i].split()[0]

            hour = int(sid[1:3])
            x = int(sid[3:6])   # UTM Easting (km)
            y = int(sid[6:9])   # UTM Northing (km)

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
# VERTICAL PROFILE
# -----------------------------
def vertical_profile(nz, h=300):

    z = np.linspace(50, 4000, nz)
    sigma = 250

    w = np.exp(-(z - h)**2 / (2*sigma**2))
    return w / w.sum()

# -----------------------------
# INJECTION (FIXED: UTM → WRF)
# -----------------------------
from pyproj import Transformer
import numpy as np

utm_to_ll = Transformer.from_crs("EPSG:32756", "EPSG:4326", always_xy=True)

def inject(cit, LAT, LON, nz=20):

    ny, nx = LAT.shape
    emis = np.zeros((24, NSPEC, nz, ny, nx), dtype=np.float32)

    wv = vertical_profile(nz)

    for hour, x, y, val in cit:

        # ---- FIX: real UTM conversion ----
        lon_pt, lat_pt = utm_to_ll.transform(x * 1000.0, y * 1000.0)

        # ---- nearest WRF grid cell ----
        dist = (LAT - lat_pt)**2 + (LON - lon_pt)**2
        j, i = np.unravel_index(np.argmin(dist), dist.shape)

        # ---- distribute spatially (IMPORTANT) ----
        for dj in range(-1, 2):
            for di in range(-1, 2):

                jj = np.clip(j + dj, 0, ny-1)
                ii = np.clip(i + di, 0, nx-1)

                w = np.exp(-(di**2 + dj**2) / 2.0)

                emis[hour, :, :, jj, ii] += val[:, None] * wv[None, :] * w

    return emis


# -----------------------------
# WRITE NETCDF
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

    # metadata
    nc.CEN_LAT = wps["ref_lat"]
    nc.CEN_LON = wps["ref_lon"]
    nc.STAND_LON = wps["stand_lon"]

    # Times
    times = nc.createVariable("Times", "S1", ("Time","DateStrLen"))

    for t in range(nt):
        ts = f"2023-12-19_{t:02d}:00:00"
        times[t, :] = np.array(list(ts.ljust(19)), dtype="S1")

    # emissions
    for s, name in enumerate(SPECIES):

        v = nc.createVariable(
            f"E_{name}",
            "f4",
            ("Time","bottom_top","south_north","west_east"),
            zlib=True
        )

        v[:] = emis[:, s, :, :, :]

    nc.description = "CIT → WRF-Chem emissions (UTM-corrected)"
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

    print("Injecting emissions (UTM corrected)...")
    emis = inject(cit, LAT, LON)

    print("Writing NetCDF...")
    write_nc(emis, LAT, LON, wps, out_file)

    print("DONE:", out_file)

