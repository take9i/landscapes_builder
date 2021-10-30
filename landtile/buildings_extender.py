#%%
import geopandas as gpd
from shapely.geometry import Polygon
from landtile import tile as ltile

MARGIN = 0.001  # about 100m


def extend(shape_gpkg, tz, tx, ty):
    def get_floor(r):
        if r['type'] == '高層建物':
            return 20
        elif r['type'] == '堅ろう建物':
            return 5
        elif r.geometry.area < 20:
            return 1
        else:
            return 2

    w, s, e, n = ltile.get_bounds(tz, tx, ty)
    bbox = (w - MARGIN, s - MARGIN, e + MARGIN, n + MARGIN)
    proj = ltile.get_meter_proj(tz, tx, ty)
    df = gpd.read_file(shape_gpkg, layer='BldA', bbox=bbox).to_crs(proj)
    df = df[df.geom_type == 'Polygon']
    df['floor'] = df.apply(get_floor, axis=1)
    df['height'] = 0

    w, h = ltile.get_meter_size(tz, tx, ty)
    rect = Polygon([(0, 0), (w, 0), (w, h), (0, h)])
    return df[df.geometry.centroid.intersects(rect)]

#%%
if __name__ == '__main__':
    Z, X, Y = 15, 29079, 12944
    df = extend('~xxx_shape.gpkg', Z, X, Y)
    df.to_file(f'{Z}_{X}_{Y}_bldgs.geojson', driver='GeoJSON')

