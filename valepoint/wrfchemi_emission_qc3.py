import xarray as xr
import numpy as np
import matplotlib.pyplot as plt

# =========================
# INPUT FILES
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
# 1. COMPUTE FULL 3D DIFFERENCE
# =========================
print("\nComputing emission differences...")

diff_3d = {}

for sp in species_list:
    diff_3d[sp] = (new[sp][t].values - orig[sp][t].values)

# =========================
# 2. FIND SOURCE (CORRECT METHOD)
# =========================
print("\nDetecting emission source...")

# vertically integrated signal
combined_2d = np.zeros(diff_3d[species_list[0]].shape[1:])

for sp in species_list:
    combined_2d += np.sum(diff_3d[sp], axis=0)

j, i = np.unravel_index(np.argmax(combined_2d), combined_2d.shape)

print(f"Detected injection grid cell: i={i}, j={j}")

# =========================
# 3. VERTICAL PROFILE CHECK
# =========================
print("\nVertical profile check:")

for sp in species_list:
    profile = diff_3d[sp][:, j, i]
    print(f"\n{sp}:")
    print(profile)

# =========================
# 4. MASS CONSERVATION CHECK
# =========================
print("\nMass conservation check:")

for sp in species_list:
    total_added = np.sum(diff_3d[sp])
    print(f"{sp}: total added = {total_added:.6e}")

# =========================
# 5. SPATIAL VERIFICATION (FIXED)
# =========================
print("\nSpatial verification (2D integrated):")

for sp in species_list:

    field_2d = np.sum(diff_3d[sp], axis=0)

    max_loc = np.unravel_index(np.argmax(field_2d), field_2d.shape)

    print(f"{sp} max at (j,i): {max_loc}")

# =========================
# 6. PLOT DIAGNOSTIC MAP
# =========================
print("\nGenerating QC plot...")

plt.figure(figsize=(7,6))

plt.imshow(combined_2d, origin="lower")
plt.colorbar(label="Vertically integrated emission difference")

plt.scatter(i, j, color="red", label="Detected source")

plt.title("WRF-Chem Emission Audit Map")
plt.legend()

plt.tight_layout()
plt.savefig("wrfchemi_emission_audit.png", dpi=200)
plt.show()

# =========================
# 7. PLUME STRUCTURE CHECK
# =========================
print("\nPlume structure summary:")

for sp in species_list:
    vertical_sum = np.sum(diff_3d[sp], axis=(1,2))
    print(f"{sp} vertical distribution:")
    print(vertical_sum)

# =========================
# 8. FINAL REPORT
# =========================
print("\n=========================")
print("WRF-CHEM EMISSION AUDIT REPORT")
print("=========================")

print(f"Detected source location: i={i}, j={j}")

for sp in species_list:
    print(f"{sp}: total added = {np.sum(diff_3d[sp]):.6e}")

print("\nAudit complete ✔")

