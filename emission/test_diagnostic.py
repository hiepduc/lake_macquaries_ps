import pandas as pd

df = pd.read_excel("noxso2flowrate.xlsx", engine="openpyxl")

df.rename(columns={df.columns[0]: "Time"}, inplace=True)
df["Time"] = pd.to_datetime(df["Time"], dayfirst=True)

print("\nUnit 5 Load statistics")
print(df["Unit 5 Load (MW)"].describe())

print("\nUnit 6 Load statistics")
print(df["Unit 6 Load (MW)"].describe())

print("\nFirst 20 Unit 5 values")
print(df["Unit 5 Load (MW)"].head(20))

print("\nRows where Unit 5 MW is missing")
print(
    df.loc[
        df["Unit 5 Load (MW)"].isna(),
        ["Time","Unit 5 Load (MW)"]
    ].head(20)
)

mask = df["Unit 5 Load (MW)"].isna()

groups = (mask != mask.shift()).cumsum()

print(
    mask.groupby(groups).sum().max()
)
