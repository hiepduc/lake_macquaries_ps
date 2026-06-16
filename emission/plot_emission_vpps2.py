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

# Rename first column if needed
df.rename(columns={df.columns[0]: "Time"}, inplace=True)

# Convert time column
df["Time"] = pd.to_datetime(df["Time"], dayfirst=True)

# Set index
df.set_index("Time", inplace=True)

# ==========================================================
# COLUMN LISTS
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
# PLOT 1: NOx comparison
# ==========================================================
fig1 = plt.figure(figsize=(16,6))

for col in nox_cols:
    plt.plot(df.index, df[col], label=col, linewidth=0.8)

plt.title("Hourly NOx Emission Comparison")
plt.ylabel("NOx (mg/m3)")
plt.xlabel("Date")
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.savefig("NOx_comparison.png", dpi=300)

# ==========================================================
# PLOT 2: SO2 comparison
# ==========================================================
fig2 = plt.figure(figsize=(16,6))

for col in so2_cols:
    plt.plot(df.index, df[col], label=col, linewidth=0.8)

plt.title("Hourly SO2 Emission Comparison")
plt.ylabel("SO2 (mg/m3)")
plt.xlabel("Date")
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.savefig("SO2_comparison.png", dpi=300)

# ==========================================================
# DAILY AVERAGE
# ==========================================================
daily = df.resample("D").mean()

# ==========================================================
# PLOT 3: Daily averaged NOx
# ==========================================================
fig3 = plt.figure(figsize=(16,6))

for col in nox_cols:
    plt.plot(daily.index, daily[col], label=col)

plt.title("Daily Mean NOx Emissions")
plt.ylabel("NOx (mg/m3)")
plt.xlabel("Date")
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.savefig("Daily_NOx.png", dpi=300)

# ==========================================================
# PLOT 4: Boxplot comparison
# ==========================================================
fig4 = plt.figure(figsize=(10,6))

df[nox_cols].boxplot()

plt.ylabel("NOx (mg/m3)")
plt.title("NOx Distribution by Stack")

plt.tight_layout()
plt.savefig("NOx_boxplot.png", dpi=300)

# ==========================================================
# SUMMARY STATISTICS
# ==========================================================
summary = df.describe()

print(summary)

summary.to_csv("Emission_summary_statistics.csv")

print("Finished plotting.")

# ==========================================================
# SHOW ALL FIGURES ON SCREEN
# ==========================================================
plt.show()

