# misc utilities
import os
import math
import json
import psycopg2
import geopandas as gpd
from pyproj import Proj, transform
import functools as ft
import common.tile_utils as tu

def commit_shapes_on_db(files, db, table):
    os.system(f"psql -d {db} -c 'drop table {table};'")
    os.system(f"shp2pgsql -W cp932 -I -s 4612 -p -S {files[0]} {table} | gsed -e 's/varchar([0-9]\+)/varchar(64)/' | psql -d {db}")
    for file in files:
        os.system(f'shp2pgsql -a -W cp932 -s 4612 -S {file} {table} | psql -d {db}')

def get_tiled_df(db, table, z, x, y):
    w, s, e, n = tu.get_tile_bounds(z, x, y)
    sql = f"select * from {table} where st_within(st_centroid(geom), st_makeenvelope({w}, {s}, {e}, {n}, 4612));"
    conn = psycopg2.connect(database=db, user='')
    return gpd.GeoDataFrame.from_postgis(sql, conn)

# ---

def get_cesium_proj_str(tz, tx, ty):
    west, south, _, _ = tu.get_tile_bounds(tz, tx, ty)
    return f'+proj=tmerc +lat_0={south} +lon_0={west} +k=1.000000 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs'

def get_cesium_tile_size(tz, tx, ty):
    west, south, east, north = tu.get_tile_bounds(tz, tx, ty)
    to_cesium = ft.partial(
        transform, Proj(init='epsg:4612'), 
        Proj(get_cesium_proj_str(tz, tx, ty)))
    # to_cesium(west, south) は (0, 0) になる
    return to_cesium(east, north)

def crop_dem_for_digging(src_path, tz, tx, ty, dst_path):
    proj_str = get_cesium_proj_str(tz, tx, ty)
    iw, ih = [int(math.ceil(v))
              for v in get_cesium_tile_size(tz, tx, ty)]
    os.system(
        f"gdalwarp -t_srs '{proj_str}' -te -100 -100 {iw+100} {ih+100} -tr 1 1 -r bilinear {src_path} {dst_path}")

def crop_dem_for_tile(src_path, tz, tx, ty, dst_path):
    w, h = get_cesium_tile_size(tz, tx, ty)
    os.system(f'gdal_translate -of "GTiff" -projwin 0 {h} {w} 0 {src_path} {dst_path}')


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

def write_batchtable(properties, path):
    batchtable = {}
    batchtable['batchId'] = [i for i, _ in enumerate(properties)]
    for k in properties[0].keys():
        batchtable[k] = [p[k] for p in properties] 
    with open(path, 'wb') as fd:
        fd.write(json.dumps(batchtable, indent=2, ensure_ascii=False).encode('utf-8'))
