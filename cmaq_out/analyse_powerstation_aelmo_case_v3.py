#!/usr/bin/env python3

import xarray as xr
import numpy as np
import matplotlib.pyplot as plt


# ==================================================
# Input
# ==================================================

f = "PM25_EPA_AELMO_202307.nc"

ds = xr.open_dataset(f)


# remove LAY if present
if "LAY" in ds.dims:
    ds = ds.isel(LAY=0)

pm25 = ds["PM25"]

lat = ds["LAT"].values
lon = ds["LON"].values


# ==================================================
# helper
# ==================================================

def nearest_cell(lat, lon, target_lat, target_lon):

    dist = (
        (lat - target_lat)**2 +
        (lon - target_lon)**2
    )

    idx = np.unravel_index(
        np.nanargmin(dist),
        dist.shape
    )

    return idx


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
        i,j,
        float(lat[i,j]),
        float(lon[i,j])
    )


# ==================================================
# Mean PM25
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


plt.colorbar(label="PM2.5 ug m-3")
plt.legend()
plt.title("July 2023 Mean PM2.5")

plt.savefig(
    "AELMO_PM25_mean_v3.png",
    dpi=300
)

plt.show()
plt.close()



# ==================================================
# Maximum plume
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


plt.colorbar(label="PM2.5 ug m-3")
plt.legend()
plt.title("Maximum hourly PM2.5")


plt.savefig(
    "AELMO_PM25_max_v3.png",
    dpi=300
)

plt.show()
plt.close()



# ==================================================
# Diurnal cycle (96 hours -> 24 hour)
# ==================================================

nt = pm25.shape[0]

hours = np.arange(nt) % 24


diurnal = []

for h in range(24):

    diurnal.append(
        pm25.isel(
            TSTEP=np.where(hours==h)[0]
        ).mean()
    )


diurnal = np.array(diurnal)



plt.figure(figsize=(8,4))

plt.plot(
    np.arange(24),
    diurnal,
    marker="o"
)


plt.xlabel("Hour")
plt.ylabel("PM2.5 ug m-3")
plt.title("Domain mean PM2.5 diurnal")

plt.grid()

plt.savefig(
    "AELMO_PM25_diurnal_v3.png",
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


    ts = pm25[:,i,j]


    plt.figure(figsize=(10,4))

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
        f"{name}_PM25_timeseries_v3.png",
        dpi=300
    )

    plt.show()
    plt.close()



# ==================================================
# EPA / AELMO composition
# ==================================================

#species = {
#
#"SO4":"PM25_SO4",
#"NO3":"PM25_NO3",
#"NH4":"PM25_NH4",
#"OA":"PM25_OA",
#"OC":"PM25_OC",
#"EC":"PM25_EC",
#"SOIL":"PM25_SOIL",
#"Na":"PM25_NA",
#"Cl":"PM25_CL",
#"K":"PM25_K",
#"Ca":"PM25_CA",
#"Mg":"PM25_MG",
#"OTHER":"PM25_OTHER"

#}

species = {

"SO4":"SO4",
"NO3":"NO3",
"NH4":"NH4",
"EC":"EC",
"OA":"OA",
"POA":"POA",
"SOA":"SOA",
"SOIL":"SOIL",
"NA":"NA",
"CL":"CL",
"K":"K",
"MG":"MG",
"OTHER":"OTHER"

}


print("\nEPA/AELMO PM2.5 composition\n")


values=[]


pmmean_all = float(pm25.mean())


for name,var in species.items():

    if var in ds:

        v=float(ds[var].mean())

        values.append(v)

        print(
            f"{name:8s} {v:8.3f} "
            f"{100*v/pmmean_all:6.1f}%"
        )



plt.figure(figsize=(10,5))


plt.bar(
    list(species.keys())[:len(values)],
    values
)


plt.xticks(rotation=45)
plt.ylabel("ug m-3")
plt.title("EPA/AELMO PM2.5 Composition")


plt.tight_layout()

plt.savefig(
    "AELMO_PM25_composition_v3.png",
    dpi=300
)
plt.show()

plt.close()



# ==================================================
# sulphate fraction
# ==================================================

so4frac = (
    #float(ds["PM25_SO4"].mean())
    float(ds["SO4"].mean())
    /
    pmmean_all
    *
    100
)


print(
    "\nSulphate fraction =",
    so4frac,
    "%"
)


print("\nFinished")

