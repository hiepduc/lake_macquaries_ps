#!/usr/bin/env python3

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# =====================================================
# INPUT FILES
# =====================================================

vpps_file = "VPPS_hourly_emission_rates.csv"
era_file  = "Eraring_hourly_emissions.csv"

# =====================================================
# READ DATA
# =====================================================

vpps = pd.read_csv(
    vpps_file,
    parse_dates=["Time"]
)

era = pd.read_csv(
    era_file,
    parse_dates=["Time"]
)

# =====================================================
# VPPS TOTAL LOAD
# =====================================================

#vpps["VPPS_MW"] = (
#    vpps["Unit 5 Load (MW)"] +
#    vpps["Unit 6 Load (MW)"]
#)

vpps["VPPS_MW"] = (
    vpps["Unit 5 Load (MW)"].fillna(0) +
    vpps["Unit 6 Load (MW)"].fillna(0)
)

# =====================================================
# ERARING TOTAL LOAD
# =====================================================

#era["ERARING_MW"] = (
#    era["U1LoadMW"] +
#    era["U2LoadMW"] +
#    era["U3LoadMW"] +
#    era["U4LoadMW"]
#)

era["ERARING_MW"] = (
    era["U1LoadMW"].fillna(0) +
    era["U2LoadMW"].fillna(0) +
    era["U3LoadMW"].fillna(0) +
    era["U4LoadMW"].fillna(0)
)

# =====================================================
# MERGE
# =====================================================

df = pd.merge(
    vpps[
        [
            "Time",
            "VPPS_MW",
            "TOTAL_NOx_gs",
            "TOTAL_SO2_gs"
        ]
    ],
    era[
        [
            "Time",
            "ERARING_MW",
            "TOTAL_NOx_gs",
            "TOTAL_SO2_gs"
        ]
    ],
    on="Time",
    suffixes=("_VPPS", "_ERARING")
)

df.set_index("Time", inplace=True)

# =====================================================
# FILL MISSING GENERATION
# =====================================================

df["VPPS_MW"] = df["VPPS_MW"].fillna(0.0)
df["ERARING_MW"] = df["ERARING_MW"].fillna(0.0)
df["TOTAL_NOx_gs_VPPS"] = df["TOTAL_NOx_gs_VPPS"].fillna(0.0)
df["TOTAL_SO2_gs_VPPS"] = df["TOTAL_SO2_gs_VPPS"].fillna(0.0)
df["TOTAL_NOx_gs_ERARING"] = df["TOTAL_NOx_gs_ERARING"].fillna(0.0)
df["TOTAL_SO2_gs_ERARING"] = df["TOTAL_SO2_gs_ERARING"].fillna(0.0)

# =====================================================
# DAILY ENERGY (GWh/day)
# =====================================================

daily_energy = (
    df[["VPPS_MW", "ERARING_MW"]]
    .resample("D")
    .sum()
    / 1000.0
)

daily_energy.columns = [
    "VPPS_GWh",
    "ERARING_GWh"
]

# =====================================================
# DAILY EMISSIONS
# =====================================================

daily = df[["TOTAL_NOx_gs_VPPS", "TOTAL_SO2_gs_VPPS","TOTAL_NOx_gs_ERARING","TOTAL_SO2_gs_ERARING"]].resample("D").sum()
#daily = (
#    df
#    .fillna(0)
#    .resample("D")
#    .mean()
#)

#daily = df.resample("D").mean(min_count=1)

# =====================================================
# DAILY AVAILABILITY
# =====================================================

availability = pd.DataFrame(index=df.index)

availability["VPPS"] = (
    df["VPPS_MW"] > 0
).astype(float)

availability["ERARING"] = (
    df["ERARING_MW"] > 0
).astype(float)

availability_daily = (
    availability
    .resample("D")
    .mean()
    * 100.0
)

# =====================================================
# ANNUAL TOTALS
# =====================================================

VPPS_GWh = df["VPPS_MW"].sum() / 1000.0
ERA_GWh  = df["ERARING_MW"].sum() / 1000.0

VPPS_NOx_t = (
    df["TOTAL_NOx_gs_VPPS"].sum()
    * 3600.0 / 1e6
)

VPPS_SO2_t = (
    df["TOTAL_SO2_gs_VPPS"].sum()
    * 3600.0 / 1e6
)

ERA_NOx_t = (
    df["TOTAL_NOx_gs_ERARING"].sum()
    * 3600.0 / 1e6
)

ERA_SO2_t = (
    df["TOTAL_SO2_gs_ERARING"].sum()
    * 3600.0 / 1e6
)

# =====================================================
# EMISSION FACTORS
# =====================================================

VPPS_NOx_EF = VPPS_NOx_t / VPPS_GWh
VPPS_SO2_EF = VPPS_SO2_t / VPPS_GWh

ERA_NOx_EF = ERA_NOx_t / ERA_GWh
ERA_SO2_EF = ERA_SO2_t / ERA_GWh

# =====================================================
# SUMMARY TABLE
# =====================================================

summary = pd.DataFrame({

    "Station": [
        "Vales Point",
        "Eraring"
    ],

    "Generation_GWh": [
        VPPS_GWh,
        ERA_GWh
    ],

    "NOx_tonnes": [
        VPPS_NOx_t,
        ERA_NOx_t
    ],

    "SO2_tonnes": [
        VPPS_SO2_t,
        ERA_SO2_t
    ],

    "NOx_t_per_GWh": [
        VPPS_NOx_EF,
        ERA_NOx_EF
    ],

    "SO2_t_per_GWh": [
        VPPS_SO2_EF,
        ERA_SO2_EF
    ]
})

print("\n===== SUMMARY =====\n")
print(summary)

summary.to_csv(
    "Powerstation_summary.csv",
    index=False
)

# =====================================================
# HOURLY GENERATION
# =====================================================

plt.figure(figsize=(16,6))

plt.plot(
    df.index,
    df["VPPS_MW"],
    label="Vales Point"
)

plt.plot(
    df.index,
    df["ERARING_MW"],
    label="Eraring"
)

plt.title("Hourly Generation")
plt.ylabel("MW")
plt.xlabel("Date")
plt.grid(True)
plt.legend()

plt.tight_layout()
plt.savefig(
    "Generation_Hourly.png",
    dpi=300
)

# =====================================================
# DAILY ENERGY
# =====================================================

plt.figure(figsize=(16,6))

plt.plot(
    daily_energy.index,
    daily_energy["VPPS_GWh"],
    label="Vales Point"
)

plt.plot(
    daily_energy.index,
    daily_energy["ERARING_GWh"],
    label="Eraring"
)

plt.title("Daily Energy Production")
plt.ylabel("GWh/day")
plt.xlabel("Date")
plt.grid(True)
plt.legend()

plt.tight_layout()
plt.savefig(
    "Daily_Energy_GWh.png",
    dpi=300
)

# =====================================================
# DAILY AVAILABILITY
# =====================================================

plt.figure(figsize=(16,6))

plt.plot(
    availability_daily.index,
    availability_daily["VPPS"],
    label="Vales Point"
)

plt.plot(
    availability_daily.index,
    availability_daily["ERARING"],
    label="Eraring"
)

plt.title("Daily Availability")
plt.ylabel("Availability (%)")
plt.xlabel("Date")

plt.ylim(0,105)

plt.grid(True)
plt.legend()

plt.tight_layout()
plt.savefig(
    "Daily_Availability.png",
    dpi=300
)

# =====================================================
# DAILY NOx
# =====================================================

plt.figure(figsize=(16,6))

plt.plot(
    daily.index,
    daily["TOTAL_NOx_gs_VPPS"],
#    drawstyle="default",
#    marker="o",
#    linewidth=1,
    label="Vales Point"
)

plt.plot(
    daily.index,
    daily["TOTAL_NOx_gs_ERARING"],
#    drawstyle="default",
#    marker="o",
#    linewidth=1,
    label="Eraring"
)

plt.title("Daily Sum NOx Emission")
plt.ylabel("g/s")
plt.xlabel("Date")
plt.grid(True)
plt.legend()

plt.tight_layout()
plt.savefig(
    "NOx_Daily.png",
    dpi=300
)

# =====================================================
# DAILY SO2
# =====================================================

plt.figure(figsize=(16,6))

plt.plot(
    daily.index,
    daily["TOTAL_SO2_gs_VPPS"],
    label="Vales Point"
)

plt.plot(
    daily.index,
    daily["TOTAL_SO2_gs_ERARING"],
    label="Eraring"
)

plt.title("Daily Sum SO2 Emission")
plt.ylabel("g/s")
plt.xlabel("Date")
plt.grid(True)
plt.legend()

plt.tight_layout()
plt.savefig(
    "SO2_Daily.png",
    dpi=300
)

# =====================================================
# HOURLY NOx
# =====================================================

plt.figure(figsize=(16,6))

plt.plot(
    df.index,
    df["TOTAL_NOx_gs_VPPS"],
    label="Vales Point"
)

plt.plot(
    df.index,
    df["TOTAL_NOx_gs_ERARING"],
    label="Eraring"
)

plt.title("Hourly NOx Emission")
plt.ylabel("g/s")
plt.xlabel("Date")
plt.grid(True)
plt.legend()

plt.tight_layout()
plt.savefig(
    "NOx_Hourly.png",
    dpi=300
)

# =====================================================
# HOURLY SO2
# =====================================================

plt.figure(figsize=(16,6))

plt.plot(
    df.index,
    df["TOTAL_SO2_gs_VPPS"],
    label="Vales Point"
)

plt.plot(
    df.index,
    df["TOTAL_SO2_gs_ERARING"],
    label="Eraring"
)

plt.title("Hourly SO2 Emission")
plt.ylabel("g/s")
plt.xlabel("Date")
plt.grid(True)
plt.legend()

plt.tight_layout()
plt.savefig(
    "SO2_Hourly.png",
    dpi=300
)


# =====================================================
# NOx vs MW
# =====================================================

plt.figure(figsize=(8,8))

plt.scatter(
    df["VPPS_MW"],
    df["TOTAL_NOx_gs_VPPS"],
    s=2,
    label="Vales Point"
)

plt.scatter(
    df["ERARING_MW"],
    df["TOTAL_NOx_gs_ERARING"],
    s=2,
    label="Eraring"
)

plt.xlabel("MW")
plt.ylabel("NOx (g/s)")
plt.title("NOx vs Power Output")

plt.grid(True)
plt.legend()

plt.tight_layout()
plt.savefig(
    "NOx_vs_MW.png",
    dpi=300
)

# =====================================================
# SO2 vs MW
# =====================================================

plt.figure(figsize=(8,8))

plt.scatter(
    df["VPPS_MW"],
    df["TOTAL_SO2_gs_VPPS"],
    s=2,
    label="Vales Point"
)

plt.scatter(
    df["ERARING_MW"],
    df["TOTAL_SO2_gs_ERARING"],
    s=2,
    label="Eraring"
)

plt.xlabel("MW")
plt.ylabel("SO2 (g/s)")
plt.title("SO2 vs Power Output")

plt.grid(True)
plt.legend()

plt.tight_layout()
plt.savefig(
    "SO2_vs_MW.png",
    dpi=300
)

# =====================================================
# DAILY SUMMARY CSV
# =====================================================

daily_summary = pd.concat(
    [
        daily_energy,
        availability_daily
    ],
    axis=1
)

daily_summary.columns = [
    "VPPS_GWh",
    "ERARING_GWh",
    "VPPS_Availability_pct",
    "ERARING_Availability_pct"
]

daily_summary.to_csv(
    "Daily_Energy_Availability.csv"
)

# =====================================================
# STATISTICS
# =====================================================

df.describe().to_csv(
    "Comparison_statistics.csv"
)

# =====================================================
# CAPACITY FACTOR
# =====================================================

VPPS_CAPACITY = 1320.0
ERARING_CAPACITY = 2880.0

VPPS_CF = (
    df["VPPS_MW"].mean()
    / VPPS_CAPACITY
    * 100.0
)

ERA_CF = (
    df["ERARING_MW"].mean()
    / ERARING_CAPACITY
    * 100.0
)

print("\n===== CAPACITY FACTOR =====")
print(f"VPPS    : {VPPS_CF:.1f}%")
print(f"Eraring : {ERA_CF:.1f}%")

print("\nCreated:")
print("  Powerstation_summary.csv")
print("  Daily_Energy_Availability.csv")
print("  Comparison_statistics.csv")
print("  Generation_Hourly.png")
print("  Daily_Energy_GWh.png")
print("  Daily_Availability.png")
print("  NOx_Daily.png")
print("  SO2_Daily.png")
print("  NOx_vs_MW.png")
print("  SO2_vs_MW.png")

plt.show()

