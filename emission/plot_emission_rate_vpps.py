#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt

# ==========================================================
# INPUT EXCEL FILE
# ==========================================================
excel_file = "noxso2flowrate.xlsx"

# ==========================================================
# READ EXCEL
# ==========================================================
df = pd.read_excel(excel_file, engine="openpyxl")

# Rename first column to Time
df.rename(columns={df.columns[0]: "Time"}, inplace=True)

# Convert datetime
df["Time"] = pd.to_datetime(df["Time"], dayfirst=True)

# Set datetime index
df.set_index("Time", inplace=True)

# ==========================================================
# EMISSION COLUMNS
# ==========================================================
nox_cols = [
    "5A NOx (mg/m3)",
    "5B NOx (mg/m3)",
    "6A NOx (mg/m3)",
    "6B NOx (mg/m3)"
]

so2_cols = [
    "5A SO2 (mg/m3)",
    "5B SO2 (mg/m3)",
    "6A SO2 (mg/m3)",
    "6B SO2 (mg/m3)"
]

# ==========================================================
# FLOW RATE COLUMNS
# ==========================================================
stack_map = {
    "5A": "U5 DUCT A Flow (m3/s)",
    "5B": "U5 DUCT B Flow (m3/s)",
    "6A": "U6 DUCT C Flow (m3/s)",
    "6B": "U6 DUCT D Flow (m3/s)"
}

# ==========================================================
# CALCULATE EMISSION RATES (g/s)
# ==========================================================
for stack, flow_col in stack_map.items():

    # Convert concentration mg/m3 -> g/m3
    nox_gm3 = df[f"{stack} NOx (mg/m3)"] / 1000.0
    so2_gm3 = df[f"{stack} SO2 (mg/m3)"] / 1000.0

    # Flow rate
    flow = df[flow_col]

    # Emission rate (g/s)
    df[f"{stack}_NOx_gs"] = nox_gm3 * flow
    df[f"{stack}_SO2_gs"] = so2_gm3 * flow

# ==========================================================
# TOTAL EMISSIONS
# ==========================================================
df["TOTAL_NOx_gs"] = (
    df["5A_NOx_gs"] +
    df["5B_NOx_gs"] +
    df["6A_NOx_gs"] +
    df["6B_NOx_gs"]
)

df["TOTAL_SO2_gs"] = (
    df["5A_SO2_gs"] +
    df["5B_SO2_gs"] +
    df["6A_SO2_gs"] +
    df["6B_SO2_gs"]
)

# ==========================================================
# PLOT NOx EMISSIONS
# ==========================================================
plt.figure(figsize=(16,6))

for stack in stack_map:
    plt.plot(
        df.index,
        df[f"{stack}_NOx_gs"],
        label=f"{stack} NOx",
        linewidth=0.8
    )

plt.plot(
    df.index,
    df["TOTAL_NOx_gs"],
    label="TOTAL NOx",
    linewidth=2
)

plt.title("Hourly NOx Emission Rate")
plt.ylabel("Emission Rate (g/s)")
plt.xlabel("Date")
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.savefig("NOx_emission_rate.png", dpi=300)

# ==========================================================
# PLOT SO2 EMISSIONS
# ==========================================================
plt.figure(figsize=(16,6))

for stack in stack_map:
    plt.plot(
        df.index,
        df[f"{stack}_SO2_gs"],
        label=f"{stack} SO2",
        linewidth=0.8
    )

plt.plot(
    df.index,
    df["TOTAL_SO2_gs"],
    label="TOTAL SO2",
    linewidth=2
)

plt.title("Hourly SO2 Emission Rate")
plt.ylabel("Emission Rate (g/s)")
plt.xlabel("Date")
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.savefig("SO2_emission_rate.png", dpi=300)

# ==========================================================
# DAILY AVERAGES
# ==========================================================
daily = df.resample("D").mean()

# ==========================================================
# DAILY TOTAL NOx
# ==========================================================
plt.figure(figsize=(16,6))

plt.plot(
    daily.index,
    daily["TOTAL_NOx_gs"],
    linewidth=1.5
)

plt.title("Daily Mean Total NOx Emission")
plt.ylabel("g/s")
plt.xlabel("Date")
plt.grid(True)

plt.tight_layout()
plt.savefig("Daily_TOTAL_NOx.png", dpi=300)

# ==========================================================
# SAVE RESULTS
# ==========================================================
df.to_csv("VPPS_hourly_emission_rates.csv")

print("Finished.")
print("Created:")
print("  NOx_emission_rate.png")
print("  SO2_emission_rate.png")
print("  Daily_TOTAL_NOx.png")
print("  VPPS_hourly_emission_rates.csv")

# ==========================================================
# SHOW FIGURES ON SCREEN
# ==========================================================
plt.show()

