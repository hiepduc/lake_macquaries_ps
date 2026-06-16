import numpy as np
import matplotlib.pyplot as plt
from netCDF4 import Dataset

nc = Dataset("wrfchemi_d01_outwps2.nc")

v = nc.variables["E_NO"]

data = v[0, 0, :, :]

print("min:", np.min(data))
print("max:", np.max(data))
print("nonzero cells:", np.count_nonzero(data))

plt.figure()
plt.imshow(data, origin="lower")
plt.colorbar()
plt.title("Surface NO emissions (hour 0)")
plt.show()

