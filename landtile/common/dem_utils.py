# get altitude
from osgeo import gdal
import numpy as np
from scipy import interpolate

def get_get_alt(dem_name):
    driver = gdal.GetDriverByName('GTiff')
    dataset = gdal.Open(dem_name)
    band = dataset.GetRasterBand(1)
    data = band.ReadAsArray(0, 0, dataset.RasterXSize, dataset.RasterYSize)
    transform = dataset.GetGeoTransform()

    def get_alt(p):
        x = (p[0] - transform[0]) / transform[1]
        y = (transform[3] - p[1] ) / -transform[5]
        ix, iy = int(x), int(y)
        if 0 <= y < dataset.RasterYSize-1 and 0 <= x < dataset.RasterXSize-1:
            f = interpolate.interp2d([ix,ix+1],[iy,iy+1],[[data[iy][ix],data[iy][ix+1]],[data[iy+1][ix],data[iy+1][ix+1]]])
            return f(x, y)[0]
        else:
            return 0

    return get_alt
