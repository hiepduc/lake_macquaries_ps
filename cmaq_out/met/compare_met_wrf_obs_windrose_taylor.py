#!/usr/bin/env python3
import glob
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from netCDF4 import Dataset
from wrf import getvar, ll_to_xy, ALL_TIMES
import pandas as pd
import numpy as np
import skill_metrics as sm

# ==========================================================
# INPUT FILES
# ==========================================================

obs_file = "/mnt/scratch_lustre/duch/lake_macquarie_ps/HiepMetDataAllSites2023.csv"

station_file = "/mnt/scratch_lustre/duch/lake_macquarie_ps/air-quality-monitoring-sites-summary-9-feb-2026.csv"

#wrf_files = [
    # "/mnt/scratch_lustre/duch/runpillaga/jkong/wrfout_d02_2023-12-8to19_wrfnative.nc"
#]

wrf_files = sorted(
    glob.glob("/mnt/scratch_lustre/ar_policy/whe_project/esme_local/wrf_cu_gmr_2023/run/WRF/run/wrfout_d02_2023-10*")
)

UTC_OFFSET = 10

# ==========================================================
# STATIONS TO VALIDATE
# ==========================================================

stations_to_use = [
    "LIVERPOOL",
    "LIDCOMBE",
    "PROSPECT",
    "BRINGELLY",
    "NEWCASTLE",
    "SINGLETON",
    "MUSWELLBROOK",
    "RICHMOND",
    "ST MARYS",
    "BARGO",
    "ROZELLE",
    "RANDWICK",
    "MERRIWA",
    "BERESFIELD",
    "MAYFIELD",
    "ALBION PARK SOUTH",
    "WALLSEND",
    "MORISSET",
    "WYONG",
    "CAMDEN",
    "CAMPBELLTOWN WEST",
    "CAMBERWELL",
    "EARLWOOD",
    "PENRITH",
    "OAKDALE",
    "WOLLONGONG"
]

# ==========================================================
# LOAD OBS DATA
# ==========================================================

obs = pd.read_csv(obs_file)

obs["datetime"] = pd.to_datetime(
    obs["Date_time"],
    dayfirst=True,
    errors="coerce"
)

obs = obs.set_index("datetime")

obs.columns = (
    obs.columns
    .str.upper()
    .str.strip()
)

print("\nObservation file loaded")
print("Rows:", len(obs))

# ==========================================================
# COLUMN MATCHING
# ==========================================================

def find_col(station, var):

    station = station.upper()

    for c in obs.columns:

        if station in c and var in c:
            return c

    return None

# ==========================================================
# STATION COORDS
# ==========================================================

site_df = pd.read_csv(
    station_file,
    encoding="latin1"
)

site_df["STATION"] = (
    site_df["NSW air quality monitoring (AQMN) site"]
    .astype(str)
    .str.upper()
    .str.strip()
)

coord_lookup = {}

for _, r in site_df.iterrows():

    try:

        coord_lookup[r["STATION"]] = (
            float(r["Latitude\n(South)"]),
            float(r["Longitude\n(East)"])
        )

    except:
        pass

print("Stations with coordinates:", len(coord_lookup))

# ==========================================================
# READ WRF ONCE
# ==========================================================

print("\nLoading WRF data...")

nc = [Dataset(f) for f in wrf_files]

#nc = Dataset(wrf_files[0])

t2 = getvar(nc, "T2", timeidx=ALL_TIMES)
q2 = getvar(nc, "Q2", timeidx=ALL_TIMES)
u10 = getvar(nc, "U10", timeidx=ALL_TIMES)
v10 = getvar(nc, "V10", timeidx=ALL_TIMES)
psfc = getvar(nc, "PSFC", timeidx=ALL_TIMES)

times = getvar(nc, "times", timeidx=ALL_TIMES)

wrf_times = pd.to_datetime(
    [str(t.values) for t in times]
) + pd.Timedelta(hours=UTC_OFFSET)

ny = t2.shape[1]
nx = t2.shape[2]

print("WRF dimensions:", ny, nx)
print("WRF timesteps :", len(wrf_times))

# ==========================================================
# EXTRACT WRF AT STATIONS
# ==========================================================

wrf_cache = {}

for station in stations_to_use:

    station = station.upper()

    if station not in coord_lookup:

        print(f"{station}: no coordinates")
        continue

    lat, lon = coord_lookup[station]

    try:

        xy = ll_to_xy(nc, lat, lon)

        ix = int(xy[0])
        iy = int(xy[1])

    except Exception as e:

        print(f"{station}: ll_to_xy failed")
        print(e)
        continue

    if (
        ix < 0 or ix >= nx or
        iy < 0 or iy >= ny
    ):

        print(
            f"{station}: outside WRF domain "
            f"(ix={ix}, iy={iy})"
        )
        continue

    print(
        f"Processing {station} "
        f"(ix={ix}, iy={iy})"
    )

    T2_all = []
    RH_all = []
    WS_all = []
    WD_all = []

    nt = len(wrf_times)

    for t in range(nt):

        temp_c = float(
            t2[t, iy, ix]
        ) - 273.15

        T2_all.append(temp_c)

        u = float(u10[t, iy, ix])
        v = float(v10[t, iy, ix])

        ws = np.sqrt(u*u + v*v)

        wd = (
            270 -
            np.degrees(
                np.arctan2(v, u)
            )
        ) % 360

        WS_all.append(ws)
        WD_all.append(wd)

        es = (
            6.112 *
            np.exp(
                (17.67 * temp_c) /
                (temp_c + 243.5)
            )
        )

        e = (
            float(q2[t, iy, ix]) *
            float(psfc[t, iy, ix]) /
            0.622
        ) / 100.0

        rh = 100.0 * e / es

        rh = max(0, min(100, rh))

        RH_all.append(rh)

    wrf_cache[station] = pd.DataFrame(
        {
            "T_WRF": T2_all,
            "RH_WRF": RH_all,
            "WS_WRF": WS_all,
            "WD_WRF": WD_all
        },
        index=wrf_times
    )

# ==========================================================
# STATS
# ==========================================================

def calc_stats(model, obs):

    mask = (
        np.isfinite(model) &
        np.isfinite(obs)
    )

    model = np.asarray(model)[mask]
    obs = np.asarray(obs)[mask]

    if len(model) < 10:
        return np.nan, np.nan, np.nan

    r = np.corrcoef(
        model,
        obs
    )[0, 1]

    mb = np.mean(model - obs)

    rmse = np.sqrt(
        np.mean(
            (model - obs) ** 2
        )
    )

    return r, mb, rmse

# ==========================================================
# VALIDATION
# ==========================================================

results = []

for station in wrf_cache:

    temp_col = find_col(station, "TEMP")
    rh_col   = find_col(station, "HUMID")
    ws_col   = find_col(station, "WSP")
    wd_col   = find_col(station, "WDR")

    #print(
    #station,
    #    "TEMP =", temp_col,
    #    "RH =", rh_col,
    #    "WS =", ws_col,
    #    "WD =", wd_col
    #)

    if temp_col is None:

        print(
            f"{station}: "
            "temperature column not found"
        )

        continue

    obs_df = pd.DataFrame(
        index=obs.index
    )

    obs_df["T_OBS"] = pd.to_numeric(
        obs[temp_col],
        errors="coerce"
    )

    if rh_col:
        obs_df["RH_OBS"] = pd.to_numeric(
            obs[rh_col],
            errors="coerce"
        )

    if ws_col:
        obs_df["WS_OBS"] = pd.to_numeric(
            obs[ws_col],
            errors="coerce"
        )

    if wd_col:
        obs_df["WD_OBS"] = pd.to_numeric(
            obs[wd_col],
            errors="coerce"
        )

    compare = pd.merge(
        wrf_cache[station],
        obs_df,
        left_index=True,
        right_index=True,
        how="inner"
    )

    if len(compare) < 10:

        print(
            f"{station}: "
            f"only {len(compare)} matched records"
        )

        continue

    rT, mbT, rmseT = calc_stats(
        compare["T_WRF"],
        compare["T_OBS"]
    )

    rW, mbW, rmseW = calc_stats(
        compare["WS_WRF"],
        compare["WS_OBS"]
    )

    rH, mbH, rmseH = calc_stats(
        compare["RH_WRF"],
        compare["RH_OBS"]
    )

    results.append([
        station,
        len(compare),
        rT, mbT, rmseT,
        rW, mbW, rmseW,
        rH, mbH, rmseH
    ])

# ==========================================================
# OUTPUT
# ==========================================================

df = pd.DataFrame(
    results,
    columns=[
        "Station",
        "N",
        "R_T",
        "MB_T",
        "RMSE_T",
        "R_WS",
        "MB_WS",
        "RMSE_WS",
        "R_RH",
        "MB_RH",
        "RMSE_RH"
    ]
)

df = df.sort_values(
    "Station"
)

df.to_csv(
    "WRF_MET_validation.csv",
    index=False
)

print("\nValidation Summary")
print(df)

print(
    "\nSaved: "
    "WRF_MET_validation.csv"
)

from windrose import WindroseAxes

def plot_windrose(obs_wd, obs_ws, wrf_wd, wrf_ws, station):

    fig = plt.figure(figsize=(12, 5))

    # -----------------------------
    # OBS WIND ROSE
    # -----------------------------
    ax1 = WindroseAxes.from_ax(fig=fig, rect=[0.0, 0.1, 0.45, 0.8])
    ax1.bar(obs_wd, obs_ws, bins=np.arange(0, 10, 2), cmap=plt.cm.viridis, alpha=0.7)
    ax1.set_title(f"{station} - OBS")

    # -----------------------------
    # WRF WIND ROSE
    # -----------------------------
    ax2 = WindroseAxes.from_ax(fig=fig, rect=[0.5, 0.1, 0.45, 0.8])
    ax2.bar(wrf_wd, wrf_ws, bins=np.arange(0, 10, 2), cmap=plt.cm.plasma, alpha=0.7)
    ax2.set_title(f"{station} - WRF")

    plt.tight_layout()

    outfile = f"windrose_{station.replace(' ','_')}.png"
    plt.savefig(outfile, dpi=300, bbox_inches="tight")
    plt.show()
    plt.close()

    print("Saved:", outfile)

def plot_taylor_first_quadrant(ref_std, stds, corrs, labels, title, outfile):

    fig = plt.figure(figsize=(8, 6))

    sm.taylor_diagram(
        ref_std,
        stds,
        corrs,
        markerLabel=labels,
        markerLabelColor='black',
        markerLegend='on',
        titleSTD="Std Dev",
        titleCOR="Correlation",
        titleOBS="OBS",
        styleOBS='-',
        colOBS='red',
        markerobs='o'
    )

    ax = plt.gca()

    # -------------------------------------------------
    # FORCE FIRST QUADRANT ONLY
    # -------------------------------------------------
    ax.set_thetamin(0)     # correlation = 1 side
    ax.set_thetamax(90)    # correlation = 0 side

    ax.set_ylim(0, None)

    ax.grid(True)

    plt.title(title)

    plt.tight_layout()
    plt.savefig(outfile, dpi=300)
    plt.close()

    print("Saved:", outfile)

# ==========================
# PANEL PLOT
# Temperature + WS +
# OBS Windrose + WRF Windrose
# ==========================

# ==========================================================
# PANEL PLOT FOR ONE STATION
# ==========================================================

from windrose import WindroseAxes

def plot_station(station):

    temp_col = find_col(station, "TEMP")
    ws_col   = find_col(station, "WSP")
    wd_col   = find_col(station, "WDR")

    if temp_col is None:
        print(f"{station}: no temperature column")
        return

    # --------------------------------------------------
    # OBS DATA
    # --------------------------------------------------

    obs_df = pd.DataFrame(index=obs.index)

    obs_df["T_OBS"] = pd.to_numeric(
        obs[temp_col],
        errors="coerce"
    )

    if ws_col is not None:

        obs_df["WS_OBS"] = pd.to_numeric(
            obs[ws_col],
            errors="coerce"
        )

    if wd_col is not None:

        obs_df["WD_OBS"] = pd.to_numeric(
            obs[wd_col],
            errors="coerce"
        )

    # --------------------------------------------------
    # MERGE OBS + WRF
    # --------------------------------------------------

    compare = pd.merge(
        wrf_cache[station],
        obs_df,
        left_index=True,
        right_index=True,
        how="inner"
    ).sort_index()

    compare = compare.dropna()

    if len(compare) < 10:

        print(f"{station}: insufficient overlap")
        return

    print()
    print("Plotting", station)
    print(compare.columns.tolist())

    # --------------------------------------------------
    # FIGURE
    # --------------------------------------------------

    fig = plt.figure(
        figsize=(16,12)
    )

    # --------------------------------------------------
    # TEMPERATURE
    # --------------------------------------------------

    ax1 = fig.add_subplot(2,2,1)

    ax1.plot(
        compare.index,
        compare["T_OBS"],
        "k",
        linewidth=1.5,
        label="OBS"
    )

    ax1.plot(
        compare.index,
        compare["T_WRF"],
        "r",
        linewidth=1.5,
        label="WRF"
    )

    r_temp = np.corrcoef(
        compare["T_OBS"],
        compare["T_WRF"]
    )[0,1]

    ax1.set_title(
        f"Temperature (°C)\nR={r_temp:.2f}"
    )

    ax1.grid(True)

    ax1.legend()

    # --------------------------------------------------
    # WIND SPEED
    # --------------------------------------------------

    ax2 = fig.add_subplot(2,2,2)

    if (
        "WS_OBS" in compare.columns
        and
        "WS_WRF" in compare.columns
    ):

        ax2.plot(
            compare.index,
            compare["WS_OBS"],
            "k",
            linewidth=1.5,
            label="OBS"
        )

        ax2.plot(
            compare.index,
            compare["WS_WRF"],
            "r",
            linewidth=1.5,
            label="WRF"
        )

        r_ws = np.corrcoef(
            compare["WS_OBS"],
            compare["WS_WRF"]
        )[0,1]

        ax2.set_title(
            f"Wind Speed (m/s)\nR={r_ws:.2f}"
        )

        ax2.legend()

    else:

        ax2.set_title(
            "Wind Speed\nNo Data"
        )

    ax2.grid(True)

    # --------------------------------------------------
    # FORMAT TIME AXES
    # --------------------------------------------------

    ax1.xaxis.set_major_formatter(
        mdates.DateFormatter("%d-%b\n%H:%M")
    )

    ax2.xaxis.set_major_formatter(
        mdates.DateFormatter("%d-%b\n%H:%M")
    )

    for label in ax1.get_xticklabels():
        label.set_rotation(30)

    for label in ax2.get_xticklabels():
        label.set_rotation(30)

    # --------------------------------------------------
    # OBS WINDROSE
    # --------------------------------------------------

    if (
        "WD_OBS" in compare.columns
        and
        "WS_OBS" in compare.columns
    ):

        ax3 = WindroseAxes(
            fig,
            [0.08,0.06,0.32,0.32]
        )

        fig.add_axes(ax3)

        ax3.bar(
            compare["WD_OBS"],
            compare["WS_OBS"],
            normed=True,
            opening=0.8,
            edgecolor="white"
        )

        ax3.set_title(
            "Observed Wind Rose",
            pad=20
        )

        ax3.legend(
            loc="lower left",
            bbox_to_anchor=(-0.2,-0.15)
        )

    # --------------------------------------------------
    # WRF WINDROSE
    # --------------------------------------------------

    if (
        "WD_WRF" in compare.columns
        and
        "WS_WRF" in compare.columns
    ):

        ax4 = WindroseAxes(
            fig,
            [0.58,0.06,0.32,0.32]
        )

        fig.add_axes(ax4)

        ax4.bar(
            compare["WD_WRF"],
            compare["WS_WRF"],
            normed=True,
            opening=0.8,
            edgecolor="white"
        )

        ax4.set_title(
            "WRF Wind Rose",
            pad=20
        )

        ax4.legend(
            loc="lower left",
            bbox_to_anchor=(-0.2,-0.15)
        )

    # --------------------------------------------------
    # TITLE
    # --------------------------------------------------

    fig.suptitle(
        station,
        fontsize=18,
        y=0.97
    )

    # --------------------------------------------------
    # SAVE
    # --------------------------------------------------

    outfile = (
        f"panel_{station.replace(' ','_')}.png"
    )

    plt.savefig(
        outfile,
        dpi=300,
        bbox_inches="tight"
    )

    plt.show()
    plt.close()

    print("Saved:", outfile)


selected_stations = [
    "LIVERPOOL",
    "LIDCOMBE",
    "PROSPECT",
    "CAMDEN",
    "MUSWELLBROOK",
    "NEWCASTLE"
]

for station in selected_stations:

    if station in wrf_cache:

        plot_station(station)

# #######################
# Plot Taylor diagrms
# #######################

import numpy as np
import pandas as pd
import skill_metrics as sm
import matplotlib.pyplot as plt

# ==========================================================
# TAYLOR DIAGRAM INPUT STORAGE
# ==========================================================

compare_dict = {}
stds = []
corrs = []
labels = []

all_obs = []
all_mod = []

# ==========================================================
# BUILD compare_dict (FULL VARIABLES)
# ==========================================================

compare_dict = {}

for station in selected_stations:

    station_u = station.upper()

    if station_u not in wrf_cache:
        print(f"Skipping Taylor: {station} (no WRF data)")
        continue

    # -----------------------------
    # OBS columns
    # -----------------------------
    t_col  = find_col(station_u, "TEMP")
    rh_col = find_col(station_u, "HUMID")
    ws_col = find_col(station_u, "WSP")
    wd_col = find_col(station_u, "WDR")

    if t_col is None:
        print(f"Skipping {station}: no TEMP column")
        continue

    # -----------------------------
    # OBS dataframe
    # -----------------------------
    obs_df = pd.DataFrame(index=obs.index)

    obs_df["T_OBS"] = pd.to_numeric(obs[t_col], errors="coerce")

    if rh_col:
        obs_df["RH_OBS"] = pd.to_numeric(obs[rh_col], errors="coerce")

    if ws_col:
        obs_df["WS_OBS"] = pd.to_numeric(obs[ws_col], errors="coerce")

    if wd_col:
        obs_df["WD_OBS"] = pd.to_numeric(obs[wd_col], errors="coerce")

    # -----------------------------
    # WRF dataframe
    # -----------------------------
    wrf_df = wrf_cache[station_u].copy()

    # -----------------------------
    # ALIGN
    # -----------------------------
    compare = pd.merge(
        wrf_df,
        obs_df,
        left_index=True,
        right_index=True,
        how="inner"
    ).dropna()

    if len(compare) < 10:
        print(f"Skipping {station}: not enough overlap")
        continue

    print("Saving:", station)
    print(compare.columns.tolist())

    compare_dict[station_u] = compare

# ==========================================================
# CHECK
# ==========================================================

if len(compare_dict) == 0:
    raise ValueError("No valid station overlap for Taylor diagram")

# ==========================================================
# TAYLOR DIAGRAM - TEMPERATURE
# ==========================================================

import skill_metrics as sm

stds = []
rmss = []
corrs = []
labels = []

all_obs = []

for station in selected_stations:

    if station not in compare_dict:
        print(f"Skipping Taylor: {station}")
        continue

    df = compare_dict[station]

    obs = df["T_OBS"].values
    mod = df["T_WRF"].values

    mask = np.isfinite(obs) & np.isfinite(mod)

    obs = obs[mask]
    mod = mod[mask]

    if len(obs) < 10:
        continue

    all_obs.extend(obs)

    std_mod = np.std(mod)

    corr = np.corrcoef(mod, obs)[0, 1]

    crmsd = np.sqrt(
        np.mean(
            (
                (mod - np.mean(mod))
                -
                (obs - np.mean(obs))
            )**2
        )
    )

    stds.append(std_mod)
    rmss.append(crmsd)
    corrs.append(corr)
    labels.append(station)

# --------------------------------------------------
# Reference observation
# --------------------------------------------------

ref_std = np.std(all_obs)

print("Reference STD =", ref_std)

# --------------------------------------------------
# Arrays expected by SkillMetrics
# --------------------------------------------------

STDs = np.array([ref_std] + stds)

RMSs = np.array([0.0] + rmss)

CORs = np.array([1.0] + corrs)

marker_labels = ["OBS"] + labels

print("STDs =", STDs)
print("RMSs =", RMSs)
print("CORs =", CORs)

# --------------------------------------------------
# Plot
# --------------------------------------------------

plt.figure(figsize=(8, 8))

sm.taylor_diagram(
    STDs,
    RMSs,
    CORs,
    markerLabel=marker_labels,
    markerLegend='on',
    markerSize=10,
    colOBS='r',
    styleOBS='-',
    titleOBS='OBS',
    checkStats=False
)

plt.title("Taylor Diagram - Temperature")

plt.savefig(
    "taylor_temperature.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()
plt.close()

print("Saved: taylor_temperature.png")

plt.figure(figsize=(10,8))

sm.taylor_diagram(
    STDs,
    RMSs,
    CORs,
    markerLabel=marker_labels,
    markerLegend='on',
    markerSize=10,
    colOBS='r',
    styleOBS='-',
    titleOBS='OBS'
)

plt.title("Taylor Diagram - Temperature")
plt.show()
plt.close()

# =====================================================
# TAYLOR DIAGRAM - RH
# =====================================================

STDs = []
RMSs = []
CORs = []

marker_labels = ['OBS']

all_obs = []

for station in selected_stations:

    if station not in compare_dict:
        continue

    df = compare_dict[station]

    # skip stations without RH
    if "RH_OBS" not in df.columns:
        print(f"{station}: RH_OBS missing")
        continue

    if "RH_WRF" not in df.columns:
        print(f"{station}: RH_WRF missing")
        continue

    obs = df["RH_OBS"].values
    mod = df["RH_WRF"].values

    mask = np.isfinite(obs) & np.isfinite(mod)

    obs = obs[mask]
    mod = mod[mask]

    if len(obs) < 10:
        continue

    all_obs.extend(obs)

# ------------------------------------------
# reference std
# ------------------------------------------

ref_std = np.std(all_obs)

STDs.append(ref_std)
RMSs.append(0.0)
CORs.append(1.0)

# ------------------------------------------
# stations
# ------------------------------------------

for station in selected_stations:

    if station not in compare_dict:
        continue

    df = compare_dict[station]

    if "RH_OBS" not in df.columns:
        continue

    obs = df["RH_OBS"].values
    mod = df["RH_WRF"].values

    mask = np.isfinite(obs) & np.isfinite(mod)

    obs = obs[mask]
    mod = mod[mask]

    if len(obs) < 10:
        continue

    std_model = np.std(mod)

    corr = np.corrcoef(obs, mod)[0,1]

    crmsd = np.sqrt(
        np.mean(
            ((mod - mod.mean()) -
             (obs - obs.mean()))**2
        )
    )

    STDs.append(std_model)
    RMSs.append(crmsd)
    CORs.append(corr)

    marker_labels.append(station)

# ------------------------------------------
# convert to arrays
# ------------------------------------------

STDs = np.array(STDs)
RMSs = np.array(RMSs)
CORs = np.array(CORs)

# safety
CORs = np.clip(CORs, -1, 1)

# ------------------------------------------
# plot
# ------------------------------------------

plt.figure(figsize=(10,8))

sm.taylor_diagram(
    STDs,
    RMSs,
    CORs,
    markerLabel=marker_labels,
    markerLegend='on',
    markerSize=10,
    colOBS='red',
    styleOBS='-'
)

plt.title("Taylor Diagram - Relative Humidity")

plt.savefig(
    "taylor_humidity.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()

plt.close()

print("Saved: taylor_humidity.png")


# ==========================================================
# TAYLOR DIAGRAM - WIND SPEED
# ==========================================================

import skill_metrics as sm

stds = []
rmss = []
corrs = []
labels = []

all_obs = []

for station in selected_stations:

    if station not in compare_dict:
        print(f"Skipping Taylor: {station}")
        continue

    df = compare_dict[station]

    # skip stations without WS
    if "WS_OBS" not in df.columns:
        print(f"{station}: WS_OBS missing")
        continue

    if "WS_WRF" not in df.columns:
        print(f"{station}: WS_WRF missing")
        continue

    obs = df["WS_OBS"].values
    mod = df["WS_WRF"].values

    mask = np.isfinite(obs) & np.isfinite(mod)

    obs = obs[mask]
    mod = mod[mask]

    if len(obs) < 10:
        continue

    all_obs.extend(obs)

    std_mod = np.std(mod)

    corr = np.corrcoef(mod, obs)[0, 1]

    crmsd = np.sqrt(
        np.mean(
            (
                (mod - np.mean(mod))
                -
                (obs - np.mean(obs))
            )**2
        )
    )

    stds.append(std_mod)
    rmss.append(crmsd)
    corrs.append(corr)
    labels.append(station)

# --------------------------------------------------
# Reference observation
# --------------------------------------------------

ref_std = np.std(all_obs)

print("Reference STD =", ref_std)

# --------------------------------------------------
# Arrays expected by SkillMetrics
# --------------------------------------------------

STDs = np.array([ref_std] + stds)

RMSs = np.array([0.0] + rmss)

CORs = np.array([1.0] + corrs)

marker_labels = ["OBS"] + labels

print("STDs =", STDs)
print("RMSs =", RMSs)
print("CORs =", CORs)

# --------------------------------------------------
# Plot
# --------------------------------------------------

plt.figure(figsize=(8, 8))

sm.taylor_diagram(
    STDs,
    RMSs,
    CORs,
    markerLabel=marker_labels,
    markerLegend='on',
    markerSize=10,
    colOBS='r',
    styleOBS='-',
    titleOBS='OBS',
    checkStats=False
)

plt.title("Taylor Diagram - Wind Speed")

plt.savefig(
    "taylor_windspeed.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()
plt.close()

print("Saved: taylor_windspeed.png")

plt.figure(figsize=(10,8))

sm.taylor_diagram(
    STDs,
    RMSs,
    CORs,
    markerLabel=marker_labels,
    markerLegend='on',
    markerSize=10,
    colOBS='r',
    styleOBS='-',
    titleOBS='OBS'
)



