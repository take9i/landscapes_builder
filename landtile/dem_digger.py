#%%
import os
import sys
import math
import numpy as np
import scipy as sp
import skimage.draw as skid
from shapely.geometry import MultiPolygon
from shapely.ops import cascaded_union
from landtile import tile as ltile
from landtile import road
from landtile import building
from landtile.dem import Dem


def crop_dem(src_path, tz, tx, ty, dst_path):
    proj_str = ltile.get_meter_proj(tz, tx, ty)
    iw, ih = [int(math.ceil(v)) for v in ltile.get_meter_size(tz, tx, ty)]
    os.system(f"gdalwarp -t_srs '{proj_str}' -te -100 -100 {iw+100} {ih+100} -tr 1 1 -r bilinear {src_path} {dst_path}")

def get_extent(vs):
    x0, y0 = vs.min(axis=0)[:2]
    x1, y1 = vs.max(axis=0)[:2]
    ixmin, ixmax = math.floor(x0), math.ceil(x1)
    iymin, iymax = math.floor(y0), math.ceil(y1)
    return ixmin, ixmax, iymin, iymax

def get_slope_points(polygon, dem):
    ring = polygon.exterior
    coords = ring.coords[:] + [ring.interpolate(i).coords[0]
                            for i in np.arange(0, ring.length, 4)]
    points = [(c[0], c[1], dem.get_alt(c)) for c in coords]
    return np.array(points)

def build_xyzs(points, polygon):
    ixmin, ixmax, iymin, iymax = get_extent(points)
    X, Y = np.meshgrid(np.arange(ixmin, ixmax + 1),
                       np.arange(iymin, iymax + 1))
    Z = sp.interpolate.griddata(points[:, 0:2], points[:, 2], (X, Y))
    img = np.zeros((iymax + 1, ixmax + 1))
    img[Y, X] = Z

    vs = np.array(polygon.exterior.coords)
    R, C = skid.polygon(vs[:, 1], vs[:, 0])
    return np.vstack([C, R, img[R, C]]).T

def build_road_xyzs(center_line, width, dem):
    def get_points(segments, alts):
        coords = [s.exterior.coords[:4] for s in segments]
        f = lambda c, a: (c[0], c[1], a)
        faces = [(f(l1, a1), f(r1, a1), f(r2, a2), f(l2, a2))
                for (l1, r1, r2, l2), (a1, a2) in zip(coords, alts)]
        return np.array(faces).reshape((-1, 3))

    segments = road.build_segments(center_line, width)
    alts = road.get_segment_alts(segments, center_line, dem)
    points = get_points(segments, alts)
    poly = cascaded_union(MultiPolygon(segments))
    xyzs = build_xyzs(get_points(segments, alts), poly)

    slope_poly = center_line.buffer(width).simplify(
        0.5, preserve_topology=False)
    slope_points = get_slope_points(slope_poly, dem)
    xyzs = build_xyzs(np.vstack([xyzs, slope_points]), slope_poly)
    return xyzs

def build_building_xyzs(shape, floor, dem):
    alt = building.get_alt(shape, floor, dem)
    coords = shape.exterior.coords
    points = np.hstack([np.array(coords), np.full((len(coords), 1), alt)])
    xyzs = build_xyzs(points, shape)

    slope_poly = shape.buffer(2).simplify(0.5, preserve_topology=False)
    slope_points = get_slope_points(slope_poly, dem)
    xyzs = build_xyzs(np.vstack([xyzs, slope_points]), slope_poly)
    return xyzs

# --

def dig(dem_vrt, tz, tx, ty, road_df, bldg_df):
    os.system(f'rm -f ~~dem_a.tif')
    crop_dem(dem_vrt, tz, tx, ty, '~~dem_a.tif')

    dem = Dem('~~dem_a.tif')
    for key, row in road_df.iterrows():
        try:
            width = road.get_width(row.rnkWidth, row.Width)
            xyzs = build_road_xyzs(row.geometry, width, dem)
            dem.dig(xyzs)
        except:
            print(sys.exc_info(), key)

    for key, row in bldg_df.iterrows():
        try:
            xyzs = build_building_xyzs(row.geometry, row.floor, dem)
            dem.dig(xyzs)
        except:
            print(sys.exc_info(), key)

    return dem

def undig(dem_vrt, tz, tx, ty):
    os.system(f'rm -f ~~dem_a.tif')
    crop_dem(dem_vrt, tz, tx, ty, '~~dem_a.tif')
    return Dem('~~dem_a.tif')

#%%
if __name__ == '__main__':
    Z, X, Y = 15, 29079, 12944
    dem = dig('xxx_dem.vrt', Z, X, Y)
    dem.save(f'{Z}_{X}_{Y}_dem.tif')
