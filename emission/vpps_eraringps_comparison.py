#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt

# =====================================================
# READ FILES
# =====================================================

vpps = pd.read_csv(
    "VPPS_hourly_emission_rates.csv",
    parse_dates=["Time"]
)

era = pd.read_csv(
    "Eraring_hourly_emissions.csv",
    parse_dates=["Time"]
)

# =====================================================
# VPPS TOTAL MW
# =====================================================

vpps["VPPS_MW"] = (
    vpps["Unit 5 Load (MW)"] +
    vpps["Unit 6 Load (MW)"]
)

# =====================================================
# ERARING TOTAL MW
# =====================================================

era["ERARING_MW"] = (
    era["U1LoadMW"] +
    era["U2LoadMW"] +
    era["U3LoadMW"] +
    era["U4LoadMW"]
)

# =====================================================
# MERGE
# =====================================================

df = pd.merge(
    vpps[[
        "Time",
        "VPPS_MW",
        "TOTAL_NOx_gs",
        "TOTAL_SO2_gs"
    ]],

    era[[
        "Time",
        "ERARING_MW",
        "TOTAL_NOx_gs",
        "TOTAL_SO2_gs"
    ]],

    on="Time",
    suffixes=("_VPPS","_ERARING")
)

df = df.set_index("Time")

# =====================================================
# DAILY
# =====================================================

daily = df.resample("D").mean()

# =====================================================
# ANNUAL TOTALS
# =====================================================

VPPS_GWh = df["VPPS_MW"].sum()/1000.0
ERA_GWh  = df["ERARING_MW"].sum()/1000.0

VPPS_NOx_t = (
    df["TOTAL_NOx_gs_VPPS"].sum()
    *3600/1e6
)

VPPS_SO2_t = (
    df["TOTAL_SO2_gs_VPPS"].sum()
    *3600/1e6
)

ERA_NOx_t = (
    df["TOTAL_NOx_gs_ERARING"].sum()
    *3600/1e6
)

ERA_SO2_t = (
    df["TOTAL_SO2_gs_ERARING"].sum()
    *3600/1e6
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

    "Station":[
        "Vales Point",
        "Eraring"
    ],

    "Generation_GWh":[
        VPPS_GWh,
        ERA_GWh
    ],

    "NOx_tonnes":[
        VPPS_NOx_t,
        ERA_NOx_t
    ],

    "SO2_tonnes":[
        VPPS_SO2_t,
        ERA_SO2_t
    ],

    "NOx_t_per_GWh":[
        VPPS_NOx_EF,
        ERA_NOx_EF
    ],

    "SO2_t_per_GWh":[
        VPPS_SO2_EF,
        ERA_SO2_EF
    ]
})

print(summary)

summary.to_csv(
    "Powerstation_summary.csv",
    index=False
)

# =====================================================
# TIME SERIES MW
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
plt.grid()
plt.legend()

plt.tight_layout()
plt.savefig(
    "Generation_Hourly.png",
    dpi=300
)

# =====================================================
# DAILY MW
# =====================================================

plt.figure(figsize=(16,6))

plt.plot(
    daily.index,
    daily["VPPS_MW"],
    label="Vales Point"
)

plt.plot(
    daily.index,
    daily["ERARING_MW"],
    label="Eraring"
)

plt.title("Daily Mean Generation")
plt.ylabel("MW")
plt.grid()
plt.legend()

plt.tight_layout()
plt.savefig(
    "Generation_Daily.png",
    dpi=300
)

# =====================================================
# NOX
# =====================================================

plt.figure(figsize=(16,6))

plt.plot(
    daily.index,
    daily["TOTAL_NOx_gs_VPPS"],
    label="Vales Point"
)

plt.plot(
    daily.index,
    daily["TOTAL_NOx_gs_ERARING"],
    label="Eraring"
)

plt.title("Daily Mean NOx Emissions")
plt.ylabel("g/s")
plt.grid()
plt.legend()

plt.tight_layout()
plt.savefig(
    "NOx_Daily.png",
    dpi=300
)

# =====================================================
# SO2
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

plt.title("Daily Mean SO2 Emissions")
plt.ylabel("g/s")
plt.grid()
plt.legend()

plt.tight_layout()
plt.savefig(
    "SO2_Daily.png",
    dpi=300
)

# =====================================================
# SCATTER NOX vs MW
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
plt.ylabel("NOx g/s")
plt.title("NOx Emission vs Power Output")
plt.grid()
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
plt.title("SO2 Emission vs Power Output")

plt.grid(True)
plt.legend()

plt.tight_layout()

plt.savefig(
    "SO2_vs_MW.png",
    dpi=300
)

# =====================================================
# MONTHLY TOTALS
# =====================================================

monthly = df.resample("M").sum()

monthly["VPPS_NOx_t"] = (
    monthly["TOTAL_NOx_gs_VPPS"]
    *3600/1e6
)

monthly["ERA_NOx_t"] = (
    monthly["TOTAL_NOx_gs_ERARING"]
    *3600/1e6
)

monthly[[
    "VPPS_NOx_t",
    "ERA_NOx_t"
]].to_csv(
    "Monthly_NOx_tonnes.csv"
)

# =====================================================
# STATS
# =====================================================

df.describe().to_csv(
    "Comparison_statistics.csv"
)

print()
print("Created:")
print(" Powerstation_summary.csv")
print(" Comparison_statistics.csv")
print(" Generation_Hourly.png")
print(" Generation_Daily.png")
print(" NOx_Daily.png")
print(" SO2_Daily.png")
print(" NOx_vs_MW.png")
print(" Monthly_NOx_tonnes.csv")

plt.show()

