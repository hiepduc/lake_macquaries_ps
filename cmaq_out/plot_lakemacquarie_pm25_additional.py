import xarray as xr
import numpy as np
import matplotlib.pyplot as plt

# -------------------------------------------------------
# USER INPUTS
# -------------------------------------------------------
ncfile = "PM25_202307.nc"

# Approximate coordinates (you can refine if needed)
eraring_latlon = (-33.085, 151.508)
vales_latlon   = (-33.177, 151.580)

# Lake Macquarie bounding box (adjust if needed)
lat_min, lat_max = -33.35, -32.95
lon_min, lon_max = 151.30, 151.80

# -------------------------------------------------------
# LOAD DATA
# -------------------------------------------------------
ds = xr.open_dataset(ncfile)

pm25 = ds["PM25"]   # (T, Y, X)
lat = ds["LAT"]
lon = ds["LON"]

time_dim = pm25.shape[0]

# -------------------------------------------------------
# FIND NEAREST GRID CELLS
# -------------------------------------------------------
def find_nearest(lat2d, lon2d, target_lat, target_lon):
    dist = (lat2d - target_lat)**2 + (lon2d - target_lon)**2
    ij = np.unravel_index(np.argmin(dist.values), dist.shape)
    return ij

er_i, er_j = find_nearest(lat, lon, *eraring_latlon)
va_i, va_j = find_nearest(lat, lon, *vales_latlon)

print("Eraring grid:", er_i, er_j)
print("Vales grid:", va_i, va_j)

# -------------------------------------------------------
# 2. DIURNAL CYCLE EXTRACTION
# -------------------------------------------------------
er_ts = pm25[:, er_i, er_j]
va_ts = pm25[:, va_i, va_j]

hours = np.arange(len(er_ts)) % 24

er_diurnal = np.array([er_ts[hours == h].mean() for h in range(24)])
va_diurnal = np.array([va_ts[hours == h].mean() for h in range(24)])

# -------------------------------------------------------
# PLOT DIURNAL CYCLE
# -------------------------------------------------------
plt.figure(figsize=(8,5))
plt.plot(er_diurnal, label="Eraring PS", marker="o")
plt.plot(va_diurnal, label="Vales Point PS", marker="s")
plt.xticks(range(24))
plt.xlabel("Hour of Day")
plt.ylabel("PM2.5 (µg/m³)")
plt.title("Diurnal PM2.5 at Power Stations")
plt.legend()
plt.grid()
plt.tight_layout()
plt.show()

# -------------------------------------------------------
# 3. PLUME MAP (AVERAGE OVER SELECTED PERIOD)
# -------------------------------------------------------
t_start = 0
t_end = 24   # first day (change as needed)

pm25_mean = pm25[t_start:t_end].mean(axis=0)

mask = (
    (lat >= lat_min) & (lat <= lat_max) &
    (lon >= lon_min) & (lon <= lon_max)
)

pm25_masked = np.where(mask, pm25_mean, np.nan)

plt.figure(figsize=(8,7))
plt.pcolormesh(lon, lat, pm25_masked, shading="auto", cmap="magma")
plt.colorbar(label="PM2.5 (µg/m³)")
plt.scatter(eraring_latlon[1], eraring_latlon[0],
            c="cyan", label="Eraring PS", edgecolor="black")
plt.scatter(vales_latlon[1], vales_latlon[0],
            c="lime", label="Vales Point PS", edgecolor="black")

plt.title("PM2.5 Plume (d02) around Lake Macquarie")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.legend()
plt.tight_layout()
plt.show()

