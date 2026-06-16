#!/usr/bin/env python3

import xarray as xr
import numpy as np
import matplotlib.pyplot as plt

# --------------------------------------------------
# Input file
# --------------------------------------------------

f = "PM25_202307.nc"

ds = xr.open_dataset(f)

pm25 = ds["PM25"]
lat = ds["LAT"]
lon = ds["LON"]

# --------------------------------------------------
# Monthly mean
# --------------------------------------------------

pm25_mean = pm25.mean(dim="TSTEP")

plt.figure(figsize=(10,8))

plt.pcolormesh(
    lon,
    lat,
    pm25_mean,
    shading="auto"
)

plt.colorbar(label="PM2.5 (ug m-3)")
plt.title("July 2023 Mean PM2.5")

plt.tight_layout()
plt.savefig("PM25_monthly_mean.png", dpi=300)
plt.show()

# --------------------------------------------------
# Maximum hourly PM2.5
# --------------------------------------------------

pm25_max = pm25.max(dim="TSTEP")

plt.figure(figsize=(10,8))

plt.pcolormesh(
    lon,
    lat,
    pm25_max,
    shading="auto"
)

plt.colorbar(label="PM2.5 (ug m-3)")
plt.title("July 2023 Maximum Hourly PM2.5")

plt.tight_layout()
plt.savefig("PM25_max_hourly.png", dpi=300)
plt.show()

# --------------------------------------------------
# Domain-average diurnal cycle
# --------------------------------------------------

diurnal = pm25.mean(dim=["ROW","COL"])

plt.figure(figsize=(8,4))

plt.plot(np.arange(24), diurnal)

plt.xlabel("Hour")
plt.ylabel("PM2.5 (ug m-3)")
plt.title("Domain Mean Diurnal PM2.5")

plt.grid()

plt.tight_layout()
plt.savefig("PM25_diurnal.png", dpi=300)
plt.show()

# --------------------------------------------------
# PM2.5 composition
# --------------------------------------------------

species = [
    "SO4",
    "NO3",
    "NH4",
    "EC",
    "POA",
    "SOA"
]

means = []

for s in species:
    means.append(
        float(ds[s].mean())
    )

plt.figure(figsize=(8,5))

plt.bar(species, means)

plt.ylabel("Mean concentration (ug m-3)")
plt.title("July 2023 PM2.5 Composition")

plt.tight_layout()
plt.savefig("PM25_composition.png", dpi=300)
plt.show()

# --------------------------------------------------
# Summary statistics
# --------------------------------------------------

print("\nPM2.5 Statistics\n")

print("Mean:",
      float(pm25.mean()))

print("Max:",
      float(pm25.max()))

print("95th percentile:",
      float(pm25.quantile(0.95)))

print("99th percentile:",
      float(pm25.quantile(0.99)))

print("\nComposition:")

for s,m in zip(species,means):

    print(
        f"{s:5s} {m:8.3f} ug m-3 "
        f"({100*m/float(pm25.mean()):5.1f}%)"
    )

