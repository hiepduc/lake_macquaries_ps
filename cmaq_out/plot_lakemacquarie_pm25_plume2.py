import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd

# =========================================================
# 1. INPUT FILES
# =========================================================
cmaq_file = "/mnt/scratch_lustre/duch/lake_macquarie_ps/cmaq_out/PM25_202307.nc"
grid_file = "/mnt/scratch_lustre/ar_policy/whe_project/esme_local/cmaq_gmr_2023/run/MCIP/2023-07-02/d02/GRIDCRO2D_160801_3km.nc"

ds = xr.open_dataset(cmaq_file)
grid = xr.open_dataset(grid_file)

pm25 = ds["PM25"]   # (TSTEP, ROW, COL)

#lat = grid["LAT"].isel(LAY=0)
#lon = grid["LON"].isel(LAY=0)
lat = grid["LAT"].isel(TSTEP=0, LAY=0).values
lon = grid["LON"].isel(TSTEP=0, LAY=0).values

# =========================================================
# 2. POWER STATION LOCATIONS
# =========================================================
sites = {
    "Eraring":   (-33.078, 151.513),
    "ValesPoint":(-33.157, 151.562)
}

# =========================================================
# 3. FIND NEAREST GRID CELLS
# =========================================================
def find_nearest(lat2d, lon2d, lat0, lon0):
    dist = (lat2d - lat0)**2 + (lon2d - lon0)**2
    idx = np.unravel_index(np.argmin(dist), dist.shape)
    return idx

idx_er = find_nearest(lat, lon, *sites["Eraring"])
idx_vp = find_nearest(lat, lon, *sites["ValesPoint"])

# =========================================================
# 4. DIURNAL CYCLE EXTRACTION
# =========================================================
er_ts = pm25[:, idx_er[0], idx_er[1]].values
vp_ts = pm25[:, idx_vp[0], idx_vp[1]].values

hours = np.arange(len(er_ts))  # assumes hourly output

df = pd.DataFrame({
    "hour": hours,
    "Eraring": er_ts,
    "ValesPoint": vp_ts
})

diurnal = df.groupby("hour").mean()

# =========================================================
# 5. DIURNAL PLOT
# =========================================================
plt.figure(figsize=(10,5))
plt.plot(diurnal.index, diurnal["Eraring"], label="Eraring")
plt.plot(diurnal.index, diurnal["ValesPoint"], label="Vales Point")
plt.xlabel("Hour")
plt.ylabel("PM2.5 (µg/m³)")
plt.title("Diurnal PM2.5 at Power Station Grid Cells (d02)")
plt.legend()
plt.grid()
plt.show()

# =========================================================
# 6. FULL DOMAIN PLUME (NO ARTIFICIAL CROP)
# =========================================================
t = 12  # choose time step (e.g. midday)

plt.figure(figsize=(10,8))
plt.pcolormesh(lon, lat, pm25[t, :, :], shading="auto")
plt.colorbar(label="PM2.5 (µg/m³)")
plt.scatter([sites["Eraring"][1], sites["ValesPoint"][1]],
            [sites["Eraring"][0], sites["ValesPoint"][0]],
            c="red", s=60, label="Power Stations")

plt.title(f"PM2.5 Plume - Full d02 Domain (Hour {t})")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.legend()
plt.show()

# =========================================================
# 7. ZOOMED LAKE MACQUARIE VIEW (OPTIONAL)
# =========================================================
lat_min, lat_max = -33.35, -32.90
lon_min, lon_max = 151.2, 151.8

mask = (
    (lat >= lat_min) & (lat <= lat_max) &
    (lon >= lon_min) & (lon <= lon_max)
)

pm25_zoom = pm25[t].where(mask)

plt.figure(figsize=(8,6))
plt.pcolormesh(lon, lat, pm25_zoom, shading="auto")
plt.colorbar(label="PM2.5 (µg/m³)")
plt.scatter([sites["Eraring"][1], sites["ValesPoint"][1]],
            [sites["Eraring"][0], sites["ValesPoint"][0]],
            c="red")

plt.title("Lake Macquarie Zoom - PM2.5 (d02)")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
plt.show()

