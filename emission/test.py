#!/usr/bin/env python3

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


vpps = pd.read_csv(
    "VPPS_hourly_emission_rates.csv"
)

print(
    vpps["TOTAL_NOx_gs"].isna().sum()
)
