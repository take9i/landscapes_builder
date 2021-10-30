#%%
import os
from glob import glob

meshes, layers = ['523973', '523974'], ['RdCL', 'BldA']
GPKG = 'enoshima_shape.gpkg'
DEM = 'enoshima_dem.vrt'

os.remove(GPKG) if os.path.exists(GPKG) else None
for layer in layers:
    for mesh in meshes:
        for path in glob(f'../../data/gsi_nummap/{mesh}/*-*-*-{layer}-*-000?.shp'):
            os.system(f"ogr2ogr -update -append -f GPKG -nln {layer} -oo ENCODING=CP932 {GPKG} {path}")

os.system(f'gdalbuildvrt {DEM} ../../data/dem05s/52397[34].tif')
# os.system(f'gdalbuildvrt ~dem_10m.vrt ../../data/dem10s/*.tif')

#%%
#%%
# setup tokyocore
import os
from glob import glob

meshes, layers = ['533945', '533946', '533935', '533936'], ['RdCL', 'BldA']
GPKG = 'tokyocore_shape.gpkg'
DEM = 'tokyocore_dem.vrt'

os.remove(GPKG) if os.path.exists(GPKG) else None
for layer in layers:
    for mesh in meshes:
        for path in glob(f'../../data/gsi_nummap/{mesh}/*-*-*-{layer}-*-000?.shp'):
            os.system(f"ogr2ogr -update -append -f GPKG -nln {layer} -oo ENCODING=CP932 {GPKG} {path}")

os.system(f'gdalbuildvrt {DEM} ../../data/dem05s/5339[34][56].tif')

#%%
# setup hakone
import os
from glob import glob

meshes, layers = ['523960', '523961'], ['RdCL', 'BldA']
GPKG = 'hakone_shape.gpkg'
DEM = 'hakone_dem.vrt'

os.remove(GPKG) if os.path.exists(GPKG) else None
for layer in layers:
    for mesh in meshes:
        for path in glob(f'../../data/gsi_nummap/{mesh}/*-*-*-{layer}-*-000?.shp'):
            os.system(f"ogr2ogr -update -append -f GPKG -nln {layer} -oo ENCODING=CP932 {GPKG} {path}")

os.system(f'gdalbuildvrt {DEM} ../../data/dem05s/52396[01].tif')
