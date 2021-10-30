#%%
import math
import numpy as np
import scipy as sp
import skimage as ski
from shapely.geometry import MultiPolygon
from shapely.ops import cascaded_union
import road
import building

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
    R, C = ski.draw.polygon(vs[:, 1], vs[:, 0])
    return np.vstack([C, R, img[R, C]]).T

def plot_for_debug(xyzs, poly, slope_poly):
    ixmin, ixmax, iymin, iymax = get_extent(xyzs)
    img = np.zeros((iymax + 1, ixmax + 1))
    img[xyzs[:, 1].astype(np.int), xyzs[:, 0].astype(np.int)] = xyzs[:, 2]

    import matplotlib
    matplotlib.rcParams['figure.figsize'] = 16, 16
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.set_aspect('equal', adjustable='box')
    # im = ax.imshow(Z, origin='lower', extent=[ixmin, ixmax + 1, iymin, iymax + 1])
    im = ax.imshow(img[iymin:, ixmin:], origin='lower', extent=[
                    ixmin - 0.5, ixmax + 0.5, iymin - 0.5, iymax + 0.5])
    fig.colorbar(im)
    ax.plot(*poly.exterior.xy, linewidth=0.5)
    ax.plot(*slope_poly.exterior.xy, linewidth=0.5)
    plt.show()

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
    # plot_for_debug(xyzs, poly, slope_poly)
    return xyzs

def build_building_xyzs(shape, floor, dem):
    alt = building.get_alt(shape, floor, dem)
    coords = shape.exterior.coords
    points = np.hstack([np.array(coords), np.full((len(coords), 1), alt)])
    xyzs = build_xyzs(points, shape)

    slope_poly = shape.buffer(2).simplify(0.5, preserve_topology=False)
    slope_points = get_slope_points(slope_poly, dem)
    xyzs = build_xyzs(np.vstack([xyzs, slope_points]), slope_poly)
    # plot_for_debug(xyzs, shape, slope_poly)
    return xyzs


#%%
import sys
import geopandas as gpd
from dem import Dem
import road
import misc

if __name__ == '__main__':
    # sys.argv = ['foo', '~dem.tif', '15_29105_12903_roads.geojson',
    #             '15_29105_12903_bldgs.geojson', '~ddem.tif']
    if len(sys.argv) != 5:
        sys.exit('usage: src_dem roads_geojson bldgs_geojson dst_dem')

    dem = Dem(sys.argv[1])
    df = gpd.read_file(sys.argv[2]).rename(columns={'geometry': 'geom'})
    for key, row in df.iterrows():
        try:
            width = road.get_width(row.rnkwidth, row.width)
            xyzs = build_road_xyzs(row.geom, width, dem)
            dem.dig(xyzs)
        except ValueError as e:
            print(key, e)

    df = gpd.read_file(sys.argv[3]).rename(columns={'geometry': 'geom'})
    for key, row in df.iterrows():
        try:
            xyzs = build_building_xyzs(row.geom, row.floor, dem)
            dem.dig(xyzs)
        except ValueError as e:
            print(key, e)
        except:
            print(key, 'dig building any error')

    dem.save(sys.argv[4])
