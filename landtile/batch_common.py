#%%
import os

def create_db():
    os.system('createdb gsi -E UTF-8')
    os.system("psql gsi -c 'CREATE EXTENSION postgis;'")


#%%
import os
from glob import glob
from misc import commit_shapes_on_db as commit

def psql(sql): 
    os.system("psql gsi -c 'sql'")

def setup_gsi_nummap_on_db(meshcode_pattern):
    # meshcode_pattern ex. '53394[56]'
    psql('drop table rdcl, blda;')
    commit(glob(f'../../data/gsi_nummap/{meshcode_pattern}/*-RdCL-*.shp'), 'gsi', 'rdcl')
    commit(glob(f'../../data/gsi_nummap/{meshcode_pattern}/*-BldA-*.shp'), 'gsi', 'blda')

def setup_landnuminfo_on_db(prefcode):
    psql('drop table a29;')
    commit([f'../../data/landnuminfo/A29_用途地域データ/A29-11_{prefcode}_GML/A29-11_{prefcode}.shp'], 'gsi', 'a29')

def create_dem_vrt(meshcode_pattern):
    os.system(f'gdalbuildvrt dem.vrt ../dem_builder/dem05s/{meshcode_pattern}.tif')


#%%
# create terrain tiles
import os
import misc

def create_tiled_objs(tiles):
    def python(script, argstr):
        os.system(f'python {script} {argstr}')

    for tz, tx, ty in tiles:
        bname = f'{tz}_{tx}_{ty}'
        print(bname)
        os.system('rm ~*.*')
        python('weave_roads.py', f'{tz} {tx} {ty} {bname}_roads.geojson')
        python('extend_buildings.py', f'{tz} {tx} {ty} {bname}_bldgs.geojson')
        misc.crop_dem_for_digging('dem.vrt', tz, tx, ty, '~dem.tif')
        python('dig_dem.py', f'~dem.tif {bname}_roads.geojson {bname}_bldgs.geojson ~ddem.tif')
        misc.crop_dem_for_tile('~ddem.tif', tz, tx, ty, f'{bname}_ddem.tif')
        python('create_terrain.py', f'{bname}_ddem.tif {tz} {tx} {ty} {bname}_terrain.obj')
        python('build_roads.py', f'{bname}_ddem.tif {bname}_roads.geojson {bname}_roads.obj {bname}_roads.json')
        python('build_buildings.py', f'{bname}_ddem.tif {bname}_bldgs.geojson {bname}_bldgs.obj {bname}_bldgs.json')


#%%
# build cesium 3dtiles w tileset.json
from os import system, path
import json
import common.tile_utils as tu

def build_tileset(tiles, stop_z):
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
                    'url': f'{z}_{x}_{y}.b3dm'
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

def convert_to_tiled_b3dms(tiles, dst_dir):
    def obj23dtiles(argstr):
        system(f'./node_modules/.bin/obj23dtiles {argstr}')

    def store_b3dms(postfix, dst_dir):
        system(f'rm -Rf {dst_dir}; mkdir -p {dst_dir}')
        system('for f in *_*_*_%s.b3dm; do mv $f %s/${f%%_%s.b3dm}.b3dm; done' % (postfix, dst_dir, postfix))

    def store_tileset(tileset, dst_dir):
        open('~tileset.json', 'w').write(json.dumps(tileset))
        system(f' ./tileset_maker.js ~tileset.json {dst_dir}/tileset.json')

    for tz, tx, ty in tiles:
        bname = f'{tz}_{tx}_{ty}'
        obj23dtiles(f'-i {bname}_terrain.obj --b3dm')
        obj23dtiles(f'-i {bname}_roads.obj -c {bname}_roads.json --b3dm')
        obj23dtiles(f'-i {bname}_bldgs.obj -c {bname}_bldgs.json --b3dm')

    store_b3dms('terrain', f'{dst_dir}/terrains')
    store_b3dms('roads', f'{dst_dir}/roads')
    store_b3dms('bldgs', f'{dst_dir}/bldgs')

    tileset = build_tileset(tiles, 15)
    store_tileset(tileset, f'{dst_dir}/terrains')
    store_tileset(tileset, f'{dst_dir}/roads')
    store_tileset(tileset, f'{dst_dir}/bldgs')


#%%
from os import system

def convert_to_tiled_gltfs(tiles, dst_dir):
    def obj2gltf(argstr):
        system(f'./node_modules/.bin/obj2gltf {argstr}')

    for tz, tx, ty in tiles:
        bname = f'{tz}_{tx}_{ty}'
        obj2gltf(f'-i {bname}_terrain.obj -o {bname}_terrain.gltf')
        obj2gltf(f'-i {bname}_bldgs.obj -o {bname}_bldgs.gltf')
        obj2gltf(f'-i {bname}_roads.obj -o {bname}_roads.gltf')

    system(f'rm -Rf {dst_dir}/gltfs; mkdir -p {dst_dir}/gltfs')
    system(f'mv *.gltf {dst_dir}/gltfs')


#%%
# seam dems for making cesium terrain
from os import system

def seam_dems_for_cesium_terrain(tiles, dst_dem):
    for i, (tz, tx, ty) in enumerate(tiles):
        system(f'gdalwarp -t_srs EPSG:4612 {tz}_{tx}_{ty}_ddem.tif ~{i}_dem.tif')
    system('gdalbuildvrt ~cdem.vrt ~*_dem.tif')
    system(f'gdalwarp -t_srs EPSG:4612 ~cdem.vrt {dst_dem}')


#%%
import functools as ft
import pyproj
import common.tile_utils as tu
import misc

def print_tiles_position(tiles):
    transform = ft.partial(pyproj.transform, pyproj.Proj(
        init='epsg:4612'), misc.get_cesium_proj_str(*tiles[0]))
    for tz, tx, ty in tiles:
        w, s, e, n = tu.get_tile_bounds(tz, tx, ty)
        print([f'{tz}_{tx}_{ty}', list(transform(w, s))])

