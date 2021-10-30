from osgeo import gdal
import numpy as np
from scipy import interpolate

class Dem:
    def __init__(self, path):
        self.dataset = gdal.Open(path)
        self.data = self.dataset.GetRasterBand(1).ReadAsArray(
            0, 0, self.dataset.RasterXSize, self.dataset.RasterYSize)

    def get_alt(self, p):
        transform = self.dataset.GetGeoTransform()
        x = (p[0] - transform[0]) / transform[1]
        y = (p[1] - transform[3]) / transform[5]
        ix, iy = int(x), int(y)
        if (0 <= y < self.dataset.RasterYSize - 1 and
                0 <= x < self.dataset.RasterXSize - 1):
            X, Y = [ix, ix+1], [iy, iy+1]
            Z = [[self.data[iy, ix], self.data[iy, ix+1]],
                 [self.data[iy+1, ix], self.data[iy+1, ix+1]]]
            return interpolate.interp2d(X, Y, Z)(x, y)[0]
        else:
            return 0

    def dig(self, xyzs):
        transform = self.dataset.GetGeoTransform()
        X = ((xyzs[:, 0] - transform[0]) / transform[1]).astype(np.int)
        Y = ((xyzs[:, 1] - transform[3]) / transform[5]).astype(np.int)
        self.data[Y, X] = xyzs[:, 2]

    def save(self, path):
        dst = gdal.GetDriverByName('GTiff').CreateCopy(path, self.dataset, 0)
        dst.GetRasterBand(1).WriteArray(self.data)
        dst.GetRasterBand(1).FlushCache()
