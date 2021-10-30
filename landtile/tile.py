# zxy tile utility
import math
from pyproj import Proj, Transformer

def lonlat2tilenum(zoom, lon_deg, lat_deg):
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.log(math.tan(lat_rad) + (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n)
    return (xtile, ytile)

# gmaps zxy to lonlat (at left-top corner)
def num2lonlat(zoom, xtile, ytile):
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return (lon_deg, lat_deg)

def get_bounds(tz, tx, ty):
    w, n = num2lonlat(tz, tx, ty)
    e, s = num2lonlat(tz, tx + 1, ty + 1)
    return w, s, e, n

def get_children_tiles(tz, tx, ty, at_tz):
    tiles = [(tz, tx, ty)]
    for z in range(tz + 1, at_tz + 1):
        tiles = [(z, i, j) for _, x, y in tiles for i in [x*2, x*2+1] for j in [y*2, y*2+1]]
    return tiles

# ---

# meshcode to latlon (at bottom-left corner)
def meshcode2latlon(mc):
    lat = (int(mc[0:2]) / 1.5 * 3600 + int(mc[4:5]) * 5 * 60) / 3600
    lng = ((int(mc[2:4]) + 100) * 3600 + int(mc[5:6]) * 7.5 * 60) / 3600
    return lat, lng

# get meshcode bounds
def get_meshcode_bounds(meshcode):
    assert(len(meshcode) == 6)

    def get_next(meshcode):
        get_next = lambda v1, v2: (v1 + v2 // 8, v2 % 8)
        x1, y1 = int(meshcode[0:2]), int(meshcode[2:4])
        x2, y2 = int(meshcode[4]), int(meshcode[5])
        nx1, nx2 = get_next(x1, x2 + 1)
        ny1, ny2 = get_next(y1, y2 + 1)
        return "%02d%02d%01d%01d" % (nx1, ny1, nx2, ny2)

    s, w = meshcode2latlon(meshcode)
    n, e = meshcode2latlon(get_next(meshcode))
    return w, s, e, n

# ---

def get_meter_proj(tz, tx, ty):
    west, south, _, _ = get_bounds(tz, tx, ty)
    return f'+proj=tmerc +lat_0={south} +lon_0={west} +k=1.000000 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs'

def get_meter_size(tz, tx, ty):
    west, south, east, north = get_bounds(tz, tx, ty)
    t = Transformer.from_crs('epsg:4612', get_meter_proj(tz, tx, ty), always_xy=True)
    return t.transform(east, north)

# below functions are from mesh.py
#
# def get_to_latlon(z, x, y):
#     west, south, _, _ = tu.get_tile_bounds(z, x, y)
#     cesium_proj = f"+proj=tmerc +lat_0={south} +lon_0={west} +k=1.000000 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs"
#     return partial(pyproj.transform, pyproj.Proj(cesium_proj), pyproj.Proj(init='epsg:4612'))

# def get_width_height(z, x, y):
#     to_cesium = get_to_cesium(z, x, y)
#     west, south, east, north = tu.get_tile_bounds(z, x, y)
#     wx, sy = to_cesium(west, south)
#     ex, ny = to_cesium(east, north)
#     return ex - wx, ny - sy
