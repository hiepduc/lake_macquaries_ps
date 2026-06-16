import xarray as xr
import numpy as np
import glob
import os
from datetime import datetime, timedelta

# =========================================================
# 1. POWER PLANT (Vales Point)
# =========================================================
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

# =========================================================
# 2. NSW AEMO-LIKE LOAD PROFILE (NORMALIZED)
# =========================================================
nsw_load = {
    0: 0.75, 1: 0.70, 2: 0.68, 3: 0.67,
    4: 0.70, 5: 0.78, 6: 0.90, 7: 1.00,
    8: 1.05, 9: 0.98, 10: 0.92, 11: 0.88,
    12: 0.85, 13: 0.84, 14: 0.86, 15: 0.92,
    16: 1.00, 17: 1.15, 18: 1.20, 19: 1.10,
    20: 1.00, 21: 0.92, 22: 0.85, 23: 0.80
}

# =========================================================
# 3. TIME CONVERSION (UTC → NSW AEDT = UTC + 11)
# =========================================================
def get_utc_and_nsw_hour(file):
    base = os.path.basename(file)

    # safer: take last 2 chunks only
    date_str, time_str = base.split("_")[-2:]

    dt_utc = datetime.strptime(f"{date_str}_{time_str}", "%Y-%m-%d_%H:%M:%S")

    dt_nsw = dt_utc + timedelta(hours=11)

    return dt_utc.hour, dt_nsw.hour

# =========================================================
# 4. LOAD GRID (WRFINPUT)
# =========================================================
wrfinput = xr.open_dataset("../wrfinput_d01", engine="netcdf4")

XLAT = wrfinput["XLAT"].isel(Time=0)
XLONG = wrfinput["XLONG"].isel(Time=0)

dist = np.sqrt((XLAT - plant["lat"])**2 + (XLONG - plant["lon"])**2)
j, i = np.unravel_index(dist.argmin(), dist.shape)

print(f"Grid cell: i={i}, j={j}")

# =========================================================
# 5. PLUME RISE
# =========================================================
g = 9.81
Ta = 300.0
U = 5.0

F = (g * plant["V"] * plant["D"]**2 / 4.0) * ((plant["Ts"] - Ta) / plant["Ts"])
dH = 1.6 * (F / U) ** (1/3)
Heff = plant["Hs"] + dH

# =========================================================
# 6. VERTICAL LEVEL SELECTION
# =========================================================
PH = wrfinput["PH"]
PHB = wrfinput["PHB"]

z = (PH + PHB) / 9.81
z = z.isel(Time=0)
z_mid = 0.5 * (z[:-1, :, :] + z[1:, :, :])

z_col = z_mid[:, j, i].values
k = np.argmin(np.abs(z_col - Heff))
k2 = min(k + 1, len(z_col) - 1)

# =========================================================
# 7. UNIT CONVERSION
# =========================================================
dx = wrfinput.DX / 1000.0
dy = wrfinput.DY / 1000.0
area = dx * dy

emis_mol_km2_hr = {}
for sp in ["NO", "NO2", "SO2"]:
    mol_s = emis_gps[sp] / mw[sp]
    emis_mol_km2_hr[sp] = mol_s * 3600 / area

pm25 = emis_gps["PM10"] * 0.7
pmc  = emis_gps["PM10"] * 0.3

# =========================================================
# 8. PROCESS ALL HOURLY FILES
# =========================================================
files = sorted(glob.glob("../wrfchemi_d01_*"))

out_dir = "./wrfchemi_powerplant"
os.makedirs(out_dir, exist_ok=True)

for f in files:

    print("\nProcessing:", f)

    ds = xr.open_dataset(f, engine="netcdf4")
    t = 0

    # ---------------------------------------------
    # TIME FACTOR (AEMO + NSW LOCAL TIME)
    # ---------------------------------------------
    utc_hour, nsw_hour = get_utc_and_nsw_hour(f)
    factor = nsw_load[nsw_hour]

    print(f"UTC={utc_hour}, NSW={nsw_hour}, factor={factor:.2f}")

    # ---------------------------------------------
    # SCALE EMISSIONS
    # ---------------------------------------------
    NO  = emis_mol_km2_hr["NO"]  * factor
    NO2 = emis_mol_km2_hr["NO2"] * factor
    SO2 = emis_mol_km2_hr["SO2"] * factor

    pm25_scaled = pm25 * factor
    pmc_scaled  = pmc * factor

    # ---------------------------------------------
    # GAS INJECTION (VERTICAL SPLIT)
    # ---------------------------------------------
    ds["E_NO"][t, k, j, i]  += NO * 0.7
    ds["E_NO"][t, k2, j, i] += NO * 0.3

    ds["E_NO2"][t, k, j, i]  += NO2 * 0.7
    ds["E_NO2"][t, k2, j, i] += NO2 * 0.3

    ds["E_SO2"][t, k, j, i]  += SO2 * 0.7
    ds["E_SO2"][t, k2, j, i] += SO2 * 0.3

    # ---------------------------------------------
    # PM HANDLING (SAFE VARIABLE DETECTION)
    # ---------------------------------------------
    if "E_PM_25" in ds.variables:
        pm_var = "E_PM_25"
    elif "E_PM_10" in ds.variables:
        pm_var = "E_PM_10"
    else:
        pm_var = None

    if pm_var:
        ds[pm_var][t, k, j, i]  += pm25_scaled / area
        ds[pm_var][t, k2, j, i] += pm25_scaled / area

    # ---------------------------------------------
    # SAVE OUTPUT FILE
    # ---------------------------------------------
    base = os.path.basename(f)
    out_file = os.path.join(out_dir, base + "_pp")

    ds.to_netcdf(out_file)
    ds.close()

    print("Saved:", out_file)

print("\nDONE ✔ AEMO-based time-varying emissions applied successfully")

