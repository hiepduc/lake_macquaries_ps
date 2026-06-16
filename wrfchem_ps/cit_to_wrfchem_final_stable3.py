#!/usr/bin/env python3
import numpy as np
import re
import sys
from netCDF4 import Dataset
from pyproj import CRS, Transformer

# =========================================================
# SPECIES
# =========================================================
SPECIES = [
    "NO","NO2","CO","SO2","PM",
    "ALD2","ETH","FORM","ISOP",
    "OLE","PAR","TOL","XYL",
    "ETOH","MEOH","UNR","NH3"
]

NSPEC = len(SPECIES)

# =========================================================
# READ WPS
# =========================================================
def read_wps(fname):

    with open(fname, "r", encoding="latin-1", errors="ignore") as f:
        txt = f.read()

    def get(key):
        pattern = rf"{key}\s*=\s*([-+0-9\.eEdD]+)"
        m = re.search(pattern, txt)
        if not m:
            raise ValueError(f"Cannot find {key}")
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

# =========================================================
# BUILD WRF GRID (REAL LCC SPACE)
# =========================================================
def build_wrf_grid(wps):

    wrf_proj = CRS.from_proj4(
        f"+proj=lcc +lat_1={wps['truelat1']} "
        f"+lat_2={wps['truelat2']} "
        f"+lat_0={wps['ref_lat']} "
        f"+lon_0={wps['stand_lon']} "
        "+datum=WGS84 +units=m +no_defs"
    )

    nx, ny = wps["e_we"], wps["e_sn"]

    # centered WRF grid (meters)
    x = (np.arange(nx) - nx/2) * wps["dx"]
    y = (np.arange(ny) - ny/2) * wps["dy"]

    X, Y = np.meshgrid(x, y)

    # convert to lat/lon for ncview
    to_ll = Transformer.from_crs(wrf_proj, "EPSG:4326", always_xy=True)
    lon, lat = to_ll.transform(X, Y)

    return X, Y, lat.astype(np.float32), lon.astype(np.float32)

# =========================================================
# READ CIT EMISSIONS (UTM GRID)
# =========================================================
def read_cit(fname):

    data = []

    with open(fname, encoding="latin-1", errors="ignore") as f:
        lines = f.readlines()

    i = 0
    while i < len(lines):

        if lines[i].startswith("E") and "999999" not in lines[i]:

            sid = lines[i].split()[0]

            hour = int(sid[1:3])
            x = int(sid[3:6])   # km
            y = int(sid[6:9])   # km

            i += 1
            vals = []

            while len(vals) < NSPEC:
                vals += [float(v) for v in lines[i].split()]
                i += 1

            data.append((hour, x, y, np.array(vals[:NSPEC])))

        else:
            i += 1

    return data

# =========================================================
# VERTICAL PROFILE
# =========================================================
def vertical_profile(nz, h=300):

    z = np.linspace(50, 4000, nz)
    sigma = 250
    w = np.exp(-(z - h)**2 / (2*sigma**2))
    return w / w.sum()

# =========================================================
# INJECTION (CORRECT DISTANCE MATCHING)
# =========================================================
def inject(cit, X, Y, wps, nz=20):

    ny, nx = X.shape
    emis = np.zeros((24, NSPEC, nz, ny, nx), dtype=np.float32)

    wv = vertical_profile(nz)

    # UTM Zone 56S (Sydney/NSW)
    utm_to_ll = Transformer.from_crs("EPSG:32756", "EPSG:4326", always_xy=True)

    # WRF projection
    wrf_proj = CRS.from_proj4(
        f"+proj=lcc +lat_1={wps['truelat1']} "
        f"+lat_2={wps['truelat2']} "
        f"+lat_0={wps['ref_lat']} "
        f"+lon_0={wps['stand_lon']} "
        "+datum=WGS84 +units=m +no_defs"
    )

    ll_to_xy = Transformer.from_crs("EPSG:4326", wrf_proj, always_xy=True)

    for hour, x, y, val in cit:

        # CIT grid km → meters
        easting = x * 1000.0
        northing = y * 1000.0

        # UTM → lat/lon
        lon, lat = utm_to_ll.transform(easting, northing)

        # lat/lon → WRF projection meters
        wx, wy = ll_to_xy.transform(lon, lat)

        # FULL 2D nearest cell search (IMPORTANT FIX)
        dist2 = (X - wx)**2 + (Y - wy)**2
        j, i = np.unravel_index(np.argmin(dist2), dist2.shape)

        emis[hour, :, :, j, i] += val[:, None] * wv[None, :]

    return emis

# =========================================================
# WRITE NETCDF (NCVIEW COMPATIBLE)
# =========================================================
def write_nc(emis, LAT, LON, wps, out):

    nt, ns, nz, ny, nx = emis.shape

    nc = Dataset(out, "w", format="NETCDF4")

    nc.createDimension("Time", nt)
    nc.createDimension("DateStrLen", 19)
    nc.createDimension("bottom_top", nz)
    nc.createDimension("south_north", ny)
    nc.createDimension("west_east", nx)

    lat = nc.createVariable("XLAT", "f4", ("south_north","west_east"))
    lon = nc.createVariable("XLONG", "f4", ("south_north","west_east"))

    lat[:] = LAT
    lon[:] = LON

    # WRF metadata
    nc.CEN_LAT = wps["ref_lat"]
    nc.CEN_LON = wps["ref_lon"]
    nc.STAND_LON = wps["stand_lon"]

    # time axis
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

    nc.close()

# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":

    cit_file = sys.argv[1]
    wps_file = sys.argv[2]
    out_file = sys.argv[3]

    print("Reading WPS...")
    wps = read_wps(wps_file)

    print("Building WRF grid...")
    X, Y, LAT, LON = build_wrf_grid(wps)

    print("Reading CIT...")
    cit = read_cit(cit_file)

    print("Injecting emissions (FINAL CORRECT VERSION)...")
    emis = inject(cit, X, Y, wps)

    print("Writing NetCDF...")
    write_nc(emis, LAT, LON, wps, out_file)

    print("DONE:", out_file)

