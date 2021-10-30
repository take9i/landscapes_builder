#%%
import psycopg2
import geopandas as gpd
from shapely.geometry import Polygon
import common.tile_utils as tu
import misc

def get_df(table, tz, tx, ty):
    MARGIN = 0.001  # about 100m
    w, s, e, n = tu.get_tile_bounds(tz, tx, ty)
    ww, ws, we, wn = w - MARGIN, s - MARGIN, e + MARGIN, n + MARGIN
    sql = f'with tmp as (select st_makeenvelope({ww}, {ws}, {we}, {wn}, 4612) as enve) select {table}.* from {table} join tmp on st_intersects(geom, tmp.enve);'
    conn = psycopg2.connect(database='gsi', user='')
    df = gpd.GeoDataFrame.from_postgis(sql, conn)
    proj = misc.get_cesium_proj_str(tz, tx, ty)
    return df[df.geom.is_valid].to_crs(proj)

def get_floor(blda, a29, r):
    def get_mid_floor(r):
        g = r.geom
        m = a29[a29.geom.intersects(g.centroid)]
        if m.empty:
            a29_004, a29_006, a29_007 = 0, 1, 40  # 用途地域の指定が無い場所
        else:
            a29_004, a29_006, a29_007 = m[['a29_004', 'a29_006', 'a29_007']].values[0]
        area = g.area
        ar_area = g.buffer(5).area
        isect_area = sum(blda.geom.intersection(g.buffer(5)).area)
        if a29_004 <= 2 or area < 50:
            return 2
        elif area < 100:
            return 5
        else:
            ratio = (isect_area - area) / (ar_area - area)
            kempei = (min(ratio, 0.5) + 0.5) * a29_006
            return min(int(round(a29_007 / kempei)), 16)

    if r['type'] == '高層建物':
        return 20
    elif r['type'] == '堅ろう建物':
        return get_mid_floor(r)
    elif r.geom.area < 20:
        return 1
    else:
        return 2

def crop_df(blda, tz, tx, ty):
    w, h = misc.get_cesium_tile_size(tz, tx, ty)
    rect = Polygon([(0, 0), (w, 0), (w, h), (0, h)])
    return blda[blda.geom.centroid.intersects(rect)]


#%%
import sys
import functools as ft

if __name__ == '__main__':
    # sys.argv = ['foo', 15, 29080, 12945, 'blda.geojson']
    if len(sys.argv) != 5:
        sys.exit('usage: tz tx ty dst_geojson')

    tz, tx, ty = [int(v) for v in sys.argv[1:4]]
    blda = get_df('blda', tz, tx, ty)
    blda = blda[(blda.geom.type == 'Polygon')]
    a29 = get_df('a29', tz, tx, ty)
    getter = ft.partial(get_floor, blda, a29)
    blda['floor'] = blda.apply(getter, axis=1)
    blda['height'] = 0
    crop_df(blda, tz, tx, ty).to_file(sys.argv[4], driver='GeoJSON')
