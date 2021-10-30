# misc utilities
import os

def commit_shapes_on_db(files, db, table):
    os.system(f"psql -d {db} -c 'drop table {table};'")
    os.system(f"shp2pgsql -W cp932 -I -s 4612 -p -S {files[0]} {table} | gsed -e 's/varchar([0-9]\+)/varchar(64)/' | psql -d {db}")
    for file in files:
        os.system(f'shp2pgsql -a -W cp932 -s 4612 -S {file} {table} | psql -d {db}')

import psycopg2
import geopandas as gpd
from . import tile_utils as tu

def get_tiled_df(db, table, z, x, y):
    w, s, e, n = tu.get_tile_bounds(z, x, y)
    sql = f"select * from {table} where st_within(st_centroid(geom), st_makeenvelope({w}, {s}, {e}, {n}, 4612));"
    conn = psycopg2.connect(database=db, user='')
    return gpd.GeoDataFrame.from_postgis(sql, conn)

# ---

def crop_dem(src_dem, tz, tx, ty, dst_dem):
    west, south, east, north = tu.get_tile_bounds(tz, tx, ty)
    cesium_proj = f'+proj=tmerc +lat_0={south} +lon_0={west} +k=1.000000 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs'
    w, h = pyproj.transform(pyproj.Proj(init='epsg:4612'),
                            pyproj.Proj(cesium_proj), east, north)
    f = lambda v: int(math.ceil(v))
    iw, ih = f(w), f(h)
    os.system(
        f"gdalwarp -t_srs '{cesium_proj}' -te -100 -100 {iw+100} {ih+100} -tr 1 1 -r bilinear {src_dem} {dst_dem}")

# ---

import pyproj
from functools import partial

def get_to_cesium(z, x, y):
    west, south, _, _ = tu.get_tile_bounds(z, x, y)
    cesium_proj = f"+proj=tmerc +lat_0={south} +lon_0={west} +k=1.000000 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs"
    return partial(pyproj.transform, pyproj.Proj(init='epsg:4612'), pyproj.Proj(cesium_proj))

def get_to_latlon(z, x, y):
    west, south, _, _ = tu.get_tile_bounds(z, x, y)
    cesium_proj = f"+proj=tmerc +lat_0={south} +lon_0={west} +k=1.000000 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs"
    return partial(pyproj.transform, pyproj.Proj(cesium_proj), pyproj.Proj(init='epsg:4612'))

def get_width_height(z, x, y):
    to_cesium = get_to_cesium(z, x, y)
    west, south, east, north = tu.get_tile_bounds(z, x, y)
    wx, sy = to_cesium(west, south)
    ex, ny = to_cesium(east, north)
    return ex - wx, ny - sy

# ---

import numpy as np
from stl import mesh

def build_mesh(vertices, faces):
    vs = np.array(vertices)
    fs = np.array(faces)
    hedron = mesh.Mesh(np.zeros(len(faces), dtype=mesh.Mesh.dtype))
    for i, f in enumerate(fs):
        for j in range(3):
            hedron.vectors[i][j] = vs[f[j],:]
    return hedron

def merge_meshes(meshes):
    return mesh.Mesh(np.concatenate([m.data.copy() for m in meshes]))

# ---

import os

def write_obj(meshes, materials, path):
    base = os.path.splitext(os.path.basename(path))[0]
    with open(path, 'w') as fd:
        print = lambda s: fd.write(s + '\n')
        print('# take9 handwrite obj file:')
        print('mtllib common.mtl')
        iv, inv = 1, 1
        for mesh, material in zip(meshes, materials):
            mesh.update_normals()
            print(f'o {base}_{iv}')
            print(f'usemtl {material}')
            for vs in mesh.vectors:
                for x, y, z in vs:
                    print(f'v {x} {z} {-y}')
            for x, y, z in mesh.normals:
                print(f'vn {x} {z} {-y}')
            print('s off')
            for i, vs in enumerate(mesh.vectors):
                j, k = i * 3 + iv, i + inv
                print(f'f {j}//{k} {j+1}//{k} {j+2}//{k}')
            iv += len(mesh.vectors) * 3
            inv += len(mesh.vectors)

import json

def write_batchtable(properties, path):
    batchtable = {}
    batchtable['batchId'] = [i for i, _ in enumerate(properties)]
    for k in properties[0].keys():
        batchtable[k] = [p[k] for p in properties] 
    with open(path, 'wb') as fd:
        fd.write(json.dumps(batchtable, indent=2, ensure_ascii=False).encode('utf-8'))

# ---

from . import tile_utils as tu

def build_tileset(tiles, stop_z, postfix):
    def get_geom_error(z):
        return 2 ** (19 - z)

    def build_tileinfos(z, x, y):
        def get_tileinfo(z, x, y):
            return {
                'transform': None,
                'boundingVolume': {
                    'region': tu.get_tile_bounds(z, x, y)
                },
                'geometricError': get_geom_error(z),
                'content': {
                    'url': f'{z}_{x}_{y}_{postfix}.b3dm'
                }
            }

        if z == stop_z:
            return get_tileinfo(z, x, y)
        else:
            tileinfo = get_tileinfo(z, x, y)
            tileinfo['children'] = [build_tileinfos(z+1, i, j) 
                                    for i in range(x*2, x*2+2) for j in range(y*2, y*2+2)]
            del tileinfo['content']
            return tileinfo

    values = lambda i: [t[i] for t in tiles]
    zs, xs, ys = values(0), values(1), values(2)
    z, x1, y1, x2, y2 = min(zs), min(xs), min(ys), max(xs) + 1, max(ys) + 1
    w, n = tu.tilenum2lonlat(z, x1, y1)
    e, s = tu.tilenum2lonlat(z, x2, y2)
    root_bounds = [w, s, e, n]
    return {
      'asset': {
        'version': '1.0'
      },
      'geometricError': get_geom_error(z),
      'root': {
        'boundingVolume': {
          'region': root_bounds
        },
        'geometricError': get_geom_error(z),
        'refine': 'REPLACE',
        'children': [build_tileinfos(z, x, y) for x in range(x1, x2) for y in range(y1, y2)]
      }
    }
