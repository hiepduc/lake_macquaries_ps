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
# READ WPS (MULTI-DOMAIN CORRECT)
# =========================================================
def read_wps(fname):

    with open(fname, "r", encoding="latin-1", errors="ignore") as f:
        txt = f.read()

    def get_array(key):
        pattern = rf"{key}\s*=\s*([^\n]+)"
        m = re.search(pattern, txt)
        if not m:
            raise ValueError(f"{key} not found in namelist.wps")
        vals = m.group(1).replace(",", " ").split()
        return [float(v.replace("D","E")) for v in vals]

    def get_int_array(key):
        return [int(v) for v in get_array(key)]

    wps = {
        "ref_lat": get_array("ref_lat")[0],
        "ref_lon": get_array("ref_lon")[0],
        "truelat1": get_array("truelat1")[0],
        "truelat2": get_array("truelat2")[0],
        "stand_lon": get_array("stand_lon")[0],

        "dx": get_array("dx")[0],
        "dy": get_array("dy")[0],

        "e_we": get_int_array("e_we"),
        "e_sn": get_int_array("e_sn"),
        "parent_grid_ratio": get_int_array("parent_grid_ratio"),
    }

    wps["max_dom"] = len(wps["e_we"])

    # ---- compute dx/dy per domain ----
    wps["dx_dom"] = [wps["dx"]]
    wps["dy_dom"] = [wps["dy"]]

    for d in range(1, wps["max_dom"]):
        ratio = wps["parent_grid_ratio"][d]
        wps["dx_dom"].append(wps["dx_dom"][d-1] / ratio)
        wps["dy_dom"].append(wps["dy_dom"][d-1] / ratio)

    return wps

# =========================================================
# BUILD WRF GRID (CENTERED CORRECT)
# =========================================================
def build_wrf_grid(wps, dom):

    nx = wps["e_we"][dom]
    ny = wps["e_sn"][dom]
    dx = wps["dx_dom"][dom]
    dy = wps["dy_dom"][dom]

    proj = CRS.from_proj4(
        f"+proj=lcc +lat_1={wps['truelat1']} "
        f"+lat_2={wps['truelat2']} "
        f"+lat_0={wps['ref_lat']} "
        f"+lon_0={wps['stand_lon']} "
        "+datum=WGS84 +units=m +no_defs"
    )

    # centered WRF grid
    x = (np.arange(nx) - nx/2) * dx
    y = (np.arange(ny) - ny/2) * dy
    X, Y = np.meshgrid(x, y)

    # convert to lat/lon
    to_ll = Transformer.from_crs(proj, "EPSG:4326", always_xy=True)
    lon, lat = to_ll.transform(X, Y)

    return X, Y, lat.astype(np.float32), lon.astype(np.float32), proj

# =========================================================
# READ CIT
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
            x = int(sid[3:6])  # km
            y = int(sid[6:9])  # km

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
# INJECTION (ROBUST)
# =========================================================
def inject(cit, X, Y, proj, nz=20):

    ny, nx = X.shape
    emis = np.zeros((24, NSPEC, nz, ny, nx), dtype=np.float32)

    utm_to_ll = Transformer.from_crs("EPSG:32756", "EPSG:4326", always_xy=True)
    ll_to_wrf = Transformer.from_crs("EPSG:4326", proj, always_xy=True)

    dx = abs(X[0,1] - X[0,0])
    dy = abs(Y[1,0] - Y[0,0])

    xmin = X.min()
    ymin = Y.min()

    wv = vertical_profile(nz)

    for hour, x, y, val in cit:

        easting = x * 1000.0
        northing = y * 1000.0

        lon, lat = utm_to_ll.transform(easting, northing)
        wx, wy = ll_to_wrf.transform(lon, lat)

        i = int((wx - xmin) / dx)
        j = int((wy - ymin) / dy)

        if 0 <= i < nx and 0 <= j < ny:
            emis[hour, :, :, j, i] += val[:, None] * wv[None, :]

    return emis

# =========================================================
# WRITE NETCDF
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

    nc.CEN_LAT = wps["ref_lat"]
    nc.CEN_LON = wps["ref_lon"]
    nc.STAND_LON = wps["stand_lon"]

    times = nc.createVariable("Times", "S1", ("Time","DateStrLen"))

    for t in range(nt):
        ts = f"2023-04-10_{t:02d}:00:00"
        times[t, :] = np.array(list(ts.ljust(19)), dtype="S1")

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

    print("Reading WPS...")
    wps = read_wps(wps_file)

    print("Reading CIT...")
    cit = read_cit(cit_file)

    for dom in range(wps["max_dom"]):

        print(f"\nProcessing domain d0{dom+1}...")

        X, Y, LAT, LON, proj = build_wrf_grid(wps, dom)

        emis = inject(cit, X, Y, proj)

        out = f"wrfchemi_d0{dom+1}.nc"

        write_nc(emis, LAT, LON, wps, out)

        print("Written:", out)

    print("\nALL DONE")

