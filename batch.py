#%%
# constants - enoshima (sample)
MESHES = ['523973', '523974']
GPKG = 'enoshima_shape.gpkg'
DEM = 'enoshima_dem.vrt'
# DEM = 'dem_10m.vrt'
TILES = [
    (15, 29079, 12944),  # 片瀬海岸
    (15, 29080, 12944),  # 龍口寺
    (15, 29081, 12944),  # 津西
    (15, 29079, 12945),  # 江の島参道
    (15, 29080, 12945),  # 湘南港
    (15, 29081, 12945),  # 鎌倉高校前
    (15, 29079, 12946),  # 江の島岩屋
    (15, 29080, 12946),  # 江の島灯台
]
DST_DIR = 'dst/gsi_enoshima_5m_unleveled'

#%%
# setup
import os
from glob import glob

os.remove(GPKG) if os.path.exists(GPKG) else None
for layer in ['RdCL', 'BldA']:
    for mesh in MESHES:
        for path in glob(f'../../data/gsi_nummap/{mesh}/*-*-*-{layer}-*-000?.shp'):
            os.system(f"ogr2ogr -update -append -f GPKG -nln {layer} -oo ENCODING=CP932 {GPKG} {path}")

os.system(f'gdalbuildvrt {DEM} ../../data/dem05s/52397[34].tif')
# os.system(f'gdalbuildvrt ~dem_10m.vrt ../../data/dem10s/*.tif')

#%%
# build obj from gsi data
import os
from landtile import mesh as lmesh
from landtile import roads_weaver as rw
from landtile import buildings_extender as be
from landtile import dem_digger as dd
from landtile import terrain_creator as tc
from landtile import roads_builder as rb
from landtile import buildings_builder as bb

os.system(f'cp landtile/common.mtl .')
for tz, tx, ty in TILES:
    tname = f'{tz}_{tx}_{ty}'

    road_df = rw.weave(GPKG, tz, tx, ty)
    bldg_df = be.extend(GPKG, tz, tx, ty)
    # dem = dd.dig(DEM, tz, tx, ty, road_df, bldg_df)
    dem = dd.undig(DEM, tz, tx, ty)  # 整地しない場合
    tc.create(dem, tz, tx, ty, f'{tname}_terrain')
    tc.make_image('../../data/maptiles/', tz, tx, ty, 1).save(f'{tname}_terrain.png')

    meshes, mats, props = rb.build(dem, road_df)
    lmesh.write_obj(meshes, mats, f'{tname}_roads.obj')
    meshes, mats, props = bb.build(dem, bldg_df)
    lmesh.write_obj(meshes, mats, f'{tname}_bldgs.obj')

#%%
# convert obj to gltf
import os
from glob import glob

os.system(f'mkdir -p {DST_DIR}/gltfs')
for f in glob('*_*_*_*.obj'):
    basename = os.path.splitext(os.path.basename(f))[0]
    os.system(f'./node_modules/.bin/obj2gltf -i {f} -o {DST_DIR}/gltfs/{basename}.gltf')

#%%
# output tiles.json (for threejs viewer)
import json
from pyproj import Transformer
import numpy as np
from landtile.tile import num2lonlat

t = Transformer.from_crs('epsg:4612', 'epsg:2451', always_xy=True)
xys = np.array([t.transform(*num2lonlat(*tile)) for tile in TILES])
nxys = xys - np.mean(xys, axis=0)
locs = [[f'{z}_{x}_{y}', [xx, yy]]for (z, x, y), (xx, yy) in zip(TILES, nxys.tolist())]
json.dump(locs, open(f'{DST_DIR}/gltfs/tiles.json', 'w'), indent=2)

#%%
# build cesium 3dtiles
from landtile import tileset_builder as tb

for kind in ['terrain', 'roads', 'bldgs']:
    os.system(f'mkdir -p {DST_DIR}/{kind}')
    for tz, tx, ty in TILES:
        tn = f'{tz}_{tx}_{ty}'
        os.system(f'./node_modules/.bin/obj23dtiles -i {tn}_{kind}.obj -o {DST_DIR}/{kind}/{tn}.b3dm --b3dm')
    os.system(f'for nm in {DST_DIR}/{kind}/*.b3dm; do mv $nm ${{nm%_{kind}.b3dm}}.b3dm; done')

    tb.build(TILES, f'{DST_DIR}/{kind}')

#%%
# sweep obj & mtl files
os.system(f'mkdir -p {DST_DIR}/objs')
os.system(f'mv *_*_*_*.* {DST_DIR}/objs')
