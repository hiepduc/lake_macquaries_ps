#!/usr/bin/env python3

import xarray as xr
import numpy as np
import matplotlib.pyplot as plt


# ==================================================
# Input
# ==================================================

f = "PM25_EPA_AELMO_202307.nc"

ds = xr.open_dataset(f)


pm25 = ds["PM25"]

lat = ds["LAT"]
lon = ds["LON"]


# ==================================================
# Helper
# ==================================================

def nearest_cell(lat, lon, target_lat, target_lon):

    lat = np.asarray(lat)
    lon = np.asarray(lon)

    dist = (
        (lat-target_lat)**2 +
        (lon-target_lon)**2
    )

    idx = np.argmin(dist)

    return np.unravel_index(
        idx,
        dist.shape
    )

# ==================================================
# Power stations
# ==================================================

sites = {

"Eraring": (-33.06,151.49),
"ValesPoint":(-33.13,151.55)

}


for name,(la,lo) in sites.items():

    i,j = nearest_cell(
        lat,
        lon,
        la,
        lo
    )

    print(
        name,
        "cell:",
        i,j,
        "lat/lon:",
        float(lat[i,j]),
        float(lon[i,j])
    )


# ==================================================
# Monthly mean PM2.5
# ==================================================

pmmean = pm25.mean("TSTEP")


plt.figure(figsize=(10,8))


plt.pcolormesh(
    lon,
    lat,
    pmmean,
    shading="auto"
)


for name,(la,lo) in sites.items():

    plt.plot(
        lo,
        la,
        "o",
        label=name
    )


plt.colorbar(
    label="PM2.5 ug m-3"
)

plt.legend()

plt.title(
    "July 2023 Mean PM2.5"
)


plt.savefig(
    "AELMO_PM25_mean.png",
    dpi=300
)

plt.show()
plt.close()



# ==================================================
# Maximum PM2.5 plume
# ==================================================

pmmax = pm25.max("TSTEP")


plt.figure(figsize=(10,8))


plt.pcolormesh(
    lon,
    lat,
    pmmax,
    shading="auto"
)


for name,(la,lo) in sites.items():

    plt.plot(
        lo,
        la,
        "o",
        label=name
    )


plt.colorbar(
    label="PM2.5 ug m-3"
)

plt.legend()

plt.title(
    "Maximum hourly PM2.5"
)


plt.savefig(
    "AELMO_PM25_max.png",
    dpi=300
)

plt.show()
plt.close()



# ==================================================
# Diurnal cycle
# ==================================================

diurnal = (
    pm25
#    .isel(LAY=0)
    .mean(dim=["ROW","COL"])
)

plt.figure(figsize=(8,4))


plt.plot(
    np.arange(len(diurnal)),
    diurnal
)


plt.xlabel("Hour")
plt.ylabel("PM2.5 ug m-3")

plt.title(
    "Domain mean PM2.5 diurnal"
)

plt.grid()


plt.savefig(
    "AELMO_PM25_diurnal.png",
    dpi=300
)

plt.show()

plt.close()



# ==================================================
# Power station time series
# ==================================================

for name,(la,lo) in sites.items():

    i,j = nearest_cell(
        lat,
        lon,
        la,
        lo
    )


    #ts = pm25[:,0,i,j]
    ts = pm25[:,i,j]


    plt.figure(figsize=(9,4))


    plt.plot(
        np.arange(len(ts)),
        ts,
        marker="o"
    )


    plt.xlabel("Hour")
    plt.ylabel("PM2.5 ug m-3")

    plt.title(
        f"{name} PM2.5"
    )


    plt.grid()

    plt.savefig(
        f"{name}_PM25_timeseries.png",
        dpi=300
    )

    plt.show()
    plt.close()



# ==================================================
# Composition
# ==================================================

species = {

"SO4":"PM25_SO4",
"NO3":"PM25_NO3",
"NH4":"PM25_NH4",
"OC":"PM25_OC",
"OA":"PM25_OA",
"EC":"PM25_EC",
"SOIL":"PM25_SOIL",
"Na":"PM25_NA",
"Cl":"PM25_CL",
"OTHER":"PM25_OTHER"

}


print("\nPM2.5 composition\n")


values=[]


for name,var in species.items():

    v=float(ds[var].mean())

    values.append(v)

    print(
        f"{name:8s}",
        f"{v:8.3f}",
        f"{100*v/float(pm25.mean()):6.1f}%"
    )


plt.figure(figsize=(9,5))


plt.bar(
    list(species.keys()),
    values
)


plt.ylabel(
    "ug m-3"
)

plt.title(
    "EPA/AELMO PM2.5 composition"
)


plt.xticks(rotation=45)


plt.tight_layout()

plt.savefig(
    "AELMO_PM25_composition.png",
    dpi=300
)

plt.show()
plt.close()



# ==================================================
# Sulphate fraction
# ==================================================

so4_frac = (
    ds["PM25_SO4"].mean()
    /
    ds["PM25"].mean()
    *100
)


print(
    "\nSulphate fraction =",
    float(so4_frac),
    "%"
)



print("\nFinished")

