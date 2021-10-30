#%%
import batch_common as bc
from os import system


#%%
bc.setup_gsi_nummap_on_db('53394[56]')
bc.setup_landnuminfo_on_db('13')
bc.create_dem_vrt('53394[56]')

#%%
# # wide area
# tiles = [
#     (13, 7274, 3225), (13, 7275, 3225), (13, 7276, 3225),
#     (13, 7274, 3226), (13, 7275, 3226), (13, 7276, 3226), 
# ]
# core area
tiles = [
    (15, 29104, 12902),
    (15, 29104, 12903),
    (15, 29105, 12902),
    (15, 29105, 12903)
]

#%%
bc.create_tiled_objs(tiles)
# bc.convert_to_tiled_b3dms(tiles, '~tokyocore')
# bc.convert_to_tiled_gltfs(tiles, '~tokyocore')

#%%
bc.seam_dems_for_cesium_terrain(tiles, '~tokyocore_dem.tif')


#%%
system('rm -f ??_*_*.*')
system('rm ~*.*')

