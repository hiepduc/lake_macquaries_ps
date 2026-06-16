from netCDF4 import Dataset
import numpy as np

nc = Dataset("wrfchemi_d01_outwps2.nc")
v = nc.variables["E_NO"][:]

print("nonzero:", np.count_nonzero(v))
print("max:", np.max(v))

surf = v[0, 1, :, :]
print("nonzero surface:", np.count_nonzero(surf))

import matplotlib.pyplot as plt

plt.imshow(surf, origin="lower")
plt.colorbar()
plt.title("E_NO surface hour 0")
plt.show()

