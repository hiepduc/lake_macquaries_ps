#!/usr/bin/env python3
import numpy as np
import re
import sys
from netCDF4 import Dataset
from pyproj import CRS, Transformer

# =========================================================
SPECIES = [
    "NO","NO2","CO","SO2","PM",
    "ALD2","ETH","FORM","ISOP",
    "OLE","PAR","TOL","XYL",
    "ETOH","MEOH","UNR","NH3"
]
NSPEC = len(SPECIES)

# =========================================================
def read_wps(fname):

    with open(fname, "r", encoding="latin-1", errors="ignore") as f:
        txt = f.read()

    def get_list(key):
        vals = re.findall(rf"{key}\s*=\s*([0-9\.eEdD]+)", txt)
        return [float(v.replace("D","E")) for v in vals]

    def get(key):
        m = re.search(rf"{key}\s*=\s*([-+0-9\.eEdD]+)", txt)
        return float(m.group(1).replace("D","E"))

    return {
        "ref_lat": get("ref_lat"),
        "ref_lon": get("ref_lon"),
        "truelat1": get("truelat1"),
        "truelat2": get("truelat2"),
        "stand_lon": get("stand_lon"),
        "dx": get_list("dx"),
        "dy": get_list("dy"),
        "e_we": get_list("e_we"),
        "e_sn": get_list("e_sn"),
    }

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

# =========================================================
def vertical_profile(nz):
    z = np.linspace(50, 4000, nz)
    w = np.exp(-(z-300)**2/(2*300**2))
    return w / w.sum()

# =========================================================
def build_grid(wps, dom):

    wrf_proj = CRS.from_proj4(
        f"+proj=lcc +lat_1={wps['truelat1']} "
        f"+lat_2={wps['truelat2']} "
        f"+lat_0={wps['ref_lat']} "
        f"+lon_0={wps['stand_lon']} "
        "+datum=WGS84 +units=m +no_defs"
    )

    nx = int(wps["e_we"][dom])
    ny = int(wps["e_sn"][dom])
    dx = wps["dx"][dom]
    dy = wps["dy"][dom]

    x = (np.arange(nx) - nx/2) * dx
    y = (np.arange(ny) - ny/2) * dy

    X, Y = np.meshgrid(x, y)

    to_ll = Transformer.from_crs(wrf_proj, "EPSG:4326", always_xy=True)
    lon, lat = to_ll.transform(X, Y)

    return X, Y, lat, lon

# =========================================================
def inject(cit, lat, lon, nz=20):

    ny, nx = lat.shape
    emis = np.zeros((24, NSPEC, nz, ny, nx), dtype=np.float32)

    wv = vertical_profile(nz)

    utm = Transformer.from_crs("EPSG:32756", "EPSG:4326", always_xy=True)

    for hour, x, y, val in cit:

        lon_pt, lat_pt = utm.transform(x*1000, y*1000)

        dist = (lat - lat_pt)**2 + (lon - lon_pt)**2
        j, i = np.unravel_index(np.argmin(dist), dist.shape)

        emis[hour, :, :, j, i] += val[:, None] * wv[None, :]

    return emis

# =========================================================
def write_nc(emis, LAT, LON, dom, out):

    nt, ns, nz, ny, nx = emis.shape

    nc = Dataset(out, "w")

    nc.createDimension("Time", nt)
    nc.createDimension("bottom_top", nz)
    nc.createDimension("south_north", ny)
    nc.createDimension("west_east", nx)
    nc.createDimension("DateStrLen", 19)

    nc.createVariable("XLAT","f4",("south_north","west_east"))[:] = LAT
    nc.createVariable("XLONG","f4",("south_north","west_east"))[:] = LON

    for s, sp in enumerate(SPECIES):
        v = nc.createVariable(f"E_{sp}","f4",
                              ("Time","bottom_top","south_north","west_east"))
        v[:] = emis[:,s,:,:,:]

    nc.close()

# =========================================================
if __name__ == "__main__":

    cit_file = sys.argv[1]
    wps_file = sys.argv[2]

    print("Reading WPS...")
    wps = read_wps(wps_file)

    print("Reading CIT...")
    cit = read_cit(cit_file)

    ndom = len(wps["e_we"])

    print(f"Found {ndom} domains")

    for dom in range(ndom):

        print(f"\n=== DOMAIN d0{dom+1} ===")

        X, Y, LAT, LON = build_grid(wps, dom)

        emis = inject(cit, LAT, LON)

        out = f"wrfchemi_d0{dom+1}.nc"

        write_nc(emis, LAT, LON, dom, out)

        print("Written:", out)

    print("\nALL DOMAINS COMPLETE")

