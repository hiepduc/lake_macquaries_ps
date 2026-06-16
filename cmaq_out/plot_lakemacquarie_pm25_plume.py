import xarray as xr
import numpy as np
import matplotlib.pyplot as plt

# -------------------------------------------------------
# LOAD FILE (d02 PM2.5 OUTPUT)
# -------------------------------------------------------
ncfile = "PM25_202307.nc"
ds = xr.open_dataset(ncfile)

pm25 = ds["PM25"]     # (T, ROW, COL)
lat = ds["LAT"]       # (ROW, COL)
lon = ds["LON"]       # (ROW, COL)

# -------------------------------------------------------
# LAKE MACQUARIE DOMAIN MASK (d02 coordinates)
# -------------------------------------------------------
lat_min, lat_max = -33.35, -32.95
lon_min, lon_max = 151.30, 151.80

mask = (
    (lat >= lat_min) &
    (lat <= lat_max) &
    (lon >= lon_min) &
    (lon <= lon_max)
)

# -------------------------------------------------------
# TIME-AVERAGED PM2.5 (first day example)
# -------------------------------------------------------
pm25_mean = pm25[:24].mean(axis=0)   # (ROW, COL)

pm25_masked = np.where(mask, pm25_mean, np.nan)

# -------------------------------------------------------
# PLOT (TRUE d02 GRID)
# -------------------------------------------------------
plt.figure(figsize=(8,7))

plt.pcolormesh(
    lon,
    lat,
    pm25_masked,
    shading="auto",
    cmap="magma"
)

plt.colorbar(label="PM2.5 (µg/m³)")

plt.title("PM2.5 Plume over Lake Macquarie (d02)")
plt.xlabel("Longitude")
plt.ylabel("Latitude")

# Power station markers
eraring = (151.508, -33.085)
vales   = (151.580, -33.177)

plt.scatter(eraring[0], eraring[1], c="cyan", edgecolor="black", s=80, label="Eraring PS")
plt.scatter(vales[0], vales[1], c="lime", edgecolor="black", s=80, label="Vales Point PS")

plt.legend()
plt.tight_layout()
plt.show()

