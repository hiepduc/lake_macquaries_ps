import xarray as xr
import numpy as np
import glob
import os

# =========================
# 1. POWER PLANT
# =========================
plant = {
    "lat": -33.161,
    "lon": 151.541,
    "Hs": 178.0,
    "D": 10.3,
    "V": 26.0,
    "Ts": 369.0,
}

emis_gps = {
    "NO": 1527.0,
    "NO2": 124.0,
    "SO2": 2551.7,
    "PM10": 75.1,
}

mw = {"NO": 30.0, "NO2": 46.0, "SO2": 64.0}

# =========================
# 2. GRID (wrfinput)
# =========================
wrfinput = xr.open_dataset("../wrfinput_d01", engine="netcdf4")

XLAT = wrfinput["XLAT"].isel(Time=0)
XLONG = wrfinput["XLONG"].isel(Time=0)

dist = np.sqrt((XLAT - plant["lat"])**2 + (XLONG - plant["lon"])**2)
j, i = np.unravel_index(dist.argmin(), dist.shape)

print(f"Grid cell: i={i}, j={j}")

# =========================
# 3. PLUME RISE
# =========================
g = 9.81
Ta = 300.0
U = 5.0

F = (g * plant["V"] * plant["D"]**2 / 4.0) * ((plant["Ts"] - Ta) / plant["Ts"])
dH = 1.6 * (F / U) ** (1/3)
Heff = plant["Hs"] + dH

# =========================
# 4. VERTICAL LEVEL
# =========================
PH = wrfinput["PH"]
PHB = wrfinput["PHB"]

z = (PH + PHB) / 9.81
z = z.isel(Time=0)
z_mid = 0.5 * (z[:-1, :, :] + z[1:, :, :])

z_col = z_mid[:, j, i].values
k = np.argmin(np.abs(z_col - Heff))
k2 = min(k + 1, len(z_col) - 1)

# =========================
# 5. UNIT CONVERSION
# =========================
dx = wrfinput.DX / 1000.0
dy = wrfinput.DY / 1000.0
area = dx * dy

emis_mol_km2_hr = {}
for sp in ["NO", "NO2", "SO2"]:
    mol_s = emis_gps[sp] / mw[sp]
    emis_mol_km2_hr[sp] = mol_s * 3600 / area

# PM10 split → PM2.5 + coarse
pm25 = emis_gps["PM10"] * 0.7
pmc  = emis_gps["PM10"] * 0.3

# =========================
# 6. PROCESS FILES (SAFE OUTPUT)
# =========================
files = sorted(glob.glob("../wrfchemi_d01_*"))

out_dir = "./wrfchemi_powerplant"
os.makedirs(out_dir, exist_ok=True)

for f in files:
    print("Processing:", f)

    ds = xr.open_dataset(f, engine="netcdf4")

    t = 0  # hourly file

    # =========================
    # GAS EMISSIONS
    # =========================
    ds["E_NO"][t, k, j, i]  += emis_mol_km2_hr["NO"] * 0.7
    ds["E_NO"][t, k2, j, i] += emis_mol_km2_hr["NO"] * 0.3

    ds["E_NO2"][t, k, j, i]  += emis_mol_km2_hr["NO2"] * 0.7
    ds["E_NO2"][t, k2, j, i] += emis_mol_km2_hr["NO2"] * 0.3

    ds["E_SO2"][t, k, j, i]  += emis_mol_km2_hr["SO2"] * 0.7
    ds["E_SO2"][t, k2, j, i] += emis_mol_km2_hr["SO2"] * 0.3

    # =========================
    # PM EMISSIONS (ROBUST FIX)
    # =========================
    if "E_PM_25" in ds.variables:
        pm_var = "E_PM_25"
    elif "E_PM25" in ds.variables:
        pm_var = "E_PM25"
    elif "E_PM_10" in ds.variables:
        pm_var = "E_PM_10"
    else:
        raise KeyError("No PM variable found in file")

    ds[pm_var][t, k, j, i]  += pm25 / area
    ds[pm_var][t, k2, j, i] += pm25 / area

    # =========================
    # OPTIONAL COARSE PM (ONLY IF EXISTS)
    # =========================
    for coarse_name in ["E_PMC", "E_PMCOARSE"]:
        if coarse_name in ds.variables:
            ds[coarse_name][t, k, j, i]  += pmc / area
            ds[coarse_name][t, k2, j, i] += pmc / area
            break

    # =========================
    # 7. SAVE OUTPUT
    # =========================
    base = os.path.basename(f)
    out_file = os.path.join(out_dir, base + "_pp")

    ds.to_netcdf(out_file)
    ds.close()

    print("  → saved:", out_file)

print("DONE: all files written to wrfchemi_powerplant/")

