#!/usr/bin/env python3

import xarray as xr
import numpy as np
import matplotlib.pyplot as plt

# =====================================================
# INPUT
# =====================================================

f = "PM25_202307.nc"

ds = xr.open_dataset(f)

lat = ds["LAT"].values
lon = ds["LON"].values

# =====================================================
# POWER STATION LOCATIONS
# =====================================================

stations = {
    "Vales Point":
        (-33.056, 151.522),

    "Eraring":
        (-33.066, 151.534)
}

# =====================================================
# FIND NEAREST CMAQ CELL
# =====================================================

def nearest_cell(lat2d, lon2d, plat, plon):

    dist = np.sqrt(
        (lat2d - plat)**2 +
        (lon2d - plon)**2
    )

    j, i = np.unravel_index(
        np.argmin(dist),
        dist.shape
    )

    return j, i

# =====================================================
# PRINT CELL LOCATIONS
# =====================================================

print("\nNearest CMAQ cells\n")

cell_index = {}

for name, (plat, plon) in stations.items():

    j, i = nearest_cell(
        lat,
        lon,
        plat,
        plon
    )

    cell_index[name] = (j, i)

    print(
        f"{name:12s}"
        f" ROW={j:3d}"
        f" COL={i:3d}"
        f" LAT={lat[j,i]:.4f}"
        f" LON={lon[j,i]:.4f}"
    )

# =====================================================
# MONTHLY MEAN PM25
# =====================================================

pm25_mean = ds["PM25"].mean("TSTEP")

plt.figure(figsize=(10,8))

pcm = plt.pcolormesh(
    lon,
    lat,
    pm25_mean,
    shading="auto"
)

plt.colorbar(
    pcm,
    label="PM2.5 (ug m-3)"
)

for name,(plat,plon) in stations.items():

    plt.plot(
        plon,
        plat,
        "ro"
    )

    plt.text(
        plon,
        plat,
        name,
        fontsize=9
    )

plt.xlim(151.2,152.0)
plt.ylim(-33.5,-32.7)

plt.title(
    "July 2023 Mean PM2.5\nLake Macquarie"
)

plt.xlabel("Longitude")
plt.ylabel("Latitude")

plt.tight_layout()
plt.savefig(
    "LakeMac_PM25_mean.png",
    dpi=300
)

plt.show()

# =====================================================
# MAXIMUM HOURLY PM25
# =====================================================

pm25_max = ds["PM25"].max("TSTEP")

plt.figure(figsize=(10,8))

pcm = plt.pcolormesh(
    lon,
    lat,
    pm25_max,
    shading="auto"
)

plt.colorbar(
    pcm,
    label="PM2.5 (ug m-3)"
)

for name,(plat,plon) in stations.items():

    plt.plot(
        plon,
        plat,
        "ro"
    )

plt.xlim(151.2,152.0)
plt.ylim(-33.5,-32.7)

plt.title(
    "Maximum Hourly PM2.5\nLake Macquarie"
)

plt.tight_layout()
plt.savefig(
    "LakeMac_PM25_max.png",
    dpi=300
)

plt.show()

# =====================================================
# DIURNAL PM25
# =====================================================

plt.figure(figsize=(8,5))

for name,(j,i) in cell_index.items():

    ts = ds["PM25"][:,j,i]

    plt.plot(
        np.arange(24),
        ts,
        marker="o",
        label=name
    )

plt.xlabel("Hour")
plt.ylabel("PM2.5 (ug m-3)")
plt.title("PM2.5 Diurnal Cycle")
plt.grid()
plt.legend()

plt.tight_layout()
plt.savefig(
    "PM25_diurnal_PS.png",
    dpi=300
)

plt.show()

# =====================================================
# PM COMPONENTS
# =====================================================

species = [
    "SO4",
    "NO3",
    "NH4",
    "EC",
    "POA",
    "SOA"
]

for station,(j,i) in cell_index.items():

    plt.figure(figsize=(10,5))

    for sp in species:

        plt.plot(
            np.arange(24),
            ds[sp][:,j,i],
            marker="o",
            label=sp
        )

    plt.xlabel("Hour")
    plt.ylabel("ug m-3")

    plt.title(
        f"{station} PM2.5 Components"
    )

    plt.grid()
    plt.legend(ncol=2)

    plt.tight_layout()

    plt.savefig(
        station.replace(" ","_")
        + "_components.png",
        dpi=300
    )

plt.show()

print("\nFinished")

