#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import xarray as xr
import numpy as np

# ==========================================================
# INPUT FILE
# ==========================================================
excel_file = "noxso2flowrate.xlsx"

# ==========================================================
# POWER STATION INFO
# ==========================================================
LAT = -33.161
LON = 151.541

STACK_HEIGHT = 178.0
STACK_DIAMETER = 10.3
EXIT_VELOCITY = 26.0
EXIT_TEMPERATURE = 369.0

# ==========================================================
# READ DATA
# ==========================================================
df = pd.read_excel(excel_file, engine="openpyxl")

df.rename(columns={df.columns[0]: "Time"}, inplace=True)
df["Time"] = pd.to_datetime(df["Time"], dayfirst=True)
df.set_index("Time", inplace=True)

# ==========================================================
# COLUMN DEFINITIONS
# ==========================================================
stack_map = {
    "5A": "U5 DUCT A Flow (m3/s)",
    "5B": "U5 DUCT B Flow (m3/s)",
    "6A": "U6 DUCT C Flow (m3/s)",
    "6B": "U6 DUCT D Flow (m3/s)"
}

mw_map = {
    "5A": "Unit 5 Load (MW)",
    "5B": "Unit 5 Load (MW)",
    "6A": "Unit 6 Load (MW)",
    "6B": "Unit 6 Load (MW)"
}

MW_THRESHOLD = 10.0
SHORT_GAP = 3

# ==========================================================
# DATA SUMMARY
# ==========================================================
print("\nInput columns:\n")
print(df.columns.tolist())

print(
    "\nUnit 5 load <10 MW:",
    (df["Unit 5 Load (MW)"] < 10).sum()
)

print(
    "Unit 6 load <10 MW:",
    (df["Unit 6 Load (MW)"] < 10).sum()
)

print(
    "Missing Unit 5 load:",
    df["Unit 5 Load (MW)"].isna().sum()
)

print(
    "Missing Unit 6 load:",
    df["Unit 6 Load (MW)"].isna().sum()
)

# ==========================================================
# SHORT GAP FILLING ONLY
# ==========================================================
print("\nFilling short gaps only...\n")

all_input_cols = list(stack_map.values()) + [
    "5A NOx (mg/m3)",
    "5B NOx (mg/m3)",
    "6A NOx (mg/m3)",
    "6B NOx (mg/m3)",
    "5A SO2 (mg/m3)",
    "5B SO2 (mg/m3)",
    "6A SO2 (mg/m3)",
    "6B SO2 (mg/m3)"
]

for col in all_input_cols:

    if col not in df.columns:
        continue

    n_before = df[col].isna().sum()

    df[col] = df[col].interpolate(
        method="time",
        limit=SHORT_GAP,
        limit_direction="both"
    )

    n_after = df[col].isna().sum()

    print(
        f"{col}: "
        f"{n_before} -> {n_after} missing"
    )

# ==========================================================
# OPERATING MASK
# ==========================================================
operating_mask = pd.DataFrame(index=df.index)

for stack, mw_col in mw_map.items():

    if mw_col not in df.columns:
        raise ValueError(
            f"Missing MW column: {mw_col}"
        )

    mw = df[mw_col]

    operating_mask[stack] = (
        (mw > MW_THRESHOLD) &
        mw.notna()
    )

# ==========================================================
# EMISSION CALCULATION
# ==========================================================
mw = df[mw_col]

on_mask = mw > MW_THRESHOLD

off_mask = (mw <= MW_THRESHOLD) | mw.isna()

df[f"NOx_{stack}_gs"] = np.nan
df[f"SO2_{stack}_gs"] = np.nan

df.loc[off_mask, f"NOx_{stack}_gs"] = 0.0
df.loc[off_mask, f"SO2_{stack}_gs"] = 0.0

df.loc[on_mask, f"NOx_{stack}_gs"] = nox_raw.loc[on_mask]
df.loc[on_mask, f"SO2_{stack}_gs"] = so2_raw.loc[on_mask]

for stack, flow_col in stack_map.items():

    nox_col = f"{stack} NOx (mg/m3)"
    so2_col = f"{stack} SO2 (mg/m3)"

    nox_gm3 = df[nox_col] / 1000.0
    so2_gm3 = df[so2_col] / 1000.0

    flow = df[flow_col]

    mask = operating_mask[stack]

    nox_raw = nox_gm3 * flow
    so2_raw = so2_gm3 * flow

    mw = df[mw_col]

    on_mask = mw > MW_THRESHOLD

    off_mask = (mw <= MW_THRESHOLD) | mw.isna()

    df[f"NOx_{stack}_gs"] = np.nan
    df[f"SO2_{stack}_gs"] = np.nan

    df.loc[off_mask, f"NOx_{stack}_gs"] = 0.0
    df.loc[off_mask, f"SO2_{stack}_gs"] = 0.0

    df.loc[on_mask, f"NOx_{stack}_gs"] = nox_raw.loc[on_mask]
    df.loc[on_mask, f"SO2_{stack}_gs"] = so2_raw.loc[on_mask]

    df[f"NOx_{stack}_gs"] = np.nan
    df[f"SO2_{stack}_gs"] = np.nan

    # Unit OFF
#   df.loc[
#       ~mask,
#       f"NOx_{stack}_gs"
#   ] = 0.0

#   df.loc[
#       ~mask,
#       f"SO2_{stack}_gs"
#   ] = 0.0

    # Unit ON
#   df.loc[
#       mask,
#       f"NOx_{stack}_gs"
#   ] = nox_raw.loc[mask]

#   df.loc[
#       mask,
#       f"SO2_{stack}_gs"
#   ] = so2_raw.loc[mask]

#   missing_mw_mask = mw.isna()

# ==========================================================
# TOTAL EMISSIONS
# ==========================================================
df["TOTAL_NOx_gs"] = df[
    [
        "NOx_5A_gs",
        "NOx_5B_gs",
        "NOx_6A_gs",
        "NOx_6B_gs"
    ]
].sum(axis=1, min_count=1)

df["TOTAL_SO2_gs"] = df[
    [
        "SO2_5A_gs",
        "SO2_5B_gs",
        "SO2_6A_gs",
        "SO2_6B_gs"
    ]
].sum(axis=1, min_count=1)

# ==========================================================
# QA SUMMARY
# ==========================================================
print("\nEmission completeness:\n")

for var in [
    "NOx_5A_gs",
    "NOx_5B_gs",
    "NOx_6A_gs",
    "NOx_6B_gs",
    "SO2_5A_gs",
    "SO2_5B_gs",
    "SO2_6A_gs",
    "SO2_6B_gs"
]:
    pct_missing = (
        100.0 *
        df[var].isna().sum() /
        len(df)
    )

    print(
        f"{var}: "
        f"{pct_missing:.1f}% missing"
    )

print(
    "\nTOTAL_NOx_gs missing:",
    df["TOTAL_NOx_gs"].isna().sum()
)

print(
    "TOTAL_SO2_gs missing:",
    df["TOTAL_SO2_gs"].isna().sum()
)


# ==========================================================
# DEBUG CHECK (IMPORTANT)
# ==========================================================
for stack, mw_col in mw_map.items():
    if mw_col in df.columns:
        print(f"\n{stack}")
        print("MW min:", df[mw_col].min())
        print("MW max:", df[mw_col].max())
        print("MW < 10 hours:", (df[mw_col] < MW_THRESHOLD).sum())

# ==========================================================
# PLOTS
# ==========================================================
plt.figure(figsize=(16,6))

for stack in stack_map:
    plt.plot(df.index, df[f"NOx_{stack}_gs"], label=f"{stack} NOx", linewidth=0.8)

plt.plot(df.index, df["TOTAL_NOx_gs"], label="TOTAL NOx", linewidth=2)
plt.title("Hourly NOx Emission Rate (Correct ON/OFF)")
plt.ylabel("g/s")
plt.xlabel("Time")
plt.legend()
plt.grid()
plt.tight_layout()
plt.savefig("NOx_emission_rate.png", dpi=300)

plt.figure(figsize=(16,6))

for stack in stack_map:
    plt.plot(df.index, df[f"SO2_{stack}_gs"], label=f"{stack} SO2", linewidth=0.8)

plt.plot(df.index, df["TOTAL_SO2_gs"], label="TOTAL SO2", linewidth=2)
plt.title("Hourly SO2 Emission Rate (Correct ON/OFF)")
plt.ylabel("g/s")
plt.xlabel("Time")
plt.legend()
plt.grid()
plt.tight_layout()
plt.savefig("SO2_emission_rate.png", dpi=300)

# ==========================================================
# SAVE CSV (THIS WILL NOW CHANGE)
# ==========================================================
csv_out = "VPPS_hourly_emission_rates.csv"
df.to_csv(csv_out)

# ==========================================================
# NETCDF OUTPUT
# ==========================================================
nt = len(df)

ds = xr.Dataset(coords={"Time": df.index.values})

ds["lat"] = ("Time", np.full(nt, LAT))
ds["lon"] = ("Time", np.full(nt, LON))

ds["stack_height"] = STACK_HEIGHT
ds["stack_diameter"] = STACK_DIAMETER
ds["exit_velocity"] = EXIT_VELOCITY
ds["exit_temperature"] = EXIT_TEMPERATURE

vars_to_save = [
    "NOx_5A_gs", "NOx_5B_gs", "NOx_6A_gs", "NOx_6B_gs",
    "SO2_5A_gs", "SO2_5B_gs", "SO2_6A_gs", "SO2_6B_gs",
    "TOTAL_NOx_gs", "TOTAL_SO2_gs"
]

for var in vars_to_save:
    ds[var] = ("Time", df[var].values)
    ds[var].attrs["units"] = "g s-1"

ds.attrs["title"] = "VPPS emissions (correct MW-based ON/OFF)"
ds.attrs["power_station"] = "Vales Point Power Station"
ds.attrs["latitude"] = LAT
ds.attrs["longitude"] = LON

nc_out = "VPPS_hourly_emissions.nc"
ds.to_netcdf(nc_out)

# ==========================================================
# OUTPUT
# ==========================================================
print("\nFinished.")
print(f"CSV: {csv_out}")
print(f"NetCDF: {nc_out}")

plt.show()


