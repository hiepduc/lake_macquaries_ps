#!/usr/bin/env python3

import xarray as xr
import numpy as np
import matplotlib.pyplot as plt


# ==================================================
# Input
# ==================================================

f = "PM25_EPA_AELMO_SHIPPING_2023.nc"

ds = xr.open_dataset(f)


# remove LAY if present
if "LAY" in ds.dims:
    ds = ds.isel(LAY=0)

pm25 = ds["PM25"]
so4 = ds["SO4"]
no3 = ds["NO3"]

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
    "Vales Point":(-33.13,151.55),
    "Lidcombe":(-33.89,151.05)
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

#vmax = np.nanmax(np.abs(pmmean))
vmax = 0.5

plt.pcolormesh(
    lon,
    lat,
    pmmean,
    shading="auto",
    vmin=-vmax,
    vmax=vmax,
    cmap="RdBu_r"
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
plt.title("Shipping Contribution to PM2.5 annual 2023")

plt.savefig(
    "AELMO_PM25_Diff_mean_v3_annual.png",
    dpi=300
)

plt.show()
plt.close()

# ==================================================
# Mean SO4
# ==================================================

so4mean = so4.mean("TSTEP")


plt.figure(figsize=(10,8))

#vmax = np.nanmax(np.abs(pmmean))
vmax = 0.05

plt.pcolormesh(
    lon,
    lat,
    so4mean,
    shading="auto",
    vmin=-vmax,
    vmax=vmax,
    cmap="RdBu_r"
)

for name,(la,lo) in sites.items():

    plt.plot(
        lo,
        la,
        "o",
        label=name
    )


plt.colorbar(label="SO4 ug m-3")
plt.legend()
plt.title("Shipping Contribution to SO4 annual 2023")

plt.savefig(
    "AELMO_SO4_Diff_mean_v3_annual.png",
    dpi=300
)

plt.show()
plt.close()

# ==================================================
# Mean NO3
# ==================================================

no3mean = no3.mean("TSTEP")


plt.figure(figsize=(10,8))

#vmax = np.nanmax(np.abs(pmmean))
vmax = 0.08

plt.pcolormesh(
    lon,
    lat,
    no3mean,
    shading="auto",
    vmin=-vmax,
    vmax=vmax,
    cmap="RdBu_r"
)

for name,(la,lo) in sites.items():

    plt.plot(
        lo,
        la,
        "o",
        label=name
    )


plt.colorbar(label="NO3 ug m-3")
plt.legend()
plt.title("SHIPPING Contribution to NO3 annual 2023")

plt.savefig(
    "AELMO_NO3_Diff_mean_v3_annual.png",
    dpi=300
)

plt.show()
plt.close()

# ==================================================
# Maximum plume
# ==================================================

pmmax = pm25.max("TSTEP")


plt.figure(figsize=(10,8))

vmax = np.nanmax(np.abs(pmmax))

plt.pcolormesh(
    lon,
    lat,
    pmmax,
    shading="auto",
    vmin=-vmax,
    vmax=vmax,
    cmap="RdBu_r"
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
plt.title("Maximum Shipping PM2.5 Contribution (annual)")


plt.savefig(
    "AELMO_PM25_Diff_max_v3_annual.png",
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
plt.title("Domain Diff mean PM2.5 (annual)  diurnal")

plt.grid()

plt.savefig(
    "AELMO_PM25_Diff_diurnal_v3_annual.png",
    dpi=300
)

plt.show()
plt.close()

import pandas as pd

times = pd.date_range(
    start="2023-01-01 00:00",
    periods=len(pm25),
    freq="H"
)

# ==================================================
# Power station time series
# ==================================================
import matplotlib.dates as mdates

for name,(la,lo) in sites.items():

    i,j = nearest_cell(
        lat,
        lon,
        la,
        lo
    )

    ts = pm25[:,i,j]

    plt.figure(figsize=(12,4))

    plt.plot(
        times,
        ts,
        marker="o",
        markersize=2
    )

    ax = plt.gca()

    ax.xaxis.set_major_formatter(
        mdates.DateFormatter("%d-%b")
    )

    ax.xaxis.set_major_locator(
        mdates.DayLocator(interval=2)
    )

    plt.xlabel("Date")
    plt.ylabel("PM2.5 (ug m-3)")

    plt.title(
        f"{name} PM2.5"
    )

    plt.grid()

    plt.gcf().autofmt_xdate()

    plt.savefig(
        f"{name}_PM25_timeseries_v3_annual.png",
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

    pm_ts = pm25[:,i,j]

    so4_ts = ds["SO4"][:,i,j].values

    plt.figure(figsize=(10,4))

    plt.plot(
        times,
        #np.arange(len(pm_ts)),
        pm_ts,
        label="PM2.5",
        linewidth=2
    )

    plt.plot(
        times,
        #np.arange(len(so4_ts)),
        so4_ts,
        label="SO4",
        linewidth=2
    )

    plt.xlabel("Date")
    #plt.xlabel("Hour")
    plt.ylabel("ug m-3")

    plt.title(
        f"{name} PM2.5 and Sulphate"
    )

    plt.legend()
    plt.grid()

    plt.savefig(
        f"{name}_PM25_SO4_timeseries_annual.png",
        dpi=300
    )

    plt.show()
    plt.close()

    ######################################
    # Another plot of PM2.5, SO4 but second axis 
    # Scale for SO4
    # #####################################

    plt.figure(figsize=(10,4))

    ax1 = plt.gca()

    ax1.plot(
        times,
        #np.arange(len(pm_ts)),
        pm_ts,
        label="PM2.5"
    )

    ax1.set_ylabel("PM2.5 (ug m-3)")

    ax2 = ax1.twinx()

    ax2.plot(
        times,
        #np.arange(len(so4_ts)),
        so4_ts,
        #label="SO4"
        "--"
    )

    ax2.set_ylabel("SO4 (ug m-3)")

    plt.title(
        f"{name} PM2.5 and Sulphate"
    )

    plt.grid()

    plt.savefig(
        f"{name}_PM25_SO4_timeseries_annual.png",
        dpi=300
    )

    plt.show()
    plt.close()

    # ###################
    # Plot similar but with labels
    #####################

    plt.figure(figsize=(10,4))

    ax1 = plt.gca()

    line1 = ax1.plot(
        times,
        #np.arange(len(pm_ts)),
        pm_ts,
        label="PM2.5"
    )[0]

    ax1.set_ylabel("PM2.5 (ug m-3)")
    #ax1.set_xlabel("Hour")
    ax1.set_xlabel("Date")

    ax2 = ax1.twinx()

    line2 = ax2.plot(
        times,
        #np.arange(len(so4_ts)),
        so4_ts,
        "--",
        label="SO4"
    )[0]

    ax2.set_ylabel("SO4 (ug m-3)")

    plt.title(
        f"{name} PM2.5 and Sulphate"
    )

    # Combine legends from both axes
    lines = [line1, line2]
    labels = [l.get_label() for l in lines]

    ax1.legend(
        lines,
        labels,
        loc="upper right"
    )

    ax1.grid(True)

    plt.tight_layout()

    plt.savefig(
        f"{name}_PM25_SO4_timeseries_annual.png",
        dpi=300
    )

    plt.show()
    plt.close()

#########################################################################
# SSSo4 fraction time series is not meaningful for differences, so no plot
# ########################################################################

# ==================================================
# EPA / AELMO composition
# ==================================================

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

print("\nPower Station PM2.5 Contribution\n")

comp = []

for name,var in species.items():

    if var in ds:

        v = float(ds[var].mean())

        comp.append(
            (name, v)
        )

# ------------------------------------------
# Sort by absolute contribution
# ------------------------------------------

comp.sort(
    key=lambda x: abs(x[1]),
    reverse=True
)

print(
    f"{'Species':10s} "
    f"{'Mean Contribution (ug/m3)':>25s}"
)

print("-"*40)

for name,v in comp:

    print(
        f"{name:10s} "
        f"{v:25.4f}"
    )

# ------------------------------------------
# Bar plot
# ------------------------------------------

labels = [x[0] for x in comp]
values = [x[1] for x in comp]

plt.figure(figsize=(10,5))

plt.bar(
    labels,
    values
)

plt.axhline(
    0,
    color="k",
    linewidth=1
)

plt.xticks(rotation=45)

plt.ylabel(
    "Shipping Contribution (ug m-3)"
)

plt.title(
    "Shipping Contribution to PM2.5 Components"
)

plt.tight_layout()

plt.savefig(
    "AELMO_PM25_composition_v3_annual.png",
    dpi=300
)

plt.show()
plt.close()

# ==================================================
# sulphate fraction
# ==================================================

so4_mean = float(ds["SO4"].mean())

positive_total = sum(
    max(float(ds[var].mean()), 0.0)
    for var in species.values()
    if var in ds
)

so4_pct = (
    100.0 * max(so4_mean, 0.0)
    / positive_total
)

print(
    f"\nSulphate contribution = "
    f"{so4_pct:.1f}% of positive PM2.5 contribution"
)


print("\nFinished")


###################################
# Benefit of closing power stations
###################################
components = [
    "SO4",
    "NO3",
    "NH4",
    "OA",
    "SOA",
    "POA",
    "EC",
    "OTHER"
]

pm25_benefit = float(ds["PM25"].mean())

print(
    "\nComponent contribution to PM2.5 reduction\n"
)

for sp in components:

    if sp in ds:

        v = float(ds[sp].mean())

        pct = 100.0 * v / pm25_benefit

        print(
            f"{sp:8s}"
            f"{v:10.4f}"
            f"{pct:10.1f}%"
        )

