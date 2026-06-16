import xarray as xr
import numpy as np
import matplotlib.pyplot as plt

# =========================
# USER INPUT
# =========================
orig_file = "../wrfchemi_d01_2023-12-06_00:00:00"
new_file  = "wrfchemi_powerplant/wrfchemi_d01_2023-12-06_00:00:00_pp"

species_list = ["E_NO", "E_NO2", "E_SO2"]

# =========================
# LOAD DATA
# =========================
print("Loading files...")

orig = xr.open_dataset(orig_file, engine="netcdf4")
new  = xr.open_dataset(new_file, engine="netcdf4")

t = 0

# =========================
# DETECT INJECTION LOCATION
# =========================
print("\nDetecting emission signal...")

diff_total = 0

for sp in species_list:
    diff_total += (new[sp][t].values - orig[sp][t].values)

surface_map = np.sum(diff_total, axis=0)

j, i = np.unravel_index(np.argmax(surface_map), surface_map.shape)

print(f"Detected injection grid cell: i={i}, j={j}")

# =========================
# VERTICAL PROFILE CHECK
# =========================
print("\nVertical profile check:")

for sp in species_list:
    diff_col = new[sp][t, :, j, i].values - orig[sp][t, :, j, i].values
    print(f"\n{sp}:")
    print(diff_col)

# =========================
# MASS CONSERVATION CHECK
# =========================
print("\nMass conservation check:")

for sp in species_list:
    total_added = np.sum(new[sp][t].values - orig[sp][t].values)
    print(f"{sp}: total added = {total_added:.6e}")

# =========================
# SPATIAL VERIFICATION (FIXED)
# =========================
print("\nSpatial verification:")

for sp in species_list:
    diff_field = new[sp][t, 0, :, :].values - orig[sp][t, 0, :, :].values

    # SAFE numpy conversion (fixes your crash)
    diff_np = np.array(diff_field)

    max_loc = np.unravel_index(np.argmax(diff_np), diff_np.shape)

    print(f"{sp} max at (j,i): {max_loc}")

# =========================
# PLOT SURFACE DIFFERENCE
# =========================
print("\nPlotting surface emission difference...")

plt.figure(figsize=(7, 6))

plt.imshow(surface_map, origin="lower")
plt.colorbar(label="Emission difference")

plt.scatter(i, j, color="red", label="Detected source")

plt.title("WRF-Chem Emission QC (Surface Difference)")
plt.legend()

plt.tight_layout()
plt.savefig("wrfchemi_QC_map.png", dpi=200)
plt.show()

# =========================
# SUMMARY REPORT
# =========================
print("\n=========================")
print("QC SUMMARY REPORT")
print("=========================")

print(f"Detected source location: i={i}, j={j}")

for sp in species_list:
    diff = new[sp] - orig[sp]
    total = np.sum(diff.values)
    print(f"{sp}: total added = {total:.6e}")

print("\nQC complete ✔")

